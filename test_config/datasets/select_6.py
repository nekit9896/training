"""
Конфигурация тестового набора Select_6_tn3_56km_113

Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Одна утечка на координате 56 км
- Объём утечки 113.6 м³
"""

from constants.enums import TU, LdsStatus, LdsStatusInitialization, StationaryStatus
from test_config.models_for_tests import (
    CaseData,
    CaseMarkers,
    DiagnosticAreaStatusConfig,
    LeakTestConfig,
    SmokeSuiteConfig,
)

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
LEAK_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.УЗР НПС-3 «Нововеличковская»."

# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_3_PIPE_ID = 1444  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID

# ID линейного участка
LINEAR_PART_ID = 407

# ===== Конфигурация набора =====
SELECT_6_CONFIG = SmokeSuiteConfig(
    # ===== Метаданные =====
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu_name="Тихорецк-Новороссийск-3-Автотест",
    # ----- Ожидаемые статусы для проверки режимов на ЭФ Диагностика сигналов -----
    exp_tixoreczkaya_novovelichkovskaya_reg_lu=StationaryStatus.STATIONARY.value,
    exp_tixoreczkaya_novovelichkovskaya_reg_sou=LdsStatus.SERVICEABLE.value,
    exp_novovelichkovskaya_krymskaya_reg_lu=StationaryStatus.STATIONARY.value,
    exp_novovelichkovskaya_krymskaya_reg_sou=LdsStatus.SERVICEABLE.value,
    exp_krymskaya_grushovaya_reg_lu=StationaryStatus.STATIONARY.value,
    exp_krymskaya_grushovaya_reg_sou=LdsStatus.DEGRADATION.value,
    exp_backup_route_bejsug_reg_lu=StationaryStatus.STOPPED.value,
    exp_backup_route_bejsug_reg_sou=LdsStatus.FAULTY.value,
    exp_backup_route_ponura_reg_lu=StationaryStatus.STOPPED.value,
    exp_backup_route_ponura_reg_sou=LdsStatus.FAULTY.value,
    exp_backup_route_kuban_reg_lu=StationaryStatus.STOPPED.value,
    exp_backup_route_kuban_reg_sou=LdsStatus.FAULTY.value,
    exp_npz_afipskij_reg_lu=StationaryStatus.STOPPED.value,
    exp_npz_afipskij_reg_sou=LdsStatus.FAULTY.value,
    exp_npz_ilinskij_reg_lu=StationaryStatus.STOPPED.value,
    exp_npz_ilinskij_reg_sou=LdsStatus.FAULTY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    lds_status_init_in_journal_test=CaseMarkers(test_case_id="", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=6),
    mask_signal_test=CaseMarkers(test_case_id="45", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    diagnostics_of_signals_after_initialization_test=CaseMarkers(test_case_id="210", offset=25),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_init_out_in_journal_test=CaseMarkers(test_case_id="214", offset=31),
    # ===== КОНФИГУРАЦИЯ УТЕЧКИ =====
    leak=LeakTestConfig(
        # ----- Конфигурация статусов СОУ во время утечки -----
        lds_status_during_leak_config=DiagnosticAreaStatusConfig(
            leak_diagnostic_area_id=LEAK_DIAGNOSTIC_AREA_ID,
            leak_diagnostic_area_pipe_id=DIAGNOSTIC_AREA_2_PIPE_ID,
            leak_du_expected_lds_status=LdsStatus.INITIALIZATION,
            out_neighbors={
                DIAGNOSTIC_AREA_3_PIPE_ID: LdsStatus.DEGRADATION,
            },
        ),
        # ----- Ожидаемый статус СОУ -----
        lds_status_after_confirming_leak_data=CaseData(
            params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
            expected_result=(
                LdsStatus.INITIALIZATION,
                LdsStatusInitialization.ACCUMULATION_DATA,
            ),
        ),
        # ----- Параметры утечки -----
        coordinate_meters=LEAK_COORDINATE_METERS,
        volume_m3=LEAK_VOLUME_M3,
        linear_part_id=LINEAR_PART_ID,
        technological_object=LEAK_TECHNOLOGICAL_OBJECT,
        flow_rate_settings_threshold=FLOW_RATE_SETTINGS_THRESHOLD,
        diagnostic_area_name=LEAK_DIAGNOSTIC_AREA_NAME,
        # ----- Временные интервалы -----
        leak_start_interval_seconds=LEAK_START_INTERVAL_SECONDS,
        allowed_time_diff_seconds=ALLOWED_TIME_DIFF_SECONDS,
        # ----- Ожидаемые статусы -----
        expected_report_stationary_status=StationaryStatus.STATIONARY.value,
        expected_lds_status_in_leaks_report=LdsStatus.SERVICEABLE.value,
        # ----- Тест BalanceAlgorithmResultsContent -----
        balance_algorithm_leak_waiting_test=CaseMarkers(test_case_id="175", offset=42),  # Длительность теста 5 минут
        balance_algorithm_leak_detected_test=CaseMarkers(test_case_id="177", offset=59),
        possible_leak_in_journal_test=CaseMarkers(test_case_id="211", offset=47),
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="4", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="97", offset=59),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="119", offset=59),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="5", offset=59),
        # ----- Тест CommonSchemeContent -----
        # lds_status_during_leak_test=CaseMarkers(test_case_id="31", offset=59.5), TODO включить после LDS_13247
        # ----- Тест MainPageInfoContent -----
        leak_is_confirm_on_main_page_test=CaseMarkers(test_case_id="182", offset=60),
        lds_status_after_confirming_leak_test=CaseMarkers(test_case_id="201", offset=60),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        acknowledge_leak_in_journal_test=CaseMarkers(test_case_id="212", offset=60.5),
        # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="33", offset=61),
        # ----- Тест ExportReports -----
        export_leaks_report_test=CaseMarkers(test_case_id="234", offset=62),
        export_lds_status_report_test=CaseMarkers(test_case_id="235", offset=63),
        export_mt_mode_report_test=CaseMarkers(test_case_id="", offset=64),
    ),
)
