"""
Конфигурация тестового набора для имитации выходных сигналов СОУ (обратный обмен СДКУ).

Особенности набора:
- Имитация выходных сигналов (не входных, как imitate_sensor_signal).
- Проверка изменений выполняется напрямую через OPC UA (ns=2, string NodeId).

Пример:
- ДУ (НПС-НПС): CHTN_linearParts_9
- КП-КП (сегменты ДУ): CHTN_controlledSites_188

Запуск:
- Все наборы: pytest tests/test_output_signal_imitation.py
- Один набор: pytest tests/test_output_signal_imitation.py --suites=output_signal_imitation
"""

from constants.enums import TU, OutputSignalType
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseMarkers, OutputSignalImitationCase, OutputSignalImitationConfig

# ===== Константы набора =====
SUITE_NAME = "OutputSignalImitation_tn3"
SUITE_DATA_ID = 0
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок (ЧТН)
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# ===== Адреса участков для имитации (примеры из конфигурации трубы) =====
LINEAR_PART_ADDRESS = "CHTN_linearParts_9"
CONTROLLED_SITE_ADDRESS = "CHTN_controlledSites_188"

# ===== Кейсы имитации выходных сигналов =====
# ДУ (НПС-НПС): утечка, координата, объём, время, квитирование, маскирование
LINEAR_PART_CASES = [
    OutputSignalImitationCase(signal_type=OutputSignalType.LEAK, address=LINEAR_PART_ADDRESS, imitate_value="true"),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.LEAK_COORDINATE, address=LINEAR_PART_ADDRESS, imitate_value="35000"
    ),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.LEAK_VOLUME, address=LINEAR_PART_ADDRESS, imitate_value="100.5"
    ),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.LEAK_TIME, address=LINEAR_PART_ADDRESS, imitate_value="2026-01-01T00:00:00Z"
    ),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.ACKNOWLEDGE, address=LINEAR_PART_ADDRESS, imitate_value="true"
    ),
    OutputSignalImitationCase(signal_type=OutputSignalType.MASK, address=LINEAR_PART_ADDRESS, imitate_value="true"),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.MASK_REASON, address=LINEAR_PART_ADDRESS, imitate_value="test_reason"
    ),
]

# КП-КП (сегменты ДУ): режим МТ, режим СОУ, самотеки
CONTROLLED_SITE_CASES = [
    OutputSignalImitationCase(
        signal_type=OutputSignalType.PUMPING_STATUS, address=CONTROLLED_SITE_ADDRESS, imitate_value="1"
    ),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.LDS_STATUS, address=CONTROLLED_SITE_ADDRESS, imitate_value="4"
    ),
    OutputSignalImitationCase(
        signal_type=OutputSignalType.FREE_FLOW, address=CONTROLLED_SITE_ADDRESS, imitate_value="true"
    ),
]

# ===== Конфигурация набора =====
OUTPUT_SIGNAL_IMITATION_CONFIG = OutputSignalImitationConfig(
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    cases=LINEAR_PART_CASES + CONTROLLED_SITE_CASES,
    imitate_leak_test=CaseMarkers(test_case_id="0", offset=0),
    imitate_leak_coordinate_test=CaseMarkers(test_case_id="0", offset=2),
    imitate_leak_volume_test=CaseMarkers(test_case_id="0", offset=4),
    imitate_leak_time_test=CaseMarkers(test_case_id="0", offset=6),
    imitate_acknowledge_test=CaseMarkers(test_case_id="0", offset=8),
    imitate_mask_test=CaseMarkers(test_case_id="0", offset=10),
    imitate_mask_reason_test=CaseMarkers(test_case_id="0", offset=12),
    imitate_pumping_status_test=CaseMarkers(test_case_id="0", offset=14),
    imitate_lds_status_test=CaseMarkers(test_case_id="0", offset=16),
    imitate_free_flow_test=CaseMarkers(test_case_id="0", offset=18),
)
