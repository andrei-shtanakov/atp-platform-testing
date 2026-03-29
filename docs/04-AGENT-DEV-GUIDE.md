# Руководство по разработке агентов для тестирования на ATP Platform

> Как создать AI-агента, совместимого с ATP Protocol, и подключить его к тестам

---

## 1. Архитектура взаимодействия

```
ATP Platform                         Ваш агент
┌───────────┐                       ┌───────────┐
│ Test Suite │──ATPRequest──────────►│  Agent    │
│  (YAML)   │                       │  Logic    │
│           │◄──ATPResponse─────────│           │
│           │◄──ATPEvent (stream)───│           │
└───────────┘                       └───────────┘
     │                                    │
     ▼                                    ▼
┌───────────┐                       ┌───────────┐
│ Evaluators│                       │ LLM API   │
│ (assert)  │                       │ Tools     │
└───────────┘                       └───────────┘
```

ATP Platform отправляет агенту `ATPRequest` (JSON) и ожидает `ATPResponse` (JSON).
Опционально агент может стримить `ATPEvent` события.

---

## 2. Варианты подключения агента

| Вариант | Адаптер | Транспорт | Когда использовать |
|---------|---------|-----------|-------------------|
| HTTP API | `http` | POST JSON | Агент как веб-сервис |
| CLI скрипт | `cli` | stdin/stdout | Агент как скрипт |
| Docker | `container` | HTTP внутри контейнера | Изолированный агент |
| MCP Server | `mcp` | stdio/SSE | MCP-совместимый сервер |
| Python module | `langgraph`/`crewai`/`autogen` | Direct import | Framework-специфичный |
| Game Agent | `http` | POST JSON | Агент-игрок для теоретико-игровых тестов |

---

## 3. HTTP-агент (самый распространённый)

### 3.1. Минимальный HTTP-агент (FastAPI)

```python
"""
Минимальный HTTP-агент для ATP Platform.
Запуск: uv run uvicorn agent:app --port 8000
"""
import json
from datetime import datetime, timezone

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Task(BaseModel):
    description: str
    input_data: dict | None = None
    expected_artifacts: list[str] | None = None


class Constraints(BaseModel):
    max_steps: int | None = None
    max_tokens: int | None = None
    timeout_seconds: int | None = None
    allowed_tools: list[str] | None = None
    budget_usd: float | None = None


class ATPRequest(BaseModel):
    version: str = "1.0"
    task_id: str
    task: Task
    constraints: Constraints | None = None
    context: dict | None = None
    metadata: dict | None = None


class Artifact(BaseModel):
    type: str  # "file" или "structured"
    path: str | None = None
    name: str | None = None
    content_type: str = "text/plain"
    content: str | None = None
    data: dict | None = None


class Metrics(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_steps: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    wall_time_seconds: float = 0
    cost_usd: float = 0


class ATPResponse(BaseModel):
    version: str = "1.0"
    task_id: str
    status: str  # completed, failed, timeout, partial
    artifacts: list[Artifact] = []
    metrics: Metrics = Metrics()
    error: str | None = None


@app.post("/")
async def handle_request(request: ATPRequest) -> ATPResponse:
    """Обработка ATP-запроса."""
    start = datetime.now(timezone.utc)

    try:
        # === Здесь логика вашего агента ===
        result = process_task(request.task)
        # ===================================

        elapsed = (datetime.now(timezone.utc) - start).total_seconds()

        return ATPResponse(
            task_id=request.task_id,
            status="completed",
            artifacts=[
                Artifact(
                    type="file",
                    path="output.txt",
                    content_type="text/plain",
                    content=result,
                )
            ],
            metrics=Metrics(
                total_steps=1,
                wall_time_seconds=elapsed,
            ),
        )
    except Exception as e:
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=str(e),
        )


@app.get("/health")
async def health():
    return {"status": "ok"}


def process_task(task: Task) -> str:
    """Заглушка для логики агента. Замените на реальную реализацию."""
    return f"Processed: {task.description}"
```

### 3.2. HTTP-агент с LLM (Anthropic)

