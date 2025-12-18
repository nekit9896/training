import logging
import tarfile
from pathlib import Path
from typing import List

from models.http_models.attacments_list_testops_model import FileInfo, Items

from clients.http_client import HttpClient
from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import HTTPClientConstants as Http_const
from constants.architecture_constants import ImitatorConstants as Im_const
from infra.cmd_generator import UploadImitatorDataCmdGenerator
from infra.path_generator import ImitatorDataPathGenerator

logger = logging.getLogger(__name__)


class ImitatorDataUploader:
    """
    Класс загрузки набора данных на удаленный сервер, нужных для запуска имитатора
    Пример использования:
    uploader = ImitatorDataUploader(your_user, your_host, test_id)
    uploader.upload_with_confirm() - для загрузки данных на удаленный сервер
    remote_temp_path = uploader.remote_temp_dir_path - для получения пути ко временной директории
    uploader.delete_with_confirm() - для удаления данных на удаленном сервере
    """

    def __init__(
        self, stand_client: SubprocessClient, test_data_id: int, test_data_name: str
    ) -> None:

        self._username = stand_client.username
        self._host = stand_client.host
        self._test_data_id = test_data_id
        self._test_data_name = test_data_name
        self._http_client = HttpClient()
        self._stand_client = stand_client
        self._path_generator = ImitatorDataPathGenerator(test_data_id)
        self._cmd_generator = UploadImitatorDataCmdGenerator(
            self._username, self._host, self._path_generator
        )
        self._subprocess_client = UploadDataSubprocessClient(
            stand_client, self._cmd_generator
        )
        self._tar_package_name = self._path_generator.tar_package_name
        self.remote_temp_dir_path = self._path_generator.remote_temp_dir_path

    def upload_with_confirm(self) -> None:
        """
        Выполняется основной сценарий загрузки данных на удаленный сервер
        """
        # 1. Загрузка архива на runner
        imitator_data_bytes = self._get_run_data_bytes()
        # 2. Сохранение архива на runner
        self._save_test_data_package(imitator_data_bytes)
        # 3. Проверка архива на runner
        if not self._is_tar_valid():
            logging.error(
                f"[DATA UPLOADER] [ERROR] Архив: {self._tar_package_name} поврежден на runner"
            )
            raise ValueError("[DATA UPLOADER] [ERROR] При проверке архива на runner")
        # 4. Создание временной директории на удаленном сервере
        self._subprocess_client.create_remote_data_dir()
        # 5. Копирование архива во временную директорию на удаленный сервер
        self._subprocess_client.copy_tar_to_remote()
        # 6. Проверка целостности архива на удаленном сервере
        if not self._subprocess_client.is_remote_tar_valid():
            logging.error(
                f"[DATA UPLOADER] [ERROR] Архив: {self._tar_package_name} поврежден на удаленном сервере: {self._host}"
            )
            raise ValueError(
                "[DATA UPLOADER] [ERROR] При проверке архива на удаленном сервере"
            )
        # 7. Распаковка архива
        self._subprocess_client.unpack_remote_package()
        # 8. Проверка данных
        if not self._subprocess_client.check_remote_unpack_data():
            logging.error(
                f"[DATA UPLOADER] [ERROR] При распаковке данных на удаленном сервере: "
                f"{self._host} Путь: {self.remote_temp_dir_path}"
            )
            raise ValueError(
                "[DATA UPLOADER] [ERROR] При распаковке данных на удаленном сервере"
            )
        logging.info(
            f"[DATA UPLOADER] [OK] Тестовые данные успешно загружены на удаленный сервер: "
            f"{self._host} Путь: {self.remote_temp_dir_path}"
        )

    def delete_with_confirm(self) -> None:
        """
        Удаление временной директории с удаленного сервера с проверкой удаления
        """
        self._subprocess_client.delete_remote_data_dir()
        if self._subprocess_client.check_remote_unpack_data():
            logging.error(
                f"[DATA UPLOADER] [ERROR] При удалении данных на удаленном сервере: "
                f"{self._host} Путь: {self.remote_temp_dir_path}"
            )
            raise ValueError("[DATA UPLOADER] [ERROR] При проверке удаления данных")
        logging.info(
            f"[DATA UPLOADER] [OK] Тестовые данные успешно удалены с удаленного сервера: {self._host}"
        )

    def _get_test_data_attachment_id_by_name(self, attachments_list: dict) -> int:
        """
        Получает id архива данных для имитатора
        """
        parsed_attachments_list = Items(
            items=[
                FileInfo(**file)
                for file in attachments_list.get(Http_const.TESTOPS_ATTACHMENTS_KEY, [])
            ]
        )
        attachment_id = next(
            (
                file.id
                for file in parsed_attachments_list.items
                if file.original_filename == self._test_data_name
            ),
            None,
        )
        return attachment_id

    def _get_run_data_bytes(self) -> bytes:
        """
        Получает данные через GET запрос к Testops
        :return: содержимое ответа на запрос
        """
        # Получает список вложений для test_data_id
        attachments_list = self._http_client.get_attachments_list_by_test_case_id(
            self._test_data_id
        )
        # Получает id архива данных
        attachment_id = self._get_test_data_attachment_id_by_name(attachments_list)
        run_data_bytes = self._http_client.get_test_case_attachment_by_id(
            self._test_data_id, attachment_id
        )
        return run_data_bytes

    def _is_tar_valid(self) -> bool:
        """
        Проверяет целостность архива на runner после скачивания с testops
        """
        req_files = {Im_const.SANDBOX_TAGS, Im_const.SANDBOX_RULES}
        req_dir = Im_const.SANDBOX_DATA
        try:
            with tarfile.open(self._tar_package_name, "r:gz") as tar_file:
                names = set(tar_file.getnames())
                has_dir = any(name.startswith(req_dir) for name in names)
                has_files = req_files.issubset(names)
                if not has_dir or not has_files:
                    raise FileNotFoundError(
                        "[DATA UPLOADER] [ERROR] В архиве на runner отсутствуют необходимые файлы"
                    )
                return has_dir and has_files
        except tarfile.TarError:
            logging.exception("[DATA UPLOADER] [ERROR] Архив на runner поврежден")
            raise

    def _save_test_data_package(self, tar_bytes: bytes) -> None:
        """
        Сохраняет архив тестовых данных в рабочей директории runner
        :return: путь к архиву
        """
        file_path = Path(self._tar_package_name)
        try:
            with open(file_path, "wb") as tar_file:
                tar_file.write(tar_bytes)
            logging.info(
                f"[DATA UPLOADER] [OK] Архив: {self._tar_package_name} успешно сохранен на runner"
            )
        except (FileNotFoundError, PermissionError, OSError):
            logging.exception("[DATA UPLOADER] [ERROR] При сохранении архива на runner")
            raise


