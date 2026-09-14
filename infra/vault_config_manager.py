import json
import logging
import os
import subprocess
from typing import Optional

from constants.architecture_constants import EnvKeyConstants, VaultConstants

logger = logging.getLogger(__name__)

_session_vault_token: Optional[str] = None


class VaultConfigManager:
    """
    Управляет параметром ProcessEmptyValuesRejection в Vault через локальный CLI.

    AppRole-авторизация и kv get/put выполняются на раннере
    """

    def __init__(self) -> None:
        self._vault_token: Optional[str] = _session_vault_token

    @staticmethod
    def resolve_environment(stand_name: str) -> str:
        """
        Определяет контур Vault (Testing/Development) по подстроке в имени стенда.
        """
        stand_lower = stand_name.lower()
        if "test" in stand_lower:
            return VaultConstants.ENVIRONMENT_TESTING
        if "dev" in stand_lower:
            return VaultConstants.ENVIRONMENT_DEVELOPMENT
        raise ValueError(
            f"Неизвестный STAND_NAME='{stand_name}', невозможно определить path для настроек Vault"
        )

    def _get_stand_name(self) -> str:
        """
        Возвращает имя стенда из обязательной переменной окружения STAND_NAME.
        """
        stand_name = os.environ.get(EnvKeyConstants.STAND_NAME)
        if not stand_name:
            raise ValueError(f"Переменная окружения {EnvKeyConstants.STAND_NAME} не задана")
        return stand_name

    def resolve_secret_path(self) -> str:
        """
        Возвращает относительный путь секрета KV без mount.
        """
        stand_name = self._get_stand_name()
        environment = self.resolve_environment(stand_name)
        return VaultConstants.SECRET_PATH_TEMPLATE.format(environment=environment, stand_name=stand_name)

    def is_vault_setup_valid(self) -> bool:
        """
        Проверяет наличие кредов и возможность построить путь секрета.
        """
        required_env_keys = (
            VaultConstants.VAULT_ADDR,
            VaultConstants.ROLE_ID,
            VaultConstants.SECRET_ID,
            EnvKeyConstants.STAND_NAME,
        )
        if not all(os.environ.get(env_key) for env_key in required_env_keys):
            return False
        try:
            self.resolve_secret_path()
        except ValueError:
            return False
        return True

    def _build_subprocess_env(self) -> dict[str, str]:
        """
        Формирует окружение subprocess для vault CLI: VAULT_SKIP_VERIFY и кэшированный токен.
        """
        env = os.environ.copy()
        env["VAULT_SKIP_VERIFY"] = VaultConstants.VAULT_SKIP_VERIFY
        if self._vault_token:
            env["VAULT_TOKEN"] = self._vault_token
        return env

    def _login_approle(self) -> None:
        """
        Авторизуется через AppRole и кэширует токен на время pytest-сессии.
        """
        global _session_vault_token

        if _session_vault_token:
            self._vault_token = _session_vault_token
            return

        role_id = os.environ[VaultConstants.ROLE_ID]
        secret_id = os.environ[VaultConstants.SECRET_ID]
        output = self._run_vault_cmd(
            [
                "write",
                "-format=json",
                "auth/approle/login",
                f"role_id={role_id}",
                f"secret_id={secret_id}",
            ],
            require_token=False,
        )
        response = json.loads(output)
        token = response.get("auth", {}).get("client_token")
        if not token:
            raise RuntimeError("[VAULT] [ERROR] AppRole login не вернул client_token")

        _session_vault_token = token
        self._vault_token = token

    def _run_vault_cmd(self, args: list[str], require_token: bool = True) -> str:
        """
        Выполняет локальную команду волту и возвращает stdout.
        """
        if require_token:
            self._login_approle()

        command = ["vault", *args]
        logger.info("[VAULT] Выполняю команду: vault %s", " ".join(args[:4]))

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=VaultConstants.VAULT_CMD_TIMEOUT_S,
                env=self._build_subprocess_env(),
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("[VAULT] [ERROR] Команда vault превысила таймаут") from error
        except subprocess.CalledProcessError as error:
            stderr = (error.stderr or error.stdout or "").strip()
            raise RuntimeError(f"[VAULT] [ERROR] Команда vault завершилась с ошибкой: {stderr}") from error

        return completed.stdout

    def get_secret_data(self) -> dict[str, str]:
        """
        Читает текущие данные секрета из Vault KV v2.
        """
        secret_path = self.resolve_secret_path()
        output = self._run_vault_cmd(
            ["kv", "get", f"-mount={VaultConstants.KV_MOUNT}", "-format=json", secret_path]
        )
        response = json.loads(output)
        secret_data = response.get("data", {}).get("data")
        if secret_data is None:
            raise RuntimeError("[VAULT] [ERROR] Не удалось извлечь data из ответа kv get")

        return {str(key): str(value) for key, value in secret_data.items()}

    def set_process_empty_values_rejection(self, enabled: bool) -> None:
        """
        Устанавливает ProcessEmptyValuesRejection, сохраняя остальные ключи секрета.
        """
        secret_path = self.resolve_secret_path()
        merged_data = self.get_secret_data()
        merged_data[VaultConstants.PROCESS_EMPTY_VALUES_REJECTION_KEY] = "true" if enabled else "false"

        put_args = ["kv", "put", f"-mount={VaultConstants.KV_MOUNT}", secret_path]
        for key, value in merged_data.items():
            put_args.append(f"{key}={value}")

        self._run_vault_cmd(put_args)
        logger.info(
            "[VAULT] %s=%s для %s",
            VaultConstants.PROCESS_EMPTY_VALUES_REJECTION_KEY,
            merged_data[VaultConstants.PROCESS_EMPTY_VALUES_REJECTION_KEY],
            secret_path,
        )

    def ensure_disabled(self) -> None:
        """Сбрасывает ProcessEmptyValuesRejection в false."""
        self.set_process_empty_values_rejection(False)
