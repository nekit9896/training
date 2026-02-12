"""
Модуль сценариев тестов.

Содержит функции-обёртки для каждого типа теста.
Функции называются так же, как тесты, но без префикса test_.
Для добавления нового теста необходимо добавить в список __all__ название этого теста scenarios.your_new_test
"""

import test_scenarios.scenarios as scenarios

__all__ = [
    scenarios.basic_info,
    scenarios.journal_info,
    scenarios.lds_status_initialization,
    scenarios.main_page_info,
    scenarios.main_page_info_signals,
    scenarios.mask_signal_msg,
    scenarios.lds_status_initialization_out,
    scenarios.all_leaks_info,
    scenarios.leak_info_in_journal,
    scenarios.tu_leaks_info,
    scenarios.lds_status_during_leak,
    scenarios.acknowledge_leak_info,
    scenarios.output_signals,
]
