# Руководство по составлению плана тестирования AI-агентов

> Как подготовить окружение, файлы, контракты и тест-сьюты для ATP Platform

---

## 1. Обзор процесса

```
Шаг 1: Определить цели тестирования
   ↓
Шаг 2: Спроектировать контракт (ATP Protocol)
   ↓
Шаг 3: Подготовить окружение
   ↓
Шаг 4: Написать тест-сьют (YAML)
   ↓
Шаг 5: Подготовить фикстуры и тестовые данные
   ↓
Шаг 6: Настроить адаптер
   ↓
Шаг 7: Запустить тесты и собрать базовую линию
   ↓
Шаг 8: Настроить CI/CD
```

---

## 2. Шаг 1: Определить цели тестирования

### 2.1. Категории тестов

| Категория | Что проверяем | Пример |
|-----------|-------------|--------|
| **Функциональность** | Агент решает задачу правильно | Создание файлов, обработка данных |
| **Качество** | Качество ответов/артефактов | Полнота, точность, структура |
| **Безопасность** | Нет утечек данных, инъекций | PII, секреты, prompt injection |
| **Производительность** | Скорость, стоимость | Латентность, токены, USD |
| **Надёжность** | Стабильность при повторах | Дисперсия результатов, ошибки |
| **Взаимодействие** | Работа нескольких агентов | Comparison, collaboration, handoff |
| **Теоретико-игровой** | Стратегическое поведение агента | Кооперация, эксплуатируемость, равновесие Нэша |

### 2.2. Определение приоритетов

Для каждого теста задайте:
- **Severity**: critical / high / medium / low
- **Tags**: smoke, regression, security, performance, edge_case
- **Scoring weights**: quality, completeness, efficiency, cost (сумма = 1.0)

### 2.3. Чек-лист целей

```markdown
- [ ] Какие задачи агент должен уметь решать?
- [ ] Какие артефакты ожидаются на выходе?
- [ ] Какие инструменты агент может использовать?
- [ ] Каковы ограничения: шаги, токены, бюджет, время?
- [ ] Какой уровень качества приемлем (threshold)?
- [ ] Нужны ли проверки безопасности?
- [ ] Нужно ли сравнивать несколько агентов/моделей?
- [ ] Сколько прогонов нужно для статистической значимости?
```

---

## 3. Шаг 2: Спроектировать контракт (ATP Protocol)

### 3.1. ATP Request — что получает агент

```json
{
  "version": "1.0",
  "task_id": "task_001",
  "task": {
    "description": "Описание задачи на естественном языке",
    "input_data": {
      "key": "дополнительные данные для агента"
    },
    "expected_artifacts": ["output.txt", "report.json"]
  },
  "constraints": {
    "max_steps": 10,
    "max_tokens": 50000,
    "timeout_seconds": 120,
    "allowed_tools": ["file_read", "file_write", "web_search"],
    "budget_usd": 0.50
  },
  "context": {
    "workspace_path": "/workspace",
    "environment": {}
  },
  "metadata": {
    "test_id": "test-001",
    "run_number": 1
  }
}
```

### 3.2. ATP Response — что агент возвращает

```json
{
  "version": "1.0",
  "task_id": "task_001",
  "status": "completed",
  "artifacts": [
    {
      "type": "file",
      "path": "output.txt",
      "content_type": "text/plain",
      "content": "содержимое файла"
    },
    {
      "type": "structured",
      "name": "report",
      "content_type": "application/json",
      "data": {"score": 95, "issues": []}
    }
  ],
  "metrics": {
    "total_tokens": 15000,
    "input_tokens": 5000,
    "output_tokens": 10000,
    "total_steps": 7,
    "tool_calls": 4,
    "llm_calls": 8,
    "wall_time_seconds": 45,
    "cost_usd": 0.12
  },
  "error": null
}
```

### 3.3. ATP Event — потоковые события

```json
{
  "version": "1.0",
  "task_id": "task_001",
  "timestamp": "2026-02-28T10:30:00Z",
  "sequence": 1,
  "event_type": "tool_call",
  "payload": {
    "tool_name": "file_write",
    "tool_input": {"path": "output.txt", "content": "..."},
    "tool_output": {"success": true}
  }
}
```

### 3.4. Статусы ответа

| Status | Когда |
|--------|-------|
| `completed` | Задача выполнена успешно |
| `failed` | Ошибка при выполнении |
| `timeout` | Превышен лимит времени |
| `cancelled` | Отменено пользователем |
| `partial` | Частичный результат |

