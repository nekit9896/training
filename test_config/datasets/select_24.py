"""
Конфигурация тестового набора Select_24_tn3_181km_1900
Особенности набора:
- Режим МТ: Нестационарный
- Одна утечка на координате 181 км
- Объём утечки 1900 м³
- Интенсивность утечки 100%
"""

from constants.enums import (
    TU,
    AdminTU,
    ConfirmationStatus,
    LdsStatus,
    LdsStatusInitialization,
    MeasureConversionRule,
    ReservedType,
    StationaryReason,
    StationaryStatus,
)
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import (
    CaseData,
    CaseMarkers,
    DiagnosticAreaStatusConfig,
    LeakTestConfig,
    SmokeSuiteConfig,
)

# ===== Константы набора =====
SUITE_NAME = "Select_24_tn3_181km_1900"
SUITE_DATA_ID = 10
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Данные сообщений
MESSAGE_EVENT_LEAK_COMPLETION = "Утечка завершена"

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# ===== Ожидаемые controlledSiteId для проверки выходных сигналов =====
CONTROLLED_SITE_ID_FIRST = 6012
SEGMENT_ID_FIRST = 6013
CONTROLLED_SITE_ID_SECOND = 6074
SEGMENT_ID_SECOND = 6075
CONTROLLED_SITE_ID_THIRD = 9992054525
SEGMENT_ID_THIRD = 9992054526
CONTROLLED_SITE_ID_FOURTH = 6242
SEGMENT_ID_FOURTH = 6243
CONTROLLED_SITE_ID_FIFTH = 6076
SEGMENT_ID_FIFTH = 6077
CONTROLLED_SITE_ID_SIXTH = 6088
SEGMENT_ID_SIXTH = 6089
CONTROLLED_SITE_ID_SEVENTH = 6244
SEGMENT_ID_SEVENTH = 6245
CONTROLLED_SITE_ID_EIGHTH = 6132
SEGMENT_ID_EIGHTH = 6133

# ===== Параметры утечки =====
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.УЗР НПС-3 «Нововеличковская». - Т-Н-3.НПС-2 «Крымская».УЗР СИКН Т-К"
LEAK_TECHNOLOGICAL_OBJECT = "НПС-3 Нововеличковская - НПС-2 Крымская"
LEAK_DIAGNOSTIC_AREA_ID = 3
LEAK_CONTROL_SITE_ID = 6096
LEAK_LINEAR_PART_ID = 408
LEAK_COORDINATE_METERS = 181000.0
LEAK_VOLUME_M3 = 1900.0
LEAK_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 мин
LEAK_START_INTERVAL_SECONDS = 2040  # 34 мин
LEAK_OUTPUT_DELAY_SECONDS = 360
FLOW_RATE_SETTINGS_THRESHOLD = 30
TECHNOLOGICAL_SECTION = "Тихорецк-Новороссийск-3"
# ID труб для определения ДУ
DIAGNOSTIC_AREA_3_PIPE_ID = 474  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # IN_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID
DIAGNOSTIC_AREA_6_PIPE_ID = 999205440  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID

MAX_PUMPING_M3 = 1900  # Максимальная перекачка

CONTROL_POINTS = [
    "ЗА 105-3 - ЗА 129-3",
    "ЗА 180-3 - ЗА 207-3",
]

# ===== Конфигурация набора =====
SELECT_24_CONFIG = SmokeSuiteConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    technological_section=TECHNOLOGICAL_SECTION,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE_SELECT,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY,
    expected_report_stationary_status=StationaryStatus.STATIONARY.value,
    # ----- Ожидаемые статусы для проверки режимов на ЭФ Диагностика сигналов -----
    controlled_sites_with_segment=CaseData(
        expected_result={
            "exp_tixoreczkaya_novovelichkovskaya": (StationaryStatus.STATIONARY, LdsStatus.SERVICEABLE),
            "exp_novovelichkovskaya_krymskaya": (StationaryStatus.STATIONARY, LdsStatus.SERVICEABLE),
            "exp_krymskaya_grushovaya": (StationaryStatus.STATIONARY, LdsStatus.DEGRADATION),
            "exp_backup_route_bejsug": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_ponura": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_kuban": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_afipskij": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_ilinskij": (StationaryStatus.STOPPED, LdsStatus.DEGRADATION),
        }
    ),
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=1),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    lds_status_init_in_journal_test=CaseMarkers(test_case_id="", offset=5),
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
    diagnostics_of_signals_after_initialization_test=CaseMarkers(test_case_id="210", offset=25),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=94),
    export_mt_mode_report_test=CaseMarkers(test_case_id="240", offset=95),
    # ===== Конфигурации утечки =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            leak_diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
            leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
            neighbors_du_expected_lds_status=LdsStatus.DEGRADATION,
        ),
        # ----- Ожидаемые статусы СОУ -----
        lds_status_after_confirming_leak_data=CaseData(
            params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
            expected_result=(
                LdsStatus.INITIALIZATION,
                LdsStatusInitialization.ACCUMULATION_DATA,
            ),
        ),
        lds_status_after_completed_leak_data=CaseData(
            params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
            expected_result=(
                LdsStatus.INITIALIZATION,
                LdsStatusInitialization.ACCUMULATION_DATA,
            ),
        ),
        # ----- Идентификаторы -----
        diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
        control_site_id=LEAK_CONTROL_SITE_ID,
        linear_part_id=LEAK_LINEAR_PART_ID,
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        # ----- События сообщений -----
        message_event_leak_completion=MESSAGE_EVENT_LEAK_COMPLETION,
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        max_pumping_m3=MAX_PUMPING_M3,
        flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=LEAK_ALLOWED_TIME_DIFF_SECONDS,
        output_test_delay_seconds=LEAK_OUTPUT_DELAY_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.UNSTATIONARY,
        expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW,
        expected_leak_status=ConfirmationStatus.CONFIRMED,
        expected_lds_status_in_leaks_report=LdsStatus.SERVICEABLE.value,
        expected_report_stationary_status=StationaryStatus.STATIONARY.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=32),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=40),
        balance_algorithm_leak_completed_test=CaseMarkers(test_case_id="217", offset=92),
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=38),
        # ----- Тесты AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="134", offset=40),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="136", offset=40),
        # ----- Тесты MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="139", offset=40),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="135", offset=40),
        # ----- Тест CommonScheme -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=40.5),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=41),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=41.5),
        # ----- Тесты MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=42),
        lds_status_after_confirming_leak_test=CaseMarkers(test_case_id="201", offset=42),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="140", offset=42),
        # ----- Тесты на факт завершения утечки -----
        the_leak_is_complete_on_kg_test=CaseMarkers(test_case_id="180", offset=92),
        leak_is_complete_on_main_page_test=CaseMarkers(test_case_id="199", offset=92),
        leak_is_complete_in_output_signals_test=CaseMarkers(test_case_id="180", offset=92),
        complete_tu_leaks_info_content_test=CaseMarkers(test_case_id="180", offset=92),
        completed_leak_info_in_journal_test=CaseMarkers(test_case_id="215", offset=92),
        lds_status_completed_leak_test=CaseMarkers(test_case_id="202", offset=100),
        all_leaks_is_empty_test=CaseMarkers(test_case_id="187", offset=102),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=93),
    ),
)
