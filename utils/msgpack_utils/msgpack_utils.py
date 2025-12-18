import logging
from typing import Any, List

import msgpack

logger = logging.getLogger(__name__)


def encode_with_varint_prefix(payload: bytes) -> bytes:
    """
    Префиксирует payload длиной в varint, затем объединяет с телом в bytes.
    Это расчет длины тела меседжа в битах с установкой заголовка для signalr-based интеграций
    """
    from clients.websocket_client import logger

    length = len(payload)
    parts = []
    while True:
        byte = length & 0x7F
        length >>= 7
        if length:
            parts.append(byte | 0x80)
        else:
            parts.append(byte)
            break
    logger.info(f"Длина байтов до тела сообщения {parts}")
    return bytes(parts) + payload


def read_varint(data: bytes) -> (int, int):
    """
    Читает varint (7 бит данных + MSB-флаг продолжения) из начала байтовой строки.
    Возвращает кортеж (значение, кол-во байт в префиксе).
    """
    value = 0
    shift = 0
    index = 0
    while True:
        if index >= len(data):
            raise ValueError("Varint extends beyond data length")
        byte = data[index]
        index += 1
        # младшие 7 бит вносят вклад
        value |= (byte & 0x7F) << shift
        # MSB=0 → последний байт префикса
        if (byte & 0x80) == 0:
            break
        shift += 7
    return value, index


def parse_message(data_bytes) -> List[Any]:
    """
    Распаковывает все объекты из тела меседжа
    """

    length, header_len = read_varint(data_bytes)
    logger.info(
        f"SignalR varint length: {length} bytes (префикс занял {header_len} байт)"
    )

    # 3) извлекаем payload
    payload = data_bytes[header_len: header_len + length]  # fmt: skip
    if len(payload) < length:
        raise ValueError("Данных меньше, чем указано в префиксе длины")
    unpacked_object = msgpack.unpackb(payload, strict_map_key=False)
    return unpacked_object
