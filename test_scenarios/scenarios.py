"""
Сценарии тестов - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import time
from datetime import datetime, timedelta

import allure
import pytest

from constants.enums import Direction, LdsStatus, MessageType, ReplyStatus, StationaryStatus, UserActions
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import (
    CaseData,
    IsRejectedConfig,
    LDSStatusConfig,
    LeakTestConfig,
    RejectionTestCase,
    SmokeSuiteConfig,
)
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


async def basic_info(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig):
    """
    Проверка базовой информации СОУ: список ТУ.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: BasicInfoContent"):
        payload = await t_utils.connect_and_get_msg(ws_client, "getBasicInfoRequest", [])
        parsed_payload = parser.parse_basic_info_msg(payload)
        expected_tu = [(cfg.tu_id, cfg.tu_name)]
        actual_tu = [(tu.tuId, tu.tuName) for tu in parsed_payload.replyContent.basicInfo.tus if tu.tuId == cfg.tu_id]

    with allure.step(f"Поверка наличия {cfg.tu_name} в списке доступных ТУ на сервере"):
        # Критическая проверка: если нужного ТУ нет в BasicInfoContent — считаем что ТУ отключен (через Zookeeper)
        # и прерываем весь прогон.
        if expected_tu[0] not in actual_tu:
            msg = (
                f"ТУ отключен: в BasicInfoContent отсутствует ТУ для запущенного набора данных: "
                f"tuId={cfg.tu_id}, tuName='{cfg.tu_name}', suite={cfg.suite_name}. "
                f"Необходимо убедиться, что ТУ включен (Zookeeper) и перезапустить прогон."
            )
            allure.attach(
                f"Ожидаемый ТУ: {expected_tu}\nПолученные ТУ: {actual_tu}",
                name="Предварительная проверка: ТУ отключен",
                attachment_type=allure.attachment_type.TEXT,
            )
            pytest.fail(msg, pytrace=False)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка статуса ответа", "replyStatus", soft_failures).actual(parsed_payload.replyStatus).expected(
            ReplyStatus.OK.value
        ).equal_to()

        StepCheck("Проверка наличия объектов в списке ТУ", "tus", soft_failures).actual(
            parsed_payload.replyContent.basicInfo.tus
        ).is_not_empty()

        StepCheck(
            f"Проверка наличия ТУ: {cfg.tu_name} в списке ТУ ",
            "(tuId, tuName)",
            soft_failures,
        ).actual(
            actual_tu
        ).expected(expected_tu).equal_to()


