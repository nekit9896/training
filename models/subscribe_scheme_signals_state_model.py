from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


class RejectionCriteriaName(Enum):
    """
    Наименование критерия, по которому произошла отбраковка.
    """

    QUALITY_REJECTION = 'qualityRejection'
    RANGE_REJECTION = 'rangeRejection'
    EMPTY_REJECTION = 'emptyRejection'
    TIME_REJECTION = 'timeRejection'
    CONSTANT_SIGNAL_REJECTION = 'constantSignalRejection'
    DISCHARGE_REJECTION = 'dischargeRejection'
    SIGMA3_REJECTION = 'sigma3Rejection'
    VTOR_REJECTION = 'VTORRejection'
    NEARBY_REJECTION = 'nearbyRejection'
    DIAGN_INFO_REJECTION = 'diagnInfoRejection'


@dataclass
class ReplyErrors:
    replyErrors: List[Dict[str, Any]]


@dataclass
class SignalsState:
    """Данные о состоянии сигнала."""

    # Идентификатор сигнала.
    id: int
    # Режим имитации.
    imitation: Dict[str, Any]
    # Статус маскирования.
    isMasked: bool
    # Качество передаваемого сигнала.
    quality: int
    # Статус исправности сигнала.
    rejection: Dict[str, Any]
    # Значение сигнала.
    value: str


@dataclass
class SignalsStates:
    """Данные о состоянии сигналов."""

    signalsStates: List[SignalsState]


@dataclass
class SubscribeSchemeSignalsStateReply:
    """Ответ возвращает данные о состоянии сигналов."""

    replyStatus: ReplyStatus
    replyContent: Optional[SubscribeSchemeSignalsStateReplyContent] = None
    replyErrors: Optional[ReplyErrors] = None


@dataclass
class SubscribeSchemeSignalsStateReplyContent:
    """Информация берется из выходного слоя lb"""

    signalsStates: SignalsStates
    toStates: ToStates


@dataclass
class SubscribeSchemeSignalsStateRequest:
    """Запрос передаёт идентификатор схемы."""

    tuId: TuId


@dataclass
class ToState:
    # Идентификатор сигнала.
    id: int
    # Рабочее состояние.
    isInWork: bool


@dataclass
class ToStates:
    """Состояние ТО."""

    toStates: List[ToState]


@dataclass
class TuId:
    """Идентификатор схемы."""

    tuId: int


@dataclass
class SubscribeSchemeSignalsStateReplyMessage:
    """Ответ на запрос subscribeTiEquipmentStateRequest"""

    payload: SubscribeSchemeSignalsStateReply


@dataclass
class SubscribeSchemeSignalsStateRequestMessage:
    """Запрос передаёт идентификатор схемы."""

    payload: SubscribeSchemeSignalsStateRequest
