"""
Модуль конфигурации тестов.

Экспортирует:
- SuiteConfig - главный конфиг набора данных
- LeakTestConfig - конфиг утечки
- CaseMarkers - маркеры тест-кейса
- DiagnosticAreaStatusConfig - конфиг статусов ДУ

Общие константы находятся в constants/test_constants.py
"""

from test_config.models import (
    DiagnosticAreaStatusConfig,
    LeakTestConfig,
    CaseMarkers,
    SuiteConfig,
)

__all__ = [
    "SuiteConfig",
    "LeakTestConfig",
    "CaseMarkers",
    "DiagnosticAreaStatusConfig",
]
