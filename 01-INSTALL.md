# ATP Platform: Установка, настройка и тестирование

> Пошаговое руководство для работы с Agent Test Platform (atp-platform)

---

## 1. Системные требования

| Компонент | Требование |
|-----------|-----------|
| Python | >= 3.12 |
| Менеджер пакетов | uv (НЕ pip) |
| ОС | macOS / Linux / Windows (WSL) |
| Docker | Опционально (для container adapter) |
| API-ключи | Anthropic / OpenAI (для LLM evaluator) |

### Установка uv (если ещё не установлен)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Установка ATP Platform

### 2.1. Клонирование и переход в проект

```bash
cd /path/to/all_ai_orchestrators/atp-platform
```

### 2.2. Установка зависимостей

```bash
# Минимальная установка (core + CLI)
uv sync

# Полная установка (все extras)
uv sync --all-extras

# Конкретные extras по необходимости
uv sync --extra cloud       # boto3, google-cloud, openai (все облачные адаптеры)
uv sync --extra bedrock     # только AWS Bedrock
uv sync --extra vertex      # только Google Vertex AI
uv sync --extra azure-openai # только Azure OpenAI
uv sync --extra dashboard   # FastAPI dashboard + benchmark/tournament API
uv sync --extra enterprise  # SSO/SAML, Redis-бэкенд для dashboard
uv sync --extra analytics   # аналитика dashboard (трекинг стоимости, Excel-экспорт)
uv sync --extra llm         # anthropic SDK (для LLM evaluator)
uv sync --extra tui         # Terminal UI
uv sync --extra all         # всё сразу
```

> **Примечание:** `game-environments` и `atp-games` — это workspace-члены, устанавливаются автоматически при `uv sync`. Отдельного `--extra games` нет.

### 2.3. Проверка установки

```bash
uv run atp version
uv run atp list-agents      # список доступных адаптеров
```

Ожидаемый вывод `list-agents`:
```
Available adapters:
  http          HTTP/HTTPS REST endpoints
  cli           Command-line agents (stdin/stdout)
  container     Docker containers
  langgraph     LangGraph framework
  crewai        CrewAI framework
  autogen       AutoGen framework
  mcp           Model Context Protocol
  bedrock       AWS Bedrock
  vertex        Google Vertex AI
  azure_openai  Azure OpenAI
```

---

## 3. Настройка

### 3.1. Конфигурационный файл

Создайте `atp.config.yaml` в корне рабочей директории:

```yaml
# atp.config.yaml
log_level: INFO
parallel_workers: 4
default_timeout: 300
fail_fast: false
sandbox_enabled: false
runs_per_test: 1

# LLM (для llm_eval assertions)
anthropic_api_key: ${ANTHROPIC_API_KEY}
default_llm_model: claude-sonnet-4-20250514
default_provider: anthropic
max_retries: 3
request_timeout: 60

# Dashboard (опционально)
dashboard_host: 127.0.0.1
dashboard_port: 8080
dashboard_debug: false
```

### 3.2. Переменные окружения

```bash
# Обязательные (если используете LLM evaluator)
export ANTHROPIC_API_KEY="sk-ant-..."
# или
export OPENAI_API_KEY="sk-..."

# Опциональные — ядро
export ATP_LOG_LEVEL=DEBUG
export ATP_PARALLEL_WORKERS=8
export ATP_FAIL_FAST=true
export ATP_DEFAULT_TIMEOUT=300
export ATP_SANDBOX_ENABLED=false

# Опциональные — аутентификация dashboard
export ATP_SECRET_KEY="your-jwt-secret"          # Обязательно в production
export ATP_DATABASE_URL="sqlite:///atp.db"       # SQLite по умолчанию, поддерживает PostgreSQL
export ATP_DISABLE_AUTH=false                     # true только для разработки
export ATP_GITHUB_CLIENT_ID="..."                # GitHub OAuth OIDC
export ATP_GITHUB_CLIENT_SECRET="..."
export ATP_TOKEN_EXPIRE_MINUTES=60
export ATP_CORS_ORIGINS=""

# Опциональные — rate limiting
export ATP_RATE_LIMIT_ENABLED=true
export ATP_RATE_LIMIT_DEFAULT="60/minute"
export ATP_RATE_LIMIT_AUTH="5/minute"
export ATP_RATE_LIMIT_API="120/minute"
export ATP_RATE_LIMIT_UPLOAD="10/minute"
export ATP_RATE_LIMIT_STORAGE="memory://"         # или redis://host:port

# Опциональные — batch и upload
export ATP_BATCH_MAX_SIZE=10
export ATP_UPLOAD_MAX_SIZE_MB=1
```

