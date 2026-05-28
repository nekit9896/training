from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

from constants.enums import ExportedDataType


@dataclass
class ReplyErrors:
    reason: str
    errorType: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ExportedDataItem:
    id: int
    name: str
    exportedDataType: ExportedDataType
    start: Optional[datetime] = None
    end: Optional[datetime] = None


@dataclass
class ExportedDataListContent:
    """Контент ответа со списком сформированных файлов."""

    exportedData: List[ExportedDataItem]


@dataclass
class GetExportedDataListRequest:
    """Запрос списка сформированных файлов (выпадающий список на UI)."""

    limit: int


@dataclass
class GetExportedDataListReply:
    """Ответ со списком сформированных файлов."""

    replyStatus: int
    replyContent: Optional[ExportedDataListContent] = None
    replyErrors: Optional[ReplyErrors] = None
