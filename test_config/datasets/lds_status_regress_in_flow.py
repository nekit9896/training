"""
Конфигурация тестового набора
"""

from constants.enums import TU, DegradationLdsStatusReasons, InitializationLdsStatusReasons, LdsStatus
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
        expected_result=(LdsStatus.INITIALIZATION.value, InitializationLdsStatusReasons.COLD_START_OF_SERVERS),
    ),
    lds_status_serviceable_all_test_data=CaseData(expected_result=LdsStatus.SERVICEABLE.value),
    lds_status_deg_exceeding_distance_between_pressure_sensors_test_data=CaseData(
        params={"diagnostic_area_id": 3},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            DegradationLdsStatusReasons.EXCEEDING_DISTANCE_BETWEEN_SERVICEABLE_PRESSURE_SENSORS,
        ),
    ),
    lds_status_deg_not_enough_pressure_sensors_test_data=CaseData(
        params={"diagnostic_area_id": 3},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            DegradationLdsStatusReasons.ABSENCE_MIN_PRESSURE_SENSORS_REQUIRED_NUMBER,
        ),
    ),
    lds_status_deg_gravity_section_pumping_test_data=CaseData(
        params={"diagnostic_area_id": 5},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            DegradationLdsStatusReasons.GRAVITY_SECTION_IN_PUMPING_MODE,
        ),
    ),
    lds_status_deg_pig_sensor_passage_test_data=CaseData(
        params={"diagnostic_area_id": 2, "pig_trap_id": 344},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            DegradationLdsStatusReasons.PIG_SENSOR_PASSAGE,
        ),
    ),
    lds_status_deg_exceeding_distance_between_flow_meters_test_data=CaseData(
        params={"diagnostic_area_id": 25},
        expected_result=(
            LdsStatus.DEGRADATION.value,
            DegradationLdsStatusReasons.EXCEEDING_DISTANCE_BETWEEN_FLOW_METERS,
        ),
    ),
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    lds_status_init_cold_start_test=CaseMarkers(test_case_id="160", offset=7),
    lds_status_deg_exceeding_distance_between_pressure_sensors_test=CaseMarkers(test_case_id="164", offset=28),
    lds_status_deg_gravity_section_pumping_test=CaseMarkers(test_case_id="167", offset=30),
    lds_status_deg_not_enough_pressure_sensors_test=CaseMarkers(test_case_id="166", offset=36.5),
    lds_status_deg_pig_sensor_passage_test=CaseMarkers(test_case_id="165", offset=38),
    lds_status_serviceable_after_faulty_test=CaseMarkers(test_case_id="162", offset=97),
    lds_status_deg_exceeding_distance_between_flow_meters_test=CaseMarkers(test_case_id="169", offset=100),
)