### 3.5. Типы событий

| Event Type | Описание |
|-----------|---------|
| `tool_call` | Вызов инструмента агентом |
| `llm_request` | Обращение к LLM |
| `reasoning` | Шаг рассуждения |
| `error` | Ошибка |
| `progress` | Промежуточный статус |

---

## 4. Шаг 3: Подготовить окружение

### 4.1. Структура рабочей директории

```
my-agent-tests/
├── atp.config.yaml           # Конфигурация ATP
├── .env                      # API-ключи (НЕ коммитить)
├── test_suites/
│   ├── smoke.yaml            # Smoke-тесты
│   ├── functional.yaml       # Функциональные тесты
│   ├── security.yaml         # Тесты безопасности
│   └── performance.yaml      # Тесты производительности
├── fixtures/
│   ├── input_data/           # Входные данные для тестов
│   │   ├── sample.csv
│   │   └── config.json
│   └── expected/             # Эталонные результаты
│       ├── expected_output.txt
│       └── expected_report.json
├── agents/                   # Агенты для тестирования
│   ├── http_agent.py         # HTTP-агент (FastAPI)
│   ├── cli_agent.py          # CLI-агент (stdin/stdout)
│   └── requirements.txt
├── baselines/                # Сохранённые базовые линии
│   └── baseline_v1.json
└── reports/                  # Результаты тестирования
    ├── results.json
    └── report.html
```

### 4.2. Минимальный .env

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
```

### 4.3. Минимальный atp.config.yaml

```yaml
log_level: INFO
parallel_workers: 4
default_timeout: 300
runs_per_test: 1
anthropic_api_key: ${ANTHROPIC_API_KEY}
default_provider: anthropic
```

---

## 5. Шаг 4: Написать тест-сьют (YAML)

### 5.1. Структура файла

```yaml
test_suite: "имя_сьюта"           # Уникальный идентификатор
version: "1.0"
description: "Описание набора тестов"

# Значения по умолчанию (наследуются всеми тестами)
defaults:
  runs_per_test: 1                # Кол-во прогонов (1-100)
  timeout_seconds: 120            # Таймаут на тест
  constraints:
    max_steps: 10
    max_tokens: 50000
    timeout_seconds: 120
    allowed_tools: null            # null = все разрешены
    budget_usd: 0.50
  scoring:
    quality_weight: 0.4
    completeness_weight: 0.3
    efficiency_weight: 0.2
    cost_weight: 0.1               # Сумма = 1.0

# Определения агентов
agents:
  - name: "my-agent"
    type: "http"                   # Тип адаптера
    config:
      endpoint: "${API_ENDPOINT:http://localhost:8000}"
      timeout: 60

# Тесты
tests:
  - id: "test-001"                 # Уникальный ID
    name: "Название теста"
    tags: ["smoke", "critical"]
    task:
      description: "Описание задачи"
      input_data: {}
      expected_artifacts: ["output.txt"]
    constraints: {}                 # Переопределения defaults
    assertions: []                  # Проверки результатов
```

### 5.2. Доступные типы assertions

| Assertion | Evaluator | Что проверяет |
|-----------|-----------|-------------|
| `artifact_exists` | artifact | Файл существует |
| `contains` | artifact | Текст/regex в файле |
| `schema` | artifact | JSON Schema валидация |
| `behavior` | behavior | no_errors, must_use_tools, no_repeated_actions |
| `llm_eval` | llm_judge | Семантическая оценка Claude-as-judge |
| `code_exec` | code_exec | Запуск pytest/npm/custom |
| `security` | security | PII, секреты, инъекции |
| `factuality` | factuality | Проверка фактов, галлюцинации |
| `style` | style | Тон, читаемость |
| `performance` | performance | Латентность, throughput |
| `file_exists` | filesystem | Проверка файлов |
| `file_contains` | filesystem | Содержимое файлов |
| `dir_exists` | filesystem | Проверка директорий |
| `composite` | composite | Комбинирование проверок (AND/OR/NOT логика) |

### 5.3. Переменные в YAML

```yaml
# Обязательная переменная (ошибка если не установлена)
endpoint: "${API_ENDPOINT}"

