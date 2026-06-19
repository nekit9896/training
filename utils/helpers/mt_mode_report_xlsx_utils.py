"""
Утилиты для разбора xlsx-отчёта о режиме работы МТ.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from openpyxl import load_workbook
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
    _stringify_cell,
    build_column_cells,
    get_report_column_headers,
    parse_report_title,
    read_worksheet_cell_formula,
    read_worksheet_cell_value,
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
    chart_title_raw: str = ""
    chart_series_formula: str = ""


def _find_mt_mode_chart_series_formula(source_file_path: Path) -> str:
    """Ищет формулу SERIES/РЯД: сначала в I3, затем по всем ячейкам листа xlsx."""
    formula = read_worksheet_cell_formula(
        source_file_path,
        MtReportConst.CHART_FORMULA_ROW,
        MtReportConst.CHART_FORMULA_COLUMN,
    )
    if is_valid_mt_mode_chart_series_formula(formula):
        return formula

    if not source_file_path.exists():
        return ""

    workbook = None
    try:
        workbook = load_workbook(filename=str(source_file_path), read_only=False, data_only=False)
        for worksheet in workbook.worksheets:
            for row in worksheet.iter_rows():
                for cell in row:
                    value = cell.value
                    if isinstance(value, str) and is_valid_mt_mode_chart_series_formula(value):
                        return value
    except Exception:
        return ""
    finally:
        if workbook is not None:
            workbook.close()

    return ""


def read_mt_mode_chart_metadata(source_file_path: Path) -> tuple[str, str]:
    """
    Читает заголовок (F2) и формулу диаграммы (I3 или первую подходящую SERIES/РЯД в листе xlsx).
    """
    chart_title_value = read_worksheet_cell_value(
        source_file_path,
        MtReportConst.CHART_TITLE_ROW,
        MtReportConst.CHART_TITLE_COLUMN,
        data_only=True,
    )
    chart_title_raw = _stringify_cell(chart_title_value)
    chart_series_formula = _find_mt_mode_chart_series_formula(source_file_path)
    return chart_title_raw, chart_series_formula


def is_valid_mt_mode_chart_series_formula(formula: str) -> bool:
    """Проверяет, что в ячейке диаграммы задана формула SERIES/РЯД с ожидаемыми диапазонами."""
    if not formula.startswith("="):
        return False

    formula_normalized = formula.replace(" ", "")
    formula_upper = formula_normalized.upper()
    has_series_function = formula_upper.startswith("=SERIES(") or formula_normalized.startswith("=РЯД(")
    if not has_series_function:
        return False

    required_fragments = (
        MtReportConst.CHART_DATA_SHEET_NAME,
        MtReportConst.CHART_CATEGORY_RANGE,
        MtReportConst.CHART_VALUES_RANGE,
    )
    return all(fragment in formula for fragment in required_fragments)


def is_chart_title_valid(chart_title_raw: str, tu_description: str) -> bool:
    """Проверяет заголовок диаграммы: префикс режима МТ и название ТУ."""
    return MtReportConst.CHART_TITLE_PREFIX in chart_title_raw and tu_description in chart_title_raw


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
    *,
    source_file_path: Optional[Path] = None,
) -> MtModeReportParsed:
    """
    Разбирает лист xlsx-отчёта о режиме МТ: шапка, колонки, строки участков и суммарное время.

    В section_rows попадают только участки из expected_section_names (без учёта регистра).
    Метаданные диаграммы читаются из source_file_path отдельно (формула требует data_only=False).
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

    chart_title_raw = ""
    chart_series_formula = ""
    if source_file_path is not None:
        chart_title_raw, chart_series_formula = read_mt_mode_chart_metadata(source_file_path)

    return MtModeReportParsed(
        title_info=title_info,
        column_headers=headers,
        section_rows=section_rows,
        total_duration_seconds=total_duration_seconds,
        total_duration_raw=total_duration_raw,
        total_label_row_index=total_label_row_index,
        chart_title_raw=chart_title_raw,
        chart_series_formula=chart_series_formula,
    )


__all__ = [
    "MtModeReportParsed",
    "MtModeReportSectionRow",
    "is_chart_title_valid",
    "is_duration_cell_filled",
    "is_expected_dominant_mode_column",
    "is_valid_mt_mode_chart_series_formula",
    "parse_mt_mode_report_worksheet",
    "read_mt_mode_chart_metadata",
    "format_mt_mode_section_rows_for_allure",
    "sum_duration_columns_across_rows",
]
