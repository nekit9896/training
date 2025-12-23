"""
Тесты для набора данных Select_19_20 (две утечки).

Запуск: pytest tests/test_smoke_select_19_20.py
"""

import time

import allure
import pytest

from constants.expectations.enums import ConfirmationStatus, LdsStatus, ReservedType, ReplyStatus, StationaryStatus
from test_config.datasets import SELECT_19_20_CONFIG
from test_scenarios import scenarios
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser

CFG = SELECT_19_20_CONFIG
LEAK_1 = CFG.leaks[0]
LEAK_2 = CFG.leaks[1]

pytestmark = [
    pytest.mark.test_suite_name(CFG.suite_name),
    pytest.mark.test_suite_data_id(CFG.suite_data_id),
    pytest.mark.test_data_name(CFG.archive_name),
]


# ===== Базовые тесты =====
@allure.title(CFG.basic_info_test.title)
@allure.tag(CFG.basic_info_test.tag)
@pytest.mark.test_case_id(CFG.basic_info_test.test_case_id)
@pytest.mark.offset(CFG.basic_info_test.offset)
@pytest.mark.asyncio
async def test_basic_info(ws_client):
    await scenarios.basic_info(ws_client, CFG)


@allure.description(CFG.journal_info_test.description)
@allure.title(CFG.journal_info_test.title)
@allure.tag(CFG.journal_info_test.tag)
@pytest.mark.test_case_id(CFG.journal_info_test.test_case_id)
@pytest.mark.offset(CFG.journal_info_test.offset)
@pytest.mark.asyncio
async def test_journal_info(ws_client):
    await scenarios.journal_info(ws_client, CFG)


@allure.description(CFG.lds_status_initialization_test.description)
@allure.title(CFG.lds_status_initialization_test.title)
@allure.tag(CFG.lds_status_initialization_test.tag)
@pytest.mark.test_case_id(CFG.lds_status_initialization_test.test_case_id)
@pytest.mark.offset(CFG.lds_status_initialization_test.offset)
@pytest.mark.asyncio
async def test_lds_status_initialization(ws_client):
    await scenarios.lds_status_initialization(ws_client, CFG)


@allure.description(CFG.main_page_info_test.description)
@allure.title(CFG.main_page_info_test.title)
@allure.tag(CFG.main_page_info_test.tag)
@pytest.mark.test_case_id(CFG.main_page_info_test.test_case_id)
@pytest.mark.offset(CFG.main_page_info_test.offset)
@pytest.mark.asyncio
async def test_main_page_info_stationary(ws_client):
    await scenarios.main_page_info(ws_client, CFG)


@allure.description(CFG.mask_signal_test.description)
@allure.title(CFG.mask_signal_test.title)
@allure.tag(CFG.mask_signal_test.tag)
@pytest.mark.test_case_id(CFG.mask_signal_test.test_case_id)
@pytest.mark.offset(CFG.mask_signal_test.offset)
@pytest.mark.asyncio
async def test_mask_signal_msg(ws_client):
    await scenarios.mask_signal_msg(ws_client, CFG)


@allure.description(CFG.lds_status_initialization_out_test.description)
@allure.title(CFG.lds_status_initialization_out_test.title)
@allure.tag(CFG.lds_status_initialization_out_test.tag)
@pytest.mark.test_case_id(CFG.lds_status_initialization_out_test.test_case_id)
@pytest.mark.offset(CFG.lds_status_initialization_out_test.offset)
@pytest.mark.asyncio
async def test_lds_status_initialization_out(ws_client):
    await scenarios.lds_status_initialization_out(ws_client, CFG)


