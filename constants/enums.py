from enum import Enum, IntFlag


class TU(Enum):
    YAROSLAVL_MOSCOW = (1, "Ярославль - Москва", "volga.json")
    TIKHORETSK_NOVOROSSIYSK_2 = (2, "Тихорецк-Новороссийск-2", "tn2.json")
    TIKHORETSK_NOVOROSSIYSK_3 = (3, "Тихорецк-Новороссийск-3", "tn3.json")
    RODIONOVSKAYA_TIKHORETSKAYA = (4, "Родионовская–Тихорецкая", "lt3_rt.json")
    TIKHORETSKAYA_GRUSHEVAYA = (5, "Тихорецкая-6-Грушовая", "tn4_t6g.json")

    def __init__(self, tu_id: int, description: str, file_name: str) -> None:
        self.id = tu_id
        self.description = description
        self.file_name = file_name

    def __str__(self):
        return f"{self.id} - {self.description}"

    @classmethod
    def get_file_name_by_id(cls, target_id: int) -> str:
        for item in cls:
            if item.id == target_id:
                return item.file_name
        raise ValueError(f"ТУ с id = {target_id} не найден")


class ReplyStatus(Enum):
    OK = 200
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    REQUEST_TIMEOUT = 408
    CONFLICT = 409
    PRECONDITION_FAILED = 412
    RANGE_NOT_SATISFIABLE = 416
    TOO_MANY_REQUESTS = 429
    INTERNAL_SERVER_ERROR = 500
    NOT_IMPLEMENTED = 501
    SERVICE_UNAVAILABLE = 503
    GATEWAY_TIMEOUT = 504
    UNKNOWN_ERROR = 520


class StationaryStatus(Enum):
    UNSTATIONARY = 1  # Нестационарный режим
    STATIONARY = 2  # Стационарный режим
    STOPPED = 3  # Режим остановленной перекачки


class LeakStatus(Enum):
    CONFIRMED = 1  # Подтверждена
    WAITING = 2
    POSSIBLE = 3


class LeakLocationStatus(Enum):
    NODATA = 1  # нет данных
    LEFT_FROM_PUMP_STATION = 2  # Слева от МНС
    RIGHT_FROM_PUMP_STATION = 3  # Справа от МНС
    INSIDE_PUMP_STATION = 4  # Внутри МНС
    INSIDE_NPS = 5  # Внутри НПС при неработающей/отсутствующей МНС


class FieldName(Enum):
    SECTION_TYPE = "sectionType"
    SIGNAL_TYPE = "signalType"


class FilterCriteriaType(Enum):
    ONE_OF = "oneOf"
    ALL_OF = "allOf"


class FilterCriteriaValue(Enum):
    MASK = "mask"
    MASK_REASON = "maskReason"
    LEAK = "leak"
    LEAK_COORDINATE = "leakCoordinate"
    PUMPING_STATUS = "pumpingStatus"
    FREE_FLOW = "freeFlow"
    ACKNOWLEDGE = "acknowledge"
    LEAK_TIME = "leakTime"
    LEAK_VOLUME = "leakVolume"
    LDS_STATUS = "ldsStatus"
    CONTROLLED_SITES = "controlledSites"
    LINEAR_PARTS = "linearParts"
    SERVER_DOWN = "serverDown"
    TIME_SYNCHRONIZATION_DISABLE = "timeSynchronizationDisable"
    FREE_FLOW_START_COORDINATE = "freeFlowStartCoordinate"


class SortingParam(Enum):
    OBJECT_NAME = "objectName"
    ADDRESS = "address"


class SortingType(Enum):
    ASCENDING = "ascending"
    DESCENDING = "descending"


class Direction(Enum):
    """Направление прокрутки"""

    PREV = 1
    NEXT = 2
    FIRST = 3
    LAST = 4


class LdsStatus(Enum):
    FAULTY = 1  # Неисправность
    INITIALIZATION = 2  # Инициализация
    DEGRADATION = 3  # Ухудшенные характеристики
    SERVICEABLE = 4  # Исправность


