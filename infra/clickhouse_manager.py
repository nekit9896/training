import json
import logging
from pathlib import Path
from typing import Any, List, Optional

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import ClickhouseConstants as CH_const
from infra.cmd_generator import ClickHouseCmdGenerator

logger = logging.getLogger(__name__)


class ClickHouseManager:
    """
    Класс работы с clickhouse
    Пример использования:
    click_manager = ClickHouseManager(stand_client, infra_client)
    click_manager.copy_configuration_file_from_stand() - для загрузки конфигурации со стенда
    click_manager.delete_clickhouse_keys_with_check() - для удаления данных по определенным ключам
    """

    def __init__(
        self,
        stand_client: SubprocessClient,
        infra_client: SubprocessClient,
        configuration_file_name: str,
    ) -> None:
        self._stand_client = stand_client
        self._infra_client = infra_client
        self._configuration_file_name = configuration_file_name
        self._username = stand_client.username
        self._stand_host = stand_client.host
        self._infra_host = infra_client.host
        self._evo_id_pairs: List[tuple] = []
        self._cmd_generator = ClickHouseCmdGenerator(self._username, self._stand_host, configuration_file_name)

    def copy_configuration_file_from_stand(self) -> None:
        """
        Копирует файл конфигурации со стенда в корень проекта
        """
        copy_cmd = self._cmd_generator.generate_scp_config_file_cmd()
        configuration_file_path = Path(self._configuration_file_name)
        if not configuration_file_path.exists():
            try:
                self._stand_client.run_cmd(copy_cmd, timeout=CH_const.LONG_PROCESS_TIMEOUT_S, use_ssh=False)
                logger.info(f"[CLICKHOUSE] [OK] файл: {self._configuration_file_name} успешно сохранен на runner")

            except Exception as error:
                error_msg = f"[CLICKHOUSE] [ERROR] При сохранении файла: {self._configuration_file_name} на runner"
                logger.exception(error_msg)
                raise RuntimeError(error_msg) from error

    def delete_clickhouse_keys_with_check(self) -> None:
        """
        Метод удаления данных по ключам с проверкой из ClickHouse командами
        """

        evo_id_pairs_chunks = self._split_pairs_list()
        for chunk in evo_id_pairs_chunks:
            self._delete_clickhouse_keys(chunk)
            self._check_clickhouse_keys(chunk)
        logger.info(f"[CLICKHOUSE] [OK] Успех! Данные всех датчиков в таблице {CH_const.LAST_VALUE_TABLE_NAME} удалены")

    def _delete_clickhouse_keys(self, evo_id_pairs: List[tuple]) -> None:
        """
        Метод удаления данных по ключам из ClickHouse командой, используя clickhouse-client
        """
        delete_cmd = self._cmd_generator.generate_delete_clickhouse_keys_cmd(evo_id_pairs)
        try:
            self._infra_client.run_cmd(delete_cmd)
        except Exception as error:
            error_msg = f"[CLICKHOUSE] [ERROR] При удалении данных в таблице командой: {delete_cmd}."
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def _check_clickhouse_keys(self, evo_id_pairs: List[tuple]) -> None:
        """
        Метод проверки удаления данных по ключам из ClickHouse командой, используя clickhouse-client
        """

        check_cmd = self._cmd_generator.generate_check_sensor_data_click_cmd(evo_id_pairs)
        try:
            result = self._infra_client.run_cmd(check_cmd, need_output=True)
            try:
                result_int = int(result)
            except (TypeError, ValueError) as error:
                error_msg = (
                    f"[CLICKHOUSE] [ERROR] Результат: {result} проверки количества записей после удаления,"
                    " не является числом или равен None"
                )
                logger.exception(error_msg)
                raise TypeError(error_msg) from error
            if result_int != 0:
                error_msg = f"[CLICKHOUSE] [ERROR] Осталось: {result} записей после удаления"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
        except Exception as error:
            error_msg = f"[CLICKHOUSE] [ERROR] При проверке данных в таблице командой: {check_cmd}."
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error

    def _extract_evo_id_pairs_from_configuration(self) -> None:
        """
        Получение списка пар значений evoObjectId и evoParameterId из файла конфигурации
        """
        configuration_json = self._read_configuration_file()
        self._evo_id_pairs = self._extract_evo_id_pairs(configuration_json)

    def _extract_evo_id_pairs(self, configuration_json: Any) -> List[tuple]:
        """
        Получение списка уникальных пар значений evoObjectId и evoParameterId
        """
        uniq_pairs = set()
        evo_id_pairs = []
        stack = [configuration_json]
        try:
            while stack:
                current_element = stack.pop()  # Забирает последний элемент списка
                if isinstance(current_element, dict):
                    evo_id_pair = self._extract_evo_id_pair(current_element)
                    if evo_id_pair is not None and evo_id_pair not in uniq_pairs:
                        uniq_pairs.add(evo_id_pair)
                        evo_id_pairs.append(evo_id_pair)
                    # Добавляет все значения текущего элемента в список в обратном порядке
                    stack.extend(reversed(current_element.values()))
                elif isinstance(current_element, list):
                    stack.extend(reversed(current_element))
        except Exception as error:
            error_msg = (
                f"[CLICKHOUSE] [ERROR] При получении списка пар {CH_const.EVO_OBJECT_ID_KEY_NAME} и "
                f"{CH_const.EVO_PARAMETER_ID_KEY_NAME} из конфигурации "
            )
            logger.exception(error_msg)
            raise RuntimeError(error_msg) from error
        if not evo_id_pairs:
            error_msg = (
                f"[CLICKHOUSE] [ERROR] Пустой список при получении списка пар {CH_const.EVO_OBJECT_ID_KEY_NAME} и "
                f"{CH_const.EVO_PARAMETER_ID_KEY_NAME} из конфигурации "
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        return evo_id_pairs

    @staticmethod
    def _extract_evo_id_pair(element: dict) -> Optional[tuple]:
        """
        Ищет пару значений evoObjectId и evoParameterId в словаре
        """
        try:
            evo_id = element[CH_const.EVO_OBJECT_ID_KEY_NAME]
            param_id = element[CH_const.EVO_PARAMETER_ID_KEY_NAME]
            if (isinstance(evo_id, int) and evo_id != 0) and (isinstance(param_id, int) and param_id != 0):
                return evo_id, param_id
        except (AttributeError, KeyError, TypeError):
            pass

    def _read_configuration_file(self) -> Any:
        """
        Чтение файла конфигурации, использует список кодировок
        """
        error_msg = (
            f"[CLICKHOUSE] [ERROR] Не удалось декодировать файл {self._configuration_file_name} "
            f"в кодировках {CH_const.DEFAULT_ENCODINGS}"
        )
        for encoding in CH_const.DEFAULT_ENCODINGS:
            try:
                with open(self._configuration_file_name, "r", encoding=encoding, errors="strict") as conf_file:
                    data = json.load(conf_file)
                    if not data:
                        error_msg = f"Пустой json (кодировка:{encoding}"
                        logger.error(error_msg)
                        raise ValueError(error_msg)
                    return data
            except UnicodeDecodeError:
                # следующая кодировка
                continue
            except Exception as error:
                logger.exception(error_msg)
                raise OSError(error_msg) from error
        logger.exception(error_msg)
        raise OSError(error_msg)

    def _split_pairs_list(self) -> List[list]:
        """
        Делит список пар на части
        """
        if not self._evo_id_pairs:
            self._extract_evo_id_pairs_from_configuration()
        return [
            # fmt: off
            self._evo_id_pairs[i:i + CH_const.EVO_ID_PAIRS_CHUNK_SIZE]
            # fmt: on
            for i in range(0, len(self._evo_id_pairs), CH_const.EVO_ID_PAIRS_CHUNK_SIZE)
        ]
