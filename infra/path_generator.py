import logging
from datetime import datetime
from pathlib import PurePosixPath  # Используется для корректного запуска на Windows

from constants.architecture_constants import ImitatorConstants as JC_const

logger = logging.getLogger(__name__)


class ImitatorDataPathGenerator:
    """
    Генерация путей для данных прогона
    """

    def __init__(self, test_data_id: int):
        self._test_data_id = test_data_id
        self._expected_files: list = [JC_const.SANDBOX_TAGS, JC_const.SANDBOX_RULES]
        self._test_package_name = self._generate_test_package_name()
        # Временное название архива
        self.tar_package_name = self._add_tar_extension()
        # Путь к временной директории
        self.remote_temp_dir_path = self._generate_remote_temp_dir_path()

    def _generate_test_package_name(self) -> str:
        """
        Создает уникальное имя для набора данных
        :return: уникальное имя для набора данных
        """
        time_now_str = datetime.now().strftime(JC_const.IMITATOR_TIME_FORMAT)
        return f"test_case_id_{self._test_data_id}_{time_now_str}"

    def _add_tar_extension(self) -> str:
        """
        Добавляет tar расширение к имени набора данных
        :return: уникальное имя архива набора данных
        """
        return f"{self._test_package_name}.tar.gz"

    def _generate_remote_temp_dir_path(self) -> str:
        """
        Создает путь к временной директории на удаленном сервере
        :return: путь к временной директории на удаленном сервере
        """
        remote_temp_dir_path = PurePosixPath(JC_const.AUTOTEST_DATA_PATH) / self._test_package_name
        return str(remote_temp_dir_path)

    def generate_full_remote_tar_path(self) -> str:
        """
        Создает путь к архиву на удаленном сервере
        :return: путь к архиву на удаленном сервере
        """
        full_remote_tar_path = PurePosixPath(self.remote_temp_dir_path) / self.tar_package_name
        return str(full_remote_tar_path)
