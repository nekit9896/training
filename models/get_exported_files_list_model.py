from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

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
class ExportedFilesListContent:
    """Контент ответа со списком сформированных файлов"""

    exportedData: List[ExportedDataItem]


@dataclass
class GetExportedFilesListRequest:
    tuId: int
    additionalProperties: Optional[Dict[str, Any]] = None


@dataclass
class GetExportedFilesListReply:
    """Ответ со списком сформированных файлов"""
    replyStatus: int
    replyContent: Optional[ExportedFilesListContent] = None
    replyErrors: Optional[ReplyErrors] = None
