from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SignalRejection:
    criteriaNames: int = 0


@dataclass
class SignalState:
    """Данные о состоянии сигнала на схеме."""

    id: int = 0
    quality: Optional[int] = None
    isRejected: bool = False
    isMasked: bool = False
    isImitated: bool = False
    rejection: Optional[Dict[str, Any]] = None
    generationTime: Optional[Any] = None
    receivedTime: Optional[Any] = None
    value: Optional[Any] = None
    imitation: Optional[Any] = None


@dataclass
class ToState:
    id: int = 0
    isInWork: bool = False


@dataclass
class SchemeSignalsStateContent:
    tuId: int = 0
    signalsStates: List[SignalState] = field(default_factory=list)
    toStates: List[ToState] = field(default_factory=list)


@dataclass
class SchemeSignalsStateReply:
    replyStatus: int = 0
    replyErrors: Optional[Any] = None
    replyContent: Optional[SchemeSignalsStateContent] = None
