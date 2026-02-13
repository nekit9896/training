"""
Конфигурация тестового набора Select_6_tn3_56km_113

Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Одна утечка на координате 56 км
- Объём утечки 113.6 м³
"""

from dataclasses import asdict

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from models.subscribe_main_page_signals_info_model import SignalsInfo
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_6_tn3_56km_113"
SUITE_DATA_ID = 4
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
LINEAR_PART_ID = 407

# ===== Значения сигналов для main page signals =====
MAIN_PAGE_SIGNALS = asdict(SignalsInfo(numberOfRejectedSignals=10))

# ===== Конфигурация набора =====
SELECT_6_CONFIG = SuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ===== Ожидаемый статус стационара =====
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    expected_main_page_signals=MAIN_PAGE_SIGNALS,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=7),
    main_page_info_signals_test=CaseMarkers(test_case_id="120", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=59.5),
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
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_algorithm_type=ReservedType.STATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.STATIONARY.value,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="4", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="97", offset=59),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="119", offset=59),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="5", offset=59),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="33", offset=61),
    ),
)
