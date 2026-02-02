import json
import logging
from typing import List

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
        configuration_file_name: str = CH_const.TN_3_JSON_FILE_NAME,
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
        try:
            self._stand_client.run_cmd(copy_cmd, timeout=CH_const.LONG_PROCESS_TIMEOUT_S, use_ssh=False)
            logging.info(f"[CLICKHOUSE] [OK] файл: {self._configuration_file_name} успешно сохранен на runner")

        except Exception:
            logging.exception(f"[CLICKHOUSE] [ERROR] При сохранении файла: {self._configuration_file_name} на runner")

    def _delete_clickhouse_keys(self, evo_id_pairs: List[tuple]) -> None:
        """
        Метод удаления данных по ключам из ClickHouse командой, используя clickhouse-client
        """
        delete_cmd = self._cmd_generator.generate_delete_clickhouse_keys_cmd(evo_id_pairs)
        result = ""
        try:
            result = self._infra_client.run_cmd(delete_cmd, need_output=True)
        except Exception:
            logging.exception(
                f"[CLICKHOUSE] [ERROR] При удалении данных в таблице командой: {delete_cmd}.\n Результат: {result}"
            )

    def _check_clickhouse_keys(self, evo_id_pairs: List[tuple]) -> None:
        """
        Метод проверки удаления данных по ключам из ClickHouse командой, используя clickhouse-client
        """

        check_cmd = self._cmd_generator.generate_check_sensor_data_click_cmd(evo_id_pairs)
        result = ""
        try:
            result = self._infra_client.run_cmd(check_cmd, need_output=True)
            if result:
                logging.exception(
                    f"[CLICKHOUSE] [ERROR] При проверке данных в таблице командой: {check_cmd}.\n Результат: {result}"
                )
        except Exception:
            logging.exception(
                f"[CLICKHOUSE] [ERROR] При проверке данных в таблице командой: {check_cmd}.\n Результат: {result}"
            )

    def delete_clickhouse_keys_with_check(self) -> None:
        """
        Метод удаления данных по ключам с проверкой из ClickHouse командами
        """

        evo_id_pairs_chunks = self._split_pairs_list()
        for chunk in evo_id_pairs_chunks:
            try:
                self._delete_clickhouse_keys(chunk)
                self._check_clickhouse_keys(chunk)
            except Exception:
                logging.exception(
                    f"[CLICKHOUSE] [ERROR] При удалении данных в таблице {CH_const.LAST_VALUE_TABLE_NAME}"
                )
        logging.info(
            f"[CLICKHOUSE] [OK] Успех! Данные всех датчиков в таблице {CH_const.LAST_VALUE_TABLE_NAME} удалены"
        )

    @staticmethod
    def _extract_evo_id_pairs(configuration_json: json) -> List[tuple]:
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
                    try:
                        evo_id = current_element[CH_const.EVO_OBJECT_ID_KEY_NAME]
                        param_id = current_element[CH_const.EVO_PARAMETER_ID_KEY_NAME]
                        if (isinstance(evo_id, int) and evo_id != 0) and (isinstance(param_id, int) and param_id != 0):
                            evo_id_pair = (evo_id, param_id)
                            if evo_id_pair not in uniq_pairs:
                                uniq_pairs.add(evo_id_pair)
                                evo_id_pairs.append(evo_id_pair)
                    except (AttributeError, KeyError, TypeError):
                        pass
                    # Добавляет все значения текущего элемента в список в обратном порядке
                    stack.extend(reversed(current_element.values()))
                elif isinstance(current_element, list):
                    stack.extend(reversed(current_element))
        except Exception:
            logging.exception(
                f"[CLICKHOUSE] [ERROR] При получении списка пар {CH_const.EVO_OBJECT_ID_KEY_NAME} и "
                f"{CH_const.EVO_PARAMETER_ID_KEY_NAME} из конфигурации "
            )

        return evo_id_pairs

    def _extract_evo_id_pairs_from_configuration(self) -> None:
        """
        Получение списка пар значений evoObjectId и evoParameterId из файла конфигурации
        """
        configuration_json = self._read_configuration_file()
        try:
            evo_id_pairs = self._extract_evo_id_pairs(configuration_json)
            if not evo_id_pairs:
                logging.exception(
                    f"[CLICKHOUSE] [ERROR] Пустой список при получении списка пар {CH_const.EVO_OBJECT_ID_KEY_NAME} и "
                    f"{CH_const.EVO_PARAMETER_ID_KEY_NAME} из конфигурации "
                )
                raise
            self._evo_id_pairs = evo_id_pairs
        except Exception:
            logging.exception(
                f"[CLICKHOUSE] [ERROR] При получении списка пар {CH_const.EVO_OBJECT_ID_KEY_NAME} и "
                f"{CH_const.EVO_PARAMETER_ID_KEY_NAME} из конфигурации "
            )

    def _read_configuration_file(self) -> json:
        """
        Чтение файла конфигурации, использует список кодировок
        """
        for encoding in CH_const.DEFAULT_ENCODINGS:
            try:
                with open(self._configuration_file_name, "r", encoding=encoding, errors="strict") as conf_file:
                    return json.load(conf_file)
            except UnicodeDecodeError:
                # следующая кодировка
                continue
            except Exception:
                logging.exception(f"[CLICKHOUSE] [ERROR] При чтении файла {self._configuration_file_name}")
        logging.exception(
            f"[CLICKHOUSE] [ERROR] Не удалось декодировать файл {self._configuration_file_name} "
            f"в кодировках {CH_const.DEFAULT_ENCODINGS}"
        )

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
