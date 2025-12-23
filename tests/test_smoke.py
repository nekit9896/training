"""
Единый тестовый модуль для наборов данных с одной утечкой.

Использует параметризацию pytest для запуска одинаковых тестов
на разных наборах данных без дублирования кода.

Запуск:
- Все тесты: pytest tests/test_smoke.py
- Один набор: pytest tests/test_smoke.py -k "select_17"
- Конкретный тест: pytest tests/test_smoke.py -k "test_basic_info and select_17"
"""

import allure
import pytest

from test_config.datasets import (
    SELECT_4_CONFIG,
    SELECT_6_CONFIG,
    SELECT_7_CONFIG,
    SELECT_17_CONFIG,
)
from test_config.models import SuiteConfig
from test_scenarios import scenarios


# ===== Конфигурации для параметризации =====
SINGLE_LEAK_CONFIGS = [
    pytest.param(SELECT_4_CONFIG, id=SELECT_4_CONFIG.suite_name),
    pytest.param(SELECT_6_CONFIG, id=SELECT_6_CONFIG.suite_name),
    pytest.param(SELECT_7_CONFIG, id=SELECT_7_CONFIG.suite_name),
    pytest.param(SELECT_17_CONFIG, id=SELECT_17_CONFIG.suite_name),
]


def get_suite_markers(config: SuiteConfig):
    """Возвращает маркеры для тестового набора"""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
    ]


# ===== БАЗОВЫЕ ТЕСТЫ (параметризованные) =====

@pytest.mark.parametrize("config", SINGLE_LEAK_CONFIGS)
class TestSingleLeakSuite:
    """
    Параметризованные тесты для наборов данных с одной утечкой.
    
    Каждый тест запускается для всех наборов: select_4, select_6, select_7, select_17
    """
    
    @pytest.mark.asyncio
    async def test_basic_info(self, ws_client, config: SuiteConfig, request):
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        test_config = config.basic_info_test
        
        # Применяем маркеры динамически
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        
        await scenarios.basic_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_journal_info(self, ws_client, config: SuiteConfig, request):
        """[MessagesInfo] Проверка наличия сообщений в журнале"""
        test_config = config.journal_info_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.journal_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization(self, ws_client, config: SuiteConfig, request):
        """[CommonScheme] Проверка режима работы СОУ: Инициализация"""
        test_config = config.lds_status_initialization_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_initialization(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_main_page_info(self, ws_client, config: SuiteConfig, request):
        """[MainPageInfo] Проверка установки стационара/остановленной перекачки"""
        test_config = config.main_page_info_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.main_page_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_mask_signal_msg(self, ws_client, config: SuiteConfig, request):
        """[MaskSignal] Проверка маскирования датчиков"""
        test_config = config.mask_signal_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.mask_signal_msg(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization_out(self, ws_client, config: SuiteConfig, request):
        """[CommonScheme] Проверка выхода СОУ из Инициализации"""
        test_config = config.lds_status_initialization_out_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_initialization_out(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_all_leaks_info(self, ws_client, config: SuiteConfig, imitator_start_time, request):
        """[AllLeaksInfo] Проверка начала утечки"""
        test_config = config.leak.all_leaks_info_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.all_leaks_info(ws_client, config, config.leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_tu_leaks_info(self, ws_client, config: SuiteConfig, imitator_start_time, request):
        """[TuLeaksInfo] Проверка утечки"""
        test_config = config.leak.tu_leaks_info_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.tu_leaks_info(ws_client, config, config.leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_lds_status_during_leak(self, ws_client, config: SuiteConfig, request):
        """[CommonScheme] Проверка режима работы СОУ во время утечки"""
        test_config = config.lds_status_during_leak_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.lds_status_during_leak(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_acknowledge_leak_info(self, ws_client, config: SuiteConfig, request):
        """[AcknowledgeLeak] Проверка квитирования утечки"""
        test_config = config.leak.acknowledge_leak_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.acknowledge_leak_info(ws_client, config, config.leak)
    
    @pytest.mark.asyncio
    async def test_output_signals(self, ws_client, config: SuiteConfig, imitator_start_time, request):
        """[OutputSignalsInfo] Проверка данных об утечке в выходных сигналах"""
        test_config = config.leak.output_signals_test
        
        request.node.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        request.node.add_marker(pytest.mark.offset(test_config.offset))
        
        allure.dynamic.title(test_config.title)
        allure.dynamic.tag(test_config.tag)
        if test_config.description:
            allure.dynamic.description(test_config.description)
        
        await scenarios.output_signals(ws_client, config, config.leak, imitator_start_time)