# ===== Тест на нестационар =====
@allure.description(CFG.main_page_info_unstationary_test.description)
@allure.title(CFG.main_page_info_unstationary_test.title)
@allure.tag(CFG.main_page_info_unstationary_test.tag)
@pytest.mark.test_case_id(CFG.main_page_info_unstationary_test.test_case_id)
@pytest.mark.offset(CFG.main_page_info_unstationary_test.offset)
@pytest.mark.asyncio
async def test_main_page_info_unstationary(ws_client):
    """Проверка установки режима Нестационар"""
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [CFG.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(CFG.tu_id).equal_to()

        StepCheck(
            f"Проверка установки стационара для ТУ {CFG.tu_name}",
            "stationary_status",
            soft_failures,
        ).actual(parsed_payload.replyContent.tuInfo.stationaryStatus).expected(
            StationaryStatus.UNSTATIONARY.value
        ).equal_to()


# ===== Тесты первой утечки (LeaksContent) =====
@allure.description(LEAK_1.leaks_content_test.description)
@allure.title(LEAK_1.leaks_content_test.title)
@allure.tag(LEAK_1.leaks_content_test.tag)
@pytest.mark.test_case_id(LEAK_1.leaks_content_test.test_case_id)
@pytest.mark.offset(LEAK_1.leaks_content_test.offset)
@pytest.mark.asyncio
async def test_leaks_content_first_leak(ws_client, imitator_start_time):
    """Проверка первой утечки через LeaksContent"""
    with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "LeaksContent",
            "SubscribeLeaksRequest",
            {'tuId': CFG.tu_id},
        )
        parsed_payload = parser.parse_leaks_content_msg(payload)
        leaks_list_info = parsed_payload.replyContent.leaksListInfo
        first_leak = t_utils.find_object_by_field(
            leaks_list_info, "diagnosticAreaName", LEAK_1.diagnostic_area_name
        )
        leak_detected_at = first_leak.detectedAt
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            LEAK_1.leak_start_interval_seconds,
            LEAK_1.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(first_leak.leakVolume)
        leak_coordinate_round = round(first_leak.leakCoordinate, CFG.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(CFG.tu_id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            first_leak.diagnosticAreaName
        ).expected(LEAK_1.diagnostic_area_name).equal_to()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            first_leak.confirmationStatus
        ).expected(ConfirmationStatus.CONFIRMED.value).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(first_leak.type).expected(
            ReservedType.UNSTATIONARY_FLOW.value
        ).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(first_leak.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            LEAK_1.coordinate_meters,
            CFG.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {CFG.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            LEAK_1.volume_m3,
            LEAK_1.allowed_volume_m3,
            f"значение допустимой погрешности по объему {LEAK_1.allowed_volume_m3}",
        )


# ===== AllLeaksInfo первая утечка =====
@allure.description(LEAK_1.all_leaks_info_test.description)
@allure.title(LEAK_1.all_leaks_info_test.title)
@allure.tag(LEAK_1.all_leaks_info_test.tag)
@pytest.mark.test_case_id(LEAK_1.all_leaks_info_test.test_case_id)
@pytest.mark.offset(LEAK_1.all_leaks_info_test.offset)
@pytest.mark.asyncio
async def test_all_leaks_info_first_leak(ws_client, imitator_start_time):
    await scenarios.all_leaks_info(ws_client, CFG, LEAK_1, imitator_start_time)


# ===== TuLeaksInfo первая утечка =====
@allure.description(LEAK_1.tu_leaks_info_test.description)
@allure.title(LEAK_1.tu_leaks_info_test.title)
@allure.tag(LEAK_1.tu_leaks_info_test.tag)
@pytest.mark.test_case_id(LEAK_1.tu_leaks_info_test.test_case_id)
@pytest.mark.offset(LEAK_1.tu_leaks_info_test.offset)
@pytest.mark.asyncio
async def test_tu_leaks_info_first_leak(ws_client, imitator_start_time):
    await scenarios.tu_leaks_info(ws_client, CFG, LEAK_1, imitator_start_time)


# ===== Проверка режима СОУ во время утечки =====
@allure.description(CFG.lds_status_during_leak_test.description)
@allure.title(CFG.lds_status_during_leak_test.title)
@allure.tag(CFG.lds_status_during_leak_test.tag)
@pytest.mark.test_case_id(CFG.lds_status_during_leak_test.test_case_id)
@pytest.mark.offset(CFG.lds_status_during_leak_test.offset)
@pytest.mark.asyncio
async def test_lds_status_during_leak(ws_client):
    await scenarios.lds_status_during_leak(ws_client, CFG)


# ===== Тесты второй утечки (LeaksContent) =====
@allure.description(LEAK_2.leaks_content_test.description)
@allure.title(LEAK_2.leaks_content_test.title)
@allure.tag(LEAK_2.leaks_content_test.tag)
@pytest.mark.test_case_id(LEAK_2.leaks_content_test.test_case_id)
@pytest.mark.offset(LEAK_2.leaks_content_test.offset)
@pytest.mark.asyncio
async def test_leaks_content_second_leak(ws_client, imitator_start_time):
    """Проверка второй утечки через LeaksContent"""
    with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "LeaksContent",
            "SubscribeLeaksRequest",
            {'tuId': CFG.tu_id},
        )
        parsed_payload = parser.parse_leaks_content_msg(payload)
        leaks_list_info = parsed_payload.replyContent.leaksListInfo
        second_leak = t_utils.find_object_by_field(
            leaks_list_info, "diagnosticAreaName", LEAK_2.diagnostic_area_name
        )
        leak_detected_at = second_leak.detectedAt
        leak_wait_start_time, leak_wait_end_time = t_utils.get_leak_time_window(
            imitator_start_time,
            LEAK_2.leak_start_interval_seconds,
            LEAK_2.allowed_time_diff_seconds,
            detected_at_tz=leak_detected_at.tzinfo,
        )
        leak_volume_m3 = t_utils.convert_leak_volume_m3(second_leak.leakVolume)
        leak_coordinate_round = round(second_leak.leakCoordinate, CFG.precision)

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(CFG.tu_id).equal_to()

        StepCheck("Проверка названия диагностического участка утечки", "diagnosticAreaName", soft_failures).actual(
            second_leak.diagnosticAreaName
        ).expected(LEAK_2.diagnostic_area_name).equal_to()

        StepCheck("Проверка статуса утечки", "confirmationStatus", soft_failures).actual(
            second_leak.confirmationStatus
        ).expected(ConfirmationStatus.CONFIRMED.value).equal_to()

        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(second_leak.type).expected(
            ReservedType.UNSTATIONARY_FLOW.value
        ).equal_to()

        StepCheck("Проверка наличия id утечки", "id", soft_failures).actual(second_leak.id).is_not_none()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            LEAK_2.coordinate_meters,
            CFG.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {CFG.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени обнаружения утечки", "leakDetectedAt", soft_failures).actual(
            leak_detected_at
        ).is_between(leak_wait_start_time, leak_wait_end_time)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            LEAK_2.volume_m3,
            LEAK_2.allowed_volume_m3,
            f"значение допустимой погрешности по объему {LEAK_2.allowed_volume_m3}",
        )


