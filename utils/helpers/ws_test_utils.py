from __future__ import annotations

import asyncio
import pprint
import random
import re
from dataclasses import asdict, is_dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum, IntFlag
from typing import Any, List, Optional, Set, Type, TypeVar
from zoneinfo import ZoneInfo

import allure
from msgpack import Timestamp as MsgpackTimestamp
from pytest import fail

from clients.websocket_client import WebSocketClient
from constants.architecture_constants import WebSocketClientConstants as WS_Const
from constants.enums import (
    ConfirmationStatus,
    ExportStatus,
    LdsStatus,
    LdsStatusDegradation,
    LdsStatusFaulty,
    LdsStatusInitialization,
    LeakStatus,
    ReplyStatus,
    StationaryReason,
    StationaryStatus,
    StoppedPumpingReason,
    UnStationaryReason,
)
from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportReportConstants as ReportConst
from models.export_reports_model import ReportDataExportedContent, ReportDataExportedNotification
from models.get_messages_model import GetMessagesRequest
from models.subscribe_all_leaks_info_model import SubscribeAllLeaksInfoReply
from models.subscribe_common_scheme_model import DiagnosticArea, FlowArea
from models.subscribe_leaks_model import Leak
from models.subscribe_main_page_info_model import MainPageLeakInfo
from utils.helpers.ws_message_parser import ws_message_parser
from utils.msgpack_utils.message_filters import is_desired_invocation_id, is_desired_type

ObjectType = TypeVar("ObjectType")  # создает типовую переменную для поиска объектов в списке
RandomObjectType = TypeVar("RandomObjectType")
Event = TypeVar("Event")


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


def calculate_leak_start_time(imitator_start_time: datetime, leak_interval_seconds: int) -> Optional[datetime]:
    """
    Рассчитывает время начала утечки на основе времени старта имитатора.

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах (LEAK_START_INTERVAL)
    :return: datetime время ожидаемого начала утечки
    """
    if not imitator_start_time:
        return None
    return (imitator_start_time + timedelta(seconds=leak_interval_seconds)).replace(microsecond=0)


def calculate_leak_end_time(
    imitator_start_time: datetime, leak_interval_seconds: int, allowed_diff_seconds: int
) -> Optional[datetime]:
    """
    Рассчитывает крайнее время обнаружения утечки (с учётом допустимой погрешности).

    :param imitator_start_time: datetime объект времени старта имитатора
    :param leak_interval_seconds: интервал от старта до утечки в секундах (LEAK_START_INTERVAL)
    :param allowed_diff_seconds: допустимая погрешность времени обнаружения (ALLOWED_TIME_DIFF_SECONDS)
    :return: datetime крайнее время обнаружения утечки
    """
    if not imitator_start_time:
        return None
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
    if detected_at_tz:
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
    return input_datetime.astimezone(ZoneInfo(TestConst.ZONE_INFO))


