"""
Сценарии тестов по режимам СОУ - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import time
from datetime import datetime

import allure

from constants.architecture_constants import HTTPClientConstants as HttpConst
from constants.enums import Direction, LdsStatus, MessageType, ReplyStatus, StationaryStatus
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import CaseData, LDSStatusConfig, SmokeSuiteConfig
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


async def lds_status_check_on_longest_flow_area(ws_client, cfg: LDSStatusConfig, test_data: CaseData):
    """
    Проверка Инициализации и причины инициализации СОУ на самом протяженном участке карты течений
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
    with allure.step("Извлечение и подготовка данных для проверки"):
        # Получает список участков карты течения
        flow_areas = getattr(parsed_payload.replyContent, 'flowAreas', [])
        # Получает самый протяженный участок карты течения
        longest_flow_area = t_utils.get_longest_flow_area(flow_areas)
        # Получает список ДУ
        diagnostic_areas = getattr(longest_flow_area, 'diagnosticAreas', [])
        StepCheck("Проверка наличия данных диагностических участков", "diagnosticAreas").actual(
            diagnostic_areas
        ).is_not_empty()
    with SoftAssertions() as soft_failures:
        for diagnostic_area in diagnostic_areas:
            diagnostic_area_lds_status = LdsStatus(diagnostic_area.ldsStatus) if diagnostic_area.ldsStatus else None
            StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus", soft_failures).actual(
                diagnostic_area_lds_status
            ).expected(expected_lds_status).equal_to()
            lds_status_reasons = t_utils.parse_lds_status_reasons(
                diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons, soft_failures
            )
            StepCheck(
                f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
            ).contains(lds_status_reasons, expected_lds_status_reasons)


async def lds_status_check_with_reasons(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData):
    """
    Проверка режима работы и причины режима СОУ на заданном ДУ
    """
    # Распаковка данных для теста
    pipe_id = test_data.params.get("pipe_id")
    expected_lds_status, expected_lds_status_reasons = test_data.expected_result
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
        diagnostic_area_lds_status = LdsStatus(diagnostic_area.ldsStatus) if diagnostic_area.ldsStatus else None
    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area_lds_status
    ).expected(expected_lds_status).equal_to()
    if diagnostic_area_lds_status != LdsStatus.SERVICEABLE:
        lds_status_reasons = t_utils.parse_lds_status_reasons(
            diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons
        )
        StepCheck(f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons").contains(
            lds_status_reasons, expected_lds_status_reasons
        )


async def lds_status_check_with_2_reasons(ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData):
    """
    Проверка режима работы СОУ и двух причин режима работы СОУ на заданном ДУ
    """
    # Распаковка данных для теста
    pipe_id = test_data.params.get("pipe_id")
    expected_lds_status, expected_lds_status_reason_1, expected_lds_status_reason_2 = test_data.expected_result
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
        diagnostic_area_lds_status = LdsStatus(diagnostic_area.ldsStatus) if diagnostic_area.ldsStatus else None

    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area_lds_status
    ).expected(expected_lds_status).equal_to()
    if diagnostic_area_lds_status != LdsStatus.SERVICEABLE:
        with SoftAssertions() as soft_failures:
            lds_status_reasons = t_utils.parse_lds_status_reasons(
                diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons, soft_failures
            )
            StepCheck(
                f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
            ).contains(lds_status_reasons, expected_lds_status_reason_1)
            StepCheck(
                f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
            ).contains(lds_status_reasons, expected_lds_status_reason_2)


async def lds_status_check_on_multiple_diagnostic_areas(
    ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData
):
    """
    Проверка режима работы и причины режима СОУ на заданных ДУ
    """
    # Распаковка данных для теста
    pipe_ids = test_data.params.get("pipe_ids")
    expected_result = test_data.expected_result
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )

        parsed_payload = parser.parse_common_scheme_info_msg(payload)
    with allure.step("Извлечение и подготовка данных для проверки"):
        flow_areas = getattr(parsed_payload.replyContent, 'flowAreas', [])
        diagnostic_areas = t_utils.find_diagnostic_areas_by_pipe_ids(flow_areas, pipe_ids)
        StepCheck("Проверка наличия данных диагностических участков", "diagnosticAreas").actual(
            diagnostic_areas
        ).is_not_empty()
        lds_status_set = {diagnostic_area.ldsStatus for diagnostic_area in diagnostic_areas}
        lds_status_int = t_utils.determine_lds_status_by_priority(lds_status_set)
        lds_status = LdsStatus(lds_status_int) if lds_status_int else None

    StepCheck(
        "Проверка режима работы СОУ на заданных ДУ",
        "ldsStatus",
    ).actual(
        lds_status
    ).expected(expected_result).equal_to()


