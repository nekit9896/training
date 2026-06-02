"""
Утилиты для разбора xlsx-отчёта о режиме работы СОУ.
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import allure
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportLdsStatusReportConstants as LdsReportConst
from constants.test_constants import ExportReportConstants as ReportConst
from utils.helpers.report_xlsx_utils import (
    ReportTitleInfo,
    _stringify_cell,
    attach_report_file_to_allure,
    build_column_cells,
    is_xlsx_extension,
    is_xlsx_file_bytes,
    normalize_report_period_naive,
    parse_report_datetime,
    report_period_comparison_bounds,
)
from utils.helpers.ws_test_utils import localize_as_moscow


@dataclass
class LdsStatusReportSectionRow:
    """Строка участка с длительностями режимов СОУ."""

    row_index: int
    section_name: str
    cells: Dict[str, str] = field(default_factory=dict)

    @property
    def mode_durations_seconds(self) -> Dict[str, int]:
        return {
            column_name: parse_duration_seconds(self.cells.get(column_name)) or 0
            for column_name in LdsReportConst.MODE_DURATION_COLUMNS
        }

    @property
    def modes_sum_seconds(self) -> int:
        return sum(self.mode_durations_seconds.values())


@dataclass
class LdsStatusReportParsed:
    """Разобранный отчёт о режиме работы СОУ."""

    title_info: ReportTitleInfo
    column_headers: List[str]
    section_rows: List[LdsStatusReportSectionRow]
    total_duration_seconds: Optional[int] = None
    total_duration_raw: str = ""
    total_label_row_index: Optional[int] = None


def parse_duration_seconds(value: object) -> Optional[int]:
    """Парсит длительность из ячейки (H:MM:SS, MM:SS или time/timedelta из Excel)."""
    if value is None:
        return None
    if isinstance(value, timedelta):
        return int(value.total_seconds())
    if isinstance(value, time):
        return (
            value.hour * TestConst.SECONDS_PER_HOUR
            + value.minute * TestConst.SEC_PER_MIN
            + value.second
        )
    if isinstance(value, datetime):
        return (
            value.hour * TestConst.SECONDS_PER_HOUR
            + value.minute * TestConst.SEC_PER_MIN
            + value.second
        )

    duration_text = _stringify_cell(value).strip()
    if not duration_text:
        return None

    parts = duration_text.split(":")
    try:
        if len(parts) == LdsReportConst.DURATION_PARTS_COUNT_H_MM_SS:
            hours, minutes, seconds = (int(part) for part in parts)
            return (
                hours * TestConst.SECONDS_PER_HOUR
                + minutes * TestConst.SEC_PER_MIN
                + seconds
            )
        if len(parts) == LdsReportConst.DURATION_PARTS_COUNT_MM_SS:
            minutes, seconds = (int(part) for part in parts)
            return minutes * TestConst.SEC_PER_MIN + seconds
    except ValueError:
        return None
    return None


def is_duration_cell_filled(value: object) -> bool:
    """Ячейка с длительностью заполнена (допускается 0:00:00)."""
    return parse_duration_seconds(value) is not None


def format_duration_seconds(total_seconds: int) -> str:
    hours, remainder = divmod(total_seconds, TestConst.SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, TestConst.SEC_PER_MIN)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def parse_lds_status_report_title(title_raw: object) -> ReportTitleInfo:
    title_str = _stringify_cell(title_raw)
    match = re.search(LdsReportConst.REPORT_HEADER_PERIOD_PATTERN, title_str)
    if match is None:
        return ReportTitleInfo(raw_title=title_str)

    return ReportTitleInfo(
        raw_title=title_str,
        period_start=parse_report_datetime(match.group("period_start")),
        period_end=parse_report_datetime(match.group("period_end")),
    )


def build_lds_status_report_file_name(
    tu_description: str,
    period_start: datetime,
    period_end: datetime,
) -> str:
    start_text = normalize_report_period_naive(period_start).strftime(ReportConst.REPORT_FILE_NAME_DATETIME_FORMAT)
    end_text = normalize_report_period_naive(period_end).strftime(ReportConst.REPORT_FILE_NAME_DATETIME_FORMAT)
    return (
        f"{LdsReportConst.LDS_STATUS_REPORT_NAME_PART}. {tu_description} {start_text} - {end_text}"
        f"{ReportConst.XLSX_EXTENSION}"
    )


def parse_period_from_lds_status_report_file_name(file_name: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    match = re.search(LdsReportConst.REPORT_FILE_NAME_PERIOD_PATTERN, file_name.strip(), re.IGNORECASE)
    if match is None:
        return None, None

    parse_format = ReportConst.REPORT_FILE_NAME_DATETIME_FORMAT.replace("_", ":")

    def _parse_part(value: str) -> Optional[datetime]:
        try:
            return datetime.strptime(value.replace("_", ":"), parse_format)
        except ValueError:
            return None

    return _parse_part(match.group("period_start")), _parse_part(match.group("period_end"))


def get_lds_status_report_column_headers(worksheet: Worksheet) -> List[str]:
    headers: List[str] = []
    column_index = 1
    while True:
        cell_value = worksheet.cell(row=LdsReportConst.REPORT_COLUMN_HEADERS_ROW, column=column_index).value
        if cell_value is None or not str(cell_value).strip():
            break
        headers.append(_stringify_cell(cell_value).strip())
        column_index += 1
    return headers


def _find_total_work_duration(worksheet: Worksheet) -> Tuple[Optional[int], str, Optional[int]]:
    for row_index, row_values in enumerate(
        worksheet.iter_rows(min_row=LdsReportConst.REPORT_DATA_FIRST_ROW, values_only=True),
        start=LdsReportConst.REPORT_DATA_FIRST_ROW,
    ):
        for column_index, cell_value in enumerate(row_values):
            if cell_value is None:
                continue
            cell_text = _stringify_cell(cell_value).strip()
            if LdsReportConst.TOTAL_WORK_DURATION_LABEL not in cell_text:
                continue

            duration_candidates = []
            if column_index + 1 < len(row_values):
                duration_candidates.append(row_values[column_index + 1])
            if row_index + 1 <= worksheet.max_row:
                duration_candidates.append(
                    worksheet.cell(row=row_index + 1, column=column_index + 1).value
                )

            for candidate in duration_candidates:
                duration_seconds = parse_duration_seconds(candidate)
                if duration_seconds is not None:
                    return duration_seconds, _stringify_cell(candidate).strip(), row_index

            return None, "", row_index

    return None, "", None


def parse_lds_status_report_worksheet(
    worksheet: Worksheet,
    expected_section_names: List[str],
) -> LdsStatusReportParsed:
    headers = get_lds_status_report_column_headers(worksheet)
    title_info = parse_lds_status_report_title(
        worksheet.cell(row=LdsReportConst.REPORT_TITLE_ROW, column=1).value
    )
    total_duration_seconds, total_duration_raw, total_label_row_index = _find_total_work_duration(worksheet)

    section_rows: List[LdsStatusReportSectionRow] = []
    expected_names_lower = {name.lower() for name in expected_section_names}

    for row_index, row_values in enumerate(
        worksheet.iter_rows(
            min_row=LdsReportConst.REPORT_DATA_FIRST_ROW,
            max_col=len(headers) if headers else 5,
            values_only=True,
        ),
        start=LdsReportConst.REPORT_DATA_FIRST_ROW,
    ):
        if total_label_row_index is not None and row_index >= total_label_row_index:
            break

        cells = build_column_cells(row_values, headers)
        section_name = cells.get(LdsReportConst.COL_SECTION, "").strip()
        if not section_name:
            continue
        if section_name.lower() not in expected_names_lower:
            continue

        section_rows.append(
            LdsStatusReportSectionRow(
                row_index=row_index,
                section_name=section_name,
                cells=cells,
            )
        )

    return LdsStatusReportParsed(
        title_info=title_info,
        column_headers=headers,
        section_rows=section_rows,
        total_duration_seconds=total_duration_seconds,
        total_duration_raw=total_duration_raw,
        total_label_row_index=total_label_row_index,
    )


def save_lds_status_report_bytes_to_temp_file(file_bytes: bytes) -> Optional[Path]:
    try:
        with tempfile.NamedTemporaryFile(
            suffix=ReportConst.XLSX_EXTENSION,
            prefix="lds_status_report_",
            delete=False,
        ) as temp_file:
            temp_file.write(file_bytes)
            return Path(temp_file.name)
    except OSError:
        return None


def load_lds_status_report_worksheet(file_path: Path) -> Optional[Worksheet]:
    if not file_path.exists():
        return None
    try:
        workbook = load_workbook(filename=str(file_path), read_only=True, data_only=True)
    except Exception:
        return None
    sheet_names = workbook.sheetnames
    if not sheet_names:
        return None
    return workbook[sheet_names[ReportConst.DEFAULT_SHEET_INDEX]]


def format_section_rows_for_allure(section_rows: List[LdsStatusReportSectionRow]) -> str:
    lines = []
    for row in section_rows:
        durations_text = ", ".join(
            f"{column}={format_duration_seconds(seconds)}"
            for column, seconds in row.mode_durations_seconds.items()
        )
        lines.append(
            f"row#{row.row_index}: {row.section_name} | sum={format_duration_seconds(row.modes_sum_seconds)} | "
            f"{durations_text}"
        )
    return "\n".join(lines)


__all__ = [
    "LdsStatusReportParsed",
    "LdsStatusReportSectionRow",
    "build_lds_status_report_file_name",
    "format_duration_seconds",
    "format_section_rows_for_allure",
    "is_duration_cell_filled",
    "is_xlsx_extension",
    "is_xlsx_file_bytes",
    "load_lds_status_report_worksheet",
    "parse_duration_seconds",
    "parse_lds_status_report_worksheet",
    "parse_period_from_lds_status_report_file_name",
    "report_period_comparison_bounds",
    "save_lds_status_report_bytes_to_temp_file",
    "attach_report_file_to_allure",
]
