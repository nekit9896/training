"""
Конфигурация тестового набора Real_70_tn3_216km_56 (режим остановленной перекачки)

Особенности набора:
- Режим МТ стационар
- Режим МТ Остановленная перекачка (StationaryStatus.STOPPED) на участке, где ожидаем утечку
- Одна утечка на координате 216 км
- Объём утечки 56,8 м³
- Интенсивность утечки 1,8%
- Запускать с dataAbsence false в конфигурации
"""

from constants.enums import (
    TU,
    AdminTU,
    ConfirmationStatus,
    LdsStatus,
    MeasureConversionRule,
    ReservedType,
    StationaryReason,
    StationaryStatus,
)
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, LeakTestConfig, SmokeSuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Real_70_tn3_216km_56"
SUITE_DATA_ID = 13
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# Параметры утечки
LEAK_COORDINATE_METERS = 216000
LEAK_VOLUME_M3 = 56
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 2100  # 35 минут
FLOW_RATE_SETTINGS_THRESHOLD = 7

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 3
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.УЗР НПС-3 «Нововеличковская». - Т-Н-3.НПС-2 «Крымская».УЗР СИКН Т-К"

# ID линейного участка
LINEAR_PART_ID = 408

CONTROL_POINTS = [
    "ЗА 105-3 - ЗА 129-3",
    "ЗА 180-3 - ЗА 207-3",
]

# ===== Конфигурация набора =====
REAL_70_CONFIG = SmokeSuiteConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    measure_conversion_rules=MeasureConversionRule.MPA_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY,
    expected_report_stationary_status=StationaryStatus.STATIONARY.value,
    # ----- Ожидаемые статусы для проверки режимов на ЭФ Диагностика сигналов -----
    controlled_sites_with_segment=CaseData(
        expected_result={
            "exp_tixoreczkaya_novovelichkovskaya": (StationaryStatus.STATIONARY, LdsStatus.SERVICEABLE),
            "exp_novovelichkovskaya_krymskaya": (StationaryStatus.STATIONARY, LdsStatus.SERVICEABLE),
            "exp_krymskaya_grushovaya": (StationaryStatus.STOPPED, LdsStatus.DEGRADATION),
            "exp_backup_route_bejsug": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_ponura": (StationaryStatus.STATIONARY, LdsStatus.SERVICEABLE),
            "exp_backup_route_kuban": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_afipskij": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_ilinskij": (StationaryStatus.STATIONARY, LdsStatus.DEGRADATION),
        }
    ),
    # ===== БАЗОВЫЕ ТЕСТЫ ==
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="86", offset=5),
    lds_status_init_in_journal_test=CaseMarkers(test_case_id="228", offset=5),
    stationary_status_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.STATIONARY, StationaryReason.PRESSURE_AND_FLOW_MOVING_AVERAGES_MEET_CRITERIA),
    ),
    stationary_status_journal_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(
            StationaryStatus.STATIONARY.report_text,
            StationaryReason.PRESSURE_AND_FLOW_MOVING_AVERAGES_MEET_CRITERIA.report_text,
        ),
    ),
    stationary_status_common_scheme_test=CaseMarkers(test_case_id="42", offset=6),
    stationary_status_main_page_info_test=CaseMarkers(test_case_id="3", offset=6),
    stationary_status_in_output_signals_test=CaseMarkers(test_case_id="41", offset=6),
    stationary_status_journal_test=CaseMarkers(test_case_id="43", offset=6),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    # diagnostics_of_signals_after_initialization_test=CaseMarkers(test_case_id="210", offset=25), TODO решить LDS-14255
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=63),
    export_mt_mode_report_test=CaseMarkers(test_case_id="240", offset=64),
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
    leak=LeakTestConfig(
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
        expected_algorithm_type=ReservedType.STOP,
        expected_leak_status=ConfirmationStatus.CONFIRMED,
        expected_lds_status=LdsStatus.DEGRADATION,
        expected_stationary_status=StationaryStatus.STOPPED,
        expected_lds_status_in_leaks_report=LdsStatus.DEGRADATION.value,
        expected_report_stationary_status=StationaryStatus.STOPPED.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=42),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=59),
        # ----- Тест MessageInfo -----
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=47),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="13", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="91", offset=59),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="84", offset=59),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="154", offset=59),
        # ----- Тест MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=60),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=60.5),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="158", offset=61),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=62),
    ),
)
