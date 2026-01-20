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

import allure
import pytest

from test_config.datasets import ALL_CONFIGS
from test_config.models import SuiteConfig, LeakTestConfig
from test_scenarios import scenarios


# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====

def _get_suite_markers(config: SuiteConfig):
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
    ]


def _generate_suite_params():
    """
    Генерирует параметры для тестов уровня набора данных.
    Один параметр на каждый config.
    """
    return [
        pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config))
        for config in ALL_CONFIGS
    ]


def _generate_leak_params():
    """
    Генерирует параметры для тестов уровня утечки.
    
    Для single-leak конфигов: один параметр (config, leak, 1)
    Для multi-leak конфигов: N параметров (config, leak_n, n) для каждой утечки
    
    Returns:
        list: [(config, leak, leak_number), ...]
    """
    params = []
    
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
                    config, leak, leak_number,
                    id=param_id,
                    marks=_get_suite_markers(config),
                )
            )
    
    return params


# ===== ПАРАМЕТРЫ ДЛЯ ТЕСТОВ =====
SUITE_PARAMS = _generate_suite_params()
LEAK_PARAMS = _generate_leak_params()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====

def _apply_allure_markers(test_config):
    """Применяет allure-маркеры из конфига теста."""
    if not test_config:
        return
    allure.dynamic.title(test_config.title)
    allure.dynamic.tag(test_config.tag)
    if test_config.description:
        allure.dynamic.description(test_config.description)


# ===== ТЕСТЫ УРОВНЯ НАБОРА =====
# Запускаются один раз для каждого config

@pytest.mark.parametrize("config", SUITE_PARAMS)
class TestSuiteScenarios:
    """
    Тесты уровня набора данных.
    Запускаются один раз для каждого конфига.
    """
    
    @pytest.mark.asyncio
    async def test_basic_info(self, ws_client, config: SuiteConfig):
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        _apply_allure_markers(config.basic_info_test)
        await scenarios.basic_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_journal_info(self, ws_client, config: SuiteConfig):
        """[MessagesInfo] Проверка наличия сообщений в журнале"""
        _apply_allure_markers(config.journal_info_test)
        await scenarios.journal_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка режима работы СОУ: Инициализация"""
        _apply_allure_markers(config.lds_status_initialization_test)
        await scenarios.lds_status_initialization(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_main_page_info(self, ws_client, config: SuiteConfig):
        """[MainPageInfo] Проверка установки стационара/остановленной перекачки"""
        _apply_allure_markers(config.main_page_info_test)
        await scenarios.main_page_info(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_mask_signal_msg(self, ws_client, config: SuiteConfig):
        """[MaskSignal] Проверка маскирования датчиков"""
        _apply_allure_markers(config.mask_signal_test)
        await scenarios.mask_signal_msg(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_initialization_out(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка выхода СОУ из Инициализации"""
        _apply_allure_markers(config.lds_status_initialization_out_test)
        await scenarios.lds_status_initialization_out(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_main_page_info_unstationary(self, ws_client, config: SuiteConfig):
        """[MainPageInfo] Проверка установки режима Нестационар (для multi-leak)"""
        _apply_allure_markers(config.main_page_info_unstationary_test)
        await scenarios.main_page_info_unstationary(ws_client, config)
    
    @pytest.mark.asyncio
    async def test_lds_status_during_leak(self, ws_client, config: SuiteConfig):
        """[CommonScheme] Проверка режима работы СОУ во время утечки"""
        _apply_allure_markers(config.lds_status_during_leak_test)
        await scenarios.lds_status_during_leak(ws_client, config)


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
    async def test_leaks_content(
        self, ws_client, config: SuiteConfig, leak: LeakTestConfig, leak_number: int, imitator_start_time
    ):
        """[LeaksContent] Проверка утечки через LeaksContent"""
        _apply_allure_markers(leak.leaks_content_test)
        # Добавляем номер утечки в title для multi-leak
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{leak.leaks_content_test.title} (утечка #{leak_number})")
        await scenarios.leaks_content(ws_client, config, leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_all_leaks_info(
        self, ws_client, config: SuiteConfig, leak: LeakTestConfig, leak_number: int, imitator_start_time
    ):
        """[AllLeaksInfo] Проверка начала утечки"""
        _apply_allure_markers(leak.all_leaks_info_test)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{leak.all_leaks_info_test.title} (утечка #{leak_number})")
        await scenarios.all_leaks_info(ws_client, config, leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_tu_leaks_info(
        self, ws_client, config: SuiteConfig, leak: LeakTestConfig, leak_number: int, imitator_start_time
    ):
        """[TuLeaksInfo] Проверка утечки"""
        _apply_allure_markers(leak.tu_leaks_info_test)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{leak.tu_leaks_info_test.title} (утечка #{leak_number})")
        await scenarios.tu_leaks_info(ws_client, config, leak, imitator_start_time)
    
    @pytest.mark.asyncio
    async def test_acknowledge_leak_info(
        self, ws_client, config: SuiteConfig, leak: LeakTestConfig, leak_number: int
    ):
        """[AcknowledgeLeak] Проверка квитирования утечки"""
        _apply_allure_markers(leak.acknowledge_leak_test)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{leak.acknowledge_leak_test.title} (утечка #{leak_number})")
        await scenarios.acknowledge_leak_info(ws_client, config, leak)
    
    @pytest.mark.asyncio
    async def test_output_signals(
        self, ws_client, config: SuiteConfig, leak: LeakTestConfig, leak_number: int, imitator_start_time
    ):
        """[OutputSignalsInfo] Проверка данных об утечке в выходных сигналах"""
        _apply_allure_markers(leak.output_signals_test)
        if config.has_multiple_leaks:
            allure.dynamic.title(f"{leak.output_signals_test.title} (утечка #{leak_number})")
        await scenarios.output_signals(ws_client, config, leak, imitator_start_time)
