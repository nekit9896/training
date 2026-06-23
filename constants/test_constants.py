"""
Общие константы для тестов.
"""

from constants.enums import StationaryStatus


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
    ADDRESS_SUFFIX_PUMPING_STATUS = "RegLU"
    ADDRESS_SUFFIX_LDS_STATUS = "RegSOU"

    # ===== Ключи поиска =====
    LEAK_LINEAR_PART_ID_KEY = "id"
    CONTROLLED_SITE_ID_AND_SEGMENT_ID = "controlledSiteId"

    # ===== Ожидаемые значения выходных сигналов =====
    OUTPUT_IS_ACK_LEAK = "1"
    OUTPUT_IS_LEAK = "1"
    OUTPUT_IS_NOT_LEAK = "0"
    OUTPUT_IS_NOT_MASK = "0"
    OUTPUT_IS_MASK = "1"

    MASS_KG = 3600  # Коэффициент массы, нужно умножить, чтобы получить объем в м3/час
    KGS_SM2 = 98066  # Коэффициент давления, нужно умножить, чтобы получить объем в кгс/см2
    ALLOWED_VOLUME_DIFF = 0.3  # Относительная погрешность по объему
    ALLOWED_DISTANCE_DIFF_METERS = 5000  # Погрешность координаты в метрах
    KM_TO_METERS = 1000  # Перевод в метры
    LEAK_START_INTERVAL = 2100  # Интервал от старта имитатора до первого обнаружения утечки - 35 минут по умолчанию
    LEAK_LOCATION_STATUS = 1

    # ===== Параметры выходных сигналов =====
    OUTPUT_TEST_DELAY = 120  # Задержка для теста выходных сигналов в секундах
    OUTPUT_TIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"  # Формат времени для парсинга выходных сигналов

    # ===== Параметры маскирования =====
    IS_MASKED_TRUE = True
    IS_MASKED_FALSE = False

    # ===== Параметры имитации =====
    PRESSURE_IMITATION_RANGE = (1, 40)
    VOLUME_IMITATION_RANGE = (100, 2400)
    GOOD_QUALITY_VAL = 1

    # ===== Константы журнала =====
    JOURNAL_EVENT_MASK = "Установка признака маскирования"
    JOURNAL_EVENT_UNMASK = "Снятие признака маскирования"
    JOURNAL_SIGNAL_PRESSURE = "Значение давления"
    JOURNAL_SIGNAL_FLOW = "Расход"
    JOURNAL_MESSAGE_TYPE_USER_ACTIONS = "Действия пользователя"
    JOURNAL_STATUS_SUCCESS = "Успешно"
    JOURNAL_EXPECTED_MSG_COUNT_PER_SIGNAL = 2
    JOURNAL_MASK_PAGINATION_LIMIT = 10
    JOURNAL_EVENT_POSSIBLE_LEAK = "Возможна утечка"
    JOURNAL_EVENT_DETECTED_LEAK = "Утечка."
    JOURNAL_MESSAGE_TYPE_LEAKS = "Утечки"
    JOURNAL_EVENT_COMPLETED_LEAKS = "Утечка завершена"
    JOURNAL_EXPECTED_MASK_MSG_TOTAL = 4
    JOURNAL_MASK_EXPECTED_EVENTS = {"Установка признака маскирования", "Снятие признака маскирования"}
    JOURNAL_MASK_EXPECTED_SIGNALS = {"Значение давления", "Расход"}
    JOURNAL_PAGINATION_LIMIT = 10
    JOURNAL_PAGINATION_REJECT_LIMIT = 20
    JOURNAL_EVENT_LEAK_ACKNOWLEDGED = "Сообщение об утечке квитировано"
    JOURNAL_EVENT_LDS_INIT_ACCUM_DATA = "СОУ в инициализации (Накопление данных)"
    JOURNAL_EVENT_LDS_INIT_COLD_START = "СОУ в инициализации (Одновременный «холодный» запуск нескольких серверов СОУ)"
    JOURNAL_MESSAGE_TYPE_LDS_STATUS = "Режим работы СОУ"
    JOURNAL_MESSAGE_TYPE_REJECTION = "Отбраковка"
    SEC_PER_MIN = 60

    # ===== Параметры подтверждения =====
    IS_ACKNOWLEDGED_FALSE = False

    # ===== Параметры BalanceAlgorithmResults =====
    BALANCE_ALGORITHM_POLL_INTERVAL = 15  # Интервал опроса подписки в секундах
    BALANCE_ALGORITHM_TOTAL_WAIT = 300  # Общее время опроса в секундах
    DEBALANCE_TOLERANCE = 0.25  # Допустимое отклонение дебаланса от порога 30%

    # ===== Прочие константы =====
    BASIC_MESSAGE_TIMEOUT = 10.0  # Таймаут ожидания сообщений в секундах
    MASK_MESSAGE_TIMEOUT = 180.0  # Таймаут ожидания сообщений в секундах
    PRECISION = 3  # Точность округления для координат
    DIGITS_WITH_DOT_PATTERN = r'\d+(?:\.\d+)?'  # Регулярное выражение для поиска чисел с точкой
    DIAGNOSTIC_AREA_BASE_IDS = [2, 3, 4, 5, 7, 8]  # Список ДУ с isBase = true из конфигурации Тн-3
    REPRESENTATIVE_DIAGNOSTIC_AREA_IDS = [2, 3]  # Список показательных ДУ для определения режима СОУ
    ZONE_INFO: str = "Europe/Moscow"
    SECONDS_PER_HOUR: int = 3600
    CRITERIA_NAMES_FIELD: str = 'criteriaNames'


