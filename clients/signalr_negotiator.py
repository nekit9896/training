"""
Negotiate-контракт SignalR: получение connectionId/connectionToken до wss-подключения.

По connectionId/connectionToken api-gateway понимает,
что появился подписанный клиент, и поднимает консьюмеры для чтения топиков core и layer
builder. Без negotiate консьюмеры не вычитывают сообщения, и они приходят в автотесты с
большим опозданием.

Поведение повторяет фронт:
POST /hubs/ldsClientHub/negotiate?token=<jwt>&xUserId=<uid>&negotiateVersion=1
с заголовком x-security-signature, после чего wss-соединение устанавливается
по connectionToken через параметр id=.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any, Optional

import requests
from allure import attach, attachment_type

from clients.http_client import StandHttpClient
from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.architecture_constants import WebSocketClientConstants as WS_Const

logger = logging.getLogger(__name__)


class NegotiationError(ConnectionError):
    """
    Ошибка выполнения negotiate.

    Наследование от ConnectionError: цикл подключения WebSocketClient._connect_loop
    уже умеет повторять попытки для ошибок соединения, поэтому сбой negotiate
    приводит к повтору всей последовательности "negotiate -> wss" без отдельного ветвления.
    """


@dataclass(frozen=True)
class NegotiationResult:
    """Результат negotiate: идентификаторы соединения и список доступных транспортов."""

    connection_id: str
    connection_token: str
    available_transports: tuple


class SignalRNegotiator:
    """
    Выполняет POST на ручку negotiate и разбирает ответ api-gateway.
    """

    def __init__(self, host: str, access_token: str) -> None:
        """
        хост api-gateway (например web-app.lds-test4.tn.tngrp.ru/lds-api-gateway)
        JWT access token; уходит в query-параметр token=
        """
        self._host = host
        self._access_token = access_token
        # Отдельная http-сессия: negotiate живёт внутри цикла подключения и не должен делить
        # suppress_recv_logging и attach-политику с http_client конкретного теста.
        self._http_client = StandHttpClient(host, access_token)

    def negotiate(
        self,
        x_user_id: str,
        max_retries: int = WS_Const.NEGOTIATE_MAX_RETRIES,
        backoff: float = WS_Const.NEGOTIATE_RETRY_BACKOFF_S,
    ) -> NegotiationResult:
        """
        Запрашивает connectionId/connectionToken с повторными попытками.
        """
        url = self._build_negotiate_url(x_user_id)
        last_error: Optional[BaseException] = None
        previous_suppression = self._http_client.suppress_recv_logging
        self._http_client.suppress_recv_logging = True
        try:
            for attempt in range(1, max_retries + 1):
                logger.info("[NEGOTIATE] Попытка %s из %s: %s", attempt, max_retries, self._mask_token(url))
                try:
                    response = self._http_client.make_session_request(
                        HttpConst.POST_METHOD, url, timeout=WS_Const.NEGOTIATE_TIMEOUT_S
                    )
                    result = self._parse_response(response.json())
                    self._validate_transports(result)
                    self._attach_negotiation_result(result)
                    logger.info("[NEGOTIATE] [OK] Получен connectionId=%s", result.connection_id)
                    return result
                except (NegotiationError, requests.RequestException, ValueError, KeyError, TypeError) as error:
                    last_error = error
                    logger.warning("[NEGOTIATE] Попытка %s из %s неуспешна: %s", attempt, max_retries, error)
                    if attempt < max_retries:
                        time.sleep(backoff)
        finally:
            self._http_client.suppress_recv_logging = previous_suppression

        raise NegotiationError(f"negotiate не выполнен после {max_retries} попыток: {last_error}")

    def close(self) -> None:
        """Закрывает http-сессию negotiate (освобождает соединения пула)."""
        self._http_client.session.close()

    def _build_negotiate_url(self, x_user_id: str) -> str:
        """Собирает полный URL negotiate: путь хаба + token, xUserId, negotiateVersion."""
        query = WS_Const.NEGOTIATE_QUERY_TEMPLATE.format(
            token=self._access_token,
            x_user_id=x_user_id,
            negotiate_version=WS_Const.NEGOTIATE_VERSION,
        )
        return StandHttpClient.generate_full_url(self._host, f"{WS_Const.NEGOTIATE_URL_PATH}{query}")

    def _mask_token(self, url: str) -> str:
        """Скрывает JWT в URL для логов."""
        if not self._access_token:
            return url
        return url.replace(self._access_token, WS_Const.MASKED_TOKEN)

    @staticmethod
    def _parse_response(payload: Any) -> NegotiationResult:
        """Разбирает ответ negotiate и проверяет наличие обязательных полей."""
        if not isinstance(payload, dict):
            raise NegotiationError(f"Ответ negotiate не является объектом: {type(payload).__name__}")

        connection_id = payload.get(WS_Const.CONNECTION_ID_KEY)
        connection_token = payload.get(WS_Const.CONNECTION_TOKEN_KEY)
        if not connection_id or not connection_token:
            raise NegotiationError(
                f"Ответ negotiate не содержит {WS_Const.CONNECTION_ID_KEY}/{WS_Const.CONNECTION_TOKEN_KEY}: {payload}"
            )

        return NegotiationResult(
            connection_id=str(connection_id),
            connection_token=str(connection_token),
            available_transports=SignalRNegotiator._parse_transports(payload.get(WS_Const.AVAILABLE_TRANSPORTS_KEY)),
        )

    @staticmethod
    def _parse_transports(raw_transports: Any) -> tuple:
        """Извлекает названия транспортов из availableTransports ответа negotiate."""
        if not isinstance(raw_transports, list):
            return ()
        transports = []
        for item in raw_transports:
            if isinstance(item, dict) and item.get(WS_Const.TRANSPORT_KEY):
                transports.append(str(item[WS_Const.TRANSPORT_KEY]))
        return tuple(transports)

    @staticmethod
    def _validate_transports(result: NegotiationResult) -> None:
        """
        Проверяет, что hub отдаёт WebSockets-транспорт.
        """
        if not result.available_transports:
            logger.warning("[NEGOTIATE] Ответ не содержит availableTransports, проверка транспорта пропущена")
            return
        if WS_Const.WEBSOCKETS_TRANSPORT not in result.available_transports:
            raise NegotiationError(
                f"hub не поддерживает {WS_Const.WEBSOCKETS_TRANSPORT}: "
                f"доступные транспорты {result.available_transports}"
            )

    @staticmethod
    def _attach_negotiation_result(result: NegotiationResult) -> None:
        """Прикладывает к Allure результат negotiate."""
        try:
            attach(
                f"connectionId: {result.connection_id}\n"
                f"connectionToken: {WS_Const.MASKED_TOKEN}\n"
                f"availableTransports: {', '.join(result.available_transports) or 'нет данных'}",
                name="SignalR negotiate response",
                attachment_type=attachment_type.TEXT,
            )
        except (KeyError, RuntimeError) as error:
            logger.debug("Allure attach negotiate пропущен: %s", error)
