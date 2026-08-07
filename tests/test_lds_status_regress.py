"""

Архитектура параметризации:
- SUITE_PARAMS: тесты уровня набора (один раз на набор данных LDSStatusConfig)

Для добавления нового набора:
1. Создать файл в test_config/datasets/ с LDSStatusConfig
2. Добавить маппинг новых тестов в conftest.py -> LDS_STATUS_SUITE_LEVEL_MAPPING
3. Тесты подхватятся автоматически

Запуск:
- Все тесты: pytest tests/test_lds_status_regress.py
- Один набор: pytest tests/test_lds_status_regress.py --suites=Lds_status_regress_in_flow
- Несколько наборов: pytest tests/test_lds_status_regress.py --suites=Lds_status_regress_in_flow,Lds_status_regress_2
"""

import datetime
from typing import Any, List, Optional

import allure
import pytest

from clients.http_client import StandHttpClient
from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_LDS_STATUS_CONFIGS
from test_config.models_for_tests import CaseMarkers, LDSStatusConfig
from test_scenarios import lds_status_scenarios as scenarios
from test_scenarios import smoke_scenarios

# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====


def _get_suite_markers(config: LDSStatusConfig) -> List[pytest.MarkDecorator]:
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
    ]


def _generate_suite_params() -> List[Any]:
    """
    Генерирует параметры для тестов уровня набора данных.
    Один параметр на каждый config.
    """
    return [
        pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config))
        for config in ALL_LDS_STATUS_CONFIGS
    ]


# ===== ПАРАМЕТРЫ ДЛЯ ТЕСТОВ =====
SUITE_PARAMS: List[Any] = _generate_suite_params()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def _apply_allure_markers(test_config: CaseMarkers, tag: str, title: str, description: Optional[str] = None) -> None:
    """Применяет allure-маркеры из конфига теста."""
    if not test_config:
        pytest.skip("Не заполнена конфигурация теста: тест пропущен")
    allure.dynamic.tag(tag)
    allure.dynamic.tag("REGRESS")
    allure.dynamic.title(title)
    if description:
        allure.dynamic.description(description)


# ===== ТЕСТЫ УРОВНЯ НАБОРА =====
# Запускаются один раз для каждого config


