"""
Конфигурация тестового набора Sou_mode_InFlow

Особенности набора:
- Режим стационар 1 час
- Несколько режимов СОУ
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Sou_mode_InFlow"
SUITE_DATA_ID = 106
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Параметры утечки
LEAK_TECHNOLOGICAL_OBJECT = "НПС-3 Нововеличковская - НПС-2 Крымская"
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-3 «Нововеличковская».УЗР вых - Т-Н-3.НПС-2 «Крымская».УЗР вх"
LEAK_COORDINATE_METERS = 181000.0
LEAK_VOLUME_M3 = 189.4
ALLOWED_TIME_DIFF_SECONDS = 900  # 15 минут
LEAK_START_INTERVAL_SECONDS = 3600  # 60 минут


# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 3
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 2
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 4

# ID линейного участка
LINEAR_PART_ID = 408


# ===== Конфигурация набора =====
SOU_MODE_INFLOW = SuiteConfig(
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
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
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
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_lds_status=LdsStatus.SERVICEABLE.value,
        expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
        expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW.value,
        expected_leak_status=ConfirmationStatus.CONFIRMED.value,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="106", offset=61),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="106", offset=61),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="106", offset=61),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="106", offset=61),
        # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="106", offset=62),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="106", offset=63),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="106", offset=64),
    ),
)
