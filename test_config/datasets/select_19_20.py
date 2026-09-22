"""
Конфигурация тестового набора Select_19_20_tn3_75_181km_649 (две утечки)

Особенности набора:
- Две утечки с разными координатами и временными интервалами
- Первая утечка: 75 км, 648.8 м³, интервал 2460 с (~41 мин)
- Вторая утечка: 181 км, 648.8 м³, интервал 3300 с (~55 мин)
- Интенсивность утечки 20,4%
- Допустимое время обнаружения 6 минут
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
SUITE_NAME = "Select_19_20_tn3_75_181km_649"
SUITE_DATA_ID = 7
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3


# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

FLOW_RATE_SETTINGS_THRESHOLD = 17

# ===== Первая утечка =====
LEAK_1_DIAGNOSTIC_AREA_ID = 2
LEAK_1_CONTROL_SITE_ID = 6032
LEAK_1_LINEAR_PART_ID = 407
LEAK_1_COORDINATE_METERS = 75000.0
LEAK_1_VOLUME_M3 = 648.8
LEAK_1_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_1_START_INTERVAL_SECONDS = 2460  # ~41 минута
LEAK_1_OUTPUT_DELAY_SECONDS = 960
LEAK_1_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.УЗР НПС-3 «Нововеличковская»."

# ===== Вторая утечка =====
LEAK_2_DIAGNOSTIC_AREA_ID = 3
LEAK_2_CONTROL_SITE_ID = 6148
LEAK_2_LINEAR_PART_ID = 408
LEAK_2_COORDINATE_METERS = 181000.0
LEAK_2_VOLUME_M3 = 648.8
LEAK_2_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_2_START_INTERVAL_SECONDS = 3300  # ~55 минут
LEAK_2_OUTPUT_DELAY_SECONDS = 150
LEAK_2_DIAGNOSTIC_AREA_NAME = "Т-Н-3.УЗР НПС-3 «Нововеличковская». - Т-Н-3.НПС-2 «Крымская».УЗР СИКН Т-К"

# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с первой утечкой и IN_NEIGHBOR для второй утечки
DIAGNOSTIC_AREA_3_PIPE_ID = 474  # Труба на ДУ со второй утечкой и OUT_NEIGHBOR для первой утечки
DIAGNOSTIC_AREA_6_PIPE_ID = 999205440  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID для второй утечки

CONTROL_POINTS = [
    "ЗА 105-3 - ЗА 129-3",
    "ЗА 180-3 - ЗА 207-3",
]

# ===== Конфигурация набора =====
SELECT_19_20_CONFIG = SmokeSuiteConfig(
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
    diagnostics_of_signals_after_initialization_test=CaseMarkers(test_case_id="210", offset=25),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    # ----- Дополнительный тест на нестационар (специфика двух утечек) -----
    main_page_info_unstationary_test=CaseMarkers(test_case_id="79", offset=40),
    # ----- Тест ExportReports -----
    export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=64),
    # ===== Конфигурации утечек =====
    leaks=[
        # ===== ПЕРВАЯ УТЕЧКА (75 км) =====
        LeakTestConfig(
            # ----- Конфигурация статусов СОУ во время утечки -----
            lds_status_during_leak_config=DiagnosticAreaStatusConfig(
                leak_diagnostic_area_name=LEAK_1_DIAGNOSTIC_AREA_NAME,
                leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
                neighbors_du_expected_lds_status=LdsStatus.DEGRADATION,
            ),
            # ----- Ожидаемый статус СОУ -----
            lds_status_after_confirming_leak_data=CaseData(
                params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
                expected_result=(
                    LdsStatus.INITIALIZATION,
                    LdsStatusInitialization.ACCUMULATION_DATA,
                ),
            ),
            # ----- Идентификаторы -----
            diagnostic_area_id=LEAK_1_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_1_CONTROL_SITE_ID,
            linear_part_id=LEAK_1_LINEAR_PART_ID,
            diagnostic_area_name=LEAK_1_DIAGNOSTIC_AREA_NAME,
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_1_COORDINATE_METERS,
            volume_m3=LEAK_1_VOLUME_M3,
            flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_1_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_1_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_1_OUTPUT_DELAY_SECONDS,
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.SERVICEABLE,
            expected_stationary_status=StationaryStatus.UNSTATIONARY,
            expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW,
            expected_leak_status=ConfirmationStatus.CONFIRMED,
            # ----- Тест BalanceAlgorithmResultsContent (первая утечка) -----
            balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=42),  # Длительность теста 5 мин
            balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=47),
            # ----- Тест LeaksContent (первая утечка) -----
            leaks_content_test=CaseMarkers(test_case_id="72", offset=47),
            # ----- Тест AllLeaksInfo (первая утечка) -----
            all_leaks_info_test=CaseMarkers(test_case_id="7", offset=47),
            # ----- Тест TuLeaksInfo (первая утечка) -----
            tu_leaks_info_test=CaseMarkers(test_case_id="70", offset=47),
            # ----- Тест MessageInfo -----
            leak_info_in_journal=CaseMarkers(test_case_id="147", offset=47),
            # ----- Тест CommonSchemeContent (первая утечка) -----
            lds_status_during_leak_test=CaseMarkers(test_case_id="80", offset=47),
            possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=47),
            lds_status_after_confirming_leak_test=CaseMarkers(test_case_id="201", offset=48),
            # ----- Тест AcknowledgeLeak (первая утечка) -----
            acknowledge_leak_test=CaseMarkers(test_case_id="74", offset=62),
            acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=62.5),
            # ----- Тест OutputSignals (первая утечка) -----
            output_signals_test=CaseMarkers(test_case_id="77", offset=63),
        ),
        # ===== ВТОРАЯ УТЕЧКА (181 км) =====
        LeakTestConfig(
            # ----- Конфигурация статусов СОУ во время утечки -----
            lds_status_during_leak_config=DiagnosticAreaStatusConfig(
                leak_diagnostic_area_name=LEAK_2_DIAGNOSTIC_AREA_NAME,
                leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
                neighbors_du_expected_lds_status=LdsStatus.DEGRADATION,
            ),
            # ----- Идентификаторы -----
            diagnostic_area_id=LEAK_2_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_2_CONTROL_SITE_ID,
            linear_part_id=LEAK_2_LINEAR_PART_ID,
            diagnostic_area_name=LEAK_2_DIAGNOSTIC_AREA_NAME,
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_2_COORDINATE_METERS,
            volume_m3=LEAK_2_VOLUME_M3,
            flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_2_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_2_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_2_OUTPUT_DELAY_SECONDS,
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.DEGRADATION,
            expected_stationary_status=StationaryStatus.UNSTATIONARY,
            expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW,
            expected_leak_status=ConfirmationStatus.CONFIRMED,
            # ----- Тест BalanceAlgorithmResultsContent (вторая утечка) -----
            balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=54),  # Длительность теста 5 мин
            balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=61),
            possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=59),
            # ----- Тест LeaksContent (вторая утечка) -----
            leaks_content_test=CaseMarkers(test_case_id="73", offset=61),
            # ----- Тест AllLeaksInfo (вторая утечка) -----
            all_leaks_info_test=CaseMarkers(test_case_id="7", offset=61),
            # ----- Тест TuLeaksInfo (вторая утечка) -----
            tu_leaks_info_test=CaseMarkers(test_case_id="71", offset=61),
            # ----- Тест MessageInfo -----
            leak_info_in_journal=CaseMarkers(test_case_id="147", offset=61),
            # ----- Тест CommonSchemeContent (вторая утечка) -----
            lds_status_during_leak_test=CaseMarkers(test_case_id="80", offset=61),
            # ----- Тест AcknowledgeLeak (вторая утечка) -----
            acknowledge_leak_test=CaseMarkers(test_case_id="75", offset=62.5),
            acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=63),
            # ----- Тест OutputSignals (вторая утечка) -----
            output_signals_test=CaseMarkers(test_case_id="78", offset=63.5),
        ),
    ],
)
