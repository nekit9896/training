import logging
import os
from datetime import datetime, timedelta
from pathlib import PurePosixPath

import allure

from constants.architecture_constants import EnvKeyConstants
from constants.architecture_constants import ImitatorConstants as Im_const
from infra.path_generator import ImitatorDataPathGenerator

logger = logging.getLogger(__name__)


class TimeProcessor:
    """
    Класс для получения времени запуска и остановки имитатора
    Для получения времени:
    from utils.flag_generator import TimeProcessor
    time_processor = TimeProcessor(test_duration_m)
    start_time = time_processor.formatted_start_time
    stop_time = time_processor.formatted_stop_time
    """

    def __init__(self, duration_m: float) -> None:
        self._duration_m = duration_m
        self._current_time: datetime = datetime.now()
        self._start_time: datetime = self._add_time_delta(
            seconds=Im_const.IMITATOR_START_DELAY_S
        )
        self._formatted_start_time: str = self._get_formatted_start_time()
        self._formatted_stop_time: str = self._get_formatted_stop_time()

    @property
    def formatted_start_time(self) -> str:
        return self._formatted_start_time

    @property
    def formatted_stop_time(self) -> str:
        return self._formatted_stop_time

    def _add_time_delta(self, minutes: float = 0, seconds: int = 0) -> datetime:
        """
        :param minutes: время в минутах
        :param seconds: время в секундах
        :return: текущее время + добавленное время
        """
        try:
            delta = timedelta(minutes=minutes, seconds=seconds)
            current_time_with_delta = self._current_time + delta
            return current_time_with_delta

        except (ValueError, TypeError):
            logger.exception("[ERROR] Ошибка при добавлении времени")
            raise

    @staticmethod
    def get_formatted_time(time) -> str:
        """
        :param time: время в формате datetime
        :return: время в формате строки, которую принимает имитатор
        """
        try:
            formatted_time = time.strftime(Im_const.IMITATOR_TIME_FORMAT)
            return formatted_time

        except (ValueError, TypeError):
            logger.exception("[ERROR] Ошибка при форматировании времени")
            raise

    def _get_formatted_start_time(self) -> str:
        """
        :return: время запуска имитатора строкой
        """
        formatted_start_time = self.get_formatted_time(self._start_time)
        return formatted_start_time

    def _get_formatted_stop_time(self) -> str:
        """
        Добавляет время прогона ко времени отсрочки пуска имитатора
        :return: время остановки имитатора строкой
        """

        stop_time = self._add_time_delta(
            minutes=self._duration_m, seconds=Im_const.IMITATOR_START_DELAY_S
        )
        formatted_stop_time = self.get_formatted_time(stop_time)
        return formatted_stop_time


class ImitatorCmdGenerator:
    """
    Класс для получения команды запуска имитатора
    Большая часть флагов формируется из дефолтных значений.
    Для получения флагов:
    from utils.imitator_cmd_generator import ImitatorCmdGenerator
    cmd_generator = ImitatorCmdGenerator(path_to_test_data, host, test_duration_m)
    final_cmd = cmd_generator.generate_final_imitator_cmd()
    """

    def __init__(self, sandbox_path: str, stand_name: str, duration_m: float) -> None:
        self._sandbox_path = sandbox_path
        self._stand_name = stand_name
        self._duration_m = duration_m
        self._time_processor = TimeProcessor(self._duration_m)
        self._source_type: str = Im_const.SOURCE_TYPE_DEF_VALUE
        self._speed: int = Im_const.SPEED_DEF_VALUE
        self._opcua: str = os.environ.get(EnvKeyConstants.OPC_URL)
        self._ns: int = Im_const.NS_DEF_VALUE
        self.final_cmd: str = ""
        self._get_other_flags_values()
        self._generate_flags()

    def _generate_inner_test_data_path(self, sub_path: str) -> str:
        """
        Добавляет название файла / директорию к пути хранения тестовых данных
        :param sub_path: название файла / директорию
        :return: полный путь к файлу / директории
        """
        try:
            result_path = PurePosixPath(self._sandbox_path) / sub_path
            return str(result_path)

        except (ValueError, TypeError, OSError):
            logger.exception(
                f"[ERROR] Ошибка при создании пути к данным прогона. Данные: {sub_path}"
            )
            raise

    def _generate_sandbox_paths(self) -> tuple[str, str, str]:
        """
        :return: кортеж: пути к директории data и к файлам внутри директории с данными для запуска имитатора
        """
        # Формирует пути к папке с логами датчиков и файлам
        path_to_data = self._generate_inner_test_data_path(Im_const.SANDBOX_DATA)
        path_to_rules = self._generate_inner_test_data_path(Im_const.SANDBOX_RULES)
        path_to_tags = self._generate_inner_test_data_path(Im_const.SANDBOX_TAGS)

        return path_to_data, path_to_rules, path_to_tags

    def _get_target_host(self) -> str:
        """
        Получает target для флага из списка стендов
        :return: target для флага
        """
        try:
            return Im_const.HOST_MAP.get(self._stand_name, {}).get(
                Im_const.IMITATOR_KEY_NAME
            )

        except KeyError:
            logger.exception(
                f"[ERROR] Не удалось получить target для стенда: {self._stand_name}"
            )
            raise

    def _get_other_flags_values(self):
        """
        Метод получения значений флагов
        """
        try:
            self._path_to_data, self._path_to_rules, self._path_to_tags = (
                self._generate_sandbox_paths()
            )
            self._start_time = self._time_processor.formatted_start_time
            self._stop_time = self._time_processor.formatted_stop_time
            self._target = self._get_target_host()

        except (AttributeError, ValueError):
            logger.exception("[ERROR] Ошибка при получении флагов")
            raise

    def _generate_flags(self) -> None:
        """
        Метод получения флагов
        :return: строку с флагами для запуска имитатора
        """
        try:
            # Формирует флаги
            command_parts = [
                f'  --rules="{self._path_to_rules}"',
                f'--source="{self._path_to_data}"',
                f'--sourceType="{self._source_type}"',
                f'--sourceTagTypes="{self._path_to_tags}"',
                f'--startTime="{self._start_time}"',
                f'--stopTime="{self._stop_time}"',
                f"--speed={self._speed}",
                f'--opcua="{self._opcua}"',
                f"--ns={self._ns}",
            ]

            if self._target:
                command_parts.append(f'--target="{self._target}"')

            self._flags = " ".join(command_parts)

        except (ValueError, TypeError):
            logger.exception("[ERROR] Ошибка при создании итоговой версии флагов")
            raise

    def generate_final_imitator_cmd(self) -> str:
        """
        Собирает команду для запуска имитатора
        :return: финальная команда запуска имитатора
        """
        try:
            with allure.step(f"Запуск имитатора данных с флагами {self._flags}"):
                self.final_cmd = Im_const.IMITATOR_RUN_CMD + self._flags
                return self.final_cmd

        except (ValueError, TypeError):
            logger.exception("[ERROR] Ошибка при создании итоговой команды для запуска")
            raise


