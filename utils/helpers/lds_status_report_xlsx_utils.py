"""
Утилиты для разбора xlsx-отчёта о режиме работы СОУ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Dict, List, Optional, Tuple

from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportLdsStatusReportConstants as LdsReportConst
from utils.helpers.report_xlsx_utils import (
    ReportTitleInfo,
    _stringify_cell,
    build_column_cells,
    get_report_column_headers,
    parse_report_title,
)


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
    """Форматирует длительность в секундах в строку H:MM:SS (минуты и секунды с ведущим нулём)."""
    hours, remainder = divmod(total_seconds, TestConst.SECONDS_PER_HOUR)
    minutes, seconds = divmod(remainder, TestConst.SEC_PER_MIN)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def find_total_work_duration(
    worksheet: Worksheet,
    *,
    data_first_row: int,
    total_work_duration_label: str,
) -> Tuple[Optional[int], str, Optional[int]]:
    """
    Ищет строку «Суммарное время работы:» и парсит длительность рядом.

    Возвращает (секунды, сырое значение ячейки, номер строки с меткой) или (None, "", None).
    """
    for row_index, row_values in enumerate(
        worksheet.iter_rows(min_row=data_first_row, values_only=True),
        start=data_first_row,
    ):
        for column_index, cell_value in enumerate(row_values):
            if cell_value is None:
                continue
            cell_text = _stringify_cell(cell_value).strip()
            if total_work_duration_label not in cell_text:
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


def _find_total_work_duration(worksheet: Worksheet) -> Tuple[Optional[int], str, Optional[int]]:
    """
    Ищет строку "Суммарное время работы:" и парсит длительность рядом (в той же или следующей строке).

    Возвращает: (секунды, сырое значение ячейки, номер строки с меткой) или (None, "", None).
    """
    return find_total_work_duration(
        worksheet,
        data_first_row=LdsReportConst.REPORT_DATA_FIRST_ROW,
        total_work_duration_label=LdsReportConst.TOTAL_WORK_DURATION_LABEL,
    )


def parse_lds_status_report_worksheet(
    worksheet: Worksheet,
    expected_section_names: List[str],
) -> LdsStatusReportParsed:
    """
    Разбирает лист xlsx-отчёта о режиме СОУ: шапка, колонки, строки участков и суммарное время.

    В section_rows попадают только участки из expected_section_names (без учёта регистра).
    """
    headers = get_report_column_headers(worksheet, LdsReportConst.REPORT_COLUMN_HEADERS_ROW)
    title_info = parse_report_title(
        worksheet.cell(row=LdsReportConst.REPORT_TITLE_ROW, column=1).value,
        LdsReportConst.REPORT_HEADER_PERIOD_PATTERN,
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


__all__ = [
    "LdsStatusReportParsed",
    "LdsStatusReportSectionRow",
    "format_duration_seconds",
    "format_section_rows_for_allure",
    "is_duration_cell_filled",
    "parse_duration_seconds",
    "parse_lds_status_report_worksheet",
]
