"""
Вспомогательные функции setup/teardown СОУ через раздел Администрирование.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import Any, Optional

import allure
from pytest import fail

from clients.websocket_client import WebSocketClient
from constants.enums import ReplyStatus, SouAdminStatus
from constants.test_constants import LdsConfiguratorConstants as LdsCfgConst
from models.basic_info_model import BasicInfoReply, BasicTUInfo
from models.get_basic_info_admin_model import AdminTuInfo, GetBasicInfoAdminReply
from models.get_tus_information_model import GetTusInformationReply
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.ws_message_parser import WsMessageParser
from utils.msgpack_utils.message_filters import is_desired_type

logger = logging.getLogger(__name__)

_configurator_flow_active: bool = False


def set_configurator_flow_active(enabled: bool) -> None:
    """Включает логирование вместо Allure-шагов (setup/teardown через lds-configurator в conftest)."""
    global _configurator_flow_active
    _configurator_flow_active = enabled


def is_configurator_flow_active() -> bool:
    """True во время setup/teardown/verify СОУ через Администрирование (lds-configurator) вне теста."""
    return _configurator_flow_active


@contextmanager
def _step(name: str):
    if _configurator_flow_active:
        logger.info("[LDS_CONFIGURATOR] %s", name)
        yield
    else:
        with allure.step(name):
            yield


def attach_allure_alert(message: str) -> None:
    """
    Публикует предупреждение в Allure и лог без падения прогона.

    Используется в teardown при некритичных отклонениях.
    """
    logger.warning("[LDS_CONFIGURATOR] %s", message)
    if not _configurator_flow_active:
        allure.attach(message, name="ALERT", attachment_type=allure.attachment_type.TEXT)


async def get_basic_info(ws_client: WebSocketClient, parser: WsMessageParser) -> BasicInfoReply:
    """
    Выполняет getBasicInfoRequest и парсит ответ BasicInfoContent.
    """
    payload = await t_utils.connect_and_get_msg(ws_client, LdsCfgConst.GET_BASIC_INFO_REQUEST, [])
    return parser.parse_basic_info_msg(payload)


def is_tu_in_basic_info(tus: Optional[list[BasicTUInfo]], tu_id: int, tu_name: str) -> bool:
    """True, если в basicInfo.tus есть запись с указанными tuId и tuName."""
    return any(tu.tuId == tu_id and tu.tuName == tu_name for tu in (tus or []))


async def get_basic_info_admin(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    receive_timeout: Optional[float] = None,
) -> GetBasicInfoAdminReply:
    """
    Выполняет GetBasicInfoAdminRequest и парсит ответ.
    """
    if receive_timeout is None and _configurator_flow_active:
        receive_timeout = LdsCfgConst.CONFIGURATOR_GET_BASIC_INFO_ADMIN_TIMEOUT_SECONDS
    payload = await t_utils.connect_and_get_msg(
        ws_client,
        LdsCfgConst.GET_BASIC_INFO_ADMIN_REQUEST,
        [],
        receive_timeout=receive_timeout,
    )
    return parser.parse_get_basic_info_admin_msg(payload)


async def get_basic_info_admin_with_retry(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    retries: int = LdsCfgConst.GET_BASIC_INFO_ADMIN_RETRIES,
) -> GetBasicInfoAdminReply:
    """
    Запрашивает GetBasicInfoAdminResponse с повторными попытками.
    """
    last_error: Optional[BaseException] = None
    for attempt in range(1, retries + 1):
        with _step(f"Запрос списка ТУ в Администрировании - попытка {attempt} из {retries}"):
            try:
                return await get_basic_info_admin(ws_client, parser)
            except (
                asyncio.TimeoutError,
                ConnectionError,
                ConnectionResetError,
                OSError,
                RuntimeError,
                fail.Exception,
            ) as error:
                last_error = error
                if attempt < retries:
                    await asyncio.sleep(1)

    with _step("Проверка: GetBasicInfoAdminResponse получен"):
        fail(
            f"Не удалось получить GetBasicInfoAdminResponse за {retries} попыток: {last_error}",
            pytrace=False,
        )


def find_tu_by_name(admin_reply: GetBasicInfoAdminReply, tu_name: str) -> AdminTuInfo:
    """
    Ищет ТУ по точному совпадению tuName в ответе Администрирования.
    """
    with _step(f"Поиск ТУ '{tu_name}' по точному совпадению tuName в GetBasicInfoAdminResponse"):
        tus = admin_reply.replyContent.basicInfo.tus if admin_reply.replyContent else None
        with _step("Проверка: в ответе есть список ТУ"):
            if not tus:
                fail(
                    f"GetBasicInfoAdminResponse не содержит списка ТУ (ожидался tuName='{tu_name}')",
                    pytrace=False,
                )
        for tu in tus:
            if tu.tuName == tu_name:
                return tu
        available = [tu.tuName for tu in tus]
        with _step("Проверка: ТУ из набора данных найден в Администрировании"):
            fail(
                f"ТУ '{tu_name}' не найден в GetBasicInfoAdminResponse. Доступные tu_name: {available}",
                pytrace=False,
            )


def validate_admin_tu(tu: AdminTuInfo) -> None:
    """
    Проверяет обязательные поля AdminTuInfo и допустимость статуса СОУ.
    """
    with _step(f"Валидация параметров ТУ '{tu.tuName}' (tuId={tu.tuId})"):
        with _step("Проверка: tuId и mnId заполнены"):
            if not tu.tuId:
                fail(f"Некорректный tuId для ТУ '{tu.tuName}': {tu.tuId}", pytrace=False)
            if not tu.mnId:
                fail(f"Некорректный mnId для ТУ '{tu.tuName}': {tu.mnId}", pytrace=False)
        with _step("Проверка: статус СОУ известен Администрированию"):
            try:
                SouAdminStatus(tu.status)
            except ValueError:
                fail(f"Неизвестный статус СОУ для ТУ '{tu.tuName}': {tu.status}", pytrace=False)


def _tu_id_in_main_page_message(msg: Any, tu_id: int) -> bool:
    """True, если WS-сообщение MainPageInfoContent содержит указанный tuId."""
    if not isinstance(msg, list) or not is_desired_type(msg, LdsCfgConst.MAIN_PAGE_INFO_CONTENT):
        return False
    for item in msg:
        if isinstance(item, dict) and item.get("replyContent", {}).get("tuId") == tu_id:
            return True
        if isinstance(item, list):
            for elem in item:
                if isinstance(elem, dict) and elem.get("replyContent", {}).get("tuId") == tu_id:
                    return True
    return False


def _drain_recv_queue(ws_client: WebSocketClient) -> list[Any]:
    """Забирает все сообщения из очереди WS без блокирующего ожидания."""
    messages: list[Any] = []
    while not ws_client.recv_queue.empty():
        try:
            messages.append(ws_client.recv_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    return messages


async def is_tu_present_on_main_page(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    tu_id: int,
    timeout: float = LdsCfgConst.MAIN_PAGE_SYNC_TIMEOUT_SECONDS,
) -> bool:
    """
    Подписывается на MainPageInfoContent и определяет, отображается ли ТУ в Состоянии МТ.
    """
    with _step(f"Подписка на Состояние МТ (MainPageInfoContent) для tuId={tu_id}"):
        ws_client.clear_queue()
        await t_utils.connect(
            ws_client,
            LdsCfgConst.SUBSCRIBE_MAIN_PAGE_INFO_REQUEST,
            {"tuIds": [tu_id], "additionalProperties": None},
        )

    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        remaining = deadline - asyncio.get_running_loop().time()
        if remaining <= 0:
            break
        try:
            payload = await ws_client.receive_by_type(LdsCfgConst.MAIN_PAGE_INFO_CONTENT, timeout=remaining)
        except asyncio.TimeoutError:
            break
        parsed = parser.parse_main_page_msg(payload)
        if parsed.replyContent and parsed.replyContent.tuId == tu_id:
            return True
    return False


def check_sou_status_sync(
    sou_status: SouAdminStatus,
    is_in_basic_info: bool,
    is_on_main_page: bool,
    tu_id: int,
    tu_name: str,
) -> None:
    """
    Сверяет статус СОУ в Администрировании и на ЭФ Состояние МТ по двум DTO BasicInfo и MainPageInfoContent.
    """
    with _step(
        f"Сверка статуса СОУ: Администрирование vs Состояние МТ "
        f"(tuId={tu_id}, '{tu_name}')"
    ):
        expected_enabled = sou_status == SouAdminStatus.RUNNING
        with _step("Проверка согласованности статусов Администрирования и Состояния МТ"):
            if is_in_basic_info == expected_enabled and is_on_main_page == expected_enabled:
                return
            admin_text = SouAdminStatus.report_text_by_value(sou_status.value)
            basic_text = "СОУ запущена" if is_in_basic_info else "СОУ не запущена"
            page_text = "СОУ запущена" if is_on_main_page else "СОУ не запущена"
            fail(
                f"Рассинхронизация для ТУ '{tu_name}' (tuId={tu_id}): "
                f"Администрирование - {admin_text} ({sou_status.value}); "
                f"Состояние МТ в BasicInfo - {basic_text}; "
                f"Состояние МТ в MainPageInfoContent - {page_text}. "
                f"Статусы в разных подписках не совпадают.",
                pytrace=False,
            )


async def invoke_lds_command(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    request_name: str,
    tu_id: int,
) -> None:
    """
    Отправляет StopLdsRequest или LaunchLdsRequest и ждёт Completion с replyStatus=200.
    """
    with _step(f"Команда {request_name} для tuId={tu_id}"):
        await t_utils.connect(ws_client, request_name, {"tuId": tu_id})
        invocation_id = ws_client.invocation_id
        payload = await ws_client.receive_by_invocation_id(invocation_id)
        if request_name == LdsCfgConst.STOP_LDS_REQUEST:
            reply = parser.parse_stop_lds_msg(payload)
        else:
            reply = parser.parse_launch_lds_msg(payload)
        with _step(f"Проверка: {request_name} завершился успешно (replyStatus=200)"):
            if reply.replyStatus != ReplyStatus.OK:
                fail(
                    f"{request_name} завершился с replyStatus={reply.replyStatus}, "
                    f"ошибки: {reply.replyErrors}",
                    pytrace=False,
                )


async def poll_admin_tu_status(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    tu_id: int,
    expected_status: SouAdminStatus,
    total_wait_seconds: float = LdsCfgConst.POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = LdsCfgConst.POLL_INTERVAL_SECONDS,
) -> bool:
    """
    Long-poll GetBasicInfoAdmin до смены статуса ТУ в Администрировании.
    """
    status_label = SouAdminStatus.report_text_by_value(expected_status.value)
    with _step(
        f"Ожидание статуса '{status_label}' в Администрировании "
        f"(tuId={tu_id}, таймаут {int(total_wait_seconds)} с)"
    ):
        deadline = asyncio.get_running_loop().time() + total_wait_seconds
        while asyncio.get_running_loop().time() < deadline:
            admin_reply = await get_basic_info_admin(ws_client, parser)
            tus = admin_reply.replyContent.basicInfo.tus if admin_reply.replyContent else []
            tu = next((item for item in tus if item.tuId == tu_id), None)
            if tu and tu.status == expected_status.value:
                return True
            await asyncio.sleep(poll_interval_seconds)
        return False


async def poll_basic_info_tu_presence(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    tu_id: int,
    tu_name: str,
    expect_present: bool,
    total_wait_seconds: float = LdsCfgConst.POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = LdsCfgConst.POLL_INTERVAL_SECONDS,
) -> bool:
    """
    Long-poll getBasicInfoRequest: ожидание появления или исчезновения ТУ в basicInfo.tus.
    """
    action = "появления" if expect_present else "исчезновения"
    with _step(
        f"Ожидание {action} ТУ в BasicInfo "
        f"(tuId={tu_id}, tuName='{tu_name}', таймаут {int(total_wait_seconds)} с)"
    ):
        deadline = asyncio.get_running_loop().time() + total_wait_seconds
        while asyncio.get_running_loop().time() < deadline:
            reply = await get_basic_info(ws_client, parser)
            tus = reply.replyContent.basicInfo.tus if reply.replyContent else None
            found = is_tu_in_basic_info(tus, tu_id, tu_name)
            if expect_present and found:
                return True
            if not expect_present and not found:
                return True
            await asyncio.sleep(poll_interval_seconds)

        if _configurator_flow_active:
            logger.warning(
                "[LDS_CONFIGURATOR] Таймаут ожидания %s ТУ tuId=%s в BasicInfo за %s с",
                action,
                tu_id,
                int(total_wait_seconds),
            )
        return False


async def poll_main_page_tu_presence(
    ws_client: WebSocketClient,
    tu_id: int,
    expect_present: bool,
    total_wait_seconds: float = LdsCfgConst.POLL_TIMEOUT_SECONDS,
    poll_interval_seconds: float = LdsCfgConst.POLL_INTERVAL_SECONDS,
) -> bool:
    """
    Long-poll MainPageInfoContent: ожидание появления или исчезновения ТУ в Состоянии МТ.
    """
    action = "появления" if expect_present else "исчезновения"
    with _step(
        f"Ожидание {action} ТУ в Состоянии МТ "
        f"(tuId={tu_id}, таймаут {int(total_wait_seconds)} с)"
    ):
        ws_client.clear_queue()
        await t_utils.connect(
            ws_client,
            LdsCfgConst.SUBSCRIBE_MAIN_PAGE_INFO_REQUEST,
            {"tuIds": [tu_id], "additionalProperties": None},
        )
        deadline = asyncio.get_running_loop().time() + total_wait_seconds
        while asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(poll_interval_seconds)
            batch = _drain_recv_queue(ws_client)
            found = any(_tu_id_in_main_page_message(msg, tu_id) for msg in batch)
            if expect_present and found:
                return True
            if not expect_present and not found:
                return True

        if not _configurator_flow_active:
            t_utils._attach_ws_poll_failure(
                [],
                total_wait_seconds,
                f"{LdsCfgConst.MAIN_PAGE_INFO_CONTENT} tuId={tu_id} present={expect_present}",
            )
        else:
            logger.warning(
                "[LDS_CONFIGURATOR] Таймаут ожидания %s ТУ tuId=%s за %s с",
                action,
                tu_id,
                int(total_wait_seconds),
            )
        return False


async def verify_launched_at(
    ws_client: WebSocketClient,
    parser: WsMessageParser,
    tu_id: int,
    launch_checkpoint: datetime,
) -> None:
    """
    Проверяет, что launchedAt в GetTusInformation не раньше момента LaunchLds с допуском.
    """
    tolerance = timedelta(seconds=LdsCfgConst.LAUNCHED_AT_TOLERANCE_SECONDS)
    with _step(f"Запрос GetTusInformation для tuId={tu_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            LdsCfgConst.GET_TUS_INFORMATION_REQUEST,
            {"tuIds": [tu_id]},
        )
        reply: GetTusInformationReply = parser.parse_get_tus_information_msg(payload)
        tus_info = reply.replyContent.tusInfo if reply.replyContent else []
        tu_info = next((item for item in tus_info if item.tuId == tu_id), None)

        with _step("Проверка: в ответе есть информация о запуске ТУ"):
            if tu_info is None:
                fail(f"GetTusInformationResponse не содержит tuId={tu_id}", pytrace=False)

        launched_at = parser.timestamp_to_datetime(tu_info.launchedAt)
        with _step("Проверка: поле launchedAt заполнено"):
            if launched_at is None:
                fail(f"GetTusInformationResponse: launchedAt отсутствует для tuId={tu_id}", pytrace=False)

        launched_at_msk = t_utils.localize_as_moscow(launched_at)
        checkpoint_msk = t_utils.localize_as_moscow(launch_checkpoint)
        compare_msg = (
            f"launchedAt: {t_utils.format_datetime_moscow(launched_at_msk)}\n"
            f"checkpoint: {t_utils.format_datetime_moscow(checkpoint_msk)}\n"
            f"tolerance: {LdsCfgConst.LAUNCHED_AT_TOLERANCE_SECONDS} с"
        )
        if _configurator_flow_active:
            logger.info("[LDS_CONFIGURATOR] Сравнение времени запуска СОУ:\n%s", compare_msg)
        else:
            allure.attach(
                compare_msg,
                name="Сравнение времени запуска СОУ",
                attachment_type=allure.attachment_type.TEXT,
            )

        with _step("Проверка: launchedAt не раньше момента команды 'Запустить СОУ' (с допуском)"):
            if launched_at_msk < checkpoint_msk - tolerance:
                fail(
                    f"Время запуска СОУ на бэкенде ({t_utils.format_datetime_moscow(launched_at_msk)}) "
                    f"раньше момента команды 'Запустить СОУ' "
                    f"({t_utils.format_datetime_moscow(checkpoint_msk)}) "
                    f"с учётом допуска {int(LdsCfgConst.LAUNCHED_AT_TOLERANCE_SECONDS)} с",
                    pytrace=False,
                )


def get_admin_tu_status(admin_reply: GetBasicInfoAdminReply, tu_id: int) -> Optional[SouAdminStatus]:
    """
    Возвращает статус СОУ из GetBasicInfoAdmin для указанного tuId.
    """
    tus = admin_reply.replyContent.basicInfo.tus if admin_reply.replyContent else []
    tu = next((item for item in tus if item.tuId == tu_id), None)
    if tu is None:
        return None
    try:
        return SouAdminStatus(tu.status)
    except ValueError:
        return None
