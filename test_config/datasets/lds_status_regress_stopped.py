"""
Конфигурация тестового набора
"""

from constants.enums import TU, InitializationLdsStatusReasons, LdsStatus
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Lds_status_regress_stopping"
SUITE_DATA_ID = 172
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3


# ===== Конфигурация набора =====
LDS_STATUS_STOPPED_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    lds_status_init_cold_start_test_data=CaseData(
        expected_result=(LdsStatus.INITIALIZATION.value, InitializationLdsStatusReasons.COLD_START_OF_SERVERS),
    ),
    # ===== ТЕСТЫ =====
    lds_status_basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    lds_status_init_cold_start_test=CaseMarkers(test_case_id="172", offset=7),
)
