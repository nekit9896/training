import glob
import os
import shutil
import threading
import time

import allure
import pytest
import pytest_asyncio

from clients.keycloak_clients import KeycloakAuthError, KeycloakClient
from clients.testops_client import AllureResultsUploader, logger
from clients.websocket_client import WebSocketClient
from constants.architecture_constants import EnvKeyConstants as EnvConst
from constants.architecture_constants import ImitatorConstants as ImConst
from constants.architecture_constants import WebSocketClientConstants as WSCliConst
from infra.stand_setup_manager import StandSetupManager
from test_config.datasets import ALL_CONFIGS


def pytest_addoption(parser):
    """
    Добавляет кастомные опции командной строки pytest.
    """
    parser.addoption(
        "--suites",
        action="store",
        default=None,
        help="Запустить только указанные наборы данных. Пример: --suites=select_4,select_19_20",
    )


def _find_config_by_suite_name(suite_name: str):
    """Находит конфиг по имени набора данных."""
    for config in ALL_CONFIGS:
        if config.suite_name == suite_name:
            return config
    return None


@pytest.fixture(autouse=True)
def allure_suite_hierarchy(request):
    """
    Автоматически устанавливает иерархию Allure для группировки тестов по наборам данных.
    
    В Allure отчёте тесты группируются:
    - Parent Suite: SingleLeakSuite / MultiLeakSuite (тип набора)
    - Suite: select_4 / select_6 / ... (имя набора данных)
    
    Работает как с параметризованными тестами (config в параметрах),
    так и с обычными тестами (через маркер test_suite_name).
    """
    config = None
    suite_name = None
    
    # Пробуем получить конфиг из параметризации
    if hasattr(request, 'fixturenames') and 'config' in request.fixturenames:
        try:
            config = request.getfixturevalue('config')
            suite_name = config.suite_name
        except Exception:
            pass
    
    # Если не нашли, пробуем найти конфиг по маркеру test_suite_name
    if not config:
        marker = request.node.get_closest_marker('test_suite_name')
        if marker:
            suite_name = marker.args[0]
            config = _find_config_by_suite_name(suite_name)
    
    if config and suite_name:
        parent_suite = "MultiLeakSuite" if config.has_multiple_leaks else "SingleLeakSuite"
        allure.dynamic.parent_suite(parent_suite)
        allure.dynamic.suite(suite_name)


