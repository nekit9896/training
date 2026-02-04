from __future__ import annotations

import asyncio
import random
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, List, Set, Tuple, Type, TypeVar
from zoneinfo import ZoneInfo

import allure
from pytest import fail

from clients.websocket_client import WebSocketClient
from constants.enums import LdsStatus
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import GetMessagesRequest
from models.subscribe_all_leaks_info_model import SubscribeAllLeaksInfoReply
from models.subscribe_common_scheme_model import DiagnosticArea, FlowArea
from utils.helpers.ws_message_parser import ws_message_parser

ObjectType = TypeVar("ObjectType")  # создает типовую переменную для поиска объектов в списке
RandomObjectType = TypeVar("RandomObjectType")


def convert_leak_volume_m3(volume: float) -> float:
    """
    Преобразует объем утечки в м3/час
    """
    #  Округляет результат для читабельности
    return round(volume * TestConst.MASS_KG, 3)


def datetime_minus_seconds(datetime_obj: datetime, delta_s: int) -> datetime:
    """
    Вычитает время в секундах из datetime
    """
    return (datetime_obj - timedelta(seconds=delta_s)).replace(microsecond=0)


def calculate_leak_start_time(imitator_start_time: datetime, leak_interval_seconds: int) -> datetime:
    """
    Рассчитывает время начала утечки на основе времени старта имитатора.

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах (LEAK_START_INTERVAL)
    :return: datetime время ожидаемого начала утечки
    """
    if not imitator_start_time:
        fail("Пришло пустое значение imitator_start_time")
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
    if not imitator_start_time:
        fail("Пришло пустое значение imitator_start_time")
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
    leak_start = leak_start.replace(tzinfo=detected_at_tz)
    leak_end = leak_end.replace(tzinfo=detected_at_tz)

    return leak_start, leak_end


def ensure_moscow_timezone(input_datetime: datetime) -> None | datetime:
    """
    Конвертирует datetime в московское время, если оно не в московской таймзоне.

    :param input_datetime: datetime объект
    :return: datetime в московской таймзоне
    """
    if input_datetime is None:
        return input_datetime

    # Если datetime без timezone - считаем что это UTC
    if input_datetime.tzinfo is None:
        input_datetime = input_datetime.replace(tzinfo=timezone.utc)

    # Конвертируем в московское время
    return input_datetime.astimezone(ZoneInfo("Europe/Moscow"))


def get_random_item(item_list: List[RandomObjectType]) -> RandomObjectType:
    """
    Получает случайный объект из списка
    """
    if not item_list:
        fail("Пустой список объектов")
    try:
        return random.choice(item_list)
    except (TypeError, ValueError):
        fail(f"Не удалось получить случайный элемент из списка: {item_list}")


def get_longest_flow_area(flow_areas: List[FlowArea]) -> FlowArea:
    """
    Получает самый протяженный участок карты течения по количеству ДУ из списка всех участков
    """
    if not flow_areas:
        fail("Cписок flow_areas пустой")
    try:
        longest_flow_area = max(flow_areas, key=lambda flow_area: len(flow_area.diagnosticAreas))
        return longest_flow_area
    except (TypeError, ValueError):
        fail(f"Не найден протяженный участок из списка flow_areas: {flow_areas}.")


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
    if not lds_status_set:
        fail("Пустой список режимов СОУ ДУ")
    try:
        for status in lds_status_priority:
            if status in lds_status_set:
                return status
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        fail("Не удалось определить режим работу СОУ.")


def find_signal_type_by_address_suffix(signals_list: list, address_suffix: str) -> int:
    """
    Ищет в списке сигналов тип сигнала по части адреса
    """
    if not signals_list:
        fail("Пустой список сигналов")
    try:
        for sensor_signal in signals_list:
            if sensor_signal.address is not None and str(sensor_signal.address).endswith(address_suffix):
                return sensor_signal.signalType
        fail(f"Не найден тип сигнала по части адреса: {address_suffix} из списка: {signals_list}")
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        fail(f"Не найден тип сигнала по части адреса: {address_suffix} из списка: {signals_list}")


def find_signal_val_by_signal_type(signals_list: list, signal_type: int) -> str:
    """
    Ищет в списке сигналов значение сигнала по типу
    """
    if not signals_list:
        fail("Пустой список сигналов")
    try:
        for sensor_signal in signals_list:
            if sensor_signal.signalType is not None and sensor_signal.signalType == signal_type:
                return sensor_signal.value
        fail(f"Не найдено значение для типа сигнала: {signal_type} из списка: {signals_list}")
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        fail(f"Не найдено значение для типа сигнала: {signal_type} из списка: {signals_list}")


def find_object_by_field(item_list: List[ObjectType], field_name: str, value: Any) -> ObjectType:
    """
    Ищет объект в списке объектов по значению одного из полей объекта
    """
    if not item_list:
        fail("Список объектов пуст")
    try:
        return next((item for item in item_list if getattr(item, field_name) == value))
    except Exception:
        fail(f"Не найдено значение: {value} для поля: {field_name}, в списке: {item_list}.")


