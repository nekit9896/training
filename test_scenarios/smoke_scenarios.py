"""
Сценарии тестов - функции-обёртки без
pytest маркеров.

Каждая функция содержит логику одного теста.
Pytest маркеры и allure декораторы применяются в тестовых файлах.
"""

import time
from datetime import datetime, timedelta

import allure
import pytest

from constants.enums import (
    ConfirmationStatus,
    Direction,
    ExportedDataType,
    ExportStatus,
    GravityPipe,
    LdsStatus,
    LeakStatus,
    MessageType,
    ReplyStatus,
    SignalType,
    SiteKpKp,
    StationaryStatus,
    UserActions,
)
from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportReportConstants as ReportConst
from models.get_messages_model import Filtering, FilteringObjects, Pagination
from test_config.models_for_tests import (
    CaseData,
    ExportLeaksReportState,
    LDSStatusConfig,
    LeakTestConfig,
    SmokeSuiteConfig,
)
from utils.helpers import report_xlsx_utils as report_utils
from utils.helpers import ws_test_utils as t_utils
from utils.helpers.asserts import SoftAssertions, StepCheck
from utils.helpers.ws_message_parser import ws_message_parser as parser
from utils.helpers.ws_test_utils import get_value


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


async def diagnostics_of_signals_after_initialization(
    ws_client,
    cfg: SmokeSuiteConfig,
):
    """
    Проверка выходных сигналов после окончания режима Инициализация по причине "холодного" пуска  СОУ.

    """

    with allure.step("Подписка на сигналы для участков"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "OutputSignalsInfo",
            "SubscribeOutputSignalsRequest",
            {
                'objects': {
                    'linearParts': [],
                    'controlledSites': [
                        SiteKpKp.TIXORECZKAYA_NOVOVELICHKOVSKAYA.value,
                        SiteKpKp.NOVOVELICHKOVSKAYA_KRYMSKAYA.value,
                        SiteKpKp.KRYMSKAYA_GRUSHOVAYA.value,
                        SiteKpKp.BACKUP_ROUTE_BEJSUG.value,
                        SiteKpKp.BACKUP_ROUTE_PONURA.value,
                        SiteKpKp.BACKUP_ROUTE_KUBAN.value,
                        SiteKpKp.NPZ_AFIPSKIJ.value,
                        SiteKpKp.NPZ_ILINSKIJ.value,
                    ],
                },
                'signalTypes': 1023,
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )

        parsed_payload = parser.parse_output_signals_info_msg(payload)
        controlled_site_dict = {
            "controlled_site_first": SiteKpKp.TIXORECZKAYA_NOVOVELICHKOVSKAYA.value,
            "controlled_site_second": SiteKpKp.NOVOVELICHKOVSKAYA_KRYMSKAYA.value,
            "controlled_site_third": SiteKpKp.KRYMSKAYA_GRUSHOVAYA.value,
            "controlled_site_fourth": SiteKpKp.BACKUP_ROUTE_BEJSUG.value,
            "controlled_site_fifth": SiteKpKp.BACKUP_ROUTE_PONURA.value,
            "controlled_site_sixth": SiteKpKp.BACKUP_ROUTE_KUBAN.value,
            "controlled_site_seventh": SiteKpKp.NPZ_AFIPSKIJ.value,
            "controlled_site_eight": SiteKpKp.NPZ_ILINSKIJ.value,
        }

        controlled_site_messages = {}
        for name, key in controlled_site_dict.items():
            controlled_site_messages[name] = t_utils.find_object_by_a_few_fields(
                parsed_payload.replyContent.controlledSiteSignals, key
            )

        all_signals = {}
        for site_name, site_message in controlled_site_messages.items():
            signal_dict = {'pump': None, 'sou': None, 'gravity': None}
            if site_message:
                all_signals[site_name] = {
                    'pump': t_utils.get_signal(site_message, SignalType.REGLU),
                    'sou': t_utils.get_signal(site_message, SignalType.REGSOU),
                    'gravity': t_utils.get_signal(site_message, SignalType.GRAVITYPIPE),
                }
            else:
                all_signals[site_name] = signal_dict

        first_kp_kp = all_signals.get("controlled_site_first") or {}
        if first_kp_kp:
            first_site_signal_pump = get_value(first_kp_kp.get("pump"))
            first_site_signal_sou = get_value(first_kp_kp.get("sou"))
            first_site_signal_gravity = get_value(first_kp_kp.get("gravity"))

        second_kp_kp = all_signals.get("controlled_site_second") or {}
        if second_kp_kp:
            second_site_signal_pump = get_value(second_kp_kp.get("pump"))
            second_site_signal_sou = get_value(second_kp_kp.get("sou"))
            second_site_signal_gravity = get_value(second_kp_kp.get("gravity"))

        third_kp_kp = all_signals.get("controlled_site_third") or {}
        if third_kp_kp:
            third_site_signal_pump = get_value(third_kp_kp.get("pump"))
            third_site_signal_sou = get_value(third_kp_kp.get("sou"))
            third_site_signal_gravity = get_value(third_kp_kp.get("gravity"))

        fourth_kp_kp = all_signals.get("controlled_site_fourth") or {}
        if fourth_kp_kp:
            fourth_site_signal_pump = get_value(fourth_kp_kp.get("pump"))
            fourth_site_signal_sou = get_value(fourth_kp_kp.get("sou"))
            fourth_site_signal_gravity = get_value(fourth_kp_kp.get("gravity"))

        fifth_kp_kp = all_signals.get("controlled_site_fifth") or {}
        if fifth_kp_kp:
            fifth_site_signal_pump = get_value(fifth_kp_kp.get("pump"))
            fifth_site_signal_sou = get_value(fifth_kp_kp.get("sou"))
            fifth_site_signal_gravity = get_value(fifth_kp_kp.get("gravity"))

        sixth_kp_kp = all_signals.get("controlled_site_sixth") or {}
        if sixth_kp_kp:
            sixth_site_signal_pump = get_value(sixth_kp_kp.get("pump"))
            sixth_site_signal_sou = get_value(sixth_kp_kp.get("sou"))
            sixth_site_signal_gravity = get_value(sixth_kp_kp.get("gravity"))

        seventh_kp_kp = all_signals.get("controlled_site_seventh") or {}
        if seventh_kp_kp:
            seventh_site_signal_pump = get_value(seventh_kp_kp.get("pump"))
            seventh_site_signal_sou = get_value(seventh_kp_kp.get("sou"))
            seventh_site_signal_gravity = get_value(seventh_kp_kp.get("gravity"))

        eighth_kp_kp = all_signals.get("controlled_site_eight") or {}
        if eighth_kp_kp:
            eight_site_signal_pump = get_value(eighth_kp_kp.get("pump"))
            eight_site_signal_sou = get_value(eighth_kp_kp.get("sou"))
            eight_site_signal_gravity = get_value(eighth_kp_kp.get("gravity"))

    with SoftAssertions() as soft_failures:
        StepCheck(
            "Проверка сигнала - режим МТ на участке Тихорецкая-Нововеличковская",
            "Режим МТ",
            soft_failures,
        ).actual(first_site_signal_pump).expected(str(cfg.exp_tixoreczkaya_novovelichkovskaya_reg_lu)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на участке Тихорецкая-Нововеличковская",
            "Режим СОУ",
            soft_failures,
        ).actual(first_site_signal_sou).expected(str(cfg.exp_tixoreczkaya_novovelichkovskaya_reg_sou)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} \n"
            f"на участке Тихорецкая-Нововеличковская",
            "Количество самотеков",
            soft_failures,
        ).actual(first_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на участке Нововеличковская-Крымская",
            "Режим МТ",
            soft_failures,
        ).actual(second_site_signal_pump).expected(str(cfg.exp_novovelichkovskaya_krymskaya_reg_lu)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description}\n"
            f"на участке Нововеличковская-Крымская",
            "Количество самотеков",
            soft_failures,
        ).actual(second_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на участке Нововеличковская-Крымская",
            "Режим СОУ",
            soft_failures,
        ).actual(second_site_signal_sou).expected(str(cfg.exp_novovelichkovskaya_krymskaya_reg_sou)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на участке Крымская-Грушовая",
            "Режим МТ",
            soft_failures,
        ).actual(
            third_site_signal_pump
        ).expected(str(cfg.exp_krymskaya_grushovaya_reg_lu)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_true.description} на участке Крымская-Грушовая",
            "Количество самотеков",
            soft_failures,
        ).actual(third_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_true.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на участке Крымская-Грушовая",
            "Режим СОУ",
            soft_failures,
        ).actual(
            third_site_signal_sou
        ).expected(str(cfg.exp_krymskaya_grushovaya_reg_sou)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на резервной нитке Бейсуг",
            "Режим МТ",
            soft_failures,
        ).actual(
            fourth_site_signal_pump
        ).expected(str(cfg.exp_backup_route_bejsug_reg_lu)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} на резервной нитке Бейсуг",
            "Количество самотеков",
            soft_failures,
        ).actual(fourth_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на резервной нитке Бейсуг",
            "Режим СОУ",
            soft_failures,
        ).actual(
            fourth_site_signal_sou
        ).expected(str(cfg.exp_backup_route_bejsug_reg_sou)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на резервной нитке Понура",
            "Режим МТ",
            soft_failures,
        ).actual(
            fifth_site_signal_pump
        ).expected(str(cfg.exp_backup_route_ponura_reg_lu)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на резервной нитке Понура",
            "Режим СОУ",
            soft_failures,
        ).actual(
            fifth_site_signal_sou
        ).expected(str(cfg.exp_backup_route_ponura_reg_sou)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} на резервной нитке Понура",
            "Количество самотеков",
            soft_failures,
        ).actual(fifth_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на резервной нитке Кубань",
            "Режим МТ",
            soft_failures,
        ).actual(
            sixth_site_signal_pump
        ).expected(str(cfg.exp_backup_route_kuban_reg_lu)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на резервной нитке Кубань",
            "Режим СОУ",
            soft_failures,
        ).actual(
            sixth_site_signal_sou
        ).expected(str(cfg.exp_backup_route_kuban_reg_sou)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} на резервной нитке Кубань",
            "Количество самотеков",
            soft_failures,
        ).actual(sixth_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на НПЗ Афипский",
            "Режим МТ",
            soft_failures,
        ).actual(
            seventh_site_signal_pump
        ).expected(str(cfg.exp_npz_afipskij_reg_lu)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на НПЗ Афипский",
            "Режим СОУ",
            soft_failures,
        ).actual(
            seventh_site_signal_sou
        ).expected(str(cfg.exp_npz_afipskij_reg_sou)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} на НПЗ Афипский",
            "Количество самотеков",
            soft_failures,
        ).actual(seventh_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()
        StepCheck(
            "Проверка сигнала - режим МТ на НПЗ Ильинский",
            "Режим МТ",
            soft_failures,
        ).actual(
            eight_site_signal_pump
        ).expected(str(cfg.exp_npz_ilinskij_reg_lu)).equal_to()
        StepCheck(
            "Проверка сигнала - режим СОУ на НПЗ Ильинский",
            "Режим СОУ",
            soft_failures,
        ).actual(
            eight_site_signal_sou
        ).expected(str(cfg.exp_npz_ilinskij_reg_sou)).equal_to()
        StepCheck(
            f"Проверка {GravityPipe.expected_lds_status_gravity_false.description} на НПЗ Ильинский",
            "Количество самотеков",
            soft_failures,
        ).actual(eight_site_signal_gravity).expected(str(GravityPipe.expected_lds_status_gravity_false.id)).equal_to()


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
        # Проверяет что количество отбракованных сигналов больше или равно ОР
        StepCheck(
            f"Проверка количества отбракованных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfRejectedSignals
        ).is_greater_than_or_equal_to(cfg.expected_main_page_signals[field_name])
        field_name = "numberOfMaskedSignals"
        StepCheck(
            f"Проверка количества маскированных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfMaskedSignals
        ).expected(cfg.expected_main_page_signals[field_name]).equal_to()
        field_name = "numberOfImitatedSignals"
        StepCheck(
            f"Проверка количества имитированных сигналов ТУ {cfg.tu_name}",
            field_name,
            soft_failures,
        ).actual(
            parsed_payload.replyContent.signalsInfo.numberOfImitatedSignals
        ).expected(cfg.expected_main_page_signals[field_name]).equal_to()


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


async def leak_is_confirm_on_main_page(ws_client, cfg: SmokeSuiteConfig):
    """
    MainPageInfoContent - проверка подтвержденной утечки на ЭФ Состояние МТ
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent."):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)
        main_page_leak_info = parsed_payload.replyContent.tuInfo.leaksInfo
        confirm_leak = t_utils.find_object_by_field(main_page_leak_info, "leakStatus", LeakStatus.CONFIRMED.value)

    StepCheck("Проверка подтвержденной утечки на ЭФ Состояние МТ", "leakStatus").actual(
        confirm_leak.leakStatus
    ).expected(LeakStatus.CONFIRMED.value).equal_to()


async def leak_is_complete_on_main_page(ws_client, cfg: SmokeSuiteConfig):
    """
    MainPageInfoContent - отсутствует подтвержденная утечка на ЭФ Состояние МТ
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MainPageInfoContent."):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "MainPageInfoContent",
            "subscribeMainPageInfoRequest",
            {'tuIds': [cfg.tu_id], 'additionalProperties': None},
        )
        parsed_payload = parser.parse_main_page_msg(payload)
        main_page_leak_info = parsed_payload.replyContent.tuInfo.leaksInfo
        confirmed_and_closed_leaks = t_utils.find_confirmed_leaks_on_main_page(main_page_leak_info)

    StepCheck("Проверка подтвержденной утечки на ЭФ Состояние МТ", "leakStatus").actual(
        confirmed_and_closed_leaks
    ).is_empty()