class ExportReportConstants:
    """Константы для теста формирования отчёта об утечках"""

    # Максимальное ожидание уведомления о готовности отчёта
    NOTIFICATION_TIMEOUT_SECONDS: float = 60.0
    # Максимальное время ожидания появления отчёта в списке после уведомления
    LIST_POLL_TOTAL_WAIT_SECONDS: float = 10.0
    # Интервал между запросами getExportedFilesListRequest
    LIST_POLL_INTERVAL_SECONDS: float = 10.0
    # Таймаут получения ответа на скачивание
    DOWNLOAD_TIMEOUT_SECONDS: float = 60.0

    # ===== Имя файла отчёта =====
    LEAKS_REPORT_NAME_PART: str = "Отчет об утечках"  # подстрока в имени файла/отчёта
    XLSX_EXTENSION: str = ".xlsx"
    # Сигнатура zip-архива, используется для проверки формата файла по содержимому
    ZIP_SIGNATURE: bytes = b'PK\x03\x04'

    # ===== Формат даты/времени в отчёте =====
    REPORT_DATETIME_FORMAT: str = "%d.%m.%Y %H:%M:%S"
    # Регулярное выражение для извлечения двух дат из заголовка
    REPORT_HEADER_PERIOD_PATTERN: str = (
        r'Отчет об утечках с (?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
        r' по (?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
    )
    # Регулярное выражение для извлечения двух дат из названия файла
    REPORT_FILE_NAME_PERIOD_PATTERN: str = (
        r'^Отчет об утечках (?P<tu>.+?) '
        r'(?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r' - '
        r'(?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r'\.xlsx$'
    )

    # Двойная шапка: первая строка - название отчёта с периодом, вторая - названия колонок
    REPORT_TITLE_ROW: int = 1
    REPORT_COLUMN_HEADERS_ROW: int = 2
    REPORT_DATA_FIRST_ROW: int = 3

    # ===== Названия колонок =====
    COL_DATETIME: str = "Дата и время"
    COL_OBJECT: str = "Объект"
    COL_LDS_STATUS: str = "Режим работы СОУ"
    COL_MASK_INFO: str = "Информация о маскировании"
    COL_COORDINATE: str = "Координата"
    COL_LEAK_VOLUME: str = "Объемный расход утечки"
    COL_MT_MODE: str = "Режим работы МТ"

    EXPECTED_COLUMN_HEADERS: list = [
        COL_DATETIME,
        COL_OBJECT,
        COL_LDS_STATUS,
        COL_MASK_INFO,
        COL_COORDINATE,
        COL_LEAK_VOLUME,
        COL_MT_MODE,
    ]

    MASKING_NOT_MASKED_TEXT: str = "СОУ не замаскирована"

    # ===== Маппинг StationaryStatus <-> текст в колонке "Режим работы МТ" =====
    STATIONARY_STATUS_TO_REPORT_TEXT: dict = {
        StationaryStatus.UNSTATIONARY.value: "Нестационарный режим работы МТ",
        StationaryStatus.STATIONARY.value: "Стационарный режим работы МТ",
        StationaryStatus.STOPPED.value: "Режим остановленной перекачки МТ",
    }

    # ===== Прочее =====
    DEFAULT_SHEET_INDEX: int = 0

    SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST: str = "SubscribeReportsDataExportedRequest"
    EXPORT_REPORTS_COMMAND_REQUEST: str = "ExportReportsCommandRequest"
    REPORT_DATA_EXPORTED_NOTIFICATION: str = "ReportDataExportedNotification"
    GET_EXPORTED_DATA_LIST_REQUEST: str = "GetExportedDataListRequest"
    EXPORTED_DATA_LIST_LIMIT: int = 10
    DOWNLOAD_EXPORTED_DATA_REQUEST: str = "DownloadExportedDataRequest"

    # Допустимая погрешность при сравнении границ периода отчёта
    REPORT_PERIOD_TOLERANCE_MINUTES: int = 1
    # Формат даты/времени в имени скачиваемого xlsx-файла
    REPORT_FILE_NAME_DATETIME_FORMAT: str = "%d.%m.%Y %H_%M_%S"


