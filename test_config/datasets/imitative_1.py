"""
Конфигурация тестового набора Imitative_1_tn3_56km_113 (режим остановленной перекачки)

Особенности набора:
- Режим МТ Остановленная перекачка (StationaryStatus.STOPPED)
- Одна утечка на координате 56 км
- Объём утечки 113.6 м³
- Интенсивность утечки 3,6%
- При перестройке путей течения, Режим СОУ может меняться
"""

from constants.enums import (
    AdminTU,
    ConfirmationStatus,
    LdsStatus,
    MeasureConversionRule,
    ReservedType,
    StationaryStatus,
    StoppedPumpingReason,
    TU,
)
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, LeakTestConfig, SmokeSuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Imitative_1_tn3_56km_113"
SUITE_DATA_ID = 20
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# Параметры утечки
LEAK_COORDINATE_METERS = 56000.0
LEAK_VOLUME_M3 = 113.6
ALLOWED_TIME_DIFF_SECONDS = 1440  # 24 минуты
LEAK_START_INTERVAL_SECONDS = 1800  # 30 минут
FLOW_RATE_SETTINGS_THRESHOLD = 7

# ID диагностических участков
LEAK_DIAGNOSTIC_AREA_ID = 2
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.УЗР НПС-3 «Нововеличковская»."

# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_3_PIPE_ID = 1444  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID

# ID линейного участка
LINEAR_PART_ID = 407

CONTROL_POINTS = [
    "ЗА 105-3 - ЗА 129-3",
    "ЗА 180-3 - ЗА 207-3",
]

# ===== Конфигурация набора =====
IMITATIVE_1_CONFIG = SmokeSuiteConfig(
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
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STOPPED,
    expected_report_stationary_status=StationaryStatus.STOPPED.value,
    # ----- Ожидаемые статусы для проверки режимов на ЭФ Диагностика сигналов -----
    controlled_sites_with_segment=CaseData(
        expected_result={
            "exp_tixoreczkaya_novovelichkovskaya": (StationaryStatus.STOPPED, LdsStatus.SERVICEABLE),
            "exp_novovelichkovskaya_krymskaya": (StationaryStatus.STOPPED, LdsStatus.SERVICEABLE),
            "exp_krymskaya_grushovaya": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_bejsug": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_ponura": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_backup_route_kuban": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_afipskij": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
            "exp_npz_ilinskij": (StationaryStatus.STOPPED, LdsStatus.FAULTY),
        }
    ),
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="86", offset=5),
    lds_status_init_in_journal_test=CaseMarkers(test_case_id="228", offset=5),
    stationary_status_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.STOPPED, StoppedPumpingReason.STOPPING_PUMPS),
    ),
    stationary_status_journal_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(
            StationaryStatus.STOPPED.report_text,
            StoppedPumpingReason.STOPPING_PUMPS.report_text,
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
    export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=58),
    export_mt_mode_report_test=CaseMarkers(test_case_id="240", offset=59),
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
        expected_stationary_status=StationaryStatus.STOPPED,
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_leak_status=ConfirmationStatus.CONFIRMED,
        expected_lds_status_in_leaks_report=LdsStatus.SERVICEABLE.value,
        expected_report_stationary_status=StationaryStatus.STOPPED.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=41),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=54),
        # ----- Тест MessageInfo -----
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=46),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="20", offset=54),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="91", offset=54),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="84", offset=54),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="154", offset=54),
        # ----- Тест MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=55),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=55),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=55.5),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="158", offset=56),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=57),
    ),
)
