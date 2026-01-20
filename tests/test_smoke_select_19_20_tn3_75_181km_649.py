import time
from datetime import datetime

import allure
import pytest

from constants.expectations.select_19_expectations import Select19Expected as Exp
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser

pytestmark = [
    pytest.mark.test_suite_name(Exp.TEST_SUITE_NAME_VAL),
    pytest.mark.test_suite_data_id(66),
    pytest.mark.test_data_name(Exp.TEST_DATA_ARCH_NAME_VAL),
]


@allure.title("[BasicInfo] Проверка базовой информации СОУ: список ТУ")
@allure.tag("getBasicInfoRequest")
@pytest.mark.test_case_id("1")
@pytest.mark.offset(1)
@pytest.mark.asyncio
async def test_basic_info(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: BasicInfoContent"):
        payload = await t_utils.connect_and_get_msg(ws_client, "getBasicInfoRequest", [])
        parsed_payload = parser.parse_basic_info_msg(payload)
        expected_tu = [(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description)]
        actual_tu = [
            (tu.tuId, tu.tuName)
            for tu in parsed_payload.replyContent.basicInfo.tus
            if tu.tuId == Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id
        ]

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка статуса ответа", "replyStatus", soft_failures).actual(parsed_payload.replyStatus).expected(
            Exp.REPLY_STATUS.OK.value
        ).equal_to()

        StepCheck("Проверка наличия объектов в списке ТУ", "tus", soft_failures).actual(
            parsed_payload.replyContent.basicInfo.tus
        ).is_not_empty()

        StepCheck(
            f"Проверка наличия ТУ: {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description} в списке ТУ ",
            "(tuId, tuName)",
            soft_failures,
        ).actual(actual_tu).expected(expected_tu).equal_to()


@allure.description(
    "Проверка сообщения MessagesInfo.\n" "Синхронный запрос для проверки наличия сообщений в поле 'messageInfo'"
)
@allure.title("[MessagesInfo] Проверка наличия сообщений в журнале")
@allure.tag("GetMessagesRequest")
@pytest.mark.test_case_id("2")
@pytest.mark.offset(5)
@pytest.mark.asyncio
async def test_journal_info(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetMessagesRequest",
            {
                'pagination': {'limit': 50, 'direction': 3},
                'sorting': {'sortingParam': 1, 'sortingType': 2},
                'columnsSelection': Exp.COLUMN_SELECTION_DEF,
            },
        )
        parsed_payload = parser.parse_journal_msg(payload)

    StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(
        parsed_payload.replyContent.messagesInfo
    ).is_not_empty()


