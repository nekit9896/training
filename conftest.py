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


def pytest_configure(config):
    """
    Храним состояние сессии
    """
    config.group_state = {
        "current_suite": None,
        "suite_start_time": None,
        "stand_manager": None,
        "imitator_start_time": None,  # datetime объект времени старта имитатора для расчёта интервалов утечек
    }


# ===== Маппинг имён тестов на атрибуты конфига для получения маркеров =====
# Используется для добавления offset и test_case_id маркеров во время сбора тестов
TEST_CONFIG_MAPPING = {
    'test_basic_info': 'basic_info_test',
    'test_journal_info': 'journal_info_test',
    'test_lds_status_initialization': 'lds_status_initialization_test',
    'test_main_page_info': 'main_page_info_test',
    'test_mask_signal_msg': 'mask_signal_test',
    'test_lds_status_initialization_out': 'lds_status_initialization_out_test',
    'test_lds_status_during_leak': 'lds_status_during_leak_test',
    # Тесты утечек - для наборов с одной утечкой
    'test_leaks_content': 'leak.leaks_content_test',
    'test_all_leaks_info': 'leak.all_leaks_info_test',
    'test_tu_leaks_info': 'leak.tu_leaks_info_test',
    'test_acknowledge_leak_info': 'leak.acknowledge_leak_test',
    'test_output_signals': 'leak.output_signals_test',
}


def _get_test_config_from_suite_config(suite_config, config_path: str):
    """
    Получает конфигурацию теста из конфига набора по пути (например, 'leak.all_leaks_info_test').
    
    :param suite_config: SuiteConfig объект
    :param config_path: путь к атрибуту (разделённый точками)
    :return: CaseMarkers объект или None
    """
    obj = suite_config
    for attr in config_path.split('.'):
        obj = getattr(obj, attr, None)
        if obj is None:
            return None
    return obj


def pytest_collection_modifyitems(session, config, items):
    """
    1. Исключает тесты, у которых конфиг = None (тест отключён для этого набора данных)
    2. Добавляет маркеры offset и test_case_id из конфига к каждому параметризованному тесту
    3. Сортирует тесты по test_suite_name для группировки по наборам данных
    """
    selected_items = []
    deselected_items = []
    
    for item in items:
        # Проверяем, что это параметризованный тест с конфигом
        if hasattr(item, 'callspec') and 'config' in item.callspec.params:
            suite_config = item.callspec.params['config']
            
            # Получаем имя функции теста (без параметров)
            test_name = item.originalname or item.name.split('[')[0]
            
            # Получаем путь к конфигу теста
            config_path = TEST_CONFIG_MAPPING.get(test_name)
            if config_path:
                test_config = _get_test_config_from_suite_config(suite_config, config_path)
                
                # Если конфиг теста = None, исключаем тест из прогона
                if test_config is None:
                    deselected_items.append(item)
                    continue
                
                # Добавляем маркер offset
                if hasattr(test_config, 'offset') and test_config.offset is not None:
                    item.add_marker(pytest.mark.offset(test_config.offset))
                
                # Добавляем маркер test_case_id
                if hasattr(test_config, 'test_case_id') and test_config.test_case_id is not None:
                    item.add_marker(pytest.mark.test_case_id(test_config.test_case_id))
        
        selected_items.append(item)
    
    # Уведомляем pytest об исключённых тестах
    if deselected_items:
        config.hook.pytest_deselected(items=deselected_items)
    
    # Заменяем список тестов на отфильтрованный
    items[:] = selected_items

    # Сортировка тестов по test_suite_name
    def suite_key(item):
        """
        Сортировка тестов по test_suite_name (без падения на None)
        """
        test_suite_name_marker = item.get_closest_marker("test_suite_name")
        return test_suite_name_marker.args[0] if test_suite_name_marker else ""

    items.sort(key=suite_key)


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

        cfg["stand_manager"] = stand_manager
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
    uploader = AllureResultsUploader()
    logger.info("Uploading Allure results to TestOps")
    uploader.upload_allure_results()
    shutil.rmtree("allure-results")
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