class ConfirmationStatus(Enum):
    FAULTY = 0  # Неисправность
    AWAITING = 1  # Предварительная
    NOT_CONFIRMED = 2  # Не подтверждена
    CONFIRMED = 3  # Подтверждена
    CONFIRMED_AND_LEAK_CLOSED = 4  # Завершена


class ReservedType(Enum):
    FAULTY = 0  # Неисправность
    STOP = 1  # Дифференциальный
    STATIONARY_FLOW = 2  # Стационарный
    UNSTATIONARY_FLOW = 3  # Модельный
    BALANCE_IN_NPS = 4  # Баланс внутри НПС
    CHANGED_IN_DECISION_MAKING = 5  # Стационарный + Изменено в АПР
    CREATED_IN_DECISION_MAKING = 6  # Создано в АПР


class MessageType(IntFlag):
    AUTHENTICATION = 1  # Вход в систему
    REJECTION = 1 << 2  # Отбраковка сигналов
    LDS_STATUS = 1 << 3  # Режим работы СОУ
    INPUT_SIGNALS = 1 << 6  # Входные сигналы
    PUMPING_STATUS = 1 << 7  # Режим работы МТ
    MASKING_LDS = 1 << 8  # Маскирование СОУ
    FREE_FLOWS = 1 << 9  # Самотечное течение
    LEAKS = 1 << 10  # Утечка


class MessagePriority(IntFlag):
    LOW = 1  # Прочее
    COMMON = 1 << 1  # Информационное
    MEDIUM = 1 << 2  # Значительное
    HIGH = 1 << 3  # Важное
    VERY_HIGH = 1 << 4  # Особой важности


class DegradationLdsStatusReasons(IntFlag):
    LEAK_ON_ADJACENT_DIAGNOSTIC_AREAS = 1 << 0  # Возникновение утечки на соседнем диагностическом участке
    ADDITIVE_INJECTORS_OPERATION = 1 << 1  # Наличие ПТП
    PIG_SENSOR_PASSAGE = 1 << 2  # Наличие СОД
    TRIGGERING_EMERGENCY_RESET = 1 << 3  # Срабатывание аварийного сброса
    STARTING_PUMPING_OUT_PUMPS = 1 << 4  # Работа насосов откачки
    EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS = 1 << 5  # Расстояние между СИ давления более 50 км
    FAULTY_PRESSURE_SENSORS_AT_PUMP_STATION_NODES = 1 << 6  # Отказ СИ давления на входе/выходе НПС
    REJECTION_TEMPERATURE_SENSOR = 1 << 7  # Отказ СИ температуры
    REJECTION_VISCOSITY_SENSOR = 1 << 8  # Отказ СИ вязкости
    REJECTION_DENSITY_SENSOR = 1 << 9  # Отказ СИ плотности
    GRAVITY_SECTION_IN_PUMPING_MODE = 1 << 10  # Наличие самотечного участка/участка с неполным сечением
    ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER = 1 << 11  # Менее 4 исправных СИ давления на разных КП ЛЧ и НПС
    EXCEEDING_DISTANCE_BETWEEN_FLOW_METERS = 1 << 12  # Расстояние между СИ расхода на пути перекачки более 200 км
    GRAVITY_SECTION_IN_STOPPED_PUMPING_MODE = 1 << 13  # Наличие самотечного участка в режиме остановленной перекачки


class FaultyLdsStatusReasons(IntFlag):
    NO_DATA_SOURCE_CONNECTION = 1 << 0  # Отсутствует связь серверного оборудования СОУ с источником «сырых» данны
    ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER = 1 << 1  # Менее 4 КП с достоверными СИ давления
    ABSENCE_MIN_FLOW_METERS_REQUIRED_NUMBER = 1 << 2  # Недостоверность граничного СИ расхода


class InitializationLdsStatusReasons(IntFlag):
    ACCUMULATION_DATA = 1 << 0  # Накопление данных
    EXITING_FAULTY_MODE = 1 << 1  # Выход СОУ из режима «Неисправна»
    COLD_START_OF_SERVERS = 1 << 2  # Одновременный «холодный» запуск нескольких серверов СОУ
    SWITCHING_SHUT_OFF_IN_STOPPED_PUMPING_MODE = 1 << 3  # Переключение запорной арматуры
    USER_ACTION = 1 << 4  # По команде пользователя
