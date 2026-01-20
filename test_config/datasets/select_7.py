"""
Конфигурация тестового набора Select_7_tn3_130km_113 (4 соседних ДУ)
Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Одна утечка на координате 130 км
- Объём утечки 113.6 м³
- 4 соседних диагностических участка (in, out, out_2)
"""

from constants.enums import TU, LdsStatus, StationaryStatus
from test_config.models import (
    DiagnosticAreaStatusConfig,
    LeakTestConfig,
    CaseMarkers,
    SuiteConfig,
)

# ===== Константы набора =====
SUITE_NAME = "Select_7_tn3_130km_113"
SUITE_DATA_ID = 13
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_COORDINATE_METERS = 130000.0
LEAK_VOLUME_M3 = 113.6
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут

# ID диагностических участков (4 соседних ДУ)
LEAK_DIAGNOSTIC_AREA_ID = 3
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 2
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 4
OUT_NEIGHBOR_2_DIAGNOSTIC_AREA_ID = 6  # Дополнительный соседний ДУ

# ID линейного участка
LINEAR_PART_ID = 408


# ===== Конфигурация набора =====
SELECT_7_CONFIG = SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    
    basic_info_test=CaseMarkers(
        test_case_id="1",
        offset=5,
        title="[BasicInfo] Проверка базовой информации СОУ: список ТУ",
        tag="BasicInfo",
    ),
    
    journal_info_test=CaseMarkers(
        test_case_id="2",
        offset=5,
        title="[MessagesInfo] Проверка наличия сообщений в журнале",
        tag="MessagesInfo",
        description=(
            "Проверка сообщения MessagesInfo.\n"
            "Синхронный запрос для проверки наличия сообщений в поле 'messageInfo'"
        ),
    ),
    
    lds_status_initialization_test=CaseMarkers(
        test_case_id="34",
        offset=5,
        title=f"[CommonScheme] Проверка режима работы СОУ: 'Инициализация' на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : ~05:00\n"
            "Ожидаемый режим работы СОУ : Инициализация\n"
        ),
    ),
    
    main_page_info_test=CaseMarkers(
        test_case_id="12",
        offset=7,
        title=f"[MainPageInfo] Проверка установки стационара на данных {SUITE_NAME}",
        tag="MainPageInfo",
        description=(
            f"Проверка сообщения MainPageInfo "
            f"об установке режима Стационар на данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Ожидаемое время установки режима Стационар : ~07:00\n"
        ),
    ),
    
    mask_signal_test=CaseMarkers(
        test_case_id="37",
        offset=8.0,
        title=f"[MaskSignal] проверка маскирования датчиков на данных {SUITE_NAME}",
        tag="MaskSignal",
        description=(
            "Проверка работы маскирования и снятия маскирования через синхронные запросы типа: "
            f"MaskSignalRequest и UnmaskSignalRequest, на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Проверки:\n"
            "Статус-код ответа на синхронный запрос MaskSignalRequest.\n"
            "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
            "Статус-код ответа на синхронный запрос UnmaskSignalRequest.\n"
            "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
            "Примечание: что бы не повлиять на проверки утечек, тест на маскирование выполняется во время инициализации."
        ),
    ),
    
    lds_status_initialization_out_test=CaseMarkers(
        test_case_id="35",
        offset=30,
        title=f"[CommonScheme] Проверка выхода СОУ из Инициализации на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : ~30:00\n"
            "Ожидаемый результат : режим работы СОУ не 'Инициализация'\n"
        ),
    ),
    
    lds_status_during_leak_test=CaseMarkers(
        test_case_id="36",
        offset=59.5,
        title=f"[CommonScheme] Проверка режима работы СОУ во время утечки на данных {SUITE_NAME}",
        tag="CommonScheme",
        description=(
            f"Проверка режима работы СОУ во время утечки в сообщении типа: CommonScheme "
            f"на наборе данных {SUITE_NAME}, \n"
            f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
            "Время проведения проверки : 59:30\n"
            "Примечание: проверка режимов СОУ во время утечки должна выполняться раньше теста на квитирование\n"
            "В рамках данного теста проверяется режим СОУ на ДУ с утечкой и на соседних ДУ"
        ),
    ),
    
    # ===== КОНФИГУРАЦИЯ СТАТУСОВ СОУ ВО ВРЕМЯ УТЕЧКИ =====
    # 4 соседних ДУ (in, out, out_2)
    lds_status_during_leak_config=DiagnosticAreaStatusConfig(
        diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
        expected_lds_status=LdsStatus.INITIALIZATION.value,
        in_neighbor_id=IN_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        in_neighbor_status=LdsStatus.DEGRADATION.value,
        out_neighbor_id=OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        out_neighbor_status=LdsStatus.DEGRADATION.value,
        out_neighbor_2_id=OUT_NEIGHBOR_2_DIAGNOSTIC_AREA_ID,
        out_neighbor_2_status=LdsStatus.DEGRADATION.value,
    ),
    
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
    leak=LeakTestConfig(
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        
        # ----- Ожидаемые статусы -----
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.STATIONARY.value,
        
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(
            test_case_id="13",
            offset=59.0,
            title=f"[AllLeaksInfo] проверка начала утечки с 35 минуты на данных {SUITE_NAME}",
            tag="AllLeaksInfo",
            description=(
                f"Проверка сообщения AllLeaksInfo "
                f"об утечке для набора данных {SUITE_NAME}, \n"
                f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                "Ожидаемое окно возникновения утечки: ~35:00 - 59:00\n"
                "Допустимое время обнаружения 24 минуты с момента начала утечки, "
                f"т к для данных {SUITE_NAME} интенсивность утечки 3,6%.\n"
                "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
            ),
        ),
        
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(
            test_case_id="14",
            offset=59.0,
            title=f"[TuLeaksInfo] проверка начала утечки с 35 минуты на данных {SUITE_NAME}",
            tag="TuLeaksInfo",
            description=(
                f"Проверка сообщения TuLeaksInfo "
                f"об утечке для набора данных {SUITE_NAME}, \n"
                f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                "Ожидаемое окно возникновения утечки: ~35:00 - 59:00\n"
                "Допустимое время обнаружения 24 минуты с момента начала утечки, "
                f"т к для данных {SUITE_NAME} интенсивность утечки 3,6%.\n"
                "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
            ),
        ),
        
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(
            test_case_id="15",
            offset=60.0,
            title=f"[AcknowledgeLeak] проверка квитирования утечки на данных {SUITE_NAME}",
            tag="AcknowledgeLeak",
            description=(
                "Проверка квитирования утечки через синхронный запрос типа: AcknowledgeLeakRequest "
                f"на наборе данных {SUITE_NAME}, \n"
                f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                "Проверки:\n"
                "Статус-код ответа на синхронный запрос AcknowledgeLeakRequest,\n"
                "Отсутствие сообщений об утечках в AllLeaksInfoContent после квитирования"
            ),
        ),
        
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(
            test_case_id="38",
            offset=61.0,
            title=f"[OutputSignalsInfo] Проверка наличия данных об утечке в выходных сигналах на данных {SUITE_NAME}",
            tag="OutputSignals",
            description=(
                "Проверка наличия данных об утечке в выходных сигналах "
                f"на наборе данных {SUITE_NAME}, \n"
                f"на технологическом участке {TECHNOLOGICAL_UNIT.description}\n"
                "Получение списка выходных сигналов для линейного участка, запросом: GetOutputSignalsRequest\n"
                "Получение данных выходных сигналов для линейного участка, по подписке: SubscribeOutputSignalsRequest\n"
                "Примечание: "
                "В mark.offset указано время проверок сообщения выходных сигналов + 1 минута для корректной отработки проверок.\n"
                "Данный тест так же проверяет квитирование, время запуска выставлять после запуска теста на квитирование утечки"
            ),
        ),
    ),
)