async def journal_info(ws_client):
    """
    Проверка наличия сообщений в журнале.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        request_body = t_utils.create_journal_req_body()
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)

    StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(
        parsed_payload.replyContent.messagesInfo
    ).is_not_empty()


async def lds_status_initialization(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка режима работы СОУ: Инициализация.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает самый протяженный участок карты течения
        longest_flow_area = t_utils.get_longest_flow_area(flow_areas)
        # Получает список ДУ
        diagnostic_areas = longest_flow_area.diagnosticAreas
        allure.attach(
            f"Самый протяженный участок карты течений: {longest_flow_area}",
            name="flowArea. Инициализация",
            attachment_type=allure.attachment_type.TEXT,
        )
        # Получает коллекцию статусов списка ДУ
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in diagnostic_areas}
        # Определяет режим работы СОУ по приоритету
        lds_status = t_utils.determine_lds_status_by_priority(lds_status_set)

    StepCheck("Проверка режима работы СОУ", "ldsStatus").actual(lds_status).expected(
        LdsStatus.INITIALIZATION.value
    ).equal_to()


async def lds_status_init_in_journal(ws_client, cfg: SmokeSuiteConfig, imitator_start_time):
    """
    Проверка наличия записи в журнале о входе СОУ в режим Инициализация.
    """
    with allure.step("Запрос сообщений журнала с фильтром messageTypes=LDS_STATUS"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LDS_STATUS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и technologicalSection"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)

        lds_msg = next(
            (
                msg
                for msg in time_filtered
                if msg.technologicalSection == cfg.tu_name and msg.event == TestConst.JOURNAL_EVENT_LDS_INIT_COLD_START
            ),
            None,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n"
            f"проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_LDS_INIT_ACCUM_DATA}': {'True' if lds_msg else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_LDS_INIT_COLD_START}'"
        ):
            if lds_msg is None:
                pytest.fail(
                    f"Сообщение с technologicalSection='{cfg.tu_name}' "
                    f"и event='{TestConst.JOURNAL_EVENT_LDS_INIT_COLD_START}' "
                    f"не найдено среди {len(time_filtered)} отфильтрованных по времени сообщений"
                )

    with allure.step("Проверка актуальности сообщения"):
        msg_time_msk = t_utils.ensure_moscow_timezone(lds_msg.time)
        start_time_msk = t_utils.localize_as_moscow(imitator_start_time)

        StepCheck(
            f"Проверка: время сообщения позднее времени старта имитатора {msg_time_msk} > {start_time_msk}",
            "time",
        ).actual(msg_time_msk > start_time_msk).expected(True).equal_to()

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка event", "event", soft_failures).actual(lds_msg.event).expected(
            TestConst.JOURNAL_EVENT_LDS_INIT_COLD_START
        ).equal_to()

        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(lds_msg.mainPipeline).expected(
            cfg.main_pipeline
        ).equal_to()

        StepCheck("Проверка technologicalSection", "technologicalSection", soft_failures).actual(
            lds_msg.technologicalSection
        ).expected(cfg.tu_name).equal_to()

        StepCheck("Проверка technologicalObject не пустой", "technologicalObject", soft_failures).actual(
            lds_msg.technologicalObject
        ).is_not_none()

        StepCheck("Проверка priority не пустой", "priority", soft_failures).actual(lds_msg.priority).is_not_none()

        StepCheck("Проверка messageType", "messageType", soft_failures).actual(lds_msg.messageType).expected(
            TestConst.JOURNAL_MESSAGE_TYPE_LDS_STATUS
        ).equal_to()


async def main_page_info(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка установки режима МТ.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck(
            f"Проверка установки стационара для ТУ {cfg.tu_name}",
            "stationary_status",
            soft_failures,
        ).actual(
            parsed_payload.replyContent.tuInfo.stationaryStatus
        ).expected(cfg.expected_stationary_status).equal_to()


async def main_page_info_signals(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка счетчиков состояния сигналов
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageSignalsInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageSignalsInfoContent",
            "subscribeMainPageSignalsInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_signals_msg(payload)
    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()
        field_name = "numberOfRejectedSignals"
        StepCheck(
            f"Проверка количества отбракованных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfRejectedSignals
        ).expected(cfg.expected_stationary_status).equal_to(cfg.expected_main_page_signals[field_name])
        field_name = "numberOfMaskedSignals"
        StepCheck(
            f"Проверка количества маскированных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfMaskedSignals
        ).expected(cfg.expected_stationary_status).equal_to(cfg.expected_main_page_signals[field_name])
        field_name = "numberOfImitatedSignals"
        StepCheck(
            f"Проверка количества имитированных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfImitatedSignals
        ).expected(cfg.expected_stationary_status).equal_to(cfg.expected_main_page_signals[field_name])


async def main_page_info_unstationary(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка установки режима Нестационар (для наборов с несколькими утечками).
    Запускается после первой утечки, когда режим переходит в Нестационар.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck(
            f"Проверка установки режима Нестационар для ТУ {cfg.tu_name}",
            "stationary_status",
            soft_failures,
        ).actual(parsed_payload.replyContent.tuInfo.stationaryStatus).expected(
            StationaryStatus.UNSTATIONARY.value
        ).equal_to()


async def mask_signal_msg(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка маскирования датчиков.
    """
    with allure.step("Подключение по ws, получение и обработка данных датчиков давления и расхода"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetInputSignalsRequest",
            {
                'tuId': cfg.tu_id,
                'sorting': None,
                'filtering': None,
                'columnsSelection': 512,
                'search': None,
                'additionalProperties': None,
            },
        )

        parsed_payload = parser.parse_input_signals_msg(payload)
        # Получает список датчиков давления
        pressure_sensor_list = [
            sensor
            for sensor in parsed_payload.replyContent
            if sensor.signalType == TestConst.PRESSURE_SIGNAL_TYPE
            and sensor.objectType == TestConst.PRESSURE_SENSOR_OBJECT_TYPE
        ]
        # Получает список расходомеров
        flowmeter_list = [
            sensor
            for sensor in parsed_payload.replyContent
            if sensor.signalType == TestConst.FLOW_SIGNAL_TYPE and sensor.objectType == TestConst.FLOWMETER_OBJECT_TYPE
        ]
        # Случайно выбирает 1 расходомер и 1 датчик давления
        pressure_sensor = t_utils.get_random_item(pressure_sensor_list)
        flowmeter = t_utils.get_random_item(flowmeter_list)

    with allure.step("Маскирование датчиков"):
        with allure.step(
            f"Отправка сообщения и обработка ответа о маскировании датчика давления с id: {pressure_sensor.id}"
        ):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "MaskSignalRequest",
                {'id': pressure_sensor.id, 'tuId': cfg.tu_id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_mask_signal_msg(payload)
            pressure_sensor_mask_reply_status = parsed_payload.replyStatus

            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                pressure_sensor_mask_reply_status
            ).expected(ReplyStatus.OK.value).equal_to()

        with allure.step(f"Отправка сообщения и обработка ответа о маскировании расходомера с id: {flowmeter.id}"):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "MaskSignalRequest",
                {'id': flowmeter.id, 'tuId': cfg.tu_id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_mask_signal_msg(payload)
            flowmeter_mask_reply_status = parsed_payload.replyStatus

            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                flowmeter_mask_reply_status
            ).expected(ReplyStatus.OK.value).equal_to()

    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчиков из сообщения типа: InputSignalsContent"
    ):
        time.sleep(cfg.basic_message_timeout)
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [pressure_sensor.id, flowmeter.id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_input_signals_info_msg(payload)
        sensor_data = parsed_payload.replyContent.inputSignals
        pressure_sensor_mask_data = t_utils.find_object_by_field(sensor_data, "id", pressure_sensor.id)
        flowmeter_mask_data = t_utils.find_object_by_field(sensor_data, "id", flowmeter.id)

    with allure.step("Снятие маскирования датчиков"):
        with allure.step(
            f"Отправка сообщения и обработка ответа о снятии маскирования датчика давления с id: {pressure_sensor.id}"
        ):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "UnmaskSignalRequest",
                {'id': pressure_sensor.id, 'tuId': cfg.tu_id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_unmask_signal_msg(payload)
            pressure_sensor_unmask_reply_status = parsed_payload.replyStatus

            StepCheck("Проверка кода ответа на запрос о снятии маскирования", "replyStatus").actual(
                pressure_sensor_unmask_reply_status
            ).expected(ReplyStatus.OK.value).equal_to()

        with allure.step(
            f"Отправка сообщения и обработка ответа о снятии маскирования расходомера с id: {flowmeter.id}"
        ):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "UnmaskSignalRequest",
                {'id': flowmeter.id, 'tuId': cfg.tu_id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_unmask_signal_msg(payload)
            flowmeter_unmask_reply_status = parsed_payload.replyStatus

            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                flowmeter_unmask_reply_status
            ).expected(ReplyStatus.OK.value).equal_to()

    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчиков из сообщения типа: InputSignalsContent"
    ):
        time.sleep(cfg.basic_message_timeout)
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [pressure_sensor.id, flowmeter.id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_input_signals_info_msg(payload)
        sensor_data = parsed_payload.replyContent.inputSignals
        pressure_sensor_unmask_data = t_utils.find_object_by_field(sensor_data, "id", pressure_sensor.id)
        flowmeter_unmask_data = t_utils.find_object_by_field(sensor_data, "id", flowmeter.id)

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка маскирования датчика давления с id: {pressure_sensor.id}", "isMasked", soft_failures
        ).actual(pressure_sensor_mask_data.isMasked).expected(True).equal_to()
        StepCheck(f"Проверка маскирования расходомера с id: {flowmeter.id}", "isMasked", soft_failures).actual(
            flowmeter_mask_data.isMasked
        ).expected(True).equal_to()
        StepCheck(
            f"Проверка снятия маскирования датчика давления с id: {pressure_sensor.id}", "isMasked", soft_failures
        ).actual(pressure_sensor_unmask_data.isMasked).expected(False).equal_to()
        StepCheck(f"Проверка снятия маскирования расходомера с id: {flowmeter.id}", "isMasked", soft_failures).actual(
            flowmeter_unmask_data.isMasked
        ).expected(False).equal_to()


async def mask_info_in_journal(ws_client, cfg: SmokeSuiteConfig, imitator_start_time):
    """
    Проверка записей журнала о маскировании и размаскировании.
    """
    with allure.step("Запрос сообщений журнала с фильтром userActions"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_MASK_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(userActions=int(UserActions.SIGNAL_MASK_SIM), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        all_messages = parsed_payload.replyContent.messagesInfo

    with allure.step("Фильтрация сообщений по событиям маскирования и временному диапазону"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        mask_unmask_msgs = [
            msg
            for msg in all_messages
            if msg.event in TestConst.JOURNAL_MASK_EXPECTED_EVENTS
            and msg.signalName in TestConst.JOURNAL_MASK_EXPECTED_SIGNALS
        ]

        journal_messages = [
            msg
            for msg in mask_unmask_msgs
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]

        allure.attach(
            f"Всего получено сообщений: {len(all_messages)}\n"
            f"После фильтрации по event и signalName осталось сообщений: {len(mask_unmask_msgs)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}) "
            f"осталось сообщений: {len(journal_messages)}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step("Группировка отфильтрованных сообщений"):
        pressure_msgs = [msg for msg in journal_messages if msg.signalName == TestConst.JOURNAL_SIGNAL_PRESSURE]
        flow_msgs = [msg for msg in journal_messages if msg.signalName == TestConst.JOURNAL_SIGNAL_FLOW]

        mask_event_msgs = [msg for msg in journal_messages if msg.event == TestConst.JOURNAL_EVENT_MASK]
        unmask_event_msgs = [msg for msg in journal_messages if msg.event == TestConst.JOURNAL_EVENT_UNMASK]
        mask_signal_names = {msg.signalName for msg in mask_event_msgs}
        unmask_signal_names = {msg.signalName for msg in unmask_event_msgs}

    with SoftAssertions() as journal_soft_failures:
        StepCheck(
            "Проверка соответствия количества сообщений о действиях пользователя (снятие и установка "
            "маскирования для датчиков давления и расходомеров)",
            "total_count",
            journal_soft_failures,
        ).actual(len(journal_messages)).expected(TestConst.JOURNAL_EXPECTED_MASK_MSG_TOTAL).equal_to()

        StepCheck(
            f"Проверка соответствия количества сообщений "
            f"о действиях пользователя для датчиков давления - '{TestConst.JOURNAL_SIGNAL_PRESSURE}'",
            "count",
            journal_soft_failures,
        ).actual(len(pressure_msgs)).expected(TestConst.JOURNAL_EXPECTED_MSG_COUNT_PER_SIGNAL).equal_to()

        StepCheck(
            f"Проверка соответствия количества сообщений "
            f"о действиях пользователя для расходомеров - '{TestConst.JOURNAL_SIGNAL_FLOW}'",
            "count",
            journal_soft_failures,
        ).actual(len(flow_msgs)).expected(TestConst.JOURNAL_EXPECTED_MSG_COUNT_PER_SIGNAL).equal_to()

        StepCheck(
            f"Проверка: событие '{TestConst.JOURNAL_EVENT_MASK}' содержит '{TestConst.JOURNAL_SIGNAL_PRESSURE}'",
            "signalName",
            journal_soft_failures,
        ).actual(TestConst.JOURNAL_SIGNAL_PRESSURE in mask_signal_names).expected(True).equal_to()

        StepCheck(
            f"Проверка: событие '{TestConst.JOURNAL_EVENT_MASK}' содержит '{TestConst.JOURNAL_SIGNAL_FLOW}'",
            "signalName",
            journal_soft_failures,
        ).actual(TestConst.JOURNAL_SIGNAL_FLOW in mask_signal_names).expected(True).equal_to()

        StepCheck(
            f"Проверка: событие '{TestConst.JOURNAL_EVENT_UNMASK}' содержит '{TestConst.JOURNAL_SIGNAL_PRESSURE}'",
            "signalName",
            journal_soft_failures,
        ).actual(TestConst.JOURNAL_SIGNAL_PRESSURE in unmask_signal_names).expected(True).equal_to()

        StepCheck(
            f"Проверка: событие '{TestConst.JOURNAL_EVENT_UNMASK}' содержит '{TestConst.JOURNAL_SIGNAL_FLOW}'",
            "signalName",
            journal_soft_failures,
        ).actual(TestConst.JOURNAL_SIGNAL_FLOW in unmask_signal_names).expected(True).equal_to()

        for signal_name in [TestConst.JOURNAL_SIGNAL_PRESSURE, TestConst.JOURNAL_SIGNAL_FLOW]:
            mask_msg_for_signal = next((msg for msg in mask_event_msgs if msg.signalName == signal_name), None)
            unmask_msg_for_signal = next((msg for msg in unmask_event_msgs if msg.signalName == signal_name), None)

            if mask_msg_for_signal and unmask_msg_for_signal:
                StepCheck(
                    f"Проверка совпадения tag для '{signal_name}' между маскированием и снятием",
                    "tag",
                    journal_soft_failures,
                ).actual(mask_msg_for_signal.tag).expected(unmask_msg_for_signal.tag).equal_to()

        for msg in journal_messages:
            msg_label = f"{msg.event} - {msg.signalName}"

            StepCheck(
                f"Проверка user не пустой [{msg_label}]",
                "user",
                journal_soft_failures,
            ).actual(msg.user).is_not_none()

            StepCheck(
                f"Проверка mainPipeline [{msg_label}]",
                "mainPipeline",
                journal_soft_failures,
            ).actual(
                msg.mainPipeline
            ).expected(cfg.main_pipeline).equal_to()

            StepCheck(
                f"Проверка object не пустой [{msg_label}]",
                "object",
                journal_soft_failures,
            ).actual(msg.object).is_not_none()

            StepCheck(
                f"Проверка technologicalObject не пустой [{msg_label}]",
                "technologicalObject",
                journal_soft_failures,
            ).actual(msg.technologicalObject).is_not_none()

            StepCheck(
                f"Проверка technologicalSection [{msg_label}]",
                "technologicalSection",
                journal_soft_failures,
            ).actual(msg.technologicalSection).expected(cfg.tu_name).equal_to()

            StepCheck(
                f"Проверка priority не пустой [{msg_label}]",
                "priority",
                journal_soft_failures,
            ).actual(msg.priority).is_not_none()

            StepCheck(
                f"Проверка messageType [{msg_label}]",
                "messageType",
                journal_soft_failures,
            ).actual(
                msg.messageType
            ).expected(TestConst.JOURNAL_MESSAGE_TYPE_USER_ACTIONS).equal_to()

            StepCheck(
                f"Проверка status [{msg_label}]",
                "status",
                journal_soft_failures,
            ).actual(
                msg.status
            ).expected(TestConst.JOURNAL_STATUS_SUCCESS).equal_to()


async def mask_du_on_mini_scheme(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Маскирование ДУ на мини-схеме
    Проверка маскированного участка в выходных сигналах

    """
    linear_part_id = cfg.linear_part_identifier_for_mask
    mask_reason = cfg.mask_reason

    with allure.step("Подключение по ws, отправка сообщения типа: MaskLdsRequest"):
        payload = (
            await t_utils.connect_and_get_msg(
                ws_client,
                "MaskLdsRequest",
                {
                    'tuId': cfg.tu_id,
                    'maskInfo': [
                        {
                            'linearPartId': linear_part_id,
                            'reason': mask_reason,
                            'additionalProperties': None,
                        }
                    ],
                    'additionalProperties': None,
                },
            ),
        )
        time.sleep(cfg.basic_message_timeout)
        parsed_payload = parser.parse_unmask_lds_message(payload)
        flowmeter_mask_reply_status = parsed_payload.replyStatus

    with allure.step(f"Получение словаря для линейного участка с id: {linear_part_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetOutputSignalsRequest",
            {
                'tuId': cfg.tu_id,
                'filtering': None,
                'search': None,
                'sorting': None,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_output_signals_msg(payload)
        # Получение данных линейного участка утечки по id
        leak_linear_part = t_utils.find_object_by_field(
            parsed_payload.replyContent.linearPartSignals,
            TestConst.LEAK_LINEAR_PART_ID_KEY,
            linear_part_id,
        )

        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals

            mask_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_MASK
            )

    with allure.step(f"Получение данных выходных сигналов для линейного участка с id: {linear_part_id}"):
        with allure.step("Получение сообщения с данными выходных сигналов типа: OutputSignalsInfo"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "OutputSignalsInfo",
                "SubscribeOutputSignalsRequest",
                {
                    'objects': {
                        'linearParts': [{'linearPartId': linear_part_id}],
                        'controlledSites': [],
                    },
                    'signalTypes': 1023,
                    'tuId': cfg.tu_id,
                    'additionalProperties': None,
                },
            )
            parsed_payload = parser.parse_output_signals_info_msg(payload)
            leak_linear_part = t_utils.find_object_by_field(
                parsed_payload.replyContent.linearPartSignals,
                TestConst.LEAK_LINEAR_PART_ID_KEY,
                linear_part_id,
            )
        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)

    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        linear_parts = parsed_payload.replyContent.linearParts
        mask_linear_part = next((lp for lp in linear_parts if lp.id == linear_part_id), None)

    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent."):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "SubscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)
        # Получает информацию о ТУ
        tu_info = parsed_payload.replyContent.tuInfo
        # Получает количество маскированных ДУ
        number_of_masked_lps = tu_info.ldsStatus.numberOfMaskedLps
        # Получает список маскированных ДУ
        masked_lps = tu_info.ldsStatus.maskedLps

    with allure.step(
        "Подключение по ws, получение и обработка сообщения типа: MessagesInfo. Проверка события маскирования СОУ"
    ):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=10, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.MASKING_LDS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messagesInfo = parsed_payload.replyContent.messagesInfo

        if cfg.technological_section:
            mask_message = t_utils.find_object_by_field(messagesInfo, "technologicalSection", cfg.technological_section)
        else:
            mask_message = parsed_payload.replyContent.messagesInfo[0]

    # Проверки сообщений
    with SoftAssertions() as soft_failures:
        StepCheck(
            "Проверка сигнала маскирования ДУ в выходных сигналах", TestConst.ADDRESS_SUFFIX_MASK, soft_failures
        ).actual(mask_leak_value).expected(TestConst.OUTPUT_IS_MASK).equal_to()
        StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus", soft_failures).actual(
            flowmeter_mask_reply_status
        ).expected(ReplyStatus.OK.value).equal_to()
        StepCheck("Проверка статуса маскирования ДУ на схеме", "isMasked", soft_failures).actual(
            mask_linear_part.isMasked
        ).expected(True).equal_to()
        StepCheck("Проверка причины маски в журнале", "maskReason").actual(mask_linear_part.maskReason).expected(
            cfg.mask_reason
        ).equal_to()
        StepCheck("Проверка имени ТУ в журнале", "mainPipeline", soft_failures).actual(
            mask_message.mainPipeline
        ).expected(cfg.main_pipe_line).equal_to()
        StepCheck("Проверка имени ДУ в журнале", "technologicalObject", soft_failures).actual(
            mask_message.technologicalObject
        ).expected(cfg.mask_du_name).equal_to()
        StepCheck("Проверка события в журнале", "event", soft_failures).actual(mask_message.event).expected(
            cfg.mask_du_event
        ).equal_to()
        StepCheck("Проверка количества маскированных ДУ", "numberOfMaskedLps", soft_failures).actual(
            number_of_masked_lps
        ).expected(cfg.mask_one_du).equal_to()
        StepCheck("Проверка списка маскированных ДУ", "maskedLps", soft_failures).actual(
            cfg.mask_du_name in masked_lps
        ).expected(True).equal_to()


async def unmask_du_on_mini_scheme(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Размаскирование ДУ на мини-схеме
    Проверка маскированного участка в выходных сигналах

    """
    linear_part_id = cfg.linear_part_identifier_for_mask
    unmask_reason = cfg.unmask_reason

    with allure.step("Подключение по ws, отправка сообщения типа: UnmaskLdsRequest"):
        payload = (
            await t_utils.connect_and_get_msg(
                ws_client,
                "UnmaskLdsRequest",
                {
                    'tuId': cfg.tu_id,
                    'maskInfo': [
                        {
                            'linearPartId': linear_part_id,
                            'reason': unmask_reason,
                            'additionalProperties': None,
                        }
                    ],
                    'additionalProperties': None,
                },
            ),
        )
        time.sleep(cfg.basic_message_timeout)
        parsed_payload = parser.parse_unmask_lds_message(payload)
        flowmeter_mask_reply_status = parsed_payload.replyStatus

    with allure.step(f"Получение словаря для линейного участка с id: {linear_part_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetOutputSignalsRequest",
            {
                'tuId': cfg.tu_id,
                'filtering': None,
                'search': None,
                'sorting': None,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_output_signals_msg(payload)
        # Получение данных линейного участка утечки по id
        leak_linear_part = t_utils.find_object_by_field(
            parsed_payload.replyContent.linearPartSignals,
            TestConst.LEAK_LINEAR_PART_ID_KEY,
            linear_part_id,
        )

        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals

            mask_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_MASK
            )

    with allure.step(f"Получение данных выходных сигналов для линейного участка с id: {linear_part_id}"):
        with allure.step("Получение сообщения с данными выходных сигналов типа: OutputSignalsInfo"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "OutputSignalsInfo",
                "SubscribeOutputSignalsRequest",
                {
                    'objects': {
                        'linearParts': [{'linearPartId': linear_part_id}],
                        'controlledSites': [],
                    },
                    'signalTypes': 1023,
                    'tuId': cfg.tu_id,
                    'additionalProperties': None,
                },
            )
            parsed_payload = parser.parse_output_signals_info_msg(payload)
            leak_linear_part = t_utils.find_object_by_field(
                parsed_payload.replyContent.linearPartSignals,
                TestConst.LEAK_LINEAR_PART_ID_KEY,
                linear_part_id,
            )

        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)

    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent."):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "SubscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)
        # Получает информацию о ТУ
        tu_info = parsed_payload.replyContent.tuInfo
        # Получает количество маскированных ДУ
        number_of_masked_lps = tu_info.ldsStatus.numberOfMaskedLps

    with allure.step(
        "Подключение по ws, получение и обработка сообщения типа: MessagesInfo. Проверка события снятия маскирования"
    ):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=10, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.MASKING_LDS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messagesInfo = parsed_payload.replyContent.messagesInfo

        if cfg.technological_section:
            mask_message = t_utils.find_object_by_field(messagesInfo, "technologicalSection", cfg.technological_section)
        else:
            mask_message = parsed_payload.replyContent.messagesInfo[0]

    # Проверки сообщений
    with SoftAssertions() as soft_failures:
        StepCheck("Проверка кода ответа на запрос о размаскировании", "replyStatus", soft_failures).actual(
            flowmeter_mask_reply_status
        ).expected(ReplyStatus.OK.value).equal_to()
        StepCheck(
            "Проверяем, что тег маскирования ДУ в выходных сигналах равен null",
            TestConst.ADDRESS_SUFFIX_MASK,
            soft_failures,
        ).actual(mask_leak_value).expected(TestConst.OUTPUT_IS_NOT_MASK).equal_to()
        StepCheck("Проверяем имя ТУ в сообщении в журнале", "mainPipeline", soft_failures).actual(
            mask_message.mainPipeline
        ).expected(cfg.main_pipe_line).equal_to()
        StepCheck("Проверяем имя ДУ в сообщении в журнале", "technologicalObject", soft_failures).actual(
            mask_message.technologicalObject
        ).expected(cfg.mask_du_name).equal_to()
        StepCheck("Проверка события в сообщении в журнале", "event", soft_failures).actual(mask_message.event).expected(
            cfg.unmask_du_event
        ).equal_to()
        StepCheck("Проверка количества маскированных ДУ", "numberOfMaskedLps", soft_failures).actual(
            number_of_masked_lps
        ).expected(cfg.not_mask_du).equal_to()


async def lds_status_initialization_out(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка выхода СОУ из Инициализации.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        flow_areas = parsed_payload.replyContent.flowAreas
        longest_flow_area = t_utils.get_longest_flow_area(flow_areas)
        diagnostic_areas = longest_flow_area.diagnosticAreas
        allure.attach(
            f"Самый протяженный участок карты течений: {longest_flow_area}",
            name="flowArea. Выход из Инициализации",
            attachment_type=allure.attachment_type.TEXT,
        )
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in diagnostic_areas}
        lds_status = t_utils.determine_lds_status_by_priority(lds_status_set)

    StepCheck(
        "Проверка: СОУ находится не в режиме 'Инициализация'",
        "ldsStatus",
    ).actual(
        lds_status
    ).expected(LdsStatus.INITIALIZATION.value).is_not_equal_to()


async def lds_status_init_out_in_journal(ws_client, cfg: SmokeSuiteConfig, imitator_start_time):
    """
    Проверка наличия записи в журнале о выходе СОУ из режима Инициализация.
    """
    with allure.step("Запрос сообщений журнала с фильтром messageTypes=LDS_STATUS"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LDS_STATUS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и technologicalSection"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)

        lds_msg = next(
            (msg for msg in time_filtered if msg.technologicalSection == cfg.tu_name),
            None,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n"
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}': {'True' if lds_msg else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}'"):
            if lds_msg is None:
                pytest.fail(
                    f"Сообщение с technologicalSection='{cfg.tu_name}' "
                    f"не найдено среди {len(time_filtered)} отфильтрованных по времени сообщений"
                )

    with allure.step("Проверка актуальности сообщения"):
        msg_time_msk = t_utils.ensure_moscow_timezone(lds_msg.time)
        start_time_msk = t_utils.localize_as_moscow(imitator_start_time)

        StepCheck(
            f"Проверка: время сообщения позднее времени старта имитатора {msg_time_msk} > {start_time_msk}",
            "time",
        ).actual(msg_time_msk > start_time_msk).expected(True).equal_to()

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка: event не является Инициализацией", "event", soft_failures).actual(lds_msg.event).expected(
            TestConst.JOURNAL_EVENT_LDS_INIT_ACCUM_DATA
        ).is_not_equal_to()

        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(lds_msg.mainPipeline).expected(
            cfg.main_pipeline
        ).equal_to()

        StepCheck("Проверка technologicalSection", "technologicalSection", soft_failures).actual(
            lds_msg.technologicalSection
        ).expected(cfg.tu_name).equal_to()

        StepCheck("Проверка technologicalObject не пустой", "technologicalObject", soft_failures).actual(
            lds_msg.technologicalObject
        ).is_not_none()

        StepCheck("Проверка priority не пустой", "priority", soft_failures).actual(lds_msg.priority).is_not_none()

        StepCheck("Проверка messageType", "messageType", soft_failures).actual(lds_msg.messageType).expected(
            TestConst.JOURNAL_MESSAGE_TYPE_LDS_STATUS
        ).equal_to()


async def leaks_content(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка утечки через сообщение LeaksContent.
    """
    with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "LeaksContent",
            "SubscribeLeaksRequest",
            {'tuId': cfg.tu_id},
        )
        parsed_payload = parser.parse_leaks_content_msg(payload)
        leaks_list_info = parsed_payload.replyContent.leaksListInfo

        first_leak_info = t_utils.find_leak_by_coordinate(leaks_list_info, leak.coordinate_meters)

        # Конвертируем время обнаружения в московское время
        leak_detected_at = t_utils.ensure_moscow_timezone(first_leak_info.detectedAt)
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            leak.leak_start_interval_seconds,
            leak.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak_info.leakVolume)
        leak_coordinate_round = round(first_leak_info.leakCoordinate, cfg.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck("Проверка наличия названия участка утечки", "diagnosticAreaName", soft_failures).actual(
            first_leak_info.diagnosticAreaName
        ).is_not_none()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            first_leak_info.confirmationStatus
        ).expected(leak.expected_leak_status).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(first_leak_info.type).expected(
            leak.expected_algorithm_type
        ).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )


async def possible_leak_in_journal(ws_client, cfg: SmokeSuiteConfig, imitator_start_time):
    """
    Проверка наличия сообщения 'Возможна утечка' в журнале.
    """
    with allure.step("Подключение по ws, получение и обработка сообщений журнала типа: MessagesInfoContent"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LEAKS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и technologicalSection"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)

        possible_leak_msg = next(
            (
                msg
                for msg in time_filtered
                if msg.technologicalSection == cfg.tu_name and msg.event == TestConst.JOURNAL_EVENT_POSSIBLE_LEAK
            ),
            None,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n"
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_POSSIBLE_LEAK}': {'True' if possible_leak_msg else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_POSSIBLE_LEAK}'"
        ):
            if possible_leak_msg is None:
                pytest.fail(
                    f"Сообщение с technologicalSection='{cfg.tu_name}' "
                    f"и event='{TestConst.JOURNAL_EVENT_POSSIBLE_LEAK}' "
                    f"не найдено среди {len(time_filtered)} отфильтрованных по времени сообщений"
                )

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка статуса утечки в журнале", "event", soft_failures).actual(possible_leak_msg.event).expected(
            TestConst.JOURNAL_EVENT_POSSIBLE_LEAK
        ).equal_to()

        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(
            possible_leak_msg.mainPipeline
        ).expected(cfg.main_pipeline).equal_to()

        StepCheck("Проверка messageType", "messageType", soft_failures).actual(possible_leak_msg.messageType).expected(
            TestConst.JOURNAL_MESSAGE_TYPE_LEAKS
        ).equal_to()

        StepCheck("Проверка technologicalSection не пустой", "technologicalSection", soft_failures).actual(
            possible_leak_msg.technologicalSection
        ).is_not_none()

        StepCheck("Проверка technologicalObject не пустой", "technologicalObject", soft_failures).actual(
            possible_leak_msg.technologicalObject
        ).is_not_none()


async def leak_info_in_journal(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=1, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LEAKS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(
            parsed_payload.replyContent.messagesInfo
        ).is_not_empty()
        if leak.technological_object:
            leak_message = t_utils.find_object_by_field(messages_info, 'technologicalObject', leak.technological_object)
        else:
            leak_message = parsed_payload.replyContent.messagesInfo[0]
        leak_coordinate_km, leak_volume_m3 = t_utils.parse_journal_msg_value(leak_message.value)
        leak_detected_at = t_utils.ensure_moscow_timezone(leak_message.time)
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            leak.leak_start_interval_seconds,
            leak.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_coordinate_round = round(leak_coordinate_km * TestConst.KM_TO_METERS, TestConst.PRECISION)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка полученного ТУ", "technologicalSection", soft_failures).actual(
            leak_message.technologicalSection
        ).expected(cfg.tu_name).equal_to()
        if leak.technological_object:
            StepCheck("Проверка имени ДУ", "technologicalObject", soft_failures).actual(
                leak_message.technologicalObject
            ).expected(leak.technological_object).equal_to()
        else:
            StepCheck("Проверка имени ДУ", "technologicalObject", soft_failures).actual(
                leak_message.technologicalObject
            ).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )


async def all_leaks_info(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка сообщения AllLeaksInfo об утечке.
    """
    with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            cfg.tu_id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )

        StepCheck("Проверка наличия сообщения об утечке типа AllLeaksInfoContent", "leaksInfo").actual(
            parsed_payload.replyContent.leaksInfo
        ).is_not_empty()

    with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
        leaks_info = parsed_payload.replyContent.leaksInfo
        # Если у утечки указано имя ДУ - ищем по нему, иначе берём первую
        first_leak_info = t_utils.find_leak_by_coordinate(leaks_info, leak.coordinate_meters)

        # Конвертируем время обнаружения в московское время
        leak_detected_at = t_utils.ensure_moscow_timezone(first_leak_info.leakDetectedAt)
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            leak.leak_start_interval_seconds,
            leak.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak_info.volume)
        leak_coordinate_round = round(first_leak_info.leakCoordinate, cfg.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck("Проверка наличия названия участка утечки", "diagnosticAreaName", soft_failures).actual(
            first_leak_info.diagnosticAreaName
        ).is_not_none()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(first_leak_info.ldsStatus).expected(
            leak.expected_lds_status
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(first_leak_info.isMasked).expected(
            False
        ).equal_to()

        StepCheck("Проверка квитирования утечки", "isAcknowledged", soft_failures).actual(
            first_leak_info.isAcknowledged
        ).expected(False).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            first_leak_info.stationaryStatus
        ).expected(leak.expected_stationary_status).equal_to()


async def tu_leaks_info(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка сообщения TuLeaksInfo об утечке.
    """
    with allure.step("Подключение по ws и получение сообщения об утечке типа: TuLeaksInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "TuLeaksInfoContent",
            "subscribeTuLeaksInfoRequest",
            {'tuId': cfg.tu_id},
        )
        parsed_payload = parser.parse_tu_leaks_info_msg(payload)

        StepCheck("Проверка наличия сообщения об утечке типа TuLeaksInfoContent", "leaksInfo").actual(
            parsed_payload.replyContent.leaksInfo
        ).is_not_empty()

    with allure.step("Обработка сообщения об утечке типа TuLeaksInfoContent"):
        tu_leaks_info_list = parsed_payload.replyContent.leaksInfo

        first_leak_info = t_utils.find_leak_by_coordinate(tu_leaks_info_list, leak.coordinate_meters)

        # Конвертируем время обнаружения в московское время
        leak_detected_at = t_utils.ensure_moscow_timezone(first_leak_info.leakDetectedAt)
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            leak.leak_start_interval_seconds,
            leak.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak_info.volume)
        leak_coordinate_round = round(first_leak_info.leakCoordinate, cfg.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck("Проверка наличия id участка утечки", "controlledSiteId", soft_failures).actual(
            first_leak_info.controlledSiteId
        ).is_not_none()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(first_leak_info.ldsStatus).expected(
            leak.expected_lds_status
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(first_leak_info.isMasked).expected(
            False
        ).equal_to()

        StepCheck("Проверка наличия pipeId в сообщении", "pipeId", soft_failures).actual(
            first_leak_info.pipeId
        ).is_not_none()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            first_leak_info.stationaryStatus
        ).expected(leak.expected_stationary_status).equal_to()


async def lds_status_during_leak(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Проверка режима работы СОУ во время утечки.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

    parsed_payload = parser.parse_common_scheme_info_msg(payload)
    flow_areas = parsed_payload.replyContent.flowAreas

    status_config = leak.lds_status_during_leak_config
    if status_config is None:
        pytest.fail("Не задан leak.lds_status_during_leak_config для теста lds_status_during_leak")

    leak_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, status_config.leak_diagnostic_area_id)

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка режима работы СОУ на ДУ с утечкой, id ДУ: {status_config.leak_diagnostic_area_id}",
            "ldsStatus",
            soft_failures,
        ).actual(leak_diagnostic_area.ldsStatus).expected(status_config.leak_du_expected_lds_status).equal_to()

        # Проверки соседних ДУ: поддерживаются 0..N соседей отдельно для in/out.
        # Формат конфига: status_config.in_neighbors / status_config.out_neighbors (dict[id] = expected_status)
        in_neighbors: dict[int, int] = status_config.in_neighbors or {}
        out_neighbors: dict[int, int] = status_config.out_neighbors or {}

        # --- проверки ---
        for neighbor_id, expected_status in sorted(in_neighbors.items()):
            diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, neighbor_id)
            StepCheck(
                f"Проверка режима работы СОУ на соседнем ДУ (in_neighbor), id ДУ: {neighbor_id}",
                "ldsStatus",
                soft_failures,
            ).actual(diagnostic_area.ldsStatus).expected(expected_status).equal_to()

        for neighbor_id, expected_status in sorted(out_neighbors.items()):
            diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, neighbor_id)
            StepCheck(
                f"Проверка режима работы СОУ на соседнем ДУ (out_neighbor), id ДУ: {neighbor_id}",
                "ldsStatus",
                soft_failures,
            ).actual(diagnostic_area.ldsStatus).expected(expected_status).equal_to()


async def acknowledge_leak_info(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig = None):
    """
    Проверка квитирования утечки.

    Для multi-leak наборов: после квитирования проверяется что утечка удалена из списка.
    Для single-leak наборов: проверяется что список утечек пуст.
    """
    with allure.step("Получение id утечки"):
        with allure.step("Подключение по ws, получение и обработка сообщения об утечке типа: TuLeaksInfoContent"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "TuLeaksInfoContent",
                "subscribeTuLeaksInfoRequest",
                {'tuId': cfg.tu_id},
            )
            parsed_payload = parser.parse_tu_leaks_info_msg(payload)

        with allure.step("Получение id утечки из принятого сообщения типа: TuLeaksInfoContent"):
            StepCheck("Проверка наличия сообщения об утечке", "leaksInfo").actual(
                parsed_payload.replyContent.leaksInfo
            ).is_not_empty()

            leaks_info = parsed_payload.replyContent.leaksInfo

            leak_to_ack = t_utils.find_leak_by_coordinate(leaks_info, leak.coordinate_meters)

            acknowledged_leak_id = leak_to_ack.id

    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': str(acknowledged_leak_id), 'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_acknowledge_leak_msg(payload)
        acknowledge_reply_status = parsed_payload.replyStatus

    with allure.step(
        "Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent для проверки квитирования"
    ):
        with allure.step("Очистка очереди websocket сообщений"):
            ws_client.clear_queue()
        time.sleep(cfg.basic_message_timeout)
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            cfg.tu_id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )
        remaining_leaks = parsed_payload.replyContent.leaksInfo
        remaining_leak_ids = [leak.id for leak in remaining_leaks] if remaining_leaks else []

    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(acknowledge_reply_status).expected(
        ReplyStatus.OK.value
    ).equal_to()

    # Проверяем что квитированная утечка исчезла из списка
    StepCheck("Проверка отсутствия квитированной утечки в списке AllLeaksInfo", "id").does_not_contain(
        remaining_leak_ids, acknowledged_leak_id
    )


async def acknowledge_leak_in_journal(ws_client, cfg: SmokeSuiteConfig, imitator_start_time):
    """
    Проверка записи в журнале о квитировании утечки.
    """
    with allure.step("Запрос сообщений журнала с фильтром userActions=LEAK_ACK"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(userActions=int(UserActions.LEAK_ACK), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и technologicalSection"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)

        ack_message = next(
            (
                msg
                for msg in time_filtered
                if msg.technologicalSection == cfg.tu_name and msg.event == TestConst.JOURNAL_EVENT_LEAK_ACKNOWLEDGED
            ),
            None,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n"
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_LEAK_ACKNOWLEDGED}': {'True' if ack_message else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

        with allure.step(
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_LEAK_ACKNOWLEDGED}'"
        ):
            if ack_message is None:
                pytest.fail(
                    f"Сообщение с technologicalSection='{cfg.tu_name}' "
                    f"и event='{TestConst.JOURNAL_EVENT_LEAK_ACKNOWLEDGED}' "
                    f"не найдено среди {len(time_filtered)} отфильтрованных по времени сообщений"
                )

    with allure.step("Проверка актуальности сообщения"):
        msg_time_msk = t_utils.ensure_moscow_timezone(ack_message.time)
        start_time_msk = t_utils.localize_as_moscow(imitator_start_time)

        StepCheck(
            "Проверка: время сообщения позднее времени старта имитатора",
            "time",
        ).actual(
            msg_time_msk > start_time_msk
        ).expected(True).equal_to()

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка event", "event", soft_failures).actual(ack_message.event).expected(
            TestConst.JOURNAL_EVENT_LEAK_ACKNOWLEDGED
        ).equal_to()

        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(ack_message.mainPipeline).expected(
            cfg.main_pipeline
        ).equal_to()

        StepCheck("Проверка technologicalSection", "technologicalSection", soft_failures).actual(
            ack_message.technologicalSection
        ).expected(cfg.tu_name).equal_to()

        StepCheck("Проверка technologicalObject не пустой", "technologicalObject", soft_failures).actual(
            ack_message.technologicalObject
        ).is_not_none()


async def output_signals(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка наличия данных об утечке в выходных сигналах.
    """
    linear_part_id = leak.linear_part_id

    with allure.step(f"Получение списка выходных сигналов для линейного участка с id: {linear_part_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetOutputSignalsRequest",
            {
                'tuId': cfg.tu_id,
                'filtering': None,
                'search': None,
                'sorting': None,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_output_signals_msg(payload)
        # Получение данных линейного участка утечки по id
        leak_linear_part = t_utils.find_object_by_field(
            parsed_payload.replyContent.linearPartSignals,
            TestConst.LEAK_LINEAR_PART_ID_KEY,
            linear_part_id,
        )

        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_ACK_LEAK
            )
            leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_LEAK
            )
            mask_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_MASK
            )
            point_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_POINT_LEAK
            )
            q_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_Q_LEAK
            )
            time_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_TIME_LEAK
            )

    with allure.step(f"Получение данных выходных сигналов для линейного участка с id: {linear_part_id}"):
        with allure.step("Получение сообщения с данными выходных сигналов типа: OutputSignalsInfo"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "OutputSignalsInfo",
                "SubscribeOutputSignalsRequest",
                {
                    'objects': {
                        'linearParts': [{'linearPartId': linear_part_id}],
                        'controlledSites': [],
                    },
                    'signalTypes': 1023,
                    'tuId': cfg.tu_id,
                    'additionalProperties': None,
                },
            )
            parsed_payload = parser.parse_output_signals_info_msg(payload)
            leak_linear_part = t_utils.find_object_by_field(
                parsed_payload.replyContent.linearPartSignals,
                TestConst.LEAK_LINEAR_PART_ID_KEY,
                linear_part_id,
            )

        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, ack_leak_signal_type)
            leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, leak_signal_type)
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)
            point_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, point_leak_signal_type)
            q_leak_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, q_leak_signal_type)
            time_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, time_leak_signal_type).strip()

            StepCheck("Проверка наличия времени утечки", TestConst.ADDRESS_SUFFIX_TIME_LEAK).actual(
                time_leak_value
            ).is_not_none()

            time_leak_value_datetime = t_utils.to_moscow_timezone(time_leak_value)
            leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
                imitator_start_time,
                leak.leak_start_interval_seconds,
                leak.output_allowed_time_diff_seconds,
                detected_at_tz=time_leak_value_datetime.tzinfo,
            )
            q_leak_value_m3 = t_utils.convert_leak_volume_m3(float(q_leak_leak_value))
            point_leak_value_round = round(float(point_leak_value), cfg.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка сигнала квитирования утечки", TestConst.ADDRESS_SUFFIX_ACK_LEAK, soft_failures).actual(
            ack_leak_value
        ).expected(TestConst.OUTPUT_IS_ACK_LEAK).equal_to()

        StepCheck("Проверка сигнала наличия утечки", TestConst.ADDRESS_SUFFIX_LEAK, soft_failures).actual(
            leak_value
        ).expected(TestConst.OUTPUT_IS_LEAK).equal_to()

        StepCheck("Проверка сигнала маскирования утечки", TestConst.ADDRESS_SUFFIX_MASK, soft_failures).actual(
            mask_leak_value
        ).expected(TestConst.OUTPUT_IS_NOT_MASK).equal_to()

        StepCheck("Проверка сигнала координаты утечки", TestConst.ADDRESS_SUFFIX_POINT_LEAK, soft_failures).actual(
            point_leak_value_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка сигнала объема утечки", TestConst.ADDRESS_SUFFIX_Q_LEAK, soft_failures).actual(
            q_leak_value_m3
        ).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )

        StepCheck("Проверка времени обнаружения утечки", TestConst.ADDRESS_SUFFIX_TIME_LEAK, soft_failures).actual(
            time_leak_value_datetime
        ).is_between(leak_wait_start_time, leak_wait_end_time)


