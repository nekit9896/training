from __future__ import annotations

import asyncio
import random
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional, Set, TypeVar
from zoneinfo import ZoneInfo

import allure
from pytest import fail

from constants.enums import LdsStatus
import constants.test_constants as test_const
from test_config.models import SubscribeAllLeaksInfoReply, DiagnosticArea, FlowArea
from utils.helpers.ws_message_parser import ws_message_parser

ObjectType = TypeVar("ObjectType")  # создает типовую переменную для поиска объектов в списке
RandomObjectType = TypeVar("RandomObjectType")


def convert_leak_volume_m3(volume: float) -> float:
    """
    Преобразует объем утечки в м3/час
    """
    #  Округляет результат для читабельности
    return round(volume * test_const.MASS_KG, 3)


def get_leak_wait_start_time(datetime_now_tz: datetime, delta_s: int) -> datetime:
    # TODO переименовать в datetime_minus_seconds
    """
    Получает начала диапазона ожидания утечки
    """
    return (datetime_now_tz - timedelta(seconds=delta_s)).replace(microsecond=0)


def calculate_leak_start_time(imitator_start_time: datetime, leak_interval_seconds: int) -> datetime:
    """
    Рассчитывает время начала утечки на основе времени старта имитатора.

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах (LEAK_START_INTERVAL)
    :return: datetime время ожидаемого начала утечки
    """
    return (imitator_start_time + timedelta(seconds=leak_interval_seconds)).replace(microsecond=0)


def calculate_leak_end_time(
    imitator_start_time: datetime, leak_interval_seconds: int, allowed_diff_seconds: int
) -> datetime:
    """
    Рассчитывает крайнее время обнаружения утечки (с учётом допустимой погрешности).

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах (LEAK_START_INTERVAL)
    :param allowed_diff_seconds: допустимая погрешность времени обнаружения (ALLOWED_TIME_DIFF_SECONDS)
    :return: datetime крайнее время обнаружения утечки
    """
    total_seconds = leak_interval_seconds + allowed_diff_seconds
    return (imitator_start_time + timedelta(seconds=total_seconds)).replace(microsecond=0)


def get_leak_time_window(
    imitator_start_time: datetime, leak_interval_seconds: int, allowed_diff_seconds: int, detected_at_tz=None
) -> tuple[datetime, datetime]:
    """
    Возвращает временное окно для проверки времени обнаружения утечки.

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах
    :param allowed_diff_seconds: допустимая погрешность времени обнаружения
    :param detected_at_tz: timezone из времени обнаружения утечки (опционально)
    :return: tuple (leak_start_time, leak_end_time) для использования в is_between проверке
    """
    leak_start = calculate_leak_start_time(imitator_start_time, leak_interval_seconds)
    leak_end = calculate_leak_end_time(imitator_start_time, leak_interval_seconds, allowed_diff_seconds)

    # Если передан timezone, применяем его к временам для корректного сравнения
    if detected_at_tz is not None:
        leak_start = leak_start.replace(tzinfo=detected_at_tz)
        leak_end = leak_end.replace(tzinfo=detected_at_tz)

    return leak_start, leak_end


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

    longest_flow_area = max(flow_areas, key=lambda flow_area: len(flow_area.diagnosticAreas))
    return longest_flow_area


def determine_lds_status_by_priority(lds_status_set: Set[int]) -> int:
    """
    Определяет режим работы СОУ по приоритету и наличию режимов работы у ДУ на самом протяженном участки карты течений
    """
    lds_status_priority = [
        LdsStatus.FAULTY.value,
        LdsStatus.INITIALIZATION.value,
        LdsStatus.DEGRADATION.value,
        LdsStatus.SERVICEABLE.value,
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
            if sensor_signal.address is not None and str(sensor_signal.address).endswith(address_suffix):
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
            if sensor_signal.signalType is not None and sensor_signal.signalType == signal_type:
                return sensor_signal.value
        fail(f"Не найдено значение для типа сигнала: {signal_type}")
    except (AttributeError, TypeError):
        fail(f"Не найдено значение для типа сигнала: {signal_type}")


def find_object_by_field(item_list: List[ObjectType], field_name: str, value: Any) -> Optional[ObjectType]:
    """
    Ищет объект в списке объектов по значению одного из полей объекта
    """
    try:
        return next((item for item in item_list if getattr(item, field_name, None) == value), None)
    except (AttributeError, TypeError):
        fail(f"Не найдено значение: {str(value)} для поля: {field_name}")


def find_diagnostic_area_by_id(flow_areas: List[FlowArea], id_value: int) -> DiagnosticArea:
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


def ensure_moscow_timezone(dt: datetime) -> datetime:
    """
    Конвертирует datetime в московское время.
    
    :param dt: datetime объект (может быть naive или с любой timezone)
    :return: datetime в московской таймзоне
    """
    if dt is None:
        return dt
    
    # Если datetime без timezone - считаем что это UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    
    # Конвертируем в московское время
    return dt.astimezone(ZoneInfo("Europe/Moscow"))


def to_moscow_timezone(date_str: str) -> datetime:
    """
    Преобразует строку времени в московское время
    """
    try:
        if not isinstance(date_str, str):
            fail(f"Неверный формат: {date_str}")

        if date_str.startswith(("'", '"', '')) or date_str.endswith(("'", '"', '')):
            date_str = date_str.strip().strip("'").strip('"')

        date_utc = datetime.strptime(date_str, test_const.OUTPUT_TIME_FORMAT).replace(tzinfo=timezone.utc)
        return date_utc.astimezone(ZoneInfo("Europe/Moscow"))

    except (TypeError, ValueError):
        fail(f"Не удалось преобразовать время в московское: {date_str}")


async def connect_and_get_parsed_msg_by_tu_id(
    tu_id: int,
    ws_client,
    ws_message_type: str,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    timeout: float = test_const.BASIC_MESSAGE_TIMEOUT,
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
        with allure.step(f"Получение сообщения с контентом типа: {ws_message_type} для ТУ {tu_id}"):
            return await asyncio.wait_for(get_parsed_msg(), timeout=timeout)
    except asyncio.TimeoutError:
        raise TimeoutError(f"Не удалось получить сообщение allLeaksInfo для ТУ {tu_id}")


async def connect_and_get_msg(ws_client, ws_invoke_type: str, ws_invoke_params: Any = None) -> list:
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
    timeout: float = test_const.BASIC_MESSAGE_TIMEOUT,
) -> list:
    """
    Подключение типа subscribe к заданной подписке и получение сообщения с заданным типом контента
    """
    with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
        await ws_client.invoke(ws_invoke_type, ws_invoke_params)

    with allure.step(f"Получение сообщения с контентом типа:  {ws_message_type}"):
        payload = await ws_client.receive_by_type(ws_message_type, timeout=timeout)

    return payload
