"""
Единый тестовый модуль для всех наборов данных (single-leak и multi-leak).

Архитектура параметризации:
- SUITE_PARAMS: тесты уровня набора (один раз на набор данных)
- LEAK_PARAMS: тесты уровня утечки (один раз на каждую утечку)

Для добавления нового набора:
1. Создать файл в test_config/datasets/
2. Тесты подхватятся автоматически

Запуск:
- Все тесты: pytest tests/test_smoke.py
- Один набор: pytest tests/test_smoke.py --suites=select_4
- Несколько наборов: pytest tests/test_smoke.py --suites=select_4,select_19_20
"""

import datetime
from typing import Any, List, Optional

import allure
import pytest

from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_CONFIGS
from test_config.models_for_tests import CaseMarkers, LeakTestConfig, SuiteConfig
from test_scenarios import scenarios

# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====


def _get_suite_markers(config: SuiteConfig) -> List[pytest.MarkDecorator]:
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
    ]


def _generate_suite_params() -> List[Any]:
    """
    Генерирует параметры для тестов уровня набора данных.
    Один параметр на каждый config.
    """
    return [pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config)) for config in ALL_CONFIGS]


def _generate_leak_params() -> List[Any]:
    """
    Генерирует параметры для тестов уровня утечки.

    Для single-leak конфигов: один параметр (config, leak, 1)
    Для multi-leak конфигов: N параметров (config, leak_n, n) для каждой утечки
    """
    params: List[Any] = []

    for config in ALL_CONFIGS:
        # Собираем все утечки из конфига
        if config.has_multiple_leaks:
            leaks = config.leaks
        elif config.leak:
            leaks = [config.leak]
        else:
            continue  # Нет утечек в конфиге

        # Создаём параметр для каждой утечки
        for index, leak in enumerate(leaks):
            leak_number = index + 1

            # ID для Allure/pytest: select_4 или select_19_20_leak_1
            if len(leaks) > 1:
                param_id = f"{config.suite_name}_leak_{leak_number}"
            else:
                param_id = config.suite_name

            params.append(
                pytest.param(
                    config,
                    leak,
                    leak_number,
                    id=param_id,
                    marks=_get_suite_markers(config),
                )
            )

    return params


# ===== ПАРАМЕТРЫ ДЛЯ ТЕСТОВ =====
SUITE_PARAMS: List[Any] = _generate_suite_params()
LEAK_PARAMS: List[Any] = _generate_leak_params()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def _apply_allure_markers(test_config: CaseMarkers, tag: str, title: str, description: Optional[str] = None) -> None:
    """Применяет allure-маркеры из конфига теста."""
    if not test_config:
        msg = "Не заполнена конфигурация теста: запуск остановлен"
        allure.attach(msg, name="Ошибка подготовки тестрана", attachment_type=allure.attachment_type.TEXT)
        pytest.exit(msg)
    allure.dynamic.tag(tag)
    allure.dynamic.tag("SMOKE")
    allure.dynamic.title(title)
    if description:
        allure.dynamic.description(description)


# ===== ТЕСТЫ УРОВНЯ НАБОРА =====
# Запускаются один раз для каждого config


