from constants.expectations import enums


class BaseSelectTN3Expected:
    # ----- Enums -----
    CONFIRMATION_STATUS = enums.ConfirmationStatus
    LDS_STATUS = enums.LdsStatus
    STATIONARY_STATUS = enums.StationaryStatus
    REPLY_STATUS = enums.ReplyStatus
    RESERVED_TYPE = enums.ReservedType
    TU = enums.TU
    # ----- BasicInfoExpected -----
    TN3_TU_ID = enums.TU.TIKHORETSK_NOVOROSSIYSK_3.id
    TN3_TU_NAME = enums.TU.TIKHORETSK_NOVOROSSIYSK_3.description
    # ----- LeaksInfoExpected -----
    LDS_STATUS_FAULTY_VAL: int = enums.LdsStatus.FAULTY.value
    LDS_STATUS_INITIALIZATION_VAL: int = enums.LdsStatus.INITIALIZATION.value
    LDS_STATUS_DEGRADATION_VAL: int = enums.LdsStatus.DEGRADATION.value
    LDS_STATUS_SERVICEABLE_VAL: int = enums.LdsStatus.SERVICEABLE.value
    IS_ACKNOWLEDGED_FALSE_VAL: bool = False
    LEAK_LOCATION_STATUS: int = 1  # Нет данных
    STATIONARY_STATUS_STATIONARY_VAL: int = enums.StationaryStatus.STATIONARY.value  # Стационарный режим
    STATIONARY_STATUS_UNSTATIONARY_VAL: int = enums.StationaryStatus.UNSTATIONARY.value  # Нестационарный режим
    MASS_KG: int = 3600  # Коэффициент массы, нужно умножить что бы получить объем в м3/час
    ALLOWED_VOLUME_DIFF: float = 0.2  # Относительная погрешность по объему
    ALLOWED_DISTANCE_DIFF_METERS: int = 5000  # Погрешность координаты
    # ----- OutPutInfoExpected -----
    ADDRESS_SUFFIX_ACK_LEAK: str = "AckLeak"
    ADDRESS_SUFFIX_LEAK: str = "Leak"
    ADDRESS_SUFFIX_MASK: str = "Mask"
    ADDRESS_SUFFIX_POINT_LEAK: str = "PointLeak"
    ADDRESS_SUFFIX_Q_LEAK: str = "QLeak"
    ADDRESS_SUFFIX_TIME_LEAK: str = "TimeLeak"
    LEAK_LINEAR_PART_ID_KEY: str = "id"
    OUTPUT_IS_ACK_LEAK: str = "1"
    OUTPUT_IS_LEAK: str = "1"
    OUTPUT_IS_NOT_MASK: str = "0"
    OUTPUT_TEST_DELAY: int = 120
    OUTPUT_TIME_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"
    # ----- MaskExpected -----
    PRESSURE_SENSOR_OBJECT_TYPE: int = 2
    FLOWMETER_OBJECT_TYPE: int = 3
    PRESSURE_SIGNAL_TYPE: int = 1
    FLOW_SIGNAL_TYPE: int = 4
    IS_MASKED_TRUE_VAL: bool = True
    IS_MASKED_FALSE_VAL: bool = False
    REPLY_STATUS_OK_VAL: int = enums.ReplyStatus.OK.value
    # ----- JournalMessageExpected -----
    COLUMN_SELECTION_DEF: list = [
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
    # ----- OtherConstants -----
    BASIC_MESSAGE_TIMEOUT: float = 5.0
    PRECISION: int = 3
