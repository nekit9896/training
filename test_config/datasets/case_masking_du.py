"""
Конфигурация тестового набора данных Select_6_with_mask

Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Маскирование и размаскирование ДУ НПС-2 Крымская - НПС Грушовая
- Одна утечка на координате 56 км
- Объём утечки 113.6 м³
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SmokeSuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Case_masking_du"
SUITE_DATA_ID = 126
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_COORDINATE_METERS = 56000.0
LEAK_VOLUME_M3 = 113.6
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут
LEAK_TECHNOLOGICAL_OBJECT = "НПС-5 Тихорецкая - НПС-3 Нововеличковская"
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 2
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ID линейного участка
LINEAR_PART_ID = 409

# Данные при маскировании ДУ
LINEAR_PART_IDENTIFIER_FOR_MASK = 407
MASK_REASON = "Прохождение герметизаторов"
UNMASK_REASON = ""
MASK_ONE_DU = 1
NOT_MASK_DU = 0
TECHNOLOGICAL_SECTION = "Тихорецк-Новороссийск-3"
MASK_DU_EVENT = "Маскирование СОУ"
UNMASK_DU_EVENT = "Снятие маскирования СОУ"
MASK_DU_NAME = "НПС-5 Тихорецкая - НПС-3 Нововеличковская"
MAIN_PIPE_LINE = "МН Тихорецк-Новороссийск-3"

# ===== Конфигурация набора =====
CASE_MASKING_DU_CONFIG = SmokeSuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    technological_section=TECHNOLOGICAL_SECTION,
    mask_reason=MASK_REASON,
    unmask_reason=UNMASK_REASON,
    mask_one_du=MASK_ONE_DU,
    not_mask_du=NOT_MASK_DU,
    linear_part_identifier_for_mask=LINEAR_PART_IDENTIFIER_FOR_MASK,
    mask_du_name=MASK_DU_NAME,
    mask_du_event=MASK_DU_EVENT,
    unmask_du_event=UNMASK_DU_EVENT,
    main_pipe_line=MAIN_PIPE_LINE,
    # ===== Ожидаемый статус стационара =====
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_du_on_mini_scheme_test=CaseMarkers(test_case_id="126", offset=10),
    unmask_du_on_mini_scheme_test=CaseMarkers(test_case_id="173", offset=35),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            leak_diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
            leak_du_expected_lds_status=LdsStatus.INITIALIZATION.value,
            in_neighbors={
                IN_NEIGHBOR_DIAGNOSTIC_AREA_ID: LdsStatus.DEGRADATION.value,
            },
            out_neighbors={
                OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID: LdsStatus.DEGRADATION.value,
            },
        ),
        #     # ----- Параметры утечки -----
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        #     # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        #     # ----- Ожидаемые статусы -----
        expected_algorithm_type=ReservedType.STATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.STATIONARY.value,
        #     # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="4", offset=59),
        #     # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="97", offset=59),
        #     # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="119", offset=59),
        #     # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="5", offset=59),
        #     # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=59.5),
        #     # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        #     # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="33", offset=61),
    ),
)
