from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


@dataclass
class StopLdsRequest:
    tuId: int
    additionalProperties: Optional[object] = None


@dataclass
class StopLdsReply:
    replyStatus: ReplyStatus
    replyErrors: Optional[List[Dict[str, Any]]] = None


@dataclass
class StopLdsReplyMessage:
    payload: StopLdsReply
