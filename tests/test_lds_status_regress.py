"""

Архитектура параметризации:
- SUITE_PARAMS: тесты уровня набора (один раз на набор данных LDSStatusConfig)

Для добавления нового набора:
1. Создать файл в test_config/datasets/ с LDSStatusConfig
2. Добавить маппинг новых тестов в conftest.py -> LDS_STATUS_SUITE_LEVEL_MAPPING
3. Тесты подхватятся автоматически

Запуск:
- Все тесты: pytest tests/test_lds_status_regress.py
- Один набор: pytest tests/test_lds_status_regress.py --suites=sou_mode_inflow
- Несколько наборов: pytest tests/test_lds_status_regress.py --suites=sou_mode_inflow,sou_mode_stopped,sou_mode_biks
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
    async def test_basic_info_mode_sou(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
        """[BasicInfo] Проверка базовой информации СОУ: список ТУ"""
        tag = "BasicInfo"
        title = f"[{tag}] Проверка списка ТУ. ЭФ: Главная страница"
        _apply_allure_markers(config.basic_info_test, tag, title)
        await scenarios.basic_info(ws_client, config)

    @pytest.mark.asyncio
    async def test_lds_status_initialization_mode_sou(self, ws_client: WebSocketClient, config: LDSStatusConfig) -> None:
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
