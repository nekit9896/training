"""
Enums для тестирования СОУ.

Содержит перечисления для:
- Статусов работы СОУ (LdsStatus)
- Режимов работы ТУ (StationaryStatus)
- Статусов подтверждения утечки (ConfirmationStatus)
- Типов событий (ReservedType)
- Статусов ответов API (ReplyStatus)
"""

from enum import Enum


class LdsStatus(Enum):
    """Статусы работы СОУ"""

    FAULTY = 1  # Неисправность
    INITIALIZATION = 2  # Инициализация
    DEGRADATION = 3  # Ухудшенные характеристики
    SERVICEABLE = 4  # Исправность


class StationaryStatus(Enum):
    """Режим работы ТУ"""

    UNSTATIONARY = 1  # Нестационарный режим
    STATIONARY = 2  # Стационарный режим
    STOPPED = 3  # Режим остановленной перекачки


class ConfirmationStatus(Enum):
    """Статус подтверждения утечки"""

    CONFIRMED = 1
    WAITING = 2
    POSSIBLE = 3


class ReservedType(Enum):
    """Тип события (алгоритм обнаружения)"""

    UNSTATIONARY_FLOW = 1


class ReplyStatus(Enum):
    """Статусы ответов API"""

    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    INTERNAL_ERROR = 500
