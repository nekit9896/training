"""
Конфигурация тестового набора Lds_status_regress_in_flow

Особенности набора:
- В течении
- Проверка режимов работы СОУ
- Проверка группы причин режимов работы СОУ, связанных с БИК
"""

from constants.enums import TU, AdminTU, LdsStatus, LdsStatusDegradation, LdsStatusInitialization, MeasureConversionRule
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Lds_status_regress_bik"
SUITE_DATA_ID = 18
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

DIAGNOSTIC_AREA_2_PIPE_ID = 1463
DIAGNOSTIC_AREA_3_PIPE_ID = 474
DIAGNOSTIC_AREA_5_PIPE_ID = 1474
DIAGNOSTIC_AREA_2_CONTROL_POINT = "ЗА 105-3 - ЗА 129-3"
DIAGNOSTIC_AREA_3_CONTROL_POINT = "ЗА 180-3 - ЗА 207-3"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"


# ===== Конфигурация набора =====
LDS_STATUS_BIK_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE_BIK,
    main_pipeline=MAIN_PIPELINE,
    init_cold_start_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION, LdsStatusInitialization.COLD_START_OF_SERVERS),
    ),
    deg_rejection_temperature_sensor_on_du_2_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_TEMPERATURE_SENSOR,
        ),
    ),
    deg_rejection_temperature_sensor_on_du_3_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_TEMPERATURE_SENSOR,
        ),
    ),
    deg_rejection_temperature_sensor_on_du_5_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_TEMPERATURE_SENSOR,
        ),
    ),
    deg_rejection_density_and_viscosity_on_du_2_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_2_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_DENSITY_SENSOR,
            LdsStatusDegradation.REJECTION_VISCOSITY_SENSOR,
        ),
    ),
    deg_rejection_density_and_viscosity_on_du_3_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_3_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_DENSITY_SENSOR,
            LdsStatusDegradation.REJECTION_VISCOSITY_SENSOR,
        ),
    ),
    deg_rejection_density_and_viscosity_on_du_5_test_data=CaseData(
        params={"pipe_id": DIAGNOSTIC_AREA_5_PIPE_ID},
        expected_result=(
            LdsStatus.DEGRADATION,
            LdsStatusDegradation.REJECTION_DENSITY_SENSOR,
            LdsStatusDegradation.REJECTION_VISCOSITY_SENSOR,
        ),
    ),
    degradation_temperature_du_2_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_TEMPERATURE_SENSOR.report_text,
        ),
    ),
    degradation_density_du_2_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_DENSITY_SENSOR.report_text,
        ),
    ),
    degradation_viscosity_du_2_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_2_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_VISCOSITY_SENSOR.report_text,
        ),
    ),
    degradation_temperature_sensor_du_3_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_3_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_TEMPERATURE_SENSOR.report_text,
        ),
    ),
    degradation_density_du_3_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_3_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_DENSITY_SENSOR.report_text,
        ),
    ),
    degradation_viscosity_du_3_in_journal_test_data=CaseData(
        params={"control_points": [DIAGNOSTIC_AREA_3_CONTROL_POINT]},
        expected_result=(
            LdsStatus.DEGRADATION.report_text,
            LdsStatusDegradation.REJECTION_VISCOSITY_SENSOR.report_text,
        ),
    ),
    # ===== Базовые ТЕСТЫ ====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    init_cold_start_test=CaseMarkers(test_case_id="18", offset=7),
    init_cold_start_in_journal_test=CaseMarkers(test_case_id="228", offset=7),
    # ===== ТЕСТЫ состония СОУ на схеме =====
    deg_rejection_temperature_sensor_on_du_2_test=CaseMarkers(test_case_id="179", offset=25),
    deg_rejection_density_and_viscosity_on_du_2_test=CaseMarkers(test_case_id="181", offset=35),
    deg_rejection_temperature_sensor_on_du_3_test=CaseMarkers(test_case_id="179", offset=46),
    deg_rejection_density_and_viscosity_on_du_3_test=CaseMarkers(test_case_id="181", offset=53),
    # ===== ТЕСТЫ в журнале для ДУ2 =====
    degradation_temperature_du_2_in_journal_test=CaseMarkers(test_case_id="179", offset=23),
    degradation_density_du_2_in_journal_test=CaseMarkers(test_case_id="181", offset=32),
    degradation_viscosity_du_2_in_journal_test=CaseMarkers(test_case_id="181", offset=32),
    # ===== ТЕСТЫ в журнале для ДУ3 =====
    degradation_temperature_du_3_in_journal_test=CaseMarkers(test_case_id="179", offset=46),
    degradation_density_du_3_in_journal_test=CaseMarkers(test_case_id="181", offset=53),
    degradation_viscosity_du_3_in_journal_test=CaseMarkers(test_case_id="181", offset=53),
)
