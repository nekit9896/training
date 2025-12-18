"""
Конфигурация pytest для smoke-тестов СОУ.

Этот модуль обеспечивает:
- Автоматическую генерацию параметризованных тестов из конфигураций
- Управление стендом и имитатором
- Offset-ожидание перед каждым тестом
- Интеграцию с Allure TestOps
"""

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
from constants.architecture_constants import \
    WebSocketClientConstants as WSCliConst
from infra.stand_setup_manager import StandSetupManager

# ============================================================================
#                    PYTEST КОНФИГУРАЦИЯ
# ============================================================================


def pytest_configure(config):
    """
    Инициализация состояния сессии и регистрация маркеров.
    """
    config.group_state = {
        "current_suite": None,
        "suite_start_time": None,
        "stand_manager": None,
    }

    # Регистрация кастомных маркеров
    config.addinivalue_line("markers", "test_suite_name(name): имя набора данных")
    config.addinivalue_line(
        "markers", "test_suite_data_id(id): ID набора данных в TestOps"
    )
    config.addinivalue_line("markers", "test_data_name(name): имя архива с данными")
    config.addinivalue_line(
        "markers", "offset(minutes): время запуска теста от старта имитатора"
    )
    config.addinivalue_line("markers", "test_case_id(id): ID тест-кейса в TestOps")


def pytest_collection_modifyitems(session, config, items):
    """
    Сортировка тестов по test_suite_name для группировки по наборам данных.
    """

    def suite_key(item):
        test_suite_name_marker = item.get_closest_marker("test_suite_name")
        return test_suite_name_marker.args[0] if test_suite_name_marker else ""

    items.sort(key=suite_key)
    return items


# ============================================================================
#                    ALLURE ИНТЕГРАЦИЯ
# ============================================================================


@pytest.fixture(autouse=True)
def allure_tms_link(request):
    """
    Добавляет Allure TMS-линки по test_case_id.
    """
    if test_case_id_marker := request.node.get_closest_marker("test_case_id"):
        test_case_id = test_case_id_marker.args[0]
        testops_url = os.environ.get("TESTOPS_BASE_URL")
        allure.dynamic.link(
            f"https://{testops_url}/testcases?selected_id={test_case_id}",
            name=f"TestCase-{test_case_id}",
            link_type="tms",
        )


# ============================================================================
#                    OFFSET ОЖИДАНИЕ
# ============================================================================


@pytest.fixture(autouse=True)
def offset_wait(request):
    """
    Offset-ожидание перед каждым тестом относительно старта имитатора
    """
    if offset_marker := request.node.get_closest_marker("offset"):
        offset_value = offset_marker.args[0]
        if offset_value is None:
            pytest.skip("Тест отключен в конфигурации (offset=None)")

        offset_sec = float(offset_value) * 60
        start = request.config.group_state["suite_start_time"] or 0
        elapsed = time.monotonic() - start
        to_wait = max(0, offset_sec - elapsed)
        if to_wait:
            time.sleep(to_wait)


# ============================================================================
#                    ВЫЧИСЛЕНИЕ ДЛИТЕЛЬНОСТИ ИМИТАТОРА
# ============================================================================


def compute_imitator_duration(item, current_test_suite: str) -> float:
    """
    Вычисляет длительность для имитатора (в минутах).

    Правило:
      - Собирает все тесты (item.session.items) с меткой test_suite_name == current_test_suite
      - Извлекает все значения @pytest.mark.offset(...) (в минутах)
      - Если offsets найдены: возвращает max(offsets) + IMITATOR_FINISH_DELAY задержка остановки имитатора
      - Иначе: если у текущего item есть @pytest.mark.imitator_duration — используется как fallback и логируется
      - Если ничего не найдено — pytest.fail
    """
    suite_items = [
        item
        for item in item.session.items
        if (marker := item.get_closest_marker("test_suite_name"))
        and marker.args[0] == current_test_suite
    ]

    offsets = []
    for item in suite_items:
        offset_marker = item.get_closest_marker("offset")
        if offset_marker and offset_marker.args[0] is not None:
            try:
                offsets.append(float(offset_marker.args[0]))
            except (ValueError, TypeError):
                continue

    if offsets:
        max_offset = max(offsets)
        imitator_duration = float(max_offset) + ImConst.IMITATOR_FINISH_DELAY_MINUTE
        return imitator_duration

    # fallback: если задан старый маркер imitator_duration
    if imitator_mark := item.get_closest_marker("imitator_duration"):
        imitator_duration = float(imitator_mark.args[0])
        logger.warning(
            f"[DEPRECATED] использован pytest.mark.imitator_duration()"
            f"рекомендуется убрать и полагаться на max_offset + {ImConst.IMITATOR_FINISH_DELAY_MINUTE}"
        )
        return imitator_duration

    pytest.fail(
        "Не удалось вычислить imitator_duration: в тестовом модуле одновременно отсутствуют "
        "и @pytest.mark.offset(), и pytest.mark.imitator_duration()"
    )


