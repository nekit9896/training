# Инструкция для разработчиков автотестов

Разработчик автотестов — это инженер, который:
- понимает архитектуру setup/autotests/teardown
- может добавить новый dataset (покрытие “в ширину”)
- может добавить новую проверку/сценарий (покрытие “в глубину”)
- может разобраться, почему тест упал (диагностика по логам/Allure/TestOps)

## 0) TL;DR (архитектура в 8 строк)
- Один тестовый модуль: `tests/test_smoke.py` (suite‑level + leak‑level тесты).
- Параметризация идёт от `test_config/datasets.ALL_CONFIGS` (автодискавер).
- `conftest.py`:
  - добавляет `--suites` фильтр
  - навешивает `offset`/`test_case_id` маркеры из datasets
  - группирует тесты по `test_suite_name`
  - **перезапускает стенд/имитатор при смене suite**
  - в конце выгружает Allure в TestOps
- Сценарии тестов: `test_scenarios/scenarios.py` (WS вызовы + ассёрты по полям).
- WS клиент: `clients/websocket_client.py` (SignalR + messagepack).
- Setup стенда: `infra/stand_setup_manager.py` (контейнеры/redis/имитатор/данные).

## 1) Жизненный цикл прогона: setup → autotests → teardown

### 1.1 Коллекция тестов (pytest collection)
Источник параметров:
- `test_config/datasets/__init__.py` сканирует `test_config/datasets/*.py`
- ищет атрибуты с суффиксом `_CONFIG`
- добавляет найденные `SuiteConfig` в `ALL_CONFIGS`

В `tests/test_smoke.py` из `ALL_CONFIGS` генерируются:
- `SUITE_PARAMS`: один параметр на набор
- `LEAK_PARAMS`: один параметр на утечку (для multi‑leak — несколько)

### 1.2 Фильтрация по `--suites` и отключённые тесты
В `conftest.py` реализовано:
- `--suites=select_4,select_19_20` — фильтр по подстроке имени suite (`test_suite_name`)
- отсеивание тестов, где конфиг теста = `None` (то есть тест отключён для набора)

### 1.3 Группировка по suite и расчёт длительности имитатора
Ключевые идеи:
- каждый item имеет маркеры:
  - `test_suite_name`
  - `test_suite_data_id`
  - `test_data_name`
- `offset` маркер навешивается автоматически из `CaseMarkers.offset`
- длительность имитатора считается как:
  - `max(offsets в suite)` + `IMITATOR_FINISH_DELAY_MINUTE`

### 1.4 Setup/teardown выполняются при смене набора данных
В `conftest.py` в `pytest_runtest_setup`:
- если текущий `test_suite_name` отличается от предыдущего:
  - останавливаем старый имитатор (если был)
  - (опционально) чистим данные прогона через TestOps
  - поднимаем стенд под новый набор:
    - останов контейнеров lds
    - чистка Redis ключей
    - старт сервисов (LB, journals, web-app, api-gw, reports)
  - проверяем доступность OPC
  - стартуем имитатор и core
  - сохраняем `imitator_start_time` в group_state

В `pytest_runtest_teardown`:
- если следующий тест уже другого suite — останавливаем имитатор/чистим данные.

## 2) Инфраструктурная внутрянка

Этот раздел про то, **как именно** автотесты управляют стендом: где берутся данные, как выполняются команды на удалённом сервере, что стартует/стопается и в каком порядке.

### 2.1 Компоненты (кто за что отвечает)
- **`infra/stand_setup_manager.py::StandSetupManager`**: оркестратор setup/teardown для одного suite.
  - выбирает сервер стенда по `STAND_NAME` (через `HOST_MAP`)
  - создаёт клиентов для стенда и Redis
  - (опционально) скачивает/загружает данные набора на стенд через TestOps
  - поднимает сервисы и запускает имитатор + core
  - отдаёт `start_time` имитатора (datetime) в `conftest.py`
- **`infra/imitator_data_uploader.py::ImitatorDataUploader`**: доставка данных прогона на стенд.
  - скачивает архив данных из TestOps по `suite_data_id` + имени файла `archive_name`
  - проверяет архив локально (runner)
  - копирует архив на удалённый сервер (scp)
  - распаковывает во временную директорию и валидирует структуру
- **`infra/cmd_generator.py::ImitatorCmdGenerator`** + **`TimeProcessor`**: генерация команды запуска имитатора и расчёт `startTime/stopTime`.
- **`infra/imitator_manager.py::ImitatorManager`**: запуск/логирование/останов имитатора как “длинного процесса”.
- **`infra/docker_manager.py::DockerContainerManager`**: stop/start групп контейнеров и проверка статусов.
- **`infra/redis_manager.py::RedisCleaner`**: чистка ключей Redis для стенда.
- **`clients/subprocess_client.py::SubprocessClient`**: транспорт для выполнения команд:
  - `run_cmd()` → разовые команды (ssh wrapper)
  - `exec_popen()` → длинные процессы (например запуск имитатора)
  - умеет работать на Windows (добавляет `ssh -i <SSH_KEY_NAME> ...`)
