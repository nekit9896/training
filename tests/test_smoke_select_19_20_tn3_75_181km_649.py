"""
Smoke-тесты СОУ для набора данных Select_19_20_tn3_75_181km_649.

Запуск:
    pytest tests/test_smoke_select_19_20_tn3_75_181km_649.py

Данные:
    - ТУ: Тихорецк-Новороссийск-3
    - ДВЕ утечки:
      - Утечка 1: 75 км, 649 м³/ч
      - Утечка 2: 181 км, 649 м³/ч

Особенности:
    - Тест с двумя утечками
    - Дополнительный тест на нестационарный режим (main_page_info_unstationary)
    - Раздельное квитирование первой и второй утечки
"""

import pytest

from tests.test_config import SELECT_19_CONFIG
from tests.test_smoke_base import make_test_param
from tests.test_smoke_base import \
    test_acknowledge_leak_info as _test_acknowledge_leak_info
from tests.test_smoke_base import \
    test_acknowledge_leak_info_leak_2 as _test_acknowledge_leak_info_leak_2
from tests.test_smoke_base import test_all_leaks_info as _test_all_leaks_info
from tests.test_smoke_base import \
    test_all_leaks_info_leak_2 as _test_all_leaks_info_leak_2
from tests.test_smoke_base import test_basic_info as _test_basic_info
from tests.test_smoke_base import test_journal_info as _test_journal_info
from tests.test_smoke_base import \
    test_lds_status_during_leak as _test_lds_status_during_leak
from tests.test_smoke_base import \
    test_lds_status_initialization as _test_lds_status_initialization
from tests.test_smoke_base import \
    test_lds_status_initialization_out as _test_lds_status_initialization_out
from tests.test_smoke_base import test_leaks_content as _test_leaks_content
from tests.test_smoke_base import \
    test_leaks_content_leak_2 as _test_leaks_content_leak_2
from tests.test_smoke_base import test_main_page_info as _test_main_page_info
from tests.test_smoke_base import \
    test_main_page_info_unstationary as _test_main_page_info_unstationary
from tests.test_smoke_base import test_mask_signal_msg as _test_mask_signal_msg
from tests.test_smoke_base import test_output_signals as _test_output_signals
from tests.test_smoke_base import \
    test_output_signals_leak_2 as _test_output_signals_leak_2
from tests.test_smoke_base import test_tu_leaks_info as _test_tu_leaks_info
from tests.test_smoke_base import \
    test_tu_leaks_info_leak_2 as _test_tu_leaks_info_leak_2

CONFIG = SELECT_19_CONFIG


# ============================================================================
#                    БАЗОВЫЕ ТЕСТЫ
# ============================================================================


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


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "main_page_info")])
async def test_main_page_info_stationary(ws_client, cfg):
    """[MainPageInfo] Проверка установки стационара"""
    await _test_main_page_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "mask_signal_msg")])
async def test_mask_signal_msg(ws_client, cfg):
    """[MaskSignal] Проверка маскирования датчиков"""
    await _test_mask_signal_msg(ws_client, cfg)


@pytest.mark.parametrize(
    "cfg", [make_test_param(CONFIG, "lds_status_initialization_out")]
)
async def test_lds_status_initialization_out(ws_client, cfg):
    """[CommonScheme] Проверка выхода СОУ из Инициализации"""
    await _test_lds_status_initialization_out(ws_client, cfg)


@pytest.mark.parametrize(
    "cfg", [make_test_param(CONFIG, "main_page_info_unstationary")]
)
async def test_main_page_info_unstationary(ws_client, cfg):
    """[MainPageInfo] Проверка перехода в нестационарный режим"""
    await _test_main_page_info_unstationary(ws_client, cfg)


# ============================================================================
#                    ТЕСТЫ ПЕРВОЙ УТЕЧКИ (75 км, offset 47)
# ============================================================================


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "leaks_content")])
async def test_leaks_content_first_leak(ws_client, cfg):
    """[LeaksContent] Проверка первой утечки (75км)"""
    await _test_leaks_content(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "all_leaks_info")])
async def test_all_leaks_info_first_leak(ws_client, cfg):
    """[AllLeaksInfo] Проверка первой утечки (75км)"""
    await _test_all_leaks_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "tu_leaks_info")])
async def test_tu_leaks_info_first_leak(ws_client, cfg):
    """[TuLeaksInfo] Проверка первой утечки (75км)"""
    await _test_tu_leaks_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "lds_status_during_leak")])
async def test_lds_status_during_leak(ws_client, cfg):
    """[CommonScheme] Проверка режима работы СОУ во время утечки"""
    await _test_lds_status_during_leak(ws_client, cfg)


# ============================================================================
#                    ТЕСТЫ ВТОРОЙ УТЕЧКИ (181 км, offset 61)
# ============================================================================


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "leaks_content_leak_2")])
async def test_leaks_content_second_leak(ws_client, cfg):
    """[LeaksContent] Проверка второй утечки (181км)"""
    await _test_leaks_content_leak_2(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "all_leaks_info_leak_2")])
async def test_all_leaks_info_second_leak(ws_client, cfg):
    """[AllLeaksInfo] Проверка второй утечки (181км)"""
    await _test_all_leaks_info_leak_2(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "tu_leaks_info_leak_2")])
async def test_tu_leaks_info_second_leak(ws_client, cfg):
    """[TuLeaksInfo] Проверка второй утечки (181км)"""
    await _test_tu_leaks_info_leak_2(ws_client, cfg)


# ============================================================================
#                    ТЕСТЫ КВИТИРОВАНИЯ
# ============================================================================


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "acknowledge_leak_info")])
async def test_acknowledge_leak_info_first_leak(ws_client, cfg):
    """[AcknowledgeLeak] Проверка квитирования первой утечки (вторая должна остаться)"""
    await _test_acknowledge_leak_info(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "acknowledge_leak_info_leak_2")])
async def test_acknowledge_leak_info_second_leak(ws_client, cfg):
    """[AcknowledgeLeak] Проверка квитирования второй утечки (список должен быть пуст)"""
    await _test_acknowledge_leak_info_leak_2(ws_client, cfg)


# ============================================================================
#                    ТЕСТЫ ВЫХОДНЫХ СИГНАЛОВ
# ============================================================================


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "output_signals")])
async def test_output_signals_first_leak(ws_client, cfg):
    """[OutputSignalsInfo] Проверка выходных сигналов первой утечки (75км)"""
    await _test_output_signals(ws_client, cfg)


@pytest.mark.parametrize("cfg", [make_test_param(CONFIG, "output_signals_leak_2")])
async def test_output_signals_second_leak(ws_client, cfg):
    """[OutputSignalsInfo] Проверка выходных сигналов второй утечки (181км)"""
    await _test_output_signals_leak_2(ws_client, cfg)
