"""
Сценарии тестов - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import allure
import pytest

from constants.enums import Direction, MessageType, RejectionCriteria
from constants.test_constants import BaseTN3Constants as TestConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import IsRejectedConfig, RejectionTestCase
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser


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

        if rejection_case.expected_criteria_names:
            raw_criteria = (
                target_signal.rejection.get(TestConst.CRITERIA_NAMES_FIELD)
                if isinstance(target_signal.rejection, dict)
                else None
            )
            criteria = RejectionCriteria(raw_criteria) if raw_criteria is not None else None
            StepCheck(
                f"Проверка rejection.criteriaNames для {sensor.description} (id={sensor.id})",
                TestConst.CRITERIA_NAMES_FIELD,
                soft_failures,
            ).actual(criteria).expected(rejection_case.expected_criteria_names).equal_to()


async def rejection_journal(ws_client, cfg: IsRejectedConfig, rejection_case: RejectionTestCase, imitator_start_time):
    """
    Проверка наличия записи об отбраковке в журнале по GetMessagesRequest.
    """
    sensor = rejection_case.sensor
    with allure.step("Подготовка запроса и ожидаемого диапазона времени"):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_REJECT_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(
                messageTypes=int(MessageType.REJECTION),
                objects=FilteringObjects(tuId=cfg.tu_id),
            ),
        )
        range_start, range_end = t_utils.get_rejection_time_window(
            imitator_start_time=imitator_start_time,
            start_seconds=rejection_case.time_range_start_s,
            reserve_seconds=TestConst.SEC_PER_MIN,
        )

    with allure.step("Получение сообщений журнала с фильтром messageTypes=REJECTION"):
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        parsed_payload = parser.parse_journal_msg(payload)
        messages_info = parsed_payload.replyContent.messagesInfo

    with allure.step("Проверка наличия сообщений в журнале"):
        StepCheck("Проверка наличия сообщений в журнале", "messagesInfo").actual(messages_info).is_not_empty()

    with allure.step(
        f"Подготовка сообщений к проверке по диапазону слоя данных "
        f"({rejection_case.time_range_start_s - TestConst.SEC_PER_MIN}-"
        f"{rejection_case.time_range_end_s + TestConst.SEC_PER_MIN} с от старта имитатора)"
    ):
        time_filtered, target_msg = t_utils.find_rejection_journal_message(
            messages_info=messages_info,
            tag=sensor.description,
            range_start=range_start,
            range_end=range_end,
            technological_section=cfg.tu_name,
            expected_event=rejection_case.expected_event,
        )

        allure.attach(
            f"Всего получено сообщений: {len(messages_info)}\n"
            f"Диапазон фильтрации: {range_start} - {range_end}\n"
            f"После фильтрации по tag='{sensor.description}' и времени: {len(time_filtered)}\n"
            f"Найдено ли сообщение с technologicalSection='{cfg.tu_name}' и событием {rejection_case.expected_event}: "
            f"{'True' if target_msg else 'False'}",
            name="Результат фильтрации сообщений журнала",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(
        f"Проверка: найдено ли сообщение с tag='{sensor.description}' (id={sensor.id}) "
        f"в диапазоне {range_start}-{range_end} с"
    ):
        if target_msg is None:
            pytest.fail(
                f"Сообщение с tag='{sensor.description}' (id={sensor.id}) "
                f"и technologicalSection='{cfg.tu_name}' не найдено в диапазоне "
                f"{range_start} - {range_end} "
                f"(всего сообщений: {len(messages_info)}, после фильтрации: {len(time_filtered)})"
            )

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка mainPipeline", "mainPipeline", soft_failures).actual(target_msg.mainPipeline).expected(
            cfg.main_pipeline
        ).equal_to()

        StepCheck("Проверка messageType", "messageType", soft_failures).actual(target_msg.messageType).expected(
            TestConst.JOURNAL_MESSAGE_TYPE_REJECTION
        ).equal_to()

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
            StepCheck("Проверка signalName", "signalName", soft_failures).actual(target_msg.signalName).expected(
                rejection_case.expected_signal_name
            ).equal_to()

        if rejection_case.expected_event:
            StepCheck("Проверка event", "event", soft_failures).actual(
                (target_msg.event.rstrip() or "").strip()
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
        ).actual(parsed_payload.replyContent.signalsInfo.numberOfRejectedSignals).is_greater_than(0)


async def rejection_scheme_signals_state(ws_client, cfg: IsRejectedConfig, rejection_case: RejectionTestCase):
    """
    Проверка отбраковки сигнала по подписке SubscribeSchemeSignalsStateRequest.
    Проверяет isRejected, isMasked, isImitated и rejection.criteriaNames.
    Логирование больших ответов подавляется suppress_recv_logging.
    """
    sensor = rejection_case.sensor
    ws_client.suppress_recv_logging = True
    parser.suppress_recv_logging = True
    try:
        with allure.step(
            f"Подключение по ws, получение данных SchemeSignalsStateContent "
            f"для датчика {sensor.description} (id={sensor.id})"
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

            if target_signal is not None:
                allure.attach(
                    str(target_signal),
                    name=f"Тестируемый фрагмент ответа с бэка: сигнал id={sensor.id} ({sensor.description})",
                    attachment_type=allure.attachment_type.TEXT,
                )
    finally:
        ws_client.suppress_recv_logging = False
        parser.suppress_recv_logging = False

    with allure.step(f"Проверка: найден ли сигнал с id={sensor.id} ({sensor.description})"):
        if target_signal is None:
            pytest.fail(
                f"Сигнал с id={sensor.id} ({sensor.description}) " f"не найден среди {len(signals)} полученных сигналов"
            )

    with SoftAssertions() as soft_failures:
        StepCheck(f"Проверка isRejected для {sensor.description} (id={sensor.id})", "isRejected", soft_failures).actual(
            target_signal.isRejected
        ).expected(True).equal_to()

        StepCheck(f"Проверка isMasked для {sensor.description} (id={sensor.id})", "isMasked", soft_failures).actual(
            target_signal.isMasked
        ).expected(False).equal_to()

        StepCheck(f"Проверка isImitated для {sensor.description} (id={sensor.id})", "isImitated", soft_failures).actual(
            target_signal.isImitated
        ).expected(False).equal_to()

        if rejection_case.expected_criteria_names and target_signal.rejection is not None:
            raw_criteria = (
                target_signal.rejection.get(TestConst.CRITERIA_NAMES_FIELD)
                if isinstance(target_signal.rejection, dict)
                else None
            )
            criteria = RejectionCriteria(raw_criteria) if raw_criteria is not None else None
            StepCheck(
                f"Проверка rejection.criteriaNames для {sensor.description} (id={sensor.id})",
                TestConst.CRITERIA_NAMES_FIELD,
                soft_failures,
            ).actual(criteria).expected(rejection_case.expected_criteria_names).equal_to()
