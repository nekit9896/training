from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class FreeFlow:
    """Информация о самотёке"""

    freeFlowStartCoordinate: float
    freeFlowStartHeight: float
    freeFlowEndHeight: float


@dataclass
class MaskedLp:
    """Название ЛЧ со статусом СОУ 'Маскирование'"""

    name: str


@dataclass
class LdsStatus:
    numberOfOkControlledSites: int
    numberOfInitializingControlledSites: int
    numberOfFaultyControlledSites: int
    numberOfDegradedControlledSites: int
    numberOfMaskedLps: int
    maskedLps: Optional[List[str]]


@dataclass
class MainPageLeakInfo:
    leakStatus: int
    leakCoordinate: float
    leakVolume: float
    leakLdsStatus: int
    leakPumpingStatus: int
    timeToLeak: Optional[int] = None
    isMasked: bool = False
    leakDetectedAt: Optional[str] = None


@dataclass
class TuInfo:
    tuId: int
    stationaryStatus: int
    ldsStatus: LdsStatus
    freeFlows: Optional[List[FreeFlow]]
    leaksInfo: Optional[List[MainPageLeakInfo]]


@dataclass
class MainPageTuInfo:
    tuId: int
    tuInfo: TuInfo


@dataclass
class SubscribeMainPageInfoReply:
    replyStatus: int
    replyErrors: Optional[List[Dict[str, Any]]] = None
    replyContent: Optional[MainPageTuInfo] = None
