# Guide to Developing Agents for Testing on ATP Platform

> How to create an AI agent compatible with the ATP Protocol and connect it to tests

---

## 1. Interaction Architecture

```
ATP Platform                         Your Agent
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

ATP Platform sends the agent an `ATPRequest` (JSON) and expects an `ATPResponse` (JSON).
Optionally, the agent can stream `ATPEvent` events.

---

## 2. Agent Connection Options

| Option | Adapter | Transport | When to use |
|--------|---------|-----------|------------|
| HTTP API | `http` | POST JSON | Agent as a web service |
| CLI script | `cli` | stdin/stdout | Agent as a script |
| Docker | `container` | HTTP inside container | Isolated agent |
| MCP Server | `mcp` | stdio/SSE | MCP-compatible server |
| Python module | `langgraph`/`crewai`/`autogen` | Direct import | Framework-specific |

---

## 3. HTTP Agent (Most Common)

### 3.1. Minimal HTTP Agent (FastAPI)

```python
"""
Minimal HTTP agent for ATP Platform.
Run: uv run uvicorn agent:app --port 8000
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
    type: str  # "file" or "structured"
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
    """Handle ATP request."""
    start = datetime.now(timezone.utc)

    try:
        # === Your agent logic here ===
        result = process_task(request.task)
        # ==============================

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
    """Stub for agent logic. Replace with actual implementation."""
    return f"Processed: {task.description}"
```

### 3.2. HTTP Agent with LLM (Anthropic)

```python
"""
HTTP agent using Claude API for Code Review.
Run: uv run uvicorn code_review_agent:app --port 8000
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
    """Review code via Claude API."""
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

        # Cost calculation: Claude Sonnet 4 pricing
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

## 4. CLI Agent

### 4.1. Minimal CLI Agent

```python
"""
CLI agent for ATP Platform.
Reads ATPRequest from stdin, writes ATPResponse to stdout.
Events go to stderr.

Run from ATP:
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
    """Send event to stderr (for observability)."""
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
    """Agent logic stub. Replace with actual implementation."""
    return f"Result for: {description}"


def main() -> None:
    start = time.monotonic()

    # Read ATPRequest from stdin
    request_json = sys.stdin.read()
    request = json.loads(request_json)

    task_id = request["task_id"]
    task = request["task"]

    # Event: work started
    emit_event(task_id, "progress", {"message": "Starting task"}, 1)

    try:
        # Process the task
        result = process_task(task["description"])

        # Event: completed
        emit_event(task_id, "progress", {"message": "Task completed"}, 2)

        elapsed = time.monotonic() - start

        # Write ATPResponse to stdout
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

## 5. Key Development Rules

### 5.1. Required fields

**In ATPResponse**:
- `version` — always `"1.0"`
- `task_id` — must match exactly what came in the request
- `status` — one of: `completed`, `failed`, `timeout`, `partial`

**In Artifact**:
- `type` — `"file"` (text) or `"structured"` (JSON data)
- `path` — file path (for `file` type)
- `content` — contents (for `file` type)
- `data` — JSON object (for `structured` type)

### 5.2. Metrics

Fill in `metrics` as accurately as possible — ATP uses them for:
- **total_tokens**: cost calculation
- **total_steps**: constraint checking
- **wall_time_seconds**: latency checking
- **cost_usd**: budget checking
- **tool_calls**: behavior assertion checks

### 5.3. Error handling

```python
# Correct: return failed status with error description
return ATPResponse(
    task_id=request.task_id,
    status="failed",
    error="API key expired: unable to call LLM",
)

# Incorrect: throw exception (ATP receives HTTP 500)
raise Exception("Something went wrong")
```

### 5.4. Constraints

The agent MUST respect constraints from the request:

```python
constraints = request.constraints or {}

max_steps = constraints.get("max_steps", 50)
timeout = constraints.get("timeout_seconds", 300)
budget = constraints.get("budget_usd", 1.0)
allowed_tools = constraints.get("allowed_tools")  # None = all allowed

# Check before each step
if current_step >= max_steps:
    return partial_response(status="partial")

if elapsed > timeout:
    return partial_response(status="timeout")
```

---

## 6. Testing the Agent Locally

### 6.1. curl test

```bash
# Start the agent
uv run uvicorn agent:app --port 8000

# Test request
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

### 6.2. ATP test (smoke)

```bash
uv run atp test test_suites/smoke.yaml \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000' \
  -v
```

### 6.3. CLI agent: manual test

```bash
echo '{"version":"1.0","task_id":"t1","task":{"description":"Hello"}}' | python cli_agent.py
```

---

## 7. Agent Design Patterns

### 7.1. Agent with tool use

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
    """Agent with tools and step limits."""
    events = []
    for step in range(max_steps):
        # LLM decides which tool to call
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

### 7.2. Agent with retry

```python
async def execute_with_retry(
    task: str,
    max_retries: int = 3,
) -> str:
    """Agent with retry on errors."""
    last_error = None
    for attempt in range(max_retries):
        try:
            return await llm_call(task)
        except Exception as e:
            last_error = e
            await asyncio.sleep(2 ** attempt)  # Exponential backoff

    raise last_error
```

### 7.3. Multi-step agent

```python
async def multi_step_agent(task: Task) -> ATPResponse:
    """Agent that breaks tasks into steps."""
    # Step 1: Planning
    plan = await llm_call(f"Create a plan for: {task.description}")

    # Step 2: Execute each step
    results = []
    for step in plan.steps:
        result = await execute_step(step)
        results.append(result)

    # Step 3: Synthesize results
    final = await llm_call(
        f"Synthesize results: {results}"
    )

    return build_response(final, artifacts=results)
```

---

## 8. Pre-Connection Checklist

```markdown
- [ ] Agent accepts ATPRequest JSON
- [ ] Agent returns ATPResponse JSON
- [ ] task_id in response matches the request
- [ ] status is correct (completed/failed/timeout/partial)
- [ ] artifacts contain expected files
- [ ] metrics are populated (at least wall_time_seconds)
- [ ] Errors are returned as error field (not HTTP 500)
- [ ] Constraints are respected (max_steps, timeout, budget)
- [ ] Health endpoint responds (for HTTP agents)
- [ ] Agent does not leak PII / secrets in artifacts
```
