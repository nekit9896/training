"""

Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Одна утечка на координате 5 км
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_25_tn3_6km_56"
SUITE_DATA_ID = 20
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_COORDINATE_METERS = 5400.0
LEAK_VOLUME_M3 = 57.0
ALLOWED_TIME_DIFF_SECONDS = 1800  # 30 минут
LEAK_START_INTERVAL_SECONDS = 2100  # 40 минут
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 2
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ID линейного участка
LINEAR_PART_ID = 407


# ===== Конфигурация набора =====
SELECT_25_CONFIG = SuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ===== Ожидаемый статус стационара =====
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="86", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="83", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="89", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="89", offset=30),
    lds_status_during_leak_test=CaseMarkers(test_case_id="87", offset=61),
    # ===== КОНФИГУРАЦИЯ СТАТУСОВ СОУ ВО ВРЕМЯ УТЕЧКИ =====
    lds_status_during_leak_config=DiagnosticAreaStatusConfig(
        diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
        expected_lds_status=LdsStatus.INITIALIZATION.value,
        in_neighbor_id=IN_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        in_neighbor_status=LdsStatus.DEGRADATION.value,
        out_neighbor_id=OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        out_neighbor_status=LdsStatus.DEGRADATION.value,
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
        expected_algorithm_type=ReservedType.STATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.STATIONARY.value,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="20", offset=58.0),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="84", offset=58.0),
        # ----- Тест LeakContent -----
        leaks_content_test=CaseMarkers(test_case_id="91", offset=58.0),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="85", offset=60.0),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="90", offset=62.0),
    ),
)