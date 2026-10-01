"""
Хелперы для сценария имитации выходных сигналов СОУ (обратный обмен СДКУ).
"""

from typing import Any

from clients.opc_ua_client import build_opc_node_id
from constants.enums import OutputSignalType
from test_config.models_for_tests import OutputSignalImitationCase, OutputSignalImitationConfig


def build_imitate_request(case: OutputSignalImitationCase, tu_id: int) -> dict[str, Any]:
    """
    Формирует тело запроса imitateOutputSignalRequest по контракту (asyncapi).

    TODO: заменить на реальный вызов имитации через api-gateway (WebSocket invocation),
    когда бэк реализует метод imitateOutputSignal.
    """
    return {
        'objectId': case.object_id,
        'signalType': case.signal_type.signal_type,
        'tuId': tu_id,
        'imitateInfo': {'value': case.imitate_value},
    }


def coerce_expected_value(expected: str, actual: Any) -> Any:
    """
    Приводит строковое ожидаемое значение (imitateInfo.value) к типу фактического
    значения OPC-тега, чтобы корректно сравнивать bool/int/float.
    """
    if actual is None:
        return expected
    if isinstance(actual, bool):
        return expected.strip().lower() in ("true", "1")
    if isinstance(actual, int):
        return int(float(expected))
    if isinstance(actual, float):
        return float(expected)
    return expected


def build_case_node_id(cfg: OutputSignalImitationConfig, case: OutputSignalImitationCase, stand_name: str) -> str:
    """Собирает NodeId для кейса имитации выходного сигнала."""
    return build_opc_node_id(cfg.ost_name, stand_name, case.address, case.opc_suffix)


def format_opc_snapshot(node_id: str, data_value: Any) -> str:
    """Текстовое описание значения/статуса/времени для allure-вложений и логов."""
    value = data_value.Value.Value if data_value and data_value.Value else None
    status = data_value.StatusCode if data_value else None
    source_ts = data_value.SourceTimestamp if data_value else None
    return f"{node_id}\nValue={value}\nStatusCode={status}\nSourceTimestamp={source_ts}"


def find_case_by_signal_type(
    cases: list[OutputSignalImitationCase], signal_type: OutputSignalType
) -> OutputSignalImitationCase:
    """Находит кейс имитации в наборе данных по типу сигнала."""
    for case in cases:
        if case.signal_type == signal_type:
            return case
    raise ValueError(f"Не найден кейс имитации для типа сигнала {signal_type}")