class UploadDataSubprocessClient:
    """
    Выполняет команды в консоли для загрузки данных прогона для имитатора
    """

    def __init__(
        self, client: SubprocessClient, cmd_generator: UploadImitatorDataCmdGenerator
    ) -> None:
        self._client = client
        self._expected_files: List[str] = list(cmd_generator.expected_files)
        self._cmd_generator = cmd_generator

    def create_remote_data_dir(self) -> None:
        """
        Создает временную директорию на удаленном сервере
        """
        create_dir_cmd = self._cmd_generator.generate_create_dir_cmd()
        self._client.run_cmd(create_dir_cmd)

    def delete_remote_data_dir(self) -> None:
        """
        Удаляет временную директорию на удаленном сервере
        """
        delete_dir_cmd = self._cmd_generator.generate_delete_dir_cmd()
        self._client.run_cmd(delete_dir_cmd)

    def copy_tar_to_remote(self) -> None:
        """
        Копирует архив во временную директорию на удаленном сервере
        """
        copy_cmd = self._cmd_generator.generate_copy_tar_to_remote_cmd()
        self._client.run_cmd(
            copy_cmd, timeout=Im_const.LONG_PROCESS_TIMEOUT_S, use_ssh=False
        )

    def unpack_remote_package(self) -> None:
        """
        Распаковывает архив во временную директорию на удаленном сервере
        """
        unpack_cmd = self._cmd_generator.generate_unpack_tar_cmd()
        self._client.run_cmd(unpack_cmd, timeout=Im_const.LONG_PROCESS_TIMEOUT_S)

    def is_remote_tar_valid(self) -> bool:
        """
        Проверка целостности архива
        :return: результат проверки
        """
        check_tar_cmd = self._cmd_generator.generate_check_tar_cmd()
        result = self._client.run_cmd(check_tar_cmd, need_output=True)
        if not result:
            return False

        tar_list = result.split("\n")

        return all(file in tar_list for file in self._expected_files)

    def check_remote_unpack_data(self) -> bool:
        """
        Проверяет наличие директории с данными и сопутствующих файлов
        :return: результат проверки
        """
        check_cmd = self._cmd_generator.generate_check_remote_data_cmd()
        result = self._client.run_cmd(check_cmd, need_output=True)
        return result == Im_const.CMD_STATUS_OK
