class ImitatorConstants:
    TEST_SETTINGS_KEY_NAME: str = "test_settings"
    IMITATOR_FLAGS_KEY_NAME: str = "imitator_flags"
    IMITATOR_TIME_FORMAT: str = "%Y%m%dT%H%M%S"
    IMITATOR_START_DELAY_S: int = 50
    IMITATOR_FINISH_DELAY_MINUTE: float = 2.0
    IMITATOR_CHECK_CMD: str = "pgrep -f Playground"
    IMITATOR_KILL_CMD: str = "pkill -f Playground"
    IMITATOR_PATH = "/data/imitator/lds-flow-playground-csv-latest"
    IMITATOR_RUN_CMD: str = (
        f"dotnet {IMITATOR_PATH}/TN.LDS.Flow.Playground.Application.dll"
    )
    IMITATOR_LOG_FILE_NAME: str = "imitator.log"
    IMITATOR_KEY_NAME: str = "imitator_key"
    SERVER_IP_KEY_NAME: str = "server_ip"
    SANDBOX_PATH: str = "Sandbox_path"  # Удалить при переработке json_config_model.py
    SANDBOX_DATA: str = "data"
    SANDBOX_RULES: str = "rules.txt"
    SANDBOX_TAGS: str = "tags.txt"
    SOURCE_TYPE_DEF_VALUE: str = "inflow"
    SPEED_DEF_VALUE: int = 1
    NS_DEF_VALUE: int = 2
    KAFKA_OFFSET_EARLIEST: str = "earliest"
    KAFKA_POLL_TIMEOUT_S: float = 1.0
    KAFKA_SESSION_TIMEOUT_MS: int = 10000
    TEST_ID_KEY: str = "test_id"
    AUTOTEST_DATA_PATH: str = "/data/imitator/autotest_data"
    POPEN_WAIT_TIMOUT_S: int = 5
    LONG_PROCESS_TIMEOUT_S: int = 20
    CMD_STATUS_OK: str = "OK"
    CMD_STATUS_FAIL: str = "FAIL"
    REDIS_STAND_ADDRESS: str = "secret"
    CORE_START_DELAY_S: int = IMITATOR_START_DELAY_S + 20
    ENCODING_UTF_8: str = "utf-8"
    WIN_ENCODING_CP866: str = "cp866"  # Нужна только для запуска под WIN
    WIN_ENCODING_CP1251: str = "cp1251"  # Нужна только для запуска под WIN
    OS_NAME_WIN: str = "nt"

    HOST_MAP = {
        "dev1": {IMITATOR_KEY_NAME: "DEV1_", SERVER_IP_KEY_NAME: "secret"},
        "dev2": {IMITATOR_KEY_NAME: "DEV2_", SERVER_IP_KEY_NAME: "secret"},
        "dev3": {IMITATOR_KEY_NAME: "DEV3_", SERVER_IP_KEY_NAME: "secret"},
        "test1": {IMITATOR_KEY_NAME: "TEST1_", SERVER_IP_KEY_NAME: "secret"},
        "test2": {IMITATOR_KEY_NAME: "TEST2_", SERVER_IP_KEY_NAME: "secret"},
        "test3": {IMITATOR_KEY_NAME: "TEST3_", SERVER_IP_KEY_NAME: "secret"},
        "test4": {IMITATOR_KEY_NAME: "TEST4_", SERVER_IP_KEY_NAME: "secret"},
    }


class DockerConstants:
    HOSTNAME_CMD: str = "hostname"
    STOP_CMD: str = "docker stop"
    START_CMD: str = "docker start"
    CHECK_STATUS_CMD: str = "docker inspect -f '{{.State.Status}}'"
    RUNNING_STATUS: str = "running"
    EXITED_STATUS: str = "exited"
    CORE_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]
    LB_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]
    JOURNAL_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]
    WEB_APP_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]
    API_GW_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]
    REPORTS_CONTAINERS_GROUP: list = ["secret-node1", "secret-node2", "secret-node3"]