async def imitate_senor_signal(ws_client, cfg: SmokeSuiteConfig, test_data: CaseData):
    """
    Проверка имитации сигнала датчика.
    """
    # Распаковка данных для теста
    sensor_id = test_data.params.get("sensor_id")
    sensor_val, sensor_quality = test_data.expected_result

    with allure.step(f"Отправка сообщения и обработка ответа об имитации сигнала датчика с id: {sensor_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "ImitateSignalRequest",
            {
                'id': sensor_id,
                'tuId': cfg.tu_id,
                'imitateInfo': {
                    'value': str(sensor_val),
                    'quality': sensor_quality,
                    'additionalProperties': None,
                },
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_imitate_signal_msg(payload)
        sensor_imitate_reply_status = parsed_payload.replyStatus

        StepCheck("Проверка кода ответа на запрос об имитации", "replyStatus").actual(
            sensor_imitate_reply_status
        ).expected(ReplyStatus.OK.value).equal_to()

    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчика из сообщения типа: InputSignalsContent"
    ):
        time.sleep(cfg.basic_message_timeout)
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [sensor_id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_input_signals_info_msg(payload)
        sensor_data = parsed_payload.replyContent.inputSignals
        sensor_imitate_data = t_utils.find_object_by_field(sensor_data, "id", sensor_id)
    with allure.step(f"Отправка сообщения и обработка ответа о снятии имитации датчика с id: {sensor_id}"):
        payload = await t_utils.connect_and_get_msg(
            ws_client,
            "UnimitateSignalRequest",
            {'id': sensor_id, 'tuId': cfg.tu_id, 'additionalProperties': None},
        )
        parsed_payload = parser.parse_unimitate_signal_msg(payload)
        sensor_unimitate_reply_status = parsed_payload.replyStatus

        StepCheck("Проверка кода ответа на запрос о снятии имитации", "replyStatus").actual(
            sensor_unimitate_reply_status
        ).expected(ReplyStatus.OK.value).equal_to()

    with allure.step(
        "Подключение по ws, получение и обработка данных о статусе датчика из сообщения типа: InputSignalsContent"
    ):
        time.sleep(cfg.basic_message_timeout)
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "InputSignalsContent",
            "SubscribeInputSignalsRequest",
            {
                'signalIds': [sensor_id],
                'tuId': cfg.tu_id,
                'additionalProperties': None,
            },
        )
        parsed_payload = parser.parse_input_signals_info_msg(payload)
        sensor_data = parsed_payload.replyContent.inputSignals
        sensor_unimitate_data = t_utils.find_object_by_field(sensor_data, "id", sensor_id)

    with SoftAssertions() as soft_failures:
        StepCheck(f"Проверка имитации датчика с id: {sensor_id}", "isImitated", soft_failures).actual(
            sensor_imitate_data.isImitated
        ).expected(True).equal_to()
        StepCheck(f"Проверка показаний датчика с id: {sensor_id}", "value", soft_failures).actual(
            sensor_imitate_data.imitation.value
        ).expected(sensor_val).equal_to()
        StepCheck(f"Проверка качества сигнала датчика с id: {sensor_id}", "quality", soft_failures).actual(
            sensor_imitate_data.quality
        ).expected(sensor_quality).equal_to()
        StepCheck(f"Проверка снятия имитации датчика с id: {sensor_id}", "isImitated", soft_failures).actual(
            sensor_unimitate_data.isImitated
        ).expected(False).equal_to()


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

            StepCheck("Проверка кода ответа на запрос о снятии маскирования", "replyStatus").actual(
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


async def mask_du_on_mini_scheme(ws_client, cfg: SmokeSuiteConfig):
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
        messages_info = parsed_payload.replyContent.messagesInfo

        if cfg.technological_section:
            mask_message = t_utils.find_object_by_field(
                messages_info, "technologicalSection", cfg.technological_section
            )
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


async def unmask_du_on_mini_scheme(ws_client, cfg: SmokeSuiteConfig):
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
        messages_info = parsed_payload.replyContent.messagesInfo

        if cfg.technological_section:
            mask_message = t_utils.find_object_by_field(
                messages_info, "technologicalSection", cfg.technological_section
            )
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
        # Ищет подтвержденные утечки
        confirmed_leaks_list = t_utils.find_confirmed_leaks(leaks_list_info)
        first_leak_info = t_utils.find_leak_by_coordinate(confirmed_leaks_list, leak.coordinate_meters)

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
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LEAKS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        end_time = datetime.now()
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

            leak_message = next(
                (
                    msg
                    for msg in time_filtered
                    if msg.technologicalSection == cfg.tu_name and TestConst.JOURNAL_EVENT_DETECTED_LEAK in msg.event
                ),
                None,
            )

            allure.attach(
                f"Всего получено сообщений: {len(messages_info)}\n"
                f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n",
                name="Результат фильтрации сообщений журнала",
                attachment_type=allure.attachment_type.TEXT,
            )

    with allure.step("Первичная проверка после фильтрации"):

        StepCheck(
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event содержит подстроку подтвержденной утечки'{TestConst.JOURNAL_EVENT_DETECTED_LEAK}'",
            "event",
        ).actual(leak_message).is_not_none()

        leak_coordinate_km, leak_volume_m3 = t_utils.parse_journal_msg_value(leak_message.value)
        leak_coordinate_round = round(leak_coordinate_km * TestConst.KM_TO_METERS, TestConst.PRECISION)
        leak_message_time = t_utils.ensure_moscow_timezone(leak_message.time)

    with SoftAssertions() as soft_failures:

        StepCheck("Проверка полученного события event", "event", soft_failures).contains(
            leak_message.event, TestConst.JOURNAL_EVENT_DETECTED_LEAK
        )

        StepCheck("Проверка полученного ТУ", "technologicalSection", soft_failures).actual(
            leak_message.technologicalSection
        ).expected(cfg.tu_name).equal_to()

        StepCheck("Проверка типа полученного сообщения", "messageType", soft_failures).actual(
            leak_message.messageType
        ).expected(TestConst.JOURNAL_MESSAGE_TYPE_LEAKS).equal_to()

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
            leak_message_time
        ).is_between(filter_start_msk, filter_end_msk)

        StepCheck("Проверка объема утечки", "volume", soft_failures).actual(leak_volume_m3).is_close_to(
            leak.volume_m3,
            leak.allowed_volume_m3,
            f"значение допустимой погрешности по объему {leak.allowed_volume_m3}",
        )


async def completed_leak_info_in_journal(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time):
    """
    Проверка наличия сообщения 'Утечка завершена' в журнале.
    """
    with allure.step("Подключение по ws, получение и обработка сообщения типа: MessagesInfoContent"):
        request_body = t_utils.create_journal_req_body(
            pagination=Pagination(limit=TestConst.JOURNAL_PAGINATION_LIMIT, direction=Direction.FIRST.value),
            filtering=Filtering(messageTypes=int(MessageType.LEAKS), objects=FilteringObjects(tuId=cfg.tu_id)),
        )
        payload = await t_utils.connect_and_get_msg(ws_client, "GetMessagesRequest", request_body)
        end_time = datetime.now()
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

            completed_leak_message = next(
                (
                    msg
                    for msg in time_filtered
                    if msg.technologicalSection == cfg.tu_name and msg.event == TestConst.JOURNAL_EVENT_COMPLETED_LEAKS
                ),
                None,
            )

            allure.attach(
                f"Всего получено сообщений: {len(messages_info)}\n"
                f"После фильтрации по времени ({filter_start_msk} - {filter_end_msk}): {len(time_filtered)}\n",
                name="Результат фильтрации сообщений журнала",
                attachment_type=allure.attachment_type.TEXT,
            )

    with allure.step("Первичная проверка после фильтрации"):

        StepCheck(
            f"Проверка: найдено ли сообщение с technologicalSection='{cfg.tu_name}' "
            f"и event='{TestConst.JOURNAL_EVENT_COMPLETED_LEAKS}'",
            "event",
        ).actual(completed_leak_message).is_not_none()

        leak_coordinate_km, leak_volume_m3 = t_utils.parse_journal_msg_value(completed_leak_message.value)
        leak_coordinate_round = round(leak_coordinate_km * TestConst.KM_TO_METERS, TestConst.PRECISION)
        leak_message_time = t_utils.ensure_moscow_timezone(completed_leak_message.time)

    with SoftAssertions() as soft_failures:

        StepCheck("Проверка статуса утечки в журнале", "event", soft_failures).actual(
            completed_leak_message.event
        ).expected(TestConst.JOURNAL_EVENT_COMPLETED_LEAKS).equal_to()

        StepCheck("Проверка полученного ТУ", "technologicalSection", soft_failures).actual(
            completed_leak_message.technologicalSection
        ).expected(cfg.tu_name).equal_to()

        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )

        StepCheck("Проверка времени завершения утечки", "leakDetectedAt", soft_failures).actual(
            leak_message_time
        ).is_between(filter_start_msk, filter_end_msk)


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


