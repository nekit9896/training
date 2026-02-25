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

from typing import Any, List, Optional

import allure
import pytest

from clients.websocket_client import WebSocketClient
from test_config.datasets import ALL_LDS_STATUS_CONFIGS
from test_config.models_for_tests import CaseMarkers, LDSStatusConfig
from test_scenarios import scenarios

# ===== ГЕНЕРАЦИЯ ПАРАМЕТРОВ =====


def _get_suite_markers(config: LDSStatusConfig) -> List[pytest.MarkDecorator]:
    """Маркеры для тестового набора."""
    return [
        pytest.mark.test_suite_name(config.suite_name),
        pytest.mark.test_suite_data_id(config.suite_data_id),
        pytest.mark.test_data_name(config.archive_name),
        pytest.mark.tu_id(config.technological_unit.id),
    ]


def _generate_suite_params() -> List[Any]:
    """
    Генерирует параметры для тестов уровня набора данных.
    Один параметр на каждый config.
    """
    return [
        pytest.param(config, id=config.suite_name, marks=_get_suite_markers(config))
        for config in ALL_LDS_STATUS_CONFIGS
    ]


# ===== ПАРАМЕТРЫ ДЛЯ ТЕСТОВ =====
SUITE_PARAMS: List[Any] = _generate_suite_params()


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====


def _apply_allure_markers(test_config: CaseMarkers, tag: str, title: str, description: Optional[str] = None) -> None:
    """Применяет allure-маркеры из конфига теста."""
    if not test_config:
        msg = "Не заполнена конфигурация теста: запуск остановлен"
        allure.attach(msg, name="Ошибка подготовки тестрана", attachment_type=allure.attachment_type.TEXT)
        pytest.exit(msg)
    allure.dynamic.tag(tag)
    allure.dynamic.tag("REGRESS")
    allure.dynamic.title(title)
    if description:
        allure.dynamic.description(description)


# ===== ТЕСТЫ УРОВНЯ НАБОРА =====
# Запускаются один раз для каждого config


@pytest.mark.parametrize("config", SUITE_PARAMS)
class TestSuiteScenarios:
    """
    Тесты уровня набора данных.
    Запускаются один раз для каждого конфига.
    """

    @pytest.mark.asyncio
    @pytest.mark.critical_stop
    async def test_basic_info(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.basic_info_test, tag, title)
        await scenarios.basic_info(ws_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_initialization(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """[CommonScheme] Проверка режима работы СОУ: Инициализация"""
        tag = "CommonScheme"
        title = f"[{tag}] Проверка режима работы СОУ: 'Инициализация', по причине: 'Холодный пуск'. ЭФ: Схема"
        description = (
            f"Проверка режима работы СОУ на базовых ДУ, на наборе данных {config.suite_name}, \n"
            f"на технологическом участке {config.technological_unit.description}\n"
            f"Время проведения проверки : {config.lds_status_initialization_test.offset} мин.\n"
            "Подписка на сообщения типа: CommonScheme\n"
            "Ожидаемый режим работы СОУ: Инициализация\n Ожидаемая причина режима работы СОУ: Холодный пуск"
        )
        _apply_allure_markers(config.lds_status_initialization_test, tag, title, description)
        await scenarios.lds_status_initialization_check_with_reasons(ws_client, config)