class UploadImitatorDataCmdGenerator:
    def __init__(
        self, username: str, host: str, path_generator: ImitatorDataPathGenerator
    ):
        # Список ожидаемых файлов в архиве
        self.expected_files: list = [Im_const.SANDBOX_TAGS, Im_const.SANDBOX_RULES]
        self._username = username
        self._host = host
        self._ssh_key_name: str = os.environ.get(EnvKeyConstants.SSH_KEY_NAME)
        self._os_is_windows: bool = os.name == Im_const.OS_NAME_WIN
        self._path_generator = path_generator
        self._remote_temp_dir_path = self._path_generator.remote_temp_dir_path
        self._tar_package_name = self._path_generator.tar_package_name
        # Путь к архиву во временной директории на удаленном сервере
        self._full_remote_tar_path = (
            self._path_generator.generate_full_remote_tar_path()
        )

    def generate_check_remote_data_cmd(self) -> str:
        """
        Создает команду проверки существования директории с данными и сопутствующих файлов
        :return: команда для выполнения в консоли
        """
        expected_dir = Im_const.SANDBOX_DATA

        check_dir_part = f"[ -d '{self._remote_temp_dir_path}/{expected_dir}' ]"
        check_parts = [check_dir_part]
        for file in self.expected_files:
            check_parts.append(f"[ -f '{self._remote_temp_dir_path}/{file}' ]")

        condition = " && ".join(check_parts)
        check_cmd = f"if {condition}; then echo {Im_const.CMD_STATUS_OK}; else echo {Im_const.CMD_STATUS_FAIL}; fi"
        return check_cmd

    def generate_create_dir_cmd(self) -> str:
        """
        Генерирует команду создания временной директории
        """
        return f"mkdir -p {self._remote_temp_dir_path}"

    def generate_delete_dir_cmd(self) -> str:
        """
        Генерирует команду удаления временной директории
        """
        return f"rm -rf {self._remote_temp_dir_path}"

    def generate_copy_tar_to_remote_cmd(self) -> str:
        """
        Генерирует команду копирования данных на удаленный сервер
        """
        if self._os_is_windows:
            return (
                f"scp -i {self._ssh_key_name} {self._tar_package_name} "
                f"{self._username}@{self._host}:{self._remote_temp_dir_path}/"
            )
        else:
            return f"scp {self._tar_package_name} {self._username}@{self._host}:{self._remote_temp_dir_path}/"

    def generate_unpack_tar_cmd(self) -> str:
        """
        Генерирует команду распаковки архива на удаленном сервере
        """
        return f"tar -xvzf {self._full_remote_tar_path} -C {self._remote_temp_dir_path}"

    def generate_check_tar_cmd(self) -> str:
        """
        Генерирует команду проверки архива на удаленном сервере
        """
        return f"tar -tzf {self._full_remote_tar_path}"