# ===== AllLeaksInfo вторая утечка =====
@allure.description(LEAK_2.all_leaks_info_test.description)
@allure.title(LEAK_2.all_leaks_info_test.title)
@allure.tag(LEAK_2.all_leaks_info_test.tag)
@pytest.mark.test_case_id(LEAK_2.all_leaks_info_test.test_case_id)
@pytest.mark.offset(LEAK_2.all_leaks_info_test.offset)
@pytest.mark.asyncio
async def test_all_leaks_info_second_leak(ws_client, imitator_start_time):
    await scenarios.all_leaks_info(ws_client, CFG, LEAK_2, imitator_start_time)


# ===== TuLeaksInfo вторая утечка =====
@allure.description(LEAK_2.tu_leaks_info_test.description)
@allure.title(LEAK_2.tu_leaks_info_test.title)
@allure.tag(LEAK_2.tu_leaks_info_test.tag)
@pytest.mark.test_case_id(LEAK_2.tu_leaks_info_test.test_case_id)
@pytest.mark.offset(LEAK_2.tu_leaks_info_test.offset)
@pytest.mark.asyncio
async def test_tu_leaks_info_second_leak(ws_client, imitator_start_time):
    await scenarios.tu_leaks_info(ws_client, CFG, LEAK_2, imitator_start_time)


# ===== Квитирование первой утечки =====
@allure.description(LEAK_1.acknowledge_leak_test.description)
@allure.title(LEAK_1.acknowledge_leak_test.title)
@allure.tag(LEAK_1.acknowledge_leak_test.tag)
@pytest.mark.test_case_id(LEAK_1.acknowledge_leak_test.test_case_id)
@pytest.mark.offset(LEAK_1.acknowledge_leak_test.offset)
@pytest.mark.asyncio
async def test_acknowledge_leak_info_first_leak(ws_client):
    """Квитирование первой утечки (проверяет что она исчезает из списка)"""
    with allure.step("Получение id первой утечки"):
        with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "LeaksContent",
                "SubscribeLeaksRequest",
                {'tuId': CFG.tu_id},
            )

        with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
            parsed_payload = parser.parse_leaks_content_msg(payload)
            leaks_list_info = parsed_payload.replyContent.leaksListInfo
            first_leak_info = t_utils.find_object_by_field(
                leaks_list_info, "diagnosticAreaName", LEAK_1.diagnostic_area_name
            )
            first_leak_id = first_leak_info.id

    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': str(first_leak_id), 'tuId': CFG.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_acknowledge_leak_msg(payload)
        acknowledge_reply_status = parsed_payload.replyStatus

    with allure.step(
        "Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent для проверки квитирования"
    ):
        with allure.step("Очистка очереди websocket сообщений"):
            ws_client.clear_queue()
        time.sleep(CFG.basic_message_timeout)
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            CFG.tu_id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )
        leaks_info = parsed_payload.replyContent.leaksInfo
        leaks_id_list = [leak.id for leak in leaks_info]

    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(
        acknowledge_reply_status
    ).expected(ReplyStatus.OK.value).equal_to()

    StepCheck("Проверка наличия сообщений о неквитированных утечках", "leaksInfo").actual(leaks_info).is_not_empty()

    StepCheck("Проверка отсутствия квитированной утечки в сообщении allLeakInfo", "id").does_not_contain(
        leaks_id_list, first_leak_id
    )


