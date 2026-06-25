"""
Утилиты для разбора xlsx-отчёта о режиме работы СОУ.
"""

from __future__ import annotations

from typing import List

from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import ExportLdsStatusReportConstants as LdsReportConst
from utils.helpers import mode_duration_report_xlsx_utils as mode_duration_utils

_LDS_LAYOUT = mode_duration_utils.ModeDurationReportLayout.from_constants(LdsReportConst)

# Публичные алиасы типов отчёта СОУ (общая реализация — в mode_duration_report_xlsx_utils).
LdsStatusReportSectionRow = mode_duration_utils.ModeDurationReportSectionRow
LdsStatusReportParsed = mode_duration_utils.ModeDurationReportParsed

find_total_work_duration = mode_duration_utils.find_total_work_duration
format_duration_seconds = mode_duration_utils.format_duration_seconds
format_section_rows_for_allure = mode_duration_utils.format_mode_duration_section_rows_for_allure
is_duration_cell_filled = mode_duration_utils.is_duration_cell_filled
parse_duration_seconds = mode_duration_utils.parse_duration_seconds


def parse_lds_status_report_worksheet(
    worksheet: Worksheet,
    expected_section_names: List[str],
) -> LdsStatusReportParsed:
    """Разбирает лист xlsx-отчёта о режиме СОУ."""
    return mode_duration_utils.parse_mode_duration_report_worksheet(
        worksheet,
        expected_section_names,
        _LDS_LAYOUT,
    )


__all__ = [
    "LdsStatusReportParsed",
    "LdsStatusReportSectionRow",
    "find_total_work_duration",
    "format_duration_seconds",
    "format_section_rows_for_allure",
    "is_duration_cell_filled",
    "parse_duration_seconds",
    "parse_lds_status_report_worksheet",
]
