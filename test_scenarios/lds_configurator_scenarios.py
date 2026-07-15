"""
Сценарии setup/teardown СОУ через раздел Администрирование (LDS Configurator).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from pytest import fail

from clients.websocket_client import WebSocketClient
from constants.enums import SouAdminStatus
from constants.test_constants import LdsConfiguratorConstants as LdsCfgConst
from test_config.models_for_tests import BaseSuiteConfig
from utils.helpers import lds_configurator_utils as lds_utils
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.ws_message_parser import ws_message_parser as parser

logger = logging.getLogger(__name__)


def _save_group_state(group_state: Optional[Dict[str, Any]], cfg: BaseSuiteConfig, tu_id: int) -> None:
    """
    Сохраняет resolved tu_id и флаги в group_state для teardown в conftest.
    """
    if group_state is None:
        return
    group_state["use_lds_configurator"] = cfg.use_lds_configurator
    group_state["resolved_tu_id"] = tu_id
    group_state["admin_tu_name"] = cfg.admin_tu_name


def _save_pre_run_running_tus(
    group_state: Optional[Dict[str, Any]],
    snapshot: list[Dict[str, Any]],
) -> None:
    """Сохраняет список включённых ТУ стенда до запуска автотестов."""
    if group_state is None:
        return
    group_state["pre_run_running_tus"] = snapshot


async def lds_configurator_admin_setup(
    ws_client: WebSocketClient,
    cfg: BaseSuiteConfig,
    group_state: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Холодный запуск СОУ через Администрирование до старта имитатора.

    1. Получить tu_id по admin_tu_name из GetBasicInfoAdmin.
    2. Снять слепок всех RUNNING ТУ и остановить их на стенде.
    3. LaunchLdsRequest и ожидание status=включена.
    4. Подтвердить launchedAt в GetTusInformation.
    """
    tu_id: int

    logger.info("[SETUP] Получение ТУ '%s' из Администрирования", cfg.admin_tu_name)
    admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)
    admin_tu = lds_utils.find_tu_by_name(admin_reply, cfg.admin_tu_name)
    lds_utils.validate_admin_tu(admin_tu)
    tu_id = admin_tu.tuId
    cfg.resolved_tu_id = tu_id
    _save_group_state(group_state, cfg, tu_id)
    logger.info(
        "[SETUP] Найден ТУ: tuId=%s, tuName=%r, status=%s (%s)",
        tu_id,
        admin_tu.tuName,
        SouAdminStatus(admin_tu.status),
        SouAdminStatus.report_text_by_value(admin_tu.status),
    )

    running_tus = lds_utils.extract_running_tus(admin_reply)
    pre_run_snapshot = lds_utils.running_tus_to_snapshot(running_tus)
    _save_pre_run_running_tus(group_state, pre_run_snapshot)
    logger.info(
        "[SETUP] Спсиок включённых ТУ на стенде: %s шт. %s",
        len(pre_run_snapshot),
        pre_run_snapshot,
    )
    await lds_utils.stop_all_running_tus(ws_client, parser, running_tus)

    launch_checkpoint = t_utils.moscow_now()
    logger.info(
        "[SETUP] Момент фиксации времени перед LaunchLds: %s",
        t_utils.format_datetime_moscow(launch_checkpoint),
    )

    logger.info("[SETUP] Холодный запуск СОУ (LaunchLdsRequest) для tuId=%s", tu_id)
    await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.LAUNCH_LDS_REQUEST, tu_id)

    logger.info("[SETUP] Ожидание включения СОУ в Администрировании")
    if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.RUNNING):
        fail(
            "Не удалось запустить СОУ: статус в Администрировании не стал 'включена' за 2 минуты",
            pytrace=False,
        )

    logger.info("[SETUP] Подтверждение времени запуска (GetTusInformation)")
    await lds_utils.verify_launched_at(ws_client, parser, tu_id, launch_checkpoint)