async def all_leaks_is_empty(ws_client, cfg: SmokeSuiteConfig):
    """
    Проверка отсутствия информации об утечке
    """
    with allure.step("Подключение по ws и получение сообщения об утечке типа: AllLeaksInfoContent"):
        parsed_payload = await t_utils.connect_and_get_parsed_msg_by_tu_id(
            cfg.tu_id,
            ws_client,
            "AllLeaksInfoContent",
            "subscribeAllLeaksInfoRequest",
            [],
        )

    StepCheck("Проверка отсутствия информации об утечке в сообщении AllLeaksInfoContent", "leaksInfo").actual(
        parsed_payload.replyContent.leaksInfo
    ).is_empty()


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

    leak_diagnostic_area = t_utils.find_diagnostic_area_by_pipe_id(
        flow_areas, status_config.leak_diagnostic_area_pipe_id
    )
    if not leak_diagnostic_area:
        pytest.fail(f"В сообщении не найден ДУ с id: {status_config.leak_diagnostic_area_id}")

    # Формат конфига: status_config.in_neighbors / status_config.out_neighbors (dict[id] = expected_status)
    in_neighbors: dict[int, int] = status_config.in_neighbors or {}
    out_neighbors: dict[int, int] = status_config.out_neighbors or {}
    all_neighbors = in_neighbors | out_neighbors
    if not all_neighbors:
        pytest.fail("Не заданы id, соседних с утечкой ДУ для теста lds_status_during_leak")
    found_diagnostic_area_count = 0

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка режима работы СОУ на ДУ с утечкой, pipe_id ДУ: {status_config.leak_diagnostic_area_pipe_id}",
            "ldsStatus",
            soft_failures,
        ).actual(leak_diagnostic_area.ldsStatus).expected(status_config.leak_du_expected_lds_status).equal_to()

        # Проверки соседних ДУ: поддерживаются 0. N соседей
        for neighbor_pipe_id, expected_status in sorted(all_neighbors.items()):
            diagnostic_area = t_utils.find_diagnostic_area_by_pipe_id(flow_areas, neighbor_pipe_id)
            if diagnostic_area:
                found_diagnostic_area_count += 1
                StepCheck(
                    f"Проверка режима работы СОУ на соседнем ДУ, pipe_id ДУ: {neighbor_pipe_id}",
                    "ldsStatus",
                    soft_failures,
                ).actual(diagnostic_area.ldsStatus).expected(expected_status).equal_to()
        if found_diagnostic_area_count == 0:
            pytest.fail(f"Не найдены соседние с утечкой ДУ по pipe_id: {list(all_neighbors.keys())}")


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

        if collected_diagnostic_areas is not None:
            allure.attach(
                str(collected_diagnostic_areas),
                name="Тестируемый фрагмент ответа с бэка",
                attachment_type=allure.attachment_type.TEXT,
            )

        diagnostic_area_names_with_possible = [
            diagnostic_area.name for diagnostic_area in collected_diagnostic_areas if diagnostic_area.isLeakPossible
        ]

        diagnostic_area_possible_leak = next(
            (diagnostic_area for diagnostic_area in collected_diagnostic_areas if diagnostic_area.isLeakDetected),
            None,
        )

        is_leak_possible_seen = any(diagnostic_area.isLeakPossible for diagnostic_area in collected_diagnostic_areas)

    with SoftAssertions() as soft_failures:

        StepCheck(
            "Проверка: получен хотя бы один ДУ с подозрением на утечку",
            "isLeakPossible",
            soft_failures,
        ).actual(diagnostic_area_names_with_possible).is_not_empty()

        StepCheck(
            f"Проверка: на ДУ {str(diagnostic_area_names_with_possible)} бы раз за "
            f"{TestConst.BALANCE_ALGORITHM_TOTAL_WAIT / TestConst.SEC_PER_MIN} минут приходил"
            " статус 'подозрение на утечку': isLeakPossible=True",
            "isLeakPossible",
            soft_failures,
        ).actual(is_leak_possible_seen).expected(True).equal_to()

        if leak.flow_rate_settings_threshold is not None and diagnostic_area_possible_leak is not None:
            threshold = leak.flow_rate_settings_threshold
            tolerance = TestConst.DEBALANCE_TOLERANCE
            lower_bound = threshold * (1 - tolerance)

            StepCheck(
                f"Проверка значения дебаланса на ДУ name={diagnostic_area_possible_leak.name} с будущей утечкой"
                f" в пределах {int(tolerance * 100)}% снизу от порогового значения по объему: {threshold}).",
                "debalance",
                soft_failures,
            ).actual(abs(diagnostic_area_possible_leak.debalance)).is_greater_than(lower_bound)


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
            (diagnostic_area for diagnostic_area in all_diagnostic_areas if diagnostic_area.isLeakDetected),
            None,
        )

        if leak_diagnostic_area is None:
            pytest.fail("Ни одного ДУ с утечкой не найдено в ответе BalanceAlgorithmResultsContent")

        leak_diagnostic_area_name = leak_diagnostic_area.name

    with SoftAssertions() as soft_failures:
        StepCheck(
            f"Проверка: на ДУ name={leak_diagnostic_area_name} обнаружена утечка",
            "isLeakDetected",
            soft_failures,
        ).actual(leak_diagnostic_area.isLeakDetected).expected(True).equal_to()

        foreign_with_detected = [
            diagnostic_area
            for diagnostic_area in all_diagnostic_areas
            if diagnostic_area.name != leak_diagnostic_area_name and diagnostic_area.isLeakDetected
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
                f"Дебаланс на ДУ name={leak_diagnostic_area_name} по модулю больше порога для данного режима МТ:"
                f" {threshold}",
                "debalance",
                soft_failures,
            ).actual(abs(leak_diagnostic_area.debalance)).is_greater_than(threshold)


