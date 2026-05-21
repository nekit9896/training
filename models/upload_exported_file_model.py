from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from constants.enums import ReplyStatus


@dataclass
class File:
    """Информация о файле"""

    # Идентификатор файла
    id: Optional[int] = None
    # Наименование файла
    name: Optional[str] = None


@dataclass
class ReplyErrors:
    # Причина ошибки
    reason: str
    # Тип ошибки
    errorType: Optional[str] = None
    # Место возникновения ошибки
    location: Optional[str] = None


@dataclass
class UploadExportedFileReply:
    """Ответ на запрос uploadExportedFileRequest"""

    replyStatus: ReplyStatus
    replyErrors: Optional[ReplyErrors] = None


@dataclass
class UploadExportedFileRequest:
    """Метод позволяет скачать (выгрузить) сформированный файл."""

    # Информация о файле
    file: Dict[str, Any]


@dataclass
class UploadExportedFileReplyMessage:
    """Ответ на запрос uploadExportedFileRequest"""

    payload: UploadExportedFileReply


@dataclass
class UploadExportedFileRequestMessage:
    """Запрос позволяет скачать (выгрузить) сформированный файл."""

    payload: UploadExportedFileRequest
