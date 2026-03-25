from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ColumnsSelection(Enum):
    """Возможные названия столбцов"""

    TIME = 'Time'
    USER = 'User'
    MAIN_PIPELINE = 'MainPipeline'
    TECHNOLOGICAL_SECTION = 'TechnologicalSection'
    TECHNOLOGICAL_OBJECT = 'TechnologicalObject'
    CONTROL_POINT = 'ControlPoint'
    OBJECT = 'Object'
    SIGNAL_NAME = 'SignalName'
    EVENT = 'Event'
    VALUE = 'Value'
    MESSAGE_TYPE = 'MessageType'
    TAG = 'Tag'
    STATUS = 'Status'


class Direction(Enum):
    """Направление прокрутки"""

    PREV = 'PREV'
    NEXT = 'NEXT'
    FIRST = 'FIRST'
    LAST = 'LAST'


@dataclass
class Pagination:
    """Пагинация в запросе"""

    # Запрашиваемое количество элементов на странице
    limit: Optional[int] = 50
    id: Optional[int] = None
    # Направление прокрутки
    direction: Optional[int] = 3
    eventTime: Optional[datetime] = None
    additionalProperties: Optional[str] = None


@dataclass
class Sorting:
    """Сортировка по выбранному столбцу."""

    # Название столбца, по которому происходит сортировка
    sortingParam: Optional[int] = 1
    # Тип сортировки (по возрастанию, по убыванию)
    sortingType: Optional[int] = 2
    additionalProperties: Optional[str] = None


@dataclass
class FilteringObjects:
    tuId: Optional[int] = None
    objectIds: List[int] = field(default_factory=list)
    objectTypes: Optional[int] = 0
    additionalProperties: Optional[str] = None


@dataclass
class Filtering:
    """Фильтрация по выбранному полю"""

    priorities: Optional[int] = 0
    messageTypes: Optional[int] = 0
    userActions: Optional[int] = 0
    objects: Optional[FilteringObjects] = field(default_factory=FilteringObjects)
    additionalProperties: Optional[str] = None


@dataclass
class GetMessagesReply:
    """Ответ на запрос getMessagesRequest"""

    replyStatus: int
    replyContent: Optional[MessagesContent] = None
    replyErrors: Optional[List[dict]] = None


@dataclass
class Search:
    """- Поиск сообщений
    - Осуществляется по полям из БД lds-Journal: details[columnId = x]
    .argument, где x - от 1 до 8
    """

    # Строка, которая ищется в сообщении.
    query: Optional[str] = ''
    additionalProperties: Optional[str] = None


@dataclass
class GetMessagesRequest:
    """Запрос для получения журнала"""

    pagination: Pagination = field(default_factory=Pagination)
    periodTime: Optional[PeriodTime] = None
    sorting: Optional[Sorting] = field(default_factory=Sorting)
    search: Optional[Search] = field(default_factory=Search)
    # Фильтрация по нескольким полям
    filtering: Optional[Filtering] = None
    # Выбор отображаемых колонок
    columnsSelection: List[str] = field(default_factory=lambda: [column.value for column in ColumnsSelection])
    availableMessageIds: List[int] = field(default_factory=list)
    isHistorical: bool = False
    additionalProperties: Optional[str] = None


@dataclass
class MessagesInfo:
    """Информация о сообщении."""

    # - Событие Из БД lds-Journal: details[columnId = 7].text
    event: Optional[str]
    # - Важность сообщения Из БД lds-journal: PriorityByEvent.priority
    priority: Optional[int]
    # - Тег сигнала Из БД lds-Journal: tag
    tag: Optional[str]
    # - Дата и время события в формате ISO: yyyy-mm-dd"T"HH:mm:ss Из БД lds-Journal: eventTime
    time: Optional[datetime]
    # - Наименование КП Из БД lds-Journal: details[columnId = 4].argument
    controlPoint: Optional[str] = None
    # - Логин пользователя Из БД lds-Journal: userName
    login: Optional[str] = None
    # - Наименование МН Из БД lds-Journal: details[columnId = 1].argument
    mainPipeline: Optional[str] = None
    # - Идентификатор сообщения Из БД lds-Journal: details[columnId = 1].id
    messageId: Optional[float] = None
    # - Тип сообщения Из БД lds-journal: MessageTypeByEvent.messageType
    messageType: Optional[str] = None
    # - Наименование объекта Из БД lds-Journal: details[columnId = 5].argument
    object: Optional[str] = None
    # - Наименование сигнала Из БД lds-Journal: details[columnId = 6].argument
    signalName: Optional[str] = None
    # - Статус сообщения Из БД lds-Journal: details[columnId = 9].text
    status: Optional[str] = None
    # - Наименование Площадочного объекта\Линейного участка Из БД lds-Journal: details[columnId = 3].argument
    technologicalObject: Optional[str] = None
    # - Наименование ТУ Из БД lds-Journal: details[columnId = 2].argument
    technologicalSection: Optional[str] = None
    # - ФИО пользователя Из БД lds-Journal: userInitials
    user: Optional[str] = None
    # - Ip-адрес пользователя Из БД lds-Journal: clientInfo
    userIpAddress: Optional[str] = None
    # - Значение сигнала Из БД lds-Journal: details[columnId = 8].text
    value: Optional[str] = None


@dataclass
class PeriodTime:
    """- Период отображения архивного журнала
    - Фильтрация осуществляется по данным из БД lds-Journal eventTime
    """

    # Время конца отображения сообщений в формате ISO: yyyy-mm-dd"T"HH:mm:ss
    end: datetime
    # Время начала отображения сообщений в формате ISO: yyyy-mm-dd"T"HH:mm:ss
    start: datetime
    additionalProperties: Optional[str] = None


@dataclass
class MessagesContent:
    """Ответ на запрос getMessagesRequest"""

    messagesInfo: List[MessagesInfo] = field(default_factory=list)


@dataclass
class GetMessagesRequestMessage:
    """Запрос для получения журнала"""

    payload: GetMessagesRequest
