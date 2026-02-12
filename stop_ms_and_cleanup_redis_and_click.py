import logging
import os

from constants.architecture_constants import EnvKeyConstants
from constants.architecture_constants import MockConstants as M_Const
from infra.stand_setup_manager import StandSetupManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def stop_ms_and_cleanup_redis_and_click():
    """
    Останавливает контейнеры и чистит БД ClickHouse и Redis.
    Для инициализации класса StandSetupManager подставляет произвольные значения, которые не влияют на основную функцию
    """
    data_id = M_Const.MOCK_TEST_DATA_ID
    imitator_duration = M_Const.MOCK_DURATION
    test_data_name = M_Const.MOCK_TEST_DATA_NAME
    try:
        tu_id = int(os.environ.get(EnvKeyConstants.TU_ID))
    except Exception as error:
        error_msg = "[ERROR] Ошибка получения или преобразования ТУ id"
        logger.exception(error_msg)
        raise ValueError(error_msg) from error

    stand_manager = StandSetupManager(
        duration_m=imitator_duration, test_data_id=data_id, test_data_name=test_data_name, tu_id=tu_id
    )
    try:
        stand_manager.stop_all_containers()
    except Exception as error:
        error_msg = "[ERROR] Ошибка остановки контейнеров"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from error

    try:
        stand_manager.clean_redis_and_clickhouse()
    except Exception as error:
        error_msg = f"[ERROR] Ошибка чистки БД для ТУ c id = {tu_id}"
        logger.exception(error_msg)
        raise RuntimeError(error_msg) from error
    logger.info(f"[OK] Успех! Все контейнеры остановлены. Чистка Redis и Clickhouse для ТУ c id = {tu_id} выполнена.")


if __name__ == "__main__":
    stop_ms_and_cleanup_redis_and_click()
    