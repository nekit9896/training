from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


@dataclass
class FlowAreas:
    """Результаты работы алгоритма для каждой области течения. Находятся в выходном слое LDS: flowAreas"""

    flowAreas: List[Dict[str, Any]]


@dataclass
class ReplyErrors:
    replyErrors: List[Dict[str, Any]]


@dataclass
class SubscribeBalanceAlgorithmResultsReply:
    """Информация для каждого диагностического участка"""

    replyStatus: ReplyStatus
    replyContent: Optional[FlowAreas] = None
    replyErrors: Optional[ReplyErrors] = None


@dataclass
class SubscribeBalanceAlgorithmResultsRequest:
    """ТУ, для которого нужны результаты работы алгоритма"""

    tuId: TuId


@dataclass
class TuId:
    """Идентификатор ТУ"""

    tuId: int


@dataclass
class SubscribeBalanceAlgorithmResultsReplyMessage:
    """Ответ на запрос subscribeBalanceAlgorithmResultsRequest"""

    payload: SubscribeBalanceAlgorithmResultsReply


@dataclass
class SubscribeBalanceAlgorithmResultsRequestMessage:
    """Подписка на получение результатов работы алгоритма баланса на ТУ"""

    payload: SubscribeBalanceAlgorithmResultsRequest
