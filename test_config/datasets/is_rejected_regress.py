"""
Конфигурация тестового набора is_rejected_regress

Особенности набора:
- Проверка отбраковки сигналов с датчиков давления и расходомеров
- Типы отбраковки: empty, quality, VTOR, nearbySensors,
  diagnosticInfo, constantSignal, range, discharge

Слои данных:
- emptyFilterSettings:       0-111 с (расход), 0-174 с (давление)
- qualityFilterSettings:     234-294 с (расход), 294-354 с (давление)
- vtorFilterSettings:        354-414 с (расход), 414-474 с (давление)
- nearbySensorsFilterSettings: 474--534 с (давление Pin+Pout)
- diagnosticInfoFilterSettings: 534-594 с (расход)
- constantSignalFilter:      655-713 с (расход), 717-777 с (давление)
- rangeFilterSettings upper:  779-839 с (расход), 1015-1075 с (давление)
- rangeFilterSettings lower:  899-957 с (расход), 1133-1196 cс (давление)
- dischargeFilterSettings:    ~1194 с (расход), ~1270 с (давление)
"""

from constants.enums import TU, RejectionCriteria, RejectionSensorTag
from test_config.models_for_tests import CaseMarkers, IsRejectedConfig, RejectionTestCase

# ===== Константы набора =====
SUITE_NAME = "is_rejected_regress"
SUITE_DATA_ID = 183
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"

# ===== Тегированные датчики =====
FLOW_KRIM = RejectionSensorTag.NPS_KRIM_P_Vmom
PRESSURE_VELKRIM = RejectionSensorTag.KP_209_1_Pin
FLOW_TIH = RejectionSensorTag.NPS_TIH_5_Vmom
PRESSURE_KP7 = RejectionSensorTag.KP_7_Pin
PRESSURE_KP8_PIN = RejectionSensorTag.KP_8_Pin
PRESSURE_KP8_POUT = RejectionSensorTag.KP_8_Pout

# ===== Ожидаемые signalName =====
SIGNAL_FLOW = "Расход"
SIGNAL_PRESSURE = "Значение давления"


# ===== Конфигурация набора =====
IS_REJECTED_REGRESS_CONFIG = IsRejectedConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    rejection_cases=[
        # ===== emptyFilterSettings =====
        RejectionTestCase(
            name="empty_flow",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по отсутствию значения",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.EMPTY,
            time_range_start_s=0,
            time_range_end_s=111,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=1.85),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=1.85),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=1.85),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=1.85),
        ),
        RejectionTestCase(
            name="empty_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по отсутствию значения",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.EMPTY,
            time_range_start_s=0,
            time_range_end_s=174,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=2.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=2.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=2.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=2.9),
        ),
        # ===== qualityFilterSettings =====
        RejectionTestCase(
            name="quality_flow",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=234,
            time_range_end_s=294,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=4.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=4.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=4.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=4.9),
        ),
        RejectionTestCase(
            name="quality_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=294,
            time_range_end_s=354,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=5.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=5.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=5.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=5.9),
        ),
        # ===== vtorFilterSettings =====
        RejectionTestCase(
            name="vtor_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по ВТОР сигналу",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=354,
            time_range_end_s=414,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=6.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=6.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=6.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=6.9),
        ),
        RejectionTestCase(
            name="vtor_pressure",
            sensor=PRESSURE_KP7,
            expected_event="Отбраковка по ВТОР сигналу",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=414,
            time_range_end_s=474,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=7.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=7.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=7.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=7.9),
        ),
        # ===== nearbySensorsFilterSettings =====
        RejectionTestCase(
            name="nearby_pressure_pin",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка соседних датчиков",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=474,
            time_range_end_s=534,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=8.8),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=8.8),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=8.8),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=8.8),
        ),
        RejectionTestCase(
            name="nearby_pressure_pout",
            sensor=PRESSURE_KP8_POUT,
            expected_event="Отбраковка соседних датчиков",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=474,
            time_range_end_s=534,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=8.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=8.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=8.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=8.9),
        ),
        # ===== diagnosticInfoFilterSettings =====
        RejectionTestCase(
            name="diagnostic_info_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диагностической информации",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.DIAGNOSTIC_INFO,
            time_range_start_s=534,
            time_range_end_s=594,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=9.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=9.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=9.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=9.9),
        ),
        # ===== constantSignalFilter =====
        RejectionTestCase(
            name="constant_signal_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по постоянному сигналу",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
            time_range_start_s=655,
            time_range_end_s=713,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=11.8),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=11.8),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=11.8),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=11.8),
        ),
        RejectionTestCase(
            name="constant_signal_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по постоянному сигналу",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
            time_range_start_s=717,
            time_range_end_s=777,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=12.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=12.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=12.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=12.9),
        ),
        # ===== rangeFilterSettings (верхняя граница) =====
        RejectionTestCase(
            name="range_upper_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диапазону значений",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=779,
            time_range_end_s=839,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=13.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=13.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=13.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=13.9),
        ),
        RejectionTestCase(
            name="range_upper_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по диапазону значений",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=1015,
            time_range_end_s=1075,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=17.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=17.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=17.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=17.9),
        ),
        # ===== rangeFilterSettings (нижняя граница) =====
        RejectionTestCase(
            name="range_lower_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диапазону значений",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=899,
            time_range_end_s=957,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=15.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=15.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=15.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=15.9),
        ),
        RejectionTestCase(
            name="range_lower_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по диапазону значений",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=1133,
            time_range_end_s=1196,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=19.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=19.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=19.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=19.9),
        ),
        # ===== dischargeFilterSettings =====
        RejectionTestCase(
            name="discharge_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по единичному выбросу",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.DISCHARGE,
            time_range_start_s=1164,
            time_range_end_s=1224,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=20.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=20.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=20.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=20.4),
        ),
        RejectionTestCase(
            name="discharge_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по единичному выбросу",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.DISCHARGE,
            time_range_start_s=1240,
            time_range_end_s=1300,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=21.6),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=21.6),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=21.6),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=21.6),
        ),
    ],
)
