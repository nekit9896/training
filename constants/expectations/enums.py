from enum import Enum


class TU(Enum):
    YAROSLAVL_MOSCOW = (1, "Ярославль - Москва")
    TIKHORETSK_NOVOROSSIYSK_3 = (3, "Тихорецк-Новороссийск-3")

    def __init__(self, tu_id: int, description: str) -> None:
        self.id = tu_id
        self.description = description

    def __str__(self):
        return f"{self.id} - {self.description}"


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
    CONFIRMED = 1
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


class LdsStatus(Enum):
    FAULTY = 1  # Неисправность
    INITIALIZATION = 2  # Инициализация
    DEGRADATION = 3  # Ухудшенные характеристики
    SERVICEABLE = 4  # Исправность
    