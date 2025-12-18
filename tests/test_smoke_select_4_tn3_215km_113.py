"""
Smoke-тесты СОУ для набора данных Select_4_tn3_215km_113.

Запуск:
    pytest tests/test_smoke_select_4_tn3_215km_113.py

Данные:
    - ТУ: Тихорецк-Новороссийск-3
    - Координата утечки: 215 км
    - Объем утечки: 113 м³/ч

Особенности:
    - Режим: Остановленная перекачка (STOPPED)
    - Ожидаемый статус СОУ: DEGRADATION
"""

import pytest

from tests.test_config import SELECT_4_CONFIG
from tests.test_smoke_base import make_test_param
from tests.test_smoke_base import \
    test_acknowledge_leak_info as _test_acknowledge_leak_info
from tests.test_smoke_base import test_all_leaks_info as _test_all_leaks_info
from tests.test_smoke_base import test_basic_info as _test_basic_info
from tests.test_smoke_base import test_journal_info as _test_journal_info
from tests.test_smoke_base import \
    test_lds_status_during_leak as _test_lds_status_during_leak
from tests.test_smoke_base import \
    test_lds_status_initialization as _test_lds_status_initialization
from tests.test_smoke_base import \
    test_lds_status_initialization_out as _test_lds_status_initialization_out
from tests.test_smoke_base import test_main_page_info as _test_main_page_info
from tests.test_smoke_base import test_mask_signal_msg as _test_mask_signal_msg
from tests.test_smoke_base import test_output_signals as _test_output_signals
from tests.test_smoke_base import test_tu_leaks_info as _test_tu_leaks_info

CONFIG = SELECT_4_CONFIG


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "basic_info")])
async def test_basic_info(ws_client, cfg):
    """[BasicInfo] Проверка базовой информации СОУ"""
    await _test_basic_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "journal_info")])
async def test_journal_info(ws_client, cfg):
    """[MessagesInfo] Проверка наличия сообщений в журнале"""
    await _test_journal_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "lds_status_initialization")])
async def test_lds_status_initialization(ws_client, cfg):
    """[CommonScheme] Проверка режима работы СОУ: 'Инициализация'"""
    await _test_lds_status_initialization(ws_client, cfg)


@pytest.mark.parametrize(
    "cfg", [make_test_param(CONFIG, "lds_status_initialization_out")]
)
async def test_lds_status_initialization_out(ws_client, cfg):
    """[CommonScheme] Проверка выхода СОУ из Инициализации"""
    await _test_lds_status_initialization_out(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "lds_status_during_leak")])
async def test_lds_status_during_leak(ws_client, cfg):
    """[CommonScheme] Проверка режима работы СОУ во время утечки"""
    await _test_lds_status_during_leak(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "main_page_info")])
async def test_main_page_info(ws_client, cfg):
    """[MainPageInfo] Проверка установки режима остановленной перекачки"""
    await _test_main_page_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "mask_signal_msg")])
async def test_mask_signal_msg(ws_client, cfg):
    """[MaskSignal] Проверка маскирования датчиков"""
    await _test_mask_signal_msg(ws_client, cfg)


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
