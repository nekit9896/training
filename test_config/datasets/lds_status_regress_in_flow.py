"""
Конфигурация тестового набора Lds_status_regress_in_flow

Особенности набора:
- В течении
- Проверка режимов работы СОУ
- Проверка причин режимов работы СОУ
"""

from constants.enums import (
    TU,
    LdsStatus,
    LdsStatusDegradation,
    LdsStatusFaulty,
    LdsStatusInitialization,
    StationaryStatus,
    UnStationaryReason,
)
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Lds_status_regress_in_flow"
SUITE_DATA_ID = 160
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3


# ===== Конфигурация набора =====
LDS_STATUS_INFLOW_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    lds_status_init_cold_start_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION.value, LdsStatusInitialization.COLD_START_OF_SERVERS),
    ),
    lds_status_serviceable_all_test_data=CaseData(expected_result=LdsStatus.SERVICEABLE.value),
    lds_status_deg_exceeding_distance_between_pressure_sensors_test_data=CaseData(
        params={"diagnostic_area_id": 3},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS,
        ),
    ),
    lds_status_deg_not_enough_pressure_sensors_test_data=CaseData(
        params={"diagnostic_area_id": 3},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER,
        ),
    ),
    lds_status_deg_gravity_section_pumping_test_data=CaseData(
        params={"diagnostic_area_id": 5},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.GRAVITY_SECTION_IN_PUMPING_MODE,
        ),
    ),
    lds_status_deg_pig_sensor_passage_test_data=CaseData(
        params={"diagnostic_area_id": 2, "pig_trap_id": 344},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.PIG_SENSOR_PASSAGE,
        ),
    ),
    lds_status_deg_starting_pumping_out_pumps_test_data=CaseData(
        params={"diagnostic_area_id": 25},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.STARTING_PUMPING_OUT_PUMPS,
            StationaryStatus.UNSTATIONARY.value,
            UnStationaryReason.CHANGING_WORKING_OF_PUMPING_OUT_PUMPS,
        ),
    ),
    lds_status_faulty_absence_min_flow_meters_test_data=CaseData(
        params={"diagnostic_area_id": 5},
        expected_result=(
            LdsStatus.FAULTY.value,
            LdsStatusFaulty.ABSENCE_MIN_FLOW_METERS_REQUIRED_NUMBER,
        ),
    ),
    lds_status_deg_exceeding_distance_between_flow_meters_test_data=CaseData(
        params={"diagnostic_area_id": 25},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            LdsStatusDegradation.EXCEEDING_DISTANCE_BETWEEN_FLOW_METERS,
        ),
    ),
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    lds_status_init_cold_start_test=CaseMarkers(test_case_id="160", offset=7),
    lds_status_deg_exceeding_distance_between_pressure_sensors_test=CaseMarkers(test_case_id="164", offset=32),
    lds_status_deg_gravity_section_pumping_test=CaseMarkers(test_case_id="167", offset=34),
    lds_status_deg_not_enough_pressure_sensors_test=CaseMarkers(test_case_id="166", offset=41.5),
    lds_status_deg_starting_pumping_out_pumps_test=CaseMarkers(test_case_id="174", offset=46.5),
    lds_status_deg_exceeding_distance_between_flow_meters_test=CaseMarkers(test_case_id="169", offset=54),
    lds_status_faulty_absence_min_flow_meters_test=CaseMarkers(test_case_id="170", offset=70),
    lds_status_deg_pig_sensor_passage_test=CaseMarkers(test_case_id="165", offset=100),
)
