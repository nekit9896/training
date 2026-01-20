"""
Автоматическое обнаружение конфигураций наборов данных.

Для добавления нового набора:
1. Создать файл конфигурации (например, select_XX.py)
2. Экспортировать переменную с суффиксом _CONFIG (например, SELECT_XX_CONFIG)
3. Для наборов с одной утечкой - config.leak должен быть заполнен
4. Для наборов с несколькими утечками - config.leaks должен содержать список

Всё! Импорты обновятся автоматически.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Dict, List

from test_config.models import SuiteConfig

# Путь к директории datasets
_DATASETS_PATH = Path(__file__).parent

# Кэш для прямого доступа по имени переменной (SELECT_4_CONFIG и т.д.)
_CONFIG_CACHE: Dict[str, SuiteConfig] = {}


def _discover_configs() -> tuple[List[SuiteConfig], List[SuiteConfig]]:
    """
    Автоматически находит все конфигурации в директории datasets.
    
    Returns:
        tuple: (single_leak_configs, multi_leak_configs)
    """
    single_leak_configs = []
    multi_leak_configs = []
    
    # Сканируем все .py файлы в директории
    for module_info in pkgutil.iter_modules([str(_DATASETS_PATH)]):
        if module_info.name.startswith('_'):
            continue  # Пропускаем __init__ и приватные модули
            
        # Импортируем модуль
        module = importlib.import_module(f"test_config.datasets.{module_info.name}")
        
        # Ищем переменные с суффиксом _CONFIG
        for attr_name in dir(module):
            if attr_name.endswith('_CONFIG'):
                config = getattr(module, attr_name)
                
                # Проверяем что это SuiteConfig
                if isinstance(config, SuiteConfig):
                    # Сохраняем в кэш для прямого доступа
                    _CONFIG_CACHE[attr_name] = config
                    
                    # Разделяем на single/multi leak
                    if config.has_multiple_leaks:
                        multi_leak_configs.append(config)
                    else:
                        single_leak_configs.append(config)
    
    # Сортируем по имени для стабильного порядка
    single_leak_configs.sort(key=lambda c: c.suite_name)
    multi_leak_configs.sort(key=lambda c: c.suite_name)
    
    return single_leak_configs, multi_leak_configs


# Автоматически обнаруженные конфиги
SINGLE_LEAK_CONFIGS, MULTI_LEAK_CONFIGS = _discover_configs()

# Все конфиги
ALL_CONFIGS = SINGLE_LEAK_CONFIGS + MULTI_LEAK_CONFIGS


def get_config_by_name(name: str) -> SuiteConfig:
    """Получить конфиг по имени suite_name"""
    for config in ALL_CONFIGS:
        if config.suite_name == name:
            return config
    raise ValueError(f"Конфиг с именем '{name}' не найден")


def __getattr__(name: str):
    """
    Динамический доступ к конфигам по имени переменной.
    Позволяет использовать: from test_config.datasets import SELECT_4_CONFIG
    """
    if name in _CONFIG_CACHE:
        return _CONFIG_CACHE[name]
    raise AttributeError(f"module 'test_config.datasets' has no attribute '{name}'")


def __dir__():
    """Для автодополнения в IDE"""
    return list(_CONFIG_CACHE.keys()) + [
        "SINGLE_LEAK_CONFIGS",
        "MULTI_LEAK_CONFIGS",
        "ALL_CONFIGS",
        "get_config_by_name",
    ]


__all__ = [
    "SINGLE_LEAK_CONFIGS",
    "MULTI_LEAK_CONFIGS", 
    "ALL_CONFIGS",
    "get_config_by_name",
] + list(_CONFIG_CACHE.keys())