def report_time_offset_hours(tz_name: str = TestConst.ZONE_INFO) -> Optional[int]:
    """
    Смещение часового пояса (часы от UTC) для поля timeOffset в запросах отчётов.
    """
    now = datetime.now(ZoneInfo(tz_name))
    utc_offset = now.utcoffset()
    if utc_offset is None:
        return None
    return int(utc_offset.total_seconds() // TestConst.SECONDS_PER_HOUR)


def localize_as_moscow(input_datetime: datetime) -> None | datetime:
    """
    Присваивает datetime московский часовой пояс без сдвига времени.
    Если datetime уже имеет timezone - конвертирует в московское время.
    """
    if input_datetime is None:
        return input_datetime

    moscow_tz = ZoneInfo(TestConst.ZONE_INFO)
    if input_datetime.tzinfo is None:
        return input_datetime.replace(tzinfo=moscow_tz)
    return input_datetime.astimezone(moscow_tz)


def format_datetime_moscow(value: Optional[datetime]) -> str:
    """Строковое представление datetime в Europe/Moscow для вложений Allure."""
    if value is None:
        return "None"
    return str(localize_as_moscow(value))


def get_rejection_time_window(
    imitator_start_time: datetime,
    start_seconds: int | float,
    reserve_seconds: int | float = 0,
) -> tuple[datetime, datetime]:
    """
    Возвращает временное окно для проверки сообщения об отбраковке.
    """
    imitator_msk = localize_as_moscow(imitator_start_time)
    range_start = imitator_msk + timedelta(seconds=start_seconds - reserve_seconds)
    range_end = localize_as_moscow(datetime.now())
    return range_start, range_end


def find_rejection_journal_message(
    messages_info: List[ObjectType],
    tag: str,
    range_start: datetime,
    range_end: datetime,
    technological_section: str,
    expected_event: str,
) -> tuple[list[ObjectType], ObjectType | None]:
    """
    Фильтрует сообщения журнала по tag и временному диапазону,
    затем ищет целевое сообщение по technologicalSection и event.
    """
    time_filtered = [
        msg for msg in messages_info if msg.tag == tag and range_start <= ensure_moscow_timezone(msg.time) <= range_end
    ]
    time_filtered.sort(key=lambda msg: ensure_moscow_timezone(msg.time), reverse=True)

    target_msg = next(
        (
            msg
            for msg in time_filtered
            if msg.technologicalSection == technological_section and msg.event.rstrip() == expected_event
        ),
        None,
    )
    return time_filtered, target_msg


def get_random_item(item_list: List[RandomObjectType]) -> RandomObjectType:
    """
    Получает случайный объект из списка
    """
    if not item_list:
        return None
    try:
        return random.choice(item_list)
    except (TypeError, ValueError):
        return None


def get_longest_flow_area(flow_areas: List[FlowArea]) -> Optional[FlowArea]:
    """
    Получает самый протяженный участок карты течения по количеству ДУ из списка всех участков
    """
    if not flow_areas:
        return None
    try:
        longest_flow_area = max(flow_areas, key=lambda flow_area: len(flow_area.diagnosticAreas))
        return longest_flow_area
    except (TypeError, ValueError):
        return None


def determine_lds_status_by_priority(lds_status_set: Set[int]) -> Optional[int]:
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
        return None
    try:
        for status in lds_status_priority:
            if status in lds_status_set:
                return status
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None


def find_signal_type_by_address_suffix(signals_list: list, address_suffix: str) -> Optional[int]:
    """
    Ищет в списке сигналов тип сигнала по части адреса
    """
    if not signals_list:
        return None
    try:
        for sensor_signal in signals_list:
            if sensor_signal.address is not None and str(sensor_signal.address).endswith(address_suffix):
                return sensor_signal.signalType
        return None
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None


def find_signal_val_by_signal_type(signals_list: list, signal_type: int) -> Optional[str]:
    """
    Ищет в списке сигналов значение сигнала по типу
    """
    if not signals_list:
        return None
    try:
        for sensor_signal in signals_list:
            if sensor_signal.signalType is not None and sensor_signal.signalType == signal_type:
                return sensor_signal.value
        return None
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None


def find_object_by_field(item_list: List[ObjectType], field_name: str, value: Any) -> ObjectType:
    """
    Ищет объект в списке объектов по значению одного из полей объекта
    """
    if not item_list:
        return None
    try:
        return next((item for item in item_list if getattr(item, field_name) == value))
    except Exception:
        return None


def find_object_by_a_few_fields(item_list: List[ObjectType], fields_dict: dict) -> ObjectType:
    """
    Ищет объект в списке объектов по значениям нескольких полей
    """
    if not item_list:
        return None

    return next(
        (item for item in item_list if all(getattr(item, field) == value for field, value in fields_dict.items())), None
    )


def parse_event(event_value: str) -> tuple[str | None, str | None]:
    """
    Разделяет строку события на имя и причину, вложенную с скобки
    """
    if not event_value or not isinstance(event_value, str):
        return None, None

    # Паттерн для "Состояние режима (Причина)"
    pattern = r'^([^\(]+?)\s*\(([^\)]+)\)\s*$'
    match = re.match(pattern, event_value)

    if match:
        mode_part = match.group(1).strip()
        reason_part = match.group(2).strip()
        return (mode_part if mode_part else None, reason_part if reason_part else None)
    # Если значение события не соответствует паттерну, возвращаю текст, если нет текста, тогда None
    return event_value, None


def get_signal(site_message, signal_type):
    if not site_message:
        return None
    return next((s for s in site_message.signals if s.signalType == signal_type.value), None)


def get_value(obj):
    return getattr(obj, "value", None)


def find_confirmed_leaks(item_list: List[Leak]) -> List[Leak]:
    """Ищет подтвержденные утечки"""
    try:
        return [
            item
            for item in item_list
            if item.confirmationStatus == ConfirmationStatus.CONFIRMED.value and item.detectedAt is not None
        ]
    except (AttributeError, KeyError, TypeError, ValueError):
        return []


def find_confirmed_leaks_on_main_page(item_list: List[MainPageLeakInfo]) -> List[MainPageLeakInfo]:
    """Ищет подтвержденные утечки"""
    try:
        return [
            item
            for item in item_list
            if item.leakStatus == LeakStatus.CONFIRMED.value and item.leakDetectedAt is not None
        ]
    except (AttributeError, KeyError, TypeError, ValueError):
        return []


def find_diagnostic_area_by_id(flow_areas: List[FlowArea], id_value: int) -> Optional[DiagnosticArea]:
    """
    Ищет ДУ по id в списке участков карты течений, исключает дубликаты по количеству pipeIds
    """
    candidates = []
    if not flow_areas:
        return None
    try:
        for flow_area in flow_areas:
            for diagnostic_area in flow_area.diagnosticAreas:
                if diagnostic_area.id == id_value:
                    candidates.append(diagnostic_area)
        if not candidates:
            return None
        elif len(candidates) == 1:
            return candidates[0]
        else:
            # Среди дубликатов ищет ДУ с наибольшим количеством pipeIds
            return max(candidates, key=lambda candidate: len(candidate.pipeIds))
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None


def find_diagnostic_area_by_pipe_id(flow_areas: List[FlowArea], pipe_id: int) -> Optional[DiagnosticArea]:
    """
    Ищет ДУ по pipe id в списке участков карты течений, исключает дубликаты по количеству pipeIds
    """
    candidates = []
    if not flow_areas:
        return None
    try:
        for flow_area in flow_areas:
            for diagnostic_area in flow_area.diagnosticAreas:
                if diagnostic_area.pipeIds and pipe_id in diagnostic_area.pipeIds:
                    candidates.append(diagnostic_area)
        if not candidates:
            return None
        elif len(candidates) == 1:
            return candidates[0]
        else:
            # Среди дубликатов ищет ДУ с наибольшим количеством pipeIds
            return max(candidates, key=lambda candidate: len(candidate.pipeIds))
    except (AttributeError, KeyError, RuntimeError, TypeError, ValueError):
        return None


def find_diagnostic_areas_by_ids(flow_areas: List[FlowArea], id_list: List[int]) -> List[DiagnosticArea]:
    """
    Получает список ДУ из списка flow_areas по списку id
    """
    diagnostic_areas = [
        result
        for diagnostic_area_id in id_list
        if (result := find_diagnostic_area_by_id(flow_areas, diagnostic_area_id)) is not None
    ]

    return diagnostic_areas


def find_diagnostic_areas_by_pipe_ids(flow_areas: List[FlowArea], id_list: List[int]) -> List[DiagnosticArea]:
    """
    Получает список ДУ из списка flow_areas по списку pipe id
    """
    diagnostic_areas = [
        result for pipe_id in id_list if (result := find_diagnostic_area_by_pipe_id(flow_areas, pipe_id)) is not None
    ]

    return diagnostic_areas


def find_base_diagnostic_areas(flow_areas: List[FlowArea]) -> List[DiagnosticArea]:
    """
    Получает список базовых ДУ из списка flow_areas
    """
    return find_diagnostic_areas_by_ids(flow_areas, TestConst.DIAGNOSTIC_AREA_BASE_IDS)


def find_leak_by_coordinate(
    leaks_list: List[ObjectType], expected_coordinate: float, tolerance: float = TestConst.ALLOWED_DISTANCE_DIFF_METERS
) -> ObjectType:
    """
    Ищет утечку в списке по координатам с допустимой погрешностью
    """
    if not leaks_list:
        return None

    for leak in leaks_list:
        leak_coordinate = getattr(leak, "leakCoordinate")
        if leak_coordinate is None or "":
            continue
        if abs(leak_coordinate - expected_coordinate) <= tolerance:
            return leak
    return None


def to_moscow_timezone(date_str: str) -> Optional[datetime]:
    """
    Преобразует строку времени в московское время
    """
    if not date_str or not date_str.strip():
        return None

    try:
        if date_str.startswith(("'", '"', '')) or date_str.endswith(("'", '"', '')):
            date_str = date_str.strip().strip("'").strip('"')

        date_utc = datetime.strptime(date_str, TestConst.OUTPUT_TIME_FORMAT).replace(tzinfo=timezone.utc)
        return date_utc.astimezone(ZoneInfo(TestConst.ZONE_INFO))

    except (AttributeError, TypeError, ValueError):
        return None


def create_dict_from_dataclass(cls: Type, **kwargs) -> Optional[dict]:
    """Создает словарь из экземпляра dataclass c нужными параметрами"""
    if not is_dataclass(cls):
        return None
    instance = cls(**kwargs)
    return asdict(instance)


def datetime_to_msgpack_timestamp(dt: datetime) -> list:
    """Конвертирует datetime в формат [Timestamp(seconds, nanoseconds), tz_offset] для отправки на бэкенд."""
    return [MsgpackTimestamp(seconds=int(dt.timestamp()), nanoseconds=0), 0]


def create_journal_req_body(**kwargs) -> dict:
    """Создает дефолтные параметры запроса к журналу"""
    result = create_dict_from_dataclass(GetMessagesRequest, **kwargs)
    period = result.get('periodTime')
    if period:
        for key in ('start', 'end'):
            if isinstance(period.get(key), datetime):
                period[key] = datetime_to_msgpack_timestamp(period[key])
    return result


def extract_first_number(value: object) -> Optional[float]:
    """
    Извлекает первое число из ячейки (int/float/str вида '55.55 км', '111.11 м3/ч').
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, str):
        matches = re.findall(TestConst.DIGITS_WITH_DOT_PATTERN, value)
        if matches:
            try:
                return float(matches[0].replace(",", "."))
            except ValueError:
                return None
    return None


def _attach_ws_poll_failure(
    collected_messages: List[Any],
    total_wait_seconds: float,
    expected_message_type: str,
) -> None:
    """Краткая сводка и pprint каждого WS-сообщения при таймауте поллинга."""
    allure.attach(
        "\n".join(
            [
                f"Таймаут ожидания: {total_wait_seconds} с",
                f"Ожидаемый тип сообщения: {expected_message_type}",
                f"Всего сообщений за период поллинга: {len(collected_messages)}",
            ]
        ),
        name="WS poll timeout",
        attachment_type=allure.attachment_type.TEXT,
    )
    for msg in collected_messages:
        allure.attach(
            pprint.pformat(msg, width=120, sort_dicts=False),
            name="received ws message",
            attachment_type=allure.attachment_type.TEXT,
        )


def _attach_ws_reply_parse_failure(
    reply_payload: Optional[Any],
    invocation_id: str,
    request_name: str,
    error: BaseException,
) -> None:
    """Прикрепляет к Allure ответ бэка при ошибке парсинга."""
    allure.attach(
        "\n".join(
            [
                f"Запрос: {request_name}",
                f"invocation_id: {invocation_id}",
                f"Ошибка: {error}",
            ]
        ),
        name="WS parse failure",
        attachment_type=allure.attachment_type.TEXT,
    )
    if reply_payload is not None:
        allure.attach(
            pprint.pformat(reply_payload, width=120, sort_dicts=False),
            name="received ws message",
            attachment_type=allure.attachment_type.TEXT,
        )


def _drain_recv_queue(ws_client: WebSocketClient) -> List[Any]:
    """Забирает все сообщения из очереди ws без блокирующего receive_by_..."""
    messages: List[Any] = []
    while not ws_client.recv_queue.empty():
        try:
            messages.append(ws_client.recv_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return messages


def _find_valid_report_export_notification(
    messages: List[Any],
    parser,
    notification_type: str,
) -> Optional[ReportDataExportedNotification]:
    """Ищет среди уже полученных сообщений успешную ReportDataExportedNotification."""
    for msg in messages:
        if not isinstance(msg, list) or not is_desired_type(msg, notification_type):
            continue
        try:
            notification = parser.parse_report_data_exported_notification_msg(msg)
        except (ValueError, TypeError, KeyError):
            continue
        if notification.replyStatus != ReplyStatus.OK.value:
            continue
        content: Optional[ReportDataExportedContent] = notification.replyContent
        if content is None:
            continue
        if content.exportStatus != ExportStatus.DONE:
            continue
        return notification
    return None


async def poll_for_report_export_notification(
    ws_client: WebSocketClient,
    parser,
    total_wait_seconds: float,
    poll_interval_seconds: float,
) -> Optional[Any]:
    """
    Собирает сообщения из очереди ws и ищет ReportDataExportedNotification с успешным exportStatus.
    При таймауте прикрепляет к Allure все полученные за период сообщения.
    """

    deadline = asyncio.get_event_loop().time() + total_wait_seconds
    collected_messages: List[Any] = []
    ws_client.suppress_recv_logging = True
    parser.suppress_recv_logging = True
    try:
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(poll_interval_seconds)
            batch = _drain_recv_queue(ws_client)
            collected_messages.extend(batch)
            notification = _find_valid_report_export_notification(
                batch, parser, ReportConst.REPORT_DATA_EXPORTED_NOTIFICATION
            )
            if notification is not None:
                return notification
    finally:
        collected_messages.extend(_drain_recv_queue(ws_client))
        ws_client.suppress_recv_logging = False
        parser.suppress_recv_logging = False

    _attach_ws_poll_failure(
        collected_messages,
        total_wait_seconds,
        ReportConst.REPORT_DATA_EXPORTED_NOTIFICATION,
    )
    return None


def _find_ws_reply_by_invocation_id(messages: List[Any], invocation_id: str, parser) -> Optional[list]:
    """
    Ищет последний ответ с заданным invocation_id и телом replyStatus.
    """
    reply_payload = None
    for msg in messages:
        if not isinstance(msg, list) or not is_desired_invocation_id(msg, invocation_id):
            continue
        if parser.find_reply_status_in_ws_msg(msg):
            reply_payload = msg
    return reply_payload


async def poll_for_exported_file(
    ws_client: WebSocketClient,
    parser,
    list_limit: int,
    expected_data_type: Any,
    name_substring: str,
    tu_name_substring: str,
    period_start: datetime,
    period_end: datetime,
    total_wait_seconds: float,
    poll_interval_seconds: float,
    period_tolerance_minutes: int = ReportConst.REPORT_PERIOD_TOLERANCE_MINUTES,
) -> Optional[Any]:
    """
    Периодически шлёт GetExportedDataListRequest, забирает ответы из очереди
    по invocation_id среди всех накопленных сообщений.
    При таймауте или ошибке парсинга прикрепляет к Allure полученные ответы.
    """

    deadline = asyncio.get_event_loop().time() + total_wait_seconds
    last_items_count = -1
    collected_messages: List[Any] = []
    request_name = ReportConst.GET_EXPORTED_DATA_LIST_REQUEST
    ws_client.suppress_recv_logging = True
    parser.suppress_recv_logging = True
    try:
        while asyncio.get_event_loop().time() < deadline:
            drained_before_request = _drain_recv_queue(ws_client)
            collected_messages.extend(drained_before_request)
            await connect(
                ws_client,
                request_name,
                {"limit": list_limit},
            )
            invocation_id = ws_client.invocation_id
            await asyncio.sleep(poll_interval_seconds)

            batch = _drain_recv_queue(ws_client)
            collected_messages.extend(batch)
            list_reply_payload = _find_ws_reply_by_invocation_id(batch, invocation_id, parser)

            if list_reply_payload is None:
                continue

            try:
                parsed_payload = parser.parse_exported_data_list_msg(list_reply_payload)
            except Exception as error:
                _attach_ws_reply_parse_failure(list_reply_payload, invocation_id, request_name, error)
                for msg in collected_messages:
                    allure.attach(
                        pprint.pformat(msg, width=120, sort_dicts=False),
                        name="received ws message",
                        attachment_type=allure.attachment_type.TEXT,
                    )
                fail(f"Не удалось разобрать ответ на {request_name}: {error}")

            items = []
            if parsed_payload.replyContent is not None:
                items = parsed_payload.replyContent.exportedData or []

            if len(items) != last_items_count:
                allure.attach(
                    "\n".join(
                        f"id={item.id}, name={item.name}, type={item.exportedDataType}, "
                        f"start={format_datetime_moscow(item.start)}, end={format_datetime_moscow(item.end)}"
                        for item in items
                    ),
                    name=f"Список сформированных файлов (всего: {len(items)})",
                    attachment_type=allure.attachment_type.TEXT,
                )
                last_items_count = len(items)

            match = find_matching_exported_item(
                items=items,
                expected_data_type=expected_data_type,
                name_substring=name_substring,
                tu_name_substring=tu_name_substring,
                period_start=period_start,
                period_end=period_end,
                period_tolerance_minutes=period_tolerance_minutes,
            )
            if match is not None:
                return match
    finally:
        collected_messages.extend(_drain_recv_queue(ws_client))
        ws_client.suppress_recv_logging = False
        parser.suppress_recv_logging = False

    _attach_ws_poll_failure(
        collected_messages,
        total_wait_seconds,
        request_name,
    )
    return None


def _normalize_report_period_datetime(value: datetime) -> datetime:
    """Приводит datetime периода отчёта к московскому времени без микросекунд."""
    return localize_as_moscow(value).replace(microsecond=0)


def _exported_item_period_matches(
    item_start: datetime,
    item_end: datetime,
    period_start: datetime,
    period_end: datetime,
    tolerance_minutes: int,
) -> bool:
    """Проверяет start/end элемента списка в пределах периода запроса +- tolerance_minutes."""
    item_start_norm = _normalize_report_period_datetime(item_start)
    item_end_norm = _normalize_report_period_datetime(item_end)
    period_start_norm = _normalize_report_period_datetime(period_start)
    period_end_norm = _normalize_report_period_datetime(period_end)
    delta = timedelta(minutes=tolerance_minutes)
    return (period_start_norm - delta) <= item_start_norm <= (period_start_norm + delta) and (
        period_end_norm - delta
    ) <= item_end_norm <= (period_end_norm + delta)


def _normalize_report_text_for_match(text: str) -> str:
    return text.lower().replace("ё", "е")


def find_matching_exported_item(
    items: List[Any],
    expected_data_type: Any,
    name_substring: str,
    tu_name_substring: str,
    period_start: datetime,
    period_end: datetime,
    period_tolerance_minutes: int = ReportConst.REPORT_PERIOD_TOLERANCE_MINUTES,
) -> Optional[Any]:
    """
    Ищет элемент списка по типу, подстрокам в имени (отчёт + ТУ) и периоду start/end с допуском.
    """
    name_substring_normalized = _normalize_report_text_for_match(name_substring)
    tu_name_normalized = _normalize_report_text_for_match(tu_name_substring)

    matched_items = []
    for item in items:
        if item.exportedDataType != expected_data_type:
            continue
        item_name_normalized = _normalize_report_text_for_match(item.name or "")
        if name_substring_normalized not in item_name_normalized:
            continue
        if tu_name_normalized not in item_name_normalized:
            continue
        if item.start is None or item.end is None:
            continue
        if not _exported_item_period_matches(item.start, item.end, period_start, period_end, period_tolerance_minutes):
            continue
        matched_items.append(item)

    if not matched_items:
        return None
    return max(matched_items, key=lambda exported_item: exported_item.id)


def parse_journal_msg_value(value: str) -> tuple:
    """Парсит поле value в сообщении журнала"""
    try:
        # ищет группы цифр с точкой в строке
        matches = re.findall(TestConst.DIGITS_WITH_DOT_PATTERN, value)
        coordinate, volume = (matches + [None, None])[:2]
        if coordinate is not None:
            try:
                coordinate = float(coordinate)
            except ValueError:
                coordinate = None
        if volume is not None:
            try:
                volume = float(volume)
            except ValueError:
                volume = None
        return coordinate, volume
    except (AttributeError, TypeError, ValueError):
        return None, None


def parse_bit_flags(
    value: int, enum_cls: Type[IntEnum | IntFlag], failures: Optional[List[str]] = None
) -> List[IntFlag]:
    """
    Распаковка битовых флагов
    """
    # 0 - это валидное состояние когда причин нет, в прошлой реализации тест бы падал если причин нет
    # хотя это может быть ожидаемо, например при тестировании исправности или где-нибудь еще
    if value == 0:
        return []

    found_flags = [flag for flag in enum_cls if value & flag.value]
    known_bits = sum(flag.value for flag in found_flags)

    if known_bits != value:
        unknown_bits = value ^ known_bits
        error_message = f"Неизвестные биты при распаковке {enum_cls.__name__}: {unknown_bits}"
        if failures is not None:
            failures.append(error_message)
        else:
            fail(f"Неизвестные биты при распаковке {enum_cls.__name__}: {unknown_bits}")

    # та же сортировка только не цифры, а их текстовое значение
    return sorted(found_flags, key=lambda flag: flag.value)


def get_reason_enum_by_lds_status(lds_status: int | LdsStatus, failures: Optional[List[str]] = None) -> Type[IntFlag]:
    """
    Получение класса причин по режимам СОУ
    """

    if isinstance(lds_status, int):
        try:
            lds_status = LdsStatus(lds_status)
        except ValueError:
            error_message = f"Неизвестный LdsStatus: {lds_status}"
            if failures is not None:
                failures.append(error_message)
            else:
                fail(error_message)

    reason_by_lds_status = {
        LdsStatus.FAULTY: LdsStatusFaulty,
        LdsStatus.INITIALIZATION: LdsStatusInitialization,
        LdsStatus.DEGRADATION: LdsStatusDegradation,
    }
    enum_class = reason_by_lds_status.get(lds_status)
    if enum_class is None:
        error_message = f"Для LdsStatus{lds_status.name} не определены причины"
        if failures is not None:
            failures.append(error_message)
        else:
            fail(error_message)
    return enum_class


def get_reason_enum_by_stationary_status(
    stationary_status: int | StationaryStatus, failures: Optional[List[str]] = None
) -> Type[IntFlag]:
    """
    Получение класса причин по режимам МТ
    """

    if isinstance(stationary_status, int):
        try:
            stationary_status = StationaryStatus(stationary_status)
        except ValueError:
            error_message = f"Неизвестный StationaryStatus: {stationary_status}"
            if failures is not None:
                failures.append(error_message)
            else:
                fail(error_message)

    reason_by_stationary_status = {
        StationaryStatus.STATIONARY: StationaryReason,
        StationaryStatus.UNSTATIONARY: UnStationaryReason,
        StationaryStatus.STOPPED: StoppedPumpingReason,
    }
    enum_class = reason_by_stationary_status.get(stationary_status)
    if enum_class is None:
        error_message = f"Для StationaryStatus{stationary_status.name} не определены причины"
        if failures is not None:
            failures.append(error_message)
        else:
            fail(error_message)
    return enum_class


def parse_lds_status_reasons(lds_status: int, lds_status_reasons: int, failures: Optional[List[str]] = None):
    """
    Получение списка ldsStatusReasons, соответствующего ldsStatus
    """
    enum_cls = get_reason_enum_by_lds_status(lds_status, failures)
    flags = enum_cls(lds_status_reasons)
    if flags == str(lds_status_reasons):
        error_message = f"Не удалось распаковать флаги: {lds_status_reasons} для {enum_cls.__name__}"
        if failures is not None:
            failures.append(error_message)
    return flags


def parse_stationary_status_reasons(
    stationary_status: int, stationary_status_reasons: int, failures: Optional[List[str]] = None
):
    """
    Получение списка stationaryStatusReasons, соответствующего stationaryStatus
    """
    enum_cls = get_reason_enum_by_stationary_status(stationary_status, failures)
    flags = enum_cls(stationary_status_reasons)
    if flags == str(stationary_status_reasons):
        error_message = f"Не удалось распаковать флаги: {stationary_status_reasons} для {enum_cls.__name__}"
        if failures is not None:
            failures.append(error_message)
    return flags


async def connect(ws_client: WebSocketClient, ws_invoke_type: str, ws_invoke_params: Any = None) -> None:
    """
    Подключение к заданной подписке
    """
    try:
        with allure.step(f"Вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
            await ws_client.invoke(ws_invoke_type, ws_invoke_params)
    except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
        fail(f"Не удалось отправить сообщение типа: {ws_invoke_type} c параметрами {ws_invoke_params}. Ошибка: {error}")


async def connect_stream(
    ws_client: WebSocketClient,
    ws_invoke_type: str,
    ws_invoke_params: Any = None,
    purpose: str = "streaming-вызов WS",
) -> None:
    """
    Streaming-вызов (StreamInvocation)
    """
    try:
        with allure.step(f"Streaming-вызов {ws_invoke_type} c параметрами {ws_invoke_params}"):
            await ws_client.invoke_stream(ws_invoke_type, ws_invoke_params)
    except (asyncio.TimeoutError, ConnectionError, ConnectionResetError, OSError) as error:
        fail(
            f"Не удалось выполнить {purpose} ({ws_invoke_type}, StreamInvocation). "
            f"Параметры запроса: {ws_invoke_params}. Ошибка соединения: {error}"
        )


def _stream_completion_error(msg: Any, invocation_id: str) -> Optional[str]:
    """Текст ошибки из ответа SignalR Completion для данного invocation_id, если есть."""
    if not isinstance(msg, list):
        return None
    if msg[0] != WS_Const.COMPLETION_MESSAGE_TYPE:
        return None
    if not is_desired_invocation_id(msg, invocation_id):
        return None
    if len(msg) <= WS_Const.COMPLETION_ERROR_MESSAGE_INDEX:
        return None
    error_text = msg[WS_Const.COMPLETION_ERROR_MESSAGE_INDEX]
    if isinstance(error_text, str):
        return error_text
    return None


async def receive_download_exported_data_reply(
    ws_client: WebSocketClient,
    parser,
    invocation_id: str,
    request_name: str,
    total_wait_seconds: float,
    poll_interval_seconds: float = 0.5,
    purpose: str = "скачивании xlsx-отчёта после выбора файла в списке сформированных отчётов",
) -> Any:
    """
    Ожидает StreamItem с fileChunk после streaming DownloadExportedDataRequest.
    """
    deadline = asyncio.get_event_loop().time() + total_wait_seconds
    collected_messages: List[Any] = []
    ws_client.suppress_recv_logging = True
    parser.suppress_recv_logging = True
    try:
        while asyncio.get_event_loop().time() < deadline:
            await asyncio.sleep(poll_interval_seconds)
            batch = _drain_recv_queue(ws_client)
            collected_messages.extend(batch)

            for msg in batch:
                stream_error = _stream_completion_error(msg, invocation_id)
                if stream_error:
                    _attach_ws_reply_parse_failure(msg, invocation_id, request_name, RuntimeError(stream_error))
                    fail(
                        f"При {purpose} бэк вернул Completion с ошибкой "
                        f"({request_name}, invocation_id={invocation_id}): {stream_error}"
                    )

            for msg in batch:
                if (
                    not isinstance(msg, list)
                    or msg[0] != WS_Const.STREAM_ITEM_MESSAGE_TYPE
                    or not is_desired_invocation_id(msg, invocation_id)
                ):
                    continue
                if parser.find_reply_status_in_ws_msg(msg) is None:
                    continue
                try:
                    return parser.parse_download_exported_data_msg(msg)
                except Exception as error:
                    _attach_ws_reply_parse_failure(msg, invocation_id, request_name, error)
                    fail(
                        f"При {purpose} получен StreamItem ({request_name}, invocation_id={invocation_id}), "
                        f"но не удалось разобрать ответ с fileChunk: {error}"
                    )
    finally:
        collected_messages.extend(_drain_recv_queue(ws_client))
        ws_client.suppress_recv_logging = False
        parser.suppress_recv_logging = False

    _attach_ws_poll_failure(collected_messages, total_wait_seconds, f"{request_name} (StreamItem)")
    fail(
        f"При {purpose} за {total_wait_seconds} с не получен StreamItem с fileChunk "
        f"({request_name}, invocation_id={invocation_id}). Смотреть вложения received ws message"
    )


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


async def poll_balance_algorithm_diagnostic_areas(
    ws_client: WebSocketClient,
    ws_parser: ws_message_parser,
    imitator_start_time: datetime,
    end_time: datetime,
    poll_interval: float,
) -> list:
    """
    Опрашивает очередь ws_client на наличие BalanceAlgorithmResultsContent,
    собирает и возвращает все diagnosticAreas из flowAreas.
    """
    collected_diagnostic_areas = []
    ws_client.suppress_recv_logging = True
    ws_parser.suppress_recv_logging = True
    try:
        while datetime.now(tz=imitator_start_time.tzinfo) < end_time:
            await asyncio.sleep(poll_interval)

            latest_msg = None
            while not ws_client.recv_queue.empty():
                try:
                    msg = ws_client.recv_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                if isinstance(msg, list) and is_desired_type(msg, "BalanceAlgorithmResultsContent"):
                    latest_msg = msg

            if latest_msg is None:
                continue

            parsed_payload = ws_message_parser.parse_balance_algorithm_msg(latest_msg)
            reply_content = parsed_payload.replyContent
            if reply_content and reply_content.flowAreas:
                for flow_area in reply_content.flowAreas:
                    if flow_area.diagnosticAreas:
                        collected_diagnostic_areas.extend(flow_area.diagnosticAreas)
    finally:
        ws_client.suppress_recv_logging = False
        ws_parser.suppress_recv_logging = False

    return collected_diagnostic_areas


def get_leak_diagnostic_area_samples(
    collected_diagnostic_areas: list,
    leak_diagnostic_area_name: str,
    total_wait: int,
) -> list:
    """
    Проверяет наличие diagnosticAreas и возвращает подмножество
    для ДУ с заданным leak_diagnostic_area_id. Падает, если данные не найдены.
    """
    if not collected_diagnostic_areas:
        fail(f"За {total_wait} секунд не пришло ни одной diagnosticArea в BalanceAlgorithmResultsContent")

    leak_diagnostic_area_samples = [
        diagnostic_area
        for diagnostic_area in collected_diagnostic_areas
        if diagnostic_area.name == leak_diagnostic_area_name
    ]
    if not leak_diagnostic_area_samples:
        fail(f"За {total_wait} секунд не пришло ни одного сообщения для ДУ с name={leak_diagnostic_area_name}.")
    return leak_diagnostic_area_samples
