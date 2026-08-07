"""
Сценарии тестов по режимам МТ - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

from datetime import datetime

import allure
import pytest

from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.enums import Direction, MessageType, StationaryStatus
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import BaseSuiteConfig, CaseData
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


async def stationary_status_check_with_reasons(ws_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка режима работы и причины режима МТ на заданном ДУ
    """
    # Распаковка данных для теста
    pipe_id = test_data.params.get(TestConst.PIPE_ID_KEY)
    expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
    with allure.step("Извлечение и подготовка данных для проверки"):
        # Получает список участков карты течения
        flow_areas = getattr(parsed_payload.replyContent, 'flowAreas', [])
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_pipe_id(flow_areas, pipe_id)
        StepCheck("Проверка наличия данных диагностического участка", "diagnosticAreas").actual(
            diagnostic_area
        ).is_not_none()
        stationary_status_int = getattr(diagnostic_area, 'stationaryStatus', None)
        stationary_status_reasons_int = getattr(diagnostic_area, 'stationaryStatusReasons', None)
        diagnostic_area_stationary_status = StationaryStatus(stationary_status_int) if stationary_status_int else None
    StepCheck(f"Проверка режима работы МТ на ДУ с id:{diagnostic_area.id}", "stationaryStatus").actual(
        diagnostic_area_stationary_status
    ).expected(expected_stationary_status).equal_to()
    stationary_status_reasons = t_utils.parse_stationary_status_reasons(
        stationary_status_int, stationary_status_reasons_int
    )
    StepCheck(f"Проверка причины режима работы МТ на ДУ с id:{diagnostic_area.id}", "stationaryStatusReasons").contains(
        stationary_status_reasons, expected_stationary_status_reasons
    )


def stationary_status_in_journal(http_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка наличия записи в журнале о режиме МТ.
    """
    # Распаковка данных для теста
    if not test_data:
        pytest.fail("Не заполнены данные для теста")
    control_points = test_data.params.get(TestConst.CONTROL_POINTS_KEY, [])
    expected_stationary_status, expected_stationary_status_reasons = (
        test_data.expected_result if test_data.expected_result else None
    ), None

    with allure.step("Http запрос сообщений журнала с фильтром messageTypes=PUMPING_STATUS"):
        end_time = datetime.now()
        start_time = t_utils.datetime_minus_seconds(end_time, TestConst.JOURNAL_STATUS_TOTAL_WAIT)
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_STATUS_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.PUMPING_STATUS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        response = http_client.post_request(HttpConst.GET_MESSAGES_URL_PATH, request_body)
        payload = t_utils.get_json_from_http_response(response)
        parsed_payload = parser.parse_journal_msg(payload)

    with allure.step("Извлечение и подготовка данных для проверки"):
        messages_info = getattr(parsed_payload.replyContent, 'messagesInfo', [])
        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step("Фильтрация сообщений по времени и controlPoint"):
        filter_start_msk = t_utils.localize_as_moscow(start_time)
        filter_end_msk = t_utils.localize_as_moscow(end_time)
        stationary_msg_by_control_points = []
        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)
        # Поиск нужных сообщений по КП
        for control_point in control_points:
            stationary_msg = next(
                (msg for msg in time_filtered if msg.controlPoint == control_point),
                None,
            )
            if stationary_msg:
                stationary_msg_by_control_points.append(stationary_msg)
        StepCheck(
            f"Проверка наличия сообщений c controlPoint из списка {control_points} в журнале", "messagesInfo"
        ).actual(stationary_msg_by_control_points).is_not_empty()
    with SoftAssertions() as soft_failures:
        for msg in stationary_msg_by_control_points:
            msg_event = getattr(msg, 'event', None)
            cp_stationary_status, cp_stationary_status_reasons = t_utils.parse_event(msg_event)
            StepCheck(f"Проверка режима работы МТ на КП:{msg.controlPoint}", "event", soft_failures).actual(
                cp_stationary_status
            ).expected(expected_stationary_status).equal_to()
            StepCheck(f"Проверка причины режима работы МТ на КП:{msg.controlPoint}", "event", soft_failures).contains(
                cp_stationary_status_reasons, expected_stationary_status_reasons
            )
            