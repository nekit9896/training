"""
Конфигурация тестового набора Select_22_tn3_75km_375
Особенности набора:
- Режим МТ: нестационар
- Одна утечка на координате 75 км
- Объём утечки 375 м³
- Интенсивность утечки 19,7%
"""

from constants.enums import (
    TU,
    AdminTU,
    ConfirmationStatus,
    LdsStatus,
    LdsStatusInitialization,
    MeasureConversionRule,
    ReservedType,
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
SUITE_NAME = "Select_22_tn3_75km_375"
SUITE_DATA_ID = 9
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# ===== Параметры утечки =====
FLOW_RATE_SETTINGS_THRESHOLD = 30
LEAK_DIAGNOSTIC_AREA_ID = 2
LEAK_CONTROL_SITE_ID = 6034
LEAK_LINEAR_PART_ID = 407
LEAK_COORDINATE_METERS = 75000.0
LEAK_VOLUME_M3 = 375.0
LEAK_ALLOWED_TIME_DIFF_SECONDS = 720  # 12 мин
LEAK_START_INTERVAL_SECONDS = 2100  # 35 мин
LEAK_OUTPUT_DELAY_SECONDS = 360
# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_3_PIPE_ID = 1444  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID

MAX_PUMPING_M3 = 1900  # Максимальная перекачка
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.УЗР НПС-3 «Нововеличковская»."

# ===== Конфигурация набора =====
SELECT_22_CONFIG = SmokeSuiteConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
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
    main_page_info_test=CaseMarkers(test_case_id="3", offset=6),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    diagnostics_of_signals_after_initialization_test=CaseMarkers(test_case_id="210", offset=25),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=51),
    export_mt_mode_report_test=CaseMarkers(test_case_id="240", offset=52),
    # ===== Конфигурации утечки =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            leak_diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
            leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
            neighbors_du_expected_lds_status=LdsStatus.DEGRADATION,
        ),
        # ----- Ожидаемый статус СОУ -----
        lds_status_after_confirming_leak_data=CaseData(
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
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
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
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=41),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=47),
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=46),
        # ----- Тесты LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="124", offset=47),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="9", offset=47),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="168", offset=47),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="19", offset=47),
        # ----- Тест CommonSchemeContent -----
        lds_status_during_leak_test=CaseMarkers(test_case_id="122", offset=47),
        # ----- Тест MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=48),
        lds_status_after_confirming_leak_test=CaseMarkers(test_case_id="201", offset=48),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=48.5),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=49),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="123", offset=50),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=50),
    ),
)
