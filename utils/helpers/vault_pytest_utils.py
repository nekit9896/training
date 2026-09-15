"""
Интеграция Vault с setup/teardown.

Настраивает ProcessEmptyValuesRejection перед setup стенда и сбрасывает после
завершения набора отбраковки
"""

from __future__ import annotations

import logging
import os
from typing import Any

from constants.architecture_constants import EnvKeyConstants, VaultConstants
from infra.vault_config_manager import VaultConfigManager

logger = logging.getLogger(__name__)

VAULT_CREDENTIALS_MISSING_MESSAGE = (
    "[SETUP] [ERROR] Vault не настроен для набора отбраковки (требуются VAULT_ADDR, ROLE_ID, SECRET_ID, STAND_NAME)"
)


def suite_requires_process_empty_values_rejection(suite_config: Any) -> bool:
    """
    Проверяет, нужен ли для набора ProcessEmptyValuesRejection=true в Vault.
    """
    return bool(getattr(suite_config, "requires_process_empty_values_rejection", False))


def has_vault_credentials() -> bool:
    """
    Проверяет наличие обязательных переменных окружения для работы с Vault.
    """
    return all(
        os.environ.get(env_key)
        for env_key in (
            VaultConstants.VAULT_ADDR,
            VaultConstants.ROLE_ID,
            VaultConstants.SECRET_ID,
            EnvKeyConstants.STAND_NAME,
        )
    )


def configure_vault_for_suite(suite_config: Any) -> tuple[bool, str | None]:
    """
    Настраивает ProcessEmptyValuesRejection в Vault перед подготовкой стенда.
    """
    requires_rejection = suite_requires_process_empty_values_rejection(suite_config)

    if not has_vault_credentials():
        if requires_rejection:
            return False, VAULT_CREDENTIALS_MISSING_MESSAGE
        logger.warning("[SETUP] [SKIP] Vault credentials не заданы - ProcessEmptyValuesRejection не изменен")
        return False, None

    enabled = requires_rejection
    VaultConfigManager().set_process_empty_values_rejection(enabled)
    logger.info(
        "[VAULT] ProcessEmptyValuesRejection установлен в %s для набора",
        "true" if enabled else "false",
    )
    return enabled, None


def reset_vault_process_empty_values_rejection() -> None:
    """
    Сбрасывает ProcessEmptyValuesRejection в false.
    """
    try:
        if not has_vault_credentials():
            return
        manager = VaultConfigManager()
        manager.ensure_disabled()
        logger.info("[VAULT] ProcessEmptyValuesRejection сброшен в false")
    except Exception as error:
        logger.warning(
            "[TEARDOWN] [ALERT] Не удалось сбросить ProcessEmptyValuesRejection в Vault: %s",
            error,
        )
