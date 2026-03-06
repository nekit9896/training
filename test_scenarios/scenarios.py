"""
Сценарии тестов - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import asyncio
import time
from datetime import datetime, timedelta

import allure
import pytest

from constants.enums import Direction, LdsStatus, MessageType, ReplyStatus, StationaryStatus, InitializationLdsStatusReasons
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import Filtering, Pagination
from test_config.models_for_tests import LDSStatusConfig, LeakTestConfig, SmokeSuiteConfig
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


async def basic_info(ws_client, cfg: SmokeSuiteConfig):
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

        # Ищем утечку по имени ДУ или берём первую
        if leak.diagnostic_area_name:
            first_leak_info = t_utils.find_object_by_field(
                leaks_list_info, "diagnosticAreaName", leak.diagnostic_area_name
            )
        else:
            first_leak_info = leaks_list_info[0]
            StepCheck(
                "Проверка: пришла хотя бы одна утечка",
                "leak",
            ).actual(first_leak_info).is_not_none()
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

        if leak.diagnostic_area_name:
            StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
                first_leak_info.diagnosticAreaName
            ).expected(leak.diagnostic_area_name).equal_to()
        else:
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


async def leak_info_in_journal(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=1, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LEAKS)),
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
        if leak.diagnostic_area_name:
            first_leak_info = t_utils.find_object_by_field(leaks_info, "diagnosticAreaName", leak.diagnostic_area_name)
        else:
            first_leak_info = leaks_info[0]
            StepCheck(
                "Проверка: пришла хотя бы одна утечка",
                "leakInfo",
            ).actual(first_leak_info).is_not_none()

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

        if leak.diagnostic_area_name:
            StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
                first_leak_info.diagnosticAreaName
            ).expected(leak.diagnostic_area_name).equal_to()
        else:
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

    leak_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, status_config.diagnostic_area_id)

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка режима работы СОУ на ДУ с утечкой, id ДУ: {status_config.diagnostic_area_id}",
            "ldsStatus",
            soft_failures,
        ).actual(leak_diagnostic_area.ldsStatus).expected(status_config.expected_lds_status).equal_to()

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

            # Для multi-leak ищем по control_site_id или diagnostic_area_name
            if leak and leak.control_site_id:
                leak_to_ack = t_utils.find_object_by_field(leaks_info, "controlledSiteId", leak.control_site_id)
            else:
                leak_to_ack = leaks_info[0]
                StepCheck(
                    "Проверка: пришла хотя бы одна утечка",
                    "leakInfo",
                ).actual(leak_to_ack).is_not_none()

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


async def leaks_content_end(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка завершенной утечки через сообщение LeaksContent.
    Проверяется только confirmationStatus на значения confirmed и closed.
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

        # Ищем утечку по имени ДУ или берём первую
        if leak.diagnostic_area_name:
            first_leak_info = t_utils.find_object_by_field(
                leaks_list_info, "diagnosticAreaName", leak.diagnostic_area_name
            )
        else:
            first_leak_info = leaks_list_info[0]
            StepCheck(
                "Проверка: пришла хотя бы одна утечка",
                "leak",
            ).actual(first_leak_info).is_not_none()

    with SoftAssertions() as soft_failures:
        # Проверка confirmationStatus
        StepCheck(
            "Проверка статуса утечки: должен быть подтверждена и завершена", "confirmationStatus", soft_failures
        ).actual(first_leak_info.confirmationStatus).expected(leak.expected_leak_completed_status).equal_to()


async def lds_status_initialization_check_with_reasons(ws_client, cfg: LDSStatusConfig):
    """
    Проверка Инициализации и причины инициализации СОУ на базовых ДУ
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
        base_diagnostic_areas = t_utils.find_base_diagnostic_areas(flow_areas)
        with allure.step(f"Причины режима СОУ{base_diagnostic_areas}"):
            pass
        for diagnostic_area in base_diagnostic_areas:
            StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
                diagnostic_area.ldsStatus
            ).expected(LdsStatus.INITIALIZATION.value).equal_to()
            lds_status_reasons = t_utils.parse_lds_status_reasons(
                diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons
            )
            StepCheck(
                f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons"
            ).contains(lds_status_reasons, InitializationLdsStatusReasons.LDS_COLD_START)

