"""
Автоматическое обнаружение конфигураций наборов данных.

Для добавления нового набора:
1. Создать файл конфигурации (например, select_XX.py)
2. Экспортировать переменную с суффиксом _CONFIG (например, SELECT_XX_CONFIG)
3. Для наборов с одной утечкой - config.leak должен быть заполнен
4. Для наборов с несколькими утечками - config.leaks должен содержать список

Всё! Импорты обновятся автоматически.

Архитектура:
- ALL_SMOKE_CONFIGS: конфиги для smoke-тестов (SmokeSuiteConfig)
- ALL_LDS_STATUS_CONFIGS: конфиги для regress-тестов режимов СОУ (LDSStatusConfig)
- ALL_CONFIGS: все конфиги (для обратной совместимости, алиас ALL_SMOKE_CONFIGS)
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Any, Dict, List, Type

from test_config.models_for_tests import BaseSuiteConfig, LDSStatusConfig, SmokeSuiteConfig

# Путь к директории datasets
_DATASETS_PATH = Path(__file__).parent

# Кэш для прямого доступа по имени переменной (SELECT_4_CONFIG и т.д.)
_CONFIG_CACHE: Dict[str, BaseSuiteConfig] = {}


def _discover_configs_by_type(config_type: Type[BaseSuiteConfig]) -> List[BaseSuiteConfig]:
    """
    Автоматически находит все конфигурации указанного типа в директории datasets.
    """
    configs = []

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

                # Проверяем точное соответствие типу (не наследников)
                if type(config) is config_type:
                    _CONFIG_CACHE[attr_name] = config
                    configs.append(config)

    configs.sort(key=lambda c: c.suite_name)
    return configs


def _split_smoke_configs(configs: List[SmokeSuiteConfig]) -> tuple[List[SmokeSuiteConfig], List[SmokeSuiteConfig]]:
    """Разделяет smoke-конфиги на single-leak и multi-leak."""
    single = [config for config in configs if not config.has_multiple_leaks]
    multi = [config for config in configs if config.has_multiple_leaks]
    return single, multi


# ===== Smoke-тесты (утечки) =====
_ALL_SMOKE_CONFIGS = _discover_configs_by_type(SmokeSuiteConfig)
SINGLE_LEAK_CONFIGS, MULTI_LEAK_CONFIGS = _split_smoke_configs(_ALL_SMOKE_CONFIGS)
ALL_SMOKE_CONFIGS = SINGLE_LEAK_CONFIGS + MULTI_LEAK_CONFIGS

# ===== Regress-тесты режимов СОУ =====
ALL_LDS_STATUS_CONFIGS = _discover_configs_by_type(LDSStatusConfig)

# ===== Обратная совместимость =====
ALL_CONFIGS = ALL_SMOKE_CONFIGS


def get_config_by_name(name: str) -> BaseSuiteConfig:
    """Получить конфиг по имени suite_name"""
    for config in _CONFIG_CACHE.values():
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
        "ALL_SMOKE_CONFIGS",
        "ALL_LDS_STATUS_CONFIGS",
        "get_config_by_name",
    ]


__all__ = [
    "SINGLE_LEAK_CONFIGS",
    "MULTI_LEAK_CONFIGS",
    "ALL_CONFIGS",
    "ALL_SMOKE_CONFIGS",
    "ALL_LDS_STATUS_CONFIGS",
    "get_config_by_name",
] + list(_CONFIG_CACHE.keys())
