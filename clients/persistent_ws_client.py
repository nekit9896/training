"""
Фасад постоянного соединения для тестов.

Сигнатуры методов совпадают с WebSocketClient, поэтому сценарии и хелперы не меняются.
Все операции выполняются в event loop фонового соединения через run_coroutine_threadsafe:
очереди принадлежат тому loop, а прямое обращение к asyncio.Queue из чужого потока
небезопасно (get_nowait будит future чужого loop).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Dict, List, Optional

from constants.architecture_constants import PersistentConnectionConstants as PersistConst
from constants.architecture_constants import WebSocketClientConstants as WS_Const

if TYPE_CHECKING:
    from clients.ws_connection_manager import WsConnectionManager
    from clients.ws_message_dispatcher import SubscriptionScope

logger = logging.getLogger(__name__)


class PersistentWsClient:
    """
    Клиент постоянного соединения, привязанный к области видимости одного теста.

    Область видимости (scope) гарантирует, что в проверки теста попадают только сообщения,
    пришедшие после его собственных подписок: контент подписок предыдущих тестов отсекается
    по watermark, а не по invocationId (контент подписок приходит без invocationId).
    """

    def __init__(self, manager: "WsConnectionManager", scope: "SubscriptionScope") -> None:
        """
        :param manager: владелец постоянного соединения
        :param scope: область видимости текущего теста
        """
        self._manager = manager
        self._scope = scope
        # Флаг совместимости со сценариями: на постоянном соединении фоновый приём сообщений
        # всегда логируется подавленно (иначе log-cli тонет в сотнях строк в минуту),
        # поэтому переключение флага тестом на приём не влияет.
        self.suppress_recv_logging: bool = False

    @property
    def scope_id(self) -> str:
        """Идентификатор области видимости (nodeid теста)."""
        return self._scope.scope_id

    @property
    def invocation_id(self) -> Optional[str]:
        """invocationId последнего вызова: счётчик общий на соединение, тесты идут последовательно."""
        return self._manager.last_invocation_id

    @property
    def connection_id(self) -> Optional[str]:
        """connectionId постоянного соединения из negotiate."""
        return self._manager.connection_id

    async def invoke(self, target: str, args: Any) -> None:
        """Отправляет подписку/вызов; watermark скоупа сдвигается до отправки."""
        await self._call(self._manager.invoke, self._scope, target, args)

    async def invoke_stream(self, target: str, args: Any) -> None:
        """Отправляет streaming-вызов (StreamInvocation)."""
        await self._call(self._manager.invoke_stream, self._scope, target, args)

    async def receive_by_type(self, message_type: str, timeout: float = WS_Const.FILTERING_TIMEOUT) -> List[Any]:
        """Ждёт сообщение скоупа с нужным типом контента."""
        return await self._call(self._manager.dispatcher.receive_by_type, self._scope, message_type, timeout)

    async def receive_by_invocation_id(
        self, invocation_id: str, timeout: float = WS_Const.FILTERING_TIMEOUT
    ) -> List[Any]:
        """Ищет сообщение скоупа по invocationId."""
        return await self._call(
            self._manager.dispatcher.receive_by_invocation_id, self._scope, invocation_id, timeout
        )

    async def reconnect(self) -> None:
        """Инициирует переподключение постоянного соединения с восстановлением подписок."""
        await self._call(self._manager.reconnect_now)

    def clear_queue(self) -> None:
        """Очищает очереди скоупа. Синхронный, как у разового клиента: сценарии вызывают без await."""
        self._call_sync(self._manager.dispatcher.clear, self._scope)

    def drain_messages(self) -> List[Any]:
        """Вычитывает все очереди скоупа без блокирующего ожидания, сохраняя порядок сообщений."""
        return self._call_sync(self._manager.dispatcher.drain, self._scope)

    def queue_sizes(self) -> Dict[str, int]:
        """Размеры непустых очередей скоупа (мониторинг)."""
        return self._manager.dispatcher.queue_sizes(self._scope)

    async def _call(self, coroutine_factory: Callable[..., Coroutine], *args: Any) -> Any:
        """
        Выполняет корутину в loop фонового соединения и ждёт результат в текущем loop.

        Исключения (включая asyncio.TimeoutError) пробрасываются в поток теста как есть,
        поэтому существующая логика ретраев и реконнектов в сценариях продолжает работать.
        """
        future = asyncio.run_coroutine_threadsafe(coroutine_factory(*args), self._manager.loop)
        return await asyncio.wrap_future(future)

    def _call_sync(self, coroutine_factory: Callable[..., Coroutine], *args: Any) -> Any:
        """Синхронный вариант _call для методов, которые сценарии вызывают без await."""
        future = asyncio.run_coroutine_threadsafe(coroutine_factory(*args), self._manager.loop)
        return future.result(timeout=PersistConst.CALL_TIMEOUT_S)
