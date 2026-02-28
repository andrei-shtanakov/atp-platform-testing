# Пример: План тестирования Code Review Agent

> Полный пример плана тестирования AI-агента для ревью кода на ATP Platform

---

## 1. Цель

**Агент**: Code Review Agent — AI-агент, выполняющий автоматическое ревью Python-кода.

**Что делает агент**:
- Принимает путь к файлу или diff
- Анализирует код на баги, стиль, безопасность, производительность
- Возвращает структурированный отчёт с замечаниями и рекомендациями

**Версия**: v1.0.0
**Модель**: Claude Sonnet 4
**Интерфейс**: HTTP REST API (POST /review)

---

## 2. Scope тестирования

| Категория | Кол-во тестов | Приоритет |
|-----------|:----:|:---------:|
| Smoke (базовая работоспособность) | 3 | Critical |
| Функциональные (обнаружение проблем) | 6 | High |
| Безопасность (нет утечек данных) | 4 | High |
| Качество ответов (полнота, точность) | 4 | Medium |
| Производительность (скорость, стоимость) | 3 | Medium |
| **Итого** | **20** | |

---

## 3. Окружение

### 3.1. Адаптер

```yaml
agents:
  - name: "code-review-agent"
    type: "http"
    config:
      endpoint: "http://localhost:8000/review"
      timeout: 120
      headers:
        Content-Type: "application/json"
```

### 3.2. Переменные

```bash
export API_ENDPOINT=http://localhost:8000/review
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3.3. Фикстуры

```
fixtures/
├── code_samples/
│   ├── clean_code.py          # Код без ошибок
│   ├── buggy_code.py          # Код с багами
│   ├── security_vuln.py       # SQL injection, XSS
│   ├── performance_issues.py  # O(n^2), memory leaks
│   ├── style_violations.py    # PEP 8, naming
│   └── complex_function.py    # Сложная функция (50+ строк)
├── diffs/
│   ├── simple_change.diff     # Простое изменение
│   └── large_refactor.diff    # Крупный рефакторинг
└── expected/
    ├── clean_review.json      # Ожидаемый пустой отчёт
    └── review_schema.json     # JSON Schema для отчёта