@allure.description(
    "Проверка режима работы СОУ в сообщении типа: CommonScheme "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Время проведения проверки : ~05:00\n"
    "Ожидаемый режим работы СОУ : Инициализация\n"
)
@allure.title(f"[CommonScheme] Проверка режима работы СОУ: 'Инициализация' на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("SubscribeCommonSchemeRequest")
@pytest.mark.test_case_id("29")
@pytest.mark.offset(5)
@pytest.mark.asyncio
async def test_lds_status_initialization(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        # Получает список участков карты течения
        flow_areas = parsed_payload.replyContent.flowAreas
        # Получает самый протяженный участок карты течения
        longest_flow_area = t_utils.get_longest_flow_area(flow_areas)
        # Получает список ДУ
        diagnostic_areas = longest_flow_area.diagnosticAreas
        allure.attach(
            f"Cамый протяженный участок карты течений: {longest_flow_area}",
            name="flowArea. Инициализация",
            attachment_type=allure.attachment_type.TEXT,
        )
        # Получает коллекцию статусов списка ДУ
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in diagnostic_areas}
        # Определяет режим работы СОУ по приоритету
        lds_status = t_utils.determine_lds_status_by_priority(lds_status_set)
    StepCheck("Проверка режима работы СОУ", "ldsStatus").actual(lds_status).expected(
        Exp.LDS_STATUS.INITIALIZATION.value
    ).equal_to()


@allure.description(
    "Проверка сообщения MainPageInfo "
    f"об установке режима Стационар на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое время установки режима Стационар : ~05:00\n"
)
@allure.title(f"[MainPageInfo] Проверка установки стационара на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeMainPageInfoRequest")
@pytest.mark.test_case_id("3")
@pytest.mark.offset(7)
@pytest.mark.asyncio
async def test_main_page_info_stationary(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck(
            f"Проверка установки стационара для ТУ {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}",
            "stationary_status",
            soft_failures,
        ).actual(parsed_payload.replyContent.tuInfo.stationaryStatus).expected(
            Exp.STATIONARY_STATUS.STATIONARY.value
        ).equal_to()


@allure.description(
    "Проверка работы маскирования и снятия маскирования через синхронные запросы типа: "
    f"MaskSignalRequest и UnmaskSignalRequest, на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Проверки:\n"
    "Статус-код ответа на синхронный запрос MaskSignalRequest.\n"
    "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
    "Статус-код ответа на синхронный запрос UnmaskSignalRequest.\n"
    "Значение в поле isMasked сигнала в запросе InputSignalsContent после маскирования.\n"
    "Примечание: что бы не повлиять на проверки утечек, тест на маскирование выполняется во время инициализации."
)
@allure.title(f"[MaskSignal] проверка маскирования датчиков на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("MaskSignalRequest")
@pytest.mark.test_case_id("32")
@pytest.mark.offset(8.0)
@pytest.mark.asyncio
async def test_mask_signal_msg(ws_client):
    with allure.step("Подключение по ws, получение и обработка данных датчиков давления и расхода"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetInputSignalsRequest",
            {
                'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
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
            if sensor.signalType == Exp.PRESSURE_SIGNAL_TYPE and sensor.objectType == Exp.PRESSURE_SENSOR_OBJECT_TYPE
        ]
        # Получает список расходомеров
        flowmeter_list = [
            sensor
            for sensor in parsed_payload.replyContent
            if sensor.signalType == Exp.FLOW_SIGNAL_TYPE and sensor.objectType == Exp.FLOWMETER_OBJECT_TYPE
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
                {'id': pressure_sensor.id, 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_mask_signal_msg(payload)
            pressure_sensor_mask_reply_status = parsed_payload.replyStatus
            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                pressure_sensor_mask_reply_status
            ).expected(Exp.REPLY_STATUS.OK.value).equal_to()
        with allure.step(f"Отправка сообщения и обработка ответа о маскировании расходомера с id: {flowmeter.id}"):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "MaskSignalRequest",
                {'id': flowmeter.id, 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_mask_signal_msg(payload)
            flowmeter_mask_reply_status = parsed_payload.replyStatus
            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                flowmeter_mask_reply_status
            ).expected(Exp.REPLY_STATUS.OK.value).equal_to()
    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчиков из сообщения типа: InputSignalsContent"
    ):
        time.sleep(Exp.BASIC_MESSAGE_TIMEOUT)
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [pressure_sensor.id, flowmeter.id],
                'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
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
                {'id': pressure_sensor.id, 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_unmask_signal_msg(payload)
            pressure_sensor_unmask_reply_status = parsed_payload.replyStatus
            StepCheck("Проверка кода ответа на запрос о снятии маскирования", "replyStatus").actual(
                pressure_sensor_unmask_reply_status
            ).expected(Exp.REPLY_STATUS.OK.value).equal_to()
        with allure.step(
            f"Отправка сообщения и обработка ответа о снятии маскирования расходомера с id: {flowmeter.id}"
        ):
            payload = await t_utils.connect_and_get_msg(
                ws_client,
                "UnmaskSignalRequest",
                {'id': flowmeter.id, 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
            )
            parsed_payload = parser.parse_unmask_signal_msg(payload)
            flowmeter_unmask_reply_status = parsed_payload.replyStatus
            StepCheck("Проверка кода ответа на запрос о маскировании", "replyStatus").actual(
                flowmeter_unmask_reply_status
            ).expected(Exp.REPLY_STATUS.OK.value).equal_to()
    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчиков из сообщения типа: InputSignalsContent"
    ):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [pressure_sensor.id, flowmeter.id],
                'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
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
        ).actual(pressure_sensor_mask_data.isMasked).expected(Exp.IS_MASKED_TRUE_VAL).equal_to()
        StepCheck(f"Проверка маскирования расходомера с id: {flowmeter.id}", "isMasked", soft_failures).actual(
            flowmeter_mask_data.isMasked
        ).expected(Exp.IS_MASKED_TRUE_VAL).equal_to()
        StepCheck(
            f"Проверка снятия маскирования датчика давления с id: {pressure_sensor.id}", "isMasked", soft_failures
        ).actual(pressure_sensor_unmask_data.isMasked).expected(Exp.IS_MASKED_FALSE_VAL).equal_to()
        StepCheck(f"Проверка снятия маскирования расходомера с id: {flowmeter.id}", "isMasked", soft_failures).actual(
            flowmeter_unmask_data.isMasked
        ).expected(Exp.IS_MASKED_FALSE_VAL).equal_to()


@allure.description(
    "Проверка режима работы СОУ в сообщении типа: CommonScheme "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Время проведения проверки : ~30:00\n"
    "Ожидаемый результат : режим работы СОУ не 'Инициализация'\n"
)
@allure.title(f"[CommonScheme] Проверка выхода СОУ из Инициализации на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("SubscribeCommonSchemeRequest")
@pytest.mark.test_case_id("30")
@pytest.mark.offset(30)
@pytest.mark.asyncio
async def test_lds_status_initialization_out(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
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
    ).expected(Exp.LDS_STATUS.INITIALIZATION.value).is_not_equal_to()


@allure.description(
    "Проверка сообщения MainPageInfo "
    f"об установке режима Не стационар на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое время установки режима Стационар : ~05:00\n"
)
@allure.title(f"[MainPageInfo] Проверка установки не стационара на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeMainPageInfoRequest")
@pytest.mark.test_case_id("3")
@pytest.mark.offset(45)
@pytest.mark.asyncio
async def test_main_page_info_unstationary(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck(
            f"Проверка установки стационара для ТУ {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}",
            "stationary_status",
            soft_failures,
        ).actual(parsed_payload.replyContent.tuInfo.stationaryStatus).expected(
            Exp.STATIONARY_STATUS.UNSTATIONARY.value
        ).equal_to()


@allure.description(
    "Проверка сообщения LeaksContent "
    f"о первой утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~37:00 - 43:00\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[LeaksContent] проверка первой утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("SubscribeLeaksRequest")
@pytest.mark.test_case_id("4")
@pytest.mark.offset(47.0)
@pytest.mark.asyncio
async def test_leaks_content_first_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "LeaksContent",
            "SubscribeLeaksRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id},
        )
        parsed_payload = parser.parse_leaks_info_msg(payload)
        leaks_list_info = parsed_payload.replyContent.leaksListInfo
        first_leak = t_utils.find_object_by_field(
            leaks_list_info, "diagnosticAreaName", Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL
        )
        # Получает время обнаружения утечки
        leak_detected_at = first_leak.detectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        # Получает объем утечки в м3/час
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak.leakVolume)
        leak_coordinate_round = round(first_leak.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            first_leak.diagnosticAreaName
        ).expected(Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL).equal_to()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            first_leak.confirmationStatus
        ).expected(Exp.CONFIRMATION_STATUS.CONFIRMED.value).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(first_leak.type).expected(
            Exp.RESERVED_TYPE.UNSTATIONARY_FLOW.value
        ).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_1_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(
            leak_wait_end_time,
            leak_wait_start_time,
        )

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_1_VOLUME_M3,
            Exp.LEAK_1_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )


@allure.description(
    "Проверка сообщения AllLeaksInfo "
    f"о первой утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~37:00 - 43:00\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[AllLeaksInfo] проверка первой утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeAllLeaksInfoRequest")
@pytest.mark.test_case_id("4")
@pytest.mark.offset(47.0)
@pytest.mark.asyncio
async def test_all_leaks_info_first_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )

    StepCheck("Проверка наличия сообщения об утечке типа AllLeaksInfoContent", "leaksInfo").actual(
        parsed_payload.replyContent.leaksInfo
    ).is_not_empty()
    with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
        # Для дальнейших проверок берет первое сообщение об утечке
        leaks_info = parsed_payload.replyContent.leaksInfo
        first_leak_info = t_utils.find_object_by_field(
            leaks_info, "diagnosticAreaName", Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL
        )
        # Получает время обнаружения утечки
        leak_detected_at = first_leak_info.leakDetectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        # Получает объем утечки в м3/час
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak_info.volume)
        leak_coordinate_round = round(first_leak_info.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            first_leak_info.diagnosticAreaName
        ).expected(Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL).equal_to()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(first_leak_info.ldsStatus).expected(
            Exp.LDS_STATUS.SERVICEABLE.value
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(first_leak_info.isMasked).expected(
            Exp.IS_MASKED_FALSE_VAL
        ).equal_to()

        StepCheck("Проверка квитирования утечки", "isAcknowledged", soft_failures).actual(
            first_leak_info.isAcknowledged
        ).expected(Exp.IS_ACKNOWLEDGED_FALSE_VAL).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_1_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(
            leak_wait_end_time,
            leak_wait_start_time,
        )

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_1_VOLUME_M3,
            Exp.LEAK_1_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            first_leak_info.stationaryStatus
        ).expected(Exp.STATIONARY_STATUS.UNSTATIONARY.value).equal_to()


@allure.description(
    "Проверка сообщения TuLeaksInfo "
    f"о первой утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~37:00 - 43:00\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[TuLeaksInfo] проверка первой утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeTuLeaksInfoRequest")
@pytest.mark.test_case_id("5")
@pytest.mark.offset(47.0)
@pytest.mark.asyncio
async def test_tu_leaks_info_first_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: TuLeaksInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "TuLeaksInfoContent",
            "subscribeTuLeaksInfoRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id},
        )
    parsed_payload = parser.parse_tu_leaks_info_msg(payload)

    StepCheck("Проверка наличия сообщения об утечке типа TuLeaksInfoContent", "leaksInfo").actual(
        parsed_payload.replyContent.leaksInfo
    ).is_not_empty()

    with allure.step("Обработка сообщения об утечке типа TuLeaksInfoContent"):
        # Ищет сообщение об утечке по controlledSiteId
        tu_leaks_info = parsed_payload.replyContent.leaksInfo
        first_leak_tu_info = t_utils.find_object_by_field(
            tu_leaks_info, "controlledSiteId", Exp.LEAK_1_CONTROL_SITE_ID_VAL
        )
        leak_detected_at = first_leak_tu_info.leakDetectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak_tu_info.volume)
        leak_coordinate_round = round(first_leak_tu_info.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка наличия id участка утечки", "controlledSiteId", soft_failures).actual(
            first_leak_tu_info.controlledSiteId
        ).expected(Exp.LEAK_1_CONTROL_SITE_ID_VAL).equal_to()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(first_leak_tu_info.ldsStatus).expected(
            Exp.LDS_STATUS.SERVICEABLE.value
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(
            first_leak_tu_info.isMasked
        ).expected(Exp.IS_MASKED_FALSE_VAL).equal_to()

        StepCheck("Проверка наличия pipeId в сообщении", "pipeId", soft_failures).actual(
            first_leak_tu_info.pipeId
        ).is_not_none()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak_tu_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_1_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_end_time, leak_wait_start_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_1_VOLUME_M3,
            Exp.LEAK_1_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            first_leak_tu_info.stationaryStatus
        ).expected(Exp.STATIONARY_STATUS.UNSTATIONARY.value).equal_to()


