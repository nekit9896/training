"""
Модуль конфигурации тестов.

Экспортирует:
- SmokeSuiteConfig - конфиг для smoke-тестов (утечки)
- LDSStatusConfig - конфиг для regress-тестов режимов СОУ
- LeakTestConfig - конфиг утечки
- CaseMarkers - маркеры тест-кейса
- DiagnosticAreaStatusConfig - конфиг статусов ДУ
- Constants - общие константы
"""

import test_config.models_for_tests as models

__all__ = [
    models.BaseSuiteConfig,
    models.SmokeSuiteConfig,
    models.LDSStatusConfig,
    models.LeakTestConfig,
    models.CaseMarkers,
    models.CaseData,
    models.DiagnosticAreaStatusConfig,
]
