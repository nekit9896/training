"""
Утилиты для разбора xlsx-отчёта о режиме работы МТ.
"""

from __future__ import annotations

from typing import Dict, List

from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import ExportMtModeReportConstants as MtReportConst
from utils.helpers import mode_duration_report_xlsx_utils as mode_duration_utils
from utils.helpers.report_xlsx_utils import sum_duration_columns_across_rows

_MT_LAYOUT = mode_duration_utils.ModeDurationReportLayout.from_constants(MtReportConst)

MtModeReportSectionRow = mode_duration_utils.ModeDurationReportSectionRow
MtModeReportParsed = mode_duration_utils.ModeDurationReportParsed

format_duration_seconds = mode_duration_utils.format_duration_seconds
format_mt_mode_section_rows_for_allure = mode_duration_utils.format_mode_duration_section_rows_for_allure
is_duration_cell_filled = mode_duration_utils.is_duration_cell_filled
parse_duration_seconds = mode_duration_utils.parse_duration_seconds


def is_expected_dominant_mode_column(mode_totals: Dict[str, int], expected_column: str) -> bool:
    """
    Проверяет, что суммарное время ожидаемого режима строго максимально и больше нуля.
    """
    expected_total = mode_totals.get(expected_column, 0)
    if expected_total <= 0:
        return False
    return expected_total == max(mode_totals.values())


def parse_mt_mode_report_worksheet(
    worksheet: Worksheet,
    expected_section_names: List[str],
) -> MtModeReportParsed:
    """Разбирает лист xlsx-отчёта о режиме МТ."""
    return mode_duration_utils.parse_mode_duration_report_worksheet(
        worksheet,
        expected_section_names,
        _MT_LAYOUT,
    )


__all__ = [
    "MtModeReportParsed",
    "MtModeReportSectionRow",
    "format_mt_mode_section_rows_for_allure",
    "is_duration_cell_filled",
    "is_expected_dominant_mode_column",
    "parse_mt_mode_report_worksheet",
    "sum_duration_columns_across_rows",
]