```python
"""
HTTP-агент с вызовом Claude API для Code Review.
Запуск: uv run uvicorn code_review_agent:app --port 8000
"""
import os
import time

import anthropic
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

SYSTEM_PROMPT = """You are a code review agent.
Analyze the provided code and return a JSON review report with this structure:
{
  "summary": "brief summary",
  "issues": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "bug|security|performance|style|maintainability",
      "line": <line_number>,
      "message": "description",
      "suggestion": "how to fix"
    }
  ],
  "metrics": {
    "total_issues": <count>,
    "critical": <count>,
    "high": <count>,
    "medium": <count>,
    "low": <count>
  },
  "overall_quality": "excellent|good|acceptable|needs_improvement|poor"
}
Respond ONLY with valid JSON, no markdown."""


class Task(BaseModel):
    description: str
    input_data: dict | None = None
    expected_artifacts: list[str] | None = None


class ATPRequest(BaseModel):
    version: str = "1.0"
    task_id: str
    task: Task
    constraints: dict | None = None
    context: dict | None = None
    metadata: dict | None = None


class Artifact(BaseModel):
    type: str
    path: str | None = None
    content_type: str = "text/plain"
    content: str | None = None
    data: dict | None = None


class Metrics(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_steps: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    wall_time_seconds: float = 0
    cost_usd: float = 0


class ATPResponse(BaseModel):
    version: str = "1.0"
    task_id: str
    status: str
    artifacts: list[Artifact] = []
    metrics: Metrics = Metrics()
    error: str | None = None


@app.post("/review")
async def review(request: ATPRequest) -> ATPResponse:
    """Ревью кода через Claude API."""
    start = time.monotonic()

    try:
        code = request.task.input_data.get("code", "") if request.task.input_data else ""
        language = request.task.input_data.get("language", "python") if request.task.input_data else "python"

        user_message = f"Review this {language} code:\n\n```{language}\n{code}\n```\n\nContext: {request.task.description}"

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        review_content = response.content[0].text
        elapsed = time.monotonic() - start

        # Подсчёт стоимости (Claude Sonnet 4 pricing)
        input_cost = response.usage.input_tokens * 3.0 / 1_000_000
        output_cost = response.usage.output_tokens * 15.0 / 1_000_000

        return ATPResponse(
            task_id=request.task_id,
            status="completed",
            artifacts=[
                Artifact(
                    type="file",
                    path="review.json",
                    content_type="application/json",
                    content=review_content,
                )
            ],
            metrics=Metrics(
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_steps=1,
                llm_calls=1,
                wall_time_seconds=elapsed,
                cost_usd=round(input_cost + output_cost, 6),
            ),
        )
    except Exception as e:
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=str(e),
        )


@app.get("/health")
async def health():
    return {"status": "ok"}
```

---

## 4. CLI-агент

### 4.1. Минимальный CLI-агент

