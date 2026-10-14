"""
Авторизация pytest-прогона: Keycloak access token и x-user-id для HTTP/WS.

Кэш кредов на уровне dataset (group_state)
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

import pytest
import requests

from clients.http_client import StandHttpClient
from clients.keycloak_clients import KeycloakAuthError, KeycloakClient
from clients.testops_client import logger
from clients.websocket_client import WebSocketClient
from clients.ws_connection_manager import WsConnectionManager
from constants.architecture_constants import EnvKeyConstants as EnvConst
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.architecture_constants import PersistentConnectionConstants as PersistConst
from constants.architecture_constants import WebSocketClientConstants as WSCliConst

# Один KeycloakClient на pytest-сессию; TTL токена проверяется внутри клиента.
_keycloak_client: KeycloakClient | None = None

# Ключ постоянного ws-соединения в group_state (жизненный цикл - набор данных).
WS_MANAGER_STATE_KEY: str = "ws_manager"


def get_instance() -> str:
    """Имя стенда из переменной окружения STAND_NAME."""
    instance = os.environ.get(EnvConst.STAND_NAME)
    if not instance:
        pytest.exit(f"Переменная окружения {EnvConst.STAND_NAME} не задана в .env")
    return instance


def build_stand_host() -> str:
    """Хост api-gateway для HTTP и WSS запросов к стенду."""
    instance = get_instance()
    return (
        f"{WSCliConst.SERVICE_NAME}.{WSCliConst.COMPONENT}-{instance}.{WSCliConst.ROOT_DOMAIN}/"
        f"{WSCliConst.API_GATEWAY_PATH_SEGMENT}"
    )


def _get_keycloak_client() -> KeycloakClient:
    """
    Возвращает единственный KeycloakClient на время pytest-сессии.

    Вызовы get_access_token() внутри одного клиента ждут истечения токена KeycloakClient._is_token_expired.
    """
    global _keycloak_client
    if _keycloak_client is None:
        _keycloak_client = KeycloakClient(
            url=os.environ.get(EnvConst.KEYCLOAK_SZI_URL),
            client_id=os.environ.get(EnvConst.KEYCLOAK_CLIENT_ID),
            client_secret=os.environ.get(EnvConst.KEYCLOAK_SZI_CLIENT_SECRET),
            username=os.environ.get(EnvConst.KEYCLOAK_USERNAME),
            password=os.environ.get(EnvConst.KEYCLOAK_PASSWORD),
        )
    return _keycloak_client


def _invalidate_keycloak_token() -> None:
    """
    Сбрасывает закэшированный access token в KeycloakClient.

    Вызывается при force_refresh=True (смена dataset), чтобы запросить новый JWT,
    даже если предыдущий ещё в пределах TTL.
    """
    client = _get_keycloak_client()
    client._token = None
    client._token_data = None


def get_token(max_retries: int = 12, backoff: float = 5.0, force_refresh: bool = False) -> str:
    """
    Получает JWT access token из Keycloak с повторными попытками.

    max_retries: сколько всего попыток
    backoff: время в секундах между попытками
    force_refresh: принудительно запросить новый token в Keycloak
    """
    if force_refresh:
        _invalidate_keycloak_token()

    last_exc = None
    keycloak = _get_keycloak_client()
    for attempt in range(1, max_retries + 1):
        try:
            token = keycloak.get_access_token()
            if not token:
                raise KeycloakAuthError("Получен пустой access token")
            return token

        except KeycloakAuthError as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] KeycloakAuthError: {e}. Повтор через {backoff} сек.")
        except Exception as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] Неожиданная ошибка: {e}. Повтор через {backoff} сек.")

        if attempt < max_retries:
            time.sleep(backoff)

    # все попытки исчерпаны
    logger.error(f"[KEYCLOAK] [ERROR] Не удалось получить токен после {max_retries} попыток: {last_exc}")
    pytest.fail(f"[KEYCLOAK][ERROR] Не удалось получить токен после {max_retries} попыток: {last_exc}")


def clear_suite_auth(group_state: dict) -> None:
    """
    Сбрасывает кэш auth в group_state перед инициализацией нового dataset.
    Очищает stand_host, auth_token, x_user_id и метку auth_suite.
    """
    group_state["stand_host"] = None
    group_state["auth_token"] = None
    group_state["x_user_id"] = None
    group_state["auth_suite"] = None


def _fetch_x_user_id(http_client: StandHttpClient, max_retries: int = 12, backoff: float = 5.0) -> str:
    """
    Запрашивает x-user-id через POST /apigateway/Ping с повторными попытками.
    Значение нужно для параметра xUserId= в URL WebSocket-подключения.
    Вызывается после старта api-gateway.
    """
    http_client.suppress_recv_logging = True
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            response = http_client.post_request(HttpConst.PING_URL_PATH, {})
            x_user_id = response.headers.get(HttpConst.X_USER_ID_KEY)
            if not x_user_id:
                raise ValueError("/Ping не вернул x-user-id")
            logger.info("[AUTH] [OK] Получен x-user-id")
            return x_user_id

        except (requests.RequestException, ValueError) as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] /Ping: {e}. Повтор через {backoff} сек.")
        except Exception as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] Неожиданная ошибка /Ping: {e}. Повтор через {backoff} сек.")

        if attempt < max_retries:
            time.sleep(backoff)

    # все попытки исчерпаны
    logger.error(f"[AUTH] [ERROR] Не удалось получить x-user-id после {max_retries} попыток: {last_exc}")
    pytest.fail(f"[AUTH][ERROR] Не удалось получить x-user-id после {max_retries} попыток: {last_exc}")


def ensure_suite_auth(group_state: dict, suite_name: str) -> None:
    """
    Получает и кэширует credentials набора: stand_host, auth_token, x-user-id.

    Порядок: Keycloak token -> Ping к api-gateway (x-user-id). Оба запрашиваются
    после setup_stand_for_imitator_run(), когда gateway уже доступен.
    Повторный вызов для того же suite_name с валидным кэшем ничего не делает.
    """
    if (
        group_state.get("auth_suite") == suite_name
        and group_state.get("auth_token")
        and group_state.get("x_user_id")
        and group_state.get("stand_host")
    ):
        return

    stand_host = build_stand_host()
    auth_token = get_token(force_refresh=True)
    http_client = StandHttpClient(stand_host, auth_token)
    x_user_id = _fetch_x_user_id(http_client)

    group_state["stand_host"] = stand_host
    group_state["auth_token"] = auth_token
    group_state["x_user_id"] = x_user_id
    group_state["auth_suite"] = suite_name

    logger.info("[AUTH] Инициализация auth для dataset '%s'", suite_name)


def ensure_auth_for_fixture(group_state: dict) -> None:
    """
    Подстраховка для фикстур http_client / ws_client.

    Основная инициализация auth выполняется в pytest_runtest_setup при смене dataset.
    Если тест по какой-то причине стартует раньше (нет current_suite), здесь
    выполняется инициализация по auth_suite или fallback '__default__'.
    """
    suite_name = group_state.get("current_suite") or group_state.get("auth_suite") or "__default__"
    ensure_suite_auth(group_state, suite_name)


def _require_auth(group_state: dict, *, require_x_user_id: bool = False) -> None:
    """
    Проверяет, что auth уже инициализирован в group_state.
    При отсутствии stand_host/auth_token (и x_user_id для WS) завершает прогон через pytest.exit.
    """
    if not group_state.get("auth_token") or not group_state.get("stand_host"):
        pytest.exit("[AUTH] auth не инициализирован - ожидается ensure_suite_auth()")
    if require_x_user_id and not group_state.get("x_user_id"):
        pytest.exit("[AUTH] x_user_id не инициализирован - ожидается ensure_suite_auth()")


def init_http_stand_client(group_state: dict) -> StandHttpClient:
    """Создает StandHttpClient. Креды из group_state (кэш на dataset)."""
    _require_auth(group_state)
    return StandHttpClient(group_state["stand_host"], group_state["auth_token"])


def init_ws_stand_client(group_state: dict) -> WebSocketClient:
    """Создает WebSocketClient. Креды из group_state (кэш на dataset)."""
    _require_auth(group_state, require_x_user_id=True)
    return WebSocketClient(
        group_state["stand_host"],
        group_state["auth_token"],
        group_state["x_user_id"],
    )


def build_subscription_bundle(tu_id: int) -> list[tuple[str, Any]]:
    """
    Bundle подписок постоянного соединения - повторяет набор фронта после авторизации.

    Эти подписки вместе с negotiate дают api-gateway понять, что есть подписанный клиент,
    и держать консьюмеры для чтения core и layer builder на всё время набора данных.
    """
    main_page_args = {
        PersistConst.TU_IDS_KEY: [tu_id],
        PersistConst.ADDITIONAL_PROPERTIES_KEY: None,
    }
    return [
        (PersistConst.SUBSCRIBE_PLAYER_STATUS_INFO_REQUEST, PersistConst.EMPTY_SUBSCRIBE_ARGS),
        (PersistConst.SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST, PersistConst.EMPTY_SUBSCRIBE_ARGS),
        (PersistConst.SUBSCRIBE_SELF_DIAGNOSTIC_INFO_REQUEST, PersistConst.EMPTY_SUBSCRIBE_ARGS),
        (PersistConst.SUBSCRIBE_MAIN_PAGE_INFO_REQUEST, dict(main_page_args)),
        (PersistConst.SUBSCRIBE_MAIN_PAGE_SIGNALS_INFO_REQUEST, dict(main_page_args)),
    ]


def start_ws_connection_manager(group_state: dict, tu_id: int) -> WsConnectionManager:
    """
    Создаёт и запускает постоянное соединение набора данных (один раз на dataset).

    Ошибка запуска не пробрасывается в pytest: прогон должен продолжаться, а соединение
    поднимет supervisor внутри менеджера с экспоненциальным backoff.
    """
    _require_auth(group_state, require_x_user_id=True)
    existing = group_state.get(WS_MANAGER_STATE_KEY)
    if existing is not None:
        return existing

    manager = WsConnectionManager(
        host=group_state["stand_host"],
        access_token=group_state["auth_token"],
        x_user_id=group_state["x_user_id"],
        bundle=build_subscription_bundle(tu_id),
    )
    group_state[WS_MANAGER_STATE_KEY] = manager
    try:
        manager.start()
        logger.info("[WS_MANAGER] Постоянное соединение набора запущено (tuId=%s)", tu_id)
    except BaseException as error:
        logger.warning("[WS_MANAGER] [ALERT] Не удалось запустить постоянное соединение: %s", error)
    return manager


def get_ws_connection_manager(group_state: dict) -> Optional[WsConnectionManager]:
    """Возвращает запущенное постоянное соединение набора либо None."""
    return group_state.get(WS_MANAGER_STATE_KEY)


def close_ws_connection_manager(group_state: dict) -> None:
    """Останавливает постоянное соединение набора. Идемпотентно: повторный вызов безопасен."""
    manager = group_state.pop(WS_MANAGER_STATE_KEY, None)
    if manager is None:
        return
    try:
        manager.stop()
        logger.info("[WS_MANAGER] Постоянное соединение набора остановлено")
    except BaseException as error:
        logger.warning("[WS_MANAGER] [ALERT] Ошибка при остановке постоянного соединения: %s", error)
