import json
import logging
import os
from pathlib import Path
from typing import BinaryIO, Optional

import conftest
import requests

from constants.architecture_constants import EnvKeyConstants as Env_Const
from constants.architecture_constants import TestOpsConstants as T_const

logger = logging.getLogger(__name__)


class AllureResultsFileManager:
    """
    Подготавливает файлы allure отчета для отправки по http
    """

    def __init__(self):
        self._script_dir_path = self._get_script_dir_path()
        self._allure_results_path = self._get_allure_results_path()
        self._allure_results_files_list = self._get_allure_results_files_list()

    def setup_allure_results_for_upload(self) -> list[tuple[str, tuple[str, Optional[BinaryIO]]]]:
        """
        Финальная стадия подготовки файлов allure отчета для отправки по http
        :return: финальная версия списка файлов
        """
        files = []
        for file in self._allure_results_files_list:
            file_obj = self._get_file_object(file)
            files.append((T_const.TESTOPS_UPLOAD_FILES_KEY, (file.name, file_obj)))
        return files

    @staticmethod
    def _get_file_object(file_path: Path) -> Optional[BinaryIO]:
        """
        Открывает файл в режиме 'rb'
        :param file_path: путь к файлу
        :return: открытый файл
        """
        if file_path.is_file():
            try:
                file_obj = open(file_path, "rb")
                return file_obj
            except OSError:
                logger.exception(f"[TEARDOWN] [ERROR] Не удалось открыть файл: {file_path}")
                return None
        else:
            logger.warning(f"[TEARDOWN] [WARNING] Не является файлом: {file_path}")
            return None

    @staticmethod
    def _get_script_dir_path() -> Path:
        """
        :return: путь к директории, в которой хранится скрипт
        """
        return Path(__file__).resolve().parent

    def _get_allure_results_path(self) -> Path:
        """
        :return: путь к директории allure-results
        """
        allure_results_path = self._script_dir_path.parent / T_const.ALLURE_RESULTS_DIR_NAME
        if not allure_results_path.is_dir():
            logger.error(f"[TEARDOWN] [ERROR] {T_const.ALLURE_RESULTS_DIR_NAME} не найдена или не является директорией")
            raise FileNotFoundError
        return allure_results_path

    def _create_environment_properties(self) -> None:
        """
        Создает файл environment.properties в allure-results с json-объектом
        {
            "stand": "<STAND_NAME>"
        }
        """
        stand_key = Env_Const.STAND_NAME

        stand_value = os.environ.get(stand_key)

        environment_properties_path = self._allure_results_path / "environment.properties"
        try:
            with environment_properties_path.open("w", encoding="utf-8") as env_prop_file:
                json.dump({"stand": stand_value}, env_prop_file, ensure_ascii=False, indent=1)
            logger.info(f"[TEARDOWN] [OK] Создан файл environment.properties в {env_prop_file}")
        except Exception:
            logger.exception(f"[TEARDOWN] [ERROR] Не удалось создать {env_prop_file}")

    def _get_allure_results_files_list(self) -> list[Path]:
        """
        :return: список всех файлов в директории allure-results
        Перед сбором файлов создаем environment.properties
        """
        self._create_environment_properties()

        files_list = list(self._allure_results_path.rglob("*"))
        return files_list


class AllureResultsUploader:
    """
    Отправка отчета в TestOps
    from clients.testops_client import AllureResultsUploader
    uploader = AllureResultsUploader()
    uploader.upload_allure_results()
    """

    def __init__(self):
        self._file_manager: AllureResultsFileManager = AllureResultsFileManager()
        self._files: list[tuple[str, tuple[str, Optional[BinaryIO]]]] = (
            self._file_manager.setup_allure_results_for_upload()
        )

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
            response = requests.request(method, url, **kwargs)
            response.raise_for_status()
            return response
        except Exception as e:
            logger.error(f"[TEARDOWN] [ERROR] METHOD: {method} URL: {url}. Ошибка выполнения запроса: {e}")
            pytest.exit(f"Не удалось загрузить allure-results: {e}")

    def upload_allure_results(self) -> None:
        """
        Отправляет отчеты в TestOps по http
        """
        try:
            response = self._make_upload_request()
            if response:
                message = self._get_upload_success_msg(response)
                logger.info(f"[TEARDOWN] [OK] UPLOAD MESSAGE: {message}")
            else:
                logger.error(f"[TEARDOWN] [ERROR] {T_const.TESTOPS_UPLOAD_ERROR_MSG}")

        finally:
            # Закрывает файлы
            for _, (_, file_obj) in self._files:
                if file_obj:
                    try:
                        file_obj.close()
                    except Exception:
                        logger.exception("[TEARDOWN] [WARNING] Ошибка при закрытии файла")

    @staticmethod
    def _get_upload_success_msg(response: requests.Response) -> str:
        """
        Пытается получить значение для ключа 'message' из ответа на запрос отправки
        :param response:
        :return: значение для ключа 'message'
        """
        try:
            response_json = response.json()
            message = response_json.get(T_const.TESTOPS_UPLOAD_RESPONSE_MSG_KEY, T_const.TESTOPS_UPLOAD_ERROR_MSG)
            return message
        except ValueError:
            logger.exception("[TEARDOWN] [ERROR] Ошибка получения сообщения о загрузке файлов allure отчета")

    def _make_upload_request(self) -> Optional[requests.Response]:
        """
        Обертка для выполнения запроса на загрузку отчетов
        :return: объект ответа на запрос загрузки отчета
        """
        base_testops_url = os.environ.get(Env_Const.TESTOPS_BASE_URL)
        full_url = f"https://{base_testops_url}{T_const.TESTOPS_UPLOAD_ENDPOINT}"
        response = self.make_request(T_const.POST_METHOD, full_url, files=self._files)
        return response