async def lds_status_check_on_base_diagnostic_areas(ws_client, cfg: LDSStatusConfig, test_data: CaseData):
    """
    Проверка Инициализации и причины инициализации СОУ на базовых ДУ
    """
    # Распаковка данных для теста
    expected_lds_status, expected_lds_status_reasons = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает список базовых ДУ
        base_diagnostic_areas = t_utils.find_base_diagnostic_areas(flow_areas)
    for diagnostic_area in base_diagnostic_areas:
        StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
            diagnostic_area.ldsStatus
        ).expected(expected_lds_status).equal_to()
        lds_status_reasons = t_utils.parse_lds_status_reasons(
            diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons
        )
        StepCheck(f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons").contains(
            lds_status_reasons, expected_lds_status_reasons
        )


async def lds_status_check_on_representative(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData):
    """
    Проверка режима работы СОУ на показательных ДУ
    """
    # Распаковка данных для теста
    expected_result = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        flow_areas = parsed_payload.replyContent.flowAreas
        representative_diagnostic_areas = t_utils.find_representative_diagnostic_areas(flow_areas)
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in representative_diagnostic_areas}
        lds_status = t_utils.determine_lds_status_by_priority(lds_status_set)

    StepCheck(
        "Проверка режима работы СОУ на базовых ДУ",
        "ldsStatus",
    ).actual(
        lds_status
    ).expected(expected_result).equal_to()


