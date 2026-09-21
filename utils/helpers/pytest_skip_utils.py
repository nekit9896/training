"""
Скип теста по причине, заданной в конфигурации теста (test_config/datasets).

Технически: на коллекции item помечается маркером skip_reason(reason=...),
а autouse-фикстура skip_reason_guard в conftest.py поднимает pytest.skip уже после
проставления allure-лейблов набора и TMS-линк - иначе в отчёте потерялась бы
группировка по набору данных и привязка к тест-кейсу TestOps.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import allure

if TYPE_CHECKING:
    import pytest

    from test_config.models_for_tests import CaseMarkers

# Имя маркера, которым item помечается на коллекции
SKIP_MARKER_NAME = "skip_reason"

# Тег для фильтрации скипнутых тестов в Allure/TestOps
SKIPPED_TAG = "SKIPPED"


def resolve_skip_reason(test_config: CaseMarkers | None) -> str | None:
    """
    Причина скипа из конфигурации теста. None - тест выполняется.

    test_config - это CaseMarkers именно того набора данных, для которого собран item
    (резолвится в conftest по маппингу "имя теста -> поле конфига"), поэтому skip_reason
    одного набора не влияет на прогон того же теста на других наборах.
    Пустая строка трактуется как отсутствие причины.
    """
    return getattr(test_config, "skip_reason", None) or None


def get_skip_reason_marker(item: pytest.Item) -> str | None:
    """Читает причину скипа из маркера skip_reason. None - тест выполняется."""
    skip_marker = item.get_closest_marker(SKIP_MARKER_NAME)
    if not skip_marker:
        return None
    return skip_marker.kwargs.get("reason")


def is_marked_as_skipped(item: pytest.Item) -> bool:
    """
    True, если тест помечен маркером skip_reason и будет пропущен.

    Используется при расчёте длительности имитатора: пропущенный тест не выполняется,
    поэтому ждать его offset не нужно.
    """
    return bool(get_skip_reason_marker(item))


def decorate_skipped_test_in_allure(item: pytest.Item, reason: str) -> None:
    """
    Делает скипнутый тест читаемым в отчёте.
    """
    test_function = getattr(item, "function", None)
    test_docstring = (getattr(test_function, "__doc__", None) or "").strip()
    if test_docstring:
        allure.dynamic.title(test_docstring)
    allure.dynamic.tag(SKIPPED_TAG)
    allure.dynamic.description(f"Тест скипнут. Причина: {reason}")
