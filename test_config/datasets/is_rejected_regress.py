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

from constants.enums import TU, RejectionSensorTag
from test_config.models_for_tests import CaseMarkers, IsRejectedConfig, RejectionTestCase

# ===== Константы набора =====
SUITE_NAME = "is_rejected_regress"
SUITE_DATA_ID = 0
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
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=6),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=6),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=6),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=6),
        ),
        RejectionTestCase(
            name="empty_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=6.5),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=6.5),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=6.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=6.5),
        ),
        # ===== qualityFilterSettings =====
        RejectionTestCase(
            name="quality_flow",
            sensor=FLOW_KRIM,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=9.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=9.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=9.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=9.4),
        ),
        RejectionTestCase(
            name="quality_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=10.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=10.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=10.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=10.4),
        ),
        # ===== vtorFilterSettings =====
        RejectionTestCase(
            name="vtor_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=11.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=11.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=11.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=11.4),
        ),
        RejectionTestCase(
            name="vtor_pressure",
            sensor=PRESSURE_KP7,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=12.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=12.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=12.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=12.4),
        ),
        # ===== nearbySensorsFilterSettings =====
        RejectionTestCase(
            name="nearby_pressure_pin",
            sensor=PRESSURE_KP8_PIN,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=13.4),
        ),
        RejectionTestCase(
            name="nearby_pressure_pout",
            sensor=PRESSURE_KP8_POUT,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=13.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=13.4),
        ),
        # ===== diagnosticInfoFilterSettings =====
        RejectionTestCase(
            name="diagnostic_info_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=14.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=14.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=14.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=14.4),
        ),
        # ===== constantSignalFilter =====
        RejectionTestCase(
            name="constant_signal_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=16.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=16.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=16.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=16.4),
        ),
        RejectionTestCase(
            name="constant_signal_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=17.5),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=17.5),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=17.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=17.5),
        ),
        # ===== rangeFilterSettings (верхняя граница) =====
        RejectionTestCase(
            name="range_upper_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=18.5),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=18.5),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=18.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=18.5),
        ),
        RejectionTestCase(
            name="range_upper_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=22.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=22.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=22.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=22.4),
        ),
        # ===== rangeFilterSettings (нижняя граница) =====
        RejectionTestCase(
            name="range_lower_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=20),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=20),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=20),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=20),
        ),
        RejectionTestCase(
            name="range_lower_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=24.4),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=24.4),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=24.4),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=24.4),
        ),
        # ===== dischargeFilterSettings =====
        RejectionTestCase(
            name="discharge_flow",
            sensor=FLOW_TIH,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=24.9),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=24.9),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=24.9),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=24.9),
        ),
        RejectionTestCase(
            name="discharge_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="",
            expected_signal_name="",
            expected_criteria_names=0,
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=26.2),
            rejection_journal_test=CaseMarkers(test_case_id="", offset=26.2),
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=26.2),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=26.2),
        ),
    ],
)
