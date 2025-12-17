import logging

from clients.subprocess_client import SubprocessClient
from constants.architecture_constants import DockerConstants as DC_const

logger = logging.getLogger(__name__)


class DockerContainerManager:
    """
    Класс для выполнения команд с докер контейнерами в консоли
    Для остановки и запуска контейнеров:
    from clients.subprocess_client import SubprocessClient
    from infra.docker_manager import DockerContainerManager
    client = SubprocessClient(your_user, your_host)
    docker_manager = DockerContainerManager(client)
    docker_manager.stop_all_lds_containers()
    docker_manager.start_lds_layer_builder_containers()
    """

    def __init__(self, client: SubprocessClient):
        self._client = client

    def _operate_with_containers(self, command: str, containers: list) -> None:
        """
        Метод, который выполняет команду для докер контейнеров в консоли
        """
        final_command = self._add_containers_to_cmd(command, containers)

        try:
            self._client.run_cmd(final_command)

        except RuntimeError:
            logger.exception(
                f"[CONTAINERS] [ERROR] Ошибка при выполнении команды для docker контейнеров. "
                f"Команда: {final_command}"
            )

    def _check_container_status(self, container: str, exp_status: str) -> bool:
        """
        Метод проверки статуса контейнера
        :param container:
        :param exp_status: ожидаемый статус
        :return: соответствует или не соответствует ожидаемому статусу
        """
        check_cmd = f"{DC_const.CHECK_STATUS_CMD} {container}"
        result = self._client.run_cmd(check_cmd, need_output=True)

        if result == exp_status:
            logger.info(f"Статус контейнера: {container} соответствует ожидаемому статусу: {result}")
        else:
            logger.error(f"[CONTAINERS] [ERROR] Статус: {result} контейнера: {container} не совпадает с ожидаемым")
        return result == exp_status

    def _check_container_group_status(self, containers: list, exp_status: str) -> None:
        """
        Метод проверки статуса группы контейнеров
        :param containers:
        :param exp_status: ожидаемый статус
        :return:
        """
        if all(self._check_container_status(container, exp_status) for container in containers):
            logger.info(
                f"[CONTAINERS] [OK] У всех контейнеров группы: {containers[0][:-6]} Статус: {exp_status} ожидаемый"
            )
        else:
            logger.error(
                f"[CONTAINERS] [ERROR] Статус группы контейнеров: {containers[0][:-6]} "
                f"не соответствует ожидаемому статусу: {exp_status}"
            )
            raise RuntimeError

    @staticmethod
    def _add_containers_to_cmd(command: str, containers: list) -> str:
        """
        :param command: докер команду для консоли
        :param containers: контейнеры для которых нужно выполнить команду
        :return: полную команду, для выполнения в консоли
        """

        if not containers:
            error_msg = "[CONTAINERS] [ERROR] Пустой список контейнеров"
            logger.error(error_msg)
            raise ValueError(error_msg)

        containers = " ".join(containers)
        final_command = f"{command} {containers}"
        return final_command

    def stop_all_lds_containers(self) -> None:
        """
        Останавливает все контейнеры lds командой в консоли
        """
        self.stop_lds_layer_builder_containers()
        self.stop_lds_core_containers()
        self.stop_lds_journals_containers()
        self.stop_lds_web_app_containers()
        self.stop_lds_api_gw_containers()
        self.stop_lds_reports_containers()

    def stop_lds_layer_builder_containers(self) -> None:
        """
        Останавливает контейнеры lds-layer-builder командой в консоли
        """
        container_group = DC_const.LB_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def stop_lds_core_containers(self) -> None:
        """
        Останавливает контейнеры lds-core командой в консоли
        """
        container_group = DC_const.CORE_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def stop_lds_journals_containers(self) -> None:
        """
        Останавливает контейнеры lds-journals командой в консоли
        """
        container_group = DC_const.JOURNAL_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def stop_lds_web_app_containers(self) -> None:
        """
        Останавливает контейнеры lds-web-app командой в консоли
        """
        container_group = DC_const.WEB_APP_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def stop_lds_api_gw_containers(self) -> None:
        """
        Останавливает контейнеры lds-api-gw командой в консоли
        """
        container_group = DC_const.API_GW_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def stop_lds_reports_containers(self) -> None:
        """
        Останавливает контейнеры lds-reports командой в консоли
        """
        container_group = DC_const.REPORTS_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.STOP_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.EXITED_STATUS)

    def start_lds_layer_builder_containers(self) -> None:
        """
        Метод, который запускает контейнеры lds-layer-builder командой в консоли
        """
        container_group = DC_const.LB_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)

    def start_lds_core_containers(self) -> None:
        """
        Запускает lds-core контейнеры командой в консоли
        """
        container_group = DC_const.CORE_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)

    def start_lds_journals_containers(self) -> None:
        """
        Запускает контейнеры lds-journals командой в консоли
        """
        container_group = DC_const.JOURNAL_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)

    def start_lds_web_app_containers(self) -> None:
        """
        Запускает контейнеры web-app командой в консоли
        """
        container_group = DC_const.WEB_APP_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)

    def start_lds_api_gw_containers(self) -> None:
        """
        Запускает контейнеры lds-api-gw командой в консоли
        """
        container_group = DC_const.API_GW_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)

    def start_lds_reports_containers(self) -> None:
        """
        Запускает контейнеры lds-reports командой в консоли
        """
        container_group = DC_const.REPORTS_CONTAINERS_GROUP

        self._operate_with_containers(DC_const.START_CMD, container_group)
        self._check_container_group_status(container_group, DC_const.RUNNING_STATUS)



        