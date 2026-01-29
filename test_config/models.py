"""
Датаклассы для конфигурации тестовых наборов.

Архитектура:
- SuiteConfig - главный конфиг набора, содержит всё для запуска тестов
- LeakTestConfig - конфиг утечки с параметрами и тест-кейсами
- CaseMarkers - маркеры для allure и pytest

Принцип: один файл конфига = один набор данных.
"""

from dataclasses import dataclass, field
from typing import Optional

from constants.enums import TU, LdsStatus, ReservedType, StationaryStatus
import constants.test_constants as test_const


@dataclass
class CaseMarkers:
    """
    Маркеры тест-кейса для pytest и allure.

    """
    
    test_case_id: str
    offset: float
    title: str
    tag: str
    description: Optional[str] = None


@dataclass
class DiagnosticAreaStatusConfig:
    """
    Конфигурация ожидаемых статусов СОУ для диагностического участка.
    Используется в тесте lds_status_during_leak.
    """
    
    diagnostic_area_id: int
    expected_lds_status: int
    
    # Соседние ДУ и их статусы
    in_neighbor_id: Optional[int] = None
    in_neighbor_status: Optional[int] = None
    out_neighbor_id: Optional[int] = None
    out_neighbor_status: Optional[int] = None
    out_neighbor_2_id: Optional[int] = None
    out_neighbor_2_status: Optional[int] = None


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
    diagnostic_area_name: Optional[str] = None
    diagnostic_area_id: Optional[int] = None
    control_site_id: Optional[int] = None
    linear_part_id: Optional[int] = None
    
    # ===== Параметры утечки =====
    coordinate_meters: float = None
    volume_m3: float = None
    
    # ===== Временные интервалы (секунды) =====
    leak_start_interval_seconds: int = test_const.LEAK_START_INTERVAL
    allowed_time_diff_seconds: int = 0  # Допустимое время обнаружения
    output_test_delay_seconds: int = test_const.OUTPUT_TEST_DELAY
    
    # ===== Ожидаемые статусы =====
    expected_lds_status: int = LdsStatus.SERVICEABLE.value
    expected_stationary_status: int = StationaryStatus.UNSTATIONARY.value
    expected_type: int = ReservedType.UNSTATIONARY_FLOW.value  # Ожидаемый тип источника события (алгоритм)
    
    # ===== Тест-кейсы для этой утечки =====
    leaks_content_test: Optional[CaseMarkers] = None
    all_leaks_info_test: Optional[CaseMarkers] = None
    tu_leaks_info_test: Optional[CaseMarkers] = None
    leak_info_in_journal: Optional[CaseMarkers] = None
    acknowledge_leak_test: Optional[CaseMarkers] = None
    output_signals_test: Optional[CaseMarkers] = None
    
    @property
    def allowed_volume_m3(self) -> float:
        """Допустимая погрешность объёма"""
        return self.volume_m3 * test_const.ALLOWED_VOLUME_DIFF
    
    @property
    def output_allowed_time_diff_seconds(self) -> int:
        """Допустимое время для теста выходных сигналов"""
        return self.allowed_time_diff_seconds + self.output_test_delay_seconds


@dataclass
class SuiteConfig:
    """
    Полная конфигурация тестового набора.
    
    Один конфиг = один набор данных = один файл в test_config/datasets/
    
    Структура:
    1. Метаданные набора (имя, id, архив)
    2. Технологический участок (из enum TU)
    3. Базовые тесты с маркерами
    4. Конфигурация статусов СОУ во время утечки
    5. Конфигурации утечек (LeakTestConfig)
    """
    
    # ===== Метаданные набора =====
    suite_name: str
    suite_data_id: int
    archive_name: str = ""
    
    # ===== Технологический участок =====
    technological_unit: TU = TU.TIKHORETSK_NOVOROSSIYSK_3
    
    # ===== Ожидаемый статус стационара (для main_page_info) =====
    expected_stationary_status: int = StationaryStatus.STATIONARY.value
    
    # ===== Базовые тесты =====
    basic_info_test: Optional[CaseMarkers] = None
    journal_info_test: Optional[CaseMarkers] = None
    lds_status_initialization_test: Optional[CaseMarkers] = None
    main_page_info_test: Optional[CaseMarkers] = None
    mask_signal_test: Optional[CaseMarkers] = None
    lds_status_initialization_out_test: Optional[CaseMarkers] = None
    lds_status_during_leak_test: Optional[CaseMarkers] = None
    
    # ===== Конфигурация статусов СОУ во время утечки =====
    lds_status_during_leak_config: Optional[DiagnosticAreaStatusConfig] = None
    
    # ===== Конфигурации утечек =====
    # Для наборов с одной утечкой
    leak: Optional[LeakTestConfig] = None
    
    # Для наборов с несколькими утечками (select_19_20)
    leaks: list[LeakTestConfig] = field(default_factory=list)
    
    # ===== Дополнительные тесты для двух утечек =====
    main_page_info_unstationary_test: Optional[CaseMarkers] = None
    
    # ===== Общие константы (можно переопределить) =====
    allowed_distance_diff_meters: int = test_const.ALLOWED_DISTANCE_DIFF_METERS
    precision: int = test_const.PRECISION
    basic_message_timeout: float = test_const.BASIC_MESSAGE_TIMEOUT
    
    # ===== Свойства для удобства =====
    @property
    def tu_id(self) -> int:
        """ID технологического участка"""
        return self.technological_unit.id
    
    @property
    def tu_name(self) -> str:
        """Название технологического участка"""
        return self.technological_unit.description
    
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
        return test_const.ALLOWED_VOLUME_DIFF