```python
"""
CLI-агент для ATP Platform.
Читает ATPRequest из stdin, пишет ATPResponse в stdout.
Events идут в stderr.

Запуск из ATP:
  uv run atp test suite.yaml --adapter=cli \
    --adapter-config='command=python' \
    --adapter-config='args=["cli_agent.py"]'
"""
import json
import sys
import time
from datetime import datetime, timezone


def emit_event(
    task_id: str,
    event_type: str,
    payload: dict,
    sequence: int,
) -> None:
    """Отправить событие в stderr (для observability)."""
    event = {
        "version": "1.0",
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
    }
    print(json.dumps(event), file=sys.stderr)


def process_task(description: str) -> str:
    """Логика агента. Замените на реальную реализацию."""
    return f"Result for: {description}"


def main() -> None:
    start = time.monotonic()

    # Читаем ATPRequest из stdin
    request_json = sys.stdin.read()
    request = json.loads(request_json)

    task_id = request["task_id"]
    task = request["task"]

    # Event: начало работы
    emit_event(task_id, "progress", {"message": "Starting task"}, 1)

    try:
        # Обработка задачи
        result = process_task(task["description"])

        # Event: завершение
        emit_event(task_id, "progress", {"message": "Task completed"}, 2)

        elapsed = time.monotonic() - start

        # Пишем ATPResponse в stdout
        response = {
            "version": "1.0",
            "task_id": task_id,
            "status": "completed",
            "artifacts": [
                {
                    "type": "file",
                    "path": "output.txt",
                    "content_type": "text/plain",
                    "content": result,
                }
            ],
            "metrics": {
                "total_tokens": 0,
                "total_steps": 1,
                "tool_calls": 0,
                "llm_calls": 0,
                "wall_time_seconds": elapsed,
                "cost_usd": 0,
            },
            "error": None,
        }
        print(json.dumps(response))

    except Exception as e:
        response = {
            "version": "1.0",
            "task_id": task_id,
            "status": "failed",
            "artifacts": [],
            "metrics": {},
            "error": str(e),
        }
        print(json.dumps(response))
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## 5. Ключевые правила разработки

### 5.1. Обязательные поля

**В ATPResponse**:
- `version` — всегда `"1.0"`
- `task_id` — точно тот, что пришёл в request
- `status` — одно из: `completed`, `failed`, `timeout`, `partial`

**В Artifact**:
- `type` — `"file"` (текстовый) или `"structured"` (JSON data)
- `path` — путь к файлу (для `file` type)
- `content` — содержимое (для `file` type)
- `data` — JSON-объект (для `structured` type)

### 5.2. Метрики

Заполняйте `metrics` максимально точно — ATP использует их для:
- **total_tokens**: подсчёт стоимости
- **total_steps**: проверка constraints
- **wall_time_seconds**: проверка latency
- **cost_usd**: проверка бюджета
- **tool_calls**: проверка behavior assertions

### 5.3. Обработка ошибок

```python
# Правильно: вернуть failed status с описанием ошибки
return ATPResponse(
    task_id=request.task_id,
    status="failed",
    error="API key expired: unable to call LLM",
)

# Неправильно: бросить exception (ATP получит HTTP 500)
raise Exception("Something went wrong")
```

### 5.4. Constraints

Агент ДОЛЖЕН соблюдать constraints из запроса:

```python
constraints = request.constraints or {}

max_steps = constraints.get("max_steps", 50)
timeout = constraints.get("timeout_seconds", 300)
budget = constraints.get("budget_usd", 1.0)
allowed_tools = constraints.get("allowed_tools")  # None = все

# Проверяйте перед каждым шагом
if current_step >= max_steps:
    return partial_response(status="partial")

if elapsed > timeout:
    return partial_response(status="timeout")
```

---

## 6. Тестирование агента локально

### 6.1. curl-тест

```bash
# Запустить агент
uv run uvicorn agent:app --port 8000

# Тест запрос
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{
    "version": "1.0",
    "task_id": "test-001",
    "task": {
      "description": "Create a hello world file",
      "expected_artifacts": ["output.txt"]
    }
  }'
```

### 6.2. ATP-тест (smoke)

```bash
uv run atp test test_suites/smoke.yaml \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000' \
  -v
```

### 6.3. CLI-агент: ручной тест

```bash
echo '{"version":"1.0","task_id":"t1","task":{"description":"Hello"}}' | python cli_agent.py
```

---

## 7. Паттерны проектирования агентов

### 7.1. Агент с tool use

```python
TOOLS = {
    "file_read": lambda path: open(path).read(),
    "file_write": lambda path, content: open(path, "w").write(content),
    "web_search": lambda query: search_api(query),
}

async def execute_with_tools(
    task: str,
    allowed_tools: list[str] | None,
    max_steps: int,
) -> tuple[str, list[dict]]:
    """Агент с инструментами и ограничением шагов."""
    events = []
    for step in range(max_steps):
        # LLM решает какой tool вызвать
        action = await llm_decide(task, events)

        if action["type"] == "done":
            return action["result"], events

        tool_name = action["tool"]
        if allowed_tools and tool_name not in allowed_tools:
            events.append({"error": f"Tool {tool_name} not allowed"})
            continue

        tool_fn = TOOLS.get(tool_name)
        if not tool_fn:
            events.append({"error": f"Unknown tool: {tool_name}"})
            continue

        result = tool_fn(**action["args"])
        events.append({
            "type": "tool_call",
            "tool": tool_name,
            "result": result,
        })

    return "max steps reached", events