# ============================================================================
#                    УПРАВЛЕНИЕ ИМИТАТОРОМ
# ============================================================================


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
        # Останавливаем предыдущий имитатор
        if stand_manager := cfg["stand_manager"]:
            stand_manager.stop_imitator_wrapper()
            if not os.environ.get("RUN_WITHOUT_TESTOPS", "False").lower() == "true":
                # При запуске с TestOps удаляет данные прогона
                stand_manager.server_test_data_remover()

        # Запускаем новый имитатор
        cfg["current_suite"] = current_test_suite
        cfg["suite_start_time"] = time.monotonic() + ImConst.CORE_START_DELAY_S

        data_id_marker = item.get_closest_marker("test_suite_data_id")
        test_data_name_marker = item.get_closest_marker("test_data_name")

        if not data_id_marker or not test_data_name_marker:
            pytest.fail(
                f"Тест {item.name} не имеет обязательных маркеров "
                f"test_suite_data_id или test_data_name"
            )

        data_id = data_id_marker.args[0]
        test_data_name = test_data_name_marker.args[0]

        imitator_duration = compute_imitator_duration(item, current_test_suite)

        stand_manager = StandSetupManager(
            duration_m=imitator_duration,
            test_data_id=data_id,
            test_data_name=test_data_name,
        )
        try:
            stand_manager.setup_stand_for_imitator_run()
        except RuntimeError as error:
            pytest.exit(f"[SETUP] [ERROR] ошибка при подготовке стенда: {error}")

        imitator_thread = threading.Thread(
            target=stand_manager.start_imitator,
            name=f"imitator->{current_test_suite}",
            daemon=True,
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


# ============================================================================
#                    WEBSOCKET КЛИЕНТ
# ============================================================================


def get_ws_host() -> str:
    """Получает хост для websocket подключения."""
    instance = os.environ.get(EnvConst.STAND_NAME)
    if not instance:
        pytest.exit(f"Переменная окружения {EnvConst.STAND_NAME} не задана в .env")

    ws_host = f"{WSCliConst.SERVICE_NAME}.{WSCliConst.COMPONENT}-{instance}.{WSCliConst.ROOT_DOMAIN}"
    return ws_host


def get_token(max_retries: int = 3, backoff: float = 5.0) -> str:
    """
    Получает токен авторизации с ретраями при ошибках.

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
            logger.warning(
                f"[{attempt}/{max_retries}] KeycloakAuthError: {e}. Повтор через {backoff} сек."
            )
        except Exception as e:
            last_exc = e
            logger.warning(
                f"[{attempt}/{max_retries}] Неожиданная ошибка: {e}. Повтор через {backoff} сек."
            )

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


# ============================================================================
#                    ЗАВЕРШЕНИЕ СЕССИИ
# ============================================================================


def pytest_sessionfinish(session, exitstatus):
    """
    В завершении сессии — отправляем единый Allure-отчёт в TestOps.
    """
    uploader = AllureResultsUploader()
    logger.info("Uploading Allure results to TestOps")
    uploader.upload_allure_results()

    allure_results_dir = "allure-results"
    if os.path.exists(allure_results_dir):
        shutil.rmtree(allure_results_dir)

    project_root = os.path.dirname(os.path.abspath(__file__))
    files_for_drop = glob.glob(os.path.join(project_root, "*.tar.gz"))
    if not files_for_drop:
        logger.warning("Не нашлось архивов .tar.gz с данным для удаления")
    else:
        for file in files_for_drop:
            os.remove(file)


# ============================================================================
#                    ФИКСТУРА ДЛЯ ПАРАМЕТРОВ WS
# ============================================================================


@pytest.fixture()
def ws_params(request):
    """
    Передает параметры для websocket в тест
    """
    return request.param
