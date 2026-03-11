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

from typing import Any, List, Optional

import allure
import pytest

from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_LDS_STATUS_CONFIGS
from test_config.models_for_tests import CaseMarkers, LDSStatusConfig
from test_scenarios import scenarios

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
        msg = "Не заполнена конфигурация теста: запуск остановлен"
        allure.attach(msg, name="Ошибка подготовки тестрана", attachment_type=allure.attachment_type.TEXT)
        pytest.exit(msg)
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

    @pytest.mark.asyncio
    @pytest.mark.critical_stop
    async def test_lds_status_basic_info(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.lds_status_basic_info_test, tag, title)
        await scenarios.basic_info(ws_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_initialization_cold_start(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Холодный пуск
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация', по причине: 'Холодный пуск'. ЭФ: Схема"
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки : {config.lds_status_init_cold_start_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Холодный пуск"
        )
        _apply_allure_markers(config.lds_status_init_cold_start_test, tag, title, description)
        test_data = config.lds_status_init_cold_start_test_data
        await scenarios.lds_status_check_on_base_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_faulty(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка перехода СОУ в режим Исправна, после второй Инициализации и выхода из Неисправности.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' на базовых ДУ. ЭФ: Схема"
        description = (
            "Проверка выхода СОУ из повторной Инициализации, после Неисправности, на базовых ДУ,"
            f" на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.lds_status_serviceable_after_faulty_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Исправна"
        )
        _apply_allure_markers(config.lds_status_serviceable_after_faulty_test, tag, title, description)
        test_data = config.lds_status_serviceable_all_test_data
        await scenarios.lds_status_check_on_representative(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_exceeding_distance_between_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        по причине расстояние между СИ давления более 50 км
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Расстояние между СИ давления более 50 км'. ЭФ: Схема"
        )
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            "Время проведения проверки : "
            f"{config.lds_status_deg_exceeding_distance_between_pressure_sensors_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
            "Ожидаемая причина режима работы СОУ: Расстояние между СИ давления более 50 км"
        )
        _apply_allure_markers(
            config.lds_status_deg_exceeding_distance_between_pressure_sensors_test, tag, title, description
        )
        test_data = config.lds_status_deg_exceeding_distance_between_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_not_enough_pressure_sensors(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик по причине менее 4 исправных СИ давления
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'менее 4 исправных СИ давления'. ЭФ: Схема"
        )
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            "Время проведения проверки : "
            f"{config.lds_status_deg_not_enough_pressure_sensors_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
            "Ожидаемая причина режима работы СОУ: Ухудшение При наличии менее четырех (3, 6) исправных СИ давления "
            "на разных КП ЛЧ МТ/НПС на диагностическом участке (кроме случая нахождения трубопровода "
            "в режиме остановленной перекачки)"
        )
        _apply_allure_markers(config.lds_status_deg_not_enough_pressure_sensors_test, tag, title, description)
        test_data = config.lds_status_deg_not_enough_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_pig_sensor_passage(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик по причине прохождения СОД
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', по причине: 'прохождение СОД'"
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки : {config.lds_status_deg_pig_sensor_passage_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
            "Ожидаемая причина режима работы СОУ: прохождение СОД "
        )
        _apply_allure_markers(config.lds_status_deg_pig_sensor_passage_test, tag, title, description)
        test_data = config.lds_status_deg_pig_sensor_passage_test_data
        await scenarios.lds_status_check_degradation_pig_sensor_passage(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_gravity_section_pumping(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Ухудшение характеристик
        по причине Наличие самотечного участка/участка с неполным сечением
        """
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Наличие самотечного участка/участка с неполным сечением'"
        )
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки : {config.lds_status_deg_gravity_section_pumping_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
            "Ожидаемая причина режима работы СОУ: Наличие самотечного участка/участка с неполным сечением "
        )
        _apply_allure_markers(config.lds_status_deg_gravity_section_pumping_test, tag, title, description)
        test_data = config.lds_status_deg_gravity_section_pumping_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_exceeding_distance_between_flow_meters(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Расстояние между СИ расхода на пути перекачки более 200 км
        """

        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы СОУ: 'Ухудшение характеристик', "
            "по причине: 'Расстояние между СИ расхода на пути перекачки более 200 км'. ЭФ: Схема"
        )
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            "Время проведения проверки : "
            f"{config.lds_status_deg_exceeding_distance_between_flow_meters_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
            "Ожидаемая причина режима работы СОУ: Расстояние между СИ расхода на пути перекачки более 200 км"
        )
        _apply_allure_markers(
            config.lds_status_deg_exceeding_distance_between_flow_meters_test, tag, title, description
        )
        test_data = config.lds_status_deg_exceeding_distance_between_flow_meters_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)