def pytest_configure(config):
    """
    Храним состояние сессии
    """
    config.addinivalue_line(
        "markers",
        "critical_stop: если тест упал, останавливаем дальнейшее выполнение сессии (session.shouldstop)",
    )
    config.group_state = {
        "current_suite": None,
        "suite_start_time": None,
        "stand_manager": None,
        "imitator_start_time": None,  # datetime объект времени старта имитатора для расчёта интервалов утечек
    }


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    Делает падение критического теста (marker critical_stop) однозначным:
    - сам тест будет FAILED (pytest.fail)
    - после него прекращаем запуск остальных тестов (session.shouldstop)
    """
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed and item.get_closest_marker("critical_stop"):
        item.session.shouldstop = f"Критическая проверка упала: {item.nodeid}"


# ===== Маппинг имён тестов на атрибуты конфига для получения маркеров =====
# Используется для добавления offset и test_case_id маркеров во время сбора тестов

# Тесты уровня набора (маркеры из SuiteConfig)
SUITE_LEVEL_TEST_MAPPING = {
    'test_basic_info': 'basic_info_test',
    'test_journal_info': 'journal_info_test',
    'test_lds_status_initialization': 'lds_status_initialization_test',
    'test_main_page_info': 'main_page_info_test',
    'test_mask_signal_msg': 'mask_signal_test',
    'test_lds_status_initialization_out': 'lds_status_initialization_out_test',
    'test_main_page_info_unstationary': 'main_page_info_unstationary_test',
    'test_lds_status_during_leak': 'lds_status_during_leak_test',
}

# Тесты уровня утечки (маркеры из LeakTestConfig - параметр leak)
LEAK_LEVEL_TEST_MAPPING = {
    'test_leaks_content': 'leaks_content_test',
    'test_all_leaks_info': 'all_leaks_info_test',
    'test_tu_leaks_info': 'tu_leaks_info_test',
    'test_leak_info_in_journal': 'leak_info_in_journal',
    'test_acknowledge_leak_info': 'acknowledge_leak_test',
    'test_output_signals': 'output_signals_test',
}



def _get_test_markers_config(item, test_name):
    """
    Получает конфигурацию с маркерами для теста.
    
    Для leak-level тестов: маркеры берутся из параметра leak
    Для suite-level тестов: маркеры берутся из config
    
    :return: CaseMarkers объект или None
    """
    if not hasattr(item, 'callspec'):
        return None
    
    params = item.callspec.params
    
    # Проверяем, есть ли параметр leak (для leak-level тестов)
    if 'leak' in params and test_name in LEAK_LEVEL_TEST_MAPPING:
        leak = params['leak']
        attr_name = LEAK_LEVEL_TEST_MAPPING[test_name]
        return getattr(leak, attr_name, None)
    
    # Для suite-level тестов берём из config
    if 'config' in params and test_name in SUITE_LEVEL_TEST_MAPPING:
        suite_config = params['config']
        attr_name = SUITE_LEVEL_TEST_MAPPING[test_name]
        return getattr(suite_config, attr_name, None)
    
    return None


def pytest_collection_modifyitems(session, config, items):
    """
    1. Фильтрует тесты по --suites (если указано)
    2. Исключает тесты, у которых конфиг = None (тест отключён для этого набора данных)
    3. Добавляет маркеры offset и test_case_id из конфига к каждому параметризованному тесту
    4. Сортирует тесты по test_suite_name для группировки по наборам данных
    """
    # Получаем список выбранных наборов из --suites
    suites_option = config.getoption("--suites")
    selected_suites = None
    if suites_option:
        # Парсим список наборов: "select_4,select_19_20" -> ["select_4", "select_19_20"]
        selected_suites = [s.strip().lower() for s in suites_option.split(",")]
    
    selected_items = []
    deselected_items = []
    
    for item in items:
        # Фильтрация по --suites
        if selected_suites:
            suite_marker = item.get_closest_marker("test_suite_name")
            if suite_marker:
                suite_name = suite_marker.args[0].lower()
                # Проверяем, содержит ли имя набора одну из выбранных подстрок
                if not any(selected in suite_name for selected in selected_suites):
                    deselected_items.append(item)
                    continue
        
        # Получаем имя функции теста (без параметров)
        test_name = item.originalname or item.name.split('[')[0]
        
        # Получаем конфиг с маркерами для теста
        test_config = _get_test_markers_config(item, test_name)
        
        if test_config is not None:
            # Добавляем маркер offset
            if hasattr(test_config, 'offset') and test_config.offset is not None:
                item.add_marker(pytest.mark.offset(test_config.offset))
            
            # Добавляем маркер test_case_id
            if hasattr(test_config, 'test_case_id') and test_config.test_case_id is not None:
                item.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        elif test_name in SUITE_LEVEL_TEST_MAPPING or test_name in LEAK_LEVEL_TEST_MAPPING:
            # Конфиг теста = None - исключаем тест из прогона
            deselected_items.append(item)
            continue
        
        selected_items.append(item)
    
    # Уведомляем pytest об исключённых тестах
    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)
    
    # Заменяем список тестов на отфильтрованный
    items[:] = selected_items

    # Сортировка тестов по test_suite_name и offset 
    def suite_offset_key(item):
        """
        Сортировка тестов по test_suite_name и offset (без падения на None).
        """
        test_suite_name_marker = item.get_closest_marker("test_suite_name")
        suite_name = test_suite_name_marker.args[0] if test_suite_name_marker else ""

        offset_marker = item.get_closest_marker("offset")
        if offset_marker:
            try:
                offset_value = float(offset_marker.args[0])
            except Exception:
                offset_value = float("inf")
        else:
            offset_value = float("inf")

        original_index = getattr(item, "_collection_index", 0)
        return suite_name, offset_value, original_index

    for index, item in enumerate(items):
        item._collection_index = index

    items.sort(key=suite_offset_key)

    for item in items:
        if hasattr(item, "_collection_index"):
            delattr(item, "_collection_index")


@pytest.fixture(autouse=True)
def allure_tms_link(request):
    """
    Allure TMS‑линки по test_case_id
    """
    if test_case_id_marker := request.node.get_closest_marker("test_case_id"):
        test_case_id = test_case_id_marker.args[0]
        allure.dynamic.link(
            f"https://{os.environ['TESTOPS_BASE_URL']}/testcases?selected_id={test_case_id}",
            name=f"TestCase-{test_case_id}",
            link_type="tms",
        )


@pytest.fixture(autouse=True)
def offset_wait(request):
    """
    Offset‑ожидание перед каждым тестом относительно старта имитатора
    """
    if offset_marker := request.node.get_closest_marker("offset"):
        offset_sec = float(offset_marker.args[0]) * 60
        start = request.config.group_state["suite_start_time"] or 0
        elapsed = time.monotonic() - start
        to_wait = max(0, offset_sec - elapsed)
        if to_wait:
            time.sleep(to_wait)


def compute_imitator_duration(item, current_test_suite: str) -> float:
    """
    Вычисляет длительность для имитатора (в минутах).

    Правило:
      - Собирает все тесты (item.session.items) с меткой test_suite_name == current_test_suite
      - Извлекает все значения @pytest.mark.offset(...) (в минутах)
      - Если offsets найдены: возвращает max(offsets) + IMITATOR_FINISH_DELAY задержка остановки имитатора
      - Иначе: если у текущего item есть @pytest.mark.imitator_duration — используется как fallback и логируется
      - Если ничего не найдено — pytest.fail с понятным текстом
    """

    suite_items = [
        suite_item
        for suite_item in item.session.items
        if (marker := suite_item.get_closest_marker("test_suite_name")) and marker.args[0] == current_test_suite
    ]

    offsets = []
    for suite_item in suite_items:
        offset_marker = suite_item.get_closest_marker("offset")
        if offset_marker:
            try:
                offsets.append(float(offset_marker.args[0]))
            except Exception:
                continue

    if offsets:
        max_offset = max(offsets)
        imitator_duration = float(max_offset) + ImConst.IMITATOR_FINISH_DELAY_MINUTE
        return imitator_duration

    else:
        # fallback- если все еще задан старый маркер imitator_duration, то используем его
        if imitator_mark := item.get_closest_marker("imitator_duration"):
            imitator_duration = float(imitator_mark.args[0])
            logger.warning(
                "[DEPRECATED] использован pytest.mark.imitator_duration()"
                f"рекомендуется убрать и полагаться на max_offset + {ImConst.IMITATOR_FINISH_DELAY_MINUTE}"
            )
            return imitator_duration

        pytest.fail(
            "Не удалось вычислить imitator_duration: в тестовом модуле одновременно отсутствуют "
            "и @pytest.mark.offset(), и pytest.mark.imitator_duration()"
        )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
    """
    Перезапуск имитатора при смене test_suite_name
    """
    cfg = item.config.group_state

    test_suite_marker = item.get_closest_marker("test_suite_name")
    if not test_suite_marker:
        pytest.fail("Тест без @pytest.mark.test_suite_name")
    current_test_suite = test_suite_marker.args[0]

    if current_test_suite != cfg["current_suite"]:
        # stop old
        if stand_manager := cfg["stand_manager"]:
            stand_manager.stop_imitator_wrapper()
            if not os.environ.get("RUN_WITHOUT_TESTOPS", "False").lower() == "true":
                # При запуске с TestOps удаляет данные прогона
                stand_manager.server_test_data_remover()

        # start new
        cfg["current_suite"] = current_test_suite
        cfg["suite_start_time"] = time.monotonic() + ImConst.CORE_START_DELAY_S

        data_id = item.get_closest_marker("test_suite_data_id").args[0]
        test_data_name = item.get_closest_marker("test_data_name").args[0]

        imitator_duration = compute_imitator_duration(item, current_test_suite)

        stand_manager = StandSetupManager(
            duration_m=imitator_duration, test_data_id=data_id, test_data_name=test_data_name
        )
        cfg["stand_manager"] = stand_manager
        try:
            stand_manager.check_opc_server_status()
        except RuntimeError as error:
            msg = (
                "[SETUP] [ERROR] OPC сервер недоступен. Имитатор и автотесты не запущены. "
                f"Ошибка при проверке статуса OPC: {error}"
            )
            allure.attach(msg, name="OPC сервер недоступен", attachment_type=allure.attachment_type.TEXT)
            pytest.exit(msg)
        try:
            stand_manager.setup_stand_for_imitator_run()
        except RuntimeError as error:
            pytest.exit(f"[SETUP] [ERROR] ошибка при подготовке стенда: {error}")

        imitator_thread = threading.Thread(
            target=stand_manager.start_imitator, name=f"imitator->{current_test_suite}", daemon=True
        )
        core_thread = threading.Thread(target=stand_manager.start_core)
        try:
            imitator_thread.start()
        except RuntimeError as error:
            pytest.exit(f"[SETUP] [ERROR] ошибка запуска имитатора: {error}")
        time.sleep(ImConst.CORE_START_DELAY_S)
        try:
            core_thread.start()
            core_thread.join(timeout=5)
        except RuntimeError as error:
            pytest.exit(f"[SETUP] [ERROR] ошибка запуска СORE контейнеров: {error}")

        # Сохраняем время старта имитатора для расчёта интервалов утечек в тестах
        cfg["imitator_start_time"] = stand_manager.start_time

    yield  # pytest продолжит выполнение теста


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item, nextitem):
    """
    Teardown имитатора при выходе из группы
    """
    yield
    cfg = item.config.group_state

    next_marker = nextitem.get_closest_marker("test_suite_name") if nextitem else None
    next_suite = next_marker.args[0] if next_marker else None

    if next_suite != cfg["current_suite"]:
        if stand_manager := cfg["stand_manager"]:
            stand_manager.stop_imitator_wrapper()
            if not os.environ.get("RUN_WITHOUT_TESTOPS", "False").lower() == "true":
                # При запуске с TestOps удаляет данные прогона
                stand_manager.server_test_data_remover()
            cfg["stand_manager"] = None
        cfg["current_suite"] = None

        # опционально дождаться завершения потока (если не daemon) — безопасный join
        imitator_thread = cfg.get("imitator_thread")
        if imitator_thread and not getattr(imitator_thread, "daemon", False):
            try:
                imitator_thread.join(timeout=5)
            except RuntimeError:
                logger.exception("Ошибка при join() фона имитатора")


def get_ws_host() -> str:
    instance = os.environ.get(EnvConst.STAND_NAME)
    if not instance:
        pytest.exit(f"Переменная окружения {EnvConst.STAND_NAME} не задана в .env")

    ws_host = f"{WSCliConst.SERVICE_NAME}.{WSCliConst.COMPONENT}-{instance}.{WSCliConst.ROOT_DOMAIN}"

    return ws_host


def get_token(max_retries: int = 3, backoff: float = 5.0) -> str:
    """
    :param max_retries: сколько всего попыток (включая первую)
    :param backoff: время в секундах между попытками
    """
    last_exc = None

    for attempt in range(1, max_retries + 1):
        try:
            keycloak = KeycloakClient(
                url=os.environ.get(EnvConst.KEYCLOAK_URL),
                client_id=os.environ.get(EnvConst.KEYCLOAK_CLIENT_ID),
                client_secret=os.environ.get(EnvConst.KEYCLOAK_CLIENT_SECRET),
                username=os.environ.get(EnvConst.KEYCLOAK_USERNAME),
                password=os.environ.get(EnvConst.KEYCLOAK_PASSWORD),
            )
            token = keycloak.get_access_token()
            if not token:
                raise KeycloakAuthError("Получен пустой access token")
            return token

        except KeycloakAuthError as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] KeycloakAuthError: {e}. Повтор через {backoff} сек.")
        except Exception as e:
            last_exc = e
            logger.warning(f"[{attempt}/{max_retries}] Неожиданная ошибка: {e}. Повтор через {backoff} сек.")

        if attempt < max_retries:
            time.sleep(backoff)

    # все попытки исчерпаны
    logger.error(f"Не удалось получить токен после {max_retries} попыток: {last_exc}")
    pytest.fail(f"Не удалось получить токен после {max_retries} попыток: {last_exc}")


@pytest_asyncio.fixture
async def ws_client():
    """
    Фикстура для работы с websocket клиентом
    :return: Объект wss соединения
    """
    ws_host = get_ws_host()
    auth_token = get_token()
    async with WebSocketClient(ws_host, auth_token) as client:
        yield client


@pytest.fixture
def imitator_start_time(request):
    """
    Фикстура для получения времени старта имитатора (datetime объект).
    Используется для точного расчёта времени обнаружения утечек:
    - leak_start_time = imitator_start_time + timedelta(seconds=LEAK_START_INTERVAL)
    - leak_end_time = imitator_start_time + timedelta(seconds=LEAK_START_INTERVAL + ALLOWED_TIME_DIFF_SECONDS)
    """
    start_time = request.config.group_state.get("imitator_start_time")
    if start_time is None:
        pytest.fail("imitator_start_time не установлен. Убедитесь что тест запущен после инициализации имитатора.")
    return start_time


def pytest_sessionfinish(session, exitstatus):
    """
    В завершении сессии — отправляем единый Allure‑отчёт в TestOps.
    """
    # 1) teardown стенда: остановить имитатор и удалить временные данные на стенде.
    # Делаем это здесь, потому что при pytest.exit/ошибках не всегда отрабатывают пер-suite teardown хуки.
    try:
        stand_manager = getattr(session.config, "group_state", {}).get("stand_manager")
        if stand_manager:
            try:
                stand_manager.stop_imitator_wrapper()
            except Exception:
                logger.exception("[SESSIONFINISH] Ошибка при остановке имитатора")
            try:
                stand_manager.server_test_data_remover()
            except Exception:
                logger.exception("[SESSIONFINISH] Ошибка при удалении временных данных на стенде")
    except Exception:
        logger.exception("[SESSIONFINISH] Ошибка при получении stand_manager из group_state")

    # 2) Выгрузка allure-results в TestOps
    try:
        uploader = AllureResultsUploader()
        logger.info("Uploading Allure results to TestOps")
        uploader.upload_allure_results()
    except Exception:
        logger.exception("[SESSIONFINISH] Ошибка при выгрузке allure-results в TestOps")

    try:
        if os.path.isdir("allure-results"):
            shutil.rmtree("allure-results")
    except Exception:
        logger.exception("[SESSIONFINISH] Ошибка при удалении allure-results")

    # 3) Удаление локальных архивов с данными (runner)
    project_root = os.path.dirname(os.path.abspath(__file__))
    files_for_drop = glob.glob(os.path.join(project_root, "*.tar.gz"))
    if not files_for_drop:
        logger.warning("Не нашлось архивов .tar.gz с данным для удаления")
    else:
        for file in files_for_drop:
            os.remove(file)


@pytest.fixture()
def ws_params(request):
    """
    Передает параметры для websocket в тест
    """
    return request.param