async def balance_algorithm_leak_detected(
    ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time: datetime,
):
    """
    Проверка наличия утечки (isLeakDetected) через BalanceAlgorithmResults.

    Логика:
    1. Подписка на BalanceAlgorithmResultsContent (однократно).
    2. Получение первого подходящего сообщения.
    3. Проверяем, что на ДУ с утечкой isLeakDetected=True.
    4. Проверяем, что на всех остальных ДУ isLeakDetected=False.
    5. Проверяем, что |debalance| на ДУ с утечкой > FLOW_RATE_SETTINGS_THRESHOLD.
    """
    leak_da_id = leak.leak_diagnostic_area_id
    if leak_da_id is None:
        pytest.fail(
            "В конфигурации утечки не задан leak_diagnostic_area_id "
            "(проверьте lds_status_during_leak_config)"
        )

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
        pytest.fail("В ответе BalanceAlgorithmResultsContent отсутствуют flowAreas")

    all_diagnostic_areas = []
    for flow_area in reply_content.flowAreas:
        if flow_area.diagnosticAreas:
            all_diagnostic_areas.extend(flow_area.diagnosticAreas)

    if not all_diagnostic_areas:
        pytest.fail("Во всех flowAreas отсутствуют diagnosticAreas")

    leak_da = next(
        (da for da in all_diagnostic_areas if da.id == leak_da_id), None,
    )
    if leak_da is None:
        pytest.fail(f"ДУ с id={leak_da_id} не найден в ответе BalanceAlgorithmResultsContent")

    with allure.step("Верификация BalanceAlgorithmResults: isLeakDetected"):
        with SoftAssertions() as soft_failures:
            StepCheck(
                f"На ДУ id={leak_da_id} обнаружена утечка: isLeakDetected=True",
                "isLeakDetected",
                soft_failures,
            ).actual(leak_da.isLeakDetected).expected(True).equal_to()

            foreign_with_detected = [
                da for da in all_diagnostic_areas
                if da.id != leak_da_id and da.isLeakDetected
            ]
            StepCheck(
                f"На остальных ДУ isLeakDetected=False "
                f"(нарушителей: {len(foreign_with_detected)}, "
                f"id: {[da.id for da in foreign_with_detected]})",
                "isLeakDetected_other",
                soft_failures,
            ).actual(len(foreign_with_detected)).expected(0).equal_to()

            if leak.flow_rate_settings_threshold is not None:
                threshold = leak.flow_rate_settings_threshold
                StepCheck(
                    f"Дебаланс на ДУ id={leak_da_id} по модулю "
                    f"строго больше порога {threshold}",
                    "debalance",
                    soft_failures,
                ).actual(abs(leak_da.debalance)).is_greater_than(threshold)


async def balance_algorithm_leak_waiting(
    ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time: datetime,
):
    """
    Проверка подозрения утечки через BalanceAlgorithmResults.

    Логика:
    1. Подписка на BalanceAlgorithmResultsContent (однократно).
    2. Раз в BALANCE_ALGORITHM_POLL_INTERVAL секунд забираем из очереди самое свежее сообщение.
    3. Собираем diagnosticAreas (только из flowAreas с непустым списком).
    4. Проверяем, что на ДУ с утечкой хотя бы раз пришёл isLeakPossible=True.
    5. Проверяем, что на всех остальных ДУ isLeakPossible всегда False.
    6. Проверяем дебаланс на ДУ с утечкой через is_between (±DEBALANCE_TOLERANCE от порога).
    """
    poll_interval = TestConst.BALANCE_ALGORITHM_POLL_INTERVAL
    total_wait = TestConst.BALANCE_ALGORITHM_TOTAL_WAIT
    total_wait_minutes = total_wait // 60
    end_time = imitator_start_time + timedelta(seconds=leak.leak_start_interval_seconds + total_wait)

    leak_da_id = leak.leak_diagnostic_area_id
    if leak_da_id is None:
        pytest.fail(
            "В конфигурации утечки не задан leak_diagnostic_area_id "
        )

    with allure.step(
        f"Подписка и сбор BalanceAlgorithmResults "
        f"раз в {poll_interval} с, в течение {total_wait} с после начала утечки"
    ):
        await t_utils.connect(
            ws_client,
            "SubscribeBalanceAlgorithmResultsRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        collected_diagnostic_areas = await t_utils.poll_balance_algorithm_diagnostic_areas(
            ws_client, imitator_start_time, end_time, poll_interval,
        )
        leak_da_samples = t_utils.get_leak_da_samples(
            collected_diagnostic_areas, leak_da_id, total_wait,
        )

    with SoftAssertions() as soft_failures:
        is_leak_possible_seen = any(diagnostic_area.isLeakPossible for diagnostic_area in leak_da_samples)
        StepCheck(
            f"Проверка: на ДУ id={leak_da_id} с будущей утечкой хотя бы раз за 10 минут приходил статус 'подозрение на утечку': isLeakPossible=True",
            "isLeakPossible",
            soft_failures,
        ).actual(is_leak_possible_seen).expected(True).equal_to()

        foreign_with_possible = [
            diagnostic_area for diagnostic_area in collected_diagnostic_areas if diagnostic_area.id != leak_da_id and diagnostic_area.isLeakPossible
        ]
        StepCheck(
            "Проверка: на остальных ДУ isLeakPossible всегда False",
            "isLeakPossible_other",
            soft_failures,
        ).actual(len(foreign_with_possible)).expected(0).equal_to()

        if leak.flow_rate_settings_threshold is not None:
            threshold = leak.flow_rate_settings_threshold
            tolerance = TestConst.DEBALANCE_TOLERANCE
            lower_bound = threshold * (1 - tolerance)
            upper_bound = threshold * (1 + tolerance)

            for diagnostic_area in leak_da_samples:
                if diagnostic_area.isLeakPossible:
                    StepCheck(
                        f"Проверка дебаланса на ДУ id={leak_da_id} "
                        f"(±{int(tolerance * 100)}% от порога {threshold})",
                        "debalance",
                        soft_failures,
                    ).actual(abs(diagnostic_area.debalance)).is_between(lower_bound, upper_bound)