@allure.description(
    "Проверка режима работы СОУ во время утечки в сообщении типа: CommonScheme "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Время проведения проверки : 59:30\n"
    "Примечание: проверка режимов СОУ во время утечки должна выполняться раньше теста на квитирование\n"
    "В рамках данного теста проверяется режим СОУ на ДУ с утечкой и на соседних ДУ"
)
@allure.title(f"[CommonScheme] Проверка режима работы СОУ во время утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("SubscribeCommonSchemeRequest")
@pytest.mark.test_case_id("31")
@pytest.mark.offset(47.0)
@pytest.mark.asyncio
async def test_lds_status_during_leak(ws_client):
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
        flow_areas = parsed_payload.replyContent.flowAreas
        leak_diagnostic_area = t_utils.find_diagnostic_area_by_id(flow_areas, Exp.LEAK_1_DIAGNOSTIC_AREA_ID_VAL)
        in_neighbor_diagnostic_area = t_utils.find_diagnostic_area_by_id(
            flow_areas, Exp.IN_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL
        )
        out_neighbor_diagnostic_area = t_utils.find_diagnostic_area_by_id(
            flow_areas, Exp.OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL
        )
    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка режима работы СОУ на ДУ с утечкой, id ДУ: {Exp.LEAK_1_DIAGNOSTIC_AREA_ID_VAL}",
            "ldsStatus",
            soft_failures,
        ).actual(leak_diagnostic_area.ldsStatus).expected(Exp.LDS_STATUS.INITIALIZATION.value).equal_to()
        StepCheck(
            f"Проверка режима работы СОУ на соседнем ДУ, id ДУ: {Exp.IN_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL}",
            "ldsStatus",
            soft_failures,
        ).actual(in_neighbor_diagnostic_area.ldsStatus).expected(Exp.LDS_STATUS.DEGRADATION.value).equal_to()
        StepCheck(
            f"Проверка режима работы СОУ на соседнем ДУ, id ДУ: {Exp.OUT_NEIGHBOR_DIAGNOSTIC_AREA_ID_VAL}",
            "ldsStatus",
            soft_failures,
        ).actual(out_neighbor_diagnostic_area.ldsStatus).expected(Exp.LDS_STATUS.DEGRADATION.value).equal_to()