@pytest.mark.parametrize("config", SUITE_PARAMS)
class TestSuiteScenarios:
    """
    Тесты уровня набора данных.
    Запускаются один раз для каждого конфига.
    """

    @pytest.mark.critical_stop
    def test_lds_status_basic_info(self, http_client: StandHttpClient, config: LDSStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.lds_status_basic_info_test, tag, title)
        smoke_scenarios.basic_info(http_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_init_accumulation_data(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Накопление данных
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация', по причине: 'Накопление данных'. ЭФ: Схема"
        _apply_allure_markers(
            config.init_accumulation_data_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_accumulation_data_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Инициализация\n "
                "Ожидаемая причина режима работы СОУ: Накопление данных"
            ),
        )
        test_data = config.init_accumulation_data_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_init_cold_start(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Холодный пуск
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация', по причине: 'Холодный пуск'. ЭФ: Схема"
        _apply_allure_markers(
            config.init_cold_start_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Холодный пуск"
            ),
        )
        test_data = config.init_cold_start_test_data
        await scenarios.lds_status_check_on_longest_flow_area(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_init_switching_shut_off(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Переключение запорной арматуры
        """
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Инициализация', "
            "по причине: 'Переключение запорной арматуры'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.init_switching_shut_off_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_switching_shut_off_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Инициализация\n "
                "Ожидаемая причина режима работы СОУ: Переключение запорной арматуры"
            ),
        )
        test_data = config.init_switching_shut_off_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_cold_start(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после Инициализации, по причине Холодный пуск.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после Иницализации. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_cold_start_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ после Инициализации, по причине: Холодный пуск, на показательных ДУ"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки: {config.serviceable_after_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_deg_additive_injectors_operation(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после режима Ухудшение характеристик. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_deg_additive_injectors_operation_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после режима Ухудшение характеристик, "
                "на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_deg_additive_injectors_operation_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_deg_absence_min_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после режима Ухудшение характеристик. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_deg_absence_min_pressure_sensors_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после режима Ухудшение характеристик, "
                "на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_deg_absence_min_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_deg_exceeding_distance_between_flow_meters(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после режима Ухудшение характеристик. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_deg_exceeding_distance_between_flow_meters_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после режима Ухудшение характеристик, "
                "на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_deg_exceeding_distance_between_flow_meters_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_deg_starting_pumping_out_pumps(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после режима Ухудшение характеристик. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_deg_starting_pumping_out_pumps_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после режима Ухудшение характеристик, "
                "на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_deg_starting_pumping_out_pumps_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_deg_faulty_pressure_sensors_at_pump(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' после режима Ухудшение характеристик. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_deg_faulty_pressure_sensors_at_pump_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после режима Ухудшение характеристик, "
                "на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_deg_faulty_pressure_sensors_at_pump_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_faulty(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после Инициализации, по причине выхода из Неисправности.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна', после Неисправности. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_faulty_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после Неисправности, на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки: {config.serviceable_after_faulty_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_switching_shut_off(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после Инициализации, по причине Переключение запорной арматуры.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна', после Инициализации. ЭФ: Схема"
        _apply_allure_markers(
            config.serviceable_after_switching_shut_off_test,
            tag,
            title,
            (
                "Проверка режима работы СОУ, после Инициализации по причине Переключение запорной арматуры"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки: "
                f"{config.serviceable_after_switching_shut_off_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.serviceable_all_test_data
        await scenarios.lds_status_check_on_multiple_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_additive_injectors_operation(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Наличие ПТП
        """

        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', по причине: 'Наличие ПТП'. ЭФ: Схема"
        _apply_allure_markers(
            config.deg_additive_injectors_operation_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_additive_injectors_operation_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Наличие ПТП"
            ),
        )
        test_data = config.deg_additive_injectors_operation_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_exceeding_distance_between_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: расстояние между СИ давления более 50 км
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Расстояние между СИ давления более 50 км'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_exceeding_distance_between_pressure_sensors_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_exceeding_distance_between_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Расстояние между СИ давления более 50 км"
            ),
        )
        test_data = config.deg_exceeding_distance_between_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_absence_min_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: менее 4 исправных СИ давления
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'менее 4 исправных СИ давления'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_absence_min_pressure_sensors_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_absence_min_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Ухудшение При наличии менее четырех (3, 6) исправных СИ давления "
                "на разных КП ЛЧ МТ/НПС на диагностическом участке (кроме случая нахождения трубопровода "
                "в режиме остановленной перекачки)"
            ),
        )
        test_data = config.deg_absence_min_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_faulty_pressure_sensors_at_pump_station(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Отказ СИ давления на входе/выходе НПС
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Отказ СИ давления на входе/выходе НПС'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_faulty_pressure_sensors_at_pump_station_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_faulty_pressure_sensors_at_pump_station_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ давления на входе/выходе НПС"
            ),
        )
        test_data = config.deg_faulty_pressure_sensors_at_pump_station_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_pig_sensor_passage(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: прохождение СОД
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', по причине: 'прохождение СОД'"
        _apply_allure_markers(
            config.deg_pig_sensor_passage_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.deg_pig_sensor_passage_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: прохождение СОД "
            ),
        )
        test_data = config.deg_pig_sensor_passage_test_data
        await scenarios.lds_status_check_degradation_pig_sensor_passage(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_gravity_section_pumping(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Наличие самотечного участка/участка с неполным сечением
        """
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Наличие самотечного участка/участка с неполным сечением'"
        )
        _apply_allure_markers(
            config.deg_gravity_section_pumping_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.deg_gravity_section_pumping_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Наличие самотечного участка/участка с неполным сечением "
            ),
        )
        test_data = config.deg_gravity_section_pumping_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_gravity_section_pumping_in_stopping(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Наличие самотечного участка в режиме остановленной перекачки
        """
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Наличие самотечного участка в режиме остановленной перекачки'"
        )
        _apply_allure_markers(
            config.deg_gravity_section_pumping_in_stopping_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на всей ЛЧ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_gravity_section_pumping_in_stopping_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Наличие самотечного участка в режиме остановленной перекачки "
            ),
        )
        test_data = config.deg_gravity_section_pumping_in_stopping_test_data
        await scenarios.lds_status_check_on_longest_flow_area(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_starting_pumping_out_pumps(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ и МТ
        Причина: Работа насосов откачки
        """

        tag = "CommonScheme"
        title = f"[{tag}] Проверка режимов работы СОУ и МТ, по причине: 'Работа насосов откачки'. ЭФ: Схема"
        _apply_allure_markers(
            config.deg_starting_pumping_out_pumps_test,
            tag,
            title,
            (
                f"Проверка режимов работы СОУ и МТ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_starting_pumping_out_pumps_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемый режим работы МТ: Нестационарный\n "
                "Ожидаемая причина режима работы СОУ: Работа насосов откачки"
                "Ожидаемая причина режима работы МТ: Работа насосов откачки"
            ),
        )
        test_data = config.deg_starting_pumping_out_pumps_test_data
        await scenarios.lds_and_stationary_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_exceeding_distance_between_flow_meters(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Расстояние между СИ расхода на пути перекачки более 200 км
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Расстояние между СИ расхода на пути перекачки более 200 км'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_exceeding_distance_between_flow_meters_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_exceeding_distance_between_flow_meters_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Расстояние между СИ расхода на пути перекачки более 200 км"
            ),
        )
        test_data = config.deg_exceeding_distance_between_flow_meters_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_init_exiting_faulty(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Выход СОУ из режима «Неисправна»
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Инициализация', "
            "по причине: 'Выход СОУ из режима «Неисправна»'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.init_exiting_faulty_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_exiting_faulty_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Инициализация\n "
                "Ожидаемая причина режима работы СОУ: Выход СОУ из режима «Неисправна»"
            ),
        )
        test_data = config.init_exiting_faulty_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_temperature_sensor_on_du_2(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Отказ СИ температуры
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 2: 'Ухудшение характеристик', "
            "по причине: 'Отказ СИ температуры'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_temperature_sensor_on_du_2_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 2, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_temperature_sensor_on_du_2_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.deg_rejection_temperature_sensor_on_du_2_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_temperature_sensor_on_du_3(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Отказ СИ температуры
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 3: 'Ухудшение характеристик', "
            "по причине: 'Отказ СИ температуры'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_temperature_sensor_on_du_3_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 3, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_temperature_sensor_on_du_3_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.deg_rejection_temperature_sensor_on_du_3_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_temperature_sensor_on_du_5(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причина: Отказ СИ температуры
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 5: 'Ухудшение характеристик', "
            "по причине: 'Отказ СИ температуры'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_temperature_sensor_on_du_5_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 5, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_temperature_sensor_on_du_5_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.deg_rejection_temperature_sensor_on_du_5_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_density_and_viscosity_on_du_2(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причины: Отказ СИ плотности и СИ вязкости
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 2: 'Ухудшение характеристик', "
            "по причинам: 'Отказ СИ плотности' и 'Отказ СИ вязкости'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_density_and_viscosity_on_du_2_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 2, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_density_and_viscosity_on_du_2_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.deg_rejection_density_and_viscosity_on_du_2_test_data
        await scenarios.lds_status_check_with_2_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_density_and_viscosity_on_du_3(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причины: Отказ СИ плотности и СИ вязкости
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 3: 'Ухудшение характеристик', "
            "по причинам: 'Отказ СИ плотности' и 'Отказ СИ вязкости'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_density_and_viscosity_on_du_3_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 3, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_density_and_viscosity_on_du_3_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.deg_rejection_density_and_viscosity_on_du_3_test_data
        await scenarios.lds_status_check_with_2_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_rejection_density_and_viscosity_on_du_5(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        Причины: Отказ СИ плотности и СИ вязкости
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ на ДУ 5: 'Ухудшение характеристик', "
            "по причинам: 'Отказ СИ плотности' и 'Отказ СИ вязкости'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.deg_rejection_density_and_viscosity_on_du_5_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 5, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_rejection_density_and_viscosity_on_du_5_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.deg_rejection_density_and_viscosity_on_du_5_test_data
        await scenarios.lds_status_check_with_2_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_faulty_absence_min_flow_meters(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Неисправна
        Причина: Отсутствие минимального количества СИ Расхода
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Неисправна', "
            "по причине: 'Отсутствие минимального количества СИ Расхода'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.faulty_absence_min_flow_meters_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.faulty_absence_min_flow_meters_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Неисправна\n "
                "Ожидаемая причина режима работы СОУ: При одновременном выполнении следующих условий:"
                "- отсутствие достоверных показаний граничного на диагностическом участке СИ расхода (кроме "
                "отсеченных от рассматриваемого участка СИ расхода для трубопровода в режиме остановленной перекачки);"
                "- отсутствие смежного с данным СИ расхода диагностического участка "
                "с достоверными показаниями СИ расхода"
            ),
        )
        test_data = config.faulty_absence_min_flow_meters_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_faulty_absence_min_flow_meters_continuous(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Неисправна
        Причина: Отсутствие минимального количества СИ Расхода
        После устранения причины неисправности
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Неисправна', "
            "по причине: 'Отсутствие минимального количества СИ Расхода'. "
            "После устранения причины неисправности. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.faulty_absence_min_flow_meters_continuous_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.faulty_absence_min_flow_meters_continuous_test.offset} мин.\n"
                "После устранения причины неисправности (Заменяет Инициализацию при непродолжительной неисправности)\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Неисправна\n "
                "Ожидаемая причина режима работы СОУ: При одновременном выполнении следующих условий:"
                "- отсутствие достоверных показаний граничного на диагностическом участке СИ расхода (кроме "
                "отсеченных от рассматриваемого участка СИ расхода для трубопровода в режиме остановленной перекачки);"
                "- отсутствие смежного с данным СИ расхода диагностического участка "
                "с достоверными показаниями СИ расхода"
            ),
        )
        test_data = config.faulty_absence_min_flow_meters_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_faulty_absence_min_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Неисправна
        Причина: Менее 4 КП с достоверными СИ давления
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Неисправна', "
            "по причине: 'Менее 4 КП с достоверными СИ давления'. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.faulty_absence_min_pressure_sensors_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.faulty_absence_min_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Неисправна\n "
                "Ожидаемая причина режима работы СОУ: Менее 4 КП с достоверными СИ давления"
            ),
        )
        test_data = config.faulty_absence_min_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    def test_lds_status_init_accumulation_data_in_journal(
        self, http_client: StandHttpClient, config: LDSStatusConfig
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Инициализация,
        Причина: Накопление данных
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Инициализация', по причине: 'Накопление данных'. ЭФ: Журнал. Реальное время"
        )
        _apply_allure_markers(
            config.init_accumulation_data_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_accumulation_data_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Накопление данных"
            ),
        )
        test_data = config.init_accumulation_data_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    @pytest.mark.asyncio
    def test_lds_status_init_cold_start_in_journal(
        self, http_client: StandHttpClient, config: LDSStatusConfig, imitator_start_time: datetime
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Инициализация,
        Причина: Холодный пуск
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Инициализация', по причине: 'Холодный пуск'. ЭФ: Журнал. Реальное время"
        )
        _apply_allure_markers(
            config.init_cold_start_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.init_cold_start_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Холодный пуск"
            ),
        )
        smoke_scenarios.lds_status_init_in_journal(http_client, config, imitator_start_time)

    def test_lds_status_init_switching_shut_off_in_journal(
        self, http_client: StandHttpClient, config: LDSStatusConfig
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Инициализация,
        Причина: Переключение запорной арматуры
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Инициализация', по причине: 'Переключение запорной арматуры'. ЭФ: Журнал. Реальное время"
        )
        _apply_allure_markers(
            config.init_switching_shut_off_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.init_switching_shut_off_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Инициализация\n "
                "Ожидаемая причина режима работы СОУ: Переключение запорной арматуры"
            ),
        )
        test_data = config.init_switching_shut_off_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_serviceable_after_cold_start_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Исправна.
        Установка режима Исправна после Инициализации, по причине Холодный пуск.
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Исправна', после Инициализации. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.serviceable_after_cold_start_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.serviceable_after_cold_start_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Исправна\n"
            ),
        )
        test_data = config.serviceable_all_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_serviceable_after_switching_shut_off_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Исправна.
        Установка режима Исправна после Инициализации, по причине Переключение запорной арматуры.
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Исправна', после Инициализации. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.serviceable_after_switching_shut_off_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.serviceable_after_switching_shut_off_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Исправна\n"
            ),
        )
        test_data = config.serviceable_all_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Исправна.
        Установка режима Исправна после режима Ухудшение характеристик.
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: "
            "'Исправна', после режима Ухудшение характеристик. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Исправна\n"
            ),
        )
        test_data = config.serviceable_all_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_degradation_gravity_section_pumping_in_stopping_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Ухудшение характеристик
        Причина: Наличие самотечного участка в режиме остановленной перекачки
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Наличие самотечного участка в режиме остановленной перекачки'"
        )

        _apply_allure_markers(
            config.deg_gravity_section_pumping_in_stopping_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_gravity_section_pumping_in_stopping_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Наличие самотечного участка в режиме остановленной перекачки "
            ),
        )
        test_data = config.deg_gravity_section_pumping_in_stopping_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_degradation_exceeding_distance_between_pressure_sensors_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Ухудшение характеристик
        Причина: расстояние между СИ давления более 50 км
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Расстояние между СИ давления более 50 км'"
        )

        _apply_allure_markers(
            config.deg_exceeding_distance_between_pressure_sensors_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_exceeding_distance_between_pressure_sensors_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Расстояние между СИ давления более 50 км "
            ),
        )
        test_data = config.deg_exceeding_distance_between_pressure_sensors_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_degradation_faulty_pressure_sensors_at_pump_station_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Ухудшение характеристик
        Причина: Отказ СИ давления на входе/выходе НПС
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Отказ СИ давления на входе/выходе НПС'"
        )

        _apply_allure_markers(
            config.deg_faulty_pressure_sensors_at_pump_station_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.deg_faulty_pressure_sensors_at_pump_station_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ давления на входе/выходе НПС "
            ),
        )
        test_data = config.deg_faulty_pressure_sensors_at_pump_station_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)

    def test_lds_status_faulty_absence_min_pressure_sensors_in_journal(
        self,
        http_client: StandHttpClient,
        config: LDSStatusConfig,
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы СОУ в журнале: Неисправна
        Причина: Менее 4 КП с достоверными СИ давления
        """
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка записи в журнале о режиме работы СОУ: 'Неисправна', "
            "по причине: 'Менее 4 КП с достоверными СИ давления'"
        )

        _apply_allure_markers(
            config.faulty_absence_min_pressure_sensors_in_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                "Время проведения проверки : "
                f"{config.faulty_absence_min_pressure_sensors_in_journal_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=LDS_STATUS\n"
                "Ожидаемый режим работы СОУ: Неисправна\n "
                "Ожидаемая причина режима работы СОУ: Менее 4 КП с достоверными СИ давления "
            ),
        )
        test_data = config.faulty_absence_min_pressure_sensors_in_journal_test_data
        scenarios.lds_status_in_journal(http_client, config, test_data)
        