- **`clients/http_client.py::HttpClient`**: HTTP запросы в TestOps (attachments list/download).

### 2.2 Что именно приходит из datasets в инфраструктуру
`SuiteConfig` содержит два ключевых поля, которые *инфраструктура* использует напрямую:
- **`suite_data_id`**: id тест‑кейса в TestOps, откуда берём attachments (архив данных)
- **`archive_name`**: имя файла вложения (`.tar.gz`) внутри TestOps, которое нужно скачать

В `tests/test_smoke.py` они попадают в pytest маркеры:
- `test_suite_data_id(suite_data_id)`
- `test_data_name(archive_name)`

А в `conftest.py` при смене suite эти значения читаются и передаются в `StandSetupManager(duration_m, test_data_id, test_data_name)`.

### 2.3 Поток setup (пошагово)
Ниже фактическая последовательность действий (см. `StandSetupManager.setup_stand_for_imitator_run()`):

1) **(опционально) Загрузка данных с TestOps на стенд**  
   Если `RUN_WITHOUT_TESTOPS != true`:
   - `ImitatorDataUploader.upload_with_confirm()`:
     - `HttpClient.get_attachments_list_by_test_case_id(test_data_id)`
     - выбрать attachment по `original_filename == archive_name`
     - скачать bytes через `HttpClient.get_test_case_attachment_by_id(test_case_id, attachment_id)`
     - сохранить архив на runner (рабочая директория)
     - проверить архив на runner: наличие `rules.txt`, `tags.txt`, директории `data/`
     - создать временную директорию на сервере стенда (`mkdir -p /data/imitator/autotest_data/<unique>/`)
     - скопировать архив на стенд (`scp ...`)
     - проверить архив на стенде (`tar -tzf ...`)
     - распаковать (`tar -xvzf ... -C ...`)
     - проверить структуру распаковки (`[ -d data ] && [ -f rules.txt ] && [ -f tags.txt ]`)

2) **Сброс окружения стенда**
   - `DockerContainerManager.stop_all_lds_containers()`
   - `RedisCleaner.delete_keys_with_check()`:
     - удаляет ключи вида `lds-layer-builder:<stand>` и `lds-core:<stand>` через `redis-cli` внутри docker

3) **Поднятие сервисов (без core)**
   - старт: layer-builder → journals → web-app → api-gw → reports
   - каждый шаг: docker start + проверка `docker inspect` на `running`

4) **Проверка доступности OPC**
   - `StandSetupManager.check_opc_server_status()`
   - важно: проверка выполняется **с сервера стенда**, команда через `/dev/tcp/<host>/<port>` (bash)

5) **Запуск имитатора + core**
   - `ImitatorCmdGenerator` собирает команду `dotnet ...Playground...` с флагами:
     - `--source`, `--rules`, `--sourceTagTypes` (пути к данным)
     - `--startTime`, `--stopTime` (из `TimeProcessor`)
     - `--opcua`, `--ns`, `--target`, `--speed` …
   - `ImitatorManager.run_imitator()` запускает команду как “длинный процесс” (`exec_popen`)
   - `ImitatorManager.log_imitator_stdout()` пишет stdout имитатора в `imitator.log`
   - `DockerContainerManager.start_lds_core_containers()` поднимает core

### 2.4 Поток teardown (пошагово)
Teardown делится на два уровня: “между suite” и “в конце сессии”.

- **Между suite (в `conftest.py`)**:
  - `StandSetupManager.stop_imitator_wrapper()`:
    - ждёт завершения процесса имитатора и затем принудительно останавливает, если нужно
    - при необходимости делает `pkill -f Playground`
  - если `RUN_WITHOUT_TESTOPS != true`:
    - `StandSetupManager.server_test_data_remover()` → удаляет временную директорию с данными на стенде

- **В конце сессии (в `pytest_sessionfinish`)**:
  - выгрузка Allure результатов в TestOps
  - чистка `allure-results` и временных `.tar.gz` на runner

### 2.5 Переменные окружения (инфраструктурный минимум)
- **`STAND_NAME`**: выбор стенда/адресов (через `HOST_MAP`).
- **`SSH_USER_DEV`**, **`SSH_KEY_NAME`**: выполнение команд ssh/scp.
- **`TESTOPS_BASE_URL`**: скачивание вложений (datasets) и выгрузка allure-results.
- **`OPC_URL`**: проверка доступности OPC на стенде.
- **`RUN_WITHOUT_TESTOPS=true`**: режим без скачивания/удаления данных через TestOps (используется уже подготовленная директория/архив).

