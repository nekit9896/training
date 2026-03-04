from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


@dataclass
class MaskInfoObject:
    """Параметры маскирования для одного линейного участка."""

    linearPartId: int
    reason: str
    additionalProperties: Optional[object] = None


@dataclass
class MaskLdsRequest:
    """Запрос MaskLdsRequest на маскирование выходных сигналов СОУ."""

    tuId: int
    maskInfo: List[MaskInfoObject]
    additionalProperties: Optional[object] = None


@dataclass
class MaskLdsCommandReply:
    """Ответ на запрос MaskLdsRequest."""

    replyStatus: ReplyStatus
    replyErrors: Optional[List[Dict[str, Any]]] = None


@dataclass
class MaskLdsCommandReplyMessage:
    """Обёртка ws-сообщения с ответом MaskLdsRequest."""

    payload: MaskLdsCommandReply


@dataclass
class MaskLdsCommandRequestMessage:
    """Обёртка ws-сообщения с запросом MaskLdsRequest."""

    payload: MaskLdsRequest