### 3.3. Приоритет конфигурации

```
CLI флаги > Переменные окружения (ATP_*) > atp.config.yaml > Значения по умолчанию
```

---

## 4. Первый запуск

### 4.1. Быстрый старт (quickstart)

```bash
uv run atp quickstart
```

Создаёт минимальный проект с `atp-suite.yaml` и примером smoke-теста — самый быстрый способ начать.

### 4.2. Инициализация проекта (полная)

```bash
uv run atp init
```

Создаёт полную начальную структуру с примерами.

### 4.3. Валидация тест-сьюта

```bash
uv run atp validate --suite=examples/test_suites/01_smoke_tests.yaml
```

### 4.4. Просмотр тестов без запуска

```bash
uv run atp test examples/test_suites/01_smoke_tests.yaml --list-only
```

### 4.5. Запуск smoke-тестов

```bash
# Против HTTP-агента
uv run atp test examples/test_suites/01_smoke_tests.yaml \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'

# Против CLI-агента
uv run atp test examples/test_suites/01_smoke_tests.yaml \
  --adapter=cli \
  --adapter-config='command=python' \
  --adapter-config='args=["examples/demo_agent.py"]'
```

---

## 5. Запуск тестов ATP Platform

### 5.1. Внутренние тесты платформы (pytest)

```bash
# Все тесты с покрытием
uv run pytest tests/ -v --cov=atp --cov-report=term-missing

# Только unit-тесты
uv run pytest tests/unit -v

# Быстрые тесты (без slow-маркера)
uv run pytest tests/ -v -m "not slow"

# Конкретный модуль
uv run pytest tests/unit/loader -v
uv run pytest tests/unit/evaluators -v

# HTML-отчёт о покрытии
uv run pytest --cov=atp --cov-report=html
# Открыть: htmlcov/index.html
```

### 5.2. Линтинг и форматирование

```bash
uv run ruff format .          # Форматирование
uv run ruff check .           # Проверка стиля
uv run ruff check . --fix     # Авто-исправление
pyrefly check                 # Проверка типов
```

---

## 6. Продвинутые сценарии запуска

### 6.1. Множественные прогоны со статистикой

```bash
uv run atp test suite.yaml --runs=5 --parallel=4
# Выводит: mean, std, median, 95% CI, p-value
```

### 6.2. Базовые линии и регрессия

```bash
# Сохранить базовую линию
uv run atp baseline save suite.yaml -o baseline.json --runs=10

# Сравнить с базовой линией (Welch's t-test)
uv run atp baseline compare suite.yaml -b baseline.json
```

### 6.3. Отчёты

```bash
# JSON-отчёт
uv run atp test suite.yaml --output=json --output-file=results.json

# JUnit XML (для CI/CD)
uv run atp test suite.yaml --output=junit --output-file=results.xml
```

> **Примечание**: CLI поддерживает форматы `console`, `json` и `junit`.
> HTML-отчёты генерируются через Python SDK или reporter API.

### 6.4. Фильтрация по тегам

```bash
# Только smoke-тесты
uv run atp test suite.yaml --tags=smoke

# Исключить медленные тесты
uv run atp test suite.yaml --tags='!slow'

# Комбинация
uv run atp test suite.yaml --tags=smoke,critical
```

### 6.5. Dashboard

```bash
uv run atp dashboard
# Открыть: http://127.0.0.1:8080
```

