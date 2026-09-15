"""
Конфигурация тестового набора Stationary_status_regress_stationary

Особенности набора:
- Режим МТ Стационар
- Проверка режимов работы МТ
- Проверка причин режимов работы МТ
"""

from constants.enums import TU, AdminTU, MeasureConversionRule, StationaryReason, StationaryStatus, UnStationaryReason
from constants.test_constants import BaseTN3Constants as TestConst
from test_config.models_for_tests import CaseData, CaseMarkers, StationaryStatusConfig

# ===== Константы набора =====
SUITE_NAME = "Stationary_status_regress_stationary"
SUITE_DATA_ID = 32
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
STATIONARY_STATUS_REGRESS_STATIONARY_CONFIG = StationaryStatusConfig(
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
    admin_tu=AdminTU.TIKHORETSK_NOVOROSSIYSK_3_AUTOTEST_DATA_ABSENCE_FALSE,
    status_unstationary_cold_start_test_data=CaseData(
        params={TestConst.CONTROL_POINTS_KEY: CONTROL_POINTS},
        expected_result=(StationaryStatus.UNSTATIONARY, UnStationaryReason.COLD_START),
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
    common_scheme_stationary_after_cold_test=CaseMarkers(test_case_id="32", offset=7),
    journal_stationary_after_cold_test=CaseMarkers(test_case_id="43", offset=7),
    main_page_info_stationary_after_cold_test=CaseMarkers(test_case_id="38", offset=7),
    output_signals_stationary_after_cold_test=CaseMarkers(test_case_id="41", offset=7),
)
