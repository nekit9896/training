import json
import logging
from typing import Any

from constants.architecture_constants import ImitatorConstants as Imitator_const
from utils.helpers.configuration_utils import extract_sensor_ids_by_address

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Читает локальную конфигурацию стенда и извлекает из нее данные для тестов.
    """

    def __init__(self, configuration_file_name: str) -> None:
        self._configuration_file_name = configuration_file_name

    def get_sensor_ids_by_address(self) -> dict[str, int]:
        """
        Возвращает словарь address: id из файла конфигурации.
        """
        configuration_json = self._read_configuration_file()
        return extract_sensor_ids_by_address(configuration_json)

    def _read_configuration_file(self) -> Any:
        """
        Чтение файла конфигурации, использует список кодировок.
        """
        error_msg = (
            f"[CONFIGURATION] [ERROR] Не удалось декодировать файл {self._configuration_file_name} "
            f"в кодировках {Imitator_const.DEFAULT_ENCODINGS}"
        )
        for encoding in Imitator_const.DEFAULT_ENCODINGS:
            try:
                with open(self._configuration_file_name, "r", encoding=encoding, errors="strict") as conf_file:
                    data = json.load(conf_file)
                    if not data:
                        error_msg = f"Пустой json (кодировка:{encoding}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    return data
            except UnicodeDecodeError:
                continue
            except Exception as error:
                logger.exception(error_msg)
                raise OSError(error_msg) from error
        logger.exception(error_msg)
        raise OSError(error_msg)
        