Dashboard включает:
- **Страницы**: Benchmarks, Runs (список + детали), Leaderboard, Games, Suites, Analytics
- **Обновления в реальном времени** через HTMX auto-refresh на страницах деталей run
- **Аутентификация**: GitHub OAuth (OIDC) + Device Flow для CLI-логина
- **Авторизация**: JWT-токены, RBAC (первый пользователь автоматически получает роль admin)
- **Multi-tenant** поддержка с изоляцией данных по тенантам
- **Rate limiting** (slowapi): настраивается по endpoint через переменные `ATP_RATE_LIMIT_*`

**Benchmark API** (REST):
```bash
# Создать бенчмарк
curl -X POST http://localhost:8080/api/v1/benchmarks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "my-bench", "suite": {...}}'

# Запустить run
curl -X POST http://localhost:8080/api/v1/runs \
  -d '{"benchmark_id": "...", "agent_name": "my-agent"}'

# Получить следующую задачу (pull-модель)
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/next-task

# Отправить результат
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/submit \
  -d '{"score": 0.95, "response": {...}}'

# Стриминг событий (макс. 1000 на run)
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/events \
  -d '[{"event_type": "progress", "payload": {...}}]'

# Таблица лидеров
curl http://localhost:8080/api/v1/leaderboard
```

**Webhooks**: настройте `webhook_url` на бенчмарке для получения POST-уведомлений при завершении run (защита от SSRF, retry с backoff).

### 6.6. Game-Theoretic оценка

```bash
# Запуск игрового сценария
uv run atp game run test_suites/game_prisoners_dilemma.yaml

# Список доступных игр
uv run atp game list
# prisoners_dilemma, stag_hunt, battle_of_sexes,
# public_goods, auction, colonel_blotto, congestion, el_farol_bar

# Информация об игре
uv run atp game info prisoners_dilemma

# Турнир (все стратегии друг против друга)
uv run atp game tournament test_suites/game_prisoners_dilemma.yaml

# Таблица перекрёстных результатов
uv run atp game crossplay test_suites/game_prisoners_dilemma.yaml
```

Отчёт включает: средние выплаты, уровень кооперации, эксплуатируемость, расстояние до равновесия Нэша. Формат отчёта — `game` (GameReporter), поддерживает JSON, HTML и CSV-экспорт.

> Подробнее: [05-GAME-TESTING-GUIDE.md](docs/05-GAME-TESTING-GUIDE.md)

### 6.7. Каталог тестов

```bash
# Просмотр каталога готовых тестовых сьютов
uv run atp catalog list

# Информация о конкретном сьюте
uv run atp catalog info smoke/basic

# Запуск сьюта из каталога
uv run atp catalog run smoke/basic \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'

# Публикация своего сьюта в каталог
uv run atp catalog publish test_suites/my_suite.yaml
```

Каталог содержит курированные тестовые сценарии (smoke, functional, security) — удобная стартовая точка перед написанием собственных тестов.

---

### 6.8. Дополнительные CLI-команды

```bash
# Сравнение нескольких моделей/агентов
uv run atp compare suite.yaml --agents=agent1,agent2

# Оценка стоимости запуска
uv run atp estimate suite.yaml

# Генерация тест-сьютов
uv run atp generate

# Бенчмарки
uv run atp benchmark

# Управление трейсами
uv run atp traces list
uv run atp replay <trace-id>

# Плагины
uv run atp plugins list

# Terminal UI (требует [tui] extra)
uv run atp tui

# Управление бюджетом (трекинг стоимости и лимиты)
uv run atp budget

# Эксперименты (A/B-тестирование, сравнения)
uv run atp experiment

# Анализ трендов (обнаружение постепенных регрессий)
uv run atp trend

# Синхронизация сьютов с удалённым сервером
uv run atp push suite.yaml --server=https://atp.example.com
uv run atp pull --server=https://atp.example.com
uv run atp sync --server=https://atp.example.com
```

### 6.9. SDK (программный доступ)

ATP предоставляет Python SDK (`atp-platform-sdk` на PyPI) для участников бенчмарков и программной интеграции:

```bash
uv add atp-platform-sdk
```

**Async-клиент:**
```python
from atp_sdk import AsyncATPClient

async with AsyncATPClient(base_url="http://localhost:8080") as client:
    # Запустить benchmark run
    run = await client.start_run(benchmark_id="bench-001", agent_name="my-agent")

    # Получать задачи и отправлять результаты
    async for task in run:
        result = await my_agent(task)
        await run.submit(score=result.score, response=result.data)

    # Проверить статус
    status = await run.status()
    print(f"Итоговый скор: {status.total_score}")
```

