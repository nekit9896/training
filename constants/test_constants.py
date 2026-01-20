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

# ===== Параметры утечек =====
MASS_KG = 3600  # Коэффициент массы, нужно умножить чтобы получить объем в м3/час
ALLOWED_VOLUME_DIFF = 0.2  # Относительная погрешность по объему
ALLOWED_DISTANCE_DIFF_METERS = 5000  # Погрешность координаты в метрах
LEAK_START_INTERVAL = 2100  # Интервал от старта имитатора до первого обнаружения утечки (секунды) - 35 минут по умолчанию
LEAK_LOCATION_STATUS = 1

# ===== Параметры выходных сигналов =====
OUTPUT_TEST_DELAY = 120  # Задержка для теста выходных сигналов в секундах
OUTPUT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # Формат времени для парсинга выходных сигналов

# ===== Параметры маскирования =====
IS_MASKED_TRUE = True
IS_MASKED_FALSE = False

# ===== Параметры подтверждения =====
IS_ACKNOWLEDGED_FALSE = False

# ===== Прочие константы =====
BASIC_MESSAGE_TIMEOUT = 5.0  # Таймаут ожидания сообщений в секундах
PRECISION = 3  # Точность округления для координат
