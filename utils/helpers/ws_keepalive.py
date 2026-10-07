"""
Фоновая подписка-keeper консьюмера api-gateway.

Проблема, которую решает модуль: api-gateway создаёт консьюмера очереди,
только пока есть хотя бы один ws-подписчик. В автотестах клиент подключается
на 10 секунд и отключается, поэтому консьюмер почти всегда выключен, сообщения
копятся в очереди, и к концу прогона накопленный лаг не успевает разгрестись
за окно ретраев.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time

from constants.architecture_constants import WebSocketClientConstants as WS_Const
from utils.helpers.pytest_auth import init_ws_stand_client

logger = logging.getLogger(__name__)


def start_background_subscription(group_state: dict) -> None:
    """
    Запускает фоновую подписку в отдельном daemon-потоке.

    Идемпотентна: повторный вызов при уже запущенном keeper ничего не делает.
    Состояние (поток + stop-сигнал) хранится в group_state["keepalive"].
    """
    if group_state.get("keepalive"):
        return

    stop_event = threading.Event()
    thread = threading.Thread(
        target=_keepalive_thread,
        args=(group_state, stop_event),
        name="ws-keepalive",
        daemon=True,
    )
    group_state["keepalive"] = {"thread": thread, "stop_event": stop_event}
    thread.start()


def stop_background_subscription(group_state: dict) -> None:
    """
    Останавливает фоновую подписку. Идемпотентна.

    Ставит stop-сигнал и ждёт завершения потока ограниченное время. Поскольку
    поток daemon-поток, даже при таймауте join pytest не зависнет.
    """
    keepalive = group_state.get("keepalive")
    if not keepalive:
        return

    stop_event = keepalive.get("stop_event")
    thread = keepalive.get("thread")

    if stop_event is not None:
        stop_event.set()
    if thread is not None and thread.is_alive():
        thread.join(timeout=WS_Const.KEEPALIVE_STOP_JOIN_TIMEOUT_SECONDS)

    group_state["keepalive"] = None
    logger.info("[KEEPER] фоновая подписка остановлена")


def _keepalive_thread(group_state: dict, stop_event: threading.Event) -> None:
    """Запускает асинхронный keeper-цикл в собственном event loop."""
    try:
        asyncio.run(_keepalive_async(group_state, stop_event))
    except Exception:
        logger.exception("[KEEPER] неожиданная ошибка фоновой подписки")


async def _keepalive_async(group_state: dict, stop_event: threading.Event) -> None:
    """
    Цикл фоновой подписки: подключение -> подписка -> слив очереди.

    При обрыве соединения или ошибке создаёт новый WebSocketClient и
    подписывается заново, пока не выставлен stop-сигнал.
    """
    while not stop_event.is_set():
        ws_client = init_ws_stand_client(group_state)
        ws_client.suppress_recv_logging = True
        try:
            async with ws_client as client:
                await client.invoke(WS_Const.KEEPALIVE_SUBSCRIPTION_REQUEST, [])
                logger.info(
                    "[KEEPER] фоновая подписка запущена: %s",
                    WS_Const.KEEPALIVE_SUBSCRIPTION_REQUEST,
                )
                last_clean = time.monotonic()
                while not stop_event.is_set():
                    await asyncio.sleep(WS_Const.KEEPALIVE_POLL_INTERVAL_SECONDS)
                    if stop_event.is_set():
                        break
                    if time.monotonic() - last_clean >= WS_Const.KEEPALIVE_QUEUE_CLEAN_INTERVAL_SECONDS:
                        client.clear_queue()
                        last_clean = time.monotonic()
                    if not client.is_connected:
                        logger.warning("[KEEPER] соединение потеряно, переподключаемся")
                        break
        except asyncio.CancelledError:
            break
        except Exception as error:
            if stop_event.is_set():
                break
            logger.warning(
                "[KEEPER] ошибка соединения/подписки: %s. Повтор через %s с",
                error,
                WS_Const.KEEPALIVE_RECONNECT_INTERVAL_SECONDS,
            )
            await asyncio.sleep(WS_Const.KEEPALIVE_RECONNECT_INTERVAL_SECONDS)