# ===== Квитирование второй утечки =====
@allure.description(LEAK_2.acknowledge_leak_test.description)
@allure.title(LEAK_2.acknowledge_leak_test.title)
@allure.tag(LEAK_2.acknowledge_leak_test.tag)
@pytest.mark.test_case_id(LEAK_2.acknowledge_leak_test.test_case_id)
@pytest.mark.offset(LEAK_2.acknowledge_leak_test.offset)
@pytest.mark.asyncio
async def test_acknowledge_leak_info_second_leak(ws_client):
    """Квитирование второй утечки (проверяет что список утечек пуст)"""
    with allure.step("Получение id второй утечки"):
        with allure.step("Подключение по ws и получение сообщения об утечке типа: LeaksContent"):
            payload = await t_utils.connect_and_subscribe_msg(
                ws_client,
                "LeaksContent",
                "SubscribeLeaksRequest",
                {'tuId': CFG.tu_id},
            )

        with allure.step("Обработка сообщения об утечке типа AllLeaksInfoContent"):
            parsed_payload = parser.parse_leaks_content_msg(payload)
            leaks_list_info = parsed_payload.replyContent.leaksListInfo
            second_leak = t_utils.find_object_by_field(
                leaks_list_info, "diagnosticAreaName", LEAK_2.diagnostic_area_name
            )
            second_leak_id = second_leak.id

    with allure.step(
        "Подключение по ws, отправка сообщения и обработка ответа о квитировании утечки типа: AcknowledgeLeakRequest"
    ):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "AcknowledgeLeakRequest",
            {'leakId': str(second_leak_id), 'tuId': CFG.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_acknowledge_leak_msg(payload)
        acknowledge_reply_status = parsed_payload.replyStatus

    with allure.step(
        "Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent для проверки квитирования"
    ):
        with allure.step("Очистка очереди websocket сообщений"):
            ws_client.clear_queue()
        time.sleep(CFG.basic_message_timeout)
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            CFG.tu_id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )
        leaks_info = parsed_payload.replyContent.leaksInfo

    StepCheck("Проверка кода ответа на запрос о квитировании", "replyStatus").actual(
        acknowledge_reply_status
    ).expected(ReplyStatus.OK.value).equal_to()

    StepCheck("Проверка отсутствия сообщений об утечках после квитирования", "leaksInfo").actual(leaks_info).is_empty()


# ===== OutputSignals первая утечка =====
@allure.description(LEAK_1.output_signals_test.description)
@allure.title(LEAK_1.output_signals_test.title)
@allure.tag(LEAK_1.output_signals_test.tag)
@pytest.mark.test_case_id(LEAK_1.output_signals_test.test_case_id)
@pytest.mark.offset(LEAK_1.output_signals_test.offset)
@pytest.mark.asyncio
async def test_output_signals_first_leak(ws_client, imitator_start_time):
    await scenarios.output_signals(ws_client, CFG, LEAK_1, imitator_start_time)


# ===== OutputSignals вторая утечка =====
@allure.description(LEAK_2.output_signals_test.description)
@allure.title(LEAK_2.output_signals_test.title)
@allure.tag(LEAK_2.output_signals_test.tag)
@pytest.mark.test_case_id(LEAK_2.output_signals_test.test_case_id)
@pytest.mark.offset(LEAK_2.output_signals_test.offset)
@pytest.mark.asyncio
async def test_output_signals_second_leak(ws_client, imitator_start_time):
    await scenarios.output_signals(ws_client, CFG, LEAK_2, imitator_start_time)

