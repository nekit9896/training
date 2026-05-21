from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from constants.enums import ReplyStatus


@dataclass
class ExportedFilesInfo:
    """Информация о сформированных файлах."""

    # Наименование сформированного файла
    exportedFilesName: str
    # Дата и время формирования файла
    time: float
    # Идентификатор сформированного файла
    id: Optional[str] = None


@dataclass
class ExportedFilesInfoReply:
    """Информация сформированных файлах"""

    items: Optional[ExportedFilesInfo] = None


@dataclass
class GetExportedFilesListReply:
    """Ответ на запрос getExportedFilesListRequest"""

    replyStatus: ReplyStatus
    content: Optional[ExportedFilesInfoReply] = None
    replyErrors: Optional[ReplyErrors] = None


@dataclass
class GetExportedFilesListRequest:
    """Запрос для получения списка сформированных файлов для экспорта"""

    # Идентификатор ОСТ
    OSTid: Dict[str, Any]


@dataclass
class OSTid:
    """Идентификатор ОСТ"""

    OSTid: int


@dataclass
class ReplyErrors:
    # Причина ошибки
    reason: str
    # Тип ошибки
    errorType: Optional[str] = None
    # Место возникновения ошибки
    location: Optional[str] = None


@dataclass
class GetExportedFilesListReplyMessage:
    """Ответ на запрос getExportedFilesListRequest"""

    payload: GetExportedFilesListReply


@dataclass
class GetExportedFilesListRequestMessage:
    """Запрос для просмотра списка сформированных файлов для экспорта"""

    payload: GetExportedFilesListRequest
