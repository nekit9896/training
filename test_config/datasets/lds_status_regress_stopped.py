"""
Конфигурация тестового набора Lds_status_regress_in_flow

Особенности набора:
- В режиме МТ: Режим остановленной перекачки
- Проверка режимов работы СОУ
- Проверка причин режимов работы СОУ
"""

from constants.enums import (
    TU,
    AdminTU,
    LdsStatus,
    LdsStatusDegradation,
    LdsStatusFaulty,
    LdsStatusInitialization,
    MeasureConversionRule,
)
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Lds_status_regress_stopping"
SUITE_DATA_ID = 19
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

DIAGNOSTIC_AREA_2_PIPE_ID = 1463
DIAGNOSTIC_AREA_3_PIPE_ID = 474
DIAGNOSTIC_AREA_5_PIPE_ID = 1474
DIAGNOSTIC_AREA_2_CONTROL_POINT = "ЗА 105-3 - ЗА 129-3"
DIAGNOSTIC_AREA_3_CONTROL_POINT = "ЗА 180-3 - ЗА 207-3"
DIAGNOSTIC_AREA_5_CONTROL_POINT = "ЗА 235-3-1 - ЗА 246-3-2"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"


# ===== Конфигурация набора =====
LDS_STATUS_STOPPING_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE,
    main_pipeline=MAIN_PIPELINE,
    init_accumulation_data_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.INITIALIZATION,
            LdsStatusInitialization.ACCUMULATION_DATA,
        ),
    ),
    init_accumulation_data_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.INITIALIZATION.report_text,
            LdsStatusInitialization.ACCUMULATION_DATA.report_text,
        ),
    ),
    init_cold_start_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION, LdsStatusInitialization.COLD_START_OF_SERVERS),
    ),
    init_switching_shut_off_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.INITIALIZATION,
            LdsStatusInitialization.SWITCHING_SHUT_OFF_IN_STOPPED_PUMPING_MODE,
        ),
    ),
    init_switching_shut_off_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_3_CONTROL_POINT]},
        expected_result=(
            LdsStatus.INITIALIZATION.report_text,
            LdsStatusInitialization.SWITCHING_SHUT_OFF_IN_STOPPED_PUMPING_MODE.report_text,
        ),
    ),
    serviceable_all_test_data=CaseData(
        params={"pipe_ids": [DIAGNOSTIC_AREA_3_PIPE_ID]},
        expected_result=LdsStatus.SERVICEABLE,
    ),
    serviceable_all_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_3_CONTROL_POINT]},
        expected_result=LdsStatus.SERVICEABLE.report_text,
    ),
    deg_gravity_section_pumping_in_stopping_test_data=CaseData(
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.GRAVITY_SECTION_IN_STOPPED_PUMPING_MODE,
        ),
    ),
    deg_gravity_section_pumping_in_stopping_in_journal_test_data=CaseData(
        params={
            "control_points": [
                DIAGNOSTIC_AREA_2_CONTROL_POINT,
                DIAGNOSTIC_AREA_3_CONTROL_POINT,
                DIAGNOSTIC_AREA_5_CONTROL_POINT,
            ]
        },
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.GRAVITY_SECTION_IN_STOPPED_PUMPING_MODE.report_text,
        ),
    ),
    deg_exceeding_distance_between_pressure_sensors_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS,
        ),
    ),
    deg_exceeding_distance_between_pressure_sensors_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS.report_text,
        ),
    ),
    deg_faulty_pressure_sensors_at_pump_station_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.FAULTY_PRESSURE_SENSORS_AT_PUMP_STATION_NODES,
        ),
    ),
    deg_faulty_pressure_sensors_at_pump_station_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.FAULTY_PRESSURE_SENSORS_AT_PUMP_STATION_NODES.report_text,
        ),
    ),
    faulty_absence_min_pressure_sensors_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.FAULTY,
            LdsStatusFaulty.ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER,
        ),
    ),
    faulty_absence_min_pressure_sensors_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_5_CONTROL_POINT]},
        expected_result=(
            LdsStatus.FAULTY.report_text,
            LdsStatusFaulty.ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER.report_text,
        ),
    ),
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    init_cold_start_test=CaseMarkers(test_case_id="19", offset=7),
    init_cold_start_in_journal_test=CaseMarkers(test_case_id="228", offset=7),
    deg_gravity_section_pumping_in_stopping_test=CaseMarkers(test_case_id="167", offset=22),
    deg_gravity_section_pumping_in_stopping_in_journal_test=CaseMarkers(test_case_id="239", offset=22),
    init_switching_shut_off_test=CaseMarkers(test_case_id="204", offset=32),
    init_switching_shut_off_in_journal_test=CaseMarkers(test_case_id="239", offset=32),
    serviceable_after_switching_shut_off_test=CaseMarkers(test_case_id="162", offset=35),
    serviceable_after_switching_shut_off_in_journal_test=CaseMarkers(test_case_id="239", offset=35),
    deg_faulty_pressure_sensors_at_pump_station_test=CaseMarkers(test_case_id="184", offset=37.5),
    deg_faulty_pressure_sensors_at_pump_station_in_journal_test=CaseMarkers(test_case_id="239", offset=37.5),
    serviceable_after_deg_faulty_pressure_sensors_at_pump_test=CaseMarkers(test_case_id="162", offset=42),
    serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal_test=CaseMarkers(test_case_id="239", offset=42),
    deg_exceeding_distance_between_pressure_sensors_test=CaseMarkers(test_case_id="164", offset=49),
    deg_exceeding_distance_between_pressure_sensors_in_journal_test=CaseMarkers(test_case_id="239", offset=49),
    init_accumulation_data_test=CaseMarkers(test_case_id="203", offset=70),
    init_accumulation_data_in_journal_test=CaseMarkers(test_case_id="239", offset=70),
    faulty_absence_min_pressure_sensors_test=CaseMarkers(test_case_id="170", offset=85),
    faulty_absence_min_pressure_sensors_in_journal_test=CaseMarkers(test_case_id="239", offset=85),
)
