"""
Утилиты для разбора xlsx-отчёта о режиме работы МТ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import ExportMtModeReportConstants as MtReportConst
from utils.helpers.lds_status_report_xlsx_utils import (
    find_total_work_duration,
    format_duration_seconds,
    is_duration_cell_filled,
    parse_duration_seconds,
)
from utils.helpers.report_xlsx_utils import (
    ReportTitleInfo,
    build_column_cells,
    get_report_column_headers,
    parse_report_title,
    sum_duration_columns_across_rows,
)


@dataclass
class MtModeReportSectionRow:
    """Строка участка с длительностями режимов МТ."""

    row_index: int
    section_name: str
    cells: Dict[str, str] = field(default_factory=dict)

    @property
    def mode_durations_seconds(self) -> Dict[str, int]:
        """Длительности режимов МТ в секундах по колонкам отчёта."""
        return {
            column_name: parse_duration_seconds(self.cells.get(column_name)) or 0
            for column_name in MtReportConst.MODE_DURATION_COLUMNS
        }

    @property
    def modes_sum_seconds(self) -> int:
        """Сумма длительностей всех режимов МТ для участка."""
        return sum(self.mode_durations_seconds.values())


@dataclass
class MtModeReportParsed:
    """Разобранный отчёт о режиме работы МТ."""

    title_info: ReportTitleInfo
    column_headers: List[str]
    section_rows: List[MtModeReportSectionRow]
    total_duration_seconds: Optional[int] = None
    total_duration_raw: str = ""
    total_label_row_index: Optional[int] = None


def is_expected_dominant_mode_column(mode_totals: Dict[str, int], expected_column: str) -> bool:
    """
    Проверяет, что суммарное время ожидаемого режима строго максимально и больше нуля.

    Не допускает «мягкую» проверку <=, чтобы не пропустить ничью с другим режимом.
    """
    expected_total = mode_totals.get(expected_column, 0)
    if expected_total <= 0:
        return False
    return expected_total == max(mode_totals.values())


def parse_mt_mode_report_worksheet(
    worksheet: Worksheet,
    expected_section_names: List[str],
) -> MtModeReportParsed:
    """
    Разбирает лист xlsx-отчёта о режиме МТ: шапка, колонки, строки участков и суммарное время.

    В section_rows попадают только участки из expected_section_names (без учёта регистра).
    """
    headers = get_report_column_headers(worksheet, MtReportConst.REPORT_COLUMN_HEADERS_ROW)
    title_info = parse_report_title(
        worksheet.cell(row=MtReportConst.REPORT_TITLE_ROW, column=1).value,
        MtReportConst.REPORT_HEADER_PERIOD_PATTERN,
    )
    total_duration_seconds, total_duration_raw, total_label_row_index = find_total_work_duration(
        worksheet,
        data_first_row=MtReportConst.REPORT_DATA_FIRST_ROW,
        total_work_duration_label=MtReportConst.TOTAL_WORK_DURATION_LABEL,
    )

    section_rows: List[MtModeReportSectionRow] = []
    expected_names_lower = {name.lower() for name in expected_section_names}

    for row_index, row_values in enumerate(
        worksheet.iter_rows(
            min_row=MtReportConst.REPORT_DATA_FIRST_ROW,
            max_col=len(headers) if headers else 5,
            values_only=True,
        ),
        start=MtReportConst.REPORT_DATA_FIRST_ROW,
    ):
        if total_label_row_index is not None and row_index >= total_label_row_index:
            break

        cells = build_column_cells(row_values, headers)
        section_name = cells.get(MtReportConst.COL_SECTION, "").strip()
        if not section_name:
            continue
        if section_name.lower() not in expected_names_lower:
            continue

        section_rows.append(
            MtModeReportSectionRow(
                row_index=row_index,
                section_name=section_name,
                cells=cells,
            )
        )

    return MtModeReportParsed(
        title_info=title_info,
        column_headers=headers,
        section_rows=section_rows,
        total_duration_seconds=total_duration_seconds,
        total_duration_raw=total_duration_raw,
        total_label_row_index=total_label_row_index,
    )


def format_mt_mode_section_rows_for_allure(section_rows: List[MtModeReportSectionRow]) -> str:
    """Форматирует строки участков отчёта о режиме МТ для вложения в Allure."""
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
    "MtModeReportParsed",
    "MtModeReportSectionRow",
    "format_mt_mode_section_rows_for_allure",
    "is_duration_cell_filled",
    "is_expected_dominant_mode_column",
    "parse_mt_mode_report_worksheet",
    "sum_duration_columns_across_rows",
]
