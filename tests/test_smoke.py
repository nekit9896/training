"""
Единый тестовый модуль для наборов данных с одной утечкой.

Использует параметризацию pytest для запуска одинаковых тестов
на разных наборах данных без дублирования кода.

Наборы данных обнаруживаются автоматически из test_config/datasets/.
Для добавления нового набора достаточно создать файл конфигурации.

Запуск:
- Все тесты: pytest tests/test_smoke.py
- Один набор: pytest tests/test_smoke.py -k select_17
- Конкретный тест: pytest tests/test_smoke.py -k "test_basic_info and select_17"
"""

import allure
import pytest

from test_config.datasets import SINGLE_LEAK_CONFIGS
from test_config.models import SuiteConfig
from test_scenarios import scenarios


def get_suite_markers(config: SuiteConfig):
    """Возвращает маркеры для тестового набора (на уровне набора данных)"""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
    ]


# ===== Автоматическое построение параметризации из обнаруженных конфигов =====
PARAMETRIZED_CONFIGS = [
    pytest.param(config, id=config.suite_name, marks=get_suite_markers(config))
    for config in SINGLE_LEAK_CONFIGS
]


# ===== ПАРАМЕТРИЗОВАННЫЕ ТЕСТЫ =====

@pytest.mark.parametrize("config", PARAMETRIZED_CONFIGS)
class TestSingleLeakSuite:
    """
    Параметризованные тесты для наборов данных с одной утечкой.
    
    Каждый тест запускается для всех наборов.
    
    Маркеры offset и test_case_id добавляются автоматически в pytest_collection_modifyitems
    на основе конфигурации из test_config/datasets/.
    """
    
    @pytest.mark.asyncio
    async def test_basic_info(self, ws_client, config: SuiteConfig):
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        test_config = config.basic_info_test
        
        # Allure-атрибуты (маркеры offset/test_case_id добавлены в pytest_collection_modifyitems)
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        
        await scenarios.basic_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_journal_info(self, ws_client, config: SuiteConfig):
        """[MessagesInfo] Проверка наличия сообщений в журнале"""
        test_config = config.journal_info_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.journal_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка режима работы СОУ: Инициализация"""
        test_config = config.lds_status_initialization_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_initialization(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_main_page_info(self, ws_client, config: SuiteConfig):
        """[MainPageInfo] Проверка установки стационара/остановленной перекачки"""
        test_config = config.main_page_info_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.main_page_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_mask_signal_msg(self, ws_client, config: SuiteConfig):
        """[MaskSignal] Проверка маскирования датчиков"""
        test_config = config.mask_signal_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.mask_signal_msg(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization_out(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка выхода СОУ из Инициализации"""
        test_config = config.lds_status_initialization_out_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_initialization_out(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_leaks_content(self, ws_client, config: SuiteConfig, imitator_start_time):
        """[LeaksContent] Проверка утечки через LeaksContent"""
        test_config = config.leak.leaks_content_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.leaks_content(ws_client, config, config.leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_all_leaks_info(self, ws_client, config: SuiteConfig, imitator_start_time):
        """[AllLeaksInfo] Проверка начала утечки"""
        test_config = config.leak.all_leaks_info_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.all_leaks_info(ws_client, config, config.leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_tu_leaks_info(self, ws_client, config: SuiteConfig, imitator_start_time):
        """[TuLeaksInfo] Проверка утечки"""
        test_config = config.leak.tu_leaks_info_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.tu_leaks_info(ws_client, config, config.leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_lds_status_during_leak(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка режима работы СОУ во время утечки"""
        test_config = config.lds_status_during_leak_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_during_leak(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_acknowledge_leak_info(self, ws_client, config: SuiteConfig):
        """[AcknowledgeLeak] Проверка квитирования утечки"""
        test_config = config.leak.acknowledge_leak_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.acknowledge_leak_info(ws_client, config, config.leak)
    
    @pytest.mark.asyncio
    async def test_output_signals(self, ws_client, config: SuiteConfig, imitator_start_time):
        """[OutputSignalsInfo] Проверка данных об утечке в выходных сигналах"""
        test_config = config.leak.output_signals_test
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.output_signals(ws_client, config, config.leak, imitator_start_time)
