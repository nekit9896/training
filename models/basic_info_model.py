from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional


@dataclass(frozen=True)
class BasicTUInfo:
    tuId: int
    tuName: str


@dataclass(frozen=True)
class BasicInfoContent:
    tus: List[BasicTUInfo]
    appVersion: str
    appUpdatedAt: Optional[datetime]


@dataclass(frozen=True)
class BasicInfo:
    basicInfo: BasicInfoContent


@dataclass(frozen=True)
class BasicInfoReply:
    replyStatus: int
    replyContent: Optional[BasicInfo]
    replyErrors: Optional[List[dict]] = None