```

### 7.2. Агент с retry

```python
async def execute_with_retry(
    task: str,
    max_retries: int = 3,
) -> str:
    """Агент с повторными попытками при ошибках."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await llm_call(task)
        except Exception as e:
            last_error = e
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise last_error
```

### 7.3. Multi-step агент

```python
async def multi_step_agent(task: Task) -> ATPResponse:
    """Агент, разбивающий задачу на шаги."""
    # Шаг 1: Планирование
    plan = await llm_call(f"Create a plan for: {task.description}")

    # Шаг 2: Выполнение каждого шага плана
    results = []
    for step in plan.steps:
        result = await execute_step(step)
        results.append(result)

    # Шаг 3: Синтез результатов
    final = await llm_call(
        f"Synthesize results: {results}"
    )

    return build_response(final, artifacts=results)
```

### 7.4. Агент для теоретико-игрового тестирования

Игровой агент получает описание игровой ситуации и возвращает решение (действие).

**Формат input (в `task.description`):**
```
You are playing Prisoner's Dilemma. Round 3 of 50.
Your role: player_0.
Available actions: cooperate, defect.
History: [round 0: you=cooperate, opponent=cooperate], ...
Choose your action.
```

**Ожидаемый формат ответа (structured artifact):**
```json
{"action": "cooperate", "reasoning": "Opponent cooperated last round"}
```

**Минимальный игровой агент (Anthropic Claude):**

```python
"""
Игровой агент для ATP Game-Theoretic тестирования.
Запуск: uv run uvicorn game_agent:app --port 8010
"""
import json
import os
import re
import time

import anthropic
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Game Agent (Claude)")
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

SYSTEM_PROMPT = """\
You are a strategic game-playing AI agent.
Analyze the game state and choose an action.
Respond with ONLY a JSON object:
{"action": "<chosen_action>", "reasoning": "<brief explanation>"}
"""


class Task(BaseModel):
    description: str
    input_data: dict | None = None
    expected_artifacts: list[str] | None = None


class ATPRequest(BaseModel):
    version: str = "1.0"
    task_id: str
    task: Task
    constraints: dict | None = None
    context: dict | None = None
    metadata: dict | None = None


class ATPResponse(BaseModel):
    version: str = "1.0"
    task_id: str
    status: str
    artifacts: list[dict] = []
    metrics: dict = {}
    error: str | None = None


def extract_json(text: str) -> dict | None:
    """Извлечь JSON из ответа LLM."""
    text = text.strip()
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return None


@app.post("/")
async def handle_request(request: ATPRequest) -> ATPResponse:
    start = time.monotonic()
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=256,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": request.task.description}],
        )
        raw = response.content[0].text
        parsed = extract_json(raw) or {"action": raw.strip(), "reasoning": ""}
        elapsed = time.monotonic() - start

        return ATPResponse(
            task_id=request.task_id,
            status="completed",
            artifacts=[{"type": "structured", "name": "game_action", "data": parsed}],
            metrics={
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "llm_calls": 1,
                "wall_time_seconds": round(elapsed, 3),
            },
        )
    except Exception as e:
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=str(e),
        )


@app.get("/health")
async def health():
    return {"status": "ok", "type": "game_agent"}
```

**Ключевые отличия от обычного агента:**
- Ответ — `structured` artifact с `{"action": ..., "reasoning": ...}`
- `action` должен быть из списка `available_actions`
- Temperature ниже (0.3) для более детерминированного поведения
- Timeout меньше (агент принимает одно решение за ход)

---

## 8. Чек-лист перед подключением к ATP

```markdown
- [ ] Агент принимает ATPRequest JSON
- [ ] Агент возвращает ATPResponse JSON
- [ ] task_id в ответе совпадает с запросом
- [ ] status корректный (completed/failed/timeout/partial)
- [ ] artifacts содержат ожидаемые файлы
- [ ] metrics заполнены (хотя бы wall_time_seconds)
- [ ] Ошибки возвращаются как error (не HTTP 500)
- [ ] Constraints соблюдаются (max_steps, timeout, budget)
- [ ] Health endpoint отвечает (для HTTP агентов)
- [ ] Агент не утекает PII / секреты в artifacts

### Дополнительно для игровых агентов:
- [ ] Ответ содержит `{"action": ..., "reasoning": ...}`
- [ ] `action` входит в `available_actions` из описания игры
- [ ] Агент парсит историю ходов из `task.description`
```
