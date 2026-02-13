"""
Конфигурация тестового набора Select_4_tn3_215km_113 (режим остановленной перекачки)

Особенности набора:
- Режим остановленной перекачки (StationaryStatus.STOPPED)
- Одна утечка на координате 215 км
- Объём утечки 113.6 м³
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_4_tn3_215km_113"
SUITE_DATA_ID = 43
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_COORDINATE_METERS = 215000.0
LEAK_VOLUME_M3 = 113.6
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_NAME = "КП 127 - Т-Н-3.«Грушовая».УЗР"
LEAK_DIAGNOSTIC_AREA_ID = 2
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ID линейного участка
LINEAR_PART_ID = 408


# ===== Конфигурация набора =====
SELECT_4_CONFIG = SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STOPPED.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="52", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="44", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="45", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="46", offset=30),
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
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
        # ----- Параметры утечки -----
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_algorithm_type=ReservedType.STOP.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.DEGRADATION.value,
        expected_stationary_status=StationaryStatus.STOPPED.value,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="43", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="102", offset=59),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="48", offset=59),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="50", offset=60),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="51", offset=61),
    ),
)
