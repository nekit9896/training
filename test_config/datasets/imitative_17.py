"""
Особенности набора:
- Режим МТ стационар, минимальный
- Одна утечка на координате 5 км
- Объём утечки 113 м³
- Интенсивность утечки 3,6%
- Отбор на участке между СИ давления на выходе головной НПС и СИ давления на следующем КП на ЛЧ (на входе первой ЗА ЛЧ)
"""

from constants.enums import TU, LdsStatus, LdsStatusInitialization
from test_config.models_for_tests import (
    CaseData,
    CaseMarkers,
    DiagnosticAreaStatusConfig,
    LeakTestConfig,
    SmokeSuiteConfig,
)

# ===== Константы набора =====
SUITE_NAME = "Imitative_17_tn3_5km_113"
SUITE_DATA_ID = 219
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# Параметры утечки
LEAK_COORDINATE_METERS = 5400.0
LEAK_VOLUME_M3 = 113.0
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут
FLOW_RATE_SETTINGS_THRESHOLD = 17

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 2
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_3_PIPE_ID = 1444  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID
# ID линейного участка
LINEAR_PART_ID = 407

# ===== Конфигурация набора =====
IMITATIVE_17_CONFIG = SmokeSuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="86", offset=5),
    lds_status_init_in_journal_test=CaseMarkers(test_case_id="228", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=6),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            leak_diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
            leak_diagnostic_area_pipe_id=DIAGNOSTIC_AREA_2_PIPE_ID,
            leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
            out_neighbors={
                DIAGNOSTIC_AREA_3_PIPE_ID: LdsStatus.DEGRADATION,
            },
        ),
        # ----- Ожидаемый статус СОУ -----
        lds_status_after_confirming_leak_data=CaseData(
            params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
            expected_result=(
                LdsStatus.INITIALIZATION,
                LdsStatusInitialization.ACCUMULATION_DATA.value,
            ),
        ),
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_lds_status_in_leaks_report=LdsStatus.SERVICEABLE.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=47),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=58),
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=52),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="219", offset=58),
        # ----- Тест LeakContent -----
        leaks_content_test=CaseMarkers(test_case_id="91", offset=58),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="84", offset=58),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="154", offset=58),
        # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=58.5),
        # ----- Тест MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=60),
        lds_status_after_confirming_leak_test=CaseMarkers(test_case_id="201", offset=60),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60.5),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=61),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="158", offset=62),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=63),
        export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=64),
    ),
)
