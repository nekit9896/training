"""
OPC UA клиент для чтения выходных сигналов СОУ (обратный обмен СДКУ).

Подключается к OPC UA серверу по opc.tcp и читает значения тегов
(Value + StatusCode + SourceTimestamp). Используется как в setup-части
(проверка доступности OPC), так и в сценариях имитации выходных сигналов.
"""

import asyncio
import logging
from typing import Any, Optional

from asyncua import Client, ua

from constants.architecture_constants import OpcUaConstants as OpcConst

logger = logging.getLogger(__name__)


def build_opc_node_id(
    ost_name: str,
    stand_name: str,
    address: str,
    suffix: str,
    namespace_index: int = OpcConst.NAMESPACE_INDEX,
) -> str:
    """
    Собирает NodeId вида ns=2;s=CHTNTEST4:CHTN_linearParts_9.isLeakDetected.

    ost_name: имя ОСТ (например "CHTN").
    stand_name: имя стенда (например "TEST4").
    address: тег участка из конфигурации трубы (например "CHTN_linearParts_9").
    suffix: суффикс сигнала (например "isLeakDetected").
    namespace_index: номер пространства имён (по умолчанию NS=2).
    """
    return f"ns={namespace_index};s={ost_name}{stand_name.upper()}:{address}.{suffix}"


def read_data_value_sync(
    opc_url: str,
    node_id: str,
    timeout: float = OpcConst.CONNECT_TIMEOUT_S,
) -> ua.DataValue:
    """
    Синхронное подключение и чтение DataValue тега. Используется в setup-части
    (синхронный контекст pytest), чтобы понять, что OPC UA сервер жив и отдаёт данные.
    """

    async def _read() -> ua.DataValue:
        client = Client(url=opc_url, timeout=timeout)
        try:
            await client.connect()
            logger.info("[OPC] Подключено к %s", opc_url)
            return await client.get_node(node_id).read_data_value(raise_on_bad_status=False)
        finally:
            await client.disconnect()

    return asyncio.run(_read())


class OpcUaClient:
    """Асинхронный OPC UA клиент с переподключением."""

    def __init__(self, url: str, timeout: float = OpcConst.OPERATION_TIMEOUT_S) -> None:
        self._url = url
        self._timeout = timeout
        self._client: Optional[Client] = None

    async def connect(self, attempts: int = OpcConst.RECONNECT_ATTEMPTS) -> None:
        """Подключается к OPC UA серверу с ограниченным числом попыток."""
        last_error: Optional[Exception] = None
        for attempt in range(1, attempts + 1):
            try:
                self._client = Client(url=self._url, timeout=self._timeout)
                await self._client.connect()
                logger.info("[OPC] [OK] Подключено к %s", self._url)
                return
            except Exception as error:
                last_error = error
                logger.warning("[OPC] [WARNING] Подключение не удалось (попытка %s/%s): %s", attempt, attempts, error)
                if attempt < attempts:
                    await asyncio.sleep(OpcConst.RECONNECT_INTERVAL_S)
        raise ConnectionError(f"Не удалось подключиться к OPC UA серверу {self._url}: {last_error}") from last_error

    async def disconnect(self) -> None:
        if self._client is not None:
            await self._client.disconnect()
            self._client = None

    async def read_data_value(self, node_id: str, raise_on_bad_status: bool = False) -> ua.DataValue:
        """
        Читает DataValue (Value + StatusCode + SourceTimestamp) тега.
        По умолчанию не бросает исключение при плохом статусе (например BadNoCommunication),
        а возвращает DataValue со статусом — статус проверяется в сценарии.
        """
        if self._client is None:
            raise RuntimeError("OPC UA клиент не подключён")
        return await self._client.get_node(node_id).read_data_value(raise_on_bad_status=raise_on_bad_status)

    async def read_value(self, node_id: str) -> Any:
        """Читает только значение тега."""
        if self._client is None:
            raise RuntimeError("OPC UA клиент не подключён")
        return await self._client.get_node(node_id).read_value()
