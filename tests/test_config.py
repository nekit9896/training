"""
Конфигурации тестовых наборов данных для smoke-тестов СОУ.

Этот модуль содержит конфигурации конкретных наборов данных.
Структуры данных определены в constants/test_dataclasses.py

Для добавления нового набора данных:
1. Создайте новый экземпляр TestDataConfig
2. Добавьте его в TEST_CONFIGS в конце файла


"""

from constants.test_dataclasses import (LeakConfig, NeighborArea, TestCaseIds,
                                        TestDataConfig, TestOffsets)
from constants.test_enums import (ConfirmationStatus, LdsStatus, ReservedType,
                                  StationaryStatus)

# ============================================================================
#                    КОНФИГУРАЦИИ ТЕСТОВЫХ НАБОРОВ
# ============================================================================


# --- Select 17: TN3, 75км, 416 м³/ч ---
SELECT_17_CONFIG = TestDataConfig(
    suite_name="Select_17_tn3_75km_417",
    suite_data_id=42,
    arch_name="Select_17_tn3_75km_417.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    leak=LeakConfig(
        coordinate_m=75000.0,
        volume_m3=416.0,
        time_tolerance_s=1440,
        diagnostic_area_id=2,
        linear_part_id=407,
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.UNSTATIONARY,
        neighbor_areas=[
            NeighborArea(id=1, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=3, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name=None,
        control_site_id=None,
        expected_confirmation_status=None,
        expected_type=None,
    ),
    leak_2=None,
    offsets=TestOffsets(
        basic_info=1,
        journal_info=5,
        lds_status_initialization=5,
        main_page_info=7,
        mask_signal_msg=8,
        lds_status_initialization_out=30,
        all_leaks_info=61,
        tu_leaks_info=63,
        lds_status_during_leak=64.5,
        acknowledge_leak_info=66,
        output_signals=66,
        main_page_info_unstationary=None,
        all_leaks_info_leak_2=None,
        tu_leaks_info_leak_2=None,
        output_signals_leak_2=None,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="59",
        main_page_info="12",
        mask_signal_msg="62",
        lds_status_initialization_out="61",
        all_leaks_info="42",
        tu_leaks_info="57",
        lds_status_during_leak="60",
        acknowledge_leak_info="58",
        output_signals="63",
        main_page_info_unstationary="0",
        all_leaks_info_leak_2="0",
        tu_leaks_info_leak_2="0",
        output_signals_leak_2="0",
    ),
    expected_stationary=StationaryStatus.STATIONARY,
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# --- Select 25: TN3, 6км, 56 м³/ч ---
SELECT_25_CONFIG = TestDataConfig(
    suite_name="Select_25_tn3_6km_56",
    suite_data_id=20,
    arch_name="Select25.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    leak=LeakConfig(
        coordinate_m=5400.0,
        volume_m3=57.0,
        time_tolerance_s=1440,
        diagnostic_area_id=3,
        linear_part_id=407,
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.STATIONARY,
        neighbor_areas=[
            NeighborArea(id=2, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=4, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=6, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name=None,
        control_site_id=None,
        expected_confirmation_status=None,
        expected_type=None,
    ),
    leak_2=None,
    offsets=TestOffsets(
        basic_info=5,
        journal_info=5,
        lds_status_initialization=None,  # Отключен
        main_page_info=7,
        mask_signal_msg=None,  # Отключен
        lds_status_initialization_out=None,  # Отключен
        all_leaks_info=59,
        tu_leaks_info=59,
        lds_status_during_leak=None,  # Отключен
        acknowledge_leak_info=61,
        output_signals=61,
        main_page_info_unstationary=None,
        all_leaks_info_leak_2=None,
        tu_leaks_info_leak_2=None,
        output_signals_leak_2=None,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="0",
        main_page_info="3",
        mask_signal_msg="0",
        lds_status_initialization_out="0",
        all_leaks_info="4",
        tu_leaks_info="5",
        lds_status_during_leak="0",
        acknowledge_leak_info="6",
        output_signals="7",
        main_page_info_unstationary="0",
        all_leaks_info_leak_2="0",
        tu_leaks_info_leak_2="0",
        output_signals_leak_2="0",
    ),
    expected_stationary=StationaryStatus.STATIONARY,
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# --- Select 4: TN3, 215км, 113 м³/ч (остановленная перекачка) ---
SELECT_4_CONFIG = TestDataConfig(
    suite_name="Select_4_tn3_215km_113",
    suite_data_id=43,
    arch_name="Select_4_tn3_215km_113.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    leak=LeakConfig(
        coordinate_m=215000.0,
        volume_m3=113.6,
        time_tolerance_s=1440,
        diagnostic_area_id=2,
        linear_part_id=407,
        expected_lds_status=LdsStatus.DEGRADATION,  # Особенность: статус DEGRADATION
        expected_stationary_status=StationaryStatus.STOPPED,
        neighbor_areas=[
            NeighborArea(id=1, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=3, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name=None,
        control_site_id=None,
        expected_confirmation_status=None,
        expected_type=None,
    ),
    leak_2=None,
    offsets=TestOffsets(
        basic_info=5,
        journal_info=5,
        lds_status_initialization=5,
        main_page_info=7,
        mask_signal_msg=8,
        lds_status_initialization_out=30,
        all_leaks_info=59,
        tu_leaks_info=59,
        lds_status_during_leak=59.5,
        acknowledge_leak_info=60,
        output_signals=61,
        main_page_info_unstationary=None,
        all_leaks_info_leak_2=None,
        tu_leaks_info_leak_2=None,
        output_signals_leak_2=None,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="52",
        main_page_info="44",
        mask_signal_msg="45",
        lds_status_initialization_out="46",
        all_leaks_info="43",
        tu_leaks_info="48",
        lds_status_during_leak="49",
        acknowledge_leak_info="50",
        output_signals="51",
        main_page_info_unstationary="0",
        all_leaks_info_leak_2="0",
        tu_leaks_info_leak_2="0",
        output_signals_leak_2="0",
    ),
    expected_stationary=StationaryStatus.STOPPED,  # Особенность: остановленная перекачка
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# --- Select 6: TN3, 56км, 113 м³/ч ---
SELECT_6_CONFIG = TestDataConfig(
    suite_name="Select_6_tn3_56km_113",
    suite_data_id=4,
    arch_name="Select_6_tn3_56km_113.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    leak=LeakConfig(
        coordinate_m=56000.0,
        volume_m3=113.6,
        time_tolerance_s=1440,
        diagnostic_area_id=2,
        linear_part_id=407,
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.STATIONARY,
        neighbor_areas=[
            NeighborArea(id=1, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=3, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name=None,
        control_site_id=None,
        expected_confirmation_status=None,
        expected_type=None,
    ),
    leak_2=None,
    offsets=TestOffsets(
        basic_info=5,
        journal_info=5,
        lds_status_initialization=7,
        main_page_info=7,
        mask_signal_msg=8,
        lds_status_initialization_out=30,
        all_leaks_info=59,
        tu_leaks_info=59,
        lds_status_during_leak=59.5,
        acknowledge_leak_info=60,
        output_signals=61,
        main_page_info_unstationary=None,
        all_leaks_info_leak_2=None,
        tu_leaks_info_leak_2=None,
        output_signals_leak_2=None,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="29",
        main_page_info="3",
        mask_signal_msg="32",
        lds_status_initialization_out="30",
        all_leaks_info="4",
        tu_leaks_info="5",
        lds_status_during_leak="31",
        acknowledge_leak_info="6",
        output_signals="33",
        main_page_info_unstationary="0",
        all_leaks_info_leak_2="0",
        tu_leaks_info_leak_2="0",
        output_signals_leak_2="0",
    ),
    expected_stationary=StationaryStatus.STATIONARY,
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# --- Select 7: TN3, 130км, 113 м³/ч ---
SELECT_7_CONFIG = TestDataConfig(
    suite_name="Select_7_tn3_130km_113",
    suite_data_id=13,
    arch_name="Select_7_tn3_130km_113.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    leak=LeakConfig(
        coordinate_m=130000.0,
        volume_m3=113.6,
        time_tolerance_s=1440,
        diagnostic_area_id=3,
        linear_part_id=408,
        expected_lds_status=LdsStatus.SERVICEABLE,
        expected_stationary_status=StationaryStatus.STATIONARY,
        neighbor_areas=[
            NeighborArea(id=2, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=4, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=6, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name=None,
        control_site_id=None,
        expected_confirmation_status=None,
        expected_type=None,
    ),
    leak_2=None,
    offsets=TestOffsets(
        basic_info=5,
        journal_info=5,
        lds_status_initialization=5,
        main_page_info=7,
        mask_signal_msg=8,
        lds_status_initialization_out=30,
        all_leaks_info=59,
        tu_leaks_info=59,
        lds_status_during_leak=59.5,
        acknowledge_leak_info=60,
        output_signals=61,
        main_page_info_unstationary=None,
        all_leaks_info_leak_2=None,
        tu_leaks_info_leak_2=None,
        output_signals_leak_2=None,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="34",
        main_page_info="12",
        mask_signal_msg="37",
        lds_status_initialization_out="35",
        all_leaks_info="13",
        tu_leaks_info="14",
        lds_status_during_leak="36",
        acknowledge_leak_info="15",
        output_signals="38",
        main_page_info_unstationary="0",
        all_leaks_info_leak_2="0",
        tu_leaks_info_leak_2="0",
        output_signals_leak_2="0",
    ),
    expected_stationary=StationaryStatus.STATIONARY,
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# --- Select 19/20: TN3, две утечки (75км и 181км), 649 м³/ч ---
SELECT_19_CONFIG = TestDataConfig(
    suite_name="Select_19_20_tn3_75_181km_649",
    suite_data_id=66,
    arch_name="Select_19_20_tn3_75_181km_649.tar.gz",
    tu_id=3,
    tu_name="Тихорецк-Новороссийск-3",
    # Первая утечка
    leak=LeakConfig(
        coordinate_m=75000.0,
        volume_m3=648.8,
        time_tolerance_s=360,
        diagnostic_area_id=2,
        linear_part_id=407,
        expected_lds_status=LdsStatus.INITIALIZATION,  # Особенность
        expected_stationary_status=StationaryStatus.UNSTATIONARY,
        neighbor_areas=[
            NeighborArea(id=1, expected_status=LdsStatus.DEGRADATION),
            NeighborArea(id=3, expected_status=LdsStatus.DEGRADATION),
        ],
        diagnostic_area_name="Т-Н-3.НПС-5 «Тихорецкая».УЗР вых - Т-Н-3.НПС-3 «Нововеличковская».УЗР вых",
        control_site_id=6032,
        expected_confirmation_status=ConfirmationStatus.CONFIRMED,
        expected_type=ReservedType.UNSTATIONARY_FLOW,
    ),
    # Вторая утечка
    leak_2=LeakConfig(
        coordinate_m=181000.0,
        volume_m3=648.8,
        time_tolerance_s=360,
        diagnostic_area_id=3,
        linear_part_id=408,
        expected_lds_status=LdsStatus.DEGRADATION,
        expected_stationary_status=StationaryStatus.UNSTATIONARY,
        neighbor_areas=[],
        diagnostic_area_name="Т-Н-3.НПС-3 «Нововеличковская».УЗР вых - Т-Н-3.НПС-2 «Крымская».УЗР вх",
        control_site_id=6148,
        expected_confirmation_status=ConfirmationStatus.CONFIRMED,
        expected_type=ReservedType.UNSTATIONARY_FLOW,
    ),
    offsets=TestOffsets(
        basic_info=1,
        journal_info=5,
        lds_status_initialization=5,
        main_page_info=7,
        mask_signal_msg=8,
        lds_status_initialization_out=30,
        all_leaks_info=47,
        tu_leaks_info=47,
        lds_status_during_leak=47,
        acknowledge_leak_info=62,
        output_signals=63,
        main_page_info_unstationary=45,  # Дополнительный тест на нестационар
        # --- Тесты для второй утечки (181 км) ---
        all_leaks_info_leak_2=47,
        tu_leaks_info_leak_2=47,
        output_signals_leak_2=63,
    ),
    test_case_ids=TestCaseIds(
        basic_info="1",
        journal_info="2",
        lds_status_initialization="29",
        main_page_info="3",
        mask_signal_msg="32",
        lds_status_initialization_out="30",
        all_leaks_info="4",
        tu_leaks_info="5",
        lds_status_during_leak="31",
        acknowledge_leak_info="6",
        output_signals="33",
        main_page_info_unstationary="3",
        # --- Тест-кейсы для второй утечки ---
        all_leaks_info_leak_2="4",
        tu_leaks_info_leak_2="5",
        output_signals_leak_2="33",
    ),
    expected_stationary=StationaryStatus.STATIONARY,
    distance_tolerance_m=5000,
    volume_tolerance_ratio=0.2,
    precision=3,
    enabled=True,
)


# ============================================================================
#                    РЕЕСТР ВСЕХ КОНФИГУРАЦИЙ
# ============================================================================


# Список всех конфигураций для параметризации тестов
# Для добавления нового набора данных - добавьте конфигурацию сюда
TEST_CONFIGS: list[TestDataConfig] = [
    SELECT_17_CONFIG,
    SELECT_25_CONFIG,
    SELECT_4_CONFIG,
    SELECT_6_CONFIG,
    SELECT_7_CONFIG,
    SELECT_19_CONFIG,
]


def get_enabled_configs() -> list[TestDataConfig]:
    """Возвращает только включенные конфигурации"""
    return [cfg for cfg in TEST_CONFIGS if cfg.enabled]


def get_config_by_name(suite_name: str) -> TestDataConfig | None:
    """Находит конфигурацию по имени"""
    for cfg in TEST_CONFIGS:
        if cfg.suite_name == suite_name:
            return cfg
    return None
