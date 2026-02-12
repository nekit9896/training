import logging
import os
from urllib.parse import urlparse

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import EnvKeyConstants
from constants.architecture_constants import ImitatorConstants as Im_const
from constants.enums import TU
from infra.clickhouse_manager import ClickHouseManager
from infra.cmd_generator import ImitatorCmdGenerator
from infra.docker_manager import DockerContainerManager
from infra.imitator_data_uploader import ImitatorDataUploader
from infra.imitator_manager import ImitatorManager
from infra.redis_manager import RedisCleaner

logger = logging.getLogger(__name__)


class StandSetupManager:
    """
    Подготовка стенда к запуску автотестов
    Для запуска имитатора:
    setup_manager = StandSetupManager(test_duration(minutes), test_data_id, test_data_name, tu_id)
    setup_manager.setup_stand_for_imitator_run()
    imitator_thread = threading.Thread(target=stand_manager.start_imitator, daemon=True)
    core_thread = threading.Thread(target=stand_manager.start_core)
    imitator_thread.start()
    time.sleep(20)
    core_thread.start()

    Доступ к времени старта имитатора для расчёта интервалов утечек:
    start_time = setup_manager.start_time  # datetime объект
    """

    def __init__(
        self,
        duration_m: float,  # Максимальное время работы имитатора в минутах
        test_data_id: int,  # id тест кейса из которого будут загружены данные
        test_data_name: str,  # Название архива данных имитатора для загрузки из TestOps
        tu_id: int,
        username: str = os.environ.get(EnvKeyConstants.SSH_USER_DEV),
        stand_name: str = os.environ.get(EnvKeyConstants.STAND_NAME),
    ) -> None:
        self._duration_m = duration_m
        self._test_data_id = test_data_id
        self._test_data_name = test_data_name
        self._tu_id = tu_id
        self._username = username
        self._stand_name = stand_name
        self._configuration_file_name = self._get_configuration_file_name()
        self._server_ip = self._get_server_ip()  # Получает ip сервера из словаря
        self._init_clients()
        self._cmd_generator = self._choose_cmd_generator()
        self._final_cmd = self._cmd_generator.generate_final_imitator_cmd()
        # Экземпляр имитатор менеджера нужно создавать после генерации команды, отдельно от других клиентов
        self._imitator_manager = ImitatorManager(self._stand_client, self._final_cmd)

    @property
    def start_time(self):
        """
        Возвращает время старта имитатора как datetime объект.
        Используется для расчёта интервалов утечек в тестах:
        - leak_start_time = start_time + LEAK_START_INTERVAL
        - leak_end_time = start_time + LEAK_START_INTERVAL + ALLOWED_TIME_DIFF_SECONDS
        """
        return self._cmd_generator.start_time

    def setup_stand_for_imitator_run(self) -> None:
        """
        Обертка, в которой проходит полная подготовка стенда
        """
        try:
            if not os.environ.get("RUN_WITHOUT_TESTOPS", "False").lower() == "true":
                # При запуске с TestOps загружает данные для прогона
                self._uploader.upload_with_confirm()

            self.stop_all_containers()
            self.clean_redis_and_clickhouse()
            self.start_containers_without_core()
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка подготовки стенда к запуску имитатора"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def clean_redis_and_clickhouse(self):
        """
        Чистит БД: Clickhouse и Redis
        """
        # Копирование файла конфигурации на runner
        self._clickhouse_manager.copy_configuration_file_from_stand()
        # Чистка ключей Redis
        self._redis_cleaner.delete_keys_with_check()
        # Чистка ключей ClickHouse
        self._clickhouse_manager.delete_clickhouse_keys_with_check()

    def stop_all_containers(self):
        """
        Останавливает все контейнеры и чистит БД: Clickhouse и Redis
        """
        self._docker_manager.stop_all_lds_containers()

    def start_containers_without_core(self):
        """
        Запускает все контейнеры кроме core
        """
        # Запуск lds-layer-builder
        self._docker_manager.start_lds_layer_builder_containers()
        # Запуск lds-journals
        self._docker_manager.start_lds_journals_containers()
        # Запуск lds-web-app
        self._docker_manager.start_lds_web_app_containers()
        # Запуск lds-api-gw
        self._docker_manager.start_lds_api_gw_containers()
        # Запуск lds-reports
        self._docker_manager.start_lds_reports_containers()

    def start_imitator(self) -> None:
        """
        Запускает имитатор и собирает отдельно лог имитатора в файл
        """
        try:
            self._imitator_manager.run_imitator()
            self._imitator_manager.log_imitator_stdout()
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка запуска имитатора"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def start_core(self) -> None:
        """
        Запускает core контейнеры
        """
        try:
            # Запуск CORE
            self._docker_manager.start_lds_core_containers()
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка запуска CORE"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def stop_imitator_wrapper(self) -> None:
        """
        В teardown может вызываться даже если имитатор не запущен
        """
        try:
            if not self._imitator_manager.imitator_process:
                logger.info("[TEARDOWN] [SKIP] Имитатор не был запущен")
                return
            self._imitator_manager.wait_and_stop_imitator()
            logger.info("[TEARDOWN] [OK] Имитатор остановлен")
        except Exception as error:
            error_msg = "[TEARDOWN] [ERROR] Не удалось остановить имитатор"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def server_test_data_remover(self):
        """
        Может вызваться в teardown если загрузка не была выполнена
        """
        uploader = getattr(self, "_uploader", None)
        if uploader is None:
            logger.info("[TEARDOWN] [SKIP] uploader не инициализирован, удаление данных со стенда пропущено")
            return
        try:
            uploader.delete_with_confirm()
        except Exception as error:
            error_msg = "[TEARDOWN] [ERROR] Не удалось удалить данные с сервера"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    @staticmethod
    def _parse_opc_target() -> tuple[str, int]:
        """
        Извлекает хост и порт OPC из переменной окружения OPC_URL.
        """
        opc_url = os.environ.get(EnvKeyConstants.OPC_URL)
        if not opc_url:
            raise RuntimeError(f"[SETUP] [ERROR] Переменная окружения {EnvKeyConstants.OPC_URL} не задана")

        parsed = urlparse(opc_url)
        if not parsed.hostname or not parsed.port:
            raise RuntimeError(
                f"[SETUP] [ERROR] Некорректное значение OPC_URL: '{opc_url}'. Ожидается формат вида opc.tcp://host:port"
            )

        return parsed.hostname, parsed.port

    def check_opc_server_status(self, timeout_s: int = 5) -> None:
        """
        Проверяет доступность OPC сервера с сервера стенда через /dev/tcp.
        """
        host, port = self._parse_opc_target()
        check_cmd = (
            f"if timeout {timeout_s} bash -lc 'cat < /dev/null > /dev/tcp/{host}/{port}'; "
            f"then echo {Im_const.CMD_STATUS_OK}; else echo {Im_const.CMD_STATUS_FAIL}; fi"
        )
        result = self._stand_client.run_cmd(check_cmd, need_output=True)
        if result != Im_const.CMD_STATUS_OK:
            raise RuntimeError(f"[SETUP] [ERROR] OPC сервер {host}:{port} недоступен с сервера стенда")

        logger.info(f"[SETUP] [OK] OPC сервер {host}:{port} доступен")

    def _get_server_ip(self) -> str:
        """
        Получает server ip из списка стендов
        :return: server ip
        """
        try:
            return Im_const.HOST_MAP.get(self._stand_name, {}).get(Im_const.SERVER_IP_KEY_NAME)

        except Exception as error:
            error_msg = f"[SETUP] [ERROR] Не удалось получить server ip для стенда: {self._stand_name}"
            logger.exception(error_msg)
            raise ValueError(error_msg) from error

    def _get_configuration_file_name(self) -> str:
        """
        Получает имя файла конфигурации
        """
        return TU.get_file_name_by_id(self._tu_id)

    def _choose_cmd_generator(self) -> ImitatorCmdGenerator:
        """
        Выбирает вариант генерации команды запуска имитатора, в зависимости от типа запуска
        """
        try:
            if os.environ.get("RUN_WITHOUT_TESTOPS", "False").lower() == "true":
                # Запуск без TestOps
                return ImitatorCmdGenerator(self._test_data_name, self._stand_name, self._duration_m)
            else:
                self._uploader = ImitatorDataUploader(
                    self._stand_client, self._test_data_id, self._test_data_name, self._tu_id
                )
                self._data_path = self._uploader.remote_temp_dir_path
                return ImitatorCmdGenerator(self._data_path, self._stand_name, self._duration_m)
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка при выборе варианта генерации команды запуска имитатора"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def _init_clients(self) -> None:
        """
        Создает экземпляры необходимых для запуска клиентов
        """
        try:
            self._stand_client = SubprocessClient(self._username, self._server_ip)
            self._infra_client = SubprocessClient(self._username, Im_const.REDIS_STAND_ADDRESS)
            self._clickhouse_manager = ClickHouseManager(
                self._stand_client, self._infra_client, self._configuration_file_name
            )
            self._docker_manager = DockerContainerManager(self._stand_client)
            self._redis_cleaner = RedisCleaner(self._infra_client, self._stand_name)
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка инициализации клиентов"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error
