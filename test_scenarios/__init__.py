"""
Модуль сценариев тестов.

Содержит функции-обёртки для каждого типа теста.
Функции называются так же, как тесты, но без префикса test_.
Для добавления нового теста необходимо добавить в список __all__ название этого теста scenarios.your_new_test
"""

import test_scenarios.smoke_scenarios as scenarios
from test_scenarios import lds_status_scenarios, rejected_scenarios

__all__ = [
    scenarios.basic_info,
    scenarios.journal_info,
    scenarios.imitate_sensor_signal,
    scenarios.lds_status_initialization,
    scenarios.lds_status_init_in_journal,
    scenarios.main_page_info,
    scenarios.main_page_info_signals,
    scenarios.mask_info_in_journal,
    scenarios.mask_signal_test,
    scenarios.lds_status_initialization_out,
    scenarios.lds_status_init_out_in_journal,
    scenarios.all_leaks_info,
    scenarios.leak_info_in_journal,
    scenarios.possible_leak_in_journal,
    scenarios.tu_leaks_info,
    scenarios.lds_status_during_leak,
    scenarios.acknowledge_leak_info,
    scenarios.acknowledge_leak_in_journal,
    scenarios.output_signals,
    scenarios.balance_algorithm_leak_completed,
    scenarios.completed_leak_info_in_journal,
    scenarios.mode_mt_in_journal,
    rejected_scenarios.rejection_input_signals,
    rejected_scenarios.rejection_journal,
    rejected_scenarios.rejection_main_page,
    rejected_scenarios.rejection_scheme_signals_state,
    lds_status_scenarios.lds_status_check_with_reasons,
    scenarios.export_leaks_report,
    scenarios.export_lds_status_report,
    scenarios.export_mt_mode_report,
]
