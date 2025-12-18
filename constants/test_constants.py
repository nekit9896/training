"""
Константы для тестирования СОУ.

Содержит статические значения, которые не меняются между наборами данных:
- Типы сигналов
- Суффиксы адресов
- Таймауты
- Колонки журнала
"""


class TestConstants:
    """Общие константы для всех тестов"""

    # --- Типы объектов сигналов ---
    PRESSURE_SENSOR_OBJECT_TYPE: int = 2
    FLOWMETER_OBJECT_TYPE: int = 3

    # --- Типы сигналов ---
    PRESSURE_SIGNAL_TYPE: int = 1
    FLOW_SIGNAL_TYPE: int = 4

    # --- Суффиксы адресов выходных сигналов ---
    ADDRESS_SUFFIX_ACK_LEAK: str = "AckLeak"
    ADDRESS_SUFFIX_LEAK: str = "Leak"
    ADDRESS_SUFFIX_MASK: str = "Mask"
    ADDRESS_SUFFIX_POINT_LEAK: str = "PointLeak"
    ADDRESS_SUFFIX_Q_LEAK: str = "QLeak"
    ADDRESS_SUFFIX_TIME_LEAK: str = "TimeLeak"

    # --- Ожидаемые значения выходных сигналов ---
    OUTPUT_IS_ACK_LEAK: str = "1"
    OUTPUT_IS_LEAK: str = "1"
    OUTPUT_IS_NOT_MASK: str = "0"

    # --- Таймауты ---
    BASIC_MESSAGE_TIMEOUT: float = 5.0

    # --- Для конвертации объема ---
    MASS_KG: int = 3600

    # --- Форматы даты/времени ---
    OUTPUT_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%S"

    # --- Выбор колонок журнала ---
    COLUMN_SELECTION: list = [
        "Time",
        "User",
        "MainPipeline",
        "TechnologicalSection",
        "TechnologicalObject",
        "ControlPoint",
        "Object",
        "SignalName",
        "Event",
        "Value",
        "MessageType",
        "Tag",
        "Status",
    ]
