"""
Общие константы для тестов.
"""

# ===== Константы для запросов журнала =====
COLUMN_SELECTION_DEF = [
    'Time',
    'User',
    'MainPipeline',
    'TechnologicalSection',
    'TechnologicalObject',
    'ControlPoint',
    'Object',
    'SignalName',
    'Event',
    'Value',
    'MessageType',
    'Tag',
    'Status',
]

# ===== Типы сигналов и объектов =====
PRESSURE_SENSOR_OBJECT_TYPE = 2
FLOWMETER_OBJECT_TYPE = 3
PRESSURE_SIGNAL_TYPE = 1
FLOW_SIGNAL_TYPE = 4

# ===== Суффиксы адресов выходных сигналов =====
ADDRESS_SUFFIX_ACK_LEAK = "AckLeak"
ADDRESS_SUFFIX_LEAK = "Leak"
ADDRESS_SUFFIX_MASK = "Mask"
ADDRESS_SUFFIX_POINT_LEAK = "PointLeak"
ADDRESS_SUFFIX_Q_LEAK = "QLeak"
ADDRESS_SUFFIX_TIME_LEAK = "TimeLeak"

# ===== Ключи поиска =====
LEAK_LINEAR_PART_ID_KEY = "id"

# ===== Ожидаемые значения выходных сигналов =====
OUTPUT_IS_ACK_LEAK = "1"
OUTPUT_IS_LEAK = "1"
OUTPUT_IS_NOT_MASK = "0"
