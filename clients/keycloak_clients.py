import logging
import time
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

from constants.architecture_constants import KeycloakClientConstants

load_dotenv()


class KeycloakAuthError(Exception):
    """
    Исключение для ошибок, возникающих при авторизации в Keycloak.

    Атрибуты:
        message (str): Сообщение об ошибке.
        error_code (int, optional): Код ошибки HTTP.
        details (str, optional): Дополнительные детали об ошибке.
    """

    def __init__(
        self,
        message: Optional[str] = None,
        error_code: Optional[int] = None,
        details: Optional[str] = None,
    ):
        self.message = message or "Ошибка авторизации с Keycloak"
        self.error_code = error_code
        self.details = details
        super().__init__(self.message)

    def __str__(self):
        """
        Возвращает строковое представление ошибки.
        """
        parts = [self.message]
        if self.error_code:
            parts.append(f"(код: {self.error_code})")
        if self.details:
            parts.append(f"- детали: {self.details}")
        return " ".join(parts)


class KeycloakClient:
    """
    Клиент для получения JWT access token из Keycloak с помощью Resource Owner Password Credentials.
    """

    def __init__(
        self, url: str, client_id: str, client_secret: str, username: str, password: str
    ):
        """
        Инициализация клиента Keycloak.

        Аргументы:
            url (str): URL нашего keycloak.
            client_id (str): ID клиента автотестов из keycloak.
            client_secret (str): Секрет клиента автотестов из keycloak.
            username (str): Логин пользователя автотестов из keycloak.
            password (str): Пароль пользователя автотестов из keycloak.
        """
        self.url = url
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self._token: Optional[str] = None
        self._token_data: Optional[Dict[str, Any]]
        self.token_leeway = KeycloakClientConstants.TOKEN_LEEWAY
        self.grant_type = KeycloakClientConstants.GRANT_TYPE
        self.token_key = KeycloakClientConstants.TOKEN_KEY
        self.keycloak_headers = KeycloakClientConstants.KEYCLOAK_HEADERS
        self.issued_at_key = KeycloakClientConstants.ISSUED_AT_KEY
        self.expires_in = KeycloakClientConstants.EXPIRES_IN_KEY
        self._validate_creds()

    def _validate_creds(self):
        required_vars = {
            "KEYCLOAK_URL": self.url,
            "KEYCLOAK_CLIENT_ID": self.client_id,
            "KEYCLOAK_CLIENT_SECRET": self.client_secret,
            "KEYCLOAK_USERNAME": self.username,
            "KEYCLOAK_PASSWORD": self.password,
        }
        for name, value in required_vars.items():
            if not value:
                logging.error(f"Отсутствует обязательная переменная окружения: {name}")
                exit(1)

    def get_access_token(self):
        """
        Получает текущий Access Token. Если токена нет или устарел, запрашивает новый у Keycloak через _request_token()
        Возвращает JWT access token.
        Рейзим на KeycloakAuthError если не удалось получить токен.
        """
        if not self._token or self._is_token_expired():
            self._token = self._request_token()
        return self._token

    def _request_token(self):
        """
        Делает запрос к Keycloak для получения Access Token. Возвращает JWT access token.
        Если ошибка рейзим на KeycloakAuthError: в случае ошибки авторизации или сети.
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": self.username,
            "password": self.password,
            "grant_type": self.grant_type,
        }
        try:
            headers = self.keycloak_headers
            response_token = requests.post(
                self.url, data=data, headers=headers, timeout=5
            )
            response_token.raise_for_status()
            token_data = response_token.json()
            token = token_data.get(self.token_key)
            if not token:
                raise KeycloakAuthError(
                    "Ответ не содержит access_token", details=str(token_data)
                )
            self._token = token
            self._token_data = token_data
            self._token_data[self.issued_at_key] = int(time.time())
            logging.info("Успешно получен access token")
            return token_data[self.token_key]
        except requests.HTTPError as http_err:
            try:
                error_json = response_token.json()
                error_details = error_json.get("error_description") or error_json.get(
                    "error"
                )
            except ValueError:
                error_details = str(http_err)
            error_code = (
                response_token.status_code if response_token is not None else None
            )
            logging.error(f"HTTPError при авторизации в Keycloak: {http_err}")
            raise KeycloakAuthError(
                message="Ошибка HTTP авторизации в Keycloak",
                error_code=error_code,
                details=error_details,
            )
        except requests.RequestException as req_err:
            logging.error(f"Сетевая ошибка при соединении с Keycloak: {req_err}")
            raise KeycloakAuthError(
                message="Ошибка сетевого соединения с Keycloak", details=str(req_err)
            )
        except KeyError as key_err:
            logging.error(f"Некорректный формат ответа от Keycloak: {key_err}")
            raise KeycloakAuthError(
                message="Некорректный формат ответа от Keycloak", details=str(key_err)
            )

    def _is_token_expired(self):
        """
        Проверяет, истёк ли текущий access token.
            Для проверки используется поле 'expires_in' в ответе Keycloak
            и локальное время получения токена. Если информация отсутствует,
            считаем токен недействительным.
        """
        if not self._token_data or not self._token:
            return True
        expires_in = self._token_data.get(self.expires_in)
        issued_at = self._token_data.get(self.issued_at_key)
        if not expires_in or not issued_at:
            return True
        now = int(time.time())
        if now >= issued_at + expires_in - self.token_leeway:
            return True
        return False