async def lds_status_check_with_reasons(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData):
    """
    Проверка режима работы и причины режима СОУ на заданном ДУ
    """
    # Распаковка данных для теста
    diagnostic_area_id = test_data.params.get("diagnostic_area_id")
    expected_lds_status, expected_lds_status_reasons = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, diagnostic_area_id)
    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area.ldsStatus
    ).expected(expected_lds_status).equal_to()
    lds_status_reasons = t_utils.parse_lds_status_reasons(diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons)
    StepCheck(f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons").contains(
        lds_status_reasons, expected_lds_status_reasons
    )


async def lds_status_check_with_2_reasons(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData):
    """
    Проверка режима работы СОУ и двух причин режима работы СОУ на заданном ДУ
    """
    # Распаковка данных для теста
    diagnostic_area_id = test_data.params.get("diagnostic_area_id")
    expected_lds_status, expected_lds_status_reason_1, expected_lds_status_reason_2 = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, diagnostic_area_id)
    with SoftAssertions() as soft_failures:
        StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus", soft_failures).actual(
            diagnostic_area.ldsStatus
        ).expected(expected_lds_status).equal_to()
        lds_status_reasons = t_utils.parse_lds_status_reasons(
            diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons, soft_failures
        )
        StepCheck(
            f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
        ).contains(lds_status_reasons, expected_lds_status_reason_1)
        StepCheck(
            f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
        ).contains(lds_status_reasons, expected_lds_status_reason_2)


