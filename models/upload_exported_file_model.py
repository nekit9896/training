from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

DOWNLOAD_EXPORTED_DATA_REQUEST = "DownloadExportedDataRequest"


@dataclass
class ReplyErrors:
    reason: str
    errorType: Optional[str] = None
    location: Optional[str] = None


@dataclass
class DownloadExportedDataRequest:
    """Запрос на скачивание сформированного файла"""
    exportedDataId: int
    exportedDataType: str
    timeOffset: int
    additionalProperties: Optional[Dict[str, Any]] = None


@dataclass
class DownloadExportedDataContent:
    """Контент ответа на запрос скачивания"""
    fileChunk: bytes


@dataclass
class DownloadExportedDataReply:
    """Ответ со скачанным контентом сформированного файла"""

    replyStatus: int
    replyContent: Optional[DownloadExportedDataContent] = None
    replyErrors: Optional[ReplyErrors] = None
