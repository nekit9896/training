from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from constants.enums import ReplyStatus


@dataclass
class AdminTuInfo:
    """ТУ из ответа GetBasicInfoAdminResponse."""

    tuId: int
    tuName: str
    mnId: int
    mnName: str
    ostId: int
    ostName: str
    configurationVersion: int
    status: int


@dataclass
class AdminBasicInfo:
    tus: List[AdminTuInfo]
    appVersion: str
    appUpdatedAt: Any


@dataclass
class AdminBasicInfoContent:
    basicInfo: AdminBasicInfo


@dataclass
class GetBasicInfoAdminReply:
    replyStatus: ReplyStatus
    replyContent: Optional[AdminBasicInfoContent] = None
    replyErrors: Optional[object] = None


@dataclass
class GetBasicInfoAdminReplyMessage:
    payload: GetBasicInfoAdminReply
