from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID
from zoneinfo import ZoneInfo

from allure import attach, attachment_type
from dacite import Config, DaciteError, from_dict
from msgpack import Timestamp
from pytest import fail

import models.subscribe_scheme_signals_state_model as signals_state_model
from constants.architecture_constants import WebSocketClientConstants
from constants.enums import ExportedDataType, ExportStatus, ReplyStatus
from models.acknowledge_leak_model import AcknowledgeLeakReply
from models.basic_info_model import BasicInfoReply
from models.export_reports_model import ReportDataExportedNotification
from models.get_basic_info_admin_model import GetBasicInfoAdminReply
from models.get_exported_files_list_model import GetExportedDataListReply
from models.get_tus_information_model import GetTusInformationReply
from models.get_input_signals_model import GetInputSignalsReply
from models.get_messages_model import GetMessagesReply
from models.get_output_signals_model import GetOutputSignalsReply
from models.imitate_signal_model import ImitateSignalReply
from models.launch_lds_model import LaunchLdsReply
from models.launch_pig_model import LaunchPigReply
from models.mask_lds_command_model import MaskLdsReply
from models.mask_signal_model import MaskSignalReply
from models.stop_lds_model import StopLdsReply
from models.subscribe_all_leaks_info_model import SubscribeAllLeaksInfoReply
from models.subscribe_balance_algorithm_results_model import SubscribeBalanceAlgorithmResultsReply
from models.subscribe_common_scheme_model import SubscribeCommonSchemeReply
from models.subscribe_input_signals_model import InputSignal, SubscribeInputSignalsContent, SubscribeInputSignalsReply
from models.subscribe_leaks_model import SubscribeLeaksReply
from models.subscribe_main_page_info_model import SubscribeMainPageInfoReply
from models.subscribe_main_page_signals_info_model import SubscribeMainPageSignalsInfoReply
from models.subscribe_output_signals_model import SubscribeOutputSignalsReply
from models.subscribe_tu_leaks_info_model import SubscribeTuLeaksInfoReply
from models.unimitate_signal_model import UnimitateSignalReply
from models.unmask_lds_command_model import UnmaskLdsReply
from models.unmask_signal_model import UnmaskSignalReply
from models.upload_exported_file_model import DownloadExportedDataReply

logger = logging.getLogger(__name__)

MessageType = TypeVar("MessageType")  # создает типовую переменную для парсинга сообщений
ContentType = TypeVar("ContentType")

_SIGNAL_DATA_POSITION = 1
_MIN_SIGNAL_TUPLE_LENGTH = 2


