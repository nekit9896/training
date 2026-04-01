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

    @pytest.mark.asyncio
    @pytest.mark.critical_stop
    async def test_lds_status_basic_info(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.lds_status_basic_info_test, tag, title)
        await scenarios.basic_info(ws_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_init_cold_start(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Инициализация,
        Причина: Холодный пуск
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация', по причине: 'Холодный пуск'. ЭФ: Схема"
        _apply_allure_markers(
            config.lds_status_init_cold_start_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки : {config.lds_status_init_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Холодный пуск"
            ),
        )
        test_data = config.lds_status_init_cold_start_test_data
        await scenarios.lds_status_check_on_base_diagnostic_areas(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_serviceable_after_faulty(
        self, ws_client: WebSocketClient, config: LDSStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы СОУ: Исправна.
        Установка режима Исправна после Инициализации, по причине выхода из Неисправности.
        """
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Исправна' на базовых ДУ. ЭФ: Схема"
        _apply_allure_markers(
            config.lds_status_serviceable_after_faulty_test,
            tag,
            title,
            (
                "Проверка выхода СОУ из повторной Инициализации, после Неисправности, на показательных ДУ,"
                f" на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки: {config.lds_status_serviceable_after_faulty_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Исправна"
            ),
        )
        test_data = config.lds_status_serviceable_all_test_data
        await scenarios.lds_status_check_on_representative(ws_client, config, test_data)

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
            config.lds_status_deg_exceeding_distance_between_pressure_sensors_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_exceeding_distance_between_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Расстояние между СИ давления более 50 км"
            ),
        )
        test_data = config.lds_status_deg_exceeding_distance_between_pressure_sensors_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_lds_status_degradation_not_enough_pressure_sensors(
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
            config.lds_status_deg_not_enough_pressure_sensors_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_not_enough_pressure_sensors_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Ухудшение При наличии менее четырех (3, 6) исправных СИ давления "
                "на разных КП ЛЧ МТ/НПС на диагностическом участке (кроме случая нахождения трубопровода "
                "в режиме остановленной перекачки)"
            ),
        )
        test_data = config.lds_status_deg_not_enough_pressure_sensors_test_data
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
            config.lds_status_deg_pig_sensor_passage_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки : {config.lds_status_deg_pig_sensor_passage_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: прохождение СОД "
            ),
        )
        test_data = config.lds_status_deg_pig_sensor_passage_test_data
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
            config.lds_status_deg_gravity_section_pumping_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки : {config.lds_status_deg_gravity_section_pumping_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Наличие самотечного участка/участка с неполным сечением "
            ),
        )
        test_data = config.lds_status_deg_gravity_section_pumping_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

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
            config.lds_status_deg_starting_pumping_out_pumps_test,
            tag,
            title,
            (
                f"Проверка режимов работы СОУ и МТ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_starting_pumping_out_pumps_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемый режим работы МТ: Нестационарный\n "
                "Ожидаемая причина режима работы СОУ: Работа насосов откачки"
                "Ожидаемая причина режима работы МТ: Работа насосов откачки"
            ),
        )
        test_data = config.lds_status_deg_starting_pumping_out_pumps_test_data
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
            config.lds_status_deg_exceeding_distance_between_flow_meters_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_exceeding_distance_between_flow_meters_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Расстояние между СИ расхода на пути перекачки более 200 км"
            ),
        )
        test_data = config.lds_status_deg_exceeding_distance_between_flow_meters_test_data
        await scenarios.lds_status_check_with_reasons(ws_client, config, test_data)

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
            config.lds_status_faulty_absence_min_flow_meters_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на выбранном ДУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_faulty_absence_min_flow_meters_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Неисправна\n "
                "Ожидаемая причина режима работы СОУ: При одновременном выполнении следующих условий:"
                "- отсутствие достоверных показаний граничного на диагностическом участке СИ расхода (кроме "
                "отсеченных от рассматриваемого участка СИ расхода для трубопровода в режиме остановленной перекачки);"
                "- отсутствие смежного с данным СИ расхода диагностического участка "
                "с достоверными показаниями СИ расхода2"
            ),
        )
        test_data = config.lds_status_faulty_absence_min_flow_meters_test_data
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
            config.lds_status_deg_rejection_temperature_sensor_on_du_2_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 2, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_temperature_sensor_on_du_2_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.lds_status_deg_rejection_temperature_sensor_on_du_2_test_data
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
            config.lds_status_deg_rejection_temperature_sensor_on_du_3_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 3, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_temperature_sensor_on_du_3_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.lds_status_deg_rejection_temperature_sensor_on_du_3_test_data
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
            config.lds_status_deg_rejection_temperature_sensor_on_du_5_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 5, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_temperature_sensor_on_du_5_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ температуры"
            ),
        )
        test_data = config.lds_status_deg_rejection_temperature_sensor_on_du_5_test_data
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
            config.lds_status_deg_rejection_density_and_viscosity_on_du_2_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 2, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_density_and_viscosity_on_du_2_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.lds_status_deg_rejection_density_and_viscosity_on_du_2_test_data
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
            config.lds_status_deg_rejection_density_and_viscosity_on_du_3_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 3, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_density_and_viscosity_on_du_3_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.lds_status_deg_rejection_density_and_viscosity_on_du_3_test_data
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
            config.lds_status_deg_rejection_density_and_viscosity_on_du_5_test,
            tag,
            title,
            (
                f"Проверка режима работы СОУ на ДУ 5, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.technological_unit.description}\n"
                "Время проведения проверки : "
                f"{config.lds_status_deg_rejection_density_and_viscosity_on_du_5_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                "Ожидаемый режим работы СОУ: Ухудшение характеристик\n "
                "Ожидаемая причина режима работы СОУ: Отказ СИ плотности"
                "Ожидаемая причина режима работы СОУ: Отказ СИ вязкости"
            ),
        )
        test_data = config.lds_status_deg_rejection_density_and_viscosity_on_du_5_test_data
        await scenarios.lds_status_check_with_2_reasons(ws_client, config, test_data)
