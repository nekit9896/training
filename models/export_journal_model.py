from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from constants.enums import ReplyStatus


class ColumnsSelection(Enum):
    """Список столбцов, которые необходимо отобразить"""

    DATETIME = 'dateTime'
    USER = 'user'
    MAIN_PIPE_LINE = 'mainPipeline'
    TECHNOLOGICAL_SECTION = 'technologicalSection'
    TECHNOLOGICAL_OBJECT = 'technologicalObject'
    CONTROL_POINT = 'controlPoint'
    SIGNAL = 'signal'
    EVENT = 'event'
    VALUE = 'value'
    TAG = 'tag'


class FieldName(Enum):
    """Название поля, по которому происходит фильтрация"""

    MESSAGE_TYPE = 'messageType'
    OBJECT_TYPE = 'objectType'
    PRIORITY = 'priority'


class SortingParam(Enum):
    """Название столбца, по которому происходит сортировка"""

    DATE_TIME = 'dateTime'


class SortingType(Enum):
    """Тип сортировки (по возрастанию, по убыванию)"""

    ASCENDING = 'ascending'
    DESCENDING = 'descending'


@dataclass
class ExportJournalRequest:
    """Метод позволяет сформировать журнал."""

    # Список столбцов, которые необходимо отобразить.
    columnsSelection: Dict[str, Any]
    # Фильтрация
    filtering: Optional[Dict[str, Any]] = None
    # Период времени, за который надо отобразить сообщения. Для архивного журнала.
    periodTime: Optional[Dict[str, Any]] = None
    # Поиск сообщений
    search: Optional[Dict[str, Any]] = None
    # Сортировка по столбцам.
    sorting: Optional[Dict[str, Any]] = None
    # Информация о пользователе, который хочет сформировать файл.
    user: Optional[Dict[str, Any]] = None


@dataclass
class Filtering:
    """Фильтрация по выбранному полю"""

    # Название поля, по которому происходит фильтрация
    fieldName: FieldName
    # Критерии фильтрации.
    filterCriteria: List[Dict[str, Any]]


@dataclass
class PeriodTime:
    """Период отображения архивного журнала."""

    # Время конца отображения сообщений.
    end: Optional[float] = None
    # Время начала отображения сообщений.
    start: Optional[float] = None


@dataclass
class ReadyForUploadingFiles:
    """Сообщение о том, что файл сформирован и готов к скачиванию."""

    replyStatus: ReplyStatus
    content: Optional[UploadingFilesInfoReply] = None
    replyErrors: Optional[ReplyErrors] = None


@dataclass
class ReplyErrors:
    # Причина ошибки
    reason: str
    # Тип ошибки
    errorType: Optional[str] = None
    # Место возникновения ошибки
    location: Optional[str] = None


@dataclass
class Search:
    """Поиск сообщений."""

    # Строка, которая ищется в сообщении.
    query: Optional[str] = None


@dataclass
class Sorting:
    """Сортировка по выбранному столбцу."""

    # Название столбца, по которому происходит сортировка
    sortingParam: SortingParam
    # Тип сортировки (по возрастанию, по убыванию)
    sortingType: SortingType


@dataclass
class UploadingFilesInfo:
    """Информация о сформированном файле."""

    # Наименование файла
    filesName: Optional[str] = None
    # Время формирования файла.
    time: Optional[float] = None


@dataclass
class UploadingFilesInfoReply:
    """Информация передеваемая по сформированным файлам"""

    items: Optional[UploadingFilesInfo] = None


@dataclass
class User:
    """Сортировка по выбранному столбцу."""

    # Идентификатор пользователя
    id: Optional[int] = None
    # ФИО пользователя
    name: Optional[str] = None


@dataclass
class ExportJournalRequestMessage:
    """Метод позволяет сформировать журнал."""

    payload: ExportJournalRequest


@dataclass
class ReadyForUploadingFilesMessage:
    """Сообщение о том, что файл сформирован и готов к скачиванию."""

    payload: ReadyForUploadingFiles
