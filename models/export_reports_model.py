"""
Модели websocket-сообщений формирования отчётов (фактический протокол с бэка).

ExportReportsCommandRequest  — запрос на формирование
ReportDataExportedNotification — пуш о готовности (заменяет readyForUploadingFiles из старых контрактов)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from uuid import UUID

from constants.enums import ExportStatus, ExportedDataType

EXPORT_REPORTS_COMMAND_REQUEST = "ExportReportsCommandRequest"
REPORT_DATA_EXPORTED_NOTIFICATION = "ReportDataExportedNotification"


@dataclass
class ReplyErrors:
    reason: str
    errorType: Optional[str] = None
    location: Optional[str] = None


@dataclass
class ExportReportsCommandRequest:
    """Запрос на формирование отчёта."""

    tuId: int
    exportedDataTypes: List[ExportedDataType]
    timeOffset: int
    period: Dict[str, Any]


@dataclass
class ReportDataExportedContent:
    id: UUID
    exportStatus: ExportStatus
    errorMessage: Optional[str] = None


@dataclass
class ReportDataExportedNotification:
    replyStatus: int
    replyContent: Optional[ReportDataExportedContent] = None
    replyErrors: Optional[ReplyErrors] = None
