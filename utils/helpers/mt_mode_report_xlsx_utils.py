"""
Утилиты для разбора xlsx-отчёта о режиме работы МТ.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
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
    _stringify_cell,
    build_column_cells,
    get_report_column_headers,
    parse_report_title,
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
    embedded_chart_formulas: List[str] = field(default_factory=list)


def _compact_chart_reference(reference: str) -> str:
    """Убирает пробелы и кавычки для сравнения ссылок вида 'Лист'!$A$1."""
    return reference.replace("'", "").replace(" ", "").upper()


def extract_embedded_chart_formulas(source_file_path: Path) -> List[str]:
    """
    Извлекает формулы ссылок (<c:f>) из XML встроенных диаграмм xlsx.

    Серия диаграммы в Excel хранится не в ячейке, а в xl/charts/chart*.xml.
    """
    if not source_file_path.exists():
        return []

    formulas: List[str] = []
    try:
        with zipfile.ZipFile(source_file_path, "r") as archive:
            chart_files = sorted(
                name
                for name in archive.namelist()
                if name.startswith("xl/charts/chart") and name.endswith(".xml")
            )
            for chart_file in chart_files:
                root = ET.fromstring(archive.read(chart_file))
                for element in root.iter():
                    tag_name = element.tag.rsplit("}", 1)[-1]
                    if tag_name == "f" and element.text:
                        formula = element.text.strip()
                        if formula:
                            formulas.append(formula)
    except Exception:
        return []

    return formulas


def _chart_reference_matches(reference: str, *, sheet_name: str, range_address: str) -> bool:
    compact_reference = _compact_chart_reference(reference)
    compact_sheet = _compact_chart_reference(sheet_name)
    compact_range = range_address.replace(" ", "").upper()
    return compact_sheet in compact_reference and compact_range in compact_reference


def is_valid_mt_mode_embedded_chart(chart_formulas: List[str]) -> bool:
    """
    Проверяет, что встроенная диаграмма ссылается на ожидаемые диапазоны листа данных.

    Эквивалент формулы =РЯД('Режим работы МТ'!$I$3,'Режим работы МТ'!$B$2:$D$2,'Режим работы МТ'!$I$5:$L$5,1),
    в OOXML ссылки хранятся отдельными элементами <c:f>.
    """
    if not chart_formulas:
        return False

    sheet_name = MtReportConst.CHART_DATA_SHEET_NAME
    has_category = any(
        _chart_reference_matches(formula, sheet_name=sheet_name, range_address=MtReportConst.CHART_CATEGORY_RANGE)
        for formula in chart_formulas
    )
    has_values = any(
        _chart_reference_matches(formula, sheet_name=sheet_name, range_address=MtReportConst.CHART_VALUES_RANGE)
        for formula in chart_formulas
    )
    return has_category and has_values


def format_embedded_chart_formulas_for_allure(chart_formulas: List[str]) -> str:
    """Форматирует ссылки встроенной диаграммы для отображения в Allure."""
    if not chart_formulas:
        return "встроенная диаграмма не найдена"
    return "; ".join(chart_formulas)


def read_mt_mode_chart_title(source_file_path: Path) -> str:
    """Читает заголовок диаграммы из ячейки F2."""
    chart_title_value = read_worksheet_cell_value(
        source_file_path,
        MtReportConst.CHART_TITLE_ROW,
        MtReportConst.CHART_TITLE_COLUMN,
        data_only=True,
    )
    return _stringify_cell(chart_title_value)


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
    Метаданные диаграммы читаются из source_file_path: заголовок из F2, серия - из XML диаграммы.
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
    embedded_chart_formulas: List[str] = []
    if source_file_path is not None:
        chart_title_raw = read_mt_mode_chart_title(source_file_path)
        embedded_chart_formulas = extract_embedded_chart_formulas(source_file_path)

    return MtModeReportParsed(
        title_info=title_info,
        column_headers=headers,
        section_rows=section_rows,
        total_duration_seconds=total_duration_seconds,
        total_duration_raw=total_duration_raw,
        total_label_row_index=total_label_row_index,
        chart_title_raw=chart_title_raw,
        embedded_chart_formulas=embedded_chart_formulas,
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
    "extract_embedded_chart_formulas",
    "format_embedded_chart_formulas_for_allure",
    "format_mt_mode_section_rows_for_allure",
    "is_chart_title_valid",
    "is_duration_cell_filled",
    "is_expected_dominant_mode_column",
    "is_valid_mt_mode_embedded_chart",
    "parse_mt_mode_report_worksheet",
    "read_mt_mode_chart_title",
    "sum_duration_columns_across_rows",
]
