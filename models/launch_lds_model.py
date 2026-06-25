from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


@dataclass
class LaunchLdsRequest:
    tuId: int
    additionalProperties: Optional[object] = None


@dataclass
class LaunchLdsReply:
    replyStatus: ReplyStatus
    replyErrors: Optional[List[Dict[str, Any]]] = None


@dataclass
class LaunchLdsReplyMessage:
    payload: LaunchLdsReply
