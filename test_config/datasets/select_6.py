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
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SmokeSuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_6_tn3_56km_113"
SUITE_DATA_ID = 4
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# Параметры утечки
LEAK_COORDINATE_METERS = 56000.0
LEAK_VOLUME_M3 = 113.6
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут
LEAK_TECHNOLOGICAL_OBJECT = "НПС-5 Тихорецкая - НПС-3 Нововеличковская"
FLOW_RATE_SETTINGS_THRESHOLD = 17

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 2
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3

# ID линейного участка
LINEAR_PART_ID = 407

# ===== Значения сигналов для main page signals =====
MAIN_PAGE_SIGNALS = asdict(SignalsInfo(numberOfRejectedSignals=10))

# ===== Конфигурация набора =====
SELECT_6_CONFIG = SmokeSuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
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
    mask_info_in_journal_test=CaseMarkers(test_case_id="", offset=9),
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
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_algorithm_type=ReservedType.STATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.STATIONARY.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="", offset=42),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="", offset=59),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="4", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="97", offset=59),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="119", offset=59),
        possible_leak_in_journal_test=CaseMarkers(test_case_id="", offset=50),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="5", offset=59),
        # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=59.5),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="33", offset=61),
    ),
)
