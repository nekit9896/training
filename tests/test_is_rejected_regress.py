"""
Тесты отбраковки сигналов с датчиков давления и расходомеров.

Параметризация:
- SUITE_PARAMS: генерирует (config, rejection_case, case_number) для каждого RejectionTestCase
  из каждого IsRejectedConfig.
- Все 4 теста (InputSignals, Journal, MainPage, SchemeSignalsState) запускаются с одинаковым offset
  для каждого события отбраковки.

Запуск:
pytest tests/test_is_rejected_regress.py --suites=is_rejected_regress
"""

from datetime import datetime
from typing import Any, List, Optional

import allure
import pytest

from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_IS_REJECTED_CONFIGS
from test_config.models_for_tests import CaseMarkers, IsRejectedConfig, RejectionTestCase
from test_scenarios import scenarios

# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====


def _get_suite_markers(config: IsRejectedConfig) -> List[pytest.MarkDecorator]:
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
    ]


def _generate_rejection_params() -> List[Any]:
    """
    Генерирует параметры для тестов отбраковки.
    Один параметр на каждый (config, rejection_case, case_number).
    """
    params = []
    for config in ALL_IS_REJECTED_CONFIGS:
        for rejection_case in config.rejection_cases:
            param_id = f"{config.suite_name}_{rejection_case.name}"
            params.append(
                pytest.param(
                    config,
                    rejection_case,
                    id=param_id,
                    marks=_get_suite_markers(config),
                )
            )
    return params


# ===== ПАРАМЕТРЫ ДЛЯ ТЕСТОВ =====
REJECTION_PARAMS: List[Any] = _generate_rejection_params()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def _apply_allure_markers(
    test_config: Optional[CaseMarkers], tag: str, title: str, description: Optional[str] = None
) -> None:
    """Применяет allure-маркеры из конфига теста."""
    if not test_config:
        pytest.skip("Не заполнена конфигурация теста: тест пропущен")
    allure.dynamic.tag(tag)
    allure.dynamic.tag("REGRESS")
    allure.dynamic.title(title)
    if description:
        allure.dynamic.description(description)


# ===== ТЕСТЫ ОТБРАКОВКИ =====


@pytest.mark.parametrize("config, rejection_case", REJECTION_PARAMS)
class TestIsRejectedScenarios:
    """
    Тесты отбраковки сигналов.
    Для каждого RejectionTestCase из конфига запускается 4 теста по одному на подписку.
    """

    @pytest.mark.asyncio
    async def test_rejection_input_signals(
        self,
        ws_client: WebSocketClient,
        config: IsRejectedConfig,
        rejection_case: RejectionTestCase,
    ) -> None:
        """[InputSignals] Проверка отбраковки во входных сигналах по подписке SubscribeInputSignalsRequest"""
        sensor = rejection_case.sensor
        tag = "InputSignals"
        title = (
            f"[{tag}] Проверка: {rejection_case.expected_event} для {sensor.description} (id={sensor.id}) "
            f"({rejection_case.name}). ЭФ: Входные сигналы"
        )
        _apply_allure_markers(
            rejection_case.rejection_input_signals_test,
            tag,
            title,
            (
                f"Проверка отбраковки сигнала {sensor.description} (id={sensor.id}), "
                f"на наборе данных {config.suite_name},\n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки: {rejection_case.rejection_input_signals_test.offset} мин.\n"
                f"Тип отбраковки: {rejection_case.name}\n"
                "Подписка: SubscribeInputSignalsRequest"
            ),
        )
        await scenarios.rejection_input_signals(ws_client, config, rejection_case)

    @pytest.mark.asyncio
    async def test_rejection_journal(
        self,
        ws_client: WebSocketClient,
        config: IsRejectedConfig,
        rejection_case: RejectionTestCase,
        imitator_start_time: datetime,
    ) -> None:
        """[MessagesInfo] Проверка записи об отбраковке в журнале"""
        sensor = rejection_case.sensor
        tag = "MessagesInfo"
        title = (
            f"[{tag}] Проверка: {rejection_case.expected_event} для {sensor.description} (id={sensor.id}) "
            f"({rejection_case.name}) в журнале. ЭФ: Журнал"
        )
        _apply_allure_markers(
            rejection_case.rejection_journal_test,
            tag,
            title,
            (
                f"Проверка записи в журнале об отбраковке сигнала {sensor.description} (id={sensor.id}), "
                f"на наборе данных {config.suite_name},\n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки: {rejection_case.rejection_journal_test.offset} мин.\n"
                f"Тип отбраковки: {rejection_case.name}\n"
                "Синхронный запрос типа: GetMessagesRequest с фильтром messageTypes=REJECTION"
            ),
        )
        await scenarios.rejection_journal(ws_client, config, rejection_case, imitator_start_time)

    @pytest.mark.asyncio
    async def test_rejection_main_page(
        self,
        ws_client: WebSocketClient,
        config: IsRejectedConfig,
        rejection_case: RejectionTestCase,
    ) -> None:
        """[MainPageSignalsInfo] Проверка счетчика отбраковки на состоянии МТ"""
        tag = "MainPageSignalsInfo"
        title = (
            f"[{tag}] Проверка: {rejection_case.expected_event} - счетчик отбраковки на состоянии МТ показывает отбраковку"
            f"({rejection_case.name}). ЭФ: Состояние МТ"
        )
        _apply_allure_markers(
            rejection_case.rejection_main_page_test,
            tag,
            title,
            (
                f"Проверка количества отбракованных сигналов > 0 при отбраковке {rejection_case.name}, "
                f"на наборе данных {config.suite_name},\n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки: {rejection_case.rejection_main_page_test.offset} мин.\n"
                "Подписка: subscribeMainPageSignalsInfoRequest"
            ),
        )
        await scenarios.rejection_main_page(ws_client, config)

    @pytest.mark.asyncio
    async def test_rejection_scheme_signals_state(
        self,
        ws_client: WebSocketClient,
        config: IsRejectedConfig,
        rejection_case: RejectionTestCase,
    ) -> None:
        """[SchemeSignalsState] Проверка отбраковки сигнала на схеме по подписке SubscribeSchemeSignalsStateRequest"""
        sensor = rejection_case.sensor
        tag = "SchemeSignalsState"
        title = (
            f"[{tag}] Проверка: {rejection_case.expected_event} для {sensor.description} (id={sensor.id}) "
            f"({rejection_case.name}). ЭФ: Схема"
        )
        _apply_allure_markers(
            rejection_case.rejection_scheme_signals_state_test,
            tag,
            title,
            (
                f"Проверка отбраковки сигнала {sensor.description} (id={sensor.id}), "
                f"на наборе данных {config.suite_name},\n"
                f"на технологическом участке {config.technological_unit.description}\n"
                f"Время проведения проверки: {rejection_case.rejection_scheme_signals_state_test.offset} мин.\n"
                f"Тип отбраковки: {rejection_case.name}\n"
                f"Ожидаемый criteriaNames: {rejection_case.expected_criteria_names}\n"
                "Подписка: SubscribeSchemeSignalsStateRequest"
            ),
        )
        await scenarios.rejection_scheme_signals_state(ws_client, config, rejection_case)
