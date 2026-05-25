"""
Утилиты для разбора xlsx-отчётов и проверки их формата.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import allure
from openpyxl import load_workbook
from openpyxl.worksheet.worksheet import Worksheet

from constants.test_constants import BaseTN3Constants as TestConst
from constants.test_constants import ExportReportConstants as ReportConst
from utils.helpers.ws_test_utils import extract_first_number


@dataclass
class ReportTitleInfo:
    """Разобранная шапка отчёта"""

    raw_title: str
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None


@dataclass
class LeakReportRow:
    """Разобранная строка данных по утечке"""

    row_index: int
    cells: Dict[str, str] = field(default_factory=dict)

    @property
    def datetime_value(self) -> Optional[datetime]:
        return parse_report_datetime(self.cells.get(ReportConst.COL_DATETIME))

    @property
    def object_value(self) -> str:
        return self.cells.get(ReportConst.COL_OBJECT, "")

    @property
    def lds_status(self) -> str:
        return self.cells.get(ReportConst.COL_LDS_STATUS, "")

    @property
    def masking_info(self) -> str:
        return self.cells.get(ReportConst.COL_MASK_INFO, "")

    @property
    def coordinate_meters(self) -> Optional[float]:
        coordinate_km = extract_first_number(self.cells.get(ReportConst.COL_COORDINATE))
        if coordinate_km is None:
            return None
        return coordinate_km * TestConst.KM_TO_METERS

    @property
    def leak_volume(self) -> Optional[float]:
        return extract_first_number(self.cells.get(ReportConst.COL_LEAK_VOLUME))

    @property
    def mt_mode(self) -> str:
        return self.cells.get(ReportConst.COL_MT_MODE, "")


def is_xlsx_file_bytes(file_bytes: Optional[bytes]) -> bool:
    """Проверяет zip-сигнатуру xlsx (PK\\x03\\x04)."""
    if not file_bytes:
        return False
    return file_bytes.startswith(ReportConst.ZIP_SIGNATURE)


def is_xlsx_extension(file_name: str) -> bool:
    """Проверяет расширение .xlsx без учёта регистра."""
    return file_name.lower().endswith(ReportConst.XLSX_EXTENSION)


def parse_report_datetime(value: object) -> Optional[datetime]:
    """Парсит дату/время из ячейки отчёта."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), ReportConst.REPORT_DATETIME_FORMAT)
        except ValueError:
            return None
    return None


def _stringify_cell(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime(ReportConst.REPORT_DATETIME_FORMAT)
    return str(value)


def parse_report_title(title_raw: object) -> ReportTitleInfo:
    """
    Парсит шапку отчёта с именованными группами period_start / period_end.
    """
    title_str = _stringify_cell(title_raw)
    match = re.search(ReportConst.REPORT_HEADER_PERIOD_PATTERN, title_str)
    if match is None:
        return ReportTitleInfo(raw_title=title_str)

    return ReportTitleInfo(
        raw_title=title_str,
        period_start=parse_report_datetime(match.group("period_start")),
        period_end=parse_report_datetime(match.group("period_end")),
    )


def load_report_worksheet(file_path: Path) -> Optional[Worksheet]:
    """Открывает первый лист xlsx. При ошибке возвращает None."""
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


def get_report_title_cell(worksheet: Worksheet) -> object:
    return worksheet.cell(row=ReportConst.REPORT_TITLE_ROW, column=1).value


def get_report_column_headers(worksheet: Worksheet) -> List[str]:
    """Возвращает непустые заголовки колонок из строки REPORT_COLUMN_HEADERS_ROW."""
    headers: List[str] = []
    column_index = 1
    while True:
        cell_value = worksheet.cell(row=ReportConst.REPORT_COLUMN_HEADERS_ROW, column=column_index).value
        if cell_value is None or not str(cell_value).strip():
            break
        headers.append(_stringify_cell(cell_value).strip())
        column_index += 1
    return headers


def build_column_cells(row_values: tuple, headers: List[str]) -> Dict[str, str]:
    """Собирает словарь {название колонки: значение ячейки} по строке данных."""
    return {
        header: _stringify_cell(row_values[column_index]) if column_index < len(row_values) else ""
        for column_index, header in enumerate(headers)
    }


def iter_report_data_rows(worksheet: Worksheet) -> List[LeakReportRow]:
    """
    Возвращает строки данных по утечкам, начиная с REPORT_DATA_FIRST_ROW.
    Пустые строки пропускаются.
    """
    headers = get_report_column_headers(worksheet)
    if not headers:
        return []

    rows: List[LeakReportRow] = []
    for excel_row_index, row_values in enumerate(
        worksheet.iter_rows(
            min_row=ReportConst.REPORT_DATA_FIRST_ROW,
            max_col=len(headers),
            values_only=True,
        ),
        start=ReportConst.REPORT_DATA_FIRST_ROW,
    ):
        if not any(cell is not None and str(cell).strip() for cell in row_values):
            continue
        rows.append(
            LeakReportRow(
                row_index=excel_row_index,
                cells=build_column_cells(row_values, headers),
            )
        )
    return rows


def find_row_with_object(rows: List[LeakReportRow], object_substring: str) -> Optional[LeakReportRow]:
    """Ищет первую строку, где колонка «Объект» содержит подстроку без учёта регистра"""
    substring_lower = object_substring.lower()
    for row in rows:
        if substring_lower in row.object_value.lower():
            return row
    return None


def save_report_bytes_to_temp_file(file_bytes: bytes) -> Optional[Path]:
    """Сохраняет байты отчёта во временный xlsx-файл. При ошибке возвращает None."""
    import tempfile

    try:
        with tempfile.NamedTemporaryFile(
            suffix=ReportConst.XLSX_EXTENSION,
            prefix="leaks_report_",
            delete=False,
        ) as temp_file:
            temp_file.write(file_bytes)
            return Path(temp_file.name)
    except OSError:
        return None


def attach_report_file_to_allure(file_path: Path, file_name: str) -> None:
    """Прикладывает xlsx к Allure при падении теста"""
    try:
        xlsx_type = allure.attachment_type.XLSX
    except AttributeError:
        xlsx_type = None

    if xlsx_type is not None:
        allure.attach.file(
            str(file_path),
            name=file_name,
            attachment_type=xlsx_type,
            extension="xlsx",
        )
        return

    try:
        with file_path.open("rb") as raw_file:
            allure.attach(raw_file.read(), name=file_name, extension="xlsx")
    except OSError:
        pass