class WsMessageParser:
    """
    Парсинг websocket сообщений
    """

    def __init__(self, dacite_config: Config = None):
        self._dacite_config = dacite_config or self._get_default_config()
        self.suppress_recv_logging: bool = False

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
        except (AttributeError, TypeError, ValueError) as error:
            fail(f"Ошибка конвертации времени: {error}")

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

        except (AttributeError, TypeError, ValueError) as error:
            fail(f"Ошибка конвертации UUID: {error}")

    def parse_acknowledge_leak_msg(self, data: list) -> AcknowledgeLeakReply:
        """
        Парсит acknowledgeLeak сообщение
        """
        return self._find_and_parse_message(data_class=AcknowledgeLeakReply, data=data)

    def parse_all_leaks_info_msg(self, data: list) -> SubscribeAllLeaksInfoReply:
        """
        Парсит allLeaksInfo сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeAllLeaksInfoReply, data=data)

    def parse_basic_info_msg(self, data: list) -> BasicInfoReply:
        """
        Парсит basicInfo сообщение
        """
        return self._find_and_parse_message(data_class=BasicInfoReply, data=data)

    def parse_common_scheme_info_msg(self, data: list) -> SubscribeCommonSchemeReply:
        """
        Парсит tuLeaksInfo сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeCommonSchemeReply, data=data)

    def parse_imitate_signal_msg(self, data: list) -> ImitateSignalReply:
        """
        Парсит сообщение ImitateSignal
        """
        return self._find_and_parse_message(data_class=ImitateSignalReply, data=data)

    def parse_input_signals_info_msg(self, data: list) -> SubscribeInputSignalsReply:
        """
        Парсит сообщение InputSignalsInfo
        """
        payload = self.find_reply_status_in_ws_msg(data)
        reply_content = payload.get('replyContent')
        input_signals_list = reply_content.get('inputSignals')
        parsed_payload = SubscribeInputSignalsReply(
            replyStatus=payload.get('replyStatus'),
            replyErrors=payload.get('replyErrors'),
            replyContent=SubscribeInputSignalsContent(
                tuId=reply_content.get('tuId'),
                inputSignals=[
                    self._parse_message(InputSignal, item[_SIGNAL_DATA_POSITION])
                    for item in input_signals_list
                    if self._is_valid_signal_tuple(item)
                ],
            ),
        )
        if parsed_payload.replyErrors:
            fail(f"Ошибка в сообщении типа InputSignalsInfo: {parsed_payload.replyErrors}")
        return parsed_payload

    def parse_input_signals_msg(self, data: list) -> GetInputSignalsReply:
        """
        Парсит сообщение getInputSignals
        """
        return self._find_and_parse_message(data_class=GetInputSignalsReply, data=data)

    def parse_journal_msg(self, data: list) -> GetMessagesReply:
        """
        Парсит сообщение журнала messagesInfo
        """
        return self._find_and_parse_message(data_class=GetMessagesReply, data=data)

    def parse_leaks_content_msg(self, data: list) -> SubscribeLeaksReply:
        """
        Парсит LeaksContent сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeLeaksReply, data=data)

    def parse_main_page_msg(self, data: list) -> SubscribeMainPageInfoReply:
        """
        Парсит сообщение mainPageInfo
        """
        return self._find_and_parse_message(data_class=SubscribeMainPageInfoReply, data=data)

    def parse_main_page_signals_msg(self, data: list) -> SubscribeMainPageSignalsInfoReply:
        """
        Парсит сообщение mainPageSignalsInfo
        """
        return self._find_and_parse_message(data_class=SubscribeMainPageSignalsInfoReply, data=data)

    def parse_launch_pig_msg(self, data: list) -> LaunchPigReply:
        """
        Парсит сообщение LaunchPig
        """
        return self._find_and_parse_message(data_class=LaunchPigReply, data=data)

    def parse_mask_signal_msg(self, data: list) -> MaskSignalReply:
        """
        Парсит сообщение MaskSignal
        """
        return self._find_and_parse_message(data_class=MaskSignalReply, data=data)

    def parse_mask_lds_message(self, data: list) -> MaskLdsReply:
        """
        Парсит сообщение maskLDSRequest
        """
        return self._find_and_parse_message(data_class=MaskLdsReply, data=data)

    def parse_unmask_lds_message(self, data: list) -> UnmaskLdsReply:
        """
        Парсит сообщение UnmaskLDSRequest
        """
        return self._find_and_parse_message(data_class=UnmaskLdsReply, data=data)

    def parse_output_signals_info_msg(self, data: list) -> SubscribeOutputSignalsReply:
        """
        Парсит OutputSignalsInfo сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeOutputSignalsReply, data=data)

    def parse_output_signals_msg(self, data: list):
        """
        Парсит getOutputSignals сообщение
        """
        return self._find_and_parse_message(data_class=GetOutputSignalsReply, data=data)

    def parse_balance_algorithm_msg(self, data: list) -> SubscribeBalanceAlgorithmResultsReply:
        """
        Парсит BalanceAlgorithmResults сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeBalanceAlgorithmResultsReply, data=data)

    def parse_tu_leaks_info_msg(self, data: list) -> SubscribeTuLeaksInfoReply:
        """
        Парсит tuLeaksInfo сообщение
        """
        return self._find_and_parse_message(data_class=SubscribeTuLeaksInfoReply, data=data)

    def parse_scheme_signals_state_msg(self, data: list) -> signals_state_model.SchemeSignalsStateReply:
        """
        Парсит сообщение SchemeSignalsStateContent.
        signalsStates приходят как [[signal_type, data_dict], ...] - конвертируем кортежи в словари.
        """
        payload = self.find_reply_status_in_ws_msg(data)
        reply_content = payload.get('replyContent') or {}

        raw_signals = reply_content.get('signalsStates')
        if raw_signals is None:
            raw_signals = payload.get('signalsStates') or []

        raw_to_states = reply_content.get('toStates')
        if raw_to_states is None:
            raw_to_states = payload.get('toStates') or []

        tu_id = reply_content.get('tuId')
        if tu_id is None:
            tu_id = payload.get('tuId', 0)

        parsed_payload = signals_state_model.SchemeSignalsStateReply(
            replyStatus=payload.get('replyStatus', 0),
            replyErrors=payload.get('replyErrors'),
            replyContent=signals_state_model.SchemeSignalsStateContent(
                tuId=tu_id,
                signalsStates=self._parse_scheme_signal_states(raw_signals),
                toStates=self._parse_scheme_to_states(raw_to_states),
            ),
        )
        if parsed_payload.replyErrors:
            fail(f"Ошибка в сообщении типа SchemeSignalsStateContent: {parsed_payload.replyErrors}")
        return parsed_payload

    def parse_unimitate_signal_msg(self, data: list) -> UnimitateSignalReply:
        """
        Парсит сообщение UnimitateSignal
        """
        return self._find_and_parse_message(data_class=UnimitateSignalReply, data=data)

    def parse_unmask_signal_msg(self, data: list) -> UnmaskSignalReply:
        """
        Парсит сообщение UnmaskSignal
        """
        return self._find_and_parse_message(data_class=UnmaskSignalReply, data=data)

    def parse_report_data_exported_notification_msg(self, data: list) -> ReportDataExportedNotification:
        """
        Парсит пуш-нотификацию ReportDataExportedNotification о готовности отчёта.
        """
        return self._find_and_parse_message(data_class=ReportDataExportedNotification, data=data)

    def parse_exported_data_list_msg(self, data: list) -> GetExportedDataListReply:
        """
        Парсит ответ GetExportedDataListReply со списком сформированных файлов.
        """
        return self._find_and_parse_message(data_class=GetExportedDataListReply, data=data)

    def parse_download_exported_data_msg(self, data: list) -> DownloadExportedDataReply:
        """
        Парсит ответ DownloadExportedDataReply со скачиваемым контентом файла (fileChunk).
        """
        return self._find_and_parse_message(data_class=DownloadExportedDataReply, data=data)

    def parse_get_basic_info_admin_msg(self, data: list) -> GetBasicInfoAdminReply:
        """Парсит ответ GetBasicInfoAdminRequest."""
        return self._find_and_parse_message(data_class=GetBasicInfoAdminReply, data=data)

    def parse_launch_lds_msg(self, data: list) -> LaunchLdsReply:
        """Парсит Completion-ответ LaunchLdsRequest."""
        return self._find_and_parse_message(data_class=LaunchLdsReply, data=data)

    def parse_stop_lds_msg(self, data: list) -> StopLdsReply:
        """Парсит Completion-ответ StopLdsRequest."""
        return self._find_and_parse_message(data_class=StopLdsReply, data=data)

    def parse_get_tus_information_msg(self, data: list) -> GetTusInformationReply:
        """Парсит ответ GetTusInformationRequest."""
        return self._find_and_parse_message(data_class=GetTusInformationReply, data=data)

    def _find_and_parse_message(
        self,
        data_class: Type[ContentType],
        data: List[Any],
        config: Optional[Config] = None,
    ) -> ContentType:
        """
        Ищет объект с replyStatus в ws сообщении и парсит его
        """
        payload = self.find_reply_status_in_ws_msg(data)
        parsed_payload = self._parse_message(data_class=data_class, data=payload, config=config)

        return parsed_payload

    def _parse_message(
        self,
        data_class: Type[MessageType],
        data: dict,
        config: Optional[Config] = None,
    ) -> MessageType:
        """
        Универсальная функция парсинга сообщений
        """
        data_class_name = data_class.__name__
        if not data:
            fail(f"Пустое сообщение типа: {data_class_name}")
        error_message = data.get('replyErrors')
        if error_message:
            fail(f"Ошибка в сообщении типа: {data_class_name} текст ошибки: {error_message}")
        try:
            message = from_dict(
                data_class=data_class, data=data, config=config or self._dacite_config  # type: ignore[arg-type]
            )
            if not self.suppress_recv_logging:
                try:
                    attach(
                        str(message) + f" {datetime.now(ZoneInfo(WebSocketClientConstants.ZONE_INFO))}",
                        name=data_class_name,
                        attachment_type=attachment_type.TEXT,
                    )
                except (KeyError, RuntimeError) as error:
                    logger.debug("Allure attach пропущен: %s", error)

            return message
        except DaciteError as error:
            fail(f"Ошибка парсинга сообщения типа: {data_class_name} текст ошибки: {error}")

    def _parse_scheme_signal_states(self, raw_signals: list) -> list[signals_state_model.SignalState]:
        """Разворачивает signalsStates: поддерживает формат [type, dict] и уже готовые dict."""
        signals_states = []
        for item in raw_signals:
            if self._is_valid_signal_tuple(item):
                signals_states.append(
                    self._parse_message(signals_state_model.SignalState, item[_SIGNAL_DATA_POSITION])
                )
            elif isinstance(item, dict):
                signals_states.append(self._parse_message(signals_state_model.SignalState, item))
        return signals_states

    def _parse_scheme_to_states(self, raw_to_states: list) -> list[signals_state_model.ToState]:
        """Разворачивает toStates: поддерживает формат [type, dict] и уже готовые dict."""
        to_states = []
        for item in raw_to_states:
            if self._is_valid_signal_tuple(item):
                to_states.append(self._parse_message(signals_state_model.ToState, item[_SIGNAL_DATA_POSITION]))
            elif isinstance(item, dict):
                to_states.append(self._parse_message(signals_state_model.ToState, item))
        return to_states

    @staticmethod
    def _is_valid_signal_tuple(item: Any) -> bool:
        """Проверяет, что элемент - кортеж/список [signal_type, signal_data_dict]."""
        return (
            isinstance(item, (list, tuple))
            and len(item) >= _MIN_SIGNAL_TUPLE_LENGTH
            and isinstance(item[_SIGNAL_DATA_POSITION], dict)
        )

    @staticmethod
    def find_reply_status_in_ws_msg(data: List[Any]) -> Optional[Dict[str, Any]]:
        """
        Ищет объект с replyStatus в ws сообщении
        """
        if not data:
            fail("Пустое сообщение")
        try:
            for item in reversed(data):
                # 1) Если сам элемент — словарь с replyStatus
                if isinstance(item, dict) and 'replyStatus' in item:
                    return item
                # 2) Если элемент — список / кортеж — проверяем все элементы в нём
                if isinstance(item, (list, tuple)):
                    for elem in item:
                        if isinstance(elem, dict) and 'replyStatus' in elem:
                            return elem
        except (AttributeError, KeyError, TypeError, RuntimeError, ValueError):
            fail("Не удалось найти replyStatus в сообщении")

    def _get_default_config(self) -> Config:
        """
        Получает конфиг с правилами обработки полей
        """

        # TODO добавить strict=True, после выполнения задачи LDS-8792
        def _to_export_status(value: Any) -> ExportStatus:
            return value if isinstance(value, ExportStatus) else ExportStatus(value)

        def _to_exported_data_type(value: Any) -> ExportedDataType:
            return value if isinstance(value, ExportedDataType) else ExportedDataType(value)

        def _to_reply_status(value: Any) -> ReplyStatus:
            return value if isinstance(value, ReplyStatus) else ReplyStatus(value)

        return Config(
            type_hooks={
                UUID: self.convert_to_uuid,
                datetime: self.timestamp_to_datetime,
                ExportStatus: _to_export_status,
                ExportedDataType: _to_exported_data_type,
                ReplyStatus: _to_reply_status,
            }
        )


# Создает экземпляр класса для удобства импорта
ws_message_parser = WsMessageParser()
