"""
Сценарии тестов - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import time

import allure

from constants.enums import ConfirmationStatus, LdsStatus, ReplyStatus, ReservedType
from constants.test_constants import (
    ADDRESS_SUFFIX_ACK_LEAK,
    ADDRESS_SUFFIX_LEAK,
    ADDRESS_SUFFIX_MASK,
    ADDRESS_SUFFIX_POINT_LEAK,
    ADDRESS_SUFFIX_Q_LEAK,
    ADDRESS_SUFFIX_TIME_LEAK,
    COLUMN_SELECTION_DEF,
    FLOW_SIGNAL_TYPE,
    FLOWMETER_OBJECT_TYPE,
    LEAK_LINEAR_PART_ID_KEY,
    OUTPUT_IS_ACK_LEAK,
    OUTPUT_IS_LEAK,
    OUTPUT_IS_NOT_MASK,
    PRESSURE_SENSOR_OBJECT_TYPE,
    PRESSURE_SIGNAL_TYPE,
)
from test_config.models import LeakTestConfig, SuiteConfig
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


async def basic_info(ws_client, cfg: SuiteConfig):
    """
    Проверка базовой информации СОУ: список ТУ.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: BasicInfoContent"):
        payload = await t_utils.connect_and_get_msg(ws_client, "getBasicInfoRequest", [])
        parsed_payload = parser.parse_basic_info_msg(payload)
        expected_tu = [(cfg.tu_id, cfg.tu_name)]
        actual_tu = [
            (tu.tuId, tu.tuName) for tu in parsed_payload.replyContent.basicInfo.tus if tu.tuId == cfg.tu_id
        ]

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка статуса ответа", "replyStatus", soft_failures).actual(
            parsed_payload.replyStatus
        ).expected(ReplyStatus.OK.value).equal_to()

        StepCheck("Проверка наличия объектов в списке ТУ", "tus", soft_failures).actual(
            parsed_payload.replyContent.basicInfo.tus
        ).is_not_empty()

        StepCheck(
            f"Проверка наличия ТУ: {cfg.tu_name} в списке ТУ ",
            "(tuId, tuName)",
            soft_failures,
        ).actual(actual_tu).expected(expected_tu).equal_to()


async def journal_info(ws_client, cfg: SuiteConfig):
    """
    Проверка наличия сообщений в журнале.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetMessagesRequest",
            {
                'pagination': {'limit': 50, 'direction': 3},
                'sorting': {'sortingParam': 1, 'sortingType': 2},
                'columnsSelection': COLUMN_SELECTION_DEF,
            },
        )
        parsed_payload = parser.parse_journal_msg(payload)

    StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(
        parsed_payload.replyContent.messagesInfo
    ).is_not_empty()


async def lds_status_initialization(ws_client, cfg: SuiteConfig):
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
        flow_areas = parsed_payload.replyContent.flowAreas
        longest_flow_area = t_utils.get_longest_flow_area(flow_areas)
        diagnostic_areas = longest_flow_area.diagnosticAreas
        allure.attach(
            f"Cамый протяженный участок карты течений: {longest_flow_area}",
            name="flowArea. Инициализация",
            attachment_type=allure.attachment_type.TEXT,
        )
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in diagnostic_areas}
        lds_status = t_utils.determine_lds_status_by_priority(lds_status_set)

    StepCheck("Проверка режима работы СОУ", "ldsStatus").actual(lds_status).expected(
        LdsStatus.INITIALIZATION.value
    ).equal_to()


async def main_page_info(ws_client, cfg: SuiteConfig):
    """
    Проверка установки режима стационара/остановленной перекачки.
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
        ).actual(parsed_payload.replyContent.tuInfo.stationaryStatus).expected(
            cfg.expected_stationary_status
        ).equal_to()