@pytest.mark.parametrize("config", SUITE_PARAMS)
class TestSuiteScenarios:
    """
    Тесты уровня набора данных.
    Запускаются один раз для каждого конфига.
    """

    @pytest.mark.asyncio
    @pytest.mark.critical_stop
    async def test_basic_info(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.basic_info_test, tag, title)
        await scenarios.basic_info(ws_client, config)

    @pytest.mark.asyncio
    async def test_journal_info(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[MessagesInfo] Проверка наличия сообщений в журнале"""
        tag = "MessagesInfo"
        title = f"[{tag}] Проверка наличия сообщений в журнале. ЭФ: Журнал.Реальное время"
        description = "Проверка наличия сообщений в журнале.\n" "Синхронный запрос типа: MessagesInfo"
        _apply_allure_markers(config.journal_info_test, tag, title, description)
        await scenarios.journal_info(ws_client)

    @pytest.mark.asyncio
    async def test_lds_status_initialization(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[CommonScheme] Проверка режима работы СОУ: Инициализация"""
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация'. ЭФ: Схема"
        description = (
            f"Проверка режима работы СОУ на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки : {config.lds_status_initialization_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Инициализация"
        )
        _apply_allure_markers(config.lds_status_initialization_test, tag, title, description)
        await scenarios.lds_status_initialization(ws_client, config)

    @pytest.mark.asyncio
    async def test_main_page_info(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[MainPageInfo] Проверка установки режима МТ"""
        tag = "MainPageInfo"
        title = f"[{tag}] Проверка установки режима работы МТ: стационарный. ЭФ: Главная страница.Контент таблица по ТУ"
        description = (
            f"Проверка установки режима работы МТ: стационарный на данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.main_page_info_test.offset} мин.\n"
            "Подписка на сообщения типа: MainPageInfo\n"
            "Ожидаемый режим работы МТ: Стационарный"
        )
        _apply_allure_markers(config.main_page_info_test, tag, title, description)
        await scenarios.main_page_info(ws_client, config)


    @pytest.mark.asyncio
    async def test_main_page_info_signals(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[MainPageSignalsInfo] Проверка счетчиков состояния сигналов"""
        tag = "MainPageSignalsInfo"
        title = f"[{tag}] Проверка счетчиков состояния сигналов. ЭФ: Главная страница.Контент таблица по ТУ"
        description = (
            f"Проверка счетчиков состояния сигналов на данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.main_page_info_signals_test.offset} мин.\n"
            "Подписка на сообщения типа: MainPageSignalsInfo\n"
        )
        _apply_allure_markers(config.main_page_info_signals_test, tag, title, description)
        await scenarios.main_page_info_signals(ws_client, config)

        
    @pytest.mark.asyncio
    async def test_mask_signal_msg(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[MaskSignal] Проверка маскирования датчиков"""
        tag = "MaskSignal"
        title = f"[{tag}] проверка маскирования датчиков. ЭФ: Схема"
        description = (
            f"Проверка работы маскирования и снятия маскирования  на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.mask_signal_test.offset} мин.\n"
            "Синхронные запросы типа: GetInputSignalsRequest, MaskSignalRequest, UnmaskSignalRequest\n"
            "Подписка на сообщения типа: InputSignalsContent\n"
            "Проверки:\n"
            "Статус-код ответа на синхронный запрос маскирования.\n"
            "Значение в поле isMasked сигнала во входных сигналах после маскирования.\n"
            "Статус-код ответа на синхронный запрос снятия маскирования.\n"
            "Значение в поле isMasked сигнала во входных сигналах после снятия маскирования.\n"
            "Примечание: что бы не повлиять на проверки утечек, тест на маскирование выполняется во время инициализации"
        )
        _apply_allure_markers(config.mask_signal_test, tag, title, description)
        await scenarios.mask_signal_msg(ws_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_initialization_out(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[CommonScheme] Проверка выхода СОУ из Инициализации"""
        tag = "CommonScheme"
        title = f"[{tag}] Проверка выхода СОУ из Инициализации. ЭФ: Схема"
        description = (
            f"Проверка выхода СОУ из Инициализации на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.lds_status_initialization_out_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: не Инициализация"
        )
        _apply_allure_markers(config.lds_status_initialization_out_test, tag, title, description)
        await scenarios.lds_status_initialization_out(ws_client, config)

    @pytest.mark.asyncio
    async def test_main_page_info_unstationary(self, ws_client: WebSocketClient, config: SuiteConfig) -> None:
        """[MainPageInfo] Проверка установки режима Нестационарный (для multi-leak)"""
        tag = "MainPageInfo"
        title = (
            f"[{tag}] Проверка установки режима работы МТ: нестационарный. ЭФ: Главная страница. Контент таблица по ТУ"
        )
        description = (
            f"Проверка установки режима работы МТ: нестационарный на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {config.main_page_info_unstationary_test.offset} мин.\n"
            "Подписка на сообщения типа: MainPageInfo\n"
            "Ожидаемый режим работы МТ: Нестационарный"
        )
        _apply_allure_markers(config.main_page_info_unstationary_test, tag, title, description)
        await scenarios.main_page_info_unstationary(ws_client, config)

# ===== ТЕСТЫ УРОВНЯ УТЕЧКИ =====
# Запускаются для каждой утечки в конфиге


@pytest.mark.parametrize("config, leak, leak_number", LEAK_PARAMS)
class TestLeakScenarios:
    """
    Тесты уровня утечки.
    Для single-leak: запускаются один раз.
    Для multi-leak: запускаются для каждой утечки отдельно.
    """

    @pytest.mark.asyncio
    async def test_all_leaks_info(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[AllLeaksInfo] Проверка утечки в пуше"""
        tag = "AllLeaksInfo"
        title = f"[{tag}] Проверка сообщения об утечке. ЭФ: Пуш-сообщение об утечке на всех ЭФ"
        description = (
            f"Проверка пуш-сообщения об утечке на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.all_leaks_info_test.offset} мин.\n"
            "Подписка на сообщения типа: AllLeaksInfo\n"
            f"Допустимое время обнаружения {leak.allowed_time_diff_minutes} мин. с момента начала утечки, "
            f"т к для данных {config.suite_name} интенсивность утечки {leak.leak_rate_percentages}%.\n"
            "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
        )

        _apply_allure_markers(leak.all_leaks_info_test, tag, title, description)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.all_leaks_info(ws_client, config, leak, imitator_start_time)

    @pytest.mark.asyncio
    async def test_lds_status_during_leak(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
    ) -> None:
        """[CommonScheme] Проверка режима работы СОУ во время утечки"""
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ во время утечки. ЭФ: Схема"
        description = (
            f"Проверка режима работы СОУ во время утечки на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.lds_status_during_leak_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Примечание: проверка режимов СОУ во время утечки должна выполняться раньше теста на квитирование\n"
            "В рамках данного теста проверяется режим СОУ на ДУ с утечкой и на соседних ДУ"
        )
        _apply_allure_markers(leak.lds_status_during_leak_test, tag, title, description)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.lds_status_during_leak(ws_client, config, leak)
        
    @pytest.mark.asyncio
    async def test_leaks_content(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[LeaksContent] Проверка сообщения об утечке в таблице КГ"""
        tag = "LeaksContent"
        title = f"[{tag}] Проверка сообщения об утечке. ЭФ: КГ.Табличное представление"
        description = (
            f"Проверка сообщения об утечке в таблице КГ на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.leaks_content_test.offset} мин.\n"
            "Подписка на сообщения типа: LeaksContent\n"
            f"Допустимое время обнаружения {leak.allowed_time_diff_minutes} мин. с момента начала утечки, "
            f"т к для данных {config.suite_name} интенсивность утечки {leak.leak_rate_percentages}%.\n"
            "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
        )
        _apply_allure_markers(leak.leaks_content_test, tag, title, description)
        # Добавляем номер утечки в title для multi-leak
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.leaks_content(ws_client, config, leak, imitator_start_time)

    @pytest.mark.asyncio
    async def test_leaks_content_end(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[LeaksContent] Проверка сообщения об утечке в таблице КГ"""
        tag = "LeaksContent"
        title = f"[{tag}] Проверка сообщения о завершенной утечке. ЭФ: КГ.Табличное представление"
        description = (
            f"Проверка сообщения об утечке в таблице КГ на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.leaks_content_test.offset} мин.\n"
            "Подписка на сообщения типа: LeaksContent\n"
        )
        _apply_allure_markers(leak.leaks_content_test, tag, title, description)
        # Добавляем номер утечки в title для multi-leak
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.leaks_content(ws_client, config, leak, imitator_start_time)

    @pytest.mark.asyncio
    async def test_leak_info_in_journal(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[MessagesInfo] Проверка сообщения об утечке в журнале"""
        tag = "MessagesInfo"
        title = f"[{tag}] Проверка сообщения об утечке в журнале. ЭФ: Журнал.Реальное время"
        description = (
            f"Проверка сообщения об утечке в журнале на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.leak_info_in_journal.offset} мин.\n"
            "Синхронный запрос типа: MessagesInfo\n"
            f"Допустимое время обнаружения {leak.allowed_time_diff_minutes} мин. с момента начала утечки, "
            f"т к для данных {config.suite_name} интенсивность утечки {leak.leak_rate_percentages}%.\n"
            "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
        )
        _apply_allure_markers(leak.leaks_content_test, tag, title, description)
        # Добавляем номер утечки в title для multi-leak
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.leak_info_in_journal(ws_client, config, leak, imitator_start_time)

    @pytest.mark.asyncio
    async def test_tu_leaks_info(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[TuLeaksInfo] Проверка утечки на ТУ"""
        tag = "TuLeaksInfo"
        title = f"[{tag}] Проверка сообщения об утечке. Сообщения на ЭФ: Схема, Минисхема, Гидроуклон"
        description = (
            f"Проверка сообщения об утечке на схемах и гидроуклоне на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {leak.diagnostic_area_name}\n"
            f"Время проведения проверки: {leak.tu_leaks_info_test.offset} мин.\n"
            "Подписка на сообщения типа: TuLeaksInfo\n"
            f"Допустимое время обнаружения {leak.allowed_time_diff_minutes} мин. с момента начала утечки, "
            f"т к для данных {config.suite_name} интенсивность утечки {leak.leak_rate_percentages}%.\n"
            "Примечание: тесты сообщений об утечке должны выполняться раньше теста на квитирование"
        )
        _apply_allure_markers(leak.tu_leaks_info_test, tag, title, description)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.tu_leaks_info(ws_client, config, leak, imitator_start_time)

    @pytest.mark.asyncio
    async def test_acknowledge_leak_info(
        self, ws_client: WebSocketClient, config: SuiteConfig, leak: LeakTestConfig, leak_number: int
    ) -> None:
        """[AcknowledgeLeak] Проверка квитирования утечки"""
        tag = "AcknowledgeLeak"
        title = f"[{tag}] Проверка квитирования утечки. Отсутствие Пуш-сообщений об утечке на всех ЭФ"
        description = (
            "Проверка квитирования утечки на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.acknowledge_leak_test.offset} мин.\n"
            "Синхронный запрос типа: AcknowledgeLeak\n"
            "Подписка на сообщения типа: TuLeaksInfo, AllLeaksInfo\n"
            "Проверки:\n"
            "Статус-код ответа на синхронный запрос о квитировании,\n"
            "Отсутствие пуш-сообщений об утечках после квитирования"
        )
        _apply_allure_markers(leak.acknowledge_leak_test, tag, title, description)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.acknowledge_leak_info(ws_client, config, leak)

    @pytest.mark.asyncio
    async def test_output_signals(
        self,
        ws_client: WebSocketClient,
        config: SuiteConfig,
        leak: LeakTestConfig,
        leak_number: int,
        imitator_start_time: datetime,
    ) -> None:
        """[OutputSignalsInfo] Проверка данных об утечке в выходных сигналах"""
        tag = "OutputSignalsInfo"
        title = (
            f"[{tag}] Проверка наличия данных об утечке в выходных сигналах. ЭФ: Диагностика сигналов.Выходные "
            f"сигналы"
        )
        description = (
            f"Проверка наличия данных об утечке в выходных сигналах на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки: {leak.output_signals_test.offset} мин.\n"
            "Синхронный запрос типа: GetOutputSignals\n"
            "Подписка на сообщения типа: SubscribeOutputSignals\n"
            f"Допустимое время обнаружения {leak.allowed_time_diff_minutes} мин. с момента начала утечки, "
            f"т к для данных {config.suite_name} интенсивность утечки {leak.leak_rate_percentages}%.\n"
            "Примечание: "
            "В offset указано время проверок сообщения выходных сигналов + 1 минута "
            "для корректной отработки проверок.\n"
            "Данный тест так же проверяет квитирование, offset выставлять после запуска теста на квитирование утечки"
        )
        _apply_allure_markers(leak.output_signals_test, tag, title, description)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{title} (утечка #{leak_number})")
        await scenarios.output_signals(ws_client, config, leak, imitator_start_time)
