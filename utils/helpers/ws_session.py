"""
Постоянная ws-сессия на датасет, имитирующая подключение фронта.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

import requests

from clients.websocket_client import WebSocketClient
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.architecture_constants import StandConstants
from constants.architecture_constants import WebSocketClientConstants as WS_Const

logger = logging.getLogger(__name__)


class WsSessionManager:
    """Управляет постоянным ws-соединением датасета: подписки, keepalive, реконнект."""

    def __init__(self, group_state: dict, client: WebSocketClient) -> None:
        self._group_state = group_state
        self._client = client
        self._stop_event = asyncio.Event()
        self._generation = group_state.get("dataset_generation")
        self._correlation_id = str(uuid.uuid4())
        self._supervisor_task: asyncio.Task | None = None
        self._rest_ping_task: asyncio.Task | None = None
        self._heartbeat_task: asyncio.Task | None = None
        self._rest_ping_count = 0
        self._last_received = 0
        self._last_sent_ping = 0
        self._last_rest_ping = 0

    async def start(self) -> None:
        """Подписывается на bundle и запускает фоновые задачи."""
        await self._subscribe_bundle()
        self._supervisor_task = asyncio.create_task(self._supervisor_loop())
        self._rest_ping_task = asyncio.create_task(self._rest_ping_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("[WS_SESSION] сессия запущена (correlation_id=%s)", self._correlation_id)

    async def stop(self) -> None:
        """Останавливает фоновые задачи."""
        self._stop_event.set()
        for task in (self._rest_ping_task, self._supervisor_task, self._heartbeat_task):
            if task is not None:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        logger.info("[WS_SESSION] сессия остановлена")

    def _current_tu_id(self) -> int | None:
        """tuId для MainPage: resolved из Администрирования, либо legacy из маркера."""
        return self._group_state.get("resolved_tu_id") or self._group_state.get("legacy_tu_id")

    async def _subscribe_bundle(self) -> None:
        """Подписывается на bundle так же, как это делает фронт."""
        tu_id = self._current_tu_id()
        subscriptions = [
            (WS_Const.SUBSCRIBE_PLAYER_STATUS_REQUEST, []),
            (WS_Const.SUBSCRIBE_SELF_DIAGNOSTIC_REQUEST, []),
        ]
        if tu_id is not None:
            subscriptions.append(
                (WS_Const.SUBSCRIBE_MAIN_PAGE_INFO_REQUEST, {"tuIds": [tu_id], "additionalProperties": None})
            )
        for invoke_type, invoke_params in subscriptions:
            try:
                await self._client.invoke(invoke_type, invoke_params)
            except Exception as error:
                logger.warning("[WS_SESSION] не удалось подписаться на %s: %s", invoke_type, error)
        logger.info("[WS_SESSION] bundle-подписки оформлены (tu_id=%s)", tu_id)

    async def _supervisor_loop(self) -> None:
        """Следит за состоянием соединения и сменой датасета."""
        while not self._stop_event.is_set():
            await asyncio.sleep(WS_Const.WS_SESSION_SUPERVISOR_INTERVAL_SECONDS)
            if self._stop_event.is_set():
                return
            generation = self._group_state.get("dataset_generation")
            if not self._client.is_connected or generation != self._generation:
                logger.info(
                    "[WS_SESSION] переподключение: is_connected=%s, generation %s -> %s",
                    self._client.is_connected,
                    self._generation,
                    generation,
                )
                await self._reestablish(generation)

    async def _reestablish(self, new_generation: int | None) -> None:
        """Переподключается с актуальными кредами и переподписывается на bundle."""
        auth_token = self._group_state.get("auth_token")
        x_user_id = self._group_state.get("x_user_id")
        if not auth_token or not x_user_id:
            logger.warning("[WS_SESSION] нет кредов для переподключения, пропускаю")
            return
        self._client.update_credentials(auth_token, x_user_id)
        try:
            await self._client.reconnect()
        except Exception as error:
            logger.warning("[WS_SESSION] не удалось переподключиться: %s", error)
            return
        self._generation = new_generation
        await self._subscribe_bundle()
        logger.info("[WS_SESSION] соединение переподключено, bundle переподписан")

    async def _heartbeat_loop(self) -> None:
        """Раз в минуту логирует состояние сессии: соединение, очередь, активность."""
        while not self._stop_event.is_set():
            await asyncio.sleep(WS_Const.WS_SESSION_HEARTBEAT_INTERVAL_SECONDS)
            if self._stop_event.is_set():
                return
            received = self._client.received_messages_count
            sent_ping = self._client.sent_ping_count
            rest_ping = self._rest_ping_count
            logger.info(
                "[WS_SESSION] heartbeat: активно=%s, очередь=%d, получено_за_минуту=%d (всего=%d), "
                "signalr_ping=%d, rest_ping=%d",
                self._client.is_connected,
                self._client.recv_queue.qsize(),
                received - self._last_received,
                received,
                sent_ping - self._last_sent_ping,
                rest_ping - self._last_rest_ping,
            )
            self._last_received = received
            self._last_sent_ping = sent_ping
            self._last_rest_ping = rest_ping

    async def _rest_ping_loop(self) -> None:
        """Периодически пингует REST /Ping с correlation-id."""
        while not self._stop_event.is_set():
            await asyncio.sleep(WS_Const.REST_PING_INTERVAL_SECONDS)
            if self._stop_event.is_set():
                return
            await self._ping_rest()

    async def _ping_rest(self) -> None:
        """Один REST-пинг. Ошибки (5xx/4xx/сеть) не роняют keepalive."""
        stand_host = self._group_state.get("stand_host")
        auth_token = self._group_state.get("auth_token")
        if not stand_host or not auth_token:
            logger.warning("[REST_PING] нет stand_host/auth_token, пропускаю")
            return
        url = f"https://{stand_host}{StandConstants.PING_URL_PATH}"
        headers = {
            HttpConst.X_SECURITY_SIGNATURE_KEY: auth_token,
            HttpConst.X_TN_CORRELATION_ID_KEY: self._correlation_id,
        }
        self._rest_ping_count += 1
        try:
            response = await asyncio.to_thread(requests.post, url, headers=headers, timeout=10)
            if not response.ok:
                logger.warning(
                    "[REST_PING] %s -> %s: %s",
                    StandConstants.PING_URL_PATH,
                    response.status_code,
                    response.text[:200],
                )
            else:
                logger.info("[REST_PING] %s -> %s", StandConstants.PING_URL_PATH, response.status_code)
        except requests.RequestException as error:
            logger.warning("[REST_PING] ошибка запроса %s: %s", StandConstants.PING_URL_PATH, error)