**Синхронная обёртка:**
```python
from atp_sdk import ATPClient

client = ATPClient(base_url="http://localhost:8080")
run = client.start_run_sync(benchmark_id="bench-001", agent_name="my-agent")

# Batch API: получить N задач сразу
tasks = run.next_batch_sync(n=5)
for task in tasks:
    result = my_agent(task)
    run.submit_sync(score=result.score, response=result.data)
```

**Возможности:**
- `BenchmarkRun` итератор с `submit()`, `status()`, `cancel()`
- Стриминг событий: `run.emit(event_type="progress", payload={...})`
- Batch API: `next_batch(n)` для получения нескольких задач
- Device Flow авторизация для CLI-логина
- Встроенная логика retry с экспоненциальным backoff

---

## 7. Типичные проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| `ModuleNotFoundError: anthropic` | Не установлен extra `llm` | `uv sync --extra llm` |
| `ANTHROPIC_API_KEY not set` | Нет API-ключа | `export ANTHROPIC_API_KEY=sk-ant-...` |
| `Connection refused` на endpoint | Агент не запущен | Запустите агент на указанном порту |
| `Timeout` при тестировании | Мало времени | Увеличьте `timeout_seconds` в suite |
| `ValidationError: Duplicate test ID` | Два теста с одинаковым id | Сделайте id уникальными |
| `Scoring weights must sum to 1.0` | Неверные веса | Проверьте quality+completeness+efficiency+cost=1.0 |
| Dashboard не запускается | Нет extra `dashboard` | `uv sync --extra dashboard` |
| `game-environments not found` | Workspace не синхронизирован | `uv sync` (game-environments + atp-games подтягиваются автоматически как workspace-члены) |
| `ModuleNotFoundError: atp_sdk` | Не установлен SDK | `uv add atp-platform-sdk` (или `uv sync --extra all`) |

---

## 8. Структура проекта (справка)

```
atp-platform/
├── atp/                           # Главный namespace (symlinks + локальные модули)
│   ├── cli/                       # CLI-команды (entry point)
│   ├── runner/                    # Оркестрация тестов, sandbox
│   ├── evaluators/                # 13 типов проверок результатов
│   ├── reporters/                 # 5 форматов отчётов (console, JSON, JUnit, HTML, game)
│   ├── baseline/                  # Управление базовыми линиями, обнаружение регрессий
│   ├── benchmarks/                # Бенчмарк-сьюты
│   ├── catalog/                   # Браузер каталога тестов
│   ├── generator/                 # Генерация тест-сьютов
│   ├── plugins/                   # Экосистема плагинов
│   ├── sdk/                       # Программный SDK
│   ├── tracing/                   # Воспроизведение трейсов
│   ├── tui/                       # Terminal UI (опционально)
│   ├── performance/               # Профилирование, кэширование
│   └── mock_tools/                # Mock-сервер инструментов
│
├── packages/                      # Извлечённые workspace-пакеты
│   ├── atp-core/                  # Протокол, загрузчик, скоринг, статистика, streaming, chaos
│   ├── atp-adapters/              # 10 адаптеров агентов (http, cli, container, langgraph, crewai, autogen, mcp, bedrock, vertex, azure_openai) + SDK-pull-адаптер
│   ├── atp-dashboard/             # FastAPI бэкенд, benchmark/tournament API, auth, MCP tournament-сервер
│   └── atp-sdk/                   # Python SDK (PyPI: atp-platform-sdk) для участников бенчмарков
│
├── game-environments/             # Автономная библиотека теории игр (8 игр, 25+ стратегий)
├── atp-games/                     # ATP-плагин для теоретико-игровой оценки
│
├── tests/                         # 80%+ покрытие
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── examples/
│   └── test_suites/               # 20+ примеров YAML test suites
├── docs/                          # Документация
├── deploy/                        # Конфигурации деплоя
└── pyproject.toml                 # Зависимости и конфигурация (uv workspace)
```
