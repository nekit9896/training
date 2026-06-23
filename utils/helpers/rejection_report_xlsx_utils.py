"""
Утилиты для разбора xlsx-отчёта об отбракованных входных данных.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Iterable, List, Optional, Tuple

from constants.enums import RejectionSensorTag
from constants.test_constants import ExportRejectedReportConstants as RejectedReportConst
from test_config.models_for_tests import RejectionReportRow, RejectionTestCase
from utils.helpers import report_xlsx_utils as report_utils
from utils.helpers.lds_status_report_xlsx_utils import format_duration_seconds, parse_duration_seconds
from utils.helpers.ws_test_utils import localize_as_moscow

MergeKey = Tuple[Optional[datetime], str, str, str, str]


@dataclass
class RejectionReportCaseCheck:
    """Подготовленные данные для проверки одного RejectionTestCase в xlsx-отчёте."""

    case_label: str
    tag_description: str
    report_event: str
    window_start: datetime
    window_end: datetime
    row_found: bool
    found_row_summary: str
    datetime_in_window: bool = False
    datetime_actual_text: str = "(пусто)"
    actual_duration_seconds: int = 0
    expected_duration_seconds: int = 0
    expected_duration_text: str = ""
    pipe_section: str = ""
    actual_signal_suffix: str = ""
    expected_signal_suffix: str = ""


def prepare_rejection_report_case_checks(
    monitored_rows: Iterable[RejectionReportRow],
    rejection_cases: Iterable[RejectionTestCase],
    imitator_start_time: datetime,
) -> List[RejectionReportCaseCheck]:
    """Собирает все вычисленные значения для проверки строк отчёта по кейсам набора."""
    case_checks: List[RejectionReportCaseCheck] = []

    for rejection_case in rejection_cases:
        report_event = expected_event_to_report_event(rejection_case.expected_event)
        window_start, window_end = get_case_time_window(imitator_start_time, rejection_case)
        case_label = f"события '{report_event}' - {rejection_case.sensor.description}"
        expected_signal_suffix = report_signal_suffix_by_expected_name(rejection_case.expected_signal_name)

        raw_case_rows = filter_rows_for_rejection_case(monitored_rows, rejection_case, imitator_start_time)
        merged_case_rows = merge_rejection_rows(raw_case_rows)
        primary_row = select_primary_merged_row(merged_case_rows)

        if primary_row is None:
            case_checks.append(
                RejectionReportCaseCheck(
                    case_label=case_label,
                    tag_description=rejection_case.sensor.description,
                    report_event=report_event,
                    window_start=window_start,
                    window_end=window_end,
                    row_found=False,
                    found_row_summary="строка не найдена",
                    expected_signal_suffix=expected_signal_suffix,
                )
            )
            continue

        merge_key = build_merge_key(primary_row)
        expected_duration_seconds = sum_duration_for_merge_key(raw_case_rows, merge_key)
        pipe_section, actual_signal_suffix = split_object_column(primary_row.object_value)
        datetime_in_window = is_datetime_within_closed_interval(
            primary_row.datetime_value,
            window_start,
            window_end,
        )

        case_checks.append(
            RejectionReportCaseCheck(
                case_label=case_label,
                tag_description=rejection_case.sensor.description,
                report_event=report_event,
                window_start=window_start,
                window_end=window_end,
                row_found=True,
                found_row_summary=(
                    f"{primary_row.tag_value} | {primary_row.event_value} | {primary_row.datetime_value}"
                ),
                datetime_in_window=datetime_in_window,
                datetime_actual_text=str(primary_row.datetime_value) if primary_row.datetime_value else "(пусто)",
                actual_duration_seconds=primary_row.duration_seconds,
                expected_duration_seconds=expected_duration_seconds,
                expected_duration_text=format_duration_seconds(expected_duration_seconds),
                pipe_section=pipe_section,
                actual_signal_suffix=actual_signal_suffix,
                expected_signal_suffix=expected_signal_suffix,
            )
        )

    return case_checks


def expected_event_to_report_event(expected_event: str) -> str:
    """Преобразует формулировку события из журнала в формулировку отчёта."""
    return expected_event.replace("Отбраковка", "Отбракован", 1)


def report_signal_suffix_by_expected_name(expected_signal_name: str) -> str:
    """Возвращает суффикс сигнала в колонке 'Объект' отчёта по expected_signal_name из кейса."""
    return RejectedReportConst.REPORT_SIGNAL_SUFFIX_BY_EXPECTED_NAME.get(
        expected_signal_name,
        expected_signal_name,
    )


def split_object_column(object_value: str) -> tuple[str, str]:
    """
    Разбирает колонку «Объект»:
    - до последней точки - участок трубопровода (имя объекта);
    - после последней точки - название сигнала.
    """
    if not object_value:
        return "", ""
    if RejectedReportConst.OBJECT_SIGNAL_SEPARATOR not in object_value:
        return object_value.strip(), ""

    pipe_section, signal_suffix = object_value.rsplit(
        RejectedReportConst.OBJECT_SIGNAL_SEPARATOR,
        RejectedReportConst.OBJECT_SIGNAL_RSPLIT_MAXSPLIT,
    )
    return pipe_section.strip(), signal_suffix.strip()


def is_datetime_within_closed_interval(
    value: datetime,
    interval_start: datetime,
    interval_end: datetime,
) -> bool:
    """True, если value (в Europe/Moscow) попадает в закрытый интервал [interval_start, interval_end]."""
    localized_value = localize_as_moscow(value)
    return interval_start <= localized_value <= interval_end


def report_header_contains_expected_title(raw_title: str) -> bool:
    """Проверяет, что первая строка шапки xlsx содержит ожидаемый заголовок отчёта."""
    title_lower = raw_title.lower()
    return (
        RejectedReportConst.REJECTED_REPORT_HEADER_TITLE_PART in title_lower
        or RejectedReportConst.REJECTED_REPORT_HEADER_TITLE_PART_ALT in title_lower
    )


def build_merge_key(row: RejectionReportRow) -> MergeKey:
    """Ключ объединения строк с одинаковым содержимым, кроме длительности."""
    return (
        row.datetime_value,
        row.object_value,
        row.event_value,
        row.value_text,
        row.tag_value,
    )


def parse_rejection_report_row(row_index: int, cells: dict[str, str]) -> RejectionReportRow:
    """Собирает RejectionReportRow из словаря ячеек строки отчёта."""
    duration_seconds = parse_duration_seconds(cells.get(RejectedReportConst.COL_DURATION)) or 0
    return RejectionReportRow(
        row_index=row_index,
        datetime_value=report_utils.parse_report_datetime(cells.get(RejectedReportConst.COL_DATETIME)),
        object_value=(cells.get(RejectedReportConst.COL_OBJECT) or "").strip(),
        event_value=(cells.get(RejectedReportConst.COL_EVENT) or "").strip(),
        value_text=(cells.get(RejectedReportConst.COL_VALUE) or "").strip(),
        duration_seconds=duration_seconds,
        tag_value=(cells.get(RejectedReportConst.COL_TAG) or "").strip(),
    )


def iter_rejection_report_rows(worksheet) -> List[RejectionReportRow]:
    """Возвращает строки данных отчёта, начиная с третьей строки листа."""
    headers = report_utils.get_report_column_headers(
        worksheet,
        headers_row=RejectedReportConst.REPORT_COLUMN_HEADERS_ROW,
    )
    if not headers:
        return []

    rows: List[RejectionReportRow] = []
    for excel_row_index, row_values in enumerate(
        worksheet.iter_rows(
            min_row=RejectedReportConst.REPORT_DATA_FIRST_ROW,
            max_col=len(headers),
            values_only=True,
        ),
        start=RejectedReportConst.REPORT_DATA_FIRST_ROW,
    ):
        if not any(cell is not None and str(cell).strip() for cell in row_values):
            continue
        cells = report_utils.build_column_cells(row_values, headers)
        rows.append(parse_rejection_report_row(excel_row_index, cells))
    return rows


def filter_rows_by_monitored_tags(
    rows: Iterable[RejectionReportRow],
    monitored_tags: Iterable[RejectionSensorTag],
) -> List[RejectionReportRow]:
    """Оставляет только строки с тегами из RejectionSensorTag."""
    allowed_tags = {tag.description for tag in monitored_tags}
    return [row for row in rows if row.tag_value in allowed_tags]


def get_case_time_window(
    imitator_start_time: datetime,
    rejection_case: RejectionTestCase,
    tolerance_seconds: int = RejectedReportConst.TIME_FILTER_TOLERANCE_SECONDS,
) -> tuple[datetime, datetime]:
    """Возвращает окно фильтрации строк отчёта для конкретного RejectionTestCase."""
    imitator_msk = localize_as_moscow(imitator_start_time)
    window_start = imitator_msk + timedelta(seconds=rejection_case.time_range_start_s - tolerance_seconds)
    window_end = imitator_msk + timedelta(seconds=rejection_case.time_range_end_s + tolerance_seconds)
    return window_start, window_end


def filter_rows_for_rejection_case(
    rows: Iterable[RejectionReportRow],
    rejection_case: RejectionTestCase,
    imitator_start_time: datetime,
) -> List[RejectionReportRow]:
    """Фильтрует строки отчёта по тегу, событию и временному окну RejectionTestCase."""
    report_event = expected_event_to_report_event(rejection_case.expected_event)
    window_start, window_end = get_case_time_window(imitator_start_time, rejection_case)
    filtered_rows: List[RejectionReportRow] = []

    for row in rows:
        if row.tag_value != rejection_case.sensor.description:
            continue
        if row.event_value != report_event:
            continue
        if row.datetime_value is None:
            continue
        if not is_datetime_within_closed_interval(row.datetime_value, window_start, window_end):
            continue
        filtered_rows.append(row)

    return filtered_rows


def merge_rejection_rows(rows: Iterable[RejectionReportRow]) -> List[RejectionReportRow]:
    """
    Объединяет полностью идентичные строки, суммируя длительность отбраковки.
    """
    merged_rows: dict[MergeKey, RejectionReportRow] = {}
    for row in rows:
        merge_key = build_merge_key(row)
        if merge_key not in merged_rows:
            merged_rows[merge_key] = replace(row)
            continue
        merged_rows[merge_key].duration_seconds += row.duration_seconds

    return list(merged_rows.values())


def select_primary_merged_row(merged_rows: List[RejectionReportRow]) -> Optional[RejectionReportRow]:
    """Выбирает основную строку отбраковки - с максимальной суммарной длительностью."""
    if not merged_rows:
        return None
    return max(merged_rows, key=lambda row: row.duration_seconds)


def sum_duration_for_merge_key(rows: Iterable[RejectionReportRow], merge_key: MergeKey) -> int:
    """Суммирует длительности всех сырых строк с одинаковым ключом объединения."""
    return sum(row.duration_seconds for row in rows if build_merge_key(row) == merge_key)


def format_rejection_rows_for_allure(rows: Iterable[RejectionReportRow]) -> str:
    """Форматирует строки отчёта для вложения в Allure."""
    lines = []
    for row in rows:
        duration_text = format_duration_seconds(row.duration_seconds)
        lines.append(
            f"row#{row.row_index}: {row.datetime_value} | {row.object_value} | "
            f"{row.event_value} | {row.value_text} | {duration_text} | {row.tag_value}"
        )
    return "\n".join(lines) if lines else "(нет строк)"
