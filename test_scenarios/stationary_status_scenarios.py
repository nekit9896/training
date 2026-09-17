"""
Сценарии тестов по режимам МТ - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

from datetime import datetime
from typing import Any

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


def _unpack_stationary_status_test_data(
    test_data: CaseData, require_control_points: bool = False
) -> tuple[Any, Any, list[str]]:
    """
    Проверяет и распаковывает конфигурацию теста режима МТ.
    """
    if not test_data or not test_data.expected_result:
        pytest.fail("Не заполнены данные для теста режима МТ")

    try:
        expected_stationary_status, expected_stationary_status_reasons = test_data.expected_result
    except (TypeError, ValueError) as error:
        pytest.fail(
            "Данные режима МТ должны содержать пару: "
            f"(ожидаемый режим, ожидаемая причина). Получено: {test_data.expected_result}. Ошибка: {error}"
        )

    control_points = (test_data.params or {}).get(TestConst.CONTROL_POINTS_KEY, [])
    if require_control_points and not control_points:
        pytest.fail(f"Не заполнены обязательные параметры для теста: {TestConst.CONTROL_POINTS_KEY}")

    return expected_stationary_status, expected_stationary_status_reasons, control_points


async def stationary_status_common_scheme(ws_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка режима работы и причины режима МТ в сообщении CommonSchemeContent
    """
    # Распаковка данных для теста
    expected_stationary_status, expected_stationary_status_reasons, _ = _unpack_stationary_status_test_data(test_data)
    with allure.step("Подключение по ws, получение и обработка сообщения типа: CommonSchemeContent"):
        payload = await t_utils.connect_and_poll_subscribed_msg(
            ws_client,
            "CommonSchemeContent",
            "SubscribeCommonSchemeRequest",
            {'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_common_scheme_info_msg(payload)
    with allure.step("Извлечение и подготовка данных для проверки"):
        flow_areas = t_utils.filter_flow_areas_with_available_flow(
            getattr(parsed_payload.replyContent, 'flowAreas', [])
        )
        StepCheck(
            "Проверка наличия участков карты течения с доступным течением CommonSchemeContent (ЭФ Схема)", "flowAreas"
        ).actual(flow_areas).is_not_empty()
        longest_flow_area = t_utils.get_longest_flow_area_by_pipes(flow_areas)
        StepCheck(
            "Проверка наличия самого длинного пути течения CommonSchemeContent (ЭФ Схема)", "longest_flow_area"
        ).actual(longest_flow_area is not None).is_true_with_details(
            expected_text="longest_flow_area определён",
            actual_text=(
                "longest_flow_area определён" if longest_flow_area is not None else "longest_flow_area не определён"
            ),
        )
        if longest_flow_area is not None:
            allure.attach(
                str(longest_flow_area),
                name="CommonSchemeContent: самый длинный путь течения (ЭФ Схема)",
                attachment_type=allure.attachment_type.TEXT,
            )
        diagnostic_areas = getattr(longest_flow_area, 'diagnosticAreas', [])
        StepCheck(
            "Проверка наличия данных диагностических участков CommonSchemeContent (ЭФ Схема)", "diagnosticAreas"
        ).actual(diagnostic_areas).is_not_empty()

        common_scheme_stationary_statuses = []
        for diagnostic_area in diagnostic_areas:
            stationary_status_int = getattr(diagnostic_area, 'stationaryStatus', None)
            if stationary_status_int is None:
                continue
            stationary_status = StationaryStatus(stationary_status_int)
            common_scheme_stationary_statuses.append(stationary_status)
        StepCheck(
            "Проверка наличия режимов МТ на ДУ в CommonSchemeContent (ЭФ Схема)",
            "stationaryStatus",
        ).actual(common_scheme_stationary_statuses).is_not_empty()
        common_scheme_majority = t_utils.determine_stationary_status_by_majority(common_scheme_stationary_statuses)
    StepCheck(
        "CommonSchemeContent: общий режим МТ по большинству ДУ (ЭФ Схема)",
        "stationaryStatus",
    ).actual(
        common_scheme_majority
    ).expected(expected_stationary_status).equal_to()
    majority_status_areas = []
    # Получает все ДУ с ожидаемым режимом МТ
    for diagnostic_area in diagnostic_areas:
        if diagnostic_area.stationaryStatus == expected_stationary_status.value:
            majority_status_areas.append(diagnostic_area)
    with SoftAssertions() as soft_failures:
        # Проверяет причину режима МТ у всех ДУ с ожидаемым режимом МТ
        for diagnostic_area in majority_status_areas:
            stationary_status_reasons = t_utils.parse_stationary_status_reasons(
                diagnostic_area.stationaryStatus, diagnostic_area.stationaryStatusReasons, soft_failures
            )
            StepCheck(
                f"Проверка причины режима работы МТ на ДУ с id:{diagnostic_area.id}",
                "stationaryStatusReasons",
                soft_failures,
            ).contains(stationary_status_reasons, expected_stationary_status_reasons)


async def stationary_status_main_page_info(ws_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка установки режима МТ в сообщении MainPageInfoContent
    """
    expected_stationary_status, _, _ = _unpack_stationary_status_test_data(test_data)
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent"):
        payload = await t_utils.connect_and_poll_subscribed_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)
    with allure.step("Извлечение и подготовка данных для проверки"):
        tu_info = getattr(parsed_payload.replyContent, 'tuInfo', None)
        StepCheck("Проверка наличия данных по ТУ", "tuInfo").actual(tu_info).is_not_none()

        main_pipeline_stationary_status = (
            StationaryStatus(tu_info.stationaryStatus) if tu_info.stationaryStatus else None
        )
    with SoftAssertions() as soft_failures:
        StepCheck("Проверка id полученного ТУ", "tu_id", soft_failures).actual(
            parsed_payload.replyContent.tuId
        ).expected(cfg.tu_id).equal_to()

        StepCheck(
            f"Проверка установки режима МТ для ТУ {cfg.tu_name}",
            "stationaryStatus",
            soft_failures,
        ).actual(
            main_pipeline_stationary_status
        ).expected(expected_stationary_status).equal_to()


async def stationary_status_in_output_signals(ws_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка установки режима МТ в сообщении OutputSignalsInfo
    """
    # Распаковка тестовых данных
    expected_stationary_status, _, control_points = _unpack_stationary_status_test_data(
        test_data, require_control_points=True
    )
    unknown_control_points = [name for name in control_points if name not in TestConst.CONTROLLED_SITE_SEGMENTS]
    if unknown_control_points:
        pytest.fail(
            "Для контрольных участков не найдены controlledSiteId/segmentId "
            f"в конфигурации стенда: {unknown_control_points}"
        )
    # получает часть словаря для всего списка controlled_sites_names
    controlled_sites_dict = {
        name: TestConst.CONTROLLED_SITE_SEGMENTS[name]
        for name in control_points
        if name in TestConst.CONTROLLED_SITE_SEGMENTS
    }
    controlled_sites = [
        {'controlledSiteId': controlled_site_id, 'segmentId': segment_id}
        for key, (controlled_site_id, segment_id) in controlled_sites_dict.items()
    ]
    with allure.step("Подключение по ws, получение и обработка сообщения типа: OutputSignalsInfo"):
        output_signals_payload = await t_utils.connect_and_poll_subscribed_msg(
            ws_client,
            "OutputSignalsInfo",
            "SubscribeOutputSignalsRequest",
            {
                'objects': {
                    'linearParts': [],
                    'controlledSites': controlled_sites,
                },
                'signalTypes': 1023,
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_output_signals = parser.parse_output_signals_info_msg(output_signals_payload)
    with allure.step("Извлечение и подготовка данных для проверки"):
        controlled_site_signals = getattr(parsed_output_signals.replyContent, 'controlledSiteSignals', [])
        StepCheck("Проверка наличия данных выходных сигналов", "controlledSiteSignals").actual(
            controlled_site_signals
        ).is_not_empty()
        output_signals_site_stationary_statuses, missed_controlled_points = (
            t_utils.collect_stationary_statuses_from_output_signals(controlled_site_signals, controlled_sites_dict)
        )
        output_signals_details = "\n".join(
            f"{controlled_point}: {stationary_status}"
            for controlled_point, stationary_status in output_signals_site_stationary_statuses
        )
        allure.attach(
            output_signals_details,
            name="OutputSignalsInfo: режимы МТ по участкам КП-КП (ЭФ Выходные сигналы)",
            attachment_type=allure.attachment_type.TEXT,
        )
    with SoftAssertions() as soft_failures:
        for item in output_signals_site_stationary_statuses:
            control_point, stationary_status = item
            StepCheck(
                f"Проверка режима МТ на контрольном участке: {control_point}", "stationaryStatus", soft_failures
            ).actual(stationary_status).expected(expected_stationary_status).equal_to()

        missed_controlled_points_is_empty = not missed_controlled_points
        StepCheck(
            "При обработке Выходных Сигналов найдены записи режима МТ для всех выбранных контрольных участков.",
            "участки КП-КП",
            soft_failures,
        ).actual(missed_controlled_points_is_empty).is_true_with_details(
            expected_text="Контрольные участки, для которых не найдены записи режима МТ missed_controlled_points = []",
            actual_text="Контрольные участки, для которых не найдены записи режима МТ "
            f"missed_controlled_points = {missed_controlled_points}",
        )


def stationary_status_journal(http_client, cfg: BaseSuiteConfig, test_data: CaseData):
    """
    Проверка наличия записи в журнале о режиме МТ.
    """
    # Распаковка данных для теста
    expected_stationary_status, expected_stationary_status_reasons, control_points = (
        _unpack_stationary_status_test_data(test_data, require_control_points=True)
    )

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
        missed_control_points = []
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
            else:
                missed_control_points.append(control_point)
        StepCheck("Проверка наличия сообщений c controlPoint из списка в журнале", "messagesInfo").actual(
            stationary_msg_by_control_points
        ).is_not_empty()
    with SoftAssertions() as soft_failures:
        for msg in stationary_msg_by_control_points:
            msg_event = getattr(msg, 'event', None)
            cp_stationary_status, cp_stationary_status_reasons = t_utils.parse_journal_event(msg_event)
            StepCheck(f"Проверка режима работы МТ на КП:{msg.controlPoint}", "event", soft_failures).actual(
                cp_stationary_status
            ).expected(expected_stationary_status).equal_to()
            StepCheck(f"Проверка причины режима работы МТ на КП:{msg.controlPoint}", "event", soft_failures).contains(
                cp_stationary_status_reasons, expected_stationary_status_reasons
            )
        missed_control_points_is_empty = not missed_control_points
        StepCheck(
            "При обработке сообщений журнала найдены сообщения для всех КП.",
            "controlPoint",
            soft_failures,
        ).actual(missed_control_points_is_empty).is_true_with_details(
            expected_text="КП, для которых не найдены сообщения missed_control_points = []",
            actual_text=f"КП, для которых не найдены сообщения missed_control_points = {missed_control_points}",
        )
