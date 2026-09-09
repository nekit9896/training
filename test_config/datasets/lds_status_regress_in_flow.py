"""
Конфигурация тестового набора Lds_status_regress_in_flow

Особенности набора:
- В течении
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
    StationaryStatus,
    UnStationaryReason,
)
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Lds_status_regress_in_flow"
SUITE_DATA_ID = 17
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

DIAGNOSTIC_AREA_2_PIPE_ID = 1463
DIAGNOSTIC_AREA_3_PIPE_ID = 474
DIAGNOSTIC_AREA_5_PIPE_ID = 1478
PIG_TRAP_ID = 344

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"


# ===== Конфигурация набора =====
LDS_STATUS_INFLOW_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    main_pipeline=MAIN_PIPELINE,
    technological_unit=TECHNOLOGICAL_UNIT,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE,
    init_cold_start_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION, LdsStatusInitialization.COLD_START_OF_SERVERS),
    ),
    serviceable_all_in_journal_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION, LdsStatusInitialization.COLD_START_OF_SERVERS),
    ),
    serviceable_all_test_data=CaseData(
        params={"pipe_ids": [DIAGNOSTIC_AREA_2_PIPE_ID, DIAGNOSTIC_AREA_3_PIPE_ID]},
        expected_result=LdsStatus.SERVICEABLE,
    ),
    deg_additive_injectors_operation_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.ADDITIVE_INJECTORS_OPERATION,
        ),
    ),
    deg_exceeding_distance_between_pressure_sensors_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS,
        ),
    ),
    deg_absence_min_pressure_sensors_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER,
        ),
    ),
    deg_faulty_pressure_sensors_at_pump_station_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.FAULTY_PRESSURE_SENSORS_AT_PUMP_STATION_NODES,
        ),
    ),
    deg_gravity_section_pumping_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.GRAVITY_SECTION_IN_PUMPING_MODE,
        ),
    ),
    deg_pig_sensor_passage_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID, "pig_trap_id": PIG_TRAP_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.PIG_SENSOR_PASSAGE,
        ),
    ),
    deg_starting_pumping_out_pumps_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.STARTING_PUMPING_OUT_PUMPS,
            StationaryStatus.UNSTATIONARY,
            UnStationaryReason.CHANGING_WORKING_OF_PUMPING_OUT_PUMPS,
        ),
    ),
    faulty_absence_min_flow_meters_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.FAULTY,
            LdsStatusFaulty.ABSENCE_MIN_FLOW_METERS_REQUIRED_NUMBER,
        ),
    ),
    deg_exceeding_distance_between_flow_meters_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_FLOW_METERS,
        ),
    ),
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    init_cold_start_test=CaseMarkers(test_case_id="17", offset=7),
    init_cold_start_in_journal_test=CaseMarkers(test_case_id="228", offset=7),
    serviceable_after_cold_start_test=CaseMarkers(test_case_id="186", offset=22),
    deg_exceeding_distance_between_pressure_sensors_test=CaseMarkers(test_case_id="164", offset=32),
    deg_gravity_section_pumping_test=CaseMarkers(test_case_id="167", offset=34),
    deg_absence_min_pressure_sensors_test=CaseMarkers(test_case_id="166", offset=38.5),
    serviceable_after_deg_absence_min_pressure_sensors_test=CaseMarkers(test_case_id="186", offset=43),
    deg_starting_pumping_out_pumps_test=CaseMarkers(test_case_id="174", offset=46),
    serviceable_after_deg_starting_pumping_out_pumps_test=CaseMarkers(test_case_id="186", offset=52.5),
    faulty_absence_min_flow_meters_test=CaseMarkers(test_case_id="170", offset=60),
    faulty_absence_min_flow_meters_continuous_test=CaseMarkers(test_case_id="170", offset=73),
    serviceable_after_faulty_test=CaseMarkers(test_case_id="186", offset=76),
    deg_exceeding_distance_between_flow_meters_test=CaseMarkers(test_case_id="169", offset=107),
    # serviceable_after_deg_exceeding_distance_between_flow_meters_test=CaseMarkers(test_case_id="186", offset=114.5),
    # TODO разобраться в LDS-14444
    deg_faulty_pressure_sensors_at_pump_station_test=CaseMarkers(test_case_id="184", offset=122),
    serviceable_after_deg_faulty_pressure_sensors_at_pump_test=CaseMarkers(test_case_id="186", offset=126),
    deg_additive_injectors_operation_test=CaseMarkers(test_case_id="188", offset=132),
    deg_pig_sensor_passage_test=CaseMarkers(test_case_id="165", offset=140),
)
