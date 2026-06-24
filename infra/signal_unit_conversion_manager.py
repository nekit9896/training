import json
import logging
import shutil
from pathlib import Path
from typing import Any

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import ClickhouseConstants as CH_const
from constants.architecture_constants import ImitatorConstants as Im_const
from constants.enums import MeasureConversionRule
from infra.cmd_generator import SignalUnitConversionCmdGenerator
from utils.helpers.signal_unit_conversion_utils import apply_measure_conversion_rule, conversion_rules_need_update

logger = logging.getLogger(__name__)


class SignalUnitConversionManager:
    """
    Управляет signal_unit_conversion_rules.json на стенде:
    - скачивает оригинал в original_conversion_rules/ перед прогоном набора
    - подкладывает изменённую версию в CONFIG_PATH (имя на сервере не меняется)
    - восстанавливает оригинал в teardown
    """

    def __init__(
        self,
        stand_client: SubprocessClient,
        measure_conversion_rule: MeasureConversionRule,
    ) -> None:
        self._stand_client = stand_client
        self._measure_conversion_rule = measure_conversion_rule
        self._cmd_generator = SignalUnitConversionCmdGenerator(stand_client.username, stand_client.host)
        self._local_file = Path(Im_const.SIGNAL_UNIT_CONVERSION_RULES_FILE_NAME)
        self._backup_file = (
            Path(Im_const.SIGNAL_UNIT_CONVERSION_RULES_BACKUP_DIR) / Im_const.SIGNAL_UNIT_CONVERSION_RULES_FILE_NAME
        )
        self._modified = False

    def setup_signal_unit_conversion_rules(self) -> None:
        """
        Скачивает файл со стенда, при необходимости меняет единицы и загружает обратно.
        """
        try:
            self._download_from_stand()
            rules_json = self._read_local_file()

            if not conversion_rules_need_update(rules_json, self._measure_conversion_rule):
                logger.info(
                    "[SETUP] [OK] signal_unit_conversion_rules.json уже настроен корректно для набора данных "
                    f"(правило {self._measure_conversion_rule.name})"
                )
                return

            self._save_backup()
            modified_rules = apply_measure_conversion_rule(rules_json, self._measure_conversion_rule)
            self._write_local_file(modified_rules)
            self._upload_to_stand(self._local_file)
            self._modified = True
            logger.info(
                "[SETUP] [OK] signal_unit_conversion_rules.json обновлён по правилу "
                f"{self._measure_conversion_rule.name}"
            )
        except Exception as error:
            error_msg = "[SETUP] [ERROR] Ошибка при подготовке signal_unit_conversion_rules.json"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def restore_signal_unit_conversion_rules(self) -> None:
        """
        Возвращает оригинальный signal_unit_conversion_rules.json на стенд
        """
        if not self._modified:
            logger.info("[TEARDOWN] [SKIP] signal_unit_conversion_rules.json не изменялся")
            return

        if not self._backup_file.exists():
            error_msg = f"[TEARDOWN] [ERROR] Оригинал signal_unit_conversion_rules.json не найден: {self._backup_file}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        try:
            self._upload_to_stand(self._backup_file)
            self._modified = False
            logger.info(
                f"[TEARDOWN] [OK] signal_unit_conversion_rules.json восстановлен на стенде из {self._backup_file}"
            )
        except Exception as error:
            error_msg = "[TEARDOWN] [ERROR] Ошибка при восстановлении signal_unit_conversion_rules.json"
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def _download_from_stand(self) -> None:
        copy_cmd = self._cmd_generator.generate_scp_signal_rules_from_stand_cmd()
        self._stand_client.run_cmd(copy_cmd, timeout=CH_const.LONG_PROCESS_TIMEOUT_S, use_ssh=False)
        if not self._local_file.exists():
            raise FileNotFoundError(f"Не удалось скачать {Im_const.SIGNAL_UNIT_CONVERSION_RULES_FILE_NAME} со стенда")

    def _save_backup(self) -> None:
        self._backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self._local_file, self._backup_file)

    def _upload_to_stand(self, local_file: Path) -> None:
        upload_cmd = self._cmd_generator.generate_scp_signal_rules_to_stand_cmd(local_file.as_posix())
        self._stand_client.run_cmd(upload_cmd, timeout=CH_const.LONG_PROCESS_TIMEOUT_S, use_ssh=False)

    def _read_local_file(self) -> dict[str, Any]:
        error_msg = (
            f"[SETUP] [ERROR] Не удалось декодировать файл {self._local_file} "
            f"в кодировках {Im_const.DEFAULT_ENCODINGS}"
        )
        for encoding in Im_const.DEFAULT_ENCODINGS:
            try:
                with open(self._local_file, "r", encoding=encoding, errors="strict") as rules_file:
                    data = json.load(rules_file)
                    if not data:
                        raise ValueError(f"Пустой json (кодировка:{encoding})")
                    return data
            except UnicodeDecodeError:
                continue
            except json.JSONDecodeError as error:
                logger.exception(error_msg)
                raise OSError(error_msg) from error
        logger.exception(error_msg)
        raise OSError(error_msg)

    @staticmethod
    def _write_local_file(rules_json: dict[str, Any]) -> None:
        with open(
            Im_const.SIGNAL_UNIT_CONVERSION_RULES_FILE_NAME,
            "w",
            encoding=Im_const.ENCODING_UTF_8,
        ) as rules_file:
            json.dump(rules_json, rules_file, ensure_ascii=False, indent=2)
