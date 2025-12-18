from typing import Any, List

from constants.architecture_constants import \
    WebSocketClientConstants as WS_Const


def is_desired_type(msg: List[Any], message_type: str) -> bool:
    """
    Проверяем, что msg — список нужной длины
    и msg[EVENT_TYPE_INDEX] совпадает с искомым type.
    """
    return (
        len(msg) > WS_Const.EVENT_TYPE_INDEX
        and msg[WS_Const.EVENT_TYPE_INDEX] == message_type
    )


def is_desired_invocation_id(msg: List[Any], invocation_id: str) -> bool:
    """
    Проверяем, что msg — список нужной длины
    и msg[INVOCATION_ID_INDEX]] совпадает с искомым invocation_id.
    """
    return (
        len(msg) > WS_Const.INVOCATION_ID_INDEX
        and msg[WS_Const.INVOCATION_ID_INDEX] == invocation_id
    )
