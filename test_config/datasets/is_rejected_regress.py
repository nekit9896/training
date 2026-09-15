"""
Конфигурация тестового набора is_rejected_regress

Особенности набора:
- Проверка отбраковки сигналов с датчиков давления и расходомеров
- Типы отбраковки: empty, quality, VTOR, nearbySensors,
  diagnosticInfo, constantSignal, range
- Для каждого типа - отдельный RejectionTestCase на снятие отбраковки

Запуск:
pytest tests/test_is_rejected_regress.py --suites=is_rejected_regress
"""

from constants.enums import TU, AdminTU, MeasureConversionRule, RejectionCriteria, RejectionSensorTag
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseMarkers, IsRejectedConfig, RejectionTestCase

# ===== Константы набора =====
SUITE_NAME = "is_rejected_regress"
SUITE_DATA_ID = 16
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
SIGNAL_FLOW = "СИ расхода. Расход"
SIGNAL_PRESSURE = "СИ давления"

# ===== Конфигурация набора =====
IS_REJECTED_REGRESS_CONFIG = IsRejectedConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    main_pipeline=MAIN_PIPELINE,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_REJECT,
    # ===== Vault settings =====
    requires_process_empty_values_rejection=True,
    # ===== Tests =====
    rejection_report_test=CaseMarkers(test_case_id="210", offset=72),
    rejection_cases=[
        # ===== emptyFilterSettings =====
        RejectionTestCase(
            name="empty_flow",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по отсутствию значения",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.EMPTY,
            time_range_start_s=0,
            time_range_end_s=240,
            rejection_input_signals_test=CaseMarkers(test_case_id="189", offset=3),
            rejection_main_page_test=CaseMarkers(test_case_id="189", offset=3),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="189", offset=3),
        ),
        RejectionTestCase(
            name="empty_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по отсутствию значения",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.EMPTY,
            time_range_start_s=0,
            time_range_end_s=540,
            rejection_input_signals_test=CaseMarkers(test_case_id="190", offset=4),
            rejection_main_page_test=CaseMarkers(test_case_id="190", offset=6),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="190", offset=5),
        ),
        # ===== qualityFilterSettings =====
        RejectionTestCase(
            name="quality_flow",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=600,
            time_range_end_s=840,
            rejection_input_signals_test=CaseMarkers(test_case_id="191", offset=13),
            rejection_journal_test=CaseMarkers(test_case_id="191", offset=14),
            rejection_main_page_test=CaseMarkers(test_case_id="191", offset=11),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="191", offset=12),
        ),
        RejectionTestCase(
            name="quality_flow_clearance",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по качеству снята",
            expected_signal_name=SIGNAL_FLOW,
            expected_is_rejected=False,
            time_range_start_s=600,
            time_range_end_s=840,
            # rejection_input_signals_test=CaseMarkers(test_case_id="191", offset=16), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="191", offset=16),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="191", offset=16),
        ),
        RejectionTestCase(
            name="quality_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=900,
            time_range_end_s=1140,
            rejection_input_signals_test=CaseMarkers(test_case_id="205", offset=18),
            rejection_journal_test=CaseMarkers(test_case_id="205", offset=19),
            rejection_main_page_test=CaseMarkers(test_case_id="205", offset=16.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="205", offset=17),
        ),
        RejectionTestCase(
            name="quality_pressure_clearance",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по качеству снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=900,
            time_range_end_s=1140,
            # rejection_input_signals_test=CaseMarkers(test_case_id="205", offset=21), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="205", offset=21),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="205", offset=21),
        ),
        # ===== vtorFilterSettings =====
        RejectionTestCase(
            name="vtor_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по сигналу ВТОР",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=1200,
            time_range_end_s=1440,
            rejection_input_signals_test=CaseMarkers(test_case_id="206", offset=23),
            rejection_journal_test=CaseMarkers(test_case_id="206", offset=24),
            rejection_main_page_test=CaseMarkers(test_case_id="206", offset=21.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="206", offset=22),
        ),
        RejectionTestCase(
            name="vtor_flow_clearance",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по сигналу ВТОР снята",
            expected_signal_name=SIGNAL_FLOW,
            expected_is_rejected=False,
            time_range_start_s=1200,
            time_range_end_s=1440,
            # rejection_input_signals_test=CaseMarkers(test_case_id="206", offset=26), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="206", offset=26),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="206", offset=26),
        ),
        RejectionTestCase(
            name="vtor_pressure",
            sensor=PRESSURE_KP7,
            expected_event="Отбраковка по сигналу ВТОР",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=1500,
            time_range_end_s=1740,
            rejection_input_signals_test=CaseMarkers(test_case_id="207", offset=28),
            rejection_journal_test=CaseMarkers(test_case_id="207", offset=29),
            rejection_main_page_test=CaseMarkers(test_case_id="207", offset=26.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="207", offset=27),
        ),
        RejectionTestCase(
            name="vtor_pressure_clearance",
            sensor=PRESSURE_KP7,
            expected_event="Отбраковка по сигналу ВТОР снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=1500,
            time_range_end_s=1740,
            # rejection_input_signals_test=CaseMarkers(test_case_id="207", offset=30.5), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="207", offset=30.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="207", offset=30.5),
        ),
        # ===== nearbySensorsFilterSettings =====
        RejectionTestCase(
            name="nearby_pressure_pin",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по разнице показаний СИ давления на КП",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=1800,
            time_range_end_s=2040,
            rejection_input_signals_test=CaseMarkers(test_case_id="192", offset=32),
            rejection_journal_test=CaseMarkers(test_case_id="192", offset=32.5),
            rejection_main_page_test=CaseMarkers(test_case_id="192", offset=31),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="192", offset=31.5),
        ),
        RejectionTestCase(
            name="nearby_pressure_pout",
            sensor=PRESSURE_KP8_POUT,
            expected_event="Отбраковка по разнице показаний СИ давления на КП",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=1800,
            time_range_end_s=2040,
            rejection_input_signals_test=CaseMarkers(test_case_id="193", offset=34),
            rejection_journal_test=CaseMarkers(test_case_id="193", offset=34.5),
            rejection_main_page_test=CaseMarkers(test_case_id="193", offset=33),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="193", offset=33.5),
        ),
        RejectionTestCase(
            name="nearby_pressure_pin_clearance",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по разнице показаний СИ давления на КП снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=1800,
            time_range_end_s=2040,
            # rejection_input_signals_test=CaseMarkers(test_case_id="192", offset=35.5), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="192", offset=35.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="192", offset=35.5),
        ),
        RejectionTestCase(
            name="nearby_pressure_pout_clearance",
            sensor=PRESSURE_KP8_POUT,
            expected_event="Отбраковка по разнице показаний СИ давления на КП снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=1800,
            time_range_end_s=2040,
            # rejection_input_signals_test=CaseMarkers(test_case_id="193", offset=35.5), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="193", offset=35.5),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="193", offset=35.5),
        ),
        # ===== diagnosticInfoFilterSettings =====
        RejectionTestCase(
            name="diagnostic_info_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диагностической информации",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.DIAGNOSTIC_INFO,
            time_range_start_s=2100,
            time_range_end_s=2340,
            rejection_input_signals_test=CaseMarkers(test_case_id="194", offset=38),
            # rejection_journal_test=CaseMarkers(test_case_id="194", offset=39),  # blocked by LDS-12394
            rejection_main_page_test=CaseMarkers(test_case_id="194", offset=36),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="194", offset=37),
        ),
        RejectionTestCase(
            name="diagnostic_info_flow_clearance",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диагностической информации снята",
            expected_signal_name=SIGNAL_FLOW,
            expected_is_rejected=False,
            time_range_start_s=2100,
            time_range_end_s=2340,
            # rejection_input_signals_test=CaseMarkers(test_case_id="194", offset=40.5), blocked by DEVOPS-95
            # rejection_journal_test=CaseMarkers(test_case_id="194", offset=40.5),  # blocked by LDS-12394
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="194", offset=40.5),
        ),
        # ===== constantSignalFilter =====
        # RejectionTestCase( blocked by DEVOPS-95
        #     name="constant_signal_flow",
        #     sensor=FLOW_TIH,
        #     expected_event="Отбраковка по постоянному сигналу",
        #     expected_signal_name=SIGNAL_FLOW,
        #     expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
        #     time_range_start_s=2400,
        #     time_range_end_s=2640,
        #     rejection_input_signals_test=CaseMarkers(test_case_id="208", offset=43),
        #     rejection_journal_test=CaseMarkers(test_case_id="208", offset=44),
        #     rejection_main_page_test=CaseMarkers(test_case_id="208", offset=41),
        #     rejection_scheme_signals_state_test=CaseMarkers(test_case_id="208", offset=42),
        # ),
        # RejectionTestCase( blocked by DEVOPS-95
        #     name="constant_signal_flow_clearance",
        #     sensor=FLOW_TIH,
        #     expected_event="Отбраковка по постоянному сигналу снята",
        #     expected_signal_name=SIGNAL_FLOW,
        #     expected_is_rejected=False,
        #     time_range_start_s=2400,
        #     time_range_end_s=2640,
        #     rejection_input_signals_test=CaseMarkers(test_case_id="208", offset=45),
        #     rejection_journal_test=CaseMarkers(test_case_id="208", offset=45),
        #     rejection_scheme_signals_state_test=CaseMarkers(test_case_id="208", offset=45),
        # ),
        # RejectionTestCase( blocked by DEVOPS-95
        #     name="constant_signal_pressure",
        #     sensor=PRESSURE_KP8_PIN,
        #     expected_event="Отбраковка по постоянному сигналу",
        #     expected_signal_name=SIGNAL_PRESSURE,
        #     expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
        #     time_range_start_s=2700,
        #     time_range_end_s=2940,
        #     rejection_input_signals_test=CaseMarkers(test_case_id="209", offset=48),
        #     rejection_journal_test=CaseMarkers(test_case_id="209", offset=49),
        #     rejection_main_page_test=CaseMarkers(test_case_id="209", offset=46),
        #     rejection_scheme_signals_state_test=CaseMarkers(test_case_id="209", offset=47),
        # ),
        # RejectionTestCase( blocked by DEVOPS-95
        #     name="constant_signal_pressure_clearance",
        #     sensor=PRESSURE_KP8_PIN,
        #     expected_event="Отбраковка по постоянному сигналу снята",
        #     expected_signal_name=SIGNAL_PRESSURE,
        #     expected_is_rejected=False,
        #     time_range_start_s=2700,
        #     time_range_end_s=2940,
        #     rejection_input_signals_test=CaseMarkers(test_case_id="209", offset=50),
        #     rejection_journal_test=CaseMarkers(test_case_id="209", offset=50),
        #     rejection_scheme_signals_state_test=CaseMarkers(test_case_id="209", offset=50),
        # ),
        # ===== rangeFilterSettings =====
        RejectionTestCase(
            name="range_upper_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3000,
            time_range_end_s=3240,
            rejection_input_signals_test=CaseMarkers(test_case_id="195", offset=53),
            rejection_journal_test=CaseMarkers(test_case_id="195", offset=54),
            rejection_main_page_test=CaseMarkers(test_case_id="195", offset=51),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="195", offset=52),
        ),
        RejectionTestCase(
            name="range_upper_flow_clearance",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону снята",
            expected_signal_name=SIGNAL_FLOW,
            expected_is_rejected=False,
            time_range_start_s=3000,
            time_range_end_s=3240,
            # rejection_input_signals_test=CaseMarkers(test_case_id="195", offset=55.8), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="195", offset=55.8),
            # rejection_scheme_signals_state_test=CaseMarkers(test_case_id="195", offset=55.8), blocked by DEVOPS-95
        ),
        RejectionTestCase(
            name="range_lower_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3300,
            time_range_end_s=3540,
            rejection_input_signals_test=CaseMarkers(test_case_id="197", offset=58),
            rejection_journal_test=CaseMarkers(test_case_id="197", offset=59),
            rejection_main_page_test=CaseMarkers(test_case_id="197", offset=56),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="197", offset=57),
        ),
        RejectionTestCase(
            name="range_lower_flow_clearance",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону снята",
            expected_signal_name=SIGNAL_FLOW,
            expected_is_rejected=False,
            time_range_start_s=3300,
            time_range_end_s=3540,
            # rejection_input_signals_test=CaseMarkers(test_case_id="197", offset=60.8), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="197", offset=60.8),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="197", offset=60.8),
        ),
        RejectionTestCase(
            name="range_upper_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3600,
            time_range_end_s=3840,
            rejection_input_signals_test=CaseMarkers(test_case_id="196", offset=63),
            rejection_journal_test=CaseMarkers(test_case_id="196", offset=64),
            rejection_main_page_test=CaseMarkers(test_case_id="196", offset=61),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="196", offset=62),
        ),
        RejectionTestCase(
            name="range_upper_pressure_clearance",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=3600,
            time_range_end_s=3840,
            # rejection_input_signals_test=CaseMarkers(test_case_id="196", offset=65.8), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="196", offset=65.8),
            # rejection_scheme_signals_state_test=CaseMarkers(test_case_id="196", offset=65.8), blocked by DEVOPS-95
        ),
        RejectionTestCase(
            name="range_lower_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3900,
            time_range_end_s=4140,
            rejection_input_signals_test=CaseMarkers(test_case_id="198", offset=68),
            rejection_journal_test=CaseMarkers(test_case_id="198", offset=69),
            rejection_main_page_test=CaseMarkers(test_case_id="198", offset=66),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="198", offset=67),
        ),
        RejectionTestCase(
            name="range_lower_pressure_clearance",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону снята",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_is_rejected=False,
            time_range_start_s=3900,
            time_range_end_s=4140,
            # rejection_input_signals_test=CaseMarkers(test_case_id="198", offset=71), blocked by DEVOPS-95
            rejection_journal_test=CaseMarkers(test_case_id="198", offset=71),
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="198", offset=71),
        ),
    ],
)
