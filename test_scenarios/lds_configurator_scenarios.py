"""
Сценарии setup/teardown СОУ через раздел Администрирование (LDS Configurator).
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from pytest import fail

from clients.http_client import StandHttpClient
from clients.websocket_client import WebSocketClient
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.enums import SouAdminStatus
from constants.test_constants import LdsConfiguratorConstants as LdsCfgConst
from test_config.models_for_tests import BaseSuiteConfig
from utils.helpers import lds_configurator_utils as lds_utils
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
    http_client: StandHttpClient,
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
    target_tu_id: int

    logger.info("[SETUP] Получение ТУ '%s' из Администрирования", cfg.admin_tu_name)
    admin_reply = lds_utils.get_basic_info_admin_with_retry(http_client, parser)
    target_tu = lds_utils.find_tu_by_name(admin_reply, cfg.admin_tu_name)
    running_tus = lds_utils.extract_running_tus(admin_reply)
    lds_utils.validate_admin_tu(target_tu)
    target_tu_id = target_tu.tuId
    target_tu_name = target_tu.tuName
    target_tu_status = target_tu.status
    cfg.resolved_tu_id = target_tu_id
    _save_group_state(group_state, cfg, target_tu_id)
    logger.info(
        "[SETUP] Найден целевой ТУ: tuId=%s, tuName=%r, status=%s (%s)",
        target_tu_id,
        target_tu_name,
        SouAdminStatus(target_tu.status),
        SouAdminStatus.report_text_by_value(target_tu.status),
    )
    pre_run_snapshot = lds_utils.running_tus_to_snapshot(running_tus)
    _save_pre_run_running_tus(group_state, pre_run_snapshot)

    if target_tu_status == SouAdminStatus.RUNNING.value:
        if len(running_tus) == 1:
            logger.info(
                "[SETUP] Запущен ранее только целевой ТУ: tuId=%s, tuName=%r, status=%s (%s)",
                target_tu_id,
                target_tu_name,
                SouAdminStatus(target_tu_status),
                SouAdminStatus.report_text_by_value(target_tu_status),
            )
        else:
            logger.info(
                "[SETUP] Список включённых ТУ на стенде: %s шт. %s",
                len(pre_run_snapshot),
                pre_run_snapshot,
            )
            # Получает список запущенных ТУ, кроме целевого
            extra_running_tus = [item for item in running_tus if item.tuId != target_tu_id]
            await lds_utils.stop_running_tus(http_client, parser, extra_running_tus)
            if not await lds_utils.poll_admin_tu_status(http_client, parser, target_tu_id, SouAdminStatus.RUNNING):
                fail(
                    f"Не удалось оставить только целевой ТУ tuId={target_tu_id} в статусе {SouAdminStatus.RUNNING} ",
                    pytrace=False,
                )
    else:
        logger.info(
            "[SETUP] Список включённых ТУ на стенде: %s шт. %s",
            len(pre_run_snapshot),
            pre_run_snapshot,
        )
        await lds_utils.stop_running_tus(http_client, parser, running_tus)

        logger.info("[SETUP] Холодный запуск СОУ (LaunchLdsRequest) для tuId=%s", target_tu_id)
        lds_utils.run_lds_command(http_client, HttpConst.LAUNCH_LDS_URL_PATH, target_tu_id)

        logger.info("[SETUP] Ожидание включения СОУ в Администрировании")
        if not await lds_utils.poll_admin_tu_status(http_client, parser, target_tu_id, SouAdminStatus.RUNNING):
            fail(
                "Не удалось запустить целевой ТУ: статус в Администрировании не стал 'включена' за 2 минуты",
                pytrace=False,
            )

    logger.info("[SETUP] Подтверждение наличия времени запуска (GetTusInformation)")
    lds_utils.verify_get_tus_info(http_client, parser, target_tu_id)
    logger.info("[LDS_CONFIGURATOR] [SETUP] [OK] Запуск СОУ через Администрирование до старта имитатора. Успех!")


async def lds_configurator_verify_after_core(
    ws_client: WebSocketClient,
    http_client: StandHttpClient,
    cfg: BaseSuiteConfig,
) -> None:
    """
    Проверка готовности стенда после запуска lds-core.

    1. Актуальный статус СОУ из Администрирования.
    2. Ожидание согласованного состояния ТУ на Состоянии МТ в BasicInfo из общего запаса времени.
    3. Ожидание согласованного состояния ТУ на Состоянии МТ в MainPageInfoContent - остаток от общего запаса времени.
    4. Сверка статуса СОУ: Администрирование vs Состояние МТ.
    """
    tu_id = cfg.tu_id
    tu_name = cfg.tu_name

    logger.info("[SETUP] Получение актуального статуса СОУ для tuId=%s", tu_id)
    admin_reply = lds_utils.get_basic_info_admin_with_retry(http_client, parser)
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
        "[SETUP] %s, запас времени %s с, ожидание %s ТУ в BasicInfo (до %s с)",
        admin_label,
        ui_sync_time_seconds,
        action,
        int(basic_timeout),
    )
    basic_info_poll_ok = await lds_utils.poll_basic_info_tu_presence(
        http_client, parser, tu_id, tu_name, expect_present=expect_enabled, total_wait_seconds=basic_timeout
    )
    if not basic_info_poll_ok:
        if expect_enabled:
            fail(
                f"СОУ не отображается на Состоянии МТ в BasicInfo: ТУ не появилась за {ui_sync_time_seconds} c "
                f"после запуска core",
                pytrace=False,
            )
        fail(
            "СОУ отображается на Состоянии МТ в BasicInfo при статусе 'выключена' в Администрировании",
            pytrace=False,
        )

    main_timeout = ui_sync_deadline - loop.time()
    if main_timeout <= 0:
        fail(
            f"Весь запас времени {ui_sync_time_seconds} для синхронизации подписок израсходован на ожидание BasicInfo"
            "на MainPage времени не осталось"
        )

    logger.info(
        "[SETUP] Ожидание %s ТУ в Состоянии МТ (остаток запаса времени %s с)",
        action,
        int(main_timeout),
    )
    main_page_poll_ok = await lds_utils.poll_main_page_tu_presence(
        ws_client, tu_id, expect_present=expect_enabled, total_wait_seconds=main_timeout
    )
    if not main_page_poll_ok:
        if expect_enabled:
            fail(
                "СОУ не отображается в Состоянии МТ: ТУ не появилась за оставшееся время запаса для синхронизации"
                f"({ui_sync_time_seconds} c после запуска core)",
                pytrace=False,
            )
        fail(
            "СОУ отображается в Состоянии МТ при статусе 'выключена' в Администрировании",
            pytrace=False,
        )

    logger.info("[SETUP] Сверка статуса СОУ: Администрирование vs Состояние МТ")
    lds_utils.check_sou_status_sync(sou_status, expect_enabled, expect_enabled, tu_id, tu_name)
    logger.info("[LDS_CONFIGURATOR] [SETUP] [OK] Проверка готовности стенда после запуска lds-core. Успех!")


async def lds_configurator_teardown(
    http_client: StandHttpClient,
    tu_id: int,
    admin_tu_name: str,
    pre_run_running_tus: Optional[list[Dict[str, Any]]] = None,
) -> None:
    """
    Teardown набора: остановка СОУ автотестов и восстановление ТУ стенда из снимка.
    Некритичные отклонения логируются без падения прогона.
    """
    snapshot = pre_run_running_tus or []
    running_tu = {"tuId": tu_id, "tuName": admin_tu_name}
    try:
        logger.info("[TEARDOWN] Проверка статуса СОУ (tuId=%s, «%s»)", tu_id, admin_tu_name)
        admin_reply = lds_utils.get_basic_info_admin_with_retry(http_client, parser)

        sou_status = lds_utils.get_admin_tu_status(admin_reply, tu_id)
        if sou_status == SouAdminStatus.RUNNING and not (len(snapshot) == 1 and snapshot[0] == running_tu):
            logger.info("[TEARDOWN] Остановка СОУ (StopLdsRequest) для tuId=%s", tu_id)
            lds_utils.run_lds_command(http_client, HttpConst.STOP_LDS_URL_PATH, tu_id)

            logger.info("[TEARDOWN] Ожидание выключения СОУ в Администрировании")
            if not await lds_utils.poll_admin_tu_status(http_client, parser, tu_id, SouAdminStatus.STOPPED):
                lds_utils.attach_allure_alert(
                    f"СОУ не выключилась за 2 минуты после StopLdsRequest. "
                    f"tuId={tu_id}, adminTuName={admin_tu_name!r}. Проверить вручную."
                )
        else:
            lds_utils.attach_allure_alert(
                f"[SKIP] tuId={tu_id}, adminTuName='{admin_tu_name} не в статусе 'включена' "
                "или была включена до старта прогона. Остановка пропущена."
            )
        if snapshot:
            await lds_utils.restore_pre_run_tus(http_client, parser, snapshot, tu_id)
        logger.info("[LDS_CONFIGURATOR] [TEARDOWN] [OK] Восстановление ТУ. Успех!")
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
        