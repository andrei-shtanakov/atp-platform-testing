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
uv sync --extra cloud       # boto3, google-cloud, openai
uv sync --extra dashboard   # FastAPI dashboard
uv sync --extra llm         # anthropic SDK (для LLM evaluator)
uv sync --extra tui         # Terminal UI
uv sync --extra analytics   # Excel export
```

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
```

### 3.2. Переменные окружения

```bash
# Обязательные (если используете LLM evaluator)
export ANTHROPIC_API_KEY="sk-ant-..."
# или
export OPENAI_API_KEY="sk-..."

# Опциональные
export ATP_LOG_LEVEL=DEBUG
export ATP_PARALLEL_WORKERS=8
export ATP_FAIL_FAST=true
```

### 3.3. Приоритет конфигурации

```
CLI флаги > Переменные окружения (ATP_*) > atp.config.yaml > Значения по умолчанию
```

---

## 4. Первый запуск

### 4.1. Инициализация проекта

```bash
uv run atp init
```

Создаёт начальную структуру с примерами.

### 4.2. Валидация тест-сьюта

```bash
uv run atp validate --suite=examples/test_suites/01_smoke_tests.yaml
```

### 4.3. Просмотр тестов без запуска

```bash
uv run atp test examples/test_suites/01_smoke_tests.yaml --list-only
```

### 4.4. Запуск smoke-тестов

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

# HTML-отчёт (самодостаточный файл)
uv run atp test suite.yaml --output=html --output-file=report.html

# JUnit XML (для CI/CD)
uv run atp test suite.yaml --output=junit --output-file=results.xml
```

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

### 6.6. Game-Theoretic оценка

```bash
uv run atp game examples/test_suites/11_game_prisoners_dilemma.yaml
```

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

---

## 8. Структура проекта (справка)

```
atp-platform/
├── atp/
│   ├── cli/              # CLI-команды (entry point)
│   ├── core/             # Настройки, безопасность, телеметрия
│   ├── protocol/         # ATP Protocol: Request/Response/Event
│   ├── loader/           # Парсинг YAML test suites
│   ├── runner/           # Оркестрация выполнения тестов
│   ├── adapters/         # 10 адаптеров для подключения агентов
│   ├── evaluators/       # 11 типов проверок результатов
│   ├── reporters/        # 4 формата отчётов
│   ├── scoring/          # Агрегация оценок
│   ├── statistics/       # Статистический анализ (mean, CI, t-test)
│   ├── baseline/         # Управление базовыми линиями
│   ├── dashboard/        # Web UI (FastAPI)
│   ├── analytics/        # Трекинг стоимости
│   ├── benchmarks/       # Бенчмарк-сьюты
│   ├── chaos/            # Хаос-тестирование
│   ├── tracing/          # Запись и воспроизведение трейсов
│   └── sdk/              # Python SDK для программного доступа
├── tests/
│   ├── unit/             # ~70% тестов
│   ├── integration/      # ~20% тестов
│   ├── e2e/              # ~10% тестов
│   └── fixtures/         # Тестовые данные
├── examples/
│   └── test_suites/      # 20+ примеров YAML test suites
├── docs/                 # Документация
└── pyproject.toml        # Зависимости и конфигурация
```