async def lds_and_stationary_status_check_with_reasons(
    ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData
):
    """
    Проверка режима работы и причины режима СОУ и МТ на заданном ДУ
    """
    # Распаковка данных для теста
    diagnostic_area_id = test_data.params.get("diagnostic_area_id")
    (
        expected_lds_status,
        expected_lds_status_reasons,
        expected_stationary_status,
        expected_stationary_status_reasons,
    ) = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, diagnostic_area_id)
    with SoftAssertions() as soft_failures:
        StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus", soft_failures).actual(
            diagnostic_area.ldsStatus
        ).expected(expected_lds_status).equal_to()
        lds_status_reasons = t_utils.parse_lds_status_reasons(
            diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons, soft_failures
        )
        StepCheck(
            f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
        ).contains(lds_status_reasons, expected_lds_status_reasons)
        StepCheck(
            f"Проверка режима работы МТ на ДУ с id:{diagnostic_area.id}", "stationaryStatus", soft_failures
        ).actual(diagnostic_area.stationaryStatus).expected(expected_stationary_status).equal_to()
        stationary_status_reasons = t_utils.parse_stationary_status_reasons(
            diagnostic_area.stationaryStatus, diagnostic_area.stationaryStatusReasons, soft_failures
        )
        StepCheck(
            f"Проверка причины режима работы МТ на ДУ с id:{diagnostic_area.id}",
            "stationaryStatusReasons",
            soft_failures,
        ).contains(stationary_status_reasons, expected_stationary_status_reasons)


