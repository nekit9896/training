"""
Конфигурация тестового набора Select_17_tn3_75km_417
Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Одна утечка на координате 75 км
- Объём утечки 416 м³
- Интенсивность утечки 13,2%
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_17_tn3_75km_417"
SUITE_DATA_ID = 42
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_COORDINATE_METERS = 75000.0
LEAK_VOLUME_M3 = 416.0
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
LEAK_DIAGNOSTIC_AREA_ID = 2
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ID линейного участка
LINEAR_PART_ID = 407


# ===== Конфигурация набора =====
SELECT_17_CONFIG = SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="59", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="12", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="62", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="61", offset=30),
    lds_status_during_leak_test=CaseMarkers(test_case_id="60", offset=64.5),
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
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="42", offset=61),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="103", offset=63),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="57", offset=63),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="58", offset=66),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="63", offset=66),
    ),
)
