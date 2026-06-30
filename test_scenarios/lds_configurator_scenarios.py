"""
Сценарии setup/teardown СОУ через раздел Администрирование (LDS Configurator).
"""

from __future__ import annotations

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


async def lds_configurator_admin_setup(
    ws_client: WebSocketClient,
    cfg: BaseSuiteConfig,
    group_state: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Холодный запуск СОУ через Администрирование до старта имитатора.

    1. Получить tu_id по admin_tu_name из GetBasicInfoAdmin.
    2. При необходимости остановить уже запущенную СОУ.
    3. LaunchLdsRequest и ожидание status=включена.
    4. Подтвердить launchedAt в GetTusInformation.
    """
    tu_id: int
    sou_status: SouAdminStatus

    logger.info("[SETUP] Получение ТУ '%s' из Администрирования", cfg.admin_tu_name)
    admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)
    admin_tu = lds_utils.find_tu_by_name(admin_reply, cfg.admin_tu_name)
    lds_utils.validate_admin_tu(admin_tu)
    sou_status = SouAdminStatus(admin_tu.status)
    tu_id = admin_tu.tuId
    cfg.resolved_tu_id = tu_id
    _save_group_state(group_state, cfg, tu_id)
    logger.info(
        "[SETUP] Найден ТУ: tuId=%s, tuName=%r, status=%s (%s)",
        tu_id,
        admin_tu.tuName,
        sou_status,
        SouAdminStatus.report_text_by_value(admin_tu.status),
    )

    if sou_status == SouAdminStatus.RUNNING:
        logger.info("[SETUP] Остановка СОУ перед холодным запуском (уже была включена)")
        await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.STOP_LDS_REQUEST, tu_id)
        if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.STOPPED):
            fail(
                "Не удалось перезапустить СОУ: статус в Администрировании не стал 'выключена' за 2 минуты",
                pytrace=False,
            )

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
    2. Ожидание согласованного состояния ТУ на Состоянии МТ в BasicInfo, до 120 с.
    3. Ожидание согласованного состояния ТУ на Состоянии МТ в MainPageInfoContent, до 120 с.
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
    logger.info(
        "[SETUP] Ожидание %s ТУ в BasicInfo (таймаут %s с)",
        action,
        int(LdsCfgConst.POLL_TIMEOUT_SECONDS),
    )
    basic_info_poll_ok = await lds_utils.poll_basic_info_tu_presence(
        ws_client, parser, tu_id, tu_name, expect_present=expect_enabled
    )
    if not basic_info_poll_ok:
        if expect_enabled:
            fail(
                "СОУ не отображается на Состоянии МТ в BasicInfo: ТУ не появилась за 2 минуты после запуска core",
                pytrace=False,
            )
        fail(
            "СОУ отображается на Состоянии МТ в BasicInfo при статусе 'выключена' в Администрировании",
            pytrace=False,
        )

    logger.info(
        "[SETUP] Ожидание %s ТУ в Состоянии МТ (таймаут %s с)",
        action,
        int(LdsCfgConst.POLL_TIMEOUT_SECONDS),
    )
    main_page_poll_ok = await lds_utils.poll_main_page_tu_presence(
        ws_client, tu_id, expect_present=expect_enabled
    )
    if not main_page_poll_ok:
        if expect_enabled:
            fail(
                "СОУ не отображается в Состоянии МТ: ТУ не появилась за 2 минуты после запуска core",
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
) -> None:
    """
    Teardown набора: остановка СОУ после прогона.
    Некритичные отклонения логируются без падения прогона.
    """
    try:
        logger.info("[TEARDOWN] Проверка статуса СОУ (tuId=%s, «%s»)", tu_id, admin_tu_name)
        ws_client.clear_queue()
        admin_reply = await lds_utils.get_basic_info_admin_with_retry(ws_client, parser)

        sou_status = lds_utils.get_admin_tu_status(admin_reply, tu_id)
        if sou_status != SouAdminStatus.RUNNING:
            lds_utils.attach_allure_alert(
                f"СОУ не в статусе 'включена' при teardown (status={sou_status}), остановка пропущена. "
                f"tuId={tu_id}, adminTuName='{admin_tu_name}'"
            )
            return

        logger.info(f"[TEARDOWN] Остановка СОУ (StopLdsRequest) для tuId={tu_id}")
        await lds_utils.invoke_lds_command(ws_client, parser, LdsCfgConst.STOP_LDS_REQUEST, tu_id)

        logger.info("[TEARDOWN] Ожидание выключения СОУ в Администрировании")
        if not await lds_utils.poll_admin_tu_status(ws_client, parser, tu_id, SouAdminStatus.STOPPED):
            lds_utils.attach_allure_alert(
                f"СОУ не выключилась за 2 минуты после StopLdsRequest. "
                f"tuId={tu_id}, adminTuName={admin_tu_name!r}. Проверить вручную."
            )
    except BaseException as error:
        logger.warning(
            "[TEARDOWN] [ALERT] LDS Configurator teardown: %s. tuId=%s, adminTuName=%r",
            error,
            tu_id,
            admin_tu_name,
        )
        lds_utils.attach_allure_alert(
            f"Ошибка LDS Configurator teardown: {error}. "
            f"tuId={tu_id}, adminTuName={admin_tu_name!r}"
        )
