"""
Конфигурация тестового набора данных Select_6_with_mask

Особенности набора:
- Режим стационара (StationaryStatus.STATIONARY)
- Маскирование и размаскирование ДУ НПС-2 Крымская - НПС Грушовая
- Маскирование и размаскирование датчиков
- Имитация и снятие имитации датчиков
- Одна утечка на координате 56 км
- Объём утечки 113.6 м³
"""

from dataclasses import asdict
from random import randint

from constants.enums import (
    TU,
    AdminTU,
    ConfirmationStatus,
    LdsStatus,
    MeasureConversionRule,
    ReservedType,
    StationaryStatus,
)
from constants.test_constants import BaseTN3Constants as TestConst
from models.subscribe_main_page_signals_info_model import SignalsInfo
from test_config.models_for_tests import CaseData, CaseMarkers, LeakTestConfig, SmokeSuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Case_masking_du"
SUITE_DATA_ID = 15
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
# ID труб для определения ДУ
DIAGNOSTIC_AREA_2_PIPE_ID = 1463  # Труба на ДУ с утечкой
DIAGNOSTIC_AREA_3_PIPE_ID = 1444  # OUT_NEIGHBOR_DIAGNOSTIC_AREA_PIPE_ID

# ID линейного участка
LINEAR_PART_ID = 407

# Данные при маскировании ДУ
LINEAR_PART_IDENTIFIER_FOR_MASK = 407
MASK_REASON = "Прохождение герметизаторов"
UNMASK_REASON = ""
MASK_ONE_DU = 1
NOT_MASK_DU = 0
TECHNOLOGICAL_SECTION = "Тихорецк-Новороссийск-3"
MASK_DU_EVENT = "Маскирование СОУ"
UNMASK_DU_EVENT = "Снятие маскирования СОУ"
MASK_DU_NAME = "НПС-5 Тихорецкая - НПС-3 Нововеличковская"
MAIN_PIPE_LINE = "МН Тихорецк-Новороссийск-3"

# ===== Значения сигналов для main page signals =====
MAIN_PAGE_SIGNALS = asdict(SignalsInfo())
SUCCESSFUL_STATUS = TestConst.JOURNAL_STATUS_SUCCESS
IMITATION_EVENT = TestConst.JOURNAL_EVENT_IMITATE
UNIMITATION_EVENT = TestConst.JOURNAL_EVENT_UNIMITATE

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# ===== Данные для имитации и маскирования датчиков =====
PRESSURE_SENSOR_ADDRESS = TestConst.PRESSURE_SENSOR_ADDRESS
FLOWMETER_ADDRESS = TestConst.FLOWMETER_ADDRESS
PRESSURE_SENSOR_VAL = randint(*TestConst.PRESSURE_IMITATION_RANGE) * TestConst.KGS_SM2
FLOWMETER_VAL = randint(*TestConst.VOLUME_IMITATION_RANGE) / TestConst.MASS_KG
SIGNAL_QUALITY_GOOD_VAL = TestConst.GOOD_QUALITY_VAL


# ===== Конфигурация набора =====
CASE_MASKING_DU_CONFIG = SmokeSuiteConfig(
    # ===== Метаданные =====
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    technological_section=TECHNOLOGICAL_SECTION,
    main_pipeline=MAIN_PIPELINE,
    mask_reason=MASK_REASON,
    unmask_reason=UNMASK_REASON,
    mask_one_du=MASK_ONE_DU,
    not_mask_du=NOT_MASK_DU,
    linear_part_identifier_for_mask=LINEAR_PART_IDENTIFIER_FOR_MASK,
    mask_du_name=MASK_DU_NAME,
    mask_du_event=MASK_DU_EVENT,
    unmask_du_event=UNMASK_DU_EVENT,
    main_pipe_line=MAIN_PIPE_LINE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY,
    # ----- Данные для проверки имитации -----
    imitate_flowmeter_signal_test_data=CaseData(
        params={"sensor_address": FLOWMETER_ADDRESS},
        expected_result=(FLOWMETER_VAL, SIGNAL_QUALITY_GOOD_VAL, IMITATION_EVENT, UNIMITATION_EVENT),
    ),
    imitate_pressure_sensor_signal_test_data=CaseData(
        params={"sensor_address": PRESSURE_SENSOR_ADDRESS},
        expected_result=(PRESSURE_SENSOR_VAL, SIGNAL_QUALITY_GOOD_VAL, IMITATION_EVENT, UNIMITATION_EVENT),
    ),
    # ----- Данные для проверки маскирования -----
    mask_signal_test_data=CaseData(
        params={"pressure_sensor_address": PRESSURE_SENSOR_ADDRESS, "flowmeter_address": FLOWMETER_ADDRESS}
    ),
    # ===== Ожидаемый статус сигналов =====
    expected_main_page_signals=MAIN_PAGE_SIGNALS,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_signals_test=CaseMarkers(test_case_id="120", offset=7),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    mask_info_in_journal_test=CaseMarkers(test_case_id="213", offset=9),
    imitate_flowmeter_signal_test=CaseMarkers(test_case_id="216", offset=10),
    imitate_pressure_sensor_signal_test=CaseMarkers(test_case_id="216", offset=10.5),
    mask_du_on_mini_scheme_test=CaseMarkers(test_case_id="126", offset=11),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    unmask_du_on_mini_scheme_test=CaseMarkers(test_case_id="173", offset=35),
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
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.STATIONARY,
        expected_algorithm_type=ReservedType.STATIONARY_FLOW,
        expected_leak_status=ConfirmationStatus.CONFIRMED,
        # ----- Тест AllLeaksInfo -----
        all_leaks_info_test=CaseMarkers(test_case_id="15", offset=59),
        # ----- Тест LeaksContent -----
        leaks_content_test=CaseMarkers(test_case_id="97", offset=59),
        # ----- Тест MessageInfo -----
        leak_info_in_journal=CaseMarkers(test_case_id="119", offset=59),
        # ----- Тест TuLeaksInfo -----
        tu_leaks_info_test=CaseMarkers(test_case_id="5", offset=59),
        # ----- Тест AcknowledgeLeak -----
        acknowledge_leak_test=CaseMarkers(test_case_id="6", offset=60),
        #     # ----- Тест OutputSignals -----
        output_signals_test=CaseMarkers(test_case_id="33", offset=61),
    ),
)