@allure.description(
    "Проверка сообщения LeaksContent "
    f"о второй утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~52:00 - 58:00\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[LeaksContent] проверка второй утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("SubscribeLeaksRequest")
@pytest.mark.test_case_id("4")
@pytest.mark.offset(61.0)
@pytest.mark.asyncio
async def test_leaks_content_second_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "LeaksContent",
            "SubscribeLeaksRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id},
        )
        parsed_payload = parser.parse_leaks_info_msg(payload)
        leaks_list_info = parsed_payload.replyContent.leaksListInfo
        second_leak = t_utils.find_object_by_field(
            leaks_list_info, "diagnosticAreaName", Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL
        )
        # Получает время обнаружения утечки
        leak_detected_at = second_leak.detectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        # Получает объем утечки в м3/час
        leak_volume_m3 = t_utils.convert_leak_volume_m3(second_leak.leakVolume)
        leak_coordinate_round = round(second_leak.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            second_leak.diagnosticAreaName
        ).expected(Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL).equal_to()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            second_leak.confirmationStatus
        ).expected(Exp.CONFIRMATION_STATUS.CONFIRMED.value).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(second_leak.type).expected(
            Exp.RESERVED_TYPE.UNSTATIONARY_FLOW.value
        ).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(second_leak.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_2_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(
            leak_wait_end_time,
            leak_wait_start_time,
        )

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_2_VOLUME_M3,
            Exp.LEAK_2_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )


@allure.description(
    "Проверка сообщения AllLeaksInfo "
    f"о второй утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~52:00 - 58:00\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[AllLeaksInfo] проверка второй утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeAllLeaksInfoRequest")
