"""
Авторизация pytest-прогона: Keycloak access token и x-user-id для HTTP/WS.

Кэш кредов на уровне dataset (group_state)
"""

from __future__ import annotations

import os
import time

import pytest
import requests

from clients.http_client import StandHttpClient
from clients.keycloak_clients import KeycloakAuthError, KeycloakClient
from clients.testops_client import logger
from clients.websocket_client import WebSocketClient
from constants.architecture_constants import EnvKeyConstants as EnvConst
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.architecture_constants import WebSocketClientConstants as WSCliConst

# Один KeycloakClient на pytest-сессию; TTL токена проверяется внутри клиента.
_keycloak_client: KeycloakClient | None = None


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

    max_retries: сколько всего попыток (включая первую)
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


def _fetch_x_user_id(http_client: StandHttpClient, max_retries: int = 5, backoff: float = 5.0) -> str:
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


def ensure_suite_token(group_state: dict, suite_name: str) -> None:
    """
    Один раз на dataset: stand_host + access token (Keycloak).
    Выполняется до выключения и последующего поднятия Docker-контейнеров.
    """
    if (
        group_state.get("auth_suite") == suite_name
        and group_state.get("auth_token")
        and group_state.get("stand_host")
    ):
        return

    stand_host = build_stand_host()
    auth_token = get_token(force_refresh=True)

    group_state["stand_host"] = stand_host
    group_state["auth_token"] = auth_token
    group_state["auth_suite"] = suite_name

    logger.info("[AUTH] Инициализация token для dataset '%s'", suite_name)


def ensure_suite_x_user_id(group_state: dict) -> None:
    """
    Один раз на dataset: x-user-id через /Ping к api-gateway.
    Выполняется после старта api-gateway (Docker).
    """
    if group_state.get("x_user_id"):
        return

    if not group_state.get("auth_token") or not group_state.get("stand_host"):
        pytest.exit("[AUTH] auth_token не инициализирован - ожидается ensure_suite_token()")

    http_client = StandHttpClient(group_state["stand_host"], group_state["auth_token"])
    group_state["x_user_id"] = _fetch_x_user_id(http_client)

    logger.info("[AUTH] Инициализация x-user-id для dataset '%s'", group_state.get("auth_suite"))


def ensure_suite_auth(group_state: dict, suite_name: str) -> None:
    """
    Один раз на dataset: access token (Keycloak) + x-user-id (/Ping).
    """
    if (
        group_state.get("auth_suite") == suite_name
        and group_state.get("auth_token")
        and group_state.get("x_user_id")
    ):
        return

    ensure_suite_token(group_state, suite_name)
    ensure_suite_x_user_id(group_state)


def ensure_auth_for_fixture(group_state: dict, *, require_x_user_id: bool = False) -> None:
    """
    Подстраховка для фикстур http_client / ws_client.

    Основная инициализация auth выполняется в pytest_runtest_setup при смене dataset.
    Если тест по какой-то причине стартует раньше (нет current_suite), здесь
    выполняется инициализация по auth_suite или fallback '__default__'.
    """
    suite_name = group_state.get("current_suite") or group_state.get("auth_suite") or "__default__"
    ensure_suite_token(group_state, suite_name)
    if require_x_user_id:
        ensure_suite_x_user_id(group_state)


def _require_auth(group_state: dict, *, require_x_user_id: bool = False) -> None:
    if not group_state.get("auth_token") or not group_state.get("stand_host"):
        pytest.exit("[AUTH] auth не инициализирован - ожидается ensure_suite_token()")
    if require_x_user_id and not group_state.get("x_user_id"):
        pytest.exit("[AUTH] x_user_id не инициализирован - ожидается ensure_suite_x_user_id()")


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
