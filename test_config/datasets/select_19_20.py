"""
Конфигурация тестового набора Select_19_20_tn3_75_181km_649 (две утечки)

Особенности набора:
- Две утечки с разными координатами и временными интервалами
- Первая утечка: 75 км, 648.8 м³, интервал 2460 с (~41 мин)
- Вторая утечка: 181 км, 648.8 м³, интервал 3300 с (~55 мин)
- Интенсивность утечки 20,4%
- Допустимое время обнаружения 6 минут
"""

from constants.enums import TU, ConfirmationStatus, LdsStatus, ReservedType, StationaryStatus
from test_config.models_for_tests import CaseMarkers, DiagnosticAreaStatusConfig, LeakTestConfig, SuiteConfig

# ===== Константы набора =====
SUITE_NAME = "Select_19_20_tn3_75_181km_649"
SUITE_DATA_ID = 66
ARCHIVE_NAME = f"{SUITE_NAME}.tar.gz"

# Технологический участок
TECHNOLOGICAL_UNIT = TU.TIKHORETSK_NOVOROSSIYSK_3

# ===== Первая утечка =====
LEAK_1_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых"
LEAK_1_DIAGNOSTIC_AREA_ID = 2
LEAK_1_CONTROL_SITE_ID = 6032
LEAK_1_LINEAR_PART_ID = 407
LEAK_1_COORDINATE_METERS = 75000.0
LEAK_1_VOLUME_M3 = 648.8
LEAK_1_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_1_START_INTERVAL_SECONDS = 2460  # ~41 минута
LEAK_1_OUTPUT_DELAY_SECONDS = 960

# ===== Вторая утечка =====
LEAK_2_DIAGNOSTIC_AREA_NAME = "Т-Н-3.НПС-3 «Нововеличковская».УЗР вых - Т-Н-3.НПС-2 «Крымская».УЗР вх"
LEAK_2_DIAGNOSTIC_AREA_ID = 3
LEAK_2_CONTROL_SITE_ID = 6148
LEAK_2_LINEAR_PART_ID = 408
LEAK_2_COORDINATE_METERS = 181000.0
LEAK_2_VOLUME_M3 = 648.8
LEAK_2_ALLOWED_TIME_DIFF_SECONDS = 360  # 6 минут
LEAK_2_START_INTERVAL_SECONDS = 3300  # ~55 минут
LEAK_2_OUTPUT_DELAY_SECONDS = 150

# ID диагностических участков для проверки статусов
IN_NEIGHBOR_DIAGNOSTIC_AREA_ID = 1
OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID = 3