@pytest.mark.test_case_id("4")
@pytest.mark.offset(61.0)
@pytest.mark.asyncio
async def test_all_leaks_info_second_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )

    StepCheck("Проверка наличия сообщения об утечке типа AllLeaksInfoContent", "leaksInfo").actual(
        parsed_payload.replyContent.leaksInfo
    ).is_not_empty()
    with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
        # Для дальнейших проверок берет первое сообщение об утечке
        leaks_info = parsed_payload.replyContent.leaksInfo
        second_leak_info = t_utils.find_object_by_field(
            leaks_info, "diagnosticAreaName", Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL
        )
        # Получает время обнаружения утечки
        leak_detected_at = second_leak_info.leakDetectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        # Получает объем утечки в м3/час
        leak_volume_m3 = t_utils.convert_leak_volume_m3(second_leak_info.volume)
        leak_coordinate_round = round(second_leak_info.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            second_leak_info.diagnosticAreaName
        ).expected(Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL).equal_to()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(second_leak_info.ldsStatus).expected(
            Exp.LDS_STATUS.DEGRADATION.value
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(second_leak_info.isMasked).expected(
            Exp.IS_MASKED_FALSE_VAL
        ).equal_to()

        StepCheck("Проверка квитирования утечки", "isAcknowledged", soft_failures).actual(
            second_leak_info.isAcknowledged
        ).expected(Exp.IS_ACKNOWLEDGED_FALSE_VAL).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(second_leak_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_2_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(
            leak_wait_end_time,
            leak_wait_start_time,
        )

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_2_VOLUME_M3,
            Exp.LEAK_2_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            second_leak_info.stationaryStatus
        ).expected(Exp.STATIONARY_STATUS.UNSTATIONARY.value).equal_to()


@allure.description(
    "Проверка сообщения TuLeaksInfo "
    f"о второй утечке на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Ожидаемое окно возникновения утечки: ~52:00 - 58:00\n"
    "Допустимое время обнаружения 6 минут с момента начала утечки, "
    f"т к для данных {Exp.TEST_SUITE_NAME_VAL} интенсивность утечки 20,4%.\n"
    "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
)
@allure.title(f"[TuLeaksInfo] проверка второй утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("subscribeTuLeaksInfoRequest")
@pytest.mark.test_case_id("5")
@pytest.mark.offset(61.0)
@pytest.mark.asyncio
async def test_tu_leaks_info_second_leak(ws_client):
    with allure.step("Подключение по ws и получение сообщения об утечке типа: TuLeaksInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "TuLeaksInfoContent",
            "subscribeTuLeaksInfoRequest",
            {'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id},
        )
    parsed_payload = parser.parse_tu_leaks_info_msg(payload)

    StepCheck("Проверка наличия сообщения об утечке типа TuLeaksInfoContent", "leaksInfo").actual(
        parsed_payload.replyContent.leaksInfo
    ).is_not_empty()

    with allure.step("Обработка сообщения об утечке типа TuLeaksInfoContent"):
        tu_leaks_info = parsed_payload.replyContent.leaksInfo
        second_leak_tu_info = t_utils.find_object_by_field(
            tu_leaks_info, "controlledSiteId", Exp.LEAK_2_CONTROL_SITE_ID_VAL
        )
        leak_detected_at = second_leak_tu_info.leakDetectedAt
        # Принимает timezone что бы она была одинаковая, убирает микросекунды
        leak_wait_end_time = datetime.now(leak_detected_at.tzinfo).replace(microsecond=0)
        leak_wait_start_time = t_utils.get_leak_wait_start_time(
            leak_wait_end_time, Exp.LEAK_1_ALLOWED_TIME_DIFF_SECONDS
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(second_leak_tu_info.volume)
        leak_coordinate_round = round(second_leak_tu_info.leakCoordinate, 3)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id).equal_to()

        StepCheck("Проверка наличия id участка утечки", "controlledSiteId", soft_failures).actual(
            second_leak_tu_info.controlledSiteId
        ).expected(Exp.LEAK_2_CONTROL_SITE_ID_VAL).equal_to()

        StepCheck("Проверка статуса СОУ", "ldsStatus", soft_failures).actual(second_leak_tu_info.ldsStatus).expected(
            Exp.LDS_STATUS.DEGRADATION.value
        ).equal_to()

        StepCheck("Проверка маскирования утечки", "isMasked", soft_failures).actual(
            second_leak_tu_info.isMasked
        ).expected(Exp.IS_MASKED_FALSE_VAL).equal_to()

        StepCheck("Проверка наличия pipeId в сообщении", "pipeId", soft_failures).actual(
            second_leak_tu_info.pipeId
        ).is_not_none()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(second_leak_tu_info.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            Exp.LEAK_2_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_end_time, leak_wait_start_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            Exp.LEAK_2_VOLUME_M3,
            Exp.LEAK_2_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )

        StepCheck("Проверка режима ТУ", "stationaryStatus", soft_failures).actual(
            second_leak_tu_info.stationaryStatus
        ).expected(Exp.STATIONARY_STATUS.UNSTATIONARY.value).equal_to()


@allure.description(
    "Проверка квитирования первой утечки через синхронный запрос типа: AcknowledgeLeakRequest "
    f"на наборе данных {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}, \n"
    f"на технологическом участке {Exp.TN3_TU_NAME}\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Проверки:\n"
    "Статус-код ответа на синхронный запрос AcknowledgeLeakRequest,\n"
    "Отсутствие сообщений об утечках в AllLeaksInfoContent после квитирования"
)
@allure.title(f"[AcknowledgeLeak] проверка квитирования первой утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("AcknowledgeLeakRequest")
@pytest.mark.test_case_id("6")
@pytest.mark.offset(62.0)
@pytest.mark.asyncio
async def test_acknowledge_leak_info_first_leak(ws_client):
    with allure.step("Получение id первой утечки"):
        with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
            parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
                Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
                ws_client,
                "AllLeaksInfoContent",
                "subscribeAllLeaksInfoRequest",
                [],
            )

        StepCheck("Проверка наличия сообщения об утечке типа AllLeaksInfoContent", "leaksInfo").actual(
            parsed_payload.replyContent.leaksInfo
        ).is_not_empty()
        with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
            # Для дальнейших проверок берет первое сообщение об утечке
            leaks_info = parsed_payload.replyContent.leaksInfo
            first_leak_info = t_utils.find_object_by_field(
                leaks_info, "diagnosticAreaName", Exp.LEAK_1_DIAGNOSTIC_AREA_NAME_VAL
            )
            first_leak_id = first_leak_info.id
    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': str(first_leak_id), 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_acknowledge_leak_msg(payload)
        acknowledge_reply_status = parsed_payload.replyStatus

    with allure.step(
        "Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent для проверки квитирования"
    ):
        with allure.step("Очистка очереди websocket сообщений"):
            ws_client.clear_queue()
        time.sleep(Exp.BASIC_MESSAGE_TIMEOUT)
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )
        leaks_info = parsed_payload.replyContent.leaksInfo
        leaks_id_list = [leak.id for leak in leaks_info]
    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(acknowledge_reply_status).expected(
        Exp.REPLY_STATUS.OK.value
    ).equal_to()
    StepCheck("Проверка наличия сообщений о неквитированных утечках", "leaksInfo").actual(leaks_info).is_not_empty()
    StepCheck("Проверка отсутствия квитированной утечки в сообщении allLeakInfo", "id").does_not_contain(
        leaks_id_list, first_leak_id
    )


@allure.description(
    "Проверка квитирования второй утечки через синхронный запрос типа: AcknowledgeLeakRequest "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    f"Ожидаемое ДУ возникновения утечки: {Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL}\n"
    "Проверки:\n"
    "Статус-код ответа на синхронный запрос AcknowledgeLeakRequest,\n"
    "Отсутствие сообщений об утечках в AllLeaksInfoContent после квитирования"
)
@allure.title(f"[AcknowledgeLeak] проверка квитирования второй утечки на данных {Exp.TEST_SUITE_NAME_VAL}")
@allure.tag("AcknowledgeLeakRequest")
@pytest.mark.test_case_id("6")
@pytest.mark.offset(62.5)
@pytest.mark.asyncio
async def test_acknowledge_leak_info_second_leak(ws_client):
    with allure.step("Получение id второй утечки"):
        with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
            parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
                Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
                ws_client,
                "AllLeaksInfoContent",
                "subscribeAllLeaksInfoRequest",
                [],
            )

        StepCheck("Проверка наличия сообщения об утечке типа AllLeaksInfoContent", "leaksInfo").actual(
            parsed_payload.replyContent.leaksInfo
        ).is_not_empty()
        with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
            # Для дальнейших проверок берет первое сообщение об утечке
            leaks_info = parsed_payload.replyContent.leaksInfo
            second_leak_info = t_utils.find_object_by_field(
                leaks_info, "diagnosticAreaName", Exp.LEAK_2_DIAGNOSTIC_AREA_NAME_VAL
            )
            second_leak_id = second_leak_info.id
    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': str(second_leak_id), 'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_acknowledge_leak_msg(payload)
        acknowledge_reply_status = parsed_payload.replyStatus

    with allure.step(
        "Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent для проверки квитирования"
    ):
        with allure.step("Очистка очереди websocket сообщений"):
            ws_client.clear_queue()
        time.sleep(Exp.BASIC_MESSAGE_TIMEOUT)
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )
        leaks_info = parsed_payload.replyContent.leaksInfo
    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(acknowledge_reply_status).expected(
        Exp.REPLY_STATUS.OK.value
    ).equal_to()
    StepCheck("Проверка отсутствия сообщений об утечках после квитирования", "leaksInfo").actual(leaks_info).is_empty()


