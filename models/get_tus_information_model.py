from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

from constants.enums import ReplyStatus


@dataclass
class TuInformation:
    tuId: int
    launchedBy: Optional[str]
    launchedAt: Optional[Any]
    actualConfigurationExists: bool


@dataclass
class TusInformationContent:
    tusInfo: List[TuInformation]


@dataclass
class GetTusInformationRequest:
    tuIds: List[int]
    additionalProperties: Optional[object] = None


@dataclass
class GetTusInformationReply:
    replyStatus: ReplyStatus
    replyContent: Optional[TusInformationContent] = None
    replyErrors: Optional[object] = None


@dataclass
class GetTusInformationReplyMessage:
    payload: GetTusInformationReply