class RedisConstants:
    LB_REDIS_KEY: str = "lds-layer-builder"
    CORE_REDIS_KEY: str = "lds-core"
    REDIS_KEY_FIND_CMD: str = "docker exec -i redis-redis-01-1-1 redis-cli KEYS"
    REDIS_KEY_DEL_CMD: str = (
        "| xargs -r docker exec -i redis-redis-01-1-1 redis-cli DEL"
    )


class KeycloakClientConstants:
    TOKEN_LEEWAY: int = 30
    GRANT_TYPE: str = "password"
    KEYCLOAK_HEADERS: dict = {"Content-Type": "application/x-www-form-urlencoded"}
    TOKEN_KEY: str = "access_token"
    ISSUED_AT_KEY: str = "issued_at"
    EXPIRES_IN_KEY: str = "expires_in"


class TestOpsConstants:
    TESTOPS_UPLOAD_ENDPOINT: str = "/upload"
    TESTOPS_UPLOAD_ERROR_MSG: str = "Ошибка при загрузке файлов allure отчета"
    TESTOPS_UPLOAD_RESPONSE_MSG_KEY: str = "message"
    TESTOPS_UPLOAD_FILES_KEY: str = "files"
    POST_METHOD: str = "post"
    ALLURE_RESULTS_DIR_NAME: str = "allure-results"
    GZIP_FILE_SIGNATURE: bytes = b"\x1f\x8b"


class HTTPClientConstants:
    GET_METHOD: str = "get"
    POST_METHOD: str = "post"
    TESTOPS_UPLOAD_ENDPOINT: str = "/upload"
    TESTOPS_ATTACHMENTS_LIST_ENDPOINT: str = "/test_cases/{test_case_id}/attachments"
    TESTOPS_LOAD_ATTACHMENT_ENDPOINT: str = (
        "/test_cases/{test_case_id}/attachments/{attachment_id}?download=1"
    )
    TESTOPS_ATTACHMENTS_KEY: str = "items"
    TESTOPS_ATTACHMENT_FILENAME_KEY: str = "original_filename"
    TESTOPS_ATTACHMENT_ID_KEY: str = "id"
    TEST_ID_KEY: str = "test_id"
    IMITATOR_RUN_DATA_FILENAME: str = (
        "imitator_run_data.tar.gz"  # Название архива данных для прогона
    )


class WebSocketClientConstants:
    RS: bytes = b"\x1e"  # ASCII Record Separator
    HANDSHAKE_WAITING: float | int = 5.0
    HANDSHAKE_MESSAGE: str = '{"protocol":"messagepack","version":1}'
    WS_HUBS: str = "/hubs/ldsClientHub"
    START_INVOCATION_ID: str = 1
    DEFAULT_RECONNECT_INTERVAL: float | int = 5.0
    PING_INTERVAL: int = 3
    PING_TIMEOUT: int = 5
    CLOSE_TIMEOUT: int = 30
    DEFAULT_SIGNALR_MESSAGE_TYPE: int = 1  # invocation type
    DEFAULT_SIGNALR_MAP_HEADERS: dict = {}
    EVENT_TYPE_INDEX = 3
    INVOCATION_ID_INDEX = 2
    SERVICE_NAME = "web-app"
    COMPONENT = "lds"
    ROOT_DOMAIN = "secret"


class EnvKeyConstants:
    CONNECTION_HOST: str = "CONNECTION_HOST"
    KEYCLOAK_URL: str = "KEYCLOAK_URL"
    KEYCLOAK_CLIENT_ID: str = "KEYCLOAK_CLIENT_ID"
    KEYCLOAK_CLIENT_SECRET: str = "KEYCLOAK_CLIENT_SECRET"
    KEYCLOAK_USERNAME: str = "KEYCLOAK_USERNAME"
    KEYCLOAK_PASSWORD: str = "KEYCLOAK_PASSWORD"
    TESTOPS_BASE_URL: str = "TESTOPS_BASE_URL"
    SSH_KEY_NAME: str = "SSH_KEY_NAME"
    SSH_USER_DEV: str = "SSH_USER_DEV"
    STAND_NAME: str = "STAND_NAME"
    DATA_PATH: str = "DATA_PATH"
    OPC_URL: str = "OPC_URL"
