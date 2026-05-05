"""
Конфигурация тестового набора is_rejected_regress

Особенности набора:
- Проверка отбраковки сигналов с датчиков давления и расходомеров
- Типы отбраковки: empty, quality, VTOR, nearbySensors,
  diagnosticInfo, constantSignal, range
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

# Из-за расхождений в данных и результатах работы бэка сдвинул все отбраковки на 1 минуту вперед по времени
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
            time_range_end_s=240,  # 287 - снята
            rejection_input_signals_test=CaseMarkers(test_case_id="189", offset=3),
            # Проверка отбраковки датчика AK.CHTN.NPS_KRIM_P.UZR_1.Vmom (id=30157) Ожидаемый результат:
            # isRejected = True Фактический результат: isRejected = False
            rejection_main_page_test=CaseMarkers(test_case_id="189", offset=3),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="189", offset=3),
            # Проверка isRejected для AK.CHTN.NPS_KRIM_P.UZR_1.Vmom (id=30157) Ожидаемый результат:
            # isRejected = True Фактический результат: isRejected = False
        ),
        RejectionTestCase(
            name="empty_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по отсутствию значения",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.EMPTY,
            time_range_start_s=0,
            time_range_end_s=540,  # 581
            rejection_input_signals_test=CaseMarkers(test_case_id="190", offset=4),  # passed
            rejection_main_page_test=CaseMarkers(test_case_id="190", offset=6),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="190", offset=5),  # passed
        ),
        # ===== qualityFilterSettings =====
        RejectionTestCase(
            name="quality_flow",
            sensor=FLOW_KRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=600,  # 668
            time_range_end_s=840,  # 910
            rejection_input_signals_test=CaseMarkers(test_case_id="191", offset=12),
            # Проверка отбраковки датчика AK.CHTN.NPS_KRIM_P.UZR_1.Vmom (id=30157) Ожидаемый результат:
            # isRejected = True Фактический результат: isRejected = False
            rejection_journal_test=CaseMarkers(test_case_id="191", offset=15),  # passed
            rejection_main_page_test=CaseMarkers(test_case_id="191", offset=14),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="191", offset=13),
            # Проверка isRejected для AK.CHTN.NPS_KRIM_P.UZR_1.Vmom (id=30157) Ожидаемый результат:
            # isRejected = True Фактический результат: isRejected = False
        ),
        RejectionTestCase(
            name="quality_pressure",
            sensor=PRESSURE_VELKRIM,
            expected_event="Отбраковка по качеству",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.QUALITY,
            time_range_start_s=900,  # 941 сек
            time_range_end_s=1140,  # 1181 сек
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=17),
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <qualityRejection (1)>, but was not.
            rejection_journal_test=CaseMarkers(test_case_id="", offset=20),  # passed
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=19),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=18),
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <qualityRejection (1)>, but was not.
        ),
        # ===== vtorFilterSettings =====
        RejectionTestCase(
            name="vtor_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по ВТОР сигналу",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=1200,  # 1231 sec
            time_range_end_s=1440,  # 1481 sec
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=22),  # fail
            # [1, {}, None, 'InputSignalsContent',
            # [{'replyStatus': 200, 'replyErrors': None, 'replyContent': {'tuId': 3, 'inputSignals': []}}], []]
            rejection_journal_test=CaseMarkers(test_case_id="", offset=25),  # fail - пришло на 6 8 сек позже диапазона
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=24),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=23),  # fail
            # Failed: Сигнал с id=30145 (AK.CHTN.NPS_TIH_5.UZR_1.Vmom) не найден среди 2363 полученных сигналов
        ),
        RejectionTestCase(
            name="vtor_pressure",
            sensor=PRESSURE_KP7,
            expected_event="Отбраковка по ВТОР сигналу",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.VTOR,
            time_range_start_s=1500,  # 1541 sec
            time_range_end_s=1740,  # 1781 sec
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=27),
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <VTORRejection (128)>
            rejection_journal_test=CaseMarkers(test_case_id="", offset=30),  # должно пофикситься
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=29),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=28),
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <VTORRejection (128)>
        ),
        # ===== nearbySensorsFilterSettings =====
        RejectionTestCase(
            name="nearby_pressure_pin",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по разнице показаний СИ давления на КП",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=1800,  # 1870 sec
            time_range_end_s=2040,  # 2083 sec
            rejection_input_signals_test=CaseMarkers(test_case_id="192", offset=32),
            #  Проверка rejection.criteriaNames для AK.CHTN.LU_TIHVEL.KP_8.SW_8-3.Pin (id=31439)
            #  Ожидаемый результат: criteriaNames = nearbyRejection (256) Фактический результат:
            #  criteriaNames = emptyRejection (4)
            rejection_journal_test=CaseMarkers(test_case_id="192", offset=35),  # passed
            rejection_main_page_test=CaseMarkers(test_case_id="192", offset=34),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="192", offset=33),
            # Проверка rejection.criteriaNames для AK.CHTN.LU_TIHVEL.KP_8.SW_8-3.Pin (id=31439)
            # Ожидаемый результат: criteriaNames = nearbyRejection (256) Фактический результат:
            # criteriaNames = emptyRejection (4)
        ),
        RejectionTestCase(
            name="nearby_pressure_pout",  # ставлю время 4 минуты раньше чем в описании данных
            sensor=PRESSURE_KP8_POUT,
            expected_event="Отбраковка по разнице показаний СИ давления на КП",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.NEARBY,
            time_range_start_s=2100,  # first 1870 sec | second 2770 sec
            time_range_end_s=2340,  # first 2083 sec | second 3084 sec
            rejection_input_signals_test=CaseMarkers(test_case_id="193", offset=32),  # Кривой временной диапазон
            rejection_journal_test=CaseMarkers(
                test_case_id="193", offset=35
            ),  # failed должно пофиксится из-за end по datetime
            rejection_main_page_test=CaseMarkers(test_case_id="193", offset=34),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="193", offset=33),  # Кривой временной диапазон
        ),
        # ===== diagnosticInfoFilterSettings =====
        RejectionTestCase(
            name="diagnostic_info_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по диагностической информации",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.DIAGNOSTIC_INFO,
            time_range_start_s=2100,  # 2153 сек
            time_range_end_s=2340,  # 3042 сек
            rejection_input_signals_test=CaseMarkers(test_case_id="194", offset=37),
            # [1, {}, None, 'InputSignalsContent', [{'replyStatus': 200, 'replyErrors': None, 'replyContent':
            # {'tuId': 3, 'inputSignals': []}}], []]
            rejection_journal_test=CaseMarkers(test_case_id="194", offset=40),  # тут заведена бага LDS-12394
            rejection_main_page_test=CaseMarkers(test_case_id="194", offset=39),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="194", offset=38),
            # Failed: Сигнал с id=30145 (AK.CHTN.NPS_TIH_5.UZR_1.Vmom) не найден среди 2363 полученных сигналов
        ),
        # ===== constantSignalFilter =====
        RejectionTestCase(
            name="constant_signal_flow",  # ставлю время 3 минуты позже чем в описании данных
            sensor=FLOW_TIH,
            expected_event="Отбраковка по постоянному сигналу",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
            time_range_start_s=2400,  # 2581 сек
            time_range_end_s=2640,  # 2682 сек
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=44),
            # [1, {}, None, 'InputSignalsContent', [{'replyStatus': 200, 'replyErrors': None, 'replyContent':
            # {'tuId': 3, 'inputSignals': []}}], []]
            rejection_journal_test=CaseMarkers(test_case_id="", offset=45),  # pass
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=44),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=44),
            # Failed: Сигнал с id=30145 (AK.CHTN.NPS_TIH_5.UZR_1.Vmom) не найден среди 2363 полученных сигналов
        ),
        RejectionTestCase(
            name="constant_signal_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по постоянному сигналу",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.CONSTANT_SIGNAL,
            time_range_start_s=2700,  # 2770=nearby 2950=constant_signal
            time_range_end_s=2940,  # 2984=nearby=constant_signal
            rejection_input_signals_test=CaseMarkers(test_case_id="", offset=47),
            # также отбраковка пришла очень поздно и не попала в диапазон журнала
            rejection_journal_test=CaseMarkers(
                test_case_id="", offset=50
            ),  # Отбраковка одновременно приосходит и по nearby и по constant_signal,
            # также отбраковка пришла очень поздно и не попала в диапазон журнала
            rejection_main_page_test=CaseMarkers(test_case_id="", offset=49),  # passed
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="", offset=48),
            # также отбраковка пришла очень поздно и не попала в диапазон журнала
        ),
        # ===== rangeFilterSettings =====
        RejectionTestCase(
            name="range_upper_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3000,  # 3041
            time_range_end_s=3240,  # 3284
            rejection_input_signals_test=CaseMarkers(test_case_id="195", offset=52),
            # [1, {}, None, 'InputSignalsContent', [{'replyStatus': 200, 'replyErrors': None, 'replyContent':
            # {'tuId': 3, 'inputSignals': []}}], []]
            rejection_journal_test=CaseMarkers(test_case_id="195", offset=55),  # pass
            rejection_main_page_test=CaseMarkers(test_case_id="195", offset=54),  # pass
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="195", offset=53),
            # Failed: Сигнал с id=30145 (AK.CHTN.NPS_TIH_5.UZR_1.Vmom) не найден среди 2363 полученных сигналов
        ),
        RejectionTestCase(
            name="range_lower_flow",
            sensor=FLOW_TIH,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_FLOW,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3300,  # 3359
            time_range_end_s=3540,  # 3581
            rejection_input_signals_test=CaseMarkers(test_case_id="197", offset=57),
            # [1, {}, None, 'InputSignalsContent', [{'replyStatus': 200, 'replyErrors': None, 'replyContent':
            # {'tuId': 3, 'inputSignals': []}}], []]
            rejection_journal_test=CaseMarkers(test_case_id="197", offset=60),  # pass
            rejection_main_page_test=CaseMarkers(test_case_id="197", offset=59),  # pass
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="197", offset=58),
            # Failed: Сигнал с id=30145 (AK.CHTN.NPS_TIH_5.UZR_1.Vmom) не найден среди 2363 полученных сигналов
        ),
        RejectionTestCase(
            name="range_upper_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3600,  # по факту 3641 сек
            time_range_end_s=3840,  # по факту 3883 сек
            rejection_input_signals_test=CaseMarkers(test_case_id="196", offset=62),  # fail
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <rangeRejection (2)>
            rejection_journal_test=CaseMarkers(test_case_id="196", offset=65),  # pass
            rejection_main_page_test=CaseMarkers(test_case_id="196", offset=64),  # pass
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="196", offset=63),  # fail
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <rangeRejection (2)>
        ),
        RejectionTestCase(
            name="range_lower_pressure",
            sensor=PRESSURE_KP8_PIN,
            expected_event="Отбраковка по допустимому диапазону",
            expected_signal_name=SIGNAL_PRESSURE,
            expected_criteria_names=RejectionCriteria.RANGE,
            time_range_start_s=3900,  # 3943
            time_range_end_s=4140,  # 4183
            rejection_input_signals_test=CaseMarkers(test_case_id="198", offset=67),  # fail
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <rangeRejection (2)>
            rejection_journal_test=CaseMarkers(test_case_id="198", offset=70),  # pass
            rejection_main_page_test=CaseMarkers(test_case_id="198", offset=69),  # pass
            rejection_scheme_signals_state_test=CaseMarkers(test_case_id="198", offset=68),  # fail
            # Фактический результат: criteriaNames = emptyRejection (4)] Expected <emptyRejection (4)>
            # to be equal to <rangeRejection (2)>
        ),
    ],
)