async def lds_configurator_verify_after_core(
    ws_client: WebSocketClient,
    cfg: BaseSuiteConfig,
) -> None:
    """
    Проверка готовности стенда после запуска lds-core.

    1. Актуальный статус СОУ из Администрирования.
    2. Ожидание согласованного состояния ТУ в BasicInfo (из общего запаса времени).
       При RUNNING - VERIFY_UI_SYNC_TIME_SECONDS (300 с).
    3. Ожидание согласованного состояния ТУ в MainPageInfoContent (остаток запаса времени).
    4. Сверка статуса СОУ: Администрирование vs Состояние МТ.
    """
    tu_id = cfg.tu_id
    tu_name = cfg.tu_name

    logger.info("[SETUP] Получение актуального статуса СОУ для tuId=%s", tu_id)
    admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)
    sou_status = lds_utils.get_admin_tu_status(admin_reply, tu_id)
    if sou_status is None:
        fail(
            f"ТУ tuId={tu_id} ('{tu_name}') не найден в GetBasicInfoAdminResponse",
            pytrace=False,
        )

    expect_enabled = sou_status == SouAdminStatus.RUNNING
    action = "появления" if expect_enabled else "отсутствия"
    loop = asyncio.get_running_loop()

    if expect_enabled:
        ui_sync_time_total = LdsCfgConst.VERIFY_UI_SYNC_TIME_SECONDS
        admin_label = "Admin=RUNNING"
    else:
        ui_sync_time_total = LdsCfgConst.POLL_TIMEOUT_SECONDS
        admin_label = "Admin=STOPPED"

    ui_sync_time_seconds = int(ui_sync_time_total)
    ui_sync_deadline = loop.time() + ui_sync_time_total
    basic_timeout = ui_sync_deadline - loop.time()
    logger.info(
        "[SETUP] %s, запас времени UI-sync %s с; ожидание %s ТУ в BasicInfo (до %s с)",
        admin_label,
        ui_sync_time_seconds,
        action,
        int(basic_timeout),
    )

    basic_info_poll_ok = await lds_utils.poll_basic_info_tu_presence(
        ws_client,
        parser,
        tu_id,
        tu_name,
        expect_present=expect_enabled,
        total_wait_seconds=basic_timeout,
    )
    if not basic_info_poll_ok:
        if expect_enabled:
            fail(
                f"СОУ не отображается на Состоянии МТ в BasicInfo: ТУ не появилась за {ui_sync_time_seconds} с "
                "(запас времени UI-sync после запуска core)",
                pytrace=False,
            )
        fail(
            "СОУ отображается на Состоянии МТ в BasicInfo при статусе 'выключена' в Администрировании",
            pytrace=False,
        )

    main_timeout = ui_sync_deadline - loop.time()
    if main_timeout <= 0:
        fail(
            f"Весь запас времени UI-sync {ui_sync_time_seconds} с израсходован на ожидание BasicInfo, "
            "на MainPage времени не осталось",
            pytrace=False,
        )
    logger.info(
        "[SETUP] Ожидание %s ТУ в Состоянии МТ (остаток запаса времени %s с)",
        action,
        int(main_timeout),
    )

    main_page_poll_ok = await lds_utils.poll_main_page_tu_presence(
        ws_client,
        tu_id,
        expect_present=expect_enabled,
        total_wait_seconds=main_timeout,
    )
    if not main_page_poll_ok:
        if expect_enabled:
            fail(
                f"СОУ не отображается в Состоянии МТ: ТУ не появилась в оставшееся время "
                f"запаса UI-sync ({ui_sync_time_seconds} с после запуска core)",
                pytrace=False,
            )
        fail(
            "СОУ отображается в Состоянии МТ при статусе 'выключена' в Администрировании",
            pytrace=False,
        )

    logger.info("[SETUP] Сверка статуса СОУ: Администрирование vs BasicInfo vs Состояние МТ")
    lds_utils.check_sou_status_sync(sou_status, expect_enabled, expect_enabled, tu_id, tu_name)


async def lds_configurator_teardown(
    ws_client: WebSocketClient,
    tu_id: int,
    admin_tu_name: str,
    pre_run_running_tus: Optional[list[Dict[str, Any]]] = None,
) -> None:
    """
    Teardown набора: остановка СОУ автотестов и восстановление ТУ стенда из снимка.
    Некритичные отклонения логируются без падения прогона.
    """
    snapshot = pre_run_running_tus or []
    try:
        logger.info("[TEARDOWN] Проверка статуса СОУ (tuId=%s, «%s»)", tu_id, admin_tu_name)
        ws_client.clear_queue()
        admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)

        sou_status = lds_utils.get_admin_tu_status(admin_reply, tu_id)
        if sou_status == SouAdminStatus.RUNNING:
            logger.info("[TEARDOWN] Остановка СОУ (StopLdsRequest) для tuId=%s", tu_id)
            await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.STOP_LDS_REQUEST, tu_id)

            logger.info("[TEARDOWN] Ожидание выключения СОУ в Администрировании")
            if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.STOPPED):
                lds_utils.attach_allure_alert(
                    f"СОУ не выключилась за 2 минуты после StopLdsRequest. "
                    f"tuId={tu_id}, adminTuName={admin_tu_name!r}. Проверить вручную."
                )
        else:
            lds_utils.attach_allure_alert(
                f"СОУ не в статусе 'включена' при teardown (status={sou_status}), остановка пропущена. "
                f"tuId={tu_id}, adminTuName='{admin_tu_name}'"
            )

        await lds_utils.restore_pre_run_tus(ws_client, parser, snapshot, exclude_tu_id=tu_id)
    except BaseException as error:
        logger.warning(
            "[TEARDOWN] [ALERT] LDS Configurator teardown: %s: %r. tuId=%s, adminTuName=%r",
            type(error).__name__,
            error,
            tu_id,
            admin_tu_name,
        )
        lds_utils.attach_allure_alert(
            f"Ошибка LDS Configurator teardown: {type(error).__name__}: {error!r}. "
            f"tuId={tu_id}, adminTuName={admin_tu_name!r}"
        )