def find_diagnostic_area_by_id(flow_areas: List[FlowArea], id_value: int) -> DiagnosticArea:
    """
    Ищет ДУ по id в списке участков карты течений
    """
    if not flow_areas:
        fail("Пустой список flow_areas")
    try:
        for flow_area in flow_areas:
            for diagnostic_area in flow_area.diagnosticAreas:
                if diagnostic_area.id == id_value:
                    return diagnostic_area
        fail(f"Не найден ДУ по id: {id_value}.")
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        fail(f"Не найден ДУ по id: {id_value}.")


def to_moscow_timezone(date_str: str) -> datetime:
    """
    Преобразует строку времени в московское время
    """
    if not date_str or not date_str.strip():
        fail("Пришло пустое значение для преобразования в московское время")

    try:
        if date_str.startswith(("'", '"', '')) or date_str.endswith(("'", '"', '')):
            date_str = date_str.strip().strip("'").strip('"')

        date_utc = datetime.strptime(date_str, TestConst.OUTPUT_TIME_FORMAT).replace(tzinfo=timezone.utc)
        return date_utc.astimezone(ZoneInfo("Europe/Moscow"))

    except (AttributeError, TypeError, ValueError):
        fail(f"Не удалось преобразовать время в московское: {date_str}.")


def create_dict_from_dataclass(cls: Type, **kwargs) -> dict:
    """Создает словарь из экземпляра dataclass c нужными параметрами"""
    if not is_dataclass(cls):
        fail(f"{cls} не dataclass")
    instance = cls(**kwargs)
    return asdict(instance)


def create_journal_req_body(**kwargs) -> dict:
    """Создает дефолтные параметры запроса к журналу"""
    return create_dict_from_dataclass(GetMessagesRequest, **kwargs)


def parse_journal_msg_value(value: str) -> Tuple[float, float]:
    """Парсит поле value в сообщении журнала"""
    # ищет группы цифр с точкой в строке
    try:
        coordinate_and_volume = re.findall(TestConst.DIGITS_WITH_DOT_PATTERN, value)
    except (TypeError, ValueError):
        fail("Не удалось получить данные из поля value в сообщении журнала")
    try:
        coordinate, volume = coordinate_and_volume
        return float(coordinate), float(volume)
    except (TypeError, ValueError):
        fail("Ошибка распаковки данных из поля value в сообщении журнала")


async def connect(ws_client: WebSocketClient, ws_invoke_type: str, ws_invoke_params: Any = None) -> None:
    """
    Подключение к заданной подписке
    """
    try:
        with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
            await ws_client.invoke(ws_invoke_type, ws_invoke_params)
    except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
        fail(f"Не удалось отправить сообщение типа: {ws_invoke_type} c параметрами {ws_invoke_params}. Ошибка: {error}")


async def connect_and_get_parsed_msg_by_tu_id(
    tu_id: int,
    ws_client: WebSocketClient,
    ws_message_type: str,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    timeout: float = TestConst.BASIC_MESSAGE_TIMEOUT,
) -> SubscribeAllLeaksInfoReply:
    """
    Подключается, ищет и парсит allLeaksInfo сообщение для конкретного ТУ
    """
    await connect(ws_client, ws_invoke_type, ws_invoke_params)

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
    except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
        fail(f"Не удалось получить сообщение allLeaksInfo для ТУ {tu_id}. Ошибка: {error}")


async def connect_and_get_msg(ws_client: WebSocketClient, ws_invoke_type: str, ws_invoke_params: Any = None) -> list:
    """
    Подключение типа get к заданной подписке и получение сообщения с заданным типом контента
    """
    await connect(ws_client, ws_invoke_type, ws_invoke_params)
    invocation_id = ws_client.invocation_id

    try:
        with allure.step(f"Получение входящего сообщения c invocation_id: {invocation_id}"):
            payload = await ws_client.receive_by_invocation_id(invocation_id)
        return payload
    except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
        fail(f"Не удалось получить сообщение типа: {ws_invoke_type}. Ошибка: {error}")


async def connect_and_subscribe_msg(
    ws_client: WebSocketClient,
    ws_message_type: str,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    timeout: float = TestConst.BASIC_MESSAGE_TIMEOUT,
) -> list:
    """
    Подключение типа subscribe к заданной подписке и получение сообщения с заданным типом контента
    """
    await connect(ws_client, ws_invoke_type, ws_invoke_params)
    try:
        with allure.step(f"Получение сообщения с контентом типа: {ws_message_type}"):
            payload = await ws_client.receive_by_type(ws_message_type, timeout=timeout)

        return payload
    except (asyncio.TimeoutError, OSError, ConnectionError, ConnectionResetError) as error:
        fail(f"Не удалось получить сообщение типа: {ws_invoke_type}. Ошибка: {error}")