class ExportLdsStatusReportConstants:
    """Константы для теста формирования xlsx-отчёта о режиме работы СОУ"""

    LDS_STATUS_REPORT_NAME_PART: str = "Отчет о режиме работы СОУ"
    SECTION_NAMES: list[str] = [
        "НПС-5 Тихорецкая - НПС-3 Нововеличковская",
        "НПС-3 Нововеличковская - НПС-2 Крымская",
        "НПС-2 Крымская - НПС Грушовая",
    ]
    TOTAL_WORK_DURATION_LABEL: str = "Суммарное время работы:"
    ZERO_DURATION_TEXT: str = "0:00:00"
    TOTAL_DURATION_TOLERANCE_SECONDS: int = 5
    # Число частей времени при split(':') - часы:минуты:секунды (1:02:51) и минуты:секунды (02:51)
    DURATION_PARTS_COUNT_H_MM_SS: int = 3
    DURATION_PARTS_COUNT_MM_SS: int = 2

    REPORT_TITLE_ROW: int = 1
    REPORT_COLUMN_HEADERS_ROW: int = 2
    REPORT_DATA_FIRST_ROW: int = 3

    COL_SECTION: str = "Наименование участка"
    COL_FAULTY: str = "Неисправность"
    COL_DEGRADATION: str = "В ухудшенных характеристиках"
    COL_INITIALIZATION: str = "Инициализация"
    COL_SERVICEABLE: str = "Исправность"

    MODE_DURATION_COLUMNS: list = [
        COL_FAULTY,
        COL_DEGRADATION,
        COL_INITIALIZATION,
        COL_SERVICEABLE,
    ]

    EXPECTED_COLUMN_HEADERS: list = [COL_SECTION, *MODE_DURATION_COLUMNS]

    REPORT_HEADER_PERIOD_PATTERN: str = (
        r'Отчет о режиме работы СОУ с (?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
        r' по (?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
    )
    REPORT_FILE_NAME_PERIOD_PATTERN: str = (
        r'^Отчет о режиме работы СОУ\. (?P<tu>.+?) '
        r'(?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r' - '
        r'(?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r'\.xlsx$'
    )