async def lds_and_stationary_status_check_with_reasons(
    ws_client, cfg: SmokeSuiteConfig | LDSStatusConfig, test_data: CaseData
):
    """
    Проверка режима работы и причины режима СОУ и МТ на заданном ДУ
    """
    # Распаковка данных для теста
    pipe_id = test_data.params.get("pipe_id")
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
    with allure.step("Извлечение и подготовка данных для проверки"):
        # Получает список участков карты течения
        flow_areas = getattr(parsed_payload.replyContent, 'flowAreas', [])
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_pipe_id(flow_areas, pipe_id)
        StepCheck("Проверка наличия данных диагностического участка", "diagnosticAreas").actual(
            diagnostic_area
        ).is_not_none()
        diagnostic_area_lds_status = LdsStatus(diagnostic_area.ldsStatus) if diagnostic_area.ldsStatus else None
        diagnostic_area_stationary_status = (
            StationaryStatus(diagnostic_area.stationaryStatus) if diagnostic_area.stationaryStatus else None
        )

    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area_lds_status
    ).expected(expected_lds_status).equal_to()
    StepCheck(f"Проверка режима работы МТ на ДУ с id:{diagnostic_area.id}", "stationaryStatus").actual(
        diagnostic_area_stationary_status
    ).expected(expected_stationary_status).equal_to()
    with SoftAssertions() as soft_failures:
        lds_status_reasons = t_utils.parse_lds_status_reasons(
            diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons, soft_failures
        )
        stationary_status_reasons = t_utils.parse_stationary_status_reasons(
            diagnostic_area.stationaryStatus, diagnostic_area.stationaryStatusReasons, soft_failures
        )
        StepCheck(
            f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons", soft_failures
        ).contains(lds_status_reasons, expected_lds_status_reasons)
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
    pipe_id = test_data.params.get("pipe_id")
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
    with allure.step("Извлечение и подготовка данных для проверки"):
        # Получает список участков карты течения
        flow_areas = getattr(parsed_payload.replyContent, 'flowAreas', [])
        # Получает ДУ
        diagnostic_area = t_utils.find_diagnostic_area_by_pipe_id(flow_areas, pipe_id)
        StepCheck("Проверка наличия данных диагностического участка", "diagnosticAreas").actual(
            diagnostic_area
        ).is_not_none()
        diagnostic_area_lds_status = LdsStatus(diagnostic_area.ldsStatus) if diagnostic_area.ldsStatus else None

    StepCheck(f"Проверка режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatus").actual(
        diagnostic_area_lds_status
    ).expected(expected_lds_status).equal_to()
    lds_status_reasons = t_utils.parse_lds_status_reasons(diagnostic_area.ldsStatus, diagnostic_area.ldsStatusReasons)
    StepCheck(f"Проверка причины режима работы СОУ на ДУ с id:{diagnostic_area.id}", "ldsStatusReasons").contains(
        lds_status_reasons, expected_lds_status_reasons
    )
    StepCheck("Проверка кода ответа на запрос о запуске СОД", "replyStatus").actual(launch_pig_reply_status).expected(
        ReplyStatus.OK.value
    ).equal_to()


def lds_status_in_journal(http_client, cfg: LDSStatusConfig, test_data: CaseData):
    """
    Проверка наличия записи в журнале о выходе СОУ из режима Инициализация.
    """
    # Распаковка данных для теста
    control_points = test_data.params.get("control_points")
    if isinstance(test_data.expected_result, tuple):
        expected_lds_status, expected_lds_status_reasons = test_data.expected_result
    else:
        expected_lds_status, expected_lds_status_reasons = test_data.expected_result, None

    with allure.step("Http запрос сообщений журнала с фильтром messageTypes=MASKING_LDS"):
        end_time = datetime.now()
        start_time = t_utils.datetime_minus_seconds(end_time, TestConst.JOURNAL_STATUS_TOTAL_WAIT)
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_STATUS_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LDS_STATUS), objects=FilteringObjects(tuId=cfg.tu_id)),
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
        lds_msg_by_control_points = []
        time_filtered = [
            msg
            for msg in messages_info
            if filter_start_msk <= t_utils.ensure_moscow_timezone(msg.time) <= filter_end_msk
        ]
        time_filtered.sort(key=lambda msg: t_utils.ensure_moscow_timezone(msg.time), reverse=True)
        # Поиск нужных сообщений по КП
        for control_point in control_points:
            lds_msg = next(
                (msg for msg in time_filtered if msg.controlPoint == control_point),
                None,
            )
            if lds_msg:
                lds_msg_by_control_points.append(lds_msg)
        StepCheck(
            f"Проверка наличия сообщений c controlPoint из списка {control_points} в журнале", "messagesInfo"
        ).actual(lds_msg_by_control_points).is_not_empty()
    with SoftAssertions() as soft_failures:
        for msg in lds_msg_by_control_points:
            msg_event = getattr(msg, 'event', None)
            cp_lds_status, cp_lds_status_reasons = t_utils.parse_event(msg_event)
            StepCheck(f"Проверка режима работы СОУ на КП:{msg.controlPoint}", "event", soft_failures).actual(
                cp_lds_status
            ).expected(expected_lds_status).equal_to()
            if cp_lds_status != LdsStatus.SERVICEABLE.report_text:
                StepCheck(
                    f"Проверка причины режима работы СОУ на КП:{msg.controlPoint}", "event", soft_failures
                ).contains(cp_lds_status_reasons, expected_lds_status_reasons)
