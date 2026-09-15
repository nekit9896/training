"""
Конфигурация тестового набора Status_regress_unstationary_block_valves_status

Особенности набора:
- Режим МТ Нестационар
- Причина МТ: Полное или частичное открытие/закрытие задвижки
- Проверка режимов работы МТ
- Проверка причин режимов работы МТ
- Старт данных 19.03.2026 13:14:00.000
- Частичное открытие задвижек AK.CHTN.NPS_TIH_5.SW_0-3-3.Status ~ 13:24
- Начало нестационара примерно в 13:24, окончание примерно 13:31
- Частичное закрытие задвижек AK.CHTN.NPS_TIH_5.SW_0-1-3.Status ~ 13:34
- Начало нестационара примерно в 13:34, окончание примерно 13:41
"""

from constants.enums import TU, AdminTU, MeasureConversionRule, StationaryReason, StationaryStatus, UnStationaryReason
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, StationaryStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Status_regress_unstationary_block_valves_status"
SUITE_DATA_ID = 35
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

DIAGNOSTIC_AREA_2_PIPE_ID = 1463
DIAGNOSTIC_AREA_3_PIPE_ID = 474
DIAGNOSTIC_AREA_5_PIPE_ID = 1478
CONTROL_POINTS = [
    "ЗА 105-3 - ЗА 129-3",
    "ЗА 180-3 - ЗА 207-3",
]

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# Название МН
MAIN_PIPELINE = "МН Тихорецк-Новороссийск-3"


# ===== Конфигурация набора =====
STATUS_REGRESS_UNSTATIONARY_BLOCK_VALVES_STATUS_CONFIG = StationaryStatusConfig(
    # ----- Метаданные -----
    ost_name=TestConst.CHTN_OST_NAME,
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    main_pipeline=MAIN_PIPELINE,
    technological_unit=TECHNOLOGICAL_UNIT,
    measure_conversion_rules=MeasureConversionRule.KG_CM_MEASURE,
    # ===== LDS Configurator =====
    use_lds_configurator=True,
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST,
    status_unstationary_cold_start_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.UNSTATIONARY, UnStationaryReason.COLD_START),
    ),
    status_unstationary_switch_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.UNSTATIONARY, UnStationaryReason.CHANGING_BLOCK_VALVES_STATUS),
    ),
    status_stationary_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.STATIONARY, StationaryReason.PRESSURE_AND_FLOW_MOVING_AVERAGES_MEET_CRITERIA),
    ),
    journal_unstationary_cold_start_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(
            StationaryStatus.UNSTATIONARY.report_text,
            UnStationaryReason.COLD_START.report_text,
        ),
    ),
    journal_unstationary_switch_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(
            StationaryStatus.UNSTATIONARY.report_text,
            UnStationaryReason.CHANGING_BLOCK_VALVES_STATUS.report_text,
        ),
    ),
    journal_stationary_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(
            StationaryStatus.STATIONARY.report_text,
            StationaryReason.PRESSURE_AND_FLOW_MOVING_AVERAGES_MEET_CRITERIA.report_text,
        ),
    ),
    # ===== ТЕСТЫ =====
    stationary_status_basic_info_test=CaseMarkers(test_case_id="44", offset=2),
    common_scheme_cold_start_test=CaseMarkers(test_case_id="42", offset=2),
    journal_cold_start_test=CaseMarkers(test_case_id="43", offset=2),
    main_page_info_cold_start_test=CaseMarkers(test_case_id="39", offset=2),
    output_signals_cold_start_test=CaseMarkers(test_case_id="41", offset=2),
    common_scheme_stationary_after_cold_test=CaseMarkers(test_case_id="42", offset=7),
    journal_stationary_after_cold_test=CaseMarkers(test_case_id="43", offset=7),
    main_page_info_stationary_after_cold_test=CaseMarkers(test_case_id="39", offset=7),
    output_signals_stationary_after_cold_test=CaseMarkers(test_case_id="41", offset=7),
    common_scheme_switch_on_test=CaseMarkers(test_case_id="35", offset=14),
    journal_switch_on_test=CaseMarkers(test_case_id="43", offset=14),
    main_page_info_switch_on_test=CaseMarkers(test_case_id="39", offset=14),
    output_signals_switch_on_test=CaseMarkers(test_case_id="41", offset=14),
    common_scheme_stationary_after_switch_on_test=CaseMarkers(test_case_id="42", offset=29),
    journal_stationary_after_switch_on_test=CaseMarkers(test_case_id="43", offset=29),
    main_page_info_stationary_after_switch_on_test=CaseMarkers(test_case_id="39", offset=29),
    output_signals_stationary_after_switch_on_test=CaseMarkers(test_case_id="41", offset=29),
    common_scheme_switch_off_test=CaseMarkers(test_case_id="35", offset=24),
    journal_switch_off_test=CaseMarkers(test_case_id="43", offset=24),
    main_page_info_switch_off_test=CaseMarkers(test_case_id="39", offset=24),
    output_signals_switch_off_test=CaseMarkers(test_case_id="41", offset=24),
    common_scheme_stationary_after_switch_off_test=CaseMarkers(test_case_id="42", offset=36),
    journal_stationary_after_switch_off_test=CaseMarkers(test_case_id="43", offset=36),
    main_page_info_stationary_after_switch_off_test=CaseMarkers(test_case_id="39", offset=36),
    output_signals_stationary_after_switch_off_test=CaseMarkers(test_case_id="41", offset=36),
)