### 2.6 Типовые точки отказа именно инфраструктуры
- **TestOps attachments**: нет вложения с именем `archive_name` или `suite_data_id` неверный → uploader не найдёт файл.
- **Архив данных**: отсутствуют `data/`, `rules.txt`, `tags.txt` → fail на валидации (локально или на стенде).
- **scp/ssh**: неверный ключ/пользователь/доступ → fail на копировании/командах.
- **docker**: контейнеры не переходят в `running`/`exited` → `DockerContainerManager` поднимет `RuntimeError`.
- **redis**: ключи не удаляются → тест стартует в “грязном” состоянии.
- **OPC недоступен**: `OPC_URL` некорректный или стенд не видит хост/порт.
- **имитатор**: процесс не стартует или не пишет в stdout → см. `imitator.log` и команды `pgrep/pkill`.

## 3) Как устроены WS “контракты” (sync vs subscribe)

### 3.1 WebSocketClient: SignalR invocation
`clients/websocket_client.py` реализует:
- `invoke(target, args)`:
  - инкрементирует `invocation_id`
  - отправляет messagepack по протоколу SignalR
- `receive_by_invocation_id(id)`:
  - используется для синхронных запросов (“как REST”)
- `receive_by_type(message_type)`:
  - используется для подписок (асинхронный поток событий)

### 3.2 Утилиты для сценариев
`utils/helpers/ws_test_utils.py`:
- `connect_and_get_msg()` — invoke + ждать ответ по invocation_id
- `connect_and_subscribe_msg()` — invoke + ждать первое сообщение нужного типа
- `connect_and_get_parsed_msg_by_tu_id()` — пример подписки с фильтрацией по tuId

### 3.3 Парсинг сообщений
`utils/helpers/ws_message_parser.py`:
- ищет payload с `replyStatus`
- парсит reply в типизированные структуры (через `dacite`)
- содержит хуки конвертации времени и UUID

## 4) Где “лежит покрытие”: datasets vs scenarios

### 4.1 Покрытие “в ширину” = datasets
Добавили новый набор данных → получили новый suite прогонов и повторили тот же набор проверок.

В datasets задаётся:
- набор метаданных (suite_name, suite_data_id, archive_name)
- список активных тестов (через `CaseMarkers` или `None`)
- параметры утечек, интервалы, ожидания и допустимые отклонения

### 4.2 Покрытие “в глубину” = scenarios
Добавили новую проверку в `test_scenarios/scenarios.py` → получили новый тип контракта/полей.

## 5) Как добавить новый dataset (suite)
1) Создать `test_config/datasets/select_XX.py` по образцу.
2) Экспортировать переменную `*_CONFIG` типа `SuiteConfig`.
3) Для single‑leak:
   - заполнить `leak=LeakTestConfig(...)`
4) Для multi‑leak:
   - заполнить `leaks=[LeakTestConfig(...), ...]`
5) В `CaseMarkers` обязательно:
   - `test_case_id` (TMS id)
   - `offset` (минуты)

Проверка:
- `pytest tests/test_smoke.py --suites=select_xx -q`
- убедиться, что тесты сгруппированы по suite и имитатор не падает по длительности.

## 6) Как добавить новую проверку (новый тест/сценарий)

### 6.1 Добавить сценарий
- В `test_scenarios/scenarios.py` добавить новую `async def ...`
- Внутри использовать `ws_test_utils` для invoke/subscribe
- Ассёрты делать через `StepCheck`/`SoftAssertions`

### 6.2 Добавить pytest‑тест
- В `tests/test_smoke.py` добавить метод в `TestSuiteScenarios` или `TestLeakScenarios`.
- Привязать к конфигу:
  - suite-level → поле в `SuiteConfig`
  - leak-level → поле в `LeakTestConfig`

### 6.3 Подключить маркеры (важно!)
В `conftest.py` обновить маппинги:
- `SUITE_LEVEL_TEST_MAPPING` или `LEAK_LEVEL_TEST_MAPPING`

Зачем: чтобы автоматически навешивались `offset` и `test_case_id` из datasets.

## 7) Teardown и выгрузка отчёта
В `conftest.py` в `pytest_sessionfinish`:
- выгружаются `allure-results` в TestOps
- затем локальные `allure-results` удаляются

Если нужно прогонять локально “без TestOps”:
- `RUN_WITHOUT_TESTOPS=true` (часть логики загрузки/чистки данных отключится)

## 8) Типовые причины падений и что проверять
- Token/Keycloak:
  - env `KEYCLOAK_*` корректны
  - сеть до Keycloak доступна
- OPC недоступен:
  - `OPC_URL` корректный (формат `opc.tcp://host:port`)
  - стендовый сервер видит host/port
- Нет сообщений по WS:
  - проверять что поднят `api-gateway`
  - проверить `STAND_NAME` и доменную часть
  - увеличить timeout, если стенд перегружен
- Не вычислилась длительность имитатора:
  - убедиться, что в suite есть хотя бы один `offset`