async def lds_status_check_degradation_pig_sensor_passage(
    ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData
):
    """
    Проверка режима работы и причины режима СОУ на заданном ДУ, с командой на включение СОД
    """
    # Распаковка данных для теста
    diagnostic_area_id = test_data.params.get("diagnostic_area_id")
    pig_trap_id = test_data.params.get("pig_trap_id")
    expected_lds_status, expected_lds_status_reasons = test_data.expected_result

    with allure.step("Подключение по ws, отправка сообщения и обработка ответа о запуске СОД: LaunchPigRequest"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "LaunchPigRequest",
            {'pigTrapId': pig_trap_id, 'tuId': cfg.tu_id, 'timeToLaunch': 0, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_launch_pig_msg(payload)
        launch_pig_reply_status = parsed_payload.replyStatus
        time.sleep(cfg.basic_message_timeout)

    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, diagnostic_area_id)
    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area.ldsStatus
    ).expected(expected_lds_status).equal_to()
    lds_status_reasons = t_utils.parse_lds_status_reasons(diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons)
    StepCheck(f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons").contains(
        lds_status_reasons, expected_lds_status_reasons
    )
    StepCheck("Проверка кода ответа на запрос о запуске СОД", "replyStatus").actual(launch_pig_reply_status).expected(
        ReplyStatus.OK.value
    ).equal_to()


