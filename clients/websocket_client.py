import asyncio
import logging
import time
from typing import Any, Callable, List, Optional

import msgpack
import websockets

from constants.architecture_constants import \
    WebSocketClientConstants as WS_Const
from utils.msgpack_utils.message_filters import (is_desired_invocation_id,
                                                 is_desired_type)
from utils.msgpack_utils.msgpack_utils import (encode_with_varint_prefix,
                                               parse_message)

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    Асинхронный ws-клиент для api-gateway по протоколу Async Api
    """

    def __init__(
        self,
        host: str,
        access_token: str,
        reconnect_interval: float = WS_Const.DEFAULT_RECONNECT_INTERVAL,
    ):
        self._host = host
        self._access_token = access_token
        self._reconnect_interval = reconnect_interval
        self._ws_url = f"wss://{host.rstrip('/')}{WS_Const.WS_HUBS}"
        self._buffer = b""
        self._next_id = WS_Const.START_INVOCATION_ID

        self._ws: websockets.ClientConnection | None = None
        self.recv_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._recv_task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()
        self._invocation_id: Optional[str] = None

    @property
    def invocation_id(self):
        return self._invocation_id

    def clear_queue(self):
        """
        Очищает очередь путем пересоздания экземпляра класса очереди
        """
        self.recv_queue = asyncio.Queue()

    async def __aenter__(self):
        await self._connect_loop()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        self._stop_event.set()
        if self._ws:
            self._ws.ping_interval = None
            await self._ws.close()
        if self._recv_task:
            await self._recv_task

        # TODO: дергать ручку завершения сессии в LDS-4083

    async def _handshake(self) -> None:
        payload = WS_Const.HANDSHAKE_MESSAGE + WS_Const.RS.decode()
        logger.info(
            f"Отправлен handshake: {payload}",
        )
        await self._ws.send(payload)

        buf = self._buffer
        finish = time.monotonic() + WS_Const.HANDSHAKE_WAITING
        while time.monotonic() < finish:
            chunk = await self._ws.recv()
            logger.info(f"Ответ на handshake: {chunk}")
            buf += chunk.encode() if isinstance(chunk, str) else chunk
            if WS_Const.RS in buf:
                return

        raise TimeoutError(
            "Handshake timeout: не получили сообщение с разделителем RS за указанное время"
        )

    async def _connect_loop(self) -> None:
        """
        Цикл подключения с повторными попытками до наступления stop_event.
        """
        while not self._stop_event.is_set():
            try:
                self.ws_request = f"{self._ws_url}/?access_token={self._access_token}"
                logger.info(
                    f"Попытка подключения по wss: {self._ws_url}/?access_token=..."
                )
                self._ws = await websockets.connect(
                    self.ws_request,
                    ping_interval=WS_Const.PING_INTERVAL,
                    ping_timeout=WS_Const.PING_TIMEOUT,
                    close_timeout=WS_Const.CLOSE_TIMEOUT,
                )
                # Handshake
                await self._handshake()
                # Запускаем приём в фоне
                self._recv_task = asyncio.create_task(self._recv_loop())
                logger.info("Websocket connected")
                return
            except ConnectionError:
                logger.exception(
                    f"Websocket подключение не установлено, повтор подключения через: {self._reconnect_interval}"
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
                logger.info(f"Сырые биты до обработки: {chunk[:100]}")
            except websockets.ConnectionClosed as e:
                logger.warning(f"WebSocket соединение разорвано: {e}")
                return

            result_message = parse_message(chunk)
            logger.info(
                f"Обработанное сообщение от api-gateway: {str(result_message)[:1000]} - размер можно увеличить в "
                f"WebSocketClient в _recv_loop(self)"
            )
            await self.recv_queue.put(result_message)

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
        logger.info(f"Готовится сообщение: {invocation}")
        payload = msgpack.packb(invocation, use_bin_type=True)
        packet = encode_with_varint_prefix(payload)
        logger.info(f"Отправляем сообщение: {packet}")
        await self._ws.send(packet)

    async def receive_by_type(
        self, message_type: str, timeout: float = 5.0
    ) -> List[Any]:
        """
        Фильтрует сообщения по message_type
        """
        try:
            return await self._receive_by(
                filter_func=lambda msg: is_desired_type(msg, message_type),
                timeout=timeout,
            )
        except websockets.WebSocketException:
            raise websockets.WebSocketException(
                f"Ошибка при фильтрации сообщений по {message_type}"
            )

    async def receive_by_invocation_id(
        self, invocation_id: str, timeout: float = 5.0
    ) -> List[Any]:
        """
        Фильтрует сообщения по invocation_id
        """
        try:
            return await self._receive_by(
                filter_func=lambda msg: is_desired_invocation_id(msg, invocation_id),
                timeout=timeout,
            )
        except websockets.WebSocketException:
            raise websockets.WebSocketException(
                "Ошибка при фильтрации сообщений по invocation_id"
            )

    async def _receive_by(
        self, filter_func: Callable[[list], bool], timeout: float
    ) -> List[Any]:
        """
        Ждет и фильтрует сообщение по filter_func
        """
        # 1) Единая точка вычисления дедлайна
        deadline = time.monotonic() + timeout

        while True:
            # 2) Остаток времени до таймаута
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(
                    f"Timeout при фильтрации сообщений {timeout:.1f} секунд"
                )

            try:
                # 3) Получает сообщение
                msg = await asyncio.wait_for(self.recv_queue.get(), timeout=remaining)
            except asyncio.TimeoutError:
                # 4) Явно перехватывает и пробрасывает свой TimeoutError
                raise asyncio.TimeoutError(
                    f"Timeout при фильтрации сообщений {timeout:.1f} секунд"
                )

            # 5) Фильтрация по filter_func
            if isinstance(msg, list) and filter_func(msg):
                return msg
