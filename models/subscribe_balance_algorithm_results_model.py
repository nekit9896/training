from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from constants.enums import ReplyStatus


@dataclass
class BalanceAlgorithmDiagnosticArea:
    """
    Результаты работы алгоритма баланса для одного диагностического участка
    """

    id: int
    name: str
    debalance: float
    isLeakPossible: bool
    isLeakDetected: bool
    timeToLeakDetection: int
    status: int
    statusReason: int
    timeToInitialize: int


@dataclass
class BalanceAlgorithmFlowArea:
    """
    Результаты работы алгоритма баланса для одной flowArea
    """

    id: str
    isFlowAvailable: bool
    diagnosticAreas: List[BalanceAlgorithmDiagnosticArea]


@dataclass
class BalanceAlgorithmResultsContent:
    """
    Содержимое BalanceAlgorithmResultsContent
    """

    tuId: int
    flowAreas: List[BalanceAlgorithmFlowArea]


@dataclass
class SubscribeBalanceAlgorithmResultsReply:
    """
    DTO ответа на SubscribeBalanceAlgorithmResultsRequest
    """

    replyStatus: ReplyStatus
    replyContent: Optional[BalanceAlgorithmResultsContent] = None
    replyErrors: Optional[object] = None


@dataclass
class SubscribeBalanceAlgorithmResultsRequest:
    """
    DTO запроса SubscribeBalanceAlgorithmResultsRequest
    """

    tuId: int
    additionalProperties: Optional[object] = None


@dataclass
class SubscribeBalanceAlgorithmResultsReplyMessage:
    """
    Обёртка ws-сообщения с ответом BalanceAlgorithmResultsContent
    """

    payload: SubscribeBalanceAlgorithmResultsReply


@dataclass
class SubscribeBalanceAlgorithmResultsRequestMessage:
    """
    Обёртка ws-сообщения с запросом SubscribeBalanceAlgorithmResultsRequest
    """

    payload: SubscribeBalanceAlgorithmResultsRequest
