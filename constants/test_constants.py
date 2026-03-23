"""
Общие константы для тестов.
"""


class BaseTN3Constants:
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

    MASS_KG = 3600  # Коэффициент массы, нужно умножить, чтобы получить объем в м3/час
    ALLOWED_VOLUME_DIFF = 0.3  # Относительная погрешность по объему
    ALLOWED_DISTANCE_DIFF_METERS = 5000  # Погрешность координаты в метрах
    LEAK_START_INTERVAL = 2100  # Интервал от старта имитатора до первого обнаружения утечки - 35 минут по умолчанию
    LEAK_LOCATION_STATUS = 1

    # ===== Параметры выходных сигналов =====
    OUTPUT_TEST_DELAY = 120  # Задержка для теста выходных сигналов в секундах
    OUTPUT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # Формат времени для парсинга выходных сигналов

    # ===== Параметры маскирования =====
    IS_MASKED_TRUE = True
    IS_MASKED_FALSE = False

    # ===== Константы журнала маскирования =====
    JOURNAL_EVENT_MASK = "Установка признака маскирования"
    JOURNAL_EVENT_UNMASK = "Снятие признака маскирования"
    JOURNAL_SIGNAL_PRESSURE = "Значение давления"
    JOURNAL_SIGNAL_FLOW = "Расход"
    JOURNAL_MESSAGE_TYPE_USER_ACTIONS = "Действия пользователя"
    JOURNAL_STATUS_SUCCESS = "Успешно"
    JOURNAL_EXPECTED_MSG_COUNT_PER_SIGNAL = 2
    JOURNAL_MASK_PAGINATION_LIMIT = 10

    # ===== Константы журнала утечек =====
    JOURNAL_EVENT_POSSIBLE_LEAK = "Возможна утечка"
    JOURNAL_MESSAGE_TYPE_LEAKS = "Утечки"
    JOURNAL_LEAKS_PAGINATION_LIMIT = 10

    # ===== Параметры подтверждения =====
    IS_ACKNOWLEDGED_FALSE = False

    # ===== Параметры BalanceAlgorithmResults =====
    BALANCE_ALGORITHM_POLL_INTERVAL = 15  # Интервал опроса подписки в секундах
    BALANCE_ALGORITHM_TOTAL_WAIT = 300  # Общее время опроса в секундах
    DEBALANCE_TOLERANCE = 0.25  # Допустимое отклонение дебаланса от порога 30%

    # ===== Прочие константы =====
    BASIC_MESSAGE_TIMEOUT = 10.0  # Таймаут ожидания сообщений в секундах
    PRECISION = 3  # Точность округления для координат
    KM_TO_METERS = 1000  # Перевод в метры
    DIGITS_WITH_DOT_PATTERN = r'\d+(?:\.\d+)?'  # Регулярное выражение для поиска чисел с точкой
    DIAGNOSTIC_AREA_BASE_IDS = [2, 3, 4, 5, 6, 7, 8]  # Список ДУ с isBase = true из конфигурации Тн-3
    REPRESENTATIVE_DIAGNOSTIC_AREA_IDS = [2, 3]  # Список показательных ДУ для определения режима СОУ
    