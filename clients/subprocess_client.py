import logging
import os
import subprocess
from typing import Optional

from constants.architecture_constants import EnvKeyConstants
from constants.architecture_constants import ImitatorConstants as Im_const

logger = logging.getLogger(__name__)


class SubprocessClient:
    """
    Клиент для выполнения команд в консоли, с автоматической оберткой в ssh команды
    Для выполнения команды:
    from utils.ssh_manager import SubprocessClient
    client = SubprocessClient(your_user, your_host)
    client.run_cmd(your_command)

    """

    def __init__(self, remote_username: str, remote_host: str) -> None:
        self._username = remote_username
        self._host = remote_host
        self._ssh_key_name = os.environ.get(EnvKeyConstants.SSH_KEY_NAME)

    @property
    def username(self):
        return self._username

    @property
    def host(self):
        return self._host

    def _wrap_ssh_cmd(self, cmd: str, use_ssh: bool = True) -> str:
        """
        Обертка в ssh команду
        :param cmd: команда
        :param use_ssh: нужна ли обертка
        :return: команда
        """

        if use_ssh:
            if os.name == Im_const.OS_NAME_WIN:
                # Для запуска под WIN требуется добавить в команду путь к ключу
                return f"ssh -i {self._ssh_key_name} {self._username}@{self._host} \"{cmd}\""
            else:
                return f'ssh {self._username}@{self._host} "{cmd}"'
        return cmd

    def _exec_run(
        self,
        cmd: str,
        check: bool = True,
        timeout: int = None,
        use_ssh: bool = True,
    ) -> subprocess.CompletedProcess:
        """
        Выполняет команду в консоли и возвращает результат
        :param cmd: команда для выполнения в консоли
        :return: результат выполнения команды
        """
        final_cmd = self._wrap_ssh_cmd(cmd, use_ssh)
        logging.info(f"[RUN] Выполняю команду: {final_cmd}")
        try:
            return subprocess.run(
                final_cmd,
                # Запуск команды через оболочку
                shell=True,
                # Аргумент check выбросит исключение если придет ответ не "0"
                check=check,
                capture_output=True,
                encoding=self._get_encoding(),
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.exception(f"[RUN] [ERROR] Команда превысила таймаут: {final_cmd}")
            raise
        except subprocess.CalledProcessError as err:
            output_error = err.stderr.strip()
            logging.error(f"[RUN] [ERROR] Ошибка выполнения команды: {output_error}. Код ошибки: {err.returncode}")
            raise

    def exec_popen(self, cmd, use_ssh: bool = True) -> Optional[subprocess.Popen]:
        """
        Выполняет команду в консоли.
        Используется для запуска долгих процессов
        :param cmd: команда для выполнения в консоли
        :param use_ssh: нужна ли ssh обертка
        :return: процесс выполнения команды
        """
        final_cmd = self._wrap_ssh_cmd(cmd, use_ssh)
        logging.info(f"[POPEN] выполняю команду: {final_cmd}")
        try:
            return subprocess.Popen(
                final_cmd,
                # Запуск команды через оболочку
                shell=True,
                stdout=subprocess.PIPE,
                # Объединяет вывод и вывод ошибок в один поток
                stderr=subprocess.STDOUT,
                text=True,
                # Буферизация строк
                bufsize=1,
                # При адаптации для запуска в gitlab нужно убрать кодировку
                encoding=Im_const.ENCODING_UTF_8,
                # Замена знаков, которые были декодированы с ошибкой
                errors="replace",
            )

        except (FileNotFoundError, OSError):
            logging.exception(f"[POPEN] [ERROR] Ошибка выполнения команды {cmd}")

    def run_cmd(
        self, cmd: str, check: bool = True, timeout: int = None, need_output: bool = False, use_ssh: bool = True
    ) -> Optional[str]:
        """
        Выполняет команду через subprocess.run с логированием или возвратом результата выполнения команды
        :param cmd: команда
        :param check: проверяет что код ответа 0
        :param timeout: таймаут на выполнение(опционально)
        :param need_output: нужно ли вернуть вывод после выполнения команды
        :param use_ssh: нужна ли ssh обертка
        :return: Вывод
        """
        result = self._exec_run(cmd, check, timeout, use_ssh)
        logging.info(f"[RUN] [OK] Команда выполнена успешно: {cmd}")
        if need_output:
            output = result.stdout.strip()
            return output
        if result.stdout:
            logging.debug(f"[RUN] [STDOUT]\n{result.stdout.strip()}")
        if result.stderr:
            logging.warning(f"[RUN] [STDERR]\n{result.stderr.strip()}")
        return None

    @staticmethod
    def terminate_process(process: subprocess.Popen, timeout: float) -> None:
        """
        Завершает процесс.
        :param process: Процесс, который требуется остановить
        :param timeout: Время на остановку процесс
        """
        if process is None:
            logger.warning("[POPEN] terminate_process вызван при пустом process")
            return

        try:
            if process.poll is None:
                process.terminate()
                process.wait(timeout=timeout)
                logger.info("[POPEN] [OK] Процесс завершился успешно")
        except subprocess.TimeoutExpired:
            logger.exception("[POPEN] [ERROR] Процесс не завершился, принудительное уничтожение процесса")
            try:
                process.kill()
                process.wait()
            except RuntimeError:
                logger.exception("[POPEN] [ERROR] Ошибка завершения процесса")
                raise
        except Exception:
            logger.exception("[POPEN] [ERROR] Неожиданная ошибка при завершении процесса")
            raise

    @staticmethod
    def _get_encoding() -> Optional[str]:
        """
        Временная функция. Будет удалена во время адаптации скрипта к gitlab runner
        Получает кодировку консоли или применяет дефолтную для windows
        """

        return os.device_encoding(1) or Im_const.WIN_ENCODING_CP866
