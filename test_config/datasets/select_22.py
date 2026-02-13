"""
Конфигурация тестового набора Select_22
Особенности набора:
Особенности набора:
- Режим МТ: нестационар
- Одна утечка на координате 75 км
- Объём утечки 375 м³
- Интенсивность утечки 19,7%
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_22_tn3_75km_375"
SUITE_DATA_ID = 121
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# ===== Параметры утечки =====
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
LEAK_DIAGNOSTIC_AREA_ID = 2
LEAK_CONTROL_SITE_ID = 6034
LEAK_LINEAR_PART_ID = 407
LEAK_COORDINATE_METERS = 75000.0
LEAK_VOLUME_M3 = 375.0
LEAK_ALLOWED_TIME_DIFF_SECONDS = 720  # 12 мин
LEAK_START_INTERVAL_SECONDS = 2100  # 35 мин
LEAK_OUTPUT_DELAY_SECONDS = 360

MAX_PUMPING_M3 = 1900  # Максимальная перекачка

# ID диагностических участков для проверки статусов
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ===== Конфигурация набора =====
SELECT_22_CONFIG = SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=1),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    # ===== Конфигурации утечки =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
            expected_lds_status=LdsStatus.INITIALIZATION.value,
            in_neighbors={
                IN_NEIGHBOR_DIAGNOSTIC_AREA_ID: LdsStatus.DEGRADATION.value,
            },
            out_neighbors={
                OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID: LdsStatus.DEGRADATION.value,
            },
        ),
        # ----- Идентификаторы -----
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
        control_site_id=LEAK_CONTROL_SITE_ID,
        linear_part_id=LEAK_LINEAR_PART_ID,
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        max_pumping_m3=MAX_PUMPING_M3,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=LEAK_ALLOWED_TIME_DIFF_SECONDS,
        output_test_delay_seconds=LEAK_OUTPUT_DELAY_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
        expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        # ----- Тесты LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="124", offset=47),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="121", offset=47),
        # ----- Тест TuLeaksInfo  -----
        tu_leaks_info_test=CaseMarkers(test_case_id="19", offset=47),
        # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="122", offset=47),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=48),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="123", offset=49),
    ),
)
