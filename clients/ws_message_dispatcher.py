"""
Маршрутизация входящих ws-сообщений по областям видимости тестов (subscription scope).

Причина появления модуля: ответ на подписку приходит с invocationId (replyStatus 200),
а контент подписки - без invocationId, только с типом контента. На постоянном соединении
подписки прошлых тестов продолжают присылать контент, поэтому сообщения нужно разделять
не по invocationId, а по принадлежности тесту и моменту подписки.

Механизм:
- каждое входящее сообщение получает монотонный номер seq;
- у области видимости теста есть watermark - номер seq на момент последней подписки;
- сообщения с seq <= watermark скоупу не отдаются: контент, прилетевший до подписки
  текущего теста (в том числе от подписок предыдущих тестов), в проверки попасть не может;
- после закрытия скоупа его очереди уничтожаются.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from constants.architecture_constants import PersistentConnectionConstants as PersistConst
from constants.architecture_constants import WebSocketClientConstants as WS_Const
from utils.msgpack_utils.message_filters import is_desired_invocation_id, is_desired_type

logger = logging.getLogger(__name__)

UNKNOWN_MESSAGE_QUEUE_PREFIX: str = "unknown"
SIGNALR_MESSAGE_QUEUE_PREFIX: str = "signalr"

SeqMessage = Tuple[int, Any]


def get_message_queue_key(message: Any) -> str:
    """
    Возвращает ключ очереди для сообщения.

    Invocation (тип 1) несёт тип контента в msg[EVENT_TYPE_INDEX] - именно по нему сценарии
    ищут сообщения. StreamItem и Completion типа контента не имеют, поэтому раскладываются
    по служебным очередям с номером типа SignalR: так streaming-ответы не смешиваются
    с контентом подписок и не теряются при вычитывании по типу.
    """
    if not isinstance(message, list) or not message:
        return f"{UNKNOWN_MESSAGE_QUEUE_PREFIX}:{type(message).__name__}"

    message_type = message[WS_Const.SIGNALR_MESSAGE_TYPE_INDEX]
    is_invocation = message_type == WS_Const.DEFAULT_SIGNALR_MESSAGE_TYPE
    if is_invocation and len(message) > WS_Const.EVENT_TYPE_INDEX:
        content_type = message[WS_Const.EVENT_TYPE_INDEX]
        if isinstance(content_type, str):
            return content_type
    return f"{SIGNALR_MESSAGE_QUEUE_PREFIX}:{message_type}"


@dataclass
class SubscriptionScope:
    """
    Область видимости одного теста на постоянном соединении.

    watermark сдвигается на каждую подписку теста: всё, что пришло раньше, тесту не видно.
    subscriptions хранятся, чтобы после реконнекта отправить подписки текущего теста заново.
    """

    scope_id: str
    start_seq: int
    watermark: int = 0
    queues: Dict[str, asyncio.Queue] = field(default_factory=dict)
    subscriptions: List[Tuple[str, Any]] = field(default_factory=list)
    closed: bool = False

    def __post_init__(self) -> None:
        self.watermark = self.start_seq


class WsMessageDispatcher:
    """
    Раскладывает входящие сообщения по очередям областей видимости.

    Все методы вызываются внутри event loop фонового соединения: очереди принадлежат ему,
    а обращение к asyncio.Queue из чужого потока небезопасно.
    """

    def __init__(self) -> None:
        self._seq: int = 0
        self._scopes: Dict[str, SubscriptionScope] = {}
        self.messages_routed: int = 0
        self.messages_dropped: int = 0

    @property
    def current_seq(self) -> int:
        """Текущий номер seq: используется как watermark в момент подписки."""
        return self._seq

    def open_scope(self, scope_id: str) -> SubscriptionScope:
        """Создаёт область видимости теста; повторный вызов возвращает существующую."""
        existing = self._scopes.get(scope_id)
        if existing is not None:
            return existing
        scope = SubscriptionScope(scope_id=scope_id, start_seq=self._seq)
        self._scopes[scope_id] = scope
        logger.info(f"[DISPATCH] Открыт scope {scope_id} (start_seq={self._seq})")
        return scope

    def close_scope(self, scope_id: str) -> None:
        """Закрывает область видимости и уничтожает её очереди."""
        scope = self._scopes.pop(scope_id, None)
        if scope is None:
            return
        scope.closed = True
        scope.queues.clear()
        logger.info(f"[DISPATCH] Закрыт scope {scope_id}")

    def advance_watermark(self, scope: SubscriptionScope) -> None:
        """
        Сдвигает watermark на текущий seq.

        Вызывается до отправки подписки: сообщения, уже лежащие в потоке от прошлых подписок,
        становятся невидимыми, а ответ и контент новой подписки - видимыми.
        """
        scope.watermark = self._seq

    def register_subscription(self, scope: SubscriptionScope, target: str, args: Any) -> None:
        """Запоминает подписку скоупа для повторной отправки после реконнекта."""
        scope.subscriptions.append((target, args))

    def active_subscriptions(self) -> List[Tuple[str, Any]]:
        """Подписки всех активных скоупов (для восстановления после реконнекта)."""
        subscriptions: List[Tuple[str, Any]] = []
        for scope in self._scopes.values():
            if not scope.closed:
                subscriptions.extend(scope.subscriptions)
        return subscriptions

    def route(self, message: Any) -> None:
        """Раскладывает сообщение по очередям активных скоупов с учётом watermark."""
        self._seq += 1
        seq = self._seq
        key = get_message_queue_key(message)
        is_routed = False
        for scope in list(self._scopes.values()):
            if scope.closed or seq <= scope.watermark:
                continue
            self._put_message(scope, key, seq, message)
            is_routed = True

        if is_routed:
            self.messages_routed += 1
        else:
            # Скоупов нет (пауза между тестами) либо сообщения старше watermark - не копим
            self.messages_dropped += 1

    def _put_message(self, scope: SubscriptionScope, key: str, seq: int, message: Any) -> None:
        """Кладёт сообщение в очередь скоупа, вытесняя самое старое при переполнении."""
        queue = scope.queues.setdefault(key, asyncio.Queue())
        if queue.qsize() >= PersistConst.SCOPE_QUEUE_MAXSIZE:
            # Тест не вычитывает этот тип: вытесняем старое сообщение, чтобы не расти по памяти
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                logger.debug(f"[DISPATCH] Очередь {key} оказалась пустой при вытеснении")
        queue.put_nowait((seq, message))

    async def receive_by_type(self, scope: SubscriptionScope, content_type: str, timeout: float) -> List[Any]:
        """Ждёт сообщение нужного типа контента в очереди скоупа."""
        queue = scope.queues.setdefault(content_type, asyncio.Queue())
        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(f"Timeout при фильтрации сообщений {timeout:.1f} секунд")
            _, message = await asyncio.wait_for(queue.get(), timeout=remaining)
            if isinstance(message, list) and is_desired_type(message, content_type):
                return message

    async def receive_by_invocation_id(self, scope: SubscriptionScope, invocation_id: str, timeout: float) -> List[Any]:
        """
        Ищет сообщение с нужным invocationId среди всех очередей скоупа.

        Ненайденные сообщения возвращаются в свои очереди, поэтому поиск не теряет данные
        (в отличие от чтения из общей очереди, где чужие сообщения отбрасывались).
        """
        deadline = time.monotonic() + timeout
        while True:
            drained = self._drain_with_seq(scope)
            for _, message in drained:
                if isinstance(message, list) and is_desired_invocation_id(message, invocation_id):
                    self._requeue(scope, [(seq, item) for seq, item in drained if item is not message])
                    return message

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise asyncio.TimeoutError(f"Timeout при фильтрации сообщений {timeout:.1f} секунд")
            await asyncio.sleep(PersistConst.RECEIVE_POLL_INTERVAL_S)

    async def drain(self, scope: SubscriptionScope) -> List[Any]:
        """Вычитывает все очереди скоупа, сохраняя порядок поступления (сортировка по seq)."""
        return [message for _, message in self._drain_with_seq(scope)]

    async def clear(self, scope: SubscriptionScope) -> None:
        """Очищает все очереди скоупа (аналог clear_queue разового клиента)."""
        for queue in scope.queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break

    def queue_sizes(self, scope: SubscriptionScope) -> Dict[str, int]:
        """Размеры непустых очередей скоупа для мониторинга."""
        return {key: queue.qsize() for key, queue in scope.queues.items() if queue.qsize()}

    def _drain_with_seq(self, scope: SubscriptionScope) -> List[SeqMessage]:
        """Вычитывает все очереди скоупа и возвращает пары (seq, сообщение) по порядку."""
        drained: List[SeqMessage] = []
        for queue in scope.queues.values():
            while not queue.empty():
                try:
                    drained.append(queue.get_nowait())
                except asyncio.QueueEmpty:
                    break
        drained.sort(key=lambda item: item[0])
        return drained

    def _requeue(self, scope: SubscriptionScope, items: List[SeqMessage]) -> None:
        """Возвращает сообщения обратно в очереди скоупа с сохранением их seq."""
        for seq, message in items:
            self._put_message(scope, get_message_queue_key(message), seq, message)