# ===== Конфигурация набора =====
SELECT_19_20_CONFIG = SuiteConfig(
    # ----- Метаданные -----
    suite_name=SUITE_NAME,
    suite_data_id=SUITE_DATA_ID,
    archive_name=ARCHIVE_NAME,
    technological_unit=TECHNOLOGICAL_UNIT,
    # ----- Ожидаемый статус стационара -----
    expected_stationary_status=StationaryStatus.STATIONARY.value,
    # ===== БАЗОВЫЕ ТЕСТЫ =====
    basic_info_test=CaseMarkers(test_case_id="1", offset=1),
    journal_info_test=CaseMarkers(test_case_id="2", offset=5),
    lds_status_initialization_test=CaseMarkers(test_case_id="29", offset=5),
    main_page_info_test=CaseMarkers(test_case_id="3", offset=7),
    # ----- Дополнительный тест на нестационар (специфика двух утечек) -----
    main_page_info_unstationary_test=CaseMarkers(test_case_id="79", offset=40),
    mask_signal_test=CaseMarkers(test_case_id="32", offset=8),
    lds_status_initialization_out_test=CaseMarkers(test_case_id="30", offset=30),
    lds_status_during_leak_test=CaseMarkers(test_case_id="80", offset=47),
    # ===== КОНФИГУРАЦИЯ СТАТУСОВ СОУ ВО ВРЕМЯ УТЕЧКИ =====
    lds_status_during_leak_config=DiagnosticAreaStatusConfig(
        diagnostic_area_id=LEAK_1_DIAGNOSTIC_AREA_ID,
        expected_lds_status=LdsStatus.INITIALIZATION.value,
        in_neighbor_id=IN_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        in_neighbor_status=LdsStatus.DEGRADATION.value,
        out_neighbor_id=OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID,
        out_neighbor_status=LdsStatus.DEGRADATION.value,
    ),
    # ===== Конфигурации утечек =====
    leaks=[
        # ===== ПЕРВАЯ УТЕЧКА (75 км) =====
        LeakTestConfig(
            # ----- Идентификаторы -----
            diagnostic_area_name=LEAK_1_DIAGNOSTIC_AREA_NAME,
            diagnostic_area_id=LEAK_1_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_1_CONTROL_SITE_ID,
            linear_part_id=LEAK_1_LINEAR_PART_ID,
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_1_COORDINATE_METERS,
            volume_m3=LEAK_1_VOLUME_M3,
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_1_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_1_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_1_OUTPUT_DELAY_SECONDS,
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.SERVICEABLE.value,
            expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
            expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW.value,
            expected_leak_status=ConfirmationStatus.CONFIRMED.value,
            # ----- Тест LeaksContent (первая утечка) -----
            leaks_content_test=CaseMarkers(test_case_id="72", offset=47),
            # ----- Тест AllLeaksInfo (первая утечка) -----
            all_leaks_info_test=CaseMarkers(test_case_id="66", offset=47),
            # ----- Тест TuLeaksInfo (первая утечка) -----
            tu_leaks_info_test=CaseMarkers(test_case_id="70", offset=47),
            # ----- Тест AcknowledgeLeak (первая утечка) -----
            acknowledge_leak_test=CaseMarkers(test_case_id="74", offset=62),
            # ----- Тест OutputSignals (первая утечка) -----
            output_signals_test=CaseMarkers(test_case_id="77", offset=63),
        ),
        # ===== ВТОРАЯ УТЕЧКА (181 км) =====
        LeakTestConfig(
            # ----- Идентификаторы -----
            diagnostic_area_name=LEAK_2_DIAGNOSTIC_AREA_NAME,
            diagnostic_area_id=LEAK_2_DIAGNOSTIC_AREA_ID,
            control_site_id=LEAK_2_CONTROL_SITE_ID,
            linear_part_id=LEAK_2_LINEAR_PART_ID,
            # ----- Параметры утечки -----
            coordinate_meters=LEAK_2_COORDINATE_METERS,
            volume_m3=LEAK_2_VOLUME_M3,
            # ----- Временные интервалы -----
            leak_start_interval_seconds=LEAK_2_START_INTERVAL_SECONDS,
            allowed_time_diff_seconds=LEAK_2_ALLOWED_TIME_DIFF_SECONDS,
            output_test_delay_seconds=LEAK_2_OUTPUT_DELAY_SECONDS,
            # ----- Ожидаемые статусы -----
            expected_lds_status=LdsStatus.DEGRADATION.value,
            expected_stationary_status=StationaryStatus.UNSTATIONARY.value,
            expected_algorithm_type=ReservedType.UNSTATIONARY_FLOW.value,
            expected_leak_status=ConfirmationStatus.CONFIRMED.value,
            # ----- Тест LeaksContent (вторая утечка) -----
            leaks_content_test=CaseMarkers(test_case_id="73", offset=61),
            # ----- Тест AllLeaksInfo (вторая утечка) -----
            all_leaks_info_test=CaseMarkers(test_case_id="69", offset=61),
            # ----- Тест TuLeaksInfo (вторая утечка) -----
            tu_leaks_info_test=CaseMarkers(test_case_id="71", offset=61.0),
            # ----- Тест AcknowledgeLeak (вторая утечка) -----
            acknowledge_leak_test=CaseMarkers(test_case_id="75", offset=62.5),
            # ----- Тест OutputSignals (вторая утечка) -----
            output_signals_test=CaseMarkers(test_case_id="78", offset=63.5),
        ),
    ],
)


# Экспортируем дополнительные константы для специфичных проверок
class Select19Constants:
    """Дополнительные константы для select_19_20"""

    CONFIRMATION_STATUS = ConfirmationStatus
    RESERVED_TYPE = ReservedType