async def balance_algorithm_leak_completed(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Проверка отсутствия утечки (isLeakDetected) через BalanceAlgorithmResults.

    Логика:
    - Подписка на BalanceAlgorithmResultsContent.
    - Получение первого подходящего сообщения типа BalanceAlgorithmResultsContent.
    - Проверяем, что на всех ДУ флаг isLeakDetected=False.
    - Проверяем, что дебаланс на всех ДУ < FLOW_RATE_SETTINGS_THRESHOLD.
    """

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
                "невозможно проверить наличие/отсутствие утечки"
            )

        all_diagnostic_areas = []
        for flow_area in reply_content.flowAreas:
            if flow_area.diagnosticAreas:
                all_diagnostic_areas.extend(flow_area.diagnosticAreas)

        if not all_diagnostic_areas:
            pytest.fail(
                "В ответе с бэка в DTO BalanceAlgorithmResults во всех flowAreas отсутствуют diagnosticAreas, "
                "невозможно проверить наличие/отсутствие утечки"
            )

    with SoftAssertions() as soft_failures:

        for diagnostic_area in all_diagnostic_areas:
            diagnostic_area_name = diagnostic_area.name
            StepCheck(
                f"Проверка: на ДУ {diagnostic_area_name} не должно быть утечки",
                "isLeakDetected_without_leak",
                soft_failures,
            ).actual(diagnostic_area.isLeakDetected).expected(False).equal_to()


async def the_leak_is_complete_on_kg(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """
    Проверка факта завершения утечки на ЭФ КГ(табличное представление).

    Логика:
    LeaksContent - проверить, что утечка в статусе завершена
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
        complete_leak_info = t_utils.find_leak_by_coordinate(leaks_list_info, leak.coordinate_meters)
        leak_coordinate_round = round(complete_leak_info.leakCoordinate, cfg.precision)
        complete_leak = t_utils.find_object_by_field(
            leaks_list_info, "confirmationStatus", ConfirmationStatus.CONFIRMED_AND_LEAK_CLOSED.value
        )

    with SoftAssertions() as soft_failures:
        StepCheck("Проверка статуса утечки в КГ - завершена", "confirmationStatus", soft_failures).actual(
            complete_leak.confirmationStatus
        ).expected(leak.expected_complete_leak_status).equal_to()
        StepCheck("Проверка наличия названия участка утечки", "diagnosticAreaName", soft_failures).actual(
            complete_leak_info.diagnosticAreaName
        ).is_not_none()
        StepCheck("Проверка источника события (алгоритм)", "type", soft_failures).actual(
            complete_leak_info.type
        ).expected(leak.expected_algorithm_type).equal_to()
        StepCheck("Проверка координаты утечки", "leakCoordinate", soft_failures).actual(
            leak_coordinate_round
        ).is_close_to(
            leak.coordinate_meters,
            cfg.allowed_distance_diff_meters,
            f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
        )


async def leak_is_complete_in_output_signals(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig):
    """OutputSignalsInfo - нет утечки в выходных сигналах"""
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
            leak_signal_type = t_utils.find_signal_type_by_address_suffix(
                leak_signals_list, TestConst.ADDRESS_SUFFIX_LEAK
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
            leak_value = t_utils.find_signal_val_by_signal_type(leak_signals_list, leak_signal_type)

    with SoftAssertions() as soft_failures:
        StepCheck(
            "Проверка отсутствия времени утечки в выходных сигналах",
            TestConst.ADDRESS_SUFFIX_TIME_LEAK,
            soft_failures,
        ).actual(leak_value).expected(TestConst.OUTPUT_IS_NOT_LEAK).equal_to()
        StepCheck(
            "Проверка отсутствия утечки в выходных сигналах",
            TestConst.ADDRESS_SUFFIX_LEAK,
            soft_failures,
        ).actual(leak_value).expected(TestConst.OUTPUT_IS_NOT_LEAK).equal_to()
        StepCheck(
            "Проверка отсутствия квитирования утечки в выходных сигналах",
            TestConst.ADDRESS_SUFFIX_ACK_LEAK,
            soft_failures,
        ).actual(leak_value).expected(TestConst.OUTPUT_IS_NOT_LEAK).equal_to()
        StepCheck(
            "Проверка отсутствия объема утечки в выходных сигналах",
            TestConst.ADDRESS_SUFFIX_Q_LEAK,
            soft_failures,
        ).actual(leak_value).expected(TestConst.OUTPUT_IS_NOT_LEAK).equal_to()
        StepCheck(
            "Проверка отсутствия координаты утечки в выходных сигналах",
            TestConst.ADDRESS_SUFFIX_POINT_LEAK,
            soft_failures,
        ).actual(leak_value).expected(TestConst.OUTPUT_IS_NOT_LEAK).equal_to()


async def complete_tu_leaks_info_content(ws_client, cfg: SmokeSuiteConfig):
    """
    TuLeaksInfoContent - проверка отсутствия утечки на схеме
    """
    with allure.step("Подключение по ws, получение и обработка сообщения об утечке типа: TuLeaksInfoContent"):
        payload = await t_utils.connect_and_subscribe_msg(
            ws_client,
            "TuLeaksInfoContent",
            "subscribeTuLeaksInfoRequest",
            {'tuId': cfg.tu_id},
        )
        parsed_payload = parser.parse_tu_leaks_info_msg(payload)
        leak_on_scheme = parsed_payload.replyContent.leaksInfo

    StepCheck("Проверка отсутствия утечки на схемwе", "leaksInfo").actual(leak_on_scheme).is_empty()


async def export_leaks_report(ws_client, cfg: SmokeSuiteConfig, leak: LeakTestConfig, imitator_start_time: datetime):
    """
    Сценарий формирования отчёта об утечках.

    Этапы:
    1. Подписка SubscribeReportsDataExportedRequest на пуш-нотификации.
    2. Отправка ExportReportsCommandRequest с фильтром по времени
       (start = старт имитатора, end = старт имитатора + offset теста).
    3. Ожидание пуш-нотификации ReportDataExportedNotification о готовности отчёта.
    4. Лонг-поллинг GetExportedDataListRequest до появления нашего отчёта в списке.
    5. Отправка DownloadExportedDataRequest по id отчёта.
    6. Получение fileChunk по ответу на скачивание.
    7-10. Проверки: формат файла, имя, шапка xlsx, строка утечки.

    Скачанный файл удаляется по завершению, прикладывается к Allure только при падении теста.
    """
    report_state = ExportLeaksReportState()

    with allure.step("Подготовка параметров сценария формирования отчёта об утечках"):
        report_state.report_test = leak.export_leaks_report_test
        StepCheck("В конфигурации задан export_leaks_report_test", "export_leaks_report_test").actual(
            report_state.report_test
        ).is_not_none()

        report_state.period_start = t_utils.localize_as_moscow(imitator_start_time)
        report_state.period_end = t_utils.localize_as_moscow(
            imitator_start_time + timedelta(minutes=report_state.report_test.offset)
        )
        report_state.period_start_naive = report_utils.normalize_report_period_naive(report_state.period_start)
        report_state.period_end_naive = report_utils.normalize_report_period_naive(report_state.period_end)
        report_state.expected_mt_mode = ReportConst.STATIONARY_STATUS_TO_REPORT_TEXT.get(
            leak.expected_stationary_status
        )
        report_state.tu_description_lower = cfg.technological_unit.description.lower()
        time_offset_hours = t_utils.report_time_offset_hours()
        StepCheck(
            f"Смещение timeOffset для запросов отчёта (часовой пояс {TestConst.ZONE_INFO})",
            "time_offset_hours",
        ).actual(time_offset_hours).is_not_none()
        report_state.time_offset_hours = time_offset_hours

        StepCheck(
            "Задан ожидаемый текст режима МТ для отчёта",
            "expected_mt_mode",
        ).actual(report_state.expected_mt_mode).is_not_none()

        allure.attach(
            f"period.start={report_state.period_start}\n"
            f"period.end={report_state.period_end}\n"
            f"offset_minutes={report_state.report_test.offset}",
            name="Фильтр периода отчёта",
            attachment_type=allure.attachment_type.TEXT,
        )

    with allure.step(
        f"Этап 1. Подписка на пуш-нотификации ({ReportConst.SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST})"
    ):
        await t_utils.connect(ws_client, ReportConst.SUBSCRIBE_REPORTS_DATA_EXPORTED_REQUEST, [])

    with allure.step(f"Этап 2. Запрос формирования отчёта ({ReportConst.EXPORT_REPORTS_COMMAND_REQUEST})"):
        request_payload = {
            "tuId": cfg.tu_id,
            "exportedDataTypes": [ExportedDataType.LEAKS_REPORT.value],
            "timeOffset": report_state.time_offset_hours,
            "period": {
                "start": t_utils.datetime_to_msgpack_timestamp(report_state.period_start),
                "end": t_utils.datetime_to_msgpack_timestamp(report_state.period_end),
                "additionalProperties": {},
            },
        }
        await t_utils.connect(ws_client, ReportConst.EXPORT_REPORTS_COMMAND_REQUEST, request_payload)

    with allure.step(
        f"Этап 3. Ожидание пуш-нотификации {ReportConst.REPORT_DATA_EXPORTED_NOTIFICATION} о готовности отчёта"
    ):
        report_state.notification = await t_utils.poll_for_report_export_notification(
            ws_client=ws_client,
            parser=parser,
            total_wait_seconds=ReportConst.NOTIFICATION_TIMEOUT_SECONDS,
            poll_interval_seconds=ReportConst.LIST_POLL_INTERVAL_SECONDS,
        )

    with allure.step("Извлечение полей пуш-нотификации"):
        notification = report_state.notification
        notification_reply_status = notification.replyStatus if notification else None
        notification_reply_content = notification.replyContent if notification else None
        notification_export_status = (
            notification_reply_content.exportStatus if notification_reply_content else None
        )
        notification_error_message = (
            (notification_reply_content.errorMessage or "") if notification_reply_content else ""
        )

    with allure.step("Проверка пуш-нотификации о готовности отчёта"):
        StepCheck("Получена пуш-нотификация о готовности отчёта", "notification").actual(
            report_state.notification
        ).is_not_none()
        StepCheck("Проверка статуса пуш-нотификации", "replyStatus").actual(notification_reply_status).expected(
            ReplyStatus.OK.value
        ).equal_to()
        StepCheck("Проверка наличия контента нотификации", "replyContent").actual(
            notification_reply_content
        ).is_not_none()
        StepCheck("Проверка exportStatus в нотификации", "exportStatus").actual(notification_export_status).expected(
            ExportStatus.DONE
        ).equal_to()
        StepCheck("В нотификации нет текста ошибки", "errorMessage").actual(notification_error_message).is_empty()

    with allure.step(
        f"Этап 4. Лонг-поллинг {ReportConst.GET_EXPORTED_DATA_LIST_REQUEST} до появления отчёта в списке"
    ):
        report_state.report_item = await t_utils.poll_for_exported_file(
            ws_client=ws_client,
            parser=parser,
            list_limit=ReportConst.EXPORTED_DATA_LIST_LIMIT,
            expected_data_type=ExportedDataType.LEAKS_REPORT,
            name_substring=ReportConst.LEAKS_REPORT_NAME_PART,
            tu_name_substring=cfg.technological_unit.description,
            period_start=report_state.period_start,
            period_end=report_state.period_end,
            total_wait_seconds=ReportConst.LIST_POLL_TOTAL_WAIT_SECONDS,
            poll_interval_seconds=ReportConst.LIST_POLL_INTERVAL_SECONDS,
        )

    with allure.step("Подготовка данных найденного отчёта в списке"):
        report_item = report_state.report_item
        if report_item is not None:
            allure.attach(
                f"id={report_item.id}, name={report_item.name}, "
                f"exportedDataType={report_item.exportedDataType}, "
                f"start={report_item.start}, end={report_item.end}",
                name="Найденный отчёт в списке",
                attachment_type=allure.attachment_type.TEXT,
            )
        report_state.report_file_name = report_utils.build_export_report_file_name(
            cfg.technological_unit.description,
            report_state.period_start,
            report_state.period_end,
        )

    with allure.step("Проверка: отчёт найден в списке сформированных файлов"):
        StepCheck("Отчёт найден в списке сформированных файлов", "report_item").actual(
            report_state.report_item
        ).is_not_none()

    download_request = {
        "exportedDataId": report_state.report_item.id,
        "exportedDataType": ExportedDataType.LEAKS_REPORT.to_download_name(),
        "additionalProperties": None,
        "timeOffset": report_state.time_offset_hours,
    }

    download_purpose = (
        f"скачивание xlsx-отчёта об утечках (exportedDataId={report_state.report_item.id}) "
        f"после формирования отчёта и выбора файла в списке GetExportedDataListRequest - выпадашка уведомлений на UI"
    )

    with allure.step(
        f"Этап 5. Streaming-вызов {ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST} по id={report_state.report_item.id}"
    ):
        await t_utils.connect_stream(
            ws_client,
            ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST,
            download_request,
            purpose=download_purpose,
        )
        report_state.download_invocation_id = ws_client.invocation_id

    with allure.step("Этап 6. Получение fileChunk - скачивание отчёта по утечкам"):
        report_state.download_reply = await t_utils.receive_download_exported_data_reply(
            ws_client=ws_client,
            parser=parser,
            invocation_id=report_state.download_invocation_id,
            request_name=ReportConst.DOWNLOAD_EXPORTED_DATA_REQUEST,
            total_wait_seconds=ReportConst.DOWNLOAD_TIMEOUT_SECONDS,
            purpose=download_purpose,
        )

    with allure.step("Извлечение данных ответа на скачивание"):
        download_reply = report_state.download_reply
        download_reply_status = download_reply.replyStatus
        has_download_reply_content = download_reply.replyContent is not None
        report_state.file_bytes = (
            download_reply.replyContent.fileChunk if has_download_reply_content else None
        )
        is_xlsx_signature = (
            report_utils.is_xlsx_file_bytes(report_state.file_bytes) if report_state.file_bytes else False
        )

    with allure.step("Проверка ответа на скачивание и формата xlsx"):
        StepCheck("Проверка статуса ответа на скачивание", "replyStatus").actual(download_reply_status).expected(
            ReplyStatus.OK.value
        ).equal_to()
        StepCheck("Проверка наличия контента ответа на скачивание", "replyContent").actual(
            has_download_reply_content
        ).expected(True).equal_to()
        StepCheck("Проверка наличия байт файла", "fileChunk").actual(report_state.file_bytes).is_not_empty()
        StepCheck("Проверка xlsx (zip) сигнатуры файла", "file_signature").actual(is_xlsx_signature).expected(
            True
        ).equal_to()

    with allure.step("Подготовка данных для проверки имени файла отчёта"):
        report_file_name = report_state.report_file_name
        report_file_name_lower = report_file_name.lower()
        file_name_period_start, file_name_period_end = report_utils.parse_period_from_export_file_name(report_file_name)
        period_start_lo, period_start_hi, period_end_lo, period_end_hi = report_utils.report_period_comparison_bounds(
            report_state.period_start_naive,
            report_state.period_end_naive,
        )
        has_xlsx_extension = report_utils.is_xlsx_extension(report_file_name)
        leaks_report_name_part_lower = ReportConst.LEAKS_REPORT_NAME_PART.lower()

    with allure.step("Проверка имени файла отчёта"):
        StepCheck(f"Имя файла оканчивается на {ReportConst.XLSX_EXTENSION}", "file_name").actual(
            has_xlsx_extension
        ).expected(True).equal_to()
        StepCheck(f"Имя файла содержит '{ReportConst.LEAKS_REPORT_NAME_PART}'", "file_name").contains(
            report_file_name_lower, leaks_report_name_part_lower
        )
        StepCheck(
            f"Имя файла содержит описание ТУ '{cfg.technological_unit.description}'",
            "file_name",
        ).contains(report_file_name_lower, report_state.tu_description_lower)
        StepCheck(
            "Дата начала периода в имени файла совпадает с фильтром запроса (+-1 мин)",
            "period_start_in_file_name",
        ).actual(file_name_period_start).is_between(period_start_lo, period_start_hi)
        StepCheck(
            "Дата конца периода в имени файла совпадает с фильтром запроса (+-1 мин)",
            "period_end_in_file_name",
        ).actual(file_name_period_end).is_between(period_end_lo, period_end_hi)

    with allure.step("Этап 8. Сохранение, обработка и проверка отчета по утечкам"):
        report_state.temp_file_path = report_utils.save_report_bytes_to_temp_file(report_state.file_bytes)

    try:
        with allure.step("Проверка: временный xlsx файл создан"):
            StepCheck("Временный xlsx файл создан", "temp_file_path").actual(report_state.temp_file_path).is_not_none()

        with allure.step("Этап 9. Открытие xlsx и чтение шапки"):
            report_state.worksheet = report_utils.load_report_worksheet(report_state.temp_file_path)
            report_state.title_info = report_utils.parse_report_title(
                report_utils.get_report_title_cell(report_state.worksheet)
            )
            allure.attach(
                f"Шапка отчёта (raw): {report_state.title_info.raw_title}\n"
                f"period_start: {report_state.title_info.period_start}\n"
                f"period_end: {report_state.title_info.period_end}",
                name="Шапка отчёта (1-я строка)",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Подготовка данных шапки отчёта для проверки"):
            title_info = report_state.title_info
            report_title_lower = title_info.raw_title.lower()
            leaks_report_name_part_lower = ReportConst.LEAKS_REPORT_NAME_PART.lower()
            column_headers = report_utils.get_report_column_headers(report_state.worksheet)
            period_start_lo, period_start_hi, period_end_lo, period_end_hi = report_utils.report_period_comparison_bounds(
                report_state.period_start_naive,
                report_state.period_end_naive,
            )
            header_period_start = title_info.period_start
            header_period_end = title_info.period_end

        with allure.step("Проверка двойной шапки отчёта"):
            StepCheck("Лист xlsx открыт", "worksheet").actual(report_state.worksheet).is_not_none()
            with SoftAssertions() as soft_failures:
                StepCheck(
                    f"В шапке отчёта присутствует '{ReportConst.LEAKS_REPORT_NAME_PART}'",
                    "report_title",
                    soft_failures,
                ).contains(report_title_lower, leaks_report_name_part_lower)

                StepCheck(
                    "Время начала периода в шапке совпадает с фильтром запроса (+-1 мин)",
                    "period_start",
                    soft_failures,
                ).actual(header_period_start).is_between(period_start_lo, period_start_hi)
                StepCheck(
                    "Время конца периода в шапке совпадает с фильтром запроса (+-1 мин)",
                    "period_end",
                    soft_failures,
                ).actual(header_period_end).is_between(period_end_lo, period_end_hi)
                StepCheck(
                    "Названия колонок в шапке отчёта",
                    "column_headers",
                    soft_failures,
                ).actual(column_headers).expected(ReportConst.EXPECTED_COLUMN_HEADERS).equal_to()

        with allure.step("Этап 10. Извлечение строк данных из отчёта"):
            report_state.data_rows = report_utils.iter_report_data_rows(report_state.worksheet)
            report_state.target_row = report_utils.find_row_with_object(
                report_state.data_rows, cfg.technological_unit.description
            )
            allure.attach(
                "\n".join(f"row#{row.row_index}: {row.cells}" for row in report_state.data_rows),
                name="Все строки данных отчёта",
                attachment_type=allure.attachment_type.TEXT,
            )

        with allure.step("Подготовка данных строки утечки для проверки"):
            target_row = report_state.target_row
            leak_datetime_value = target_row.datetime_value if target_row else None
            object_value_lower = target_row.object_value.lower() if target_row else ""
            lds_status_value = target_row.lds_status.strip() if target_row else ""
            masking_info_lower = target_row.masking_info.lower() if target_row else ""
            leak_coordinate_meters = target_row.coordinate_meters if target_row else None
            leak_volume_value = target_row.leak_volume if target_row else None
            mt_mode_lower = target_row.mt_mode.lower() if target_row else ""
            expected_mt_mode_lower = report_state.expected_mt_mode.lower()
            masking_not_masked_lower = ReportConst.MASKING_NOT_MASKED_TEXT.lower()
            period_start_lo, period_start_hi, period_end_lo, period_end_hi = report_utils.report_period_comparison_bounds(
                report_state.period_start_naive,
                report_state.period_end_naive,
            )

        with allure.step("Проверка содержимого строки утечки"):
            StepCheck("В отчёте есть хотя бы одна строка с данными", "data_rows").actual(
                report_state.data_rows
            ).is_not_empty()
            StepCheck(
                f"Строка с объектом, содержащим '{cfg.technological_unit.description}'",
                ReportConst.COL_OBJECT,
            ).actual(report_state.target_row).is_not_none()

            with SoftAssertions() as soft_failures:
                StepCheck(
                    "Время утечки в диапазоне [старт имитатора, старт + offset теста] (+-1 мин)",
                    ReportConst.COL_DATETIME,
                    soft_failures,
                ).actual(leak_datetime_value).is_between(period_start_lo, period_end_hi)

                StepCheck(
                    f"Колонка '{ReportConst.COL_OBJECT}' содержит '{cfg.technological_unit.description}'",
                    ReportConst.COL_OBJECT,
                    soft_failures,
                ).contains(object_value_lower, report_state.tu_description_lower)

                StepCheck(
                    f"Колонка '{ReportConst.COL_LDS_STATUS}'",
                    ReportConst.COL_LDS_STATUS,
                    soft_failures,
                ).actual(lds_status_value).expected(ReportConst.LDS_STATUS_OK_TEXT).equal_to()

                StepCheck(
                    f"Колонка '{ReportConst.COL_MASK_INFO}' содержит '{ReportConst.MASKING_NOT_MASKED_TEXT}'",
                    ReportConst.COL_MASK_INFO,
                    soft_failures,
                ).contains(masking_info_lower, masking_not_masked_lower)

                StepCheck(
                    f"Колонка '{ReportConst.COL_COORDINATE}' (с погрешностью {cfg.allowed_distance_diff_meters} м)",
                    ReportConst.COL_COORDINATE,
                    soft_failures,
                ).actual(leak_coordinate_meters).is_close_to(
                    leak.coordinate_meters,
                    cfg.allowed_distance_diff_meters,
                    f"значение допустимой погрешности координаты {cfg.allowed_distance_diff_meters}",
                )

                StepCheck(
                    f"Колонка '{ReportConst.COL_LEAK_VOLUME}' не пустая",
                    ReportConst.COL_LEAK_VOLUME,
                    soft_failures,
                ).actual(leak_volume_value).is_not_none()

                StepCheck(
                    f"Колонка '{ReportConst.COL_MT_MODE}' содержит '{report_state.expected_mt_mode}'",
                    ReportConst.COL_MT_MODE,
                    soft_failures,
                ).contains(mt_mode_lower, expected_mt_mode_lower)
    except Exception:
        with allure.step("Прикрепление xlsx отчёта к Allure при падении теста"):
            if report_state.temp_file_path and report_state.report_file_name:
                report_utils.attach_report_file_to_allure(report_state.temp_file_path, report_state.report_file_name)
        raise
    finally:
        with allure.step("Удаление временного xlsx файла"):
            temp_path = report_state.temp_file_path
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    pass
