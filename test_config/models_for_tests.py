"""
Датаклассы для конфигурации тестовых наборов.

Архитектура:
- TestSuiteConfig - главный конфиг набора, содержит всё для запуска тестов
- LeakTestConfig - конфиг утечки с параметрами и тест-кейсами
- TestCaseMarkers - маркеры для allure и pytest

Принцип: один файл конфига select_xx.py в папке datasets = один набор данных.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from constants.enums import (
    TU,
    ConfirmationStatus,
    LdsStatus,
    MeasureConversionRule,
    RejectionCriteria,
    RejectionSensorTag,
    ReservedType,
    StationaryStatus,
)
from constants.test_constants import BaseTN3Constants
from models.export_reports_model import ReportDataExportedNotification
from models.get_exported_files_list_model import ExportedDataItem
from models.subscribe_main_page_signals_info_model import SignalsInfo
from models.upload_exported_file_model import DownloadExportedDataReply
from utils.helpers.report_xlsx_utils import LeakReportRow, ReportTitleInfo


@dataclass
class CaseMarkers:
    """
    Маркеры тест-кейса для pytest и allure.
    """

    test_case_id: str
    offset: float


@dataclass
class BaseSuiteConfig:
    """
    Структура:
    1. Метаданные набора (имя, id, архив)
    2. Технологический участок (из enum TU)
    """

    # ===== Метаданные набора =====
    suite_name: str
    suite_data_id: int
    archive_name: str = ""  # Автоматически вычисляется из suite_name

    # ===== Технологический участок =====
    technological_unit: TU = TU.TIKHORETSK_NOVOROSSIYSK_3

    # ===== LDS Configurator (Администрирование) =====
    use_lds_configurator: bool = False
    tu_name: str = ""
    resolved_tu_id: Optional[int] = None
    lds_configurator_verify_test: Optional[CaseMarkers] = None

    # ===== Правила конвертации единиц измерения давления на стенде =====
    measure_conversion_rules: Optional[MeasureConversionRule] = None

    # ===== Общие константы (можно переопределить) =====
    allowed_distance_diff_meters: int = BaseTN3Constants.ALLOWED_DISTANCE_DIFF_METERS
    precision: int = BaseTN3Constants.PRECISION
    basic_message_timeout: float = BaseTN3Constants.BASIC_MESSAGE_TIMEOUT
    mask_message_timeout: float = BaseTN3Constants.MASK_MESSAGE_TIMEOUT
    mask_du_name: Optional[str] = None
    main_pipe_line: Optional[str] = None
    mask_du_event: Optional[str] = None
    unmask_du_event: Optional[str] = None

    # ===== Свойства для удобства =====
    def __post_init__(self) -> None:
        if not self.tu_name:
            object.__setattr__(self, "tu_name", self.technological_unit.description)

    @property
    def tu_id(self) -> int:
        """ID технологического участка"""
        if self.use_lds_configurator:
            if self.resolved_tu_id is None:
                raise RuntimeError(
                    "resolved_tu_id не установлен - выполните lds_configurator_admin_setup перед тестами сценария"
                )
            return self.resolved_tu_id
        # legacy: захардкоженный id из enum TU (имитатор использует тот же id для tn{id}_tags.txt)
        return self.technological_unit.id

    @property
    def infra_tu_id(self) -> int:
        """legacy: id ТУ для инфра-setup (имитатор, tags.txt, file_name)."""
        return self.technological_unit.id

    @property
    def has_multiple_leaks(self) -> bool:
        return False


@dataclass
class CaseData:
    """
    Данные тест-кейса.
    """

    name: str = ""
    params: Optional[Dict[str, Any]] = None
    expected_result: Optional[Any] = None
    description: str = ""


@dataclass
class DiagnosticAreaStatusConfig:
    """
    Конфигурация ожидаемых статусов СОУ для диагностического участка.
    Используется в тесте lds_status_during_leak.
    """

    leak_diagnostic_area_name: str
    leak_du_expected_lds_status: Any
    neighbors_du_expected_lds_status: Any


@dataclass
class LeakTestConfig:
    """
    Полная конфигурация утечки со всеми параметрами и тест-кейсами.

    Все данные для тестов утечки:
    - Параметры утечки (координата, объём)
    - Временные интервалы
    - Ожидаемые значения
    - Маркеры тестов (AllLeaksInfo, TuLeaksInfo, и т.д.)
    """

    # ===== Идентификаторы =====
    control_site_id: Optional[int] = None
    diagnostic_area_id: Optional[int] = None
    diagnostic_area_name: Optional[str] = None
    linear_part_id: Optional[int] = None
    technological_object: Optional[str] = None
    message_event_leak_completion: Optional[str] = None

    # ===== Параметры утечки =====
    coordinate_meters: float = None
    volume_m3: float = None
    max_pumping_m3: int = 2500  # Производительность(максимальная перекачка)
    flow_rate_settings_threshold: Optional[float] = None  # Порог объема дебаланса для текущего ДУ в текущем режиме

    # ===== Временные интервалы (секунды) =====
    leak_start_interval_seconds: int = BaseTN3Constants.LEAK_START_INTERVAL
    allowed_time_diff_seconds: int = 0  # Допустимое время обнаружения
    output_test_delay_seconds: int = BaseTN3Constants.OUTPUT_TEST_DELAY

    # ===== Ожидаемые статусы =====
    expected_lds_status: Any = LdsStatus.SERVICEABLE
    # Режим СОУ в xlsx export_leaks_report (колонка 'Режим работы СОУ')
    expected_lds_status_in_leaks_report: Optional[int] = None
    expected_report_stationary_status: int = StationaryStatus.STATIONARY.value
    expected_stationary_status: Any = StationaryStatus.STATIONARY
    expected_algorithm_type: Any = ReservedType.STATIONARY_FLOW
    expected_leak_status: Any = ConfirmationStatus.CONFIRMED
    expected_complete_leak_status: Any = ConfirmationStatus.CONFIRMED_AND_LEAK_CLOSED

    # ===== Конфигурация статусов СОУ во время утечки =====
    lds_status_during_leak_config: Optional[DiagnosticAreaStatusConfig] = None

    # ===== Данные тест-кейсов =====
    lds_status_after_confirming_leak_data: Optional[CaseData] = None
    lds_status_after_completed_leak_data: Optional[CaseData] = None

    # ===== Тест-кейсы для этой утечки =====
    balance_algorithm_leak_waiting_test: Optional[CaseMarkers] = None
    balance_algorithm_leak_detected_test: Optional[CaseMarkers] = None
    leaks_content_test: Optional[CaseMarkers] = None
    all_leaks_info_test: Optional[CaseMarkers] = None
    all_leaks_is_empty_test: Optional[CaseMarkers] = None
    tu_leaks_info_test: Optional[CaseMarkers] = None
    leak_info_in_journal: Optional[CaseMarkers] = None
    possible_leak_in_journal_test: Optional[CaseMarkers] = None
    acknowledge_leak_test: Optional[CaseMarkers] = None
    acknowledge_leak_in_journal_test: Optional[CaseMarkers] = None
    output_signals_test: Optional[CaseMarkers] = None
    lds_status_during_leak_test: Optional[CaseMarkers] = None
    lds_status_after_confirming_leak_test: Optional[CaseMarkers] = None
    lds_status_completed_leak_test: Optional[CaseMarkers] = None
    the_leak_is_complete_on_kg_test: Optional[CaseMarkers] = None
    leak_is_complete_in_output_signals_test: Optional[CaseMarkers] = None
    leak_is_complete_on_main_page_test: Optional[CaseMarkers] = None
    leak_is_confirm_on_main_page_test: Optional[CaseMarkers] = None
    complete_tu_leaks_info_content_test: Optional[CaseMarkers] = None
    completed_leak_info_in_journal_test: Optional[CaseMarkers] = None
    balance_algorithm_leak_completed_test: Optional[CaseMarkers] = None
    export_leaks_report_test: Optional[CaseMarkers] = None
    export_lds_status_report_test: Optional[CaseMarkers] = None
    export_mt_mode_report_test: Optional[CaseMarkers] = None

    @property
    def leak_diagnostic_area_id(self) -> Optional[int]:
        """ID диагностического участка с утечкой из lds_status_during_leak_config"""
        if self.lds_status_during_leak_config is not None:
            return self.lds_status_during_leak_config.leak_diagnostic_area_id
        return None

    @property
    def allowed_volume_m3(self) -> float:
        """Допустимая погрешность объёма"""
        return self.volume_m3 * BaseTN3Constants.ALLOWED_VOLUME_DIFF

    @property
    def leak_rate_percentages(self) -> float:
        """Интенсивность утечки в процентах"""
        return round((self.volume_m3 / self.max_pumping_m3) * 100, 2)

    @property
    def allowed_time_diff_minutes(self) -> float:
        """Допустимое время обнаружения утечки в минутах"""
        return round(self.allowed_time_diff_seconds / 60, 2)

    @property
    def output_allowed_time_diff_seconds(self) -> int:
        """Допустимое время для теста выходных сигналов"""
        return self.allowed_time_diff_seconds + self.output_test_delay_seconds


@dataclass
class SmokeSuiteConfig(BaseSuiteConfig):
    """
    Полная конфигурация тестового набора.

    Один конфиг = один набор данных = один файл в test_config/datasets/

    Структура:
    1. Базовые тесты с маркерами
    2. Конфигурации утечек (LeakTestConfig)
    """

    # ===== Ожидаемый статусы для main_page_info =====
    expected_stationary_status: Any = StationaryStatus.STATIONARY
    expected_main_page_signals: dict = field(default_factory=lambda: asdict(SignalsInfo()))

    # ===== Название Магистрального Нефтепровода =====
    main_pipeline: Optional[str] = None

    # ===== Ожидаемые переменные при маскировании ДУ =====
    mask_reason: Optional[str] = None
    unmask_reason: Optional[str] = None
    mask_one_du: Optional[int] = None
    not_mask_du: Optional[int] = None
    linear_part_identifier_for_mask: Optional[int] = None

    technological_section: Optional[str] = None
    imitate_flowmeter_signal_test_data: Optional[CaseData] = None
    imitate_pressure_sensor_signal_test_data: Optional[CaseData] = None
    # дефолтные значения для датчиков маскирования
    mask_signal_test_data: Optional[CaseData] = CaseData(
        params={
            "pressure_sensor_address": BaseTN3Constants.PRESSURE_SENSOR_ADDRESS,
            "flowmeter_address": BaseTN3Constants.FLOWMETER_ADDRESS,
        }
    )

    # ===== Ожидаемые переменные для проверок сообщений о режимах =====
    exp_mode_mt_message: Optional[CaseData] = None

    # ----- Ожидаемые статусы для проверки режимов на ЭФ Диагностика сигналов -----
    exp_tixoreczkaya_novovelichkovskaya_reg_lu: Optional[int] = None
    exp_tixoreczkaya_novovelichkovskaya_reg_sou: Optional[int] = None
    exp_novovelichkovskaya_krymskaya_reg_lu: Optional[int] = None
    exp_novovelichkovskaya_krymskaya_reg_sou: Optional[int] = None
    exp_krymskaya_grushovaya_reg_lu: Optional[int] = None
    exp_krymskaya_grushovaya_reg_sou: Optional[int] = None
    exp_backup_route_bejsug_reg_lu: Optional[int] = None
    exp_backup_route_bejsug_reg_sou: Optional[int] = None
    exp_backup_route_ponura_reg_lu: Optional[int] = None
    exp_backup_route_ponura_reg_sou: Optional[int] = None
    exp_backup_route_kuban_reg_lu: Optional[int] = None
    exp_backup_route_kuban_reg_sou: Optional[int] = None
    exp_npz_afipskij_reg_lu: Optional[int] = None
    exp_npz_afipskij_reg_sou: Optional[int] = None
    exp_npz_ilinskij_reg_lu: Optional[int] = None
    exp_npz_ilinskij_reg_sou: Optional[int] = None

    # ===== Базовые тесты =====
    basic_info_test: Optional[CaseMarkers] = None
    imitate_flowmeter_signal_test: Optional[CaseMarkers] = None
    imitate_pressure_sensor_signal_test: Optional[CaseMarkers] = None
    journal_info_test: Optional[CaseMarkers] = None
    lds_status_initialization_test: Optional[CaseMarkers] = None
    lds_status_init_in_journal_test: Optional[CaseMarkers] = None
    main_page_info_test: Optional[CaseMarkers] = None
    main_page_info_signals_test: Optional[CaseMarkers] = None
    mask_signal_test: Optional[CaseMarkers] = None
    mask_info_in_journal_test: Optional[CaseMarkers] = None
    lds_status_initialization_out_test: Optional[CaseMarkers] = None
    lds_status_init_out_in_journal_test: Optional[CaseMarkers] = None
    mask_du_on_mini_scheme_test: Optional[CaseMarkers] = None
    unmask_du_on_mini_scheme_test: Optional[CaseMarkers] = None
    diagnostics_of_signals_after_initialization_test: Optional[CaseMarkers] = None
    mode_mt_in_journal_test: Optional[CaseMarkers] = None

    # ===== Конфигурации утечек =====
    # Для наборов с одной утечкой
    leak: Optional[LeakTestConfig] = None

    # Для наборов с несколькими утечками (select_19_20)
    leaks: list[LeakTestConfig] = field(default_factory=list)

    # Участки в xlsx-отчёте о режиме работы СОУ (export_lds_status_report)
    lds_status_report_section_names: list[str] = field(default_factory=list)

    # ===== Дополнительные тесты для двух утечек =====
    main_page_info_unstationary_test: Optional[CaseMarkers] = None

    def get_leak(self, index: int = 0) -> Optional[LeakTestConfig]:
        """Получить конфигурацию утечки по индексу"""
        if self.leak and index == 0:
            return self.leak
        if self.leaks and index < len(self.leaks):
            return self.leaks[index]
        return None

    @property
    def has_multiple_leaks(self) -> bool:
        """Проверить, есть ли несколько утечек"""
        return len(self.leaks) > 1

    @property
    def allowed_volume_diff(self) -> float:
        """Относительная погрешность по объёму"""
        return BaseTN3Constants.ALLOWED_VOLUME_DIFF


@dataclass
class LDSStatusConfig(BaseSuiteConfig):
    """
    Полная конфигурация тестового набора.

    Один конфиг = один набор данных = один файл в test_config/datasets/

    Структура:
    1. Данные для тестов(параметры и ожидаемый результат)
    2. Тесты с маркерами
    """

    # ===== Название Магистрального Нефтепровода =====
    main_pipeline: Optional[str] = None

    # ===== Данные для тестов =====
    init_accumulation_data_test_data: Optional[CaseData] = None
    init_accumulation_data_in_journal_test_data: Optional[CaseData] = None
    init_cold_start_test_data: Optional[CaseData] = None
    init_exiting_faulty_test_data: Optional[CaseData] = None
    init_switching_shut_off_test_data: Optional[CaseData] = None
    init_switching_shut_off_in_journal_test_data: Optional[CaseData] = None
    serviceable_all_test_data: Optional[CaseData] = None
    serviceable_all_in_journal_test_data: Optional[CaseData] = None
    serviceable_after_switching_shut_off_test_data: Optional[CaseData] = None
    serviceable_after_switching_shut_off_in_journal_test_data: Optional[CaseData] = None
    serviceable_after_deg_faulty_pressure_sensors_at_pump_test_data: Optional[CaseData] = None
    serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal_test_data: Optional[CaseData] = None
    deg_faulty_pressure_sensors_at_pump_station_test_data: Optional[CaseData] = None
    deg_faulty_pressure_sensors_at_pump_station_in_journal_test_data: Optional[CaseData] = None
    deg_additive_injectors_operation_test_data: Optional[CaseData] = None
    deg_absence_min_pressure_sensors_test_data: Optional[CaseData] = None
    deg_exceeding_distance_between_pressure_sensors_test_data: Optional[CaseData] = None
    deg_exceeding_distance_between_pressure_sensors_in_journal_test_data: Optional[CaseData] = None
    deg_gravity_section_pumping_test_data: Optional[CaseData] = None
    deg_gravity_section_pumping_in_stopping_test_data: Optional[CaseData] = None
    deg_gravity_section_pumping_in_stopping_in_journal_test_data: Optional[CaseData] = None
    deg_pig_sensor_passage_test_data: Optional[CaseData] = None
    deg_starting_pumping_out_pumps_test_data: Optional[CaseData] = None
    deg_exceeding_distance_between_flow_meters_test_data: Optional[CaseData] = None
    deg_rejection_temperature_sensor_on_du_2_test_data: Optional[CaseData] = None
    deg_rejection_temperature_sensor_on_du_3_test_data: Optional[CaseData] = None
    deg_rejection_temperature_sensor_on_du_5_test_data: Optional[CaseData] = None
    deg_rejection_density_and_viscosity_on_du_2_test_data: Optional[CaseData] = None
    deg_rejection_density_and_viscosity_on_du_3_test_data: Optional[CaseData] = None
    deg_rejection_density_and_viscosity_on_du_5_test_data: Optional[CaseData] = None
    faulty_absence_min_flow_meters_test_data: Optional[CaseData] = None
    faulty_absence_min_pressure_sensors_test_data: Optional[CaseData] = None
    faulty_absence_min_pressure_sensors_in_journal_test_data: Optional[CaseData] = None
    # ===== Тесты =====
    lds_status_basic_info_test: Optional[CaseMarkers] = None
    init_accumulation_data_test: Optional[CaseMarkers] = None
    init_accumulation_data_in_journal_test: Optional[CaseMarkers] = None
    init_cold_start_test: Optional[CaseMarkers] = None
    init_cold_start_in_journal_test: Optional[CaseMarkers] = None
    init_exiting_faulty_test: Optional[CaseMarkers] = None
    init_switching_shut_off_test: Optional[CaseMarkers] = None
    init_switching_shut_off_in_journal_test: Optional[CaseMarkers] = None
    serviceable_after_cold_start_test: Optional[CaseMarkers] = None
    serviceable_after_cold_start_in_journal_test: Optional[CaseMarkers] = None
    serviceable_after_switching_shut_off_test: Optional[CaseMarkers] = None
    serviceable_after_switching_shut_off_in_journal_test: Optional[CaseMarkers] = None
    serviceable_after_deg_absence_min_pressure_sensors_test: Optional[CaseMarkers] = None
    serviceable_after_deg_starting_pumping_out_pumps_test: Optional[CaseMarkers] = None
    serviceable_after_deg_faulty_pressure_sensors_at_pump_test: Optional[CaseMarkers] = None
    serviceable_after_deg_faulty_pressure_sensors_at_pump_in_journal_test: Optional[CaseMarkers] = None
    serviceable_after_faulty_test: Optional[CaseMarkers] = None
    deg_additive_injectors_operation_test: Optional[CaseMarkers] = None
    deg_exceeding_distance_between_pressure_sensors_test: Optional[CaseMarkers] = None
    deg_exceeding_distance_between_pressure_sensors_in_journal_test: Optional[CaseMarkers] = None
    deg_absence_min_pressure_sensors_test: Optional[CaseMarkers] = None
    deg_faulty_pressure_sensors_at_pump_station_test: Optional[CaseMarkers] = None
    deg_faulty_pressure_sensors_at_pump_station_in_journal_test: Optional[CaseMarkers] = None
    deg_gravity_section_pumping_test: Optional[CaseMarkers] = None
    deg_gravity_section_pumping_in_stopping_test: Optional[CaseMarkers] = None
    deg_gravity_section_pumping_in_stopping_in_journal_test: Optional[CaseMarkers] = None
    deg_pig_sensor_passage_test: Optional[CaseMarkers] = None
    deg_starting_pumping_out_pumps_test: Optional[CaseMarkers] = None
    deg_exceeding_distance_between_flow_meters_test: Optional[CaseMarkers] = None
    deg_rejection_temperature_sensor_on_du_2_test: Optional[CaseMarkers] = None
    deg_rejection_temperature_sensor_on_du_3_test: Optional[CaseMarkers] = None
    deg_rejection_temperature_sensor_on_du_5_test: Optional[CaseMarkers] = None
    deg_rejection_density_and_viscosity_on_du_2_test: Optional[CaseMarkers] = None
    deg_rejection_density_and_viscosity_on_du_3_test: Optional[CaseMarkers] = None
    deg_rejection_density_and_viscosity_on_du_5_test: Optional[CaseMarkers] = None
    faulty_absence_min_flow_meters_test: Optional[CaseMarkers] = None
    faulty_absence_min_pressure_sensors_test: Optional[CaseMarkers] = None
    faulty_absence_min_pressure_sensors_in_journal_test: Optional[CaseMarkers] = None


@dataclass
class RejectionTestCase:
    """
    Описание одного события отбраковки для тестирования.

    Содержит:
    - Тег и id датчика (из RejectionSensorTag)
    - Ожидаемые значения для проверок журнала и схемы
    - Маркеры (offset и test_case_id)
    """

    name: str = ""
    sensor: RejectionSensorTag = ""
    expected_event: str = ""
    expected_signal_name: str = ""
    expected_criteria_names: Optional[RejectionCriteria] = None
    expected_is_rejected: bool = True
    time_range_start_s: float = 0
    time_range_end_s: float = 0
    rejection_input_signals_test: Optional[CaseMarkers] = None
    rejection_journal_test: Optional[CaseMarkers] = None
    rejection_main_page_test: Optional[CaseMarkers] = None
    rejection_scheme_signals_state_test: Optional[CaseMarkers] = None


@dataclass
class RejectionReportRow:
    """Разобранная строка отчёта об отбракованных входных данных."""

    row_index: int
    datetime_value: Optional[datetime] = None
    object_value: str = ""
    event_value: str = ""
    value_text: str = ""
    duration_seconds: int = 0
    tag_value: str = ""


@dataclass
class IsRejectedConfig(BaseSuiteConfig):
    """
    Конфигурация тестового набора отбраковки сигналов.

    Структура:
    1. Название МН
    2. Список случаев отбраковки (RejectionTestCase)
    """

    main_pipeline: str = ""
    rejection_cases: list[RejectionTestCase] = field(default_factory=list)
    rejection_report_test: Optional[CaseMarkers] = None


@dataclass
class ExportLeaksReportState:
    """
    Состояние сценария формирования xlsx-отчёта об утечках между allure-шагами.
    Заполняется по ходу export_leaks_report в smoke_scenarios.
    """

    report_test: Optional[CaseMarkers] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_start_naive: Optional[datetime] = None
    period_end_naive: Optional[datetime] = None
    expected_mt_mode: Optional[str] = None
    expected_lds_status_text: Optional[str] = None
    time_offset_hours: Optional[int] = None
    tu_description_lower: str = ""
    notification: Optional[ReportDataExportedNotification] = None
    report_item: Optional[ExportedDataItem] = None
    report_file_name: str = ""
    download_invocation_id: Optional[str] = None
    download_payload: Optional[list] = None
    download_reply: Optional[DownloadExportedDataReply] = None
    file_bytes: Optional[bytes] = None
    temp_file_path: Optional[Path] = None
    worksheet: Any = None
    title_info: Optional[ReportTitleInfo] = None
    data_rows: list[LeakReportRow] = field(default_factory=list)
    target_row: Optional[LeakReportRow] = None


@dataclass
class ExportLdsStatusReportState:
    """Состояние сценария формирования xlsx-отчёта о режиме работы СОУ."""

    report_test: Optional[CaseMarkers] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    period_start_naive: Optional[datetime] = None
    period_end_naive: Optional[datetime] = None
    time_offset_hours: Optional[int] = None
    tu_description_lower: str = ""
    notification: Optional[ReportDataExportedNotification] = None
    report_item: Optional[ExportedDataItem] = None
    report_file_name: str = ""
    download_invocation_id: Optional[str] = None
    download_reply: Optional[DownloadExportedDataReply] = None
    file_bytes: Optional[bytes] = None
    temp_file_path: Optional[Path] = None
    worksheet: Any = None
    parsed_report: Any = None


@dataclass
class ExportRejectedReportState:
    """
    Состояние сценария формирования xlsx-отчёта об отбракованных входных данных.
    Поля с префиксом expected_ - из конфигурации теста, actual_ - из ответов бэка и разбора xlsx.
    """

    # --- expected: конфигурация теста и расчётные ожидания ---
    expected_report_test: Optional[CaseMarkers] = None
    expected_period_start: Optional[datetime] = None
    expected_period_end: Optional[datetime] = None
    expected_period_start_naive: Optional[datetime] = None
    expected_period_end_naive: Optional[datetime] = None
    expected_tu_description_lower: str = ""
    expected_file_name: str = ""

    # --- actual: ответы бэка ---
    actual_time_offset_hours: Optional[int] = None
    actual_notification: Optional[ReportDataExportedNotification] = None
    actual_report_item: Optional[ExportedDataItem] = None
    actual_download_invocation_id: Optional[str] = None
    actual_download_reply: Optional[DownloadExportedDataReply] = None
    actual_file_bytes: Optional[bytes] = None

    # --- actual: разбор xlsx ---
    actual_temp_file_path: Optional[Path] = None
    actual_worksheet: Any = None
    actual_title_info: Optional[ReportTitleInfo] = None
    actual_data_rows: list[RejectionReportRow] = field(default_factory=list)
    actual_monitored_tag_rows: list[RejectionReportRow] = field(default_factory=list)
    actual_header_column_headers: list[str] = field(default_factory=list)
    actual_header_period_start: Optional[datetime] = None
    actual_header_period_end: Optional[datetime] = None
    actual_header_contains_expected_title: bool = False
    actual_case_checks: list = field(default_factory=list)


@dataclass
class ExportMtModeReportState:
    """
    Состояние сценария формирования xlsx-отчёта о режиме работы МТ.
    Поля с префиксом expected_ - из конфигурации теста, actual_ - из ответов бэка и разбора xlsx.
    """

    # --- expected: конфигурация теста и расчётные ожидания ---
    expected_report_test: Optional[CaseMarkers] = None
    expected_period_start: Optional[datetime] = None
    expected_period_end: Optional[datetime] = None
    expected_period_start_naive: Optional[datetime] = None
    expected_period_end_naive: Optional[datetime] = None
    expected_tu_description_lower: str = ""
    expected_file_name: str = ""
    expected_section_names: list[str] = field(default_factory=list)
    expected_dominant_mode_column: str = ""

    # --- actual: ответы бэка ---
    actual_time_offset_hours: Optional[int] = None
    actual_notification: Optional[ReportDataExportedNotification] = None
    actual_report_item: Optional[ExportedDataItem] = None
    actual_download_invocation_id: Optional[str] = None
    actual_download_reply: Optional[DownloadExportedDataReply] = None
    actual_file_bytes: Optional[bytes] = None

    # --- actual: разбор xlsx ---
    actual_temp_file_path: Optional[Path] = None
    actual_worksheet: Any = None
    actual_parsed_report: Any = None
