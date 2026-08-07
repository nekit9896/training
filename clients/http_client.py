import json
import logging
import os
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from constants.architecture_constants import EnvKeyConstants as Env_const
from constants.architecture_constants import HTTPClientConstants as Http_const

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Выполняет http запросы
    """

    def __init__(self):
        self.session = self._create_retry_session()

    @staticmethod
    def make_request(method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Обертка для отправки запроса
        :param method:
        :param url:
        :param kwargs: прочие параметры запроса
        :return: объект ответа
        """
        try:
            logging.info(f"[HTTP_CLIENT] Выполняю запрос: METHOD: {method} URL: {url}")
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as error:
            logger.error(
                f"[HTTP_CLIENT] [ERROR] При выполнении запроса. METHOD: {method} URL: {url} ERROR_TEXT:{error}"
            )
            raise
        except requests.RequestException:
            logger.exception(f"[HTTP_CLIENT] [ERROR] При выполнении запроса. METHOD: {method} URL: {url}")
            raise

    def make_session_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Обертка для отправки запроса
        :param method:
        :param url:
        :param kwargs: прочие параметры запроса
        :return: объект ответа
        """
        try:
            logging.info(f"[HTTP_CLIENT] Выполняю запрос: METHOD: {method} URL: {url}")
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as error:
            logger.error(
                f"[HTTP_CLIENT] [ERROR] При выполнении запроса. METHOD: {method} URL: {url} ERROR_TEXT:{error}"
            )
            raise
        except requests.RequestException:
            logger.exception(f"[HTTP_CLIENT] [ERROR] При выполнении запроса. METHOD: {method} URL: {url}")
            raise

    @staticmethod
    def get_base_url(url_key: str) -> str:
        return os.environ.get(url_key)

    @staticmethod
    def generate_full_url(base_url: str, endpoint: str) -> str:
        return f"https://{base_url}{endpoint}"

    def post_upload_allure_results(self, files) -> Optional[requests.Response]:
        """
        Обертка для выполнения запроса на загрузку отчетов
        :return: объект ответа на запрос загрузки отчета
        """
        base_testops_url = self.get_base_url(Env_const.TESTOPS_BASE_URL)
        full_url = self.generate_full_url(base_testops_url, Http_const.TESTOPS_UPLOAD_ENDPOINT)
        response = self.make_request(Http_const.POST_METHOD, full_url, files=files)
        return response

    def get_attachments_list_by_test_case_id(self, test_case_id: int) -> dict:
        """
        Получает список вложений для тест кейса по id через GET запрос к TESTOPS
        :return: содержимое ответа на запрос
        """
        base_testops_url = self.get_base_url(Env_const.TESTOPS_BASE_URL)
        full_endpoint = Http_const.TESTOPS_ATTACHMENTS_LIST_ENDPOINT.format(test_case_id=test_case_id)
        full_url = self.generate_full_url(base_testops_url, full_endpoint)
        response = self.make_request(Http_const.GET_METHOD, full_url)
        return response.json()

    def get_test_case_attachment_by_id(self, test_case_id: int, attachment_id: int) -> bytes:
        """
        Получает вложение по id через GET запрос к TESTOPS
        :return: содержимое ответа на запрос
        """
        base_testops_url = self.get_base_url(Env_const.TESTOPS_BASE_URL)
        full_endpoint = Http_const.TESTOPS_LOAD_ATTACHMENT_ENDPOINT.format(
            test_case_id=test_case_id, attachment_id=attachment_id
        )
        full_url = self.generate_full_url(base_testops_url, full_endpoint)
        response = self.make_request(Http_const.GET_METHOD, full_url)
        if not response.content:
            logger.exception(f"[HTTP_CLIENT] [ERROR] Пустой response.content при запросе URL: {full_url}")
            raise ValueError
        return response.content

    @staticmethod
    def _create_retry_session(
        retries: int = 3,
        backoff_factor: float = 0.3,
        status_forcelist: tuple = Http_const.STATUS_FORCE_LIST,
        allowed_methods: tuple = Http_const.ALLOWED_METHODS,
    ) -> requests.Session():
        """
        Создает сессию для выполнения нескольких одинаковых запросов
        """
        session = requests.Session()
        retry = Retry(
            total=retries,
            read=retries,
            connect=retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist,
            allowed_methods=allowed_methods,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("http//", adapter)
        session.mount("https//", adapter)
        return session


class StandHttpClient(HttpClient):
    """
    Выполняет http запросы к стендам
    """

    def __init__(self, stand_url: str, token: str) -> None:
        super().__init__()
        self._stand_url = stand_url
        self._token = token
        self._headers = self._add_token_to_headers()
        self.session.headers.update(self._headers)

    def _add_token_to_headers(self) -> dict:
        """
        Добавляет token в headers запроса
        """
        headers = Http_const.DEFAULT_HEADERS.copy()
        headers[Http_const.X_SECURITY_SIGNATURE_KEY] = self._token
        return headers

    def post_request(self, endpoint: str, payload: dict | str) -> Optional[requests.Response]:
        """
        Делает http post запрос к стенду
        """
        full_url = self.generate_full_url(self._stand_url, endpoint)
        json_payload = json.dumps(payload)
        response = self.make_session_request(Http_const.POST_METHOD, full_url, data=json_payload)
        return response
