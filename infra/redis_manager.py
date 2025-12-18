import logging

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import RedisConstants as RC_const

logger = logging.getLogger(__name__)


class RedisCleaner:
    """
    Класс для чистки определенных ключей в Redis через ssh команды в консоли
    Для удаления ключей Redis:
    from clients.subprocess_client import SubprocessClient
    from infra.redis_manager import RedisCleaner
    client = SubprocessClient(your_user, redis_host)
    redis_cleaner = RedisManager(client, stand_name)
    redis_cleaner.delete_keys_with_check()
    """

    def __init__(self, client: SubprocessClient, stand_name: str) -> None:
        self._client = client
        self._username: str = self._client.username
        self._stand_name: str = stand_name

    def delete_keys_with_check(self) -> None:
        """
        Метод удаления ключей из Redis c проверкой удаления
        """
        redis_keys = self._generate_redis_key_list()
        for key in redis_keys:
            self._delete_keys_by_keyword(key)
            self._check_deleted_keys(key)

    @staticmethod
    def _make_full_redis_key(service_name: str, stand_name: str) -> str:
        """
        Создает Redis ключ для конкретного стенда
        :param service_name: имя контейнера
        :param stand_name: имя стенда в формате "dev1"
        :return: ключ для конкретного стенда
        """
        return f"{service_name}:{stand_name}"

    @staticmethod
    def _make_redis_cmd(keyword: str, delete: bool = False) -> str:
        """
        Создает команду для redis-cli
        :param keyword: ключ, который необходимо удалить
        :param delete: добавляет команду на удаление найденного ключа
        :return:
        """
        cmd_key_name = f'"*{keyword}*"'
        cmd_parts = [RC_const.REDIS_KEY_FIND_CMD, cmd_key_name]
        if delete:
            cmd_parts.append(RC_const.REDIS_KEY_DEL_CMD)
        redis_cmd = " ".join(cmd_parts)
        return redis_cmd

    def _generate_redis_key_list(self) -> list[str]:
        """
        Создает список Redis ключей
        """
        lb_redis_key = self._make_full_redis_key(
            RC_const.LB_REDIS_KEY, self._stand_name
        )
        core_redis_key = self._make_full_redis_key(
            RC_const.CORE_REDIS_KEY, self._stand_name
        )
        return [lb_redis_key, core_redis_key]

    def _delete_keys_by_keyword(self, keyword: str) -> None:
        """
        Метод поиска и удаления ключей из Redis
        """
        try:
            delete_cmd = self._make_redis_cmd(keyword, delete=True)
            self._client.run_cmd(delete_cmd, need_output=True)
            logger.info(f"[REDIS] [OK] Успех!В Redis удалены ключи: {keyword}")

        except RuntimeError:
            logger.exception(
                f"[REDIS] [ERROR] Ошибка при удалении ключей в Redis: {keyword}"
            )

    def _check_deleted_keys(self, keyword: str) -> None:
        """
        Метод проверки удаления ключей из Redis
        """
        try:
            check_cmd = self._make_redis_cmd(keyword)
            result = self._client.run_cmd(check_cmd, need_output=True)
            if result:
                logger.error(f"[REDIS] [ERROR] Ключи Redis не удалены: {result}")
            else:
                logger.info(f"[REDIS] [OK] Успех!В Redis не найдены ключи: {keyword}")
                return
        except RuntimeError:
            logger.exception(
                f"[REDIS] [ERROR] Ошибка при проверке ключей в Redis: {keyword}"
            )
