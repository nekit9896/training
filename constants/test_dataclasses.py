"""
Dataclasses для конфигурирования тестов СОУ.

Этот модуль содержит структуры данных для параметризованного тестирования.
Все данные должны быть явно указаны при создании конфигурации.
"""

from dataclasses import dataclass
from typing import Optional

from constants.test_enums import (ConfirmationStatus, LdsStatus, ReservedType,
                                  StationaryStatus)


@dataclass
class NeighborArea:
    """
    Соседний диагностический участок.

    Attributes:
        id: ID диагностического участка
        expected_status: Ожидаемый статус СОУ во время утечки
    """

    id: int
    expected_status: LdsStatus


@dataclass
class LeakConfig:
    """
    Конфигурация параметров утечки.

    Указывайте None явно для опциональных полей.

    Attributes:
        coordinate_m: Координата утечки в метрах
        volume_m3: Объем утечки в м³/час
        time_tolerance_s: Допустимая погрешность времени обнаружения в секундах
        diagnostic_area_id: ID диагностического участка с утечкой
        linear_part_id: ID линейного участка
        expected_lds_status: Ожидаемый статус СОУ на ДУ с утечкой
        expected_stationary_status: Ожидаемый режим ТУ при утечке
        neighbor_areas: Список соседних ДУ с ожидаемыми статусами
        diagnostic_area_name: Название ДУ (для AllLeaksContent)
        control_site_id: ID контролируемого участка (для TuLeaksInfo)
        expected_confirmation_status: Ожидаемый статус подтверждения
        expected_type: Ожидаемый тип события
    """

    coordinate_m: float
    volume_m3: float
    time_tolerance_s: int
    diagnostic_area_id: int
    linear_part_id: int
    expected_lds_status: LdsStatus
    expected_stationary_status: StationaryStatus
    neighbor_areas: list[NeighborArea]
    diagnostic_area_name: Optional[str]
    control_site_id: Optional[int]
    expected_confirmation_status: Optional[ConfirmationStatus]
    expected_type: Optional[ReservedType]


@dataclass
class TestOffsets:
    """
    Тайминги запуска тестов относительно старта имитатора (в минутах).

    Установите None для отключения теста.

    Для тестов с двумя утечками используйте поля *_leak_2.
    """

    basic_info: Optional[float]
    journal_info: Optional[float]
    lds_status_initialization: Optional[float]
    main_page_info: Optional[float]
    mask_signal_msg: Optional[float]
    lds_status_initialization_out: Optional[float]
    all_leaks_info: Optional[float]
    tu_leaks_info: Optional[float]
    lds_status_during_leak: Optional[float]
    acknowledge_leak_info: Optional[float]
    output_signals: Optional[float]
    main_page_info_unstationary: Optional[float]
    # --- Тесты для второй утечки (Select_19_20) ---
    all_leaks_info_leak_2: Optional[float]
    tu_leaks_info_leak_2: Optional[float]
    output_signals_leak_2: Optional[float]


@dataclass
class TestCaseIds:
    """
    ID тест-кейсов в TestOps для каждого теста.
    """

    basic_info: str
    journal_info: str
    lds_status_initialization: str
    main_page_info: str
    mask_signal_msg: str
    lds_status_initialization_out: str
    all_leaks_info: str
    tu_leaks_info: str
    lds_status_during_leak: str
    acknowledge_leak_info: str
    output_signals: str
    main_page_info_unstationary: str
    # --- Тест-кейсы для второй утечки ---
    all_leaks_info_leak_2: str
    tu_leaks_info_leak_2: str
    output_signals_leak_2: str


@dataclass
class TestDataConfig:
    """
    Полная конфигурация тестового набора данных.

    Attributes:
        suite_name: Уникальное имя набора данных
        suite_data_id: ID набора данных в TestOps
        arch_name: Имя архива с данными
        tu_id: ID технологического участка
        tu_name: Название технологического участка
        leak: Конфигурация основной утечки
        leak_2: Конфигурация второй утечки (None если одна утечка)
        offsets: Тайминги запуска тестов
        test_case_ids: ID тест-кейсов в TestOps для данного набора
        expected_stationary: Ожидаемый режим при проверке стационара
        distance_tolerance_m: Допустимая погрешность координаты (м)
        volume_tolerance_ratio: Относительная погрешность объема (0.2 = 20%)
        precision: Точность округления координат
        enabled: Включен ли набор данных для запуска
    """

    # --- Идентификация набора ---
    suite_name: str
    suite_data_id: int
    arch_name: str

    # --- Параметры ТУ ---
    tu_id: int
    tu_name: str

    # --- Конфигурация утечки ---
    leak: LeakConfig
    leak_2: Optional[LeakConfig]

    # --- Тайминги и кейсы ---
    offsets: TestOffsets
    test_case_ids: TestCaseIds

    # --- Ожидаемые значения ---
    expected_stationary: StationaryStatus

    # --- Погрешности ---
    distance_tolerance_m: int
    volume_tolerance_ratio: float
    precision: int

    # --- Флаг включения ---
    enabled: bool

    @property
    def volume_tolerance_m3(self) -> float:
        """Абсолютная погрешность объема в м³"""
        return self.leak.volume_m3 * self.volume_tolerance_ratio

    @property
    def output_time_tolerance_s(self) -> int:
        """Погрешность времени для выходных сигналов (+ 120 сек задержки)"""
        return self.leak.time_tolerance_s + 120

    @property
    def volume_tolerance_m3_leak_2(self) -> float:
        """Абсолютная погрешность объема для второй утечки в м³"""
        if self.leak_2:
            return self.leak_2.volume_m3 * self.volume_tolerance_ratio
        return 0.0

    @property
    def output_time_tolerance_s_leak_2(self) -> int:
        """Погрешность времени для выходных сигналов второй утечки"""
        if self.leak_2:
            return self.leak_2.time_tolerance_s + 120
        return 0