async def mask_signal_msg(ws_client, cfg: SuiteConfig):
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
        pressure_sensor_list = [
            sensor
            for sensor in parsed_payload.replyContent
            if sensor.signalType == PRESSURE_SIGNAL_TYPE and sensor.objectType == PRESSURE_SENSOR_OBJECT_TYPE
        ]
        flowmeter_list = [
            sensor
            for sensor in parsed_payload.replyContent
            if sensor.signalType == FLOW_SIGNAL_TYPE and sensor.objectType == FLOWMETER_OBJECT_TYPE
        ]
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


async def lds_status_initialization_out(ws_client, cfg: SuiteConfig):
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
    ).actual(lds_status).expected(LdsStatus.INITIALIZATION.value).is_not_equal_to()


async def leaks_content(ws_client, cfg: SuiteConfig, leak: LeakTestConfig, imitator_start_time):
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
            leak_info = t_utils.find_object_by_field(
                leaks_list_info, "diagnosticAreaName", leak.diagnostic_area_name
            )
        else:
            leak_info = leaks_list_info[0]

        # Конвертируем время обнаружения в московское время
        leak_detected_at = t_utils.ensure_moscow_timezone(leak_info.detectedAt)
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            leak.leak_start_interval_seconds,
            leak.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(leak_info.leakVolume)
        leak_coordinate_round = round(leak_info.leakCoordinate, cfg.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        if leak.diagnostic_area_name:
            StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
                leak_info.diagnosticAreaName
            ).expected(leak.diagnostic_area_name).equal_to()
        else:
            StepCheck("Проверка наличия названия участка утечки", "diagnosticAreaName", soft_failures).actual(
                leak_info.diagnosticAreaName
            ).is_not_none()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            leak_info.confirmationStatus
        ).expected(ConfirmationStatus.CONFIRMED.value).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(
            leak_info.type
        ).expected(ReservedType.UNSTATIONARY_FLOW.value).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(leak_info.id).is_not_none()

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


async def all_leaks_info(ws_client, cfg: SuiteConfig, leak: LeakTestConfig, imitator_start_time):
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
            first_leak_info = t_utils.find_object_by_field(
                leaks_info, "diagnosticAreaName", leak.diagnostic_area_name
            )
        else:
            first_leak_info = leaks_info[0]

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


async def tu_leaks_info(ws_client, cfg: SuiteConfig, leak: LeakTestConfig, imitator_start_time):
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
        # Если у утечки указан controlledSiteId - ищем по нему, иначе берём первую
        if leak.control_site_id:
            first_leak_info = t_utils.find_object_by_field(
                tu_leaks_info_list, "controlledSiteId", leak.control_site_id
            )
        else:
            first_leak_info = tu_leaks_info_list[0]

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

        if leak.control_site_id:
            StepCheck("Проверка наличия id участка утечки", "controlledSiteId", soft_failures).actual(
                first_leak_info.controlledSiteId
            ).expected(leak.control_site_id).equal_to()
        else:
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


async def lds_status_during_leak(ws_client, cfg: SuiteConfig):
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

    status_config = cfg.lds_status_during_leak_config

    leak_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, status_config.diagnostic_area_id)
    in_neighbor_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, status_config.in_neighbor_id)
    out_neighbor_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, status_config.out_neighbor_id)

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка режима работы СОУ на ДУ с утечкой, id ДУ: {status_config.diagnostic_area_id}",
            "ldsStatus",
            soft_failures,
        ).actual(leak_diagnostic_area.ldsStatus).expected(status_config.expected_lds_status).equal_to()

        StepCheck(
            f"Проверка режима работы СОУ на соседнем ДУ, id ДУ: {status_config.in_neighbor_id}",
            "ldsStatus",
            soft_failures,
        ).actual(in_neighbor_diagnostic_area.ldsStatus).expected(status_config.in_neighbor_status).equal_to()

        StepCheck(
            f"Проверка режима работы СОУ на соседнем ДУ, id ДУ: {status_config.out_neighbor_id}",
            "ldsStatus",
            soft_failures,
        ).actual(out_neighbor_diagnostic_area.ldsStatus).expected(status_config.out_neighbor_status).equal_to()

        # Для select_7 есть дополнительный 4-й ДУ
        if status_config.out_neighbor_2_id and status_config.out_neighbor_2_status:
            out_neighbor_2_diagnostic_area = t_utils.find_diagnostic_area_by_id(
                flow_areas, status_config.out_neighbor_2_id
            )
            StepCheck(
                f"Проверка режима работы СОУ на соседнем ДУ, id ДУ: {status_config.out_neighbor_2_id}",
                "ldsStatus",
                soft_failures,
            ).actual(out_neighbor_2_diagnostic_area.ldsStatus).expected(
                status_config.out_neighbor_2_status
            ).equal_to()