# С значением по умолчанию
endpoint: "${API_ENDPOINT:http://localhost:8000}"
api_key: "${API_KEY:test_key}"
```

### 5.4. Теоретико-игровой тест-сьют

Для оценки стратегического поведения агента используется отдельный формат YAML:

```yaml
test_suite: "prisoners_dilemma_evaluation"
version: "1.0"
description: "Оценка поведения агента в итерированной дилемме заключённого"

# Конфигурация игры
game:
  name: "prisoners_dilemma"
  config:
    num_players: 2
    num_rounds: 50
    noise: 0.0           # trembling hand (0 = без шума)
    seed: 42

episodes: 20              # Кол-во эпизодов для статистики

# Тестируемый агент
agents:
  - name: "llm-agent"
    adapter: http
    config:
      endpoint: "${AGENT_ENDPOINT:http://localhost:8010}"
      timeout: 30

# Базовые стратегии для сравнения
baselines:
  - "tit_for_tat"
  - "always_cooperate"
  - "always_defect"
  - "random"

# Теоретико-игровые assertions
assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "random"
      min_ratio: 1.1         # Агент лучше случайного на 10%

  - type: game_exploitability
    config:
      max_exploitability: 0.20

  - type: game_cooperation
    config:
      min_cooperation_rate: 0.4

  - type: game_fairness
    config:
      check: strategy_consistency
      max_deviation: 0.15

# Веса оценки
scoring:
  payoff_weight: 0.30
  exploitability_weight: 0.25
  cooperation_weight: 0.25
  fairness_weight: 0.20
```

Доступные игровые assertions:

| Assertion | Что проверяет |
|-----------|-------------|
| `game_payoff` | Средняя выплата, сравнение с baseline |
| `game_exploitability` | Насколько стратегия уязвима к эксплуатации |
| `game_cooperation` | Уровень кооперации, тренд по раундам |
| `game_fairness` | Консистентность стратегии против разных оппонентов |
| `game_equilibrium` | Расстояние до равновесия Нэша |

> Полное руководство: [05-GAME-TESTING-GUIDE.md](docs/05-GAME-TESTING-GUIDE.md)

---

## 6. Шаг 5: Подготовить фикстуры

### 6.1. Workspace фикстуры

Для тестов с файловой системой создайте директорию-шаблон:

```
fixtures/workspace_basic/
├── readme.txt
├── data/
│   ├── input.csv
│   └── config.json
└── templates/
    └── report_template.md
```

Ссылка в тесте:
```yaml
task:
  workspace_fixture: "fixtures/workspace_basic"
  description: "Обработай файлы в рабочей директории"
```

### 6.2. Входные данные

```yaml
task:
  description: "Проанализируй CSV данные"
  input_data:
    csv_content: |
      name,age,city
      Alice,30,Moscow
      Bob,25,SPb
    format: "csv"
    expected_columns: ["name", "age", "city"]
```

### 6.3. Эталонные результаты

Для `contains` и `schema` assertions подготовьте ожидаемые паттерны:

```yaml
assertions:
  - type: "contains"
    config:
      path: "report.md"
      pattern: "## Summary"     # Ожидаемый заголовок
  - type: "schema"
    config:
      path: "data.json"
      schema:
        type: object
        required: ["status", "results"]
        properties:
          status: { type: string, enum: ["success", "error"] }
          results: { type: array }
```

---

## 7. Шаг 6: Настроить адаптер

### 7.1. Выбор адаптера

| Адаптер | Когда использовать | Конфиг |
|---------|-------------------|--------|
| `http` | REST API агент | endpoint, headers |
| `cli` | Скрипт stdin/stdout | command, args |
| `container` | Docker-контейнер | image, ports, volumes |
| `mcp` | MCP-сервер | transport, command/url |
| `langgraph` | LangGraph граф | module, graph |
| `crewai` | CrewAI crew | module, crew |
| `autogen` | AutoGen система | config_path, agent_name |
| `bedrock` | AWS Bedrock | model_id, region |
| `vertex` | Google Vertex AI | project_id, model_id |
| `azure_openai` | Azure OpenAI | endpoint, deployment_name |

### 7.2. Настройка через CLI

```bash
# HTTP
uv run atp test suite.yaml \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000' \
  --adapter-config='timeout=60'

# CLI
uv run atp test suite.yaml \
  --adapter=cli \
  --adapter-config='command=python' \
  --adapter-config='args=["agent.py"]'

# MCP
uv run atp test suite.yaml \
  --adapter=mcp \
  --adapter-config='transport=stdio' \
  --adapter-config='command=npx' \
  --adapter-config='args=["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]'
