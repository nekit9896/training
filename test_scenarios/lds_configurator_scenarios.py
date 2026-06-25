"""
Сценарии setup/teardown СОУ через раздел Администрирование (LDS Configurator).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

import allure
from pytest import fail

from clients.websocket_client import WebSocketClient
from constants.enums import SouAdminStatus
from constants.test_constants import LdsConfiguratorConstants as LdsCfgConst
from test_config.models_for_tests import BaseSuiteConfig
from utils.helpers import lds_configurator_utils as lds_utils
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.ws_message_parser import ws_message_parser as parser


def _save_group_state(group_state: Optional[Dict[str, Any]], cfg: BaseSuiteConfig, tu_id: int) -> None:
    """
    Сохраняет resolved tu_id и флаги в group_state для teardown в conftest.
    """
    if group_state is None:
        return
    group_state["use_lds_configurator"] = cfg.use_lds_configurator
    group_state["resolved_tu_id"] = tu_id
    group_state["tu_name"] = cfg.tu_name


async def lds_configurator_setup(
    ws_client: WebSocketClient,
    cfg: BaseSuiteConfig,
    group_state: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Critical-stop сценарий: подготовка стенда и холодный запуск СОУ на конфигурации из Администрирования.

    1. Получить tu_id по tu_name из Администрирования.
    2. Сверить статус с ЭФ Состояние МТ (MainPageInfoContent).
    3. При необходимости остановить уже запущенную СОУ.
    4. Выполнить LaunchLdsRequest и дождаться готовности.
    5. Подтвердить launchedAt после момента запуска.
    """
    tu_id: int
    sou_status: SouAdminStatus
    is_on_main_page: bool

    with allure.step(f"Шаг 1. Получение ТУ '{cfg.tu_name}' из Администрирования"):
        admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)
        admin_tu = lds_utils.find_tu_by_name(admin_reply, cfg.tu_name)
        lds_utils.validate_admin_tu(admin_tu)
        sou_status = SouAdminStatus(admin_tu.status)
        tu_id = admin_tu.tuId
        cfg.resolved_tu_id = tu_id
        _save_group_state(group_state, cfg, tu_id)
        allure.attach(
            f"tuId={tu_id}\n"
            f"tuName={admin_tu.tuName!r}\n"
            f"status={sou_status} ({SouAdminStatus.report_text_by_value(admin_tu.status)})",
            name="Найденный ТУ",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Шаг 2. Сверка статуса СОУ между Администрированием и Состоянием МТ"):
        is_on_main_page = await lds_utils.is_tu_present_on_main_page(ws_client, parser, tu_id)
        lds_utils.check_sou_status_sync(sou_status, is_on_main_page, tu_id, cfg.tu_name)

    launch_checkpoint = t_utils.moscow_now()
    allure.attach(
        t_utils.format_datetime_moscow(launch_checkpoint),
        name="Момент фиксации времени перед холодным запуском",
        attachment_type=allure.attachment_type.TEXT,
    )

    if sou_status == SouAdminStatus.RUNNING and is_on_main_page:
        with allure.step("Шаг 3. Остановка СОУ перед перезапуском (уже была запущена)"):
            await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.STOP_LDS_REQUEST, tu_id)
            with allure.step("Проверка: СОУ выключена в Администрировании"):
                if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.STOPPED):
                    fail(
                        "Не удалось перезапустить СОУ: статус в Администрировании не стал 'выключена' за 2 минуты",
                        pytrace=False,
                    )
            with allure.step("Проверка: ТУ исчезла из Состояния МТ"):
                if not await lds_utils.poll_main_page_tu_presence(ws_client, tu_id, expect_present=False):
                    fail(
                        "Не удалось перезапустить СОУ: ТУ не исчезла из Состояния МТ за 2 минуты",
                        pytrace=False,
                    )

    with allure.step("Шаг 4. Холодный запуск СОУ (LaunchLdsRequest)"):
        await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.LAUNCH_LDS_REQUEST, tu_id)

    with allure.step("Шаг 5. Ожидание включения СОУ в Администрировании"):
        with allure.step("Проверка: статус стал 'включена'"):
            if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.RUNNING):
                fail(
                    "Не удалось запустить СОУ: статус в Администрировании не стал 'включена' за 2 минуты",
                    pytrace=False,
                )

    with allure.step("Шаг 6. Ожидание появления ТУ в Состоянии МТ"):
        with allure.step("Проверка: ТУ отображается в Состоянии МТ"):
            if not await lds_utils.poll_main_page_tu_presence(ws_client, tu_id, expect_present=True):
                fail(
                    "Не удалось запустить СОУ: ТУ не появилась в Состоянии МТ за 2 минуты",
                    pytrace=False,
                )

    with allure.step("Шаг 7. Подтверждение времени запуска (GetTusInformation)"):
        await lds_utils.verify_launched_at(ws_client, parser, tu_id, launch_checkpoint)


async def lds_configurator_teardown(
    ws_client: WebSocketClient,
    tu_id: int,
    tu_name: str,
) -> None:
    """
    Teardown набора: остановка СОУ после прогона.

    Некритичные отклонения оформляются как Allure ALERT без падения прогона.
    Ошибки ws при StopLds логируются и не прерывают pytest session.
    """
    with allure.step(f"Teardown. Проверка статуса СОУ (tuId={tu_id}, «{tu_name}»)"):
        try:
            admin_reply = await lds_utils.get_basic_info_admin(ws_client, parser)
        except Exception as error:
            lds_utils.attach_allure_alert(
                f"Не удалось получить статус СОУ при teardown: {error}. "
                f"tuId={tu_id}, tuName={tu_name!r}"
            )
            return

        sou_status = lds_utils.get_admin_tu_status(admin_reply, tu_id)
        if sou_status != SouAdminStatus.RUNNING:
            lds_utils.attach_allure_alert(
                f"СОУ не в статусе 'включена' при teardown (status={sou_status}), остановка пропущена. "
                f"tuId={tu_id}, tuName='{tu_name}'"
            )
            return

    with allure.step("Teardown. Остановка СОУ (StopLdsRequest)"):
        try:
            await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.STOP_LDS_REQUEST, tu_id)
        except Exception as error:
            lds_utils.attach_allure_alert(
                f"Ошибка при StopLdsRequest: {error}. tuId={tu_id}, tuName={tu_name!r}"
            )
            return

    with allure.step("Teardown. Ожидание выключения СОУ в Администрировании"):
        if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.STOPPED):
            lds_utils.attach_allure_alert(
                f"СОУ не выключилась за 2 минуты после StopLdsRequest. "
                f"tuId={tu_id}, tuName={tu_name!r}. Проверить вручную."
            )
