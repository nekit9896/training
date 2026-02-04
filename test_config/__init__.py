"""
Модуль конфигурации тестов.

Экспортирует:
- SuiteConfig - главный конфиг набора данных
- LeakTestConfig - конфиг утечки
- CaseMarkers - маркеры тест-кейса
- DiagnosticAreaStatusConfig - конфиг статусов ДУ
- Constants - общие константы
"""

import test_config.models_for_tests as models

__all__ = [
    models.SuiteConfig,
    models.LeakTestConfig,
    models.CaseMarkers,
    models.DiagnosticAreaStatusConfig,
]