@allure.description(
    "Проверка наличия данных о первой утечке в выходных сигналах "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Получение списка выходных сигналов для линейного участка, запросом: GetOutputSignalsRequest\n"
    "Получение данных выходных сигналов для линейного участка, по подписке: SubscribeOutputSignalsRequest\n"
    "Примечание: "
    "Данный тест так же проверяет квитирование, время запуска выставлять после запуска теста на квитирование утечки"
)
@allure.title(
    "[OutputSignalsInfo] Проверка данных о первой утечке в выходных сигналах на линейном участке с id: "
    f"{Exp.LEAK_1_LINEAR_PART_ID_VAL}"
)
@allure.tag("SubscribeOutputSignalsRequest")
@pytest.mark.test_case_id("33")
@pytest.mark.offset(63.0)
@pytest.mark.asyncio
async def test_output_signals_first_leak(ws_client):
    with allure.step(f"Получение списка выходных сигналов для линейного участка с id: {Exp.LEAK_1_LINEAR_PART_ID_VAL}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetOutputSignalsRequest",
            {
                'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
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
            Exp.LEAK_LINEAR_PART_ID_KEY,
            Exp.LEAK_1_LINEAR_PART_ID_VAL,
        )
        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_ACK_LEAK
            )
            leak_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, Exp.ADDRESS_SUFFIX_LEAK)
            mask_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, Exp.ADDRESS_SUFFIX_MASK)
            point_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_POINT_LEAK
            )
            q_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_Q_LEAK
            )
            time_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_TIME_LEAK
            )

    with allure.step(f"Получение данных выходных сигналов для линейного участка с id: {Exp.LEAK_1_LINEAR_PART_ID_VAL}"):
        with allure.step("Получение сообщения с данными выходных сигналов типа: OutputSignalsInfo"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "OutputSignalsInfo",
                "SubscribeOutputSignalsRequest",
                {
                    'objects': {
                        'linearParts': [{'linearPartId': Exp.LEAK_1_LINEAR_PART_ID_VAL}],
                        'controlledSites': [],
                    },
                    'signalTypes': 1023,
                    'tuId': Exp.TN3_TU_ID,
                    'additionalProperties': None,
                },
            )
            parsed_payload = parser.parse_output_signals_info_msg(payload)
            leak_linear_part = t_utils.find_object_by_field(
                parsed_payload.replyContent.linearPartSignals,
                Exp.LEAK_LINEAR_PART_ID_KEY,
                Exp.LEAK_1_LINEAR_PART_ID_VAL,
            )
        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, ack_leak_signal_type)
            leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, leak_signal_type)
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)
            point_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, point_leak_signal_type)
            q_leak_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, q_leak_signal_type)
            time_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, time_leak_signal_type)
            StepCheck("Проверка наличия времени утечки", Exp.ADDRESS_SUFFIX_TIME_LEAK).actual(
                time_leak_value
            ).is_not_none()
            time_leak_value_datetime = t_utils.to_moscow_timezone(time_leak_value)
            # Получает текущее время, с временной зоной времени утечки
            datetime_now = datetime.now(time_leak_value_datetime.tzinfo).replace(microsecond=0)
            # Получает временной интервал проверки
            leak_wait_end_time = t_utils.get_leak_wait_start_time(datetime_now, Exp.LEAK_1_OUTPUT_TEST_DELAY_S)
            leak_wait_start_time = t_utils.get_leak_wait_start_time(datetime_now, Exp.LEAK_1_OUTPUT_ALLOWED_TIME_DIFF_S)
            q_leak_value_m3 = t_utils.convert_leak_volume_m3(float(q_leak_leak_value))
            point_leak_value_round = round(float(point_leak_value), 3)
    with SoftAssertions() as soft_failures:
        StepCheck("Проверка сигнала квитирования утечки", Exp.ADDRESS_SUFFIX_ACK_LEAK, soft_failures).actual(
            ack_leak_value
        ).expected(Exp.OUTPUT_IS_ACK_LEAK).equal_to()
        StepCheck("Проверка сигнала наличия утечки", Exp.ADDRESS_SUFFIX_LEAK, soft_failures).actual(
            leak_value
        ).expected(Exp.OUTPUT_IS_LEAK).equal_to()
        StepCheck("Проверка сигнала маскирования утечки", Exp.ADDRESS_SUFFIX_MASK, soft_failures).actual(
            mask_leak_value
        ).expected(Exp.OUTPUT_IS_NOT_MASK).equal_to()
        StepCheck("Проверка сигнала координаты утечки", Exp.ADDRESS_SUFFIX_POINT_LEAK, soft_failures).actual(
            point_leak_value_round
        ).is_close_to(
            Exp.LEAK_1_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )
        StepCheck("Проверка сигнала объема утечки", Exp.ADDRESS_SUFFIX_Q_LEAK, soft_failures).actual(
            q_leak_value_m3
        ).is_close_to(
            Exp.LEAK_1_VOLUME_M3,
            Exp.LEAK_1_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_1_ALLOWED_VOLUME_M3}",
        )
        StepCheck("Проверка времени обнаружения утечки", Exp.ADDRESS_SUFFIX_TIME_LEAK, soft_failures).actual(
            time_leak_value_datetime
        ).is_between(leak_wait_end_time, leak_wait_start_time)


