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
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE,
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
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    init_cold_start_test=CaseMarkers(test_case_id="18", offset=7),
    init_cold_start_in_journal_test=CaseMarkers(test_case_id="228", offset=7),
    deg_rejection_temperature_sensor_on_du_2_test=CaseMarkers(test_case_id="179", offset=25),
    deg_rejection_density_and_viscosity_on_du_2_test=CaseMarkers(test_case_id="181", offset=35),
    deg_rejection_temperature_sensor_on_du_3_test=CaseMarkers(test_case_id="179", offset=58),
    deg_rejection_density_and_viscosity_on_du_3_test=CaseMarkers(test_case_id="181", offset=68),
)
