"""
Владелец постоянного ws-соединения с хабом на время набора данных.

Почему соединение живёт в отдельном потоке со своим event loop: фикстура offset_wait ждёт
свой offset через time.sleep в главном потоке (до 55 минут), и loop pytest-asyncio в это
время не работает. Если бы соединение жило в loop pytest, пинги вставали бы на всё время
ожидания, сервер SignalR считал бы клиента мёртвым, а api-gateway переставал бы вычитывать
сообщения - то есть воспроизвёлся бы исходный баг с накоплением слоёв.

Менеджер повторяет поведение фронта: negotiate -> wss по connectionToken -> handshake ->
bundle подписок -> пинги ws ([6]) и rest (/apigateway/Ping) раз в 15 секунд.
Ошибки пингов и подключения прогон не роняют: они логируются и повторяются.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid
from typing import Any, Callable, Coroutine, Dict, List, Optional, Tuple

from allure import attach, attachment_type

from clients.http_client import StandHttpClient
from clients.persistent_ws_client import PersistentWsClient
from clients.websocket_client import WebSocketClient
from clients.ws_message_dispatcher import SubscriptionScope, WsMessageDispatcher
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.architecture_constants import PersistentConnectionConstants as PersistConst

logger = logging.getLogger(__name__)

TOKEN_EXPIRED_HINT_CODES: Tuple[str, ...] = ("401", "403")


class WsConnectionManager:
    """
    Постоянное соединение набора данных: фоновый loop, bundle подписок, пинги, реконнект.
    """

    def __init__(self, host: str, access_token: str, x_user_id: str, bundle: List[Tuple[str, Any]]) -> None:
        """
        :param host: хост api-gateway
        :param access_token: JWT access token набора данных
        :param x_user_id: идентификатор пользователя, полученный из /Ping
        :param bundle: подписки, которые соединение держит фоном (набор фронта)
        """
        self._host = host
        self._access_token = access_token
        self._x_user_id = x_user_id
        self._bundle = bundle

        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._client: Optional[WebSocketClient] = None
        self._http_client = StandHttpClient(host, access_token)
        self._stopped = threading.Event()
        self._tasks: List[asyncio.Task] = []
        self._started_at: Optional[float] = None

        self.dispatcher = WsMessageDispatcher()
        self.last_invocation_id: Optional[str] = None
        self.connections_established: int = 0
        self.connect_failures: int = 0
        self.rest_pings_sent: int = 0
        self.rest_pings_failed: int = 0

    @property
    def loop(self) -> asyncio.AbstractEventLoop:
        """Event loop фонового соединения: через него проксируются вызовы из потока теста."""
        if self._loop is None:
            raise RuntimeError("Постоянное соединение не запущено: event loop отсутствует")
        return self._loop

    @property
    def connection_id(self) -> Optional[str]:
        """connectionId текущего соединения из negotiate."""
        return self._client.connection_id if self._client else None

    def start(self) -> None:
        """
        Запускает фоновый поток и постоянное соединение.

        Ошибка подключения не пробрасывается: прогон продолжается, а соединение поднимает
        supervisor-задача с экспоненциальным backoff.
        """
        if self._thread is not None:
            logger.warning("[WS_MANAGER] Соединение уже запущено, повторный start пропущен")
            return

        self._thread = threading.Thread(target=self._run_loop, name="ws-connection-manager", daemon=True)
        self._thread.start()
        self._wait_for_loop()
        self._started_at = time.monotonic()
        self._call_sync(self._start_async, timeout=PersistConst.START_TIMEOUT_S)
        # Ждём фактического подключения: тесты стартуют сразу после setup набора, а соединение
        # поднимается асинхронно (negotiate + несколько попыток wss). Без ожидания первый тест
        # попал бы на ещё не готовое соединение.
        is_connected = self._call_sync(self._wait_for_connection, PersistConst.START_TIMEOUT_S)
        if is_connected:
            logger.info(f"[WS_MANAGER] Постоянное соединение запущено для хоста {self._host}")
        else:
            logger.warning(
                "[WS_MANAGER] [ALERT] Постоянное соединение не поднялось за отведённое время, "
                "supervisor продолжит попытки в фоне"
            )

    def stop(self) -> None:
        """Останавливает задачи, соединение и поток; публикует итоги в лог и Allure."""
        if self._thread is None:
            return
        try:
            self._call_sync(self._stop_async, timeout=PersistConst.STOP_TIMEOUT_S)
        except Exception as error:
            logger.warning(f"[WS_MANAGER] Ошибка при остановке соединения: {error}")
        finally:
            self._stopped.set()
            if self._loop is not None:
                self._loop.call_soon_threadsafe(self._loop.stop)
            if self._thread is not None:
                self._thread.join(timeout=PersistConst.STOP_TIMEOUT_S)
            self._log_health()
            self._attach_health_summary("Итоги постоянного ws-соединения")
            self._http_client.session.close()
            self._thread = None

    def _wait_for_loop(self) -> None:
        """Ждёт создания event loop в фоновом потоке."""
        deadline = time.monotonic() + PersistConst.LOOP_START_TIMEOUT_S
        while self._loop is None and time.monotonic() < deadline:
            time.sleep(0.05)
        if self._loop is None:
            raise RuntimeError("Не удалось запустить event loop постоянного соединения")

    async def _start_async(self) -> None:
        """Создаёт клиента и фоновые задачи: маршрутизация, REST Ping, мониторинг, supervisor."""
        self._client = WebSocketClient(self._host, self._access_token, self._x_user_id)
        # Приём сообщений на постоянном соединении непрерывный: без подавления log-cli
        # утонет в сотнях строк в минуту. Содержимое видно в attach парсера внутри теста.
        self._client.suppress_recv_logging = True
        self._client.set_disconnected_handler(self._on_disconnected)
        self._tasks = [
            asyncio.create_task(self._dispatch_loop(), name="ws-dispatch"),
            asyncio.create_task(self._rest_ping_loop(), name="ws-rest-ping"),
            asyncio.create_task(self._health_log_loop(), name="ws-health"),
            asyncio.create_task(self._supervisor_loop(), name="ws-supervisor"),
        ]

    def _on_disconnected(self) -> None:
        """
        Реакция на разрыв соединения из приёмного или пингового цикла.

        Реконнект здесь не запускается намеренно: этим занимается supervisor-задача,
        иначе при обрыве обоих циклов возникли бы два параллельных переподключения.
        """
        logger.warning("[WS_MANAGER] Соединение разорвано, реконнект выполнит supervisor")

    async def _supervisor_loop(self) -> None:
        """
        Следит за соединением и поднимает его заново.

        Соединение должно жить всё время набора, включая паузы между тестами и offset-ожидания:
        именно живое соединение с пингами держит консьюмеры api-gateway, которые вычитывают
        сообщения core и layer builder.
        """
        while not self._stopped.is_set():
            if not self._is_connected():
                await self._connect_with_backoff()
            await asyncio.sleep(PersistConst.CONNECTION_CHECK_INTERVAL_S)

    def _is_connected(self) -> bool:
        """True, если клиент создан и его соединение активно."""
        return bool(self._client and self._client.is_connected)

    async def _wait_for_connection(self, timeout: float) -> bool:
        """Ждёт появления активного соединения; возвращает False по истечении таймаута."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline and not self._stopped.is_set():
            if self._is_connected():
                return True
            await asyncio.sleep(PersistConst.RECEIVE_POLL_INTERVAL_S)
        return self._is_connected()

    async def _connect_with_backoff(self) -> None:
        """
        Устанавливает соединение и восстанавливает подписки, при ошибке повторяет.

        Прогон не прерывается: ошибки логируются, backoff растёт до RECONNECT_MAX_BACKOFF_S.
        """
        backoff = PersistConst.RECONNECT_BACKOFF_S
        while not self._stopped.is_set():
            try:
                await self._client.connect()
                self.connections_established += 1
                logger.info(
                    f"[WS_MANAGER] [OK] Постоянное соединение установлено "
                    f"(connectionId={self._client.connection_id})"
                )
                await self._subscribe_bundle()
                await self._restore_scope_subscriptions()
                return
            except Exception as error:
                self.connect_failures += 1
                logger.warning(f"[WS_MANAGER] Не удалось установить соединение: {error}. Повтор через {backoff:.0f} с")
                if any(code in str(error) for code in TOKEN_EXPIRED_HINT_CODES):
                    logger.warning("[WS_MANAGER] Похоже на истёкший JWT: требуется новый access token")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, PersistConst.RECONNECT_MAX_BACKOFF_S)

    async def _subscribe_bundle(self) -> None:
        """Отправляет bundle подписок фронта: они и держат консьюмеры gateway активными."""
        for target, args in self._bundle:
            try:
                await self._client.invoke(target, args)
                logger.info(f"[WS_MANAGER] Bundle-подписка отправлена: {target}")
            except Exception as error:
                logger.warning(f"[WS_MANAGER] Не удалось отправить bundle-подписку {target}: {error}")

    async def _restore_scope_subscriptions(self) -> None:
        """После реконнекта возвращает подписки активных тестов (bundle отправлен отдельно)."""
        for target, args in self.dispatcher.active_subscriptions():
            try:
                await self._client.invoke(target, args)
                logger.info(f"[WS_MANAGER] Подписка теста восстановлена: {target}")
            except Exception as error:
                logger.warning(f"[WS_MANAGER] Не удалось восстановить подписку {target}: {error}")

    async def _dispatch_loop(self) -> None:
        """Перекладывает сообщения из очереди клиента в диспетчер областей видимости."""
        while not self._stopped.is_set():
            client = self._client
            if client is None:
                await asyncio.sleep(PersistConst.DISPATCH_IDLE_TIMEOUT_S)
                continue
            try:
                message = await asyncio.wait_for(
                    client.recv_queue.get(), timeout=PersistConst.DISPATCH_IDLE_TIMEOUT_S
                )
            except asyncio.TimeoutError:
                continue
            except Exception as error:
                logger.warning(f"[WS_MANAGER] Ошибка приёма сообщения из очереди клиента: {error}")
                await asyncio.sleep(PersistConst.DISPATCH_IDLE_TIMEOUT_S)
                continue

            try:
                self.dispatcher.route(message)
            except Exception as error:
                logger.warning(f"[WS_MANAGER] Ошибка маршрутизации сообщения: {error}")

    async def _rest_ping_loop(self) -> None:
        """Шлёт REST Ping раз в 15 с: так же делает фронт, и gateway видит живого клиента."""
        while not self._stopped.is_set():
            await asyncio.sleep(HttpConst.REST_PING_INTERVAL_S)
            if self._stopped.is_set():
                return
            try:
                await asyncio.to_thread(self._send_rest_ping)
                self.rest_pings_sent += 1
            except Exception as error:
                # Прогон не роняем: пинг повторится на следующей итерации
                self.rest_pings_failed += 1
                logger.warning(f"[WS_MANAGER] REST Ping не выполнен: {error}")

    def _send_rest_ping(self) -> None:
        """Выполняет POST /apigateway/Ping с x-tn-correlation-id (requests, в отдельном потоке)."""
        self._http_client.ping(str(uuid.uuid4()))

    async def _health_log_loop(self) -> None:
        """Периодически логирует состояние соединения: пинги, счётчики, очереди."""
        while not self._stopped.is_set():
            await asyncio.sleep(PersistConst.HEALTH_LOG_INTERVAL_S)
            if self._stopped.is_set():
                return
            self._log_health()

    def health_snapshot(self) -> Dict[str, Any]:
        """Сводка состояния соединения для логов и Allure."""
        client = self._client
        uptime_seconds = time.monotonic() - self._started_at if self._started_at else 0.0
        return {
            "connectionId": self.connection_id,
            "isConnected": self._is_connected(),
            "uptimeSeconds": round(uptime_seconds),
            "connectionsEstablished": self.connections_established,
            "connectFailures": self.connect_failures,
            "wsPingsSent": client.ws_pings_sent if client else 0,
            "wsPingsFailed": client.ws_pings_failed if client else 0,
            "restPingsSent": self.rest_pings_sent,
            "restPingsFailed": self.rest_pings_failed,
            "messagesReceived": client.messages_received if client else 0,
            "messagesRouted": self.dispatcher.messages_routed,
            "messagesDropped": self.dispatcher.messages_dropped,
            "clientReconnects": client.reconnect_count if client else 0,
        }

    def _log_health(self) -> None:
        """Выводит сводку соединения в лог: рост счётчиков означает, что клиент подписан и жив."""
        logger.info(f"[WS_MANAGER] [WS_HEALTH] {self.health_snapshot()}")

    def _attach_health_summary(self, name: str) -> None:
        """Публикует итоги соединения в Allure."""
        try:
            body = "\n".join(f"{key}: {value}" for key, value in self.health_snapshot().items())
            attach(body, name=name, attachment_type=attachment_type.TEXT)
        except (KeyError, RuntimeError) as error:
            logger.debug(f"Allure attach итогов соединения пропущен: {error}")

    def open_scope(self, scope_id: str) -> SubscriptionScope:
        """Открывает область видимости теста на постоянном соединении."""
        return self._call_sync(self._open_scope_async, scope_id)

    def close_scope(self, scope: SubscriptionScope) -> None:
        """Закрывает область видимости теста и уничтожает его очереди."""
        self._call_sync(self._close_scope_async, scope.scope_id)

    def client_for(self, scope: SubscriptionScope) -> PersistentWsClient:
        """Фасад соединения для конкретного теста."""
        return PersistentWsClient(self, scope)

    async def _open_scope_async(self, scope_id: str) -> SubscriptionScope:
        """Создаёт область видимости внутри loop соединения."""
        return self.dispatcher.open_scope(scope_id)

    async def _close_scope_async(self, scope_id: str) -> None:
        """Закрывает область видимости внутри loop соединения."""
        self.dispatcher.close_scope(scope_id)

    async def invoke(self, scope: SubscriptionScope, target: str, args: Any) -> None:
        """
        Отправляет подписку теста.

        watermark сдвигается до отправки: контент, прилетевший от подписок прошлых тестов,
        в проверки текущего теста попасть не может. Подписка запоминается, чтобы восстановить
        её после реконнекта.
        """
        await self._ensure_connected_for_call()
        self.dispatcher.register_subscription(scope, target, args)
        self.dispatcher.advance_watermark(scope)
        await self._client.invoke(target, args)
        self.last_invocation_id = self._client.invocation_id

    async def invoke_stream(self, scope: SubscriptionScope, target: str, args: Any) -> None:
        """Отправляет streaming-вызов; в реестр не добавляется, потому что он одноразовый."""
        await self._ensure_connected_for_call()
        self.dispatcher.advance_watermark(scope)
        await self._client.invoke_stream(target, args)
        self.last_invocation_id = self._client.invocation_id

    async def reconnect_now(self) -> None:
        """Принудительное переподключение с восстановлением bundle и подписок тестов."""
        self._ensure_client()
        await self._client.reconnect()
        await self._subscribe_bundle()
        await self._restore_scope_subscriptions()

    def _ensure_client(self) -> None:
        """Проверяет, что клиент соединения создан."""
        if self._client is None:
            raise ConnectionError("Постоянное соединение не инициализировано")

    async def _ensure_connected_for_call(self) -> None:
        """
        Ждёт восстановления соединения перед вызовом теста.

        Ожидание нужно, потому что supervisor поднимает соединение асинхронно: без него обрыв
        соединения в момент подписки ронял бы тест вместо прозрачного восстановления.
        Если соединение так и не появилось, ошибка содержит диагностику вместо обезличенного
        таймаута ожидания сообщения.
        """
        if self._is_connected():
            return
        self._ensure_client()
        if await self._wait_for_connection(PersistConst.CALL_CONNECTION_WAIT_S):
            return
        snapshot = self.health_snapshot()
        raise ConnectionError(
            f"Постоянное соединение не активно: isConnected={snapshot['isConnected']}, "
            f"connectionsEstablished={snapshot['connectionsEstablished']}, "
            f"connectFailures={snapshot['connectFailures']}, wsPingsSent={snapshot['wsPingsSent']}"
        )

    async def _stop_async(self) -> None:
        """Останавливает фоновые задачи и закрывает соединение."""
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            try:
                await task
            except asyncio.CancelledError:
                pass
            except Exception as error:
                logger.warning(f"[WS_MANAGER] Фоновая задача завершилась с ошибкой: {error}")
        self._tasks = []
        if self._client is not None:
            await self._client.close()

    def _run_loop(self) -> None:
        """Точка входа фонового потока: собственный event loop на всё время набора."""
        loop = asyncio.new_event_loop()
        self._loop = loop
        asyncio.set_event_loop(loop)
        try:
            loop.run_forever()
        finally:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception as error:
                logger.debug(f"[WS_MANAGER] shutdown_asyncgens завершился с ошибкой: {error}")
            loop.close()
            logger.info("[WS_MANAGER] Event loop постоянного соединения закрыт")

    def _call_sync(
        self,
        coroutine_factory: Callable[..., Coroutine],
        *args: Any,
        timeout: float = PersistConst.CALL_TIMEOUT_S,
    ) -> Any:
        """Выполняет корутину в loop соединения из основного потока и ждёт результат."""
        future = asyncio.run_coroutine_threadsafe(coroutine_factory(*args), self.loop)
        return future.result(timeout=timeout)