@allure.description(
    "Проверка наличия данных о второй утечке в выходных сигналах "
    f"на наборе данных {Exp.TEST_SUITE_NAME_VAL}, \n"
    f"на технологическом участке {Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.description}\n"
    "Получение списка выходных сигналов для линейного участка, запросом: GetOutputSignalsRequest\n"
    "Получение данных выходных сигналов для линейного участка, по подписке: SubscribeOutputSignalsRequest\n"
    "Примечание: "
    "Данный тест так же проверяет квитирование, время запуска выставлять после запуска теста на квитирование утечки"
)
@allure.title(
    "[OutputSignalsInfo] Проверка данных о второй утечке в выходных сигналах на линейном участке с id: "
    f"{Exp.LEAK_2_LINEAR_PART_ID_VAL}"
)
@allure.tag("SubscribeOutputSignalsRequest")
@pytest.mark.test_case_id("33")
@pytest.mark.offset(63.5)
@pytest.mark.asyncio
async def test_output_signals_second_leak(ws_client):
    with allure.step(f"Получение списка выходных сигналов для линейного участка с id: {Exp.LEAK_2_LINEAR_PART_ID_VAL}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "GetOutputSignalsRequest",
            {
                'tuId': Exp.TU.TIKHORETSK_NOVOROSSIYSK_3.id,
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
            Exp.LEAK_LINEAR_PART_ID_KEY,
            Exp.LEAK_2_LINEAR_PART_ID_VAL,
        )
        with allure.step("Получение типов выходных сигналов из обработанных данных"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_ACK_LEAK
            )
            leak_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, Exp.ADDRESS_SUFFIX_LEAK)
            mask_signal_type = t_utils.find_signal_type_by_address_suffix(leak_signals_list, Exp.ADDRESS_SUFFIX_MASK)
            point_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_POINT_LEAK
            )
            q_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_Q_LEAK
            )
            time_leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, Exp.ADDRESS_SUFFIX_TIME_LEAK
            )

    with allure.step(f"Получение данных выходных сигналов для линейного участка с id: {Exp.LEAK_2_LINEAR_PART_ID_VAL}"):
        with allure.step("Получение сообщения с данными выходных сигналов типа: OutputSignalsInfo"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "OutputSignalsInfo",
                "SubscribeOutputSignalsRequest",
                {
                    'objects': {
                        'linearParts': [{'linearPartId': Exp.LEAK_2_LINEAR_PART_ID_VAL}],
                        'controlledSites': [],
                    },
                    'signalTypes': 1023,
                    'tuId': Exp.TN3_TU_ID,
                    'additionalProperties': None,
                },
            )
            parsed_payload = parser.parse_output_signals_info_msg(payload)
            leak_linear_part = t_utils.find_object_by_field(
                parsed_payload.replyContent.linearPartSignals,
                Exp.LEAK_LINEAR_PART_ID_KEY,
                Exp.LEAK_2_LINEAR_PART_ID_VAL,
            )
        with allure.step("Обработка полученных данных выходных сигналов"):
            leak_signals_list = leak_linear_part.signals
            ack_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, ack_leak_signal_type)
            leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, leak_signal_type)
            mask_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, mask_signal_type)
            point_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, point_leak_signal_type)
            q_leak_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, q_leak_signal_type)
            time_leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, time_leak_signal_type)
            StepCheck("Проверка наличия времени утечки", Exp.ADDRESS_SUFFIX_TIME_LEAK).actual(
                time_leak_value
            ).is_not_none()
            time_leak_value_datetime = t_utils.to_moscow_timezone(time_leak_value)
            datetime_now = datetime.now(time_leak_value_datetime.tzinfo).replace(microsecond=0)
            leak_wait_end_time = t_utils.get_leak_wait_start_time(datetime_now, Exp.LEAK_2_OUTPUT_TEST_DELAY_S)
            leak_wait_start_time = t_utils.get_leak_wait_start_time(datetime_now, Exp.LEAK_2_OUTPUT_ALLOWED_TIME_DIFF_S)
            q_leak_value_m3 = t_utils.convert_leak_volume_m3(float(q_leak_leak_value))
            point_leak_value_round = round(float(point_leak_value), 3)
    with SoftAssertions() as soft_failures:
        StepCheck("Проверка сигнала квитирования утечки", Exp.ADDRESS_SUFFIX_ACK_LEAK, soft_failures).actual(
            ack_leak_value
        ).expected(Exp.OUTPUT_IS_ACK_LEAK).equal_to()
        StepCheck("Проверка сигнала наличия утечки", Exp.ADDRESS_SUFFIX_LEAK, soft_failures).actual(
            leak_value
        ).expected(Exp.OUTPUT_IS_LEAK).equal_to()
        StepCheck("Проверка сигнала маскирования утечки", Exp.ADDRESS_SUFFIX_MASK, soft_failures).actual(
            mask_leak_value
        ).expected(Exp.OUTPUT_IS_NOT_MASK).equal_to()
        StepCheck("Проверка сигнала координаты утечки", Exp.ADDRESS_SUFFIX_POINT_LEAK, soft_failures).actual(
            point_leak_value_round
        ).is_close_to(
            Exp.LEAK_2_COORDINATE_METERS,
            Exp.ALLOWED_DISTANCE_DIFF_METERS,
            f"значение допустимой погрешности координаты {Exp.ALLOWED_DISTANCE_DIFF_METERS}",
        )
        StepCheck("Проверка сигнала объема утечки", Exp.ADDRESS_SUFFIX_Q_LEAK, soft_failures).actual(
            q_leak_value_m3
        ).is_close_to(
            Exp.LEAK_2_VOLUME_M3,
            Exp.LEAK_2_ALLOWED_VOLUME_M3,
            f"значение допустимой погрешности по объему {Exp.LEAK_2_ALLOWED_VOLUME_M3}",
        )
        StepCheck("Проверка времени обнаружения утечки", Exp.ADDRESS_SUFFIX_TIME_LEAK, soft_failures).actual(
            time_leak_value_datetime
        ).is_between(leak_wait_end_time, leak_wait_start_time)
