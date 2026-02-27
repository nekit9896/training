"""
Конфигурация тестового набора
"""

from constants.enums import TU
from test_config.models_for_tests import CaseData, CaseMarkers, LDSStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Sou_mode_InFlow"
SUITE_DATA_ID = 106
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3


# ===== Конфигурация набора =====
LDS_STATUS_REASONS_CONFIG = LDSStatusConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    lds_status_initialization_test_data=CaseData(),
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="52", offset=7),
)