async def balance_algorithm_leak_waiting(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка подозрения утечки через BalanceAlgorithmResults

    Логика:
    - Подписка на BalanceAlgorithmResults однократно
    - Раз в BALANCE_ALGORITHM_POLL_INTERVAL секунд забираем из очереди свежее сообщение
    - Собираем все diagnosticAreas (только из flowAreas с непустым списком)
    - Проверяем, что на ДУ с утечкой хотя бы раз пришёл isLeakPossible=True
    - Проверяем, что на всех остальных ДУ isLeakPossible всегда False
    - Проверяем дебаланс на ДУ с будущей утечкой, дебаланс должен быть выше значения порога - 20%
    """
    poll_interval = TestConst.BALANCE_ALGORITHM_POLL_INTERVAL
    total_wait = TestConst.BALANCE_ALGORITHM_TOTAL_WAIT
    end_time = imitator_start_time + timedelta(
        seconds=leak.balance_algorithm_leak_waiting_test.offset * 60 + total_wait
    )

    leak_diagnostic_area_id = leak.leak_diagnostic_area_id
    if leak_diagnostic_area_id is None:
        pytest.fail("В датасете конфигурации утечки для данного набора данных не указан leak_diagnostic_area_id")

    with allure.step(
        f"Подписка и сбор BalanceAlgorithmResults раз в {poll_interval} с, в течение {total_wait} с после начала утечки"
    ):
        await t_utils.connect(
            ws_client,
            "SubscribeBalanceAlgorithmResultsRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        collected_diagnostic_areas = await t_utils.poll_balance_algorithm_diagnostic_areas(
            ws_client,
            parser,
            imitator_start_time,
            end_time,
            poll_interval,
        )
        leak_diagnostic_area_samples = t_utils.get_leak_diagnostic_area_samples(
            collected_diagnostic_areas,
            leak_diagnostic_area_id,
            total_wait,
        )

    with SoftAssertions() as soft_failures:
        is_leak_possible_seen = any(diagnostic_area.isLeakPossible for diagnostic_area in leak_diagnostic_area_samples)
        StepCheck(
            f"Проверка: на ДУ id={leak_diagnostic_area_id} с будущей утечкой хотя бы раз за "
            f"{TestConst.BALANCE_ALGORITHM_TOTAL_WAIT / 60} минут приходил"
            " статус 'подозрение на утечку': isLeakPossible=True",
            "isLeakPossible",
            soft_failures,
        ).actual(is_leak_possible_seen).expected(True).equal_to()

        foreign_with_possible = [
            diagnostic_area
            for diagnostic_area in collected_diagnostic_areas
            if diagnostic_area.id != leak_diagnostic_area_id and diagnostic_area.isLeakPossible
        ]
        if not cfg.has_multiple_leaks:
            StepCheck(
                "Проверка: на остальных ДУ, где утечка не ожидается isLeakPossible всегда False",
                "isLeakPossible_without_leak",
                soft_failures,
            ).actual(len(foreign_with_possible)).expected(0).equal_to()

        if leak.flow_rate_settings_threshold is not None:
            threshold = leak.flow_rate_settings_threshold
            tolerance = TestConst.DEBALANCE_TOLERANCE
            lower_bound = threshold * (1 - tolerance)

            for diagnostic_area in leak_diagnostic_area_samples:
                if diagnostic_area.isLeakPossible:
                    StepCheck(
                        f"Проверка значения дебаланса на ДУ id={leak_diagnostic_area_id} с будущей утечкой "
                        f"в пределах {int(tolerance * 100)}% снизу от порогового значения по объему: {threshold}).",
                        "debalance",
                        soft_failures,
                    ).actual(abs(diagnostic_area.debalance)).is_greater_than(lower_bound)


async def balance_algorithm_leak_detected(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Проверка наличия утечки (isLeakDetected) через BalanceAlgorithmResults.

    Логика:
    - Подписка на BalanceAlgorithmResultsContent
    - Получение первого подходящего сообщения типа BalanceAlgorithmResultsContent
    - Проверяем, что на ДУ с утечкой isLeakDetected=True
    - Проверяем, что на всех остальных ДУ isLeakDetected=False
    - Проверяем, что дебаланс на ДУ с утечкой > FLOW_RATE_SETTINGS_THRESHOLD
    """
    leak_diagnostic_area_id = leak.leak_diagnostic_area_id
    if leak_diagnostic_area_id is None:
        pytest.fail("В конфигурации утечки не задан leak_diagnostic_area_id")

    with allure.step("Подписка и получение BalanceAlgorithmResultsContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "BalanceAlgorithmResultsContent",
            "SubscribeBalanceAlgorithmResultsRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        parsed_payload = parser.parse_balance_algorithm_msg(payload)
        reply_content = parsed_payload.replyContent
        if not reply_content or not reply_content.flowAreas:
            pytest.fail(
                "В ответе с бэка в DTO BalanceAlgorithmResults отсутствуют flowAreas, "
                "невозможно проверить наличие утечки"
            )

        all_diagnostic_areas = []
        for flow_area in reply_content.flowAreas:
            if flow_area.diagnosticAreas:
                all_diagnostic_areas.extend(flow_area.diagnosticAreas)

        if not all_diagnostic_areas:
            pytest.fail(
                "В ответе с бэка в DTO BalanceAlgorithmResults во всех flowAreas отсутствуют diagnosticAreas, "
                "невозможно проверить наличие утечки"
            )

        leak_diagnostic_area = next(
            (
                diagnostic_area
                for diagnostic_area in all_diagnostic_areas
                if diagnostic_area.id == leak_diagnostic_area_id
            ),
            None,
        )
        if leak_diagnostic_area is None:
            pytest.fail(
                f"ДУ с id={leak_diagnostic_area_id} не найден в ответе BalanceAlgorithmResultsContent,"
                "невозможно проверить наличие утечки"
            )

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка: на ДУ id={leak_diagnostic_area_id} обнаружена утечка",
            "isLeakDetected",
            soft_failures,
        ).actual(leak_diagnostic_area.isLeakDetected).expected(True).equal_to()

        foreign_with_detected = [
            diagnostic_area
            for diagnostic_area in all_diagnostic_areas
            if diagnostic_area.id != leak_diagnostic_area_id and diagnostic_area.isLeakDetected
        ]
        if not cfg.has_multiple_leaks:
            StepCheck(
                "Проверка: на остальных ДУ не обнаружена утечка, "
                f" количество ДУ с неправильным статусом: {len(foreign_with_detected)}, "
                f"их id: {[diagnostic_area.id for diagnostic_area in foreign_with_detected]})",
                "isLeakDetected_without_leak",
                soft_failures,
            ).actual(len(foreign_with_detected)).expected(0).equal_to()

        if leak.flow_rate_settings_threshold is not None:
            threshold = leak.flow_rate_settings_threshold
            StepCheck(
                f"Дебаланс на ДУ id={leak_diagnostic_area_id} по модулю больше порога для данного режима МТ:"
                f" {threshold}",
                "debalance",
                soft_failures,
            ).actual(abs(leak_diagnostic_area.debalance)).is_greater_than(threshold)


# ===== Сценарии отбраковки сигналов =====
async def rejection_input_signals(ws_client, cfg: IsRejectedConfig, rejection_case: RejectionTestCase):
    """
    Проверка отбраковки сигнала по подписке SubscribeInputSignalsRequest.
    Проверяет isRejected=True для указанного датчика.
    """
    sensor = rejection_case.sensor
    with allure.step(
        f"Подключение по ws, получение данных InputSignalsContent для датчика {sensor.description} (id={sensor.id})"
    ):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [sensor.id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_input_signals_info_msg(payload)
        sensor_data = parsed_payload.replyContent.inputSignals
        target_signal = t_utils.find_object_by_field(sensor_data, "id", sensor.id)

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка отбраковки датчика {sensor.description} (id={sensor.id})", "isRejected", soft_failures
        ).actual(target_signal.isRejected).expected(True).equal_to()


async def rejection_journal(
    ws_client, cfg: IsRejectedConfig, rejection_case: RejectionTestCase, imitator_start_time
):
    """
    Проверка наличия записи об отбраковке в журнале по GetMessagesRequest.
    """
    sensor = rejection_case.sensor
    with allure.step("Запрос сообщений журнала с фильтром messageTypes=REJECTION"):
        end_time = datetime.now()
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(
                messageTypes=int(MessageType.REJECTION),
                objects=FilteringObjects(tuId=cfg.tu_id),
            ),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и technologicalSection"):
        filter_start_msk = t_utils.localize_as_moscow(imitator_start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)

        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)

        target_msg = next(
            (
                msg
                for msg in time_filtered
                if msg.technologicalSection == cfg.tu_name and msg.tag == sensor.description
            ),
            None,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n"
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и tag='{sensor.description}' (id={sensor.id}): {'True' if target_msg else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(
        f"Проверка: найдено ли сообщение с tag='{sensor.description}' (id={sensor.id}) "
        f"и technologicalSection='{cfg.tu_name}'"
    ):
        if target_msg is None:
            pytest.fail(
                f"Сообщение с technologicalSection='{cfg.tu_name}' и tag='{sensor.description}' (id={sensor.id}) "
                f"не найдено среди {len(time_filtered)} отфильтрованных по времени сообщений"
            )

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(
            target_msg.mainPipeline
        ).expected(cfg.main_pipeline).equal_to()

        StepCheck("Проверка messageType", "messageType", soft_failures).actual(
            target_msg.messageType
        ).expected(TestConst.JOURNAL_MESSAGE_TYPE_REJECTION).equal_to()

        StepCheck("Проверка technologicalSection не пустой", "technologicalSection", soft_failures).actual(
            target_msg.technologicalSection
        ).is_not_none()

        StepCheck("Проверка technologicalObject не пустой", "technologicalObject", soft_failures).actual(
            target_msg.technologicalObject
        ).is_not_none()

        StepCheck(f"Проверка tag для {sensor.description} (id={sensor.id})", "tag", soft_failures).actual(
            target_msg.tag
        ).expected(sensor.description).equal_to()

        if rejection_case.expected_signal_name:
            StepCheck("Проверка signalName", "signalName", soft_failures).actual(
                target_msg.signalName
            ).expected(rejection_case.expected_signal_name).equal_to()

        if rejection_case.expected_event:
            StepCheck("Проверка event", "event", soft_failures).actual(
                target_msg.event
            ).expected(rejection_case.expected_event).equal_to()


async def rejection_main_page(ws_client, cfg: IsRejectedConfig):
    """
    Проверка numberOfRejectedSignals > 0 по подписке subscribeMainPageSignalsInfoRequest.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageSignalsInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageSignalsInfoContent",
            "subscribeMainPageSignalsInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_signals_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck(
            f"Проверка numberOfRejectedSignals > 0 для ТУ {cfg.tu_name}",
            "numberOfRejectedSignals",
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfRejectedSignals
        ).is_greater_than(0)


async def rejection_scheme_signals_state(
    ws_client, cfg: IsRejectedConfig, rejection_case: RejectionTestCase
):
    """
    Проверка отбраковки сигнала по подписке SubscribeSchemeSignalsStateRequest.
    Проверяет isRejected, isMasked, isImitated и rejection.criteriaNames.
    """
    sensor = rejection_case.sensor
    with allure.step(
        f"Подключение по ws, получение данных SchemeSignalsStateContent для датчика {sensor.description} (id={sensor.id})"
    ):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "SchemeSignalsStateContent",
            "SubscribeSchemeSignalsStateRequest",
            {'tuId': cfg.tu_id},
        )
        parsed_payload = parser.parse_scheme_signals_state_msg(payload)
        signals = parsed_payload.replyContent.signalsStates

        target_signal = next(
            (signal for signal in signals if signal.id == sensor.id),
            None,
        )

        allure.attach(
            f"Всего сигналов получено: {len(signals)}\n"
            f"Поиск сигнала с id={sensor.id} ({sensor.description}): "
            f"{'Найден' if target_signal else 'Не найден'}",
            name="Результат поиска сигнала в SchemeSignalsState",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(f"Проверка: найден ли сигнал с id={sensor.id} ({sensor.description})"):
        if target_signal is None:
            pytest.fail(
                f"Сигнал с id={sensor.id} ({sensor.description}) "
                f"не найден среди {len(signals)} полученных сигналов"
            )

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка isRejected для {sensor.description} (id={sensor.id})", "isRejected", soft_failures
        ).actual(target_signal.isRejected).expected(True).equal_to()

        StepCheck(
            f"Проверка isMasked для {sensor.description} (id={sensor.id})", "isMasked", soft_failures
        ).actual(target_signal.isMasked).expected(False).equal_to()

        StepCheck(
            f"Проверка isImitated для {sensor.description} (id={sensor.id})", "isImitated", soft_failures
        ).actual(target_signal.isImitated).expected(False).equal_to()

        if target_signal.rejection is not None:
            StepCheck(
                f"Проверка rejection.criteriaNames для {sensor.description} (id={sensor.id})",
                "criteriaNames",
                soft_failures,
            ).actual(
                target_signal.rejection.get('criteriaNames') if isinstance(target_signal.rejection, dict) else None
            ).expected(rejection_case.expected_criteria_names).equal_to()
