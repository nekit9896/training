"""
Модуль сценариев тестов.

Содержит функции-обёртки для каждого типа теста.
Функции называются так же, как тесты, но без префикса test_.
"""

from test_scenarios.scenarios import (
    acknowledge_leak_info,
    all_leaks_info,
    basic_info,
    journal_info,
    leak_info_in_journal,
    lds_status_during_leak,
    lds_status_initialization,
    lds_status_initialization_out,
    main_page_info,
    mask_signal_msg,
    output_signals,
    tu_leaks_info,
)

__all__ = [
    "basic_info",
    "journal_info",
    "lds_status_initialization",
    "main_page_info",
    "mask_signal_msg",
    "lds_status_initialization_out",
    "all_leaks_info",
    "leak_info_in_journal",
    "tu_leaks_info",
    "lds_status_during_leak",
    "acknowledge_leak_info",
    "output_signals",
]

