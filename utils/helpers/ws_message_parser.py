from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID

from dacite import Config, DaciteError, from_dict
from msgpack import Timestamp

from models.acknowledge_leak_model import AcknowledgeLeakReply
from models.basic_info_model import BasicInfoReply
from models.get_input_signals_model import GetInputSignalsReply
from models.get_messages_model import GetMessagesReply
from models.get_output_signals_model import GetOutputSignalsReply
from models.main_page_info_model import SubscribeMainPageInfoReply
from models.mask_signal_model import MaskSignalReply
from models.subscribe_all_leaks_info_model import SubscribeAllLeaksInfoReply
from models.subscribe_common_scheme_model import SubscribeCommonSchemeReply
from models.subscribe_input_signals_model import InputSignal, SubscribeInputSignalsContent, SubscribeInputSignalsReply
from models.subscribe_leaks_model import SubscribeLeaksReply
from models.subscribe_output_signals_model import SubscribeOutputSignalsReply
from models.subscribe_tu_leaks_info_model import SubscribeTuLeaksInfoReply
from models.unmask_signal_model import UnmaskSignalReply

MessageType = TypeVar("MessageType")  # создает типовую переменную для парсинга сообщений


class WsMessageParser:
    """
    Парсинг websocket сообщений
    """

    def __init__(self, dacite_config: Config = None):
        self._dacite_config = dacite_config or self._get_default_config()

    @staticmethod
    def timestamp_to_datetime(value: Any) -> Optional[datetime]:
        """
        Преобразует время из формата пары msgpack. Timestamp и tz в datetime с timezone
        """
        try:
            if value is None:
                return None
            if isinstance(value, list) and len(value) == 2:
                time_timestamp, timezone_offset = value
                if isinstance(time_timestamp, Timestamp):
                    datetime_timezone = timezone(timedelta(minutes=timezone_offset))
                    return datetime.fromtimestamp(time_timestamp.seconds, datetime_timezone)
            if isinstance(value, Timestamp):
                return datetime.fromtimestamp(value.seconds, tz=timezone.utc)
        except (AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def convert_to_uuid(value: Any) -> Optional[UUID]:
        """
        Преобразует строку в UUID
        """
        try:
            if value is None:
                return None
            elif isinstance(value, UUID):
                return value
            elif isinstance(value, str):
                return UUID(value)

        except (AttributeError, TypeError, ValueError):
            return None

    def parse_output_signals_msg(self, data: list):
        """
        Парсит getOutputSignals сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=GetOutputSignalsReply, data=payload)
        return parsed_payload

    def parse_input_signals_msg(self, data: list) -> GetInputSignalsReply:
        """
        Парсит сообщение getInputSignals
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=GetInputSignalsReply, data=payload)

        return parsed_payload

    def parse_acknowledge_leak_msg(self, data: list) -> AcknowledgeLeakReply:
        """
        Парсит acknowledgeLeak сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=AcknowledgeLeakReply, data=payload)

        return parsed_payload

    def parse_basic_info_msg(self, data: list) -> BasicInfoReply:
        """
        Парсит basicInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=BasicInfoReply, data=payload)

        return parsed_payload

    def parse_journal_msg(self, data: list) -> GetMessagesReply:
        """
        Парсит сообщение журнала messagesInfo
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=GetMessagesReply, data=payload)

        return parsed_payload

    def parse_main_page_msg(self, data: list) -> SubscribeMainPageInfoReply:
        """
        Парсит сообщение mainPageInfo
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeMainPageInfoReply, data=payload)

        return parsed_payload

    def parse_mask_signal_msg(self, data: list) -> MaskSignalReply:
        """
        Парсит сообщение MaskSignal
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=MaskSignalReply, data=payload)

        return parsed_payload

    def parse_unmask_signal_msg(self, data: list) -> UnmaskSignalReply:
        """
        Парсит сообщение UnmaskSignal
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=UnmaskSignalReply, data=payload)

        return parsed_payload

    def parse_all_leaks_info_msg(self, data: list) -> SubscribeAllLeaksInfoReply:
        """
        Парсит allLeaksInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeAllLeaksInfoReply, data=payload)

        return parsed_payload

    def parse_input_signals_info_msg(self, data: list) -> SubscribeInputSignalsReply:
        """
        Парсит сообщение InputSignalsInfo
        """
        payload = self._find_reply_status_in_ws_msg(data)
        reply_content = payload.get('replyContent')
        input_signals_list = reply_content.get('inputSignals')
        parsed_payload = SubscribeInputSignalsReply(
            replyStatus=payload.get('replyStatus'),
            replyErrors=payload.get('replyErrors'),
            replyContent=SubscribeInputSignalsContent(
                tuId=reply_content.get('tuId'),
                # Получает второй элемент из списка и парсит его
                inputSignals=[
                    self._parse_message(InputSignal, item[1])
                    for item in input_signals_list
                    if isinstance(item, list) and isinstance(item[1], dict)
                ],
            ),
        )
        return parsed_payload

    def parse_leaks_info_msg(self, data: list) -> SubscribeLeaksReply:
        """
        Парсит allLeaksInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeLeaksReply, data=payload)

        return parsed_payload

    def parse_output_signals_info_msg(self, data: list):
        """
        Парсит OutputSignalsInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeOutputSignalsReply, data=payload)
        return parsed_payload

    def parse_tu_leaks_info_msg(self, data: list) -> SubscribeTuLeaksInfoReply:
        """
        Парсит tuLeaksInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeTuLeaksInfoReply, data=payload)

        return parsed_payload

    def parse_common_scheme_info_msg(self, data: list) -> SubscribeCommonSchemeReply:
        """
        Парсит tuLeaksInfo сообщение
        """
        payload = self._find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=SubscribeCommonSchemeReply, data=payload)

        return parsed_payload

    def _parse_message(self, data_class: Type[MessageType], data: dict, config: Optional[Config] = None) -> MessageType:
        """
        Универсальная функция парсинга сообщений
        """
        try:
            return from_dict(
                data_class=data_class, data=data, config=config or self._dacite_config  # type: ignore[arg-type]
            )
        except DaciteError:
            raise

    @staticmethod
    def _find_reply_status_in_ws_msg(data: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Ищет объект с replyStatus в ws сообщении
        """
        for item in reversed(data):
            # 1) Если сам элемент — словарь с replyStatus
            if isinstance(item, dict):
                if 'replyStatus' in item:
                    return item
            # 2) Если элемент — список / кортеж — проверяем все элементы в нём
            if isinstance(item, (list, tuple)):
                for elem in item:
                    if isinstance(elem, dict) and 'replyStatus' in elem:
                        return elem

    def _get_default_config(self) -> Config:
        """
        Получает конфиг с правилами обработки полей
        """
        return Config(type_hooks={UUID: self.convert_to_uuid, datetime: self.timestamp_to_datetime})


# Создает экземпляр класса для удобства импорта
ws_message_parser = WsMessageParser()
