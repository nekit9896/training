"""
Конфигурации наборов данных.

Каждый набор данных имеет свой файл с полной конфигурацией.
Для добавления нового набора:
1. Создать файл конфигурации (например, select_XX.py)
2. Добавить импорт сюда
"""

from test_config.datasets.select_4 import SELECT_4_CONFIG
from test_config.datasets.select_6 import SELECT_6_CONFIG
from test_config.datasets.select_7 import SELECT_7_CONFIG
from test_config.datasets.select_17 import SELECT_17_CONFIG
from test_config.datasets.select_19_20 import SELECT_19_20_CONFIG, Select19Constants

__all__ = [
    "SELECT_4_CONFIG",
    "SELECT_6_CONFIG",
    "SELECT_7_CONFIG",
    "SELECT_17_CONFIG",
    "SELECT_19_20_CONFIG",
    "Select19Constants",
]