class ExportMtModeReportConstants:
    """Константы для теста формирования xlsx-отчёта о режиме работы МТ"""

    MT_MODE_REPORT_NAME_PART: str = "Отчет о режиме работы МТ"
    SECTION_NAMES: list[str] = [
        "НПС-5 Тихорецкая - НПС-3 Нововеличковская",
        "НПС-3 Нововеличковская - НПС-2 Крымская",
        "НПС-2 Крымская - НПС Грушовая",
    ]
    TOTAL_WORK_DURATION_LABEL: str = "Суммарное время работы:"
    ZERO_DURATION_TEXT: str = "0:00:00"
    TOTAL_DURATION_TOLERANCE_SECONDS: int = 5
    DURATION_PARTS_COUNT_H_MM_SS: int = 3
    DURATION_PARTS_COUNT_MM_SS: int = 2

    REPORT_TITLE_ROW: int = 1
    REPORT_COLUMN_HEADERS_ROW: int = 2
    REPORT_DATA_FIRST_ROW: int = 3

    COL_SECTION: str = "Наименование участка"
    COL_STOPPED: str = "Остановленный"
    COL_UNSTATIONARY: str = "Нестационарный"
    COL_STATIONARY: str = "Стационарный"

    MODE_DURATION_COLUMNS: list = [
        COL_STOPPED,
        COL_UNSTATIONARY,
        COL_STATIONARY,
    ]

    EXPECTED_COLUMN_HEADERS: list = [COL_SECTION, *MODE_DURATION_COLUMNS]

    STATIONARY_STATUS_TO_COLUMN: dict = {
        StationaryStatus.STOPPED.value: COL_STOPPED,
        StationaryStatus.UNSTATIONARY.value: COL_UNSTATIONARY,
        StationaryStatus.STATIONARY.value: COL_STATIONARY,
    }

    REPORT_HEADER_PERIOD_PATTERN: str = (
        r'Отчет о режиме работы МТ с (?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
        r' по (?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
    )
    REPORT_FILE_NAME_PERIOD_PATTERN: str = (
        r'^Отчет о режиме работы МТ\. (?P<tu>.+?) '
        r'(?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r' - '
        r'(?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r'\.xlsx$'
    )


class ExportRejectedReportConstants:
    """Константы для теста формирования xlsx-отчёта об отбракованных входных данных"""

    REJECTED_REPORT_NAME_PART: str = "Отчет об отбракованных входных данных"
    REJECTED_REPORT_NAME_PART_ALT: str = "Отчёт об отбракованных входных данных"

    REPORT_TITLE_ROW: int = 1
    REPORT_COLUMN_HEADERS_ROW: int = 2
    REPORT_DATA_FIRST_ROW: int = 3

    COL_DATETIME: str = "Дата и время"
    COL_OBJECT: str = "Объект"
    COL_EVENT: str = "Событие"
    COL_VALUE: str = "Значение"
    COL_DURATION: str = "Продолжительность отбраковки"
    COL_TAG: str = "Тег сигнала"

    EXPECTED_COLUMN_HEADERS: list = [
        COL_DATETIME,
        COL_OBJECT,
        COL_EVENT,
        COL_VALUE,
        COL_DURATION,
        COL_TAG,
    ]

    REPORT_HEADER_PERIOD_PATTERN: str = (
        r'[Оо]тч[её]т об отбракованных входных данных с '
        r'(?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
        r' по (?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2})'
    )
    REPORT_FILE_NAME_PERIOD_PATTERN: str = (
        r'^[Оо]тч[её]т об отбракованных входных данных (?P<tu>.+?) '
        r'(?P<period_start>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r' - '
        r'(?P<period_end>\d{2}\.\d{2}\.\d{4} \d{2}_\d{2}_\d{2})'
        r'\.xlsx$'
    )

    TIME_FILTER_TOLERANCE_SECONDS: int = 60

    # Суффикс сигнала в колонке «Объект» отчёта (после последней точки в строке)
    REPORT_SIGNAL_FLOW: str = "Расход"
    REPORT_SIGNAL_PRESSURE: str = "Давление"
    REPORT_SIGNAL_SUFFIX_BY_EXPECTED_NAME: dict = {
        BaseTN3Constants.JOURNAL_SIGNAL_FLOW: REPORT_SIGNAL_FLOW,
        BaseTN3Constants.JOURNAL_SIGNAL_PRESSURE: REPORT_SIGNAL_PRESSURE,
    }

    # Разбор колонки «Объект»: участок трубопровода и суффикс сигнала разделяются последней точкой
    OBJECT_SIGNAL_SEPARATOR: str = "."
    OBJECT_SIGNAL_RSPLIT_MAXSPLIT: int = 1

    REJECTED_REPORT_HEADER_TITLE_PART: str = "отчет об отбракованных входных данных с"
    REJECTED_REPORT_HEADER_TITLE_PART_ALT: str = "отчёт об отбракованных входных данных с"
