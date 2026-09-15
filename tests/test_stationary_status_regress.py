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

from clients.http_client import StandHttpClient
from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_STATIONARY_STATUS_CONFIGS
from test_config.models_for_tests import CaseMarkers, StationaryStatusConfig
from test_scenarios import smoke_scenarios
from test_scenarios import stationary_status_scenarios as scenarios

# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====


def _get_suite_markers(config: StationaryStatusConfig) -> List[pytest.MarkDecorator]:
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
        pytest.mark.ost_name(config.ost_name),
    ]


def _generate_suite_params() -> List[Any]:
    """
    Генерирует параметры для тестов уровня набора данных.
    Один параметр на каждый config.
    """
    return [
        pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config))
        for config in ALL_STATIONARY_STATUS_CONFIGS
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
    def test_stationary_status_basic_info(self, http_client: StandHttpClient, config: StationaryStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.stationary_status_basic_info_test, tag, title)
        smoke_scenarios.basic_info(http_client, config)

    @pytest.mark.asyncio
    async def test_common_scheme_cold_start(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема
        """
        test_data = config.status_unstationary_cold_start_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_cold_start_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_common_scheme_stationary_after_cold(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после холодного старта
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_stationary_after_cold_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_stationary_after_cold_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_common_scheme_switch_on(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Событие: Открытие задвижки / включение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. "
            "Событие: Открытие задвижки / включение насоса. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_common_scheme_stationary_after_switch_on(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после открытия задвижки / включения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. "
            "Стационар после открытия задвижки / включения насоса. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_stationary_after_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_stationary_after_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_common_scheme_switch_off(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Событие: Закрытие задвижки / выключение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. "
            "Событие: Закрытие задвижки / выключение насоса. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_common_scheme_stationary_after_switch_off(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после закрытия задвижки / выключения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "CommonScheme"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text},"
            f" по причине: {expected_stationary_status_reasons.report_text}. "
            "Стационар после закрытия задвижки / выключения насоса. ЭФ: Схема"
        )
        _apply_allure_markers(
            config.common_scheme_stationary_after_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.common_scheme_stationary_after_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: CommonScheme\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons.report_text}"
            ),
        )
        await scenarios.stationary_status_common_scheme(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_cold_start(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Нестационар по причине Одновременный «холодный» запуск нескольких серверов СОУ
        """
        test_data = config.status_unstationary_cold_start_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}."
            " ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_cold_start_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_stationary_after_cold(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Стационар после холодного старта
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}."
            " ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_stationary_after_cold_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_stationary_after_cold_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_switch_on(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Открытие задвижки / включение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Событие: Открытие задвижки / включение насоса. ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_stationary_after_switch_on(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Стационар после открытия задвижки / включения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}."
            " Стационар после открытия задвижки / включения насоса. ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_stationary_after_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_stationary_after_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_switch_off(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Событие: Закрытие задвижки / выключение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Событие: Закрытие задвижки / выключение насоса. ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_main_page_info_stationary_after_switch_off(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [CommonScheme] Проверка режима работы МТ на ЭФ: Главная страница. Контент таблица по ТУ.
        Стационар после закрытия задвижки / выключения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}."
            " Стационар после закрытия задвижки / выключения насоса. ЭФ: Главная страница. Контент таблица по ТУ"
        )
        _apply_allure_markers(
            config.main_page_info_stationary_after_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.main_page_info_stationary_after_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: MainPageInfoContent\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}"
            ),
        )
        await scenarios.stationary_status_main_page_info(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_cold_start(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Нестационар по причине Одновременный «холодный» запуск нескольких серверов СОУ
        """
        test_data = config.status_unstationary_cold_start_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_cold_start_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_cold_start_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_stationary_after_cold(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после холодного старта
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_stationary_after_cold_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_stationary_after_cold_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_switch_on(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Открытие задвижки / включение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Событие: Открытие задвижки / включение насоса. ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_stationary_after_switch_on(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после открытия задвижки / включения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Стационар после открытия задвижки / включения насоса. ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_stationary_after_switch_on_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_stationary_after_switch_on_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_switch_off(self, ws_client: WebSocketClient, config: StationaryStatusConfig) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Событие: Закрытие задвижки / выключение насоса
        """
        test_data = config.status_unstationary_switch_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Событие: Закрытие задвижки / выключение насоса. ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    @pytest.mark.asyncio
    async def test_output_signals_stationary_after_switch_off(
        self, ws_client: WebSocketClient, config: StationaryStatusConfig
    ) -> None:
        """
        [OutputSignalsInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Схема.
        Стационар после закрытия задвижки / выключения насоса
        """
        test_data = config.status_stationary_test_data
        expected_stationary_status, _ = test_data.expected_result
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status.report_text}. "
            "Стационар после закрытия задвижки / выключения насоса. ЭФ: Диагностика сигналов.Выходные"
        )
        _apply_allure_markers(
            config.output_signals_stationary_after_switch_off_test,
            tag,
            title,
            (
                f"Проверка режима работы МТ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.output_signals_stationary_after_switch_off_test.offset} мин.\n"
                "Подписка на сообщения типа: OutputSignalsInfo\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status.report_text}\n "
            ),
        )
        await scenarios.stationary_status_in_output_signals(ws_client, config, test_data)

    def test_journal_cold_start(self, http_client: StandHttpClient, config: StationaryStatusConfig) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Нестационар по причине Одновременный «холодный» запуск нескольких серверов СОУ
        """
        test_data = config.journal_unstationary_cold_start_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_cold_start_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_cold_start_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)

    def test_journal_stationary_after_cold(self, http_client: StandHttpClient, config: StationaryStatusConfig) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Стационар после холодного старта
        """
        test_data = config.journal_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_stationary_after_cold_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_stationary_after_cold_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)

    def test_journal_switch_on(self, http_client: StandHttpClient, config: StationaryStatusConfig) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Открытие задвижки / включение насоса
        """
        test_data = config.journal_unstationary_switch_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. "
            "Событие: Открытие задвижки / включение насоса. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_switch_on_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_switch_on_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)

    def test_journal_stationary_after_switch_on(
        self, http_client: StandHttpClient, config: StationaryStatusConfig
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Стационар после открытия задвижки / включения насоса
        """
        test_data = config.journal_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. Стационар после открытия задвижки / включения насоса. "
            "ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_stationary_after_switch_on_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_stationary_after_switch_on_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)

    def test_journal_switch_off(self, http_client: StandHttpClient, config: StationaryStatusConfig) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Событие: Закрытие задвижки / выключение насоса
        """
        test_data = config.journal_unstationary_switch_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. "
            "Событие: Закрытие задвижки / выключение насоса. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_switch_off_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_switch_off_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)

    def test_journal_stationary_after_switch_off(
        self, http_client: StandHttpClient, config: StationaryStatusConfig
    ) -> None:
        """
        [MessagesInfo] Проверка режима работы МТ и причины режима работы МТ на ЭФ: Журнал.
        Стационар после закрытия задвижки / выключения насоса
        """
        test_data = config.journal_stationary_test_data
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка режима работы МТ: {expected_stationary_status},"
            f" по причине: {expected_stationary_status_reasons}. "
            "Стационар после закрытия задвижки / выключения насоса. ЭФ: Журнал. Реальное время"
        )

        _apply_allure_markers(
            config.journal_stationary_after_switch_off_test,
            tag,
            title,
            (
                f"Проверка записи в журнале о режиме работы СОУ, на наборе данных {config.suite_name}, \n"
                f"на технологическом участке {config.tu_name}\n"
                f"Время проведения проверки : {config.journal_stationary_after_switch_off_test.offset} мин.\n"
                "Синхронный запрос типа: MessagesInfo с фильтром messageTypes=PUMPING_STATUS\n"
                f"Ожидаемый режим работы МТ: {expected_stationary_status}\n "
                f"Ожидаемая причина режима работы МТ: {expected_stationary_status_reasons}"
            ),
        )
        scenarios.stationary_status_journal(http_client, config, test_data)
