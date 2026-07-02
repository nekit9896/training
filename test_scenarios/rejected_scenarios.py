"""
Сценарии тестов - функции-обёртки без pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

from datetime import datetime, timedelta

import allure
import pytest

from constants.enums import (
    Direction,
    ExportedDataType,
    ExportStatus,
    MessageType,
    RejectionCriteria,
    RejectionSensorTag,
    ReplyStatus,
)
from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportRejectedReportConstants as RejectedReportConst
from constants.test_constants import ExportReportConstants as ReportConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import ExportRejectedReportState, IsRejectedConfig, RejectionTestCase
from utils.helpers import rejection_report_xlsx_utils as rejection_report_utils
from utils.helpers import report_xlsx_utils as report_utils
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
        _parsed_payload, target_signal = await t_utils.connect_and_poll_subscribed_signal(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [sensor.id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
            sensor.id,
            sensor.description,
            parser.parse_input_signals_info_msg,
            lambda parsed: parsed.replyContent.inputSignals,
        )

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
    expected_event = rejection_case.expected_event
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
            expected_event=expected_event,
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

        if expected_event:
            StepCheck("Проверка event", "event", soft_failures).actual(
                (target_msg.event.rstrip() or "").strip()
            ).expected(expected_event).equal_to()


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
            _parsed_payload, target_signal = await t_utils.connect_and_poll_subscribed_signal(
                ws_client,
                "SchemeSignalsStateContent",
                "SubscribeSchemeSignalsStateRequest",
                {'tuId': cfg.tu_id},
                sensor.id,
                sensor.description,
                parser.parse_scheme_signals_state_msg,
                lambda parsed: parsed.replyContent.signalsStates,
            )

            allure.attach(
                str(target_signal),
                name=f"Тестируемый фрагмент ответа с бэка: сигнал id={sensor.id} ({sensor.description})",
                attachment_type=allure.attachment_type.TEXT,
            )
    finally:
        ws_client.suppress_recv_logging = False
        parser.suppress_recv_logging = False

    with SoftAssertions() as soft_failures:
        StepCheck(f"Проверка isRejected для {sensor.description} (id={sensor.id})", "isRejected", soft_failures).actual(
            target_signal.isRejected
        ).expected(rejection_case.expected_is_rejected).equal_to()

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


async def export_rejection_report(ws_client, cfg: IsRejectedConfig, imitator_start_time: datetime):
    """
    Сценарий формирования общего xlsx-отчёта об отбракованных входных данных.

    Этапы:
    1. Подписка SubscribeReportsDataExportedRequest на пуш-нотификации.
    2. ExportReportsCommandRequest с периодом от старта имитатора до offset теста.
    3. Ожидание ReportDataExportedNotification.
    4. Лонг-поллинг GetExportedDataListRequest до появления отчёта в списке.
    5. DownloadExportedDataRequest и получение fileChunk.
    6. Проверка формата, имени файла, двойной шапки и строк по RejectionTestCase.
    """
    report_state = ExportRejectedReportState()

    with allure.step("Подготовка параметров сценария формирования отчёта об отбракованных входных данных"):
        # offset теста задаёт конец периода отчёта - после всех отдельных проверок отбраковок
        report_state.expected_report_test = cfg.rejection_report_test
        StepCheck("В конфигурации задан rejection_report_test", "rejection_report_test").actual(
            report_state.expected_report_test
        ).is_not_none()

        report_state.expected_period_start = t_utils.localize_as_moscow(imitator_start_time)
        report_state.expected_period_end = t_utils.localize_as_moscow(
            imitator_start_time + timedelta(minutes=report_state.expected_report_test.offset)
        )
        report_state.expected_period_start_naive = report_utils.normalize_report_period_naive(
            report_state.expected_period_start
        )
        report_state.expected_period_end_naive = report_utils.normalize_report_period_naive(
            report_state.expected_period_end
        )
        report_state.expected_tu_description_lower = cfg.technological_unit.description.lower()
        report_state.expected_file_name = report_utils.build_export_report_file_name(
            cfg.technological_unit.description,
            report_state.expected_period_start,
            report_state.expected_period_end,
            RejectedReportConst.REJECTED_REPORT_NAME_PART,
            " ",
        )
        time_offset_hours = t_utils.report_time_offset_hours()
        StepCheck(
            f"Смещение timeOffset для запросов отчёта (часовой пояс {TestConst.ZONE_INFO})",
            "time_offset_hours",
        ).actual(time_offset_hours).is_not_none()
        report_state.actual_time_offset_hours = time_offset_hours

        allure.attach(
            f"period.start={report_state.expected_period_start}\n"
            f"period.end={report_state.expected_period_end}\n"
            f"offset_minutes={report_state.expected_report_test.offset}",
            name="Фильтр периода отчёта об отбраковках",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(f"Этап 1. Подписка на пуш-нотификации ({ReportConst.SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST})"):
        # без подписки не придёт уведомление о готовности отчёта
        await t_utils.connect(ws_client, ReportConst.SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST, [])

    with allure.step(f"Этап 2. Запрос формирования отчёта ({ReportConst.EXPORT_REPORTS_COMMAND_REQUEST})"):
        request_payload = {
            "tuId": cfg.tu_id,
            "exportedDataTypes": [ExportedDataType.REJECTED_REPORT.value],
            "timeOffset": report_state.actual_time_offset_hours,
            "period": {
                "start": t_utils.datetime_to_msgpack_timestamp(report_state.expected_period_start),
                "end": t_utils.datetime_to_msgpack_timestamp(report_state.expected_period_end),
                "additionalProperties": {},
            },
        }
        await t_utils.connect(ws_client, ReportConst.EXPORT_REPORTS_COMMAND_REQUEST, request_payload)

    with allure.step(
        f"Этап 3. Ожидание пуш-нотификации {ReportConst.REPORT_DATA_EXPORTED_NOTIFICATION} о готовности отчёта"
    ):
        report_state.actual_notification = await t_utils.poll_for_report_export_notification(
            ws_client=ws_client,
            parser=parser,
            total_wait_seconds=ReportConst.NOTIFICATION_TIMEOUT_SECONDS,
            poll_interval_seconds=ReportConst.LIST_POLL_INTERVAL_SECONDS,
        )

    with allure.step(f"Этап 4. Лонг-поллинг {ReportConst.GET_EXPORTED_DATA_LIST_REQUEST} до появления отчёта в списке"):
        report_state.actual_report_item = await t_utils.poll_for_exported_file(
            ws_client=ws_client,
            parser=parser,
            list_limit=ReportConst.EXPORTED_DATA_LIST_LIMIT,
            expected_data_type=ExportedDataType.REJECTED_REPORT,
            name_substring=RejectedReportConst.REJECTED_REPORT_NAME_PART,
            tu_name_substring=cfg.technological_unit.description,
            period_start=report_state.expected_period_start,
            period_end=report_state.expected_period_end,
            total_wait_seconds=ReportConst.LIST_POLL_TOTAL_WAIT_SECONDS,
            poll_interval_seconds=ReportConst.LIST_POLL_INTERVAL_SECONDS,
        )

        with allure.step("Подготовка данных найденного отчёта в списке"):
            report_item = report_state.actual_report_item
            if report_item is not None:
                allure.attach(
                    f"id={report_item.id}, name={report_item.name}, "
                    f"exportedDataType={report_item.exportedDataType}, "
                    f"start={t_utils.format_datetime_moscow(report_item.start)}, "
                    f"end={t_utils.format_datetime_moscow(report_item.end)}",
                    name="Найденный отчёт в списке",
                    attachment_type=allure.attachment_type.TEXT,
                )

        with allure.step("Проверка: отчёт найден в списке сформированных файлов"):
            StepCheck("Отчёт найден в списке сформированных файлов", "report_item").actual(
                report_state.actual_report_item
            ).is_not_none()

    with allure.step(
        f"Этап 5. Streaming-вызов {ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST} "
        f"по id={report_state.actual_report_item.id}"
    ):
        download_request = {
            "exportedDataId": report_state.actual_report_item.id,
            "exportedDataType": ExportedDataType.REJECTED_REPORT.to_download_name(),
            "additionalProperties": None,
            "timeOffset": report_state.actual_time_offset_hours,
        }
        download_purpose = (
            f"скачивание xlsx-отчёта об отбракованных входных данных "
            f"(exportedDataId={report_state.actual_report_item.id}) "
            f"после формирования отчёта и выбора файла в списке GetExportedDataListRequest"
        )
        await t_utils.connect_stream(
            ws_client,
            ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST,
            download_request,
            purpose=download_purpose,
        )
        report_state.actual_download_invocation_id = ws_client.invocation_id

    with allure.step("Этап 6. Получение fileChunk - скачивание отчёта об отбракованных входных данных"):
        report_state.actual_download_reply = await t_utils.receive_download_exported_data_reply(
            ws_client=ws_client,
            parser=parser,
            invocation_id=report_state.actual_download_invocation_id,
            request_name=ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST,
            total_wait_seconds=ReportConst.DOWNLOAD_TIMEOUT_SECONDS,
            purpose=download_purpose,
        )

        with allure.step("Извлечение данных ответа на скачивание"):
            download_reply = report_state.actual_download_reply
            download_reply_status = download_reply.replyStatus
            has_download_reply_content = download_reply.replyContent is not None
            report_state.actual_file_bytes = (
                download_reply.replyContent.fileChunk if has_download_reply_content else None
            )
            is_xlsx_signature = (
                report_utils.is_xlsx_file_bytes(report_state.actual_file_bytes)
                if report_state.actual_file_bytes
                else False
            )

        with allure.step("Проверка ответа на скачивание и формата xlsx"):
            StepCheck("Проверка статуса ответа на скачивание", "replyStatus").actual(download_reply_status).expected(
                ReplyStatus.OK.value
            ).equal_to()
            StepCheck("Проверка наличия контента ответа на скачивание", "replyContent").actual(
                has_download_reply_content
            ).expected(True).equal_to()
            StepCheck("Проверка наличия байт файла", "fileChunk").actual(report_state.actual_file_bytes).is_not_empty()
            StepCheck("Проверка xlsx (zip) сигнатуры файла", "file_signature").actual(is_xlsx_signature).expected(
                True
            ).equal_to()

        with allure.step("Подготовка данных для проверки имени файла отчёта"):
            # имя файла берём из ответа бэка (список сформированных отчётов), не из шапки xlsx
            actual_file_name = report_state.actual_report_item.name if report_state.actual_report_item else ""
            actual_file_name_lower = actual_file_name.lower()
            file_name_period_start, file_name_period_end = report_utils.parse_period_from_export_file_name(
                actual_file_name,
                RejectedReportConst.REPORT_FILE_NAME_PERIOD_PATTERN,
            )
            period_start_lo, period_start_hi, period_end_lo, period_end_hi = (
                report_utils.report_period_comparison_bounds(
                    report_state.expected_period_start_naive,
                    report_state.expected_period_end_naive,
                )
            )
            has_xlsx_extension = report_utils.is_xlsx_extension(actual_file_name)
            rejected_report_file_name_part_lower = RejectedReportConst.REJECTED_REPORT_NAME_PART.lower()
            rejected_report_file_name_part_alt_lower = RejectedReportConst.REJECTED_REPORT_NAME_PART_ALT.lower()

    try:
        with allure.step("Этап 7. Сохранение и разбор xlsx-отчёта об отбракованных входных данных"):
            report_state.actual_temp_file_path = report_utils.save_report_bytes_to_temp_file(
                report_state.actual_file_bytes,
                prefix="rejected_report_",
            )
            StepCheck("Временный xlsx файл создан", "temp_file_path").actual(
                report_state.actual_temp_file_path
            ).is_not_none()
            report_state.actual_worksheet = report_utils.load_report_worksheet(report_state.actual_temp_file_path)
            report_state.actual_title_info = report_utils.parse_report_title(
                report_utils.get_report_title_cell(report_state.actual_worksheet),
                RejectedReportConst.REPORT_HEADER_PERIOD_PATTERN,
            )
            allure.attach(
                f"Шапка (raw): {report_state.actual_title_info.raw_title}\n"
                f"period_start: {report_state.actual_title_info.period_start}\n"
                f"period_end: {report_state.actual_title_info.period_end}",
                name="Первая строка шапки xlsx-отчёта",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Этап 8. Извлечение строк данных из отчёта"):
            report_state.actual_data_rows = rejection_report_utils.iter_rejection_report_rows(
                report_state.actual_worksheet
            )
            report_state.actual_monitored_tag_rows = rejection_report_utils.filter_rows_by_monitored_tags(
                report_state.actual_data_rows,
                RejectionSensorTag,
            )
            allure.attach(
                rejection_report_utils.format_rejection_rows_for_allure(report_state.actual_monitored_tag_rows),
                name="Строки отчёта по тегам RejectionSensorTag",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Подготовка данных шапки xlsx для проверки"):
            title_info = report_state.actual_title_info
            report_state.actual_header_column_headers = report_utils.get_report_column_headers(
                report_state.actual_worksheet,
                headers_row=RejectedReportConst.REPORT_COLUMN_HEADERS_ROW,
            )
            report_state.actual_header_period_start = title_info.period_start
            report_state.actual_header_period_end = title_info.period_end
            report_state.actual_header_contains_expected_title = (
                rejection_report_utils.report_header_contains_expected_title(title_info.raw_title)
            )

        with allure.step("Подготовка данных для проверки строк отчёта по RejectionTestCase"):
            report_state.actual_case_checks = rejection_report_utils.prepare_rejection_report_case_checks(
                report_state.actual_monitored_tag_rows,
                cfg.rejection_cases,
                imitator_start_time,
            )

        with allure.step("Проверка первой строки шапки xlsx-отчёта"):
            StepCheck("Лист xlsx открыт", "worksheet").actual(report_state.actual_worksheet).is_not_none()
            with SoftAssertions() as soft_failures:
                StepCheck(
                    "Первая строка шапки содержит заголовок отчёта об отбракованных входных данных",
                    "report_title",
                    soft_failures,
                ).actual(report_state.actual_header_contains_expected_title).expected(True).equal_to()
                StepCheck(
                    "Время начала периода в первой строке шапки совпадает с фильтром запроса (+-1 мин)",
                    "period_start",
                    soft_failures,
                ).actual(report_state.actual_header_period_start).is_between(period_start_lo, period_start_hi)
                StepCheck(
                    "Время конца периода в первой строке шапки совпадает с фильтром запроса (+-1 мин)",
                    "period_end",
                    soft_failures,
                ).actual(report_state.actual_header_period_end).is_between(period_end_lo, period_end_hi)
                StepCheck(
                    "Названия колонок во второй строке шапки отчёта",
                    "column_headers",
                    soft_failures,
                ).actual(
                    report_state.actual_header_column_headers
                ).expected(RejectedReportConst.EXPECTED_COLUMN_HEADERS).equal_to()

        with allure.step("Проверка строк отчёта по каждому RejectionTestCase из конфигурации набора"):
            with SoftAssertions() as soft_failures:
                for case_check in report_state.actual_case_checks:
                    StepCheck(
                        f"В отчёте найдена отбраковка для {case_check.case_label} в интервале времени "
                        f"{case_check.window_start} - {case_check.window_end}",
                        RejectedReportConst.COL_TAG,
                        soft_failures,
                    ).actual(case_check.row_found).is_true_with_details(
                        expected_text=(
                            f"найдена строка с тегом {case_check.tag_description} "
                            f"и событием '{case_check.report_event}'"
                        ),
                        actual_text=case_check.found_row_summary,
                    )

                    if not case_check.row_found:
                        continue

                    StepCheck(
                        f"Для {case_check.case_label} время получения отбраковки в допустимом диапазоне",
                        RejectedReportConst.COL_DATETIME,
                        soft_failures,
                    ).actual(case_check.datetime_in_window).is_true_with_details(
                        expected_text=(f"дата и время в диапазоне {case_check.window_start} — {case_check.window_end}"),
                        actual_text=case_check.datetime_actual_text,
                    )

                    StepCheck(
                        f"Для {case_check.case_label} суммарная продолжительность отбраковки "
                        f"({case_check.expected_duration_text}) совпадает",
                        RejectedReportConst.COL_DURATION,
                        soft_failures,
                    ).actual(case_check.actual_duration_seconds).expected(
                        case_check.expected_duration_seconds
                    ).equal_to()

                    StepCheck(
                        f"Для {case_check.case_label} участок трубопровода в колонке "
                        f"'{RejectedReportConst.COL_OBJECT}' не пустой",
                        RejectedReportConst.COL_OBJECT,
                        soft_failures,
                    ).actual(case_check.pipe_section).is_not_empty()

                    StepCheck(
                        f"Для {case_check.case_label} после последней точки в колонке "
                        f"'{RejectedReportConst.COL_OBJECT}' указан сигнал '{case_check.expected_signal_suffix}'",
                        RejectedReportConst.COL_OBJECT,
                        soft_failures,
                    ).actual(case_check.actual_signal_suffix).expected(case_check.expected_signal_suffix).equal_to()

    except Exception:
        with allure.step("Прикрепление xlsx отчёта к Allure при падении теста"):
            attachment_name = (
                report_state.actual_report_item.name
                if report_state.actual_report_item and report_state.actual_report_item.name
                else report_state.expected_file_name
            )
            if report_state.actual_temp_file_path and attachment_name:
                report_utils.attach_report_file_to_allure(report_state.actual_temp_file_path, attachment_name)
        raise

    with allure.step("Проверка имени файла отчёта из списка сформированных файлов"):
        with SoftAssertions() as soft_failures:
            StepCheck(f"Имя файла оканчивается на {ReportConst.XLSX_EXTENSION}", "file_name", soft_failures).actual(
                has_xlsx_extension
            ).expected(True).equal_to()
            StepCheck(
                "Имя файла из ответа бэка содержит название отчёта об отбракованных входных данных",
                "file_name",
                soft_failures,
            ).actual(
                rejected_report_file_name_part_lower in actual_file_name_lower
                or rejected_report_file_name_part_alt_lower in actual_file_name_lower
            ).expected(
                True
            ).equal_to()
            StepCheck(
                f"Имя файла содержит описание ТУ '{cfg.technological_unit.description}'",
                "file_name",
                soft_failures,
            ).contains(actual_file_name_lower, report_state.expected_tu_description_lower)
            StepCheck(
                "Дата начала периода в имени файла совпадает с фильтром запроса (+-1 мин)",
                "period_start_in_file_name",
                soft_failures,
            ).actual(file_name_period_start).is_between(period_start_lo, period_start_hi)
            StepCheck(
                "Дата конца периода в имени файла совпадает с фильтром запроса (+-1 мин)",
                "period_end_in_file_name",
                soft_failures,
            ).actual(file_name_period_end).is_between(period_end_lo, period_end_hi)

    with allure.step("Проверка пуш-нотификации о готовности отчёта"):
        notification = report_state.actual_notification
        notification_reply_status = notification.replyStatus if notification else None
        notification_reply_content = notification.replyContent if notification else None
        notification_export_status = notification_reply_content.exportStatus if notification_reply_content else None
        notification_error_message = (
            (notification_reply_content.errorMessage or "") if notification_reply_content else ""
        )
        with SoftAssertions() as soft_failures:
            StepCheck("Получена пуш-нотификация о готовности отчёта", "notification", soft_failures).actual(
                report_state.actual_notification
            ).is_not_none()
            StepCheck("Проверка статуса пуш-нотификации", "replyStatus", soft_failures).actual(
                notification_reply_status
            ).expected(ReplyStatus.OK.value).equal_to()
            StepCheck("Проверка наличия контента нотификации", "replyContent", soft_failures).actual(
                notification_reply_content
            ).is_not_none()
            StepCheck("Проверка exportStatus в нотификации", "exportStatus", soft_failures).actual(
                notification_export_status
            ).expected(ExportStatus.DONE).equal_to()
            StepCheck("В нотификации нет текста ошибки", "errorMessage", soft_failures).actual(
                notification_error_message
            ).is_empty()
