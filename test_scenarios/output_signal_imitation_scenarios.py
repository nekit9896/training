"""
Сценарий имитации выходных сигналов СОУ (обратный обмен СДКУ) с проверкой через OPC UA.

Порядок выполнения (чтобы не блочить сценарий):
1. Сначала читаем текущие значения всех тегов (снапшот "до").
2. Затем выполняем все действия имитации (заглушка до готовности api-gateway).
3. Затем читаем значения всех тегов (снапшот "после").
4. В конце — все проверки (мягкие, через SoftAssertions).
"""

import logging
import os
from datetime import datetime
from typing import Optional

import allure
import pytest

from clients.opc_ua_client import OpcUaClient
from constants.architecture_constants import EnvKeyConstants
from test_config.models_for_tests import OutputSignalImitationCase, OutputSignalImitationConfig
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.opc_imitation_utils import (
    build_case_node_id,
    build_imitate_request,
    coerce_expected_value,
    format_opc_snapshot,
)

logger = logging.getLogger(__name__)


async def imitate_output_signal(
    opc_client: OpcUaClient, cfg: OutputSignalImitationConfig, case: OutputSignalImitationCase
) -> None:
    """
    Универсальный сценарий: имитирует один выходной сигнал и проверяет изменение
    через OPC UA.
    """
    stand_name = os.environ.get(EnvKeyConstants.STAND_NAME) or ""
    node_id = build_case_node_id(cfg, case, stand_name)

    # ===== 1. Слепок значений ноды до имитации =====
    with allure.step("Чтение значения выходного сигнала до имитации (OPC UA)"):
        before_dv = await opc_client.read_data_value(node_id)
        if not before_dv.StatusCode.is_good():
            pytest.fail(
                f"Нет данных по тегу {case.address}.{case.opc_suffix} (NodeId: {node_id}). "
                f"Статус: {before_dv.StatusCode.name} ({before_dv.StatusCode.value})"
            )
        allure.attach(
            format_opc_snapshot(node_id, before_dv),
            name=f"до: {case.address}.{case.opc_suffix}",
            attachment_type=allure.attachment_type.TEXT,
        )

    # ===== 2. Действие имитации =====
    with allure.step("Имитация выходного сигнала через api-gateway (заглушка)"):
        request = build_imitate_request(case, cfg.tu_id)
        allure.attach(
            str(request),
            name=f"imitateOutputSignalRequest: {case.address}.{case.opc_suffix}",
            attachment_type=allure.attachment_type.JSON,
        )
        # TODO: реальный вызов имитации выходного сигнала через api-gateway.
        logger.info(
            "TODO: имитация выходного сигнала signalType=%s value=%s",
            case.signal_type.signal_type,
            case.imitate_value,
        )

    # ===== 3. Слепок значений ноды после имитации =====
    with allure.step("Чтение значения выходного сигнала после имитации (OPC UA)"):
        after_dv = await opc_client.read_data_value(node_id)
        if not after_dv.StatusCode.is_good():
            pytest.fail(
                f"Нет данных по тегу {case.address}.{case.opc_suffix} (NodeId: {node_id}) после имитации. "
                f"Статус: {after_dv.StatusCode.name} ({after_dv.StatusCode.value})"
            )
        allure.attach(
            format_opc_snapshot(node_id, after_dv),
            name=f"после: {case.address}.{case.opc_suffix}",
            attachment_type=allure.attachment_type.TEXT,
        )

    # ===== 4. Проверки =====
    with allure.step("Проверки"):
        with SoftAssertions() as soft_failures:
            after_value = after_dv.Value.Value if after_dv and after_dv.Value else None
            expected_value = coerce_expected_value(case.imitate_value, after_value)

            StepCheck(f"Проверка имитации {case.signal_type.signal_type} ({node_id})", "value", soft_failures).actual(
                after_value
            ).expected(expected_value).equal_to()

            StepCheck(
                f"Проверка качества сигнала {case.signal_type.signal_type} ({node_id})", "status", soft_failures
            ).actual(after_dv.StatusCode.is_good() if after_dv else False).expected(True).equal_to()

            before_ts: Optional[datetime] = before_dv.SourceTimestamp if before_dv else None
            after_ts: Optional[datetime] = after_dv.SourceTimestamp if after_dv else None
            ts_changed = after_ts is not None and (before_ts is None or after_ts >= before_ts)
            StepCheck(
                f"Проверка времени изменения сигнала {case.signal_type.signal_type} ({node_id})",
                "SourceTimestamp",
                soft_failures,
            ).actual(ts_changed).expected(True).equal_to()

            logger.info(
                "Имитация %s: до=%s, после=%s",
                node_id,
                before_dv.Value.Value if before_dv and before_dv.Value else None,
                after_value,
            )