```

### 7.3. Настройка в YAML

```yaml
agents:
  - name: "primary"
    type: "http"
    config:
      endpoint: "${AGENT_URL:http://localhost:8000}"
      headers:
        Authorization: "Bearer ${AUTH_TOKEN}"
      timeout: 120
```

---

## 8. Шаг 7: Запуск и базовая линия

### 8.1. Первый запуск

```bash
# Валидация
uv run atp validate --suite=test_suites/smoke.yaml

# Запуск с verbose
uv run atp test test_suites/smoke.yaml -v

# Запуск с live-отображением
uv run atp test test_suites/smoke.yaml --live
```

### 8.2. Создание базовой линии

```bash
# 10 прогонов для статистически значимой базовой линии
uv run atp baseline save test_suites/functional.yaml \
  -o baselines/baseline_v1.json \
  --runs=10
```

### 8.3. Регрессионное тестирование

```bash
uv run atp baseline compare test_suites/functional.yaml \
  -b baselines/baseline_v1.json
# Использует Welch's t-test для определения регрессий
```

---

## 9. Шаг 8: CI/CD интеграция

### 9.1. GitHub Actions

```yaml
# .github/workflows/agent-tests.yml
name: Agent Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync --extra llm
      - run: |
          uv run atp test test_suites/smoke.yaml \
            --adapter=http \
            --adapter-config='endpoint=${{ secrets.AGENT_URL }}' \
            --output=junit \
            --output-file=results.xml \
            --fail-fast
      - uses: mikepenz/action-junit-report@v4
        with:
          report_paths: results.xml
```

### 9.2. Exit-коды

| Код | Значение |
|-----|---------|
| 0 | Все тесты прошли |
| 1 | Есть неудачные тесты |
| 2 | Ошибка конфигурации / файл не найден |

---

## 10. Шаг 8а: Генерация тестов с Claude Code

Если вы используете [Claude Code](https://claude.ai/code) с загруженными skills из atp-platform, доступны два ускорителя:

**`/generate-tests`** — генерация pytest-тестов для модулей ATP:
```
/generate-tests atp/evaluators/factuality.py
```
Создаёт unit-тесты с правильными fixtures, async-паттернами, AAA-структурой.

**`/generate-game-tests`** — генерация игровых сценариев:
```
/generate-game-tests prisoners_dilemma
```
Создаёт YAML game suite + pytest-тесты для проверки корректности выплат, поведения стратегий и свойств равновесия.

Оба skill работают как ускорители: понимание ручного процесса (Шаги 1-8) остаётся необходимым для настройки и интерпретации результатов.

---

## 11. Шаг 9: Каталог тестов

ATP содержит каталог готовых курированных тестовых сценариев:

```bash
# Просмотр доступных сьютов
uv run atp catalog list

# Запуск сьюта из каталога
uv run atp catalog run smoke/basic --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'
```

Используйте каталог как стартовую точку: запустите готовый сьют, изучите формат, затем адаптируйте под своего агента.

---

## 12. Шаблон плана тестирования

```markdown
# План тестирования: [Имя агента]

## 1. Цель
- Что тестируем: [описание агента]
- Версия агента: [v1.0.0]
- Дата: [YYYY-MM-DD]

## 2. Scope
- [ ] Функциональные тесты (N тестов)
- [ ] Тесты качества (N тестов)
- [ ] Тесты безопасности (N тестов)
- [ ] Тесты производительности (N тестов)
- [ ] Теоретико-игровые тесты (N сценариев)

## 3. Окружение
- Адаптер: [http/cli/mcp/...]
- Endpoint: [URL или команда]
- API-ключи: [список необходимых]
- Фикстуры: [список файлов]

## 4. Тесты
| ID | Название | Категория | Severity | Tags |
|----|---------|-----------|----------|------|
| T-001 | ... | functional | critical | smoke |
| T-002 | ... | security | high | security |

## 5. Критерии приёмки
- Все smoke-тесты: PASS
- Quality score >= 0.8
- Нет PII-утечек
- Латентность < 5s на simple tasks

## 6. Расписание
- Smoke: при каждом PR
- Full suite: ежедневно
- Baseline comparison: еженедельно
```

> **Готовый пример:** полностью рабочая лабораторная работа по сравнению двух Code Writer агентов (GPT-4o vs Claude) — [`examples/code-writer-lab/`](examples/code-writer-lab/). Включает агентов, тест-сьюты, фикстуры и пошаговые инструкции.
