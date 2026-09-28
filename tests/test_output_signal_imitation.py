"""
Тесты имитации выходных сигналов СОУ (обратный обмен СДКУ).

Каждый тест имитирует ровно один выходной сигнал. Offset между тестами задан
с шагом 2 минуты, чтобы имитации не пересекались.

Запуск:
- Все наборы: pytest tests/test_output_signal_imitation.py
- Один набор: pytest tests/test_output_signal_imitation.py --suites=output_signal_imitation
"""

from typing import Any, List

import allure
import pytest

from clients.opc_ua_client import OpcUaClient
from constants.enums import OutputSignalType
from test_config.datasets import ALL_OUTPUT_SIGNAL_IMITATION_CONFIGS
from test_config.models_for_tests import OutputSignalImitationConfig
from test_scenarios import output_signal_imitation_scenarios as scenarios
from utils.helpers.opc_imitation_utils import find_case_by_signal_type


def _get_suite_markers(config: OutputSignalImitationConfig) -> List[pytest.MarkDecorator]:
    """Маркеры тестового набора для группировки и setup."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
        pytest.mark.ost_name(config.ost_name),
    ]


def _generate_suite_params() -> List[Any]:
    """Один параметр на каждый набор данных имитации выходных сигналов."""
    return [
        pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config))
        for config in ALL_OUTPUT_SIGNAL_IMITATION_CONFIGS
    ]


@pytest.mark.parametrize("config", _generate_suite_params())
class TestOutputSignalImitation:
    """Тесты имитации выходных сигналов СОУ (по одному сигналу на тест)."""

    async def _imitate(
        self, opc_client: OpcUaClient, config: OutputSignalImitationConfig, signal_type: OutputSignalType
    ) -> None:
        case = find_case_by_signal_type(config.cases, signal_type)
        allure.dynamic.tag("imitateOutputSignal")
        allure.dynamic.tag("OPC_UA")
        allure.dynamic.title(
            f"[imitateOutputSignal] Имитация {case.signal_type.signal_type} ({case.address}.{case.opc_suffix})"
        )
        allure.dynamic.description(
            f"Проверка имитации выходного сигнала {case.signal_type.signal_type} "
            f"на наборе {config.suite_name}.\n"
            "Проверки выполняются напрямую через OPC UA: значение, качество и время изменения сигнала."
        )
        await scenarios.imitate_output_signal(opc_client, config, case)

    @pytest.mark.asyncio
    async def test_imitate_leak(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.LEAK)

    @pytest.mark.asyncio
    async def test_imitate_leak_coordinate(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.LEAK_COORDINATE)

    @pytest.mark.asyncio
    async def test_imitate_leak_volume(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.LEAK_VOLUME)

    @pytest.mark.asyncio
    async def test_imitate_leak_time(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.LEAK_TIME)

    @pytest.mark.asyncio
    async def test_imitate_acknowledge(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.ACKNOWLEDGE)

    @pytest.mark.asyncio
    async def test_imitate_mask(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.MASK)

    @pytest.mark.asyncio
    async def test_imitate_mask_reason(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.MASK_REASON)

    @pytest.mark.asyncio
    async def test_imitate_pumping_status(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.PUMPING_STATUS)

    @pytest.mark.asyncio
    async def test_imitate_lds_status(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.LDS_STATUS)

    @pytest.mark.asyncio
    async def test_imitate_free_flow(self, opc_client: OpcUaClient, config: OutputSignalImitationConfig) -> None:
        await self._imitate(opc_client, config, OutputSignalType.FREE_FLOW)
