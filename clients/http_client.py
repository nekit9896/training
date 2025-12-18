import logging
import os
from typing import Optional

import requests

from constants.architecture_constants import EnvKeyConstants as Env_const
from constants.architecture_constants import HTTPClientConstants as Http_const

logger = logging.getLogger(__name__)


class HttpClient:
    """
    Выполняет http запросы
    """

    def __init__(self):
        pass

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
        except requests.RequestException:
            logger.exception(
                f"[HTTP_CLIENT] [ERROR] При выполнении запроса. METHOD: {method} URL: {url}"
            )

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
        full_url = self.generate_full_url(
            base_testops_url, Http_const.TESTOPS_UPLOAD_ENDPOINT
        )
        response = self.make_request(Http_const.POST_METHOD, full_url, files=files)
        return response

    def get_attachments_list_by_test_case_id(self, test_case_id: int) -> dict:
        """
        Получает список вложений для тест кейса по id через GET запрос к TESTOPS
        :return: содержимое ответа на запрос
        """
        base_testops_url = self.get_base_url(Env_const.TESTOPS_BASE_URL)
        full_endpoint = Http_const.TESTOPS_ATTACHMENTS_LIST_ENDPOINT.format(
            test_case_id=test_case_id
        )
        full_url = self.generate_full_url(base_testops_url, full_endpoint)
        response = self.make_request(Http_const.GET_METHOD, full_url)
        return response.json()

    def get_test_case_attachment_by_id(
        self, test_case_id: int, attachment_id: int
    ) -> bytes:
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
        return response.content
