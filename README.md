# LDS Autotests

Автотесты эмулируют работу фронта: отправляют WS‑сообщения в `api-gateway` (SignalR/messagepack) и проверяют ответы бэка по “контрактам” (тем же структурам/полям, которые читает UI).

Ключевой принцип покрытия:
- **в ширину**: добавляем новые наборы данных (datasets) → повторяем набор проверок на новых “отборах”
- **в глубину**: добавляем новые проверки (scenarios) → расширяем набор контрактов/полей

## Документация (готово для Confluence/выступления)
- Для пользователей (ручные тестировщики): `docs/confluence_users.md`
- Для разработчиков автотестов: `docs/confluence_devs.md`
- План выступления на 45 минут + демо: `docs/presentation_45min.md`

## Быстрый старт (локально / для разработчиков)

### Требования
- Python 3.10+
- Доступы до стенда, Keycloak и TestOps

### Установка зависимостей

```bash
pip install -r requirements.txt
```

### Переменные окружения
Скопируйте `env.example` → `.env` и заполните значения (или задайте их в CI/CD):
- **`STAND_NAME`** — имя стенда (влияет на адреса/подготовку окружения)
- **`OPC_URL`** — для проверки доступности OPC (формат `opc.tcp://host:port`)
- **`KEYCLOAK_URL`**, **`KEYCLOAK_CLIENT_ID`**, **`KEYCLOAK_CLIENT_SECRET`**, **`KEYCLOAK_USERNAME`**, **`KEYCLOAK_PASSWORD`**
- **`TESTOPS_BASE_URL`** — базовый домен TestOps (без протокола), используется для ссылок/выгрузки
- **`SSH_USER_DEV`**, **`SSH_KEY_NAME`** — для выполнения команд на сервере стенда (setup/teardown)

## Запуск тестов

### Весь smoke

```bash
pytest tests/test_smoke.py
```

### Конкретный набор данных (suite)

```bash
pytest tests/test_smoke.py --suites=select_6
```

Можно несколько:

```bash
pytest tests/test_smoke.py --suites=select_4,select_19_20
```

### Один конкретный тест
Точный способ (nodeid):

```bash
pytest tests/test_smoke.py::TestSuiteScenarios::test_basic_info[Select_6_tn3_56km_113]
pytest tests/test_smoke.py::TestLeakScenarios::test_leaks_content[Select_19_20_tn3_75_181km_649_leak_1]
```

Быстрый способ (через `-k`):

```bash
pytest tests/test_smoke.py --suites=select_19_20 -k "test_leaks_content and leak_2"
```

## Запуск из пайпа (для пользователей)
В пайпе обычно используются:
- **`STAND_NAME`** — какой стенд прогоняем
- **`SMOKE_PATH`** — запуск smoke по suite (под капотом `pytest tests/test_smoke.py --suites=...`)
- **`TEST_PATH`** — произвольный запуск (под капотом “как есть”: `pytest ...`)

Примеры:
- `SMOKE_PATH=tests/test_smoke.py --suites=select_6`
- `TEST_PATH=pytest tests/test_smoke.py --suites=select_19_20 -k "test_leaks_content"`

## Что покрыто сейчас (datasets)
См. `test_config/datasets/`:
- `Select_6_tn3_56km_113` — стационар, 1 утечка
- `Select_7_tn3_130km_113` — стационар, 1 утечка + расширенная проверка соседних ДУ
- `Select_4_tn3_215km_113` — остановленная перекачка (STOPPED), 1 утечка
- `Select_17_tn3_75km_417` — 1 утечка (с другими окнами/объёмом)
- `Select_19_20_tn3_75_181km_649` — 2 утечки (multi‑leak)

## Как это работает (в общих чертах)
1. `test_config/datasets` автодискаверится → формируется `ALL_CONFIGS`.
2. `tests/test_smoke.py` параметризует suite‑level и leak‑level тесты по `ALL_CONFIGS`.
3. `conftest.py` группирует тесты по `test_suite_name` и при смене suite:
   - подготавливает стенд (контейнеры/redis)
   - (опционально) загружает данные из TestOps
   - стартует имитатор + core
4. Сценарии (`test_scenarios/scenarios.py`) отправляют WS запросы (как фронт) и ассертят поля ответов.
5. В конце сессии Allure результаты выгружаются в TestOps.

## Как добавить новый набор данных (покрытие “в ширину”)
1. Создать `test_config/datasets/select_XX.py` по образцу:
   - 1 утечка → `select_6.py`
   - 2 утечки → `select_19_20.py`
2. Экспортировать переменную `*_CONFIG` типа `SuiteConfig` (суффикс `_CONFIG` обязателен).
3. Запустить `pytest tests/test_smoke.py --suites=select_xx` и проверить отчёт в TestOps.
