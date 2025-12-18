"""
Smoke-тесты СОУ для набора данных Select_25_tn3_6km_56.

Запуск:
    pytest tests/test_smoke_select_25_tn3_6km_56.py

Данные:
    - ТУ: Тихорецк-Новороссийск-3
    - Координата утечки: 6 км
    - Объем утечки: 56 м³/ч

Особенности:
    - Некоторые тесты отключены (initialization, mask_signal, lds_during_leak)
"""

import pytest

from tests.test_config import SELECT_25_CONFIG
from tests.test_smoke_base import make_test_param
from tests.test_smoke_base import \
    test_acknowledge_leak_info as _test_acknowledge_leak_info
from tests.test_smoke_base import test_all_leaks_info as _test_all_leaks_info
from tests.test_smoke_base import test_basic_info as _test_basic_info
from tests.test_smoke_base import test_journal_info as _test_journal_info
from tests.test_smoke_base import test_main_page_info as _test_main_page_info
from tests.test_smoke_base import test_output_signals as _test_output_signals
from tests.test_smoke_base import test_tu_leaks_info as _test_tu_leaks_info

CONFIG = SELECT_25_CONFIG


# ============================================================================
#                    ВКЛЮЧЕННЫЕ ТЕСТЫ
# ============================================================================


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "basic_info")])
async def test_basic_info(ws_client, cfg):
    """[BasicInfo] Проверка базовой информации СОУ"""
    await _test_basic_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "journal_info")])
async def test_journal_info(ws_client, cfg):
    """[MessagesInfo] Проверка наличия сообщений в журнале"""
    await _test_journal_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "main_page_info")])
async def test_main_page_info(ws_client, cfg):
    """[MainPageInfo] Проверка установки стационара"""
    await _test_main_page_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "all_leaks_info")])
async def test_all_leaks_info(ws_client, cfg):
    """[AllLeaksInfo] Проверка сообщения об утечке"""
    await _test_all_leaks_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "tu_leaks_info")])
async def test_tu_leaks_info(ws_client, cfg):
    """[TuLeaksInfo] Проверка сообщения об утечке типа TuLeaksInfoContent"""
    await _test_tu_leaks_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "acknowledge_leak_info")])
async def test_acknowledge_leak_info(ws_client, cfg):
    """[AcknowledgeLeak] Проверка квитирования утечки"""
    await _test_acknowledge_leak_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "output_signals")])
async def test_output_signals(ws_client, cfg):
    """[OutputSignalsInfo] Проверка выходных сигналов"""
    await _test_output_signals(ws_client, cfg)


# ============================================================================
#                    ОТКЛЮЧЕННЫЕ ТЕСТЫ (offset=None в конфигурации)
# ============================================================================
# Следующие тесты НЕ включены в этот модуль, т.к. они отключены для Select_25:
# - test_lds_status_initialization
# - test_lds_status_initialization_out
# - test_lds_status_during_leak
# - test_mask_signal_msg