async def acknowledge_leak_info(ws_client, cfg: SuiteConfig, leak: LeakTestConfig = None):
    """
    Проверка квитирования утечки.
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
            if leak and leak.control_site_id:
                first_leak_info = t_utils.find_object_by_field(
                    leaks_info, "controlledSiteId", leak.control_site_id
                )
            else:
                first_leak_info = leaks_info[0]

            leak_id = str(first_leak_info.id)

    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': leak_id, 'tuId': cfg.tu_id, 'additionalProperties': None},
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
        leaks_info = parsed_payload.replyContent.leaksInfo

    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(
        acknowledge_reply_status
    ).expected(ReplyStatus.OK.value).equal_to()

    StepCheck("Проверка отсутствия сообщений об утечке после квитирования", "leaksInfo").actual(leaks_info).is_empty()


async def output_signals(ws_client, cfg: SuiteConfig, leak: LeakTestConfig, imitator_start_time):
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
        leak_linear_part = t_utils.find_object_by_field(
            parsed_payload.replyContent.linearPartSignals,
            LEAK_LINEAR_PART_ID_KEY,
            linear_part_id,
        )

        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, ADDRESS_SUFFIX_ACK_LEAK
            )
            leak_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, ADDRESS_SUFFIX_LEAK)
            mask_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, ADDRESS_SUFFIX_MASK)
            point_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, ADDRESS_SUFFIX_POINT_LEAK
            )
            q_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, ADDRESS_SUFFIX_Q_LEAK
            )
            time_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, ADDRESS_SUFFIX_TIME_LEAK
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
                LEAK_LINEAR_PART_ID_KEY,
                linear_part_id,
            )

        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, ack_leak_signal_type)
            leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, leak_signal_type)
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)
            point_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, point_leak_signal_type)
            q_leak_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, q_leak_signal_type)
            time_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, time_leak_signal_type)

            StepCheck("Проверка наличия времени утечки", ADDRESS_SUFFIX_TIME_LEAK).actual(
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
        StepCheck("Проверка сигнала квитирования утечки", ADDRESS_SUFFIX_ACK_LEAK, soft_failures).actual(
            ack_leak_value
        ).expected(OUTPUT_IS_ACK_LEAK).equal_to()

        StepCheck("Проверка сигнала наличия утечки", ADDRESS_SUFFIX_LEAK, soft_failures).actual(
            leak_value
        ).expected(OUTPUT_IS_LEAK).equal_to()

        StepCheck("Проверка сигнала маскирования утечки", ADDRESS_SUFFIX_MASK, soft_failures).actual(
            mask_leak_value
        ).expected(OUTPUT_IS_NOT_MASK).equal_to()

        StepCheck("Проверка сигнала координаты утечки", ADDRESS_SUFFIX_POINT_LEAK, soft_failures).actual(
            point_leak_value_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка сигнала объема утечки", ADDRESS_SUFFIX_Q_LEAK, soft_failures).actual(
            q_leak_value_m3
        ).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )

        StepCheck("Проверка времени обнаружения утечки", ADDRESS_SUFFIX_TIME_LEAK, soft_failures).actual(
            time_leak_value_datetime
        ).is_between(leak_wait_start_time, leak_wait_end_time)

