from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Set, TypeVar
from zoneinfo import ZoneInfo

import allure
from models.subscribe_all_leaks_info_model import SubscribeAllLeaksInfoReply
from models.subscribe_common_scheme_model import DiagnosticArea, FlowArea
from pytest import fail

from constants.expectations.base_expectations import \
    BaseSelectTN3Expected as BaseExp
from utils.helpers.ws_message_parser import ws_message_parser

ObjectType = TypeVar(
    "ObjectType"
)  # создает типовую переменную для поиска объектов в списке
RandomObjectType = TypeVar("RandomObjectType")


def convert_leak_volume_m3(volume: float) -> float:
    """
    Преобразует объем утечки в м3/час
    """
    #  Округляет результат для читабельности
    return round(volume * BaseExp.MASS_KG, 3)


def get_leak_wait_start_time(datetime_now_tz: datetime, delta_s: int) -> datetime:
    # TODO переименовать в datetime_minus_seconds
    """
    Получает начала диапазона ожидания утечки
    """
    return (datetime_now_tz - timedelta(seconds=delta_s)).replace(microsecond=0)


def get_random_item(item_list: List[RandomObjectType]) -> Optional[RandomObjectType]:
    """
    Получает случайный объект из списка
    """
    if item_list:
        return random.choice(item_list)
    return None


def get_longest_flow_area(flow_areas: List[FlowArea]) -> FlowArea:
    """
    Получает самый протяженный участок карты течения по количеству ДУ из списка всех участков
    """

    longest_flow_area = max(
        flow_areas, key=lambda flow_area: len(flow_area.diagnosticAreas)
    )
    return longest_flow_area


def determine_lds_status_by_priority(lds_status_set: Set[int]) -> int:
    """
    Определяет режим работы СОУ по приоритету и наличию режимов работы у ДУ на самом протяженном участки карты течений
    """
    lds_status_priority = [
        BaseExp.LDS_STATUS_FAULTY_VAL,
        BaseExp.LDS_STATUS_INITIALIZATION_VAL,
        BaseExp.LDS_STATUS_DEGRADATION_VAL,
        BaseExp.LDS_STATUS_SERVICEABLE_VAL,
    ]

    for status in lds_status_priority:
        if status in lds_status_set:
            return status


def find_signal_type_by_address_suffix(signals_list: list, address_suffix: str) -> int:
    """
    Ищет в списке сигналов тип сигнала по части адреса
    """
    try:
        for sensor_signal in signals_list:
            if sensor_signal.address is not None and str(
                sensor_signal.address
            ).endswith(address_suffix):
                return sensor_signal.signalType
        fail(f"Не найден тип сигнала по части адреса: {address_suffix}")
    except (AttributeError, TypeError):
        fail(f"Не найден тип сигнала по части адреса: {address_suffix}")


def find_signal_val_by_signal_type(signals_list: list, signal_type: int) -> str:
    """
    Ищет в списке сигналов значение сигнала по типу
    """
    try:
        for sensor_signal in signals_list:
            if (
                sensor_signal.signalType is not None
                and sensor_signal.signalType == signal_type
            ):
                return sensor_signal.value
        fail(f"Не найдено значение для типа сигнала: {signal_type}")
    except (AttributeError, TypeError):
        fail(f"Не найдено значение для типа сигнала: {signal_type}")


def find_object_by_field(
    item_list: List[ObjectType], field_name: str, value: Any
) -> Optional[ObjectType]:
    """
    Ищет объект в списке объектов по значению одного из полей объекта
    """
    try:
        return next(
            (item for item in item_list if getattr(item, field_name, None) == value),
            None,
        )
    except (AttributeError, TypeError):
        fail(f"Не найдено значение: {str(value)} для поля: {field_name}")


def find_diagnostic_area_by_id(
    flow_areas: List[FlowArea], id_value: int
) -> DiagnosticArea:
    """
    Ищет ДУ по id в списке участков карты течений
    """
    try:
        for flow_area in flow_areas:
            for diagnostic_area in flow_area.diagnosticAreas:
                if diagnostic_area.id == id_value:
                    return diagnostic_area
    except (AttributeError, TypeError):
        fail(f"Не найден ДУ по id: {id_value}")


def to_moscow_timezone(date_str: str) -> datetime:
    """
    Преобразует строку времени в московское время
    """
    try:
        if not isinstance(date_str, str):
            fail(f"Неверный формат: {date_str}")

        if date_str.startswith(("'", '"', "")) or date_str.endswith(("'", '"', "")):
            date_str = date_str.strip().strip("'").strip('"')

        date_utc = datetime.strptime(date_str, BaseExp.OUTPUT_TIME_FORMAT).replace(
            tzinfo=timezone.utc
        )
        return date_utc.astimezone(ZoneInfo("Europe/Moscow"))

    except (TypeError, ValueError):
        fail(f"Не удалось преобразовать время в московское: {date_str}")


async def connect_and_get_parsed_msg_by_tu_id(
    tu_id: int,
    ws_client,
    ws_message_type: str,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    timeout: float = BaseExp.BASIC_MESSAGE_TIMEOUT,
) -> SubscribeAllLeaksInfoReply:
    """
    Подключается, ищет и парсит allLeaksInfo сообщение для конкретного ТУ
    """
    with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
        await ws_client.invoke(ws_invoke_type, ws_invoke_params)

    async def get_parsed_msg():
        """
        Ищет и парсит allLeaksInfo сообщение для конкретного ТУ
        """
        while True:
            payload = await ws_client.receive_by_type(ws_message_type, timeout=timeout)
            parsed_payload = ws_message_parser.parse_all_leaks_info_msg(payload)
            #  Ищет сообщение с нужным ТУ
            if parsed_payload.replyContent.tuId == tu_id:
                return parsed_payload

    try:
        with allure.step(
            f"Получение сообщения с контентом типа: {ws_message_type} для ТУ {tu_id}"
        ):
            return await asyncio.wait_for(get_parsed_msg(), timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Не удалось получить сообщение allLeaksInfo для ТУ {tu_id}")


async def connect_and_get_msg(
    ws_client, ws_invoke_type: str, ws_invoke_params: Any = None
) -> list:
    """
    Подключение типа get к заданной подписке и получение сообщения с заданным типом контента
    """
    with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
        await ws_client.invoke(ws_invoke_type, ws_invoke_params)
        invocation_id = ws_client.invocation_id

    with allure.step(f"Получение входящего сообщения c invocation_id: {invocation_id}"):
        payload = await ws_client.receive_by_invocation_id(invocation_id)

    return payload


async def connect_and_subscribe_msg(
    ws_client,
    ws_message_type: str,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    timeout: float = BaseExp.BASIC_MESSAGE_TIMEOUT,
) -> list:
    """
    Подключение типа subscribe к заданной подписке и получение сообщения с заданным типом контента
    """
    with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
        await ws_client.invoke(ws_invoke_type, ws_invoke_params)

    with allure.step(f"Получение сообщения с контентом типа:  {ws_message_type}"):
        payload = await ws_client.receive_by_type(ws_message_type, timeout=timeout)

    return payload
