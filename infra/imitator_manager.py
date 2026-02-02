import logging
import subprocess
from typing import Optional

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import ImitatorConstants as Im_const

logger = logging.getLogger(__name__)


class ImitatorManager:
    """
    Класс управления имитатором
    Для запуска имитатора:
    from clients.subprocess_client import SubprocessClient
    from infra.imitator_manager import ImitatorManager
    client = SubprocessClient(your_user, your_host)
    imitator_manager = ImitatorManager(client, your_command)
    imitator_manager.run_imitator()
    imitator_manager.log_imitator_stdout()
    imitator_manager.wait_and_stop_imitator()
    Для получения процесса с запущеным имитатором:
    imitator_process = imitator_manager.imitator_process
    Для остановки имитатора:
    imitator_manager.stop_imitator()
    Для получения процесса с запущеным имитатором
    """

    def __init__(self, client: SubprocessClient, imitator_run_cmd: str) -> None:
        self._client = client
        self._imitator_run_cmd = imitator_run_cmd
        self._logger: logging.getLogger() = logging.getLogger(self.__class__.__name__)
        self._setup_logger()
        self._imitator_process: Optional[subprocess.Popen] = None

    @property
    def imitator_process(self) -> Optional[subprocess.Popen]:
        return self._imitator_process

    def _setup_logger(self) -> None:
        """
        Настраивает отдельный логер для имитатора
        """
        # Запись логов имитатора в отдельный файл
        # Кодировка установлена под WIN, для gitlab нужно установить utf-8
        file_handler = logging.FileHandler(Im_const.IMITATOR_LOG_FILE_NAME, encoding=Im_const.WIN_ENCODING_CP1251)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter()
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)
        # Отключает дублирование логов в консоль
        self._logger.propagate = False

    def run_imitator(self) -> None:
        """
        Запускает имитатор на удаленном сервере
        """
        if self._imitator_process is not None:
            logger.error("[IMITATOR] [ERROR] Имитатор уже запущен")
            raise
        process = self._client.exec_popen(self._imitator_run_cmd)
        if process.poll() is None:
            self._imitator_process = process
            logger.info("[IMITATOR] [OK] Имитатор запущен успешно")
        else:
            logger.error("[IMITATOR] [ERROR] Ошибка запуска имитатора")
            raise

    def log_imitator_stdout(self) -> None:
        """
        Записывает логи имитатора в файл с помощью отдельного логера
        """

        try:
            if self._imitator_process.poll() is None:
                for line in self._imitator_process.stdout:
                    self._logger.info(line)
            else:
                logger.error("[IMITATOR] [ERROR] Ошибка записи логов имитатора: Имитатор не запущен")
                raise
        except (OSError, ValueError):
            logging.exception("[IMITATOR] [ERROR] Ошибка при получении логов имитатора!")

    def _is_imitator_running(self) -> bool:
        """
        Проверяет наличие PID имитатора на стенде
        """
        result = self._client.run_cmd(Im_const.IMITATOR_CHECK_CMD, check=False, need_output=True)
        if result:
            logger.warning(f"[IMITATOR] [WARNING] Имитатор не остановлен! PID: {result}")
        else:
            logger.info("[IMITATOR] [OK] Имитатор остановлен успешно")
        return bool(result and result.strip())

    def stop_imitator(self) -> None:
        """
        Останавливает имитатор
        """
        try:
            self._client.terminate_process(self._imitator_process, timeout=Im_const.POPEN_WAIT_TIMOUT_S)
            if self._is_imitator_running():
                # Останавливает имитатор на стенде
                self._client.run_cmd(Im_const.IMITATOR_KILL_CMD)
                logger.info("[IMITATOR] [OK] Имитатор остановлен успешно")
            self._imitator_process = None
        except RuntimeError:
            logger.exception("[IMITATOR] [ERROR] Ошибка остановки имитатора")
            raise

    def wait_and_stop_imitator(self) -> None:
        """
        Ожидает окончания работы имитатора и завершает его работу
        """
        try:
            self._imitator_process.wait()

        except KeyboardInterrupt:
            # На случай остановки принудительно, через Ctrl+C например
            logging.exception("[IMITATOR] [ERROR] Принудительная остановка имитатора!")
            raise
        finally:
            self.stop_imitator()
            