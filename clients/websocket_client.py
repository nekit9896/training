import asyncio
import logging
import time
from typing import Any, Callable, List, Optional

import msgpack
import websockets
from websockets import InvalidStatus

from clients.signalr_negotiator import SignalRNegotiator
from constants.architecture_constants import WebSocketClientConstants as WS_Const
from utils.msgpack_utils.message_filters import is_desired_invocation_id, is_desired_type
from utils.msgpack_utils.msgpack_utils import encode_with_varint_prefix, parse_message

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    Асинхронный ws-клиент для api-gateway по протоколу Async Api
    """

    def __init__(
        self,
        host: str,
        access_token: str,
        x_user_id: str,
        reconnect_interval: float = WS_Const.DEFAULT_RECONNECT_INTERVAL,
    ):
        self._host = host
        self._access_token = access_token
        self._x_user_id = x_user_id
        self._reconnect_interval = reconnect_interval
        self._ws_url = f"wss://{host.rstrip('/')}{WS_Const.WS_HUBS}"
        self._buffer = b""
        self._next_id: int = WS_Const.START_INVOCATION_ID

        self._ws: websockets.ClientConnection | None = None
        self.recv_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._ping_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._invocation_id: Optional[str] = None
        self.suppress_recv_logging: bool = False

        # Negotiate обязателен перед wss: без connectionToken api-gateway не поднимает консьюмеры
        self._negotiator = SignalRNegotiator(host, access_token)
        self._connection_id: Optional[str] = None
        self._connection_token: Optional[str] = None
        self._on_disconnected: Optional[Callable[[], None]] = None

        # Счётчики для мониторинга соединения: рост принятых сообщений и пинги означают,
        # что клиент подписан и соединение живо
        self.ws_pings_sent: int = 0
        self.ws_pings_failed: int = 0
        self.messages_received: int = 0
        self.reconnect_count: int = 0

    @property
    def invocation_id(self):
        return self._invocation_id

    @property
    def connection_id(self) -> Optional[str]:
        """connectionId из negotiate: используется для диагностики соединения в логах."""
        return self._connection_id

    @property
    def connection_token(self) -> Optional[str]:
        """connectionToken из negotiate: передаётся в wss URL как параметр id="""
        return self._connection_token

    def set_disconnected_handler(self, handler: Optional[Callable[[], None]]) -> None:
        """
        Регистрирует уведомление о потере соединения.

        В момент обрыва тест может ничего не читать из очереди и о разрыве не узнает,
        а авто-реконнект надо поднять немедленно, иначе api-gateway перестанет вычитывать сообщения подписок.
        """
        self._on_disconnected = handler

    def clear_queue(self):
        """
        Очищает очередь путем пересоздания экземпляра класса очереди
        """
        while not self.recv_queue.empty():
            try:
                self.recv_queue.get_nowait()
                self.recv_queue.task_done()
            except asyncio.QueueEmpty as message_empty:
                logger.info(f"Очередь сообщений очищена: {message_empty}")
                break

    async def __aenter__(self):
        await self._connect_loop()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._log_connection_summary()
        self._stop_event.set()
        await self._cancel_task(self._ping_task)
        self._ping_task = None
        await self._cancel_task(self._recv_task)
        self._recv_task = None
        if self._ws:
            await self._ws.close()
        self._negotiator.close()

        # TODO: дергать ручку завершения сессии в LDS-4083

    async def _handshake(self) -> None:
        payload = WS_Const.HANDSHAKE_MESSAGE + WS_Const.RS.decode()
        logger.debug(
            f"Отправлен handshake: {payload}",
        )
        await self._ws.send(payload)

        buf = self._buffer
        finish = time.monotonic() + WS_Const.HANDSHAKE_WAITING
        while time.monotonic() < finish:
            chunk = await self._ws.recv()
            logger.debug(f"Ответ на handshake: {chunk}")
            buf += chunk.encode() if isinstance(chunk, str) else chunk
            if WS_Const.RS in buf:
                return

        raise TimeoutError("Handshake timeout: не получили сообщение с разделителем RS за указанное время")

    async def _connect_loop(self, timeout: float = WS_Const.WS_CONNECT_TIMEOUT_SECONDS) -> None:
        """
        Цикл подключения с повторными попытками до наступления stop_event
        или истечения WS_CONNECT_TIMEOUT_SECONDS.
        """
        deadline = time.monotonic() + timeout
        attempt = 0
        transient_errors = (ConnectionError, OSError, asyncio.TimeoutError, InvalidStatus)

        while not self._stop_event.is_set():
            attempt += 1
            try:
                # Negotiate выполняется на каждую попытку подключения: connectionToken одноразовый
                # и выдаётся под конкретное соединение
                connection_token = await asyncio.to_thread(self._negotiate)
                self.ws_request = self._build_ws_request_url(connection_token)
                logger.info(f"Попытка подключения по wss: {self._ws_url}/?token=...&xUserId=...&id=...")
                self._ws = await websockets.connect(
                    self.ws_request,
                    ping_interval=WS_Const.PING_INTERVAL,
                    ping_timeout=WS_Const.PING_TIMEOUT,
                    close_timeout=WS_Const.CLOSE_TIMEOUT,
                )
                # Handshake
                await self._handshake()
                # Запускаем приём сообщений и SignalR keep-alive в фоне
                self._recv_task = asyncio.create_task(self._recv_loop())
                self._ping_task = asyncio.create_task(self._ping_loop())
                logger.info(f"Websocket connected (connectionId={self._connection_id})")
                return
            except transient_errors as exc:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(
                        f"WSS hub не готов за {WS_Const.WS_CONNECT_TIMEOUT_SECONDS} с " f"(попыток: {attempt}): {exc}"
                    ) from exc
                status_info = ""
                if isinstance(exc, InvalidStatus):
                    response = getattr(exc, "response", None)
                    if response is not None:
                        status_info = f", HTTP {response.status_code}"
                logger.warning(
                    "WSS подключение не установлено (попытка %s%s): %s. " "Повтор через %s с, осталось %.0f с",
                    attempt,
                    status_info,
                    exc,
                    self._reconnect_interval,
                    remaining,
                )
                await asyncio.sleep(self._reconnect_interval)

    async def _recv_loop(self) -> None:
        """
        Прием сообщений, парсинг и отправка в очередь.
        """
        assert self._ws is not None

        while not self._stop_event.is_set():
            try:
                chunk = await self._ws.recv()
                if not self.suppress_recv_logging:
                    logger.debug(f"Сырые биты до обработки: {chunk[:100]}")
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket соединение разорвано: {e}")
                self._notify_disconnected()
                return

            result_message = parse_message(chunk)
            # Служебные SignalR-сообщения (ping/close) не относятся к подпискам: если класть их
            # в очередь, они разбавляют батчи, которые сценарии вычитывают при накоплении
            if self._is_service_signalr_message(result_message):
                logger.debug(f"Пропущено служебное сообщение SignalR: {result_message}")
                continue

            self.messages_received += 1
            await self.recv_queue.put(result_message)
            if not self.suppress_recv_logging:
                str_message = str(result_message)
                logger.info(
                    f"Обработанное сообщение от api-gateway: {str_message[:200]}... полное сообщение в attach",
                )
            continue

    def _negotiate(self) -> str:
        """
        Выполняет negotiate и возвращает connectionToken для параметра id=.

        Вызов синхронный и выполняется через asyncio.to_thread, чтобы не блокировать
        event loop: на постоянном соединении в этом же loop живут приём сообщений и пинги.
        """
        result = self._negotiator.negotiate(self._x_user_id)
        self._connection_id = result.connection_id
        self._connection_token = result.connection_token
        return result.connection_token

    def _build_ws_request_url(self, connection_token: str) -> str:
        """
        Собирает wss URL как у фронта: token, xUserId и id=connectionToken.

        Параметр id= связывает wss-соединение с записью negotiate, по которой api-gateway
        держит консьюмеры core и layer builder для подписанного клиента.
        """
        return (
            f"{self._ws_url}/?token={self._access_token}&xUserId={self._x_user_id}"
            f"&{WS_Const.WS_ID_QUERY_PARAM}={connection_token}"
        )

    async def _ping_loop(self) -> None:
        """
        Отправляет SignalR Ping ([6]) раз в SIGNALR_PING_INTERVAL_S.

        Сервер SignalR ждёт от клиента любое сообщение в пределах ClientTimeoutInterval.
        Protocol-level ping вебсокета (ping_interval) для этого не засчитывается, поэтому без [6]
        сервер считает клиента мёртвым, рвёт соединение и перестаёт вычитывать сообщения подписок.
        """
        assert self._ws is not None
        packet = encode_with_varint_prefix(msgpack.packb([WS_Const.PING_MESSAGE_TYPE], use_bin_type=True))

        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(WS_Const.SIGNALR_PING_INTERVAL_S)
                if self._stop_event.is_set() or not self._ws:
                    return
                await self._ws.send(packet)
                self.ws_pings_sent += 1
                logger.debug("Отправлен SignalR ping [6]")
            except (websockets.WebSocketException, OSError) as error:
                # Прогон не роняем: фиксируем ошибку и сообщаем владельцу, он поднимет реконнект
                self.ws_pings_failed += 1
                logger.warning(f"Не удалось отправить SignalR ping [6]: {error}")
                self._notify_disconnected()
                return

    @staticmethod
    def _is_service_signalr_message(message: Any) -> bool:
        """True для служебных сообщений SignalR (Ping/Close) - в очередь подписок они не попадают."""
        if not isinstance(message, list) or not message:
            return False
        message_type = message[WS_Const.SIGNALR_MESSAGE_TYPE_INDEX]
        return message_type in (WS_Const.PING_MESSAGE_TYPE, WS_Const.CLOSE_MESSAGE_TYPE)

    def _notify_disconnected(self) -> None:
        """Уведомляет о разрыве; ошибка обработчика не должна ронять прогон."""
        if self._on_disconnected is None:
            return
        try:
            self._on_disconnected()
        except Exception as error:
            logger.warning(f"Обработчик разрыва соединения завершился с ошибкой: {error}")

    def _log_connection_summary(self) -> None:
        """
        Выводит итоги работы соединения: пинги, принятые сообщения, размер очереди.

        Смысл мониторинга: отправленные пинги вместе с растущим числом принятых сообщений
        означают, что клиент подписан и соединение активно, то есть api-gateway вычитывает
        сообщения подписок, а не копит их.
        """
        logger.info(
            "[WS_HEALTH] connectionId=%s pings_sent=%s pings_failed=%s messages_received=%s "
            "queue_size=%s reconnects=%s",
            self._connection_id,
            self.ws_pings_sent,
            self.ws_pings_failed,
            self.messages_received,
            self.recv_queue.qsize(),
            self.reconnect_count,
        )

    @staticmethod
    async def _cancel_task(task: Optional[asyncio.Task]) -> None:
        """Отменяет фоновую задачу и дожидается завершения, не пробрасывая CancelledError."""
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def invoke(self, target: str, args: list) -> None:
        """
        Отправляет удаленный вызов invocation о websocket соединению

        Метод формирует сообщение по протоколу SignalR, включая:
        - типа сообщения
        - заголовки
        - уникальный идентификатор запроса
        - имя целевого метода
        - аргументы запроса

        Сообщение запаковывается в messagepack и отправляется через текущее websocket соединение
        """

        if not self._ws:
            raise websockets.WebSocketException("Не установлено подключение по wss")
        self._invocation_id = str(self._next_id)
        self._next_id += 1
        invocation = [
            WS_Const.DEFAULT_SIGNALR_MESSAGE_TYPE,
            WS_Const.DEFAULT_SIGNALR_MAP_HEADERS,
            self._invocation_id,
            target,
            [args],
        ]
        logger.info(f"Сообщение подготовлено к отправке: {invocation}")
        payload = msgpack.packb(invocation, use_bin_type=True)
        packet = encode_with_varint_prefix(payload)
        logger.debug(f"Отправляем сообщение: {packet}")
        await self._ws.send(packet)

    async def invoke_stream(self, target: str, args: list) -> None:
        """
        Отправляет streaming-вызов (StreamInvocation) по протоколу SignalR.
        """
        if not self._ws:
            raise websockets.WebSocketException("Не установлено подключение по wss")
        self._invocation_id = str(self._next_id)
        self._next_id += 1
        invocation = [
            WS_Const.STREAM_INVOCATION_MESSAGE_TYPE,
            WS_Const.DEFAULT_SIGNALR_MAP_HEADERS,
            self._invocation_id,
            target,
            [args],
        ]
        logger.info(f"Streaming-сообщение подготовлено к отправке: {invocation}")
        payload = msgpack.packb(invocation, use_bin_type=True)
        packet = encode_with_varint_prefix(payload)
        await self._ws.send(packet)

    async def receive_by_type(self, message_type: str, timeout: float = WS_Const.FILTERING_TIMEOUT) -> List[Any]:
        """
        Фильтрует сообщения по message_type
        """
        try:
            return await self._receive_by(filter_func=lambda msg: is_desired_type(msg, message_type), timeout=timeout)
        except websockets.WebSocketException:
            raise websockets.WebSocketException(f"Ошибка при фильтрации сообщений по {message_type}")

    async def receive_by_invocation_id(
        self, invocation_id: str, timeout: float = WS_Const.FILTERING_TIMEOUT
    ) -> List[Any]:
        """
        Фильтрует сообщения по invocation_id
        """
        try:
            return await self._receive_by(
                filter_func=lambda msg: is_desired_invocation_id(msg, invocation_id), timeout=timeout
            )
        except websockets.WebSocketException:
            raise websockets.WebSocketException("Ошибка при фильтрации сообщений по invocation_id")

    async def _receive_by(self, filter_func: Callable[[list], bool], timeout: float) -> List[Any]:
        """
        Ждет и фильтрует сообщение по filter_func
        """
        # 1) Единая точка вычисления дедлайна
        deadline = time.monotonic() + timeout

        while True:
            # 2) Остаток времени до таймаута
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(f"Timeout при фильтрации сообщений {timeout:.1f} секунд")

            try:
                # 3) Получает сообщение
                msg = await asyncio.wait_for(self.recv_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                # 4) Явно перехватывает и пробрасывает свой TimeoutError
                raise asyncio.TimeoutError(f"Timeout при фильтрации сообщений {timeout:.1f} секунд")

            # 5) Фильтрация по filter_func
            if isinstance(msg, list) and filter_func(msg):
                return msg

    async def reconnect(self):
        """
        Переподключение websocket соединения
        """
        try:
            await self._cancel_task(self._ping_task)
            self._ping_task = None
            await self._cancel_task(self._recv_task)
            self._recv_task = None

            if self._ws:
                await self._ws.close()
                self._ws = None
            await self._connect_loop(WS_Const.WS_RECONNECT_TIMEOUT_SECONDS)
            self.reconnect_count += 1
            return self
        except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
            raise RuntimeError(f"Ошибка при попытке переподключения {error}")