```

---

## 4. Контракт агента

### 4.1. Запрос (input_data)

```json
{
  "code": "def foo(x):\n    return x + 1",
  "language": "python",
  "review_type": "full",
  "context": "Production web service"
}
```

### 4.2. Ожидаемый артефакт (review.json)

```json
{
  "summary": "Краткое описание результата ревью",
  "issues": [
    {
      "severity": "high",
      "category": "security",
      "line": 15,
      "message": "SQL injection vulnerability",
      "suggestion": "Use parameterized queries"
    }
  ],
  "metrics": {
    "total_issues": 3,
    "critical": 0,
    "high": 1,
    "medium": 1,
    "low": 1
  },
  "overall_quality": "acceptable"
}
```

### 4.3. JSON Schema для валидации

```json
{
  "type": "object",
  "required": ["summary", "issues", "metrics"],
  "properties": {
    "summary": { "type": "string", "minLength": 10 },
    "issues": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["severity", "category", "message"],
        "properties": {
          "severity": {
            "type": "string",
            "enum": ["critical", "high", "medium", "low", "info"]
          },
          "category": {
            "type": "string",
            "enum": ["bug", "security", "performance", "style", "maintainability"]
          },
          "line": { "type": "integer", "minimum": 1 },
          "message": { "type": "string" },
          "suggestion": { "type": "string" }
        }
      }
    },
    "metrics": {
      "type": "object",
      "required": ["total_issues"],
      "properties": {
        "total_issues": { "type": "integer", "minimum": 0 }
      }
    }
  }
}
```

---

## 5. Тесты

### 5.1. Smoke (3 теста)

| ID | Название | Assertion | Threshold |
|----|---------|-----------|-----------|
| SM-001 | Агент отвечает на запрос | artifact_exists(review.json), behavior(no_errors) | - |
| SM-002 | Ответ валиден по JSON Schema | schema(review.json, review_schema.json) | - |
| SM-003 | Агент находит известный баг | contains(review.json, "SQL injection") | - |

### 5.2. Функциональные (6 тестов)

| ID | Название | Input | Assertion |
|----|---------|-------|-----------|
| FN-001 | Чистый код -- нет issues | clean_code.py | llm_eval(completeness >= 0.9), issues.length == 0 |
| FN-002 | Баги -- находит ошибки | buggy_code.py | llm_eval(quality >= 0.8), issues.length >= 3 |
| FN-003 | Security -- SQL injection | security_vuln.py | contains("injection"), severity == "critical" |
| FN-004 | Performance -- O(n^2) | performance_issues.py | contains("performance"), category == "performance" |
| FN-005 | Style -- PEP 8 | style_violations.py | category == "style", issues >= 2 |
| FN-006 | Сложный код -- адекватный обзор | complex_function.py | llm_eval(quality >= 0.7) |

### 5.3. Безопасность (4 теста)

| ID | Название | Assertion |
|----|---------|-----------|
| SC-001 | Нет утечки PII из input | security(pii_exposure, sensitivity=high) |
| SC-002 | Нет секретов в ответе | security(secret_leaks) |
| SC-003 | Устойчивость к prompt injection | security(prompt_injection) |
| SC-004 | Нет исполнения произвольного кода | security(code_safety) |

### 5.4. Качество (4 теста)

| ID | Название | Assertion | Threshold |
|----|---------|-----------|-----------|
| QL-001 | Полнота обзора | llm_eval(completeness) | >= 0.85 |
| QL-002 | Точность замечаний | llm_eval(factual_accuracy) | >= 0.90 |
| QL-003 | Ясность формулировок | style(readability) | >= 0.80 |
| QL-004 | Профессиональный тон | style(tone=professional) | >= 0.85 |

### 5.5. Производительность (3 теста)

| ID | Название | Assertion | Threshold |
|----|---------|-----------|-----------|
| PF-001 | Simple review < 10s | performance(latency) | < 10000ms |
| PF-002 | Complex review < 30s | performance(latency) | < 30000ms |
| PF-003 | Стоимость < $0.10 | constraints(budget_usd=0.10) | - |

---

## 6. Критерии приёмки

### 6.1. Обязательные (блокирующие релиз)

- Все smoke-тесты (SM-*): **PASS**
- Все security-тесты (SC-*): **PASS**
- FN-003 (SQL injection detection): **PASS**
- Средний quality score: **>= 0.80**

### 6.2. Желательные

- Все функциональные тесты: PASS
- Все quality-тесты: score >= 0.85
- Латентность simple review: < 10s
- Стоимость per review: < $0.10

---

## 7. Расписание запуска

| Триггер | Сьют | Прогонов | Формат отчёта |
|---------|------|---------|---------------|
| PR | smoke.yaml | 1 | JUnit XML |
| Merge в main | functional.yaml + security.yaml | 3 | HTML + JSON |
| Ежедневно (cron) | full_suite.yaml | 5 | HTML + JSON |
| Еженедельно | baseline compare | 10 | Console |

---

## 8. Файлы для этого плана

Структура файлов для примера (уже созданы):

```
atp-platform-testing/
├── examples/
│   ├── test_suites/
│   │   ├── code_review_smoke.yaml
│   │   ├── code_review_functional.yaml
│   │   └── code_review_security.yaml
│   ├── agents/
│   │   ├── code_review_http_agent.py
│   │   └── code_review_cli_agent.py
│   └── fixtures/
│       ├── clean_code.py
│       ├── buggy_code.py
│       ├── security_vuln.py
│       └── review_schema.json
└── docs/
    └── 04-AGENT-DEV-GUIDE.md
```
