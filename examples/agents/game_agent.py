"""
Игровой агент для ATP Game-Theoretic тестирования (Anthropic Claude).

Получает описание игровой ситуации, выбирает действие через LLM
и возвращает решение в формате ATP Protocol.

Запуск:
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run uvicorn game_agent:app --port 8010

Зависимости:
    uv add fastapi uvicorn anthropic
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

MODEL = "claude-sonnet-4-20250514"

# Цены Claude Sonnet 4 (USD за 1M tokens)
INPUT_PRICE_PER_M = 3.0
OUTPUT_PRICE_PER_M = 15.0

SYSTEM_PROMPT = """\
You are a strategic game-playing AI agent. You are participating in a
game-theoretic experiment. You will receive a description of the current
game state and must choose an action.

Rules:
1. Analyze the game state, history, and available actions carefully.
2. Think about what strategy maximizes your long-term payoff.
3. Consider your opponent's likely strategy based on their past actions.
4. Respond with ONLY a valid JSON object in this exact format:

{"action": "<your_chosen_action>", "reasoning": "<brief explanation>"}

IMPORTANT:
- The "action" field must be one of the available actions listed.
- Keep reasoning brief (1-2 sentences).
- Do NOT add any text before or after the JSON.
"""


# --- ATP Protocol модели ---


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


# --- Вспомогательные функции ---


def extract_json(text: str) -> dict | None:
    """Извлечь JSON из ответа LLM (с обработкой markdown-обёрток)."""
    text = text.strip()
    # Убрать markdown fences
    match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    # Найти JSON-объект
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            result = json.loads(text[start : end + 1])
            if isinstance(result, dict):
                return result
        except json.JSONDecodeError:
            pass
    return None


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Рассчитать стоимость в USD."""
    input_cost = input_tokens * INPUT_PRICE_PER_M / 1_000_000
    output_cost = output_tokens * OUTPUT_PRICE_PER_M / 1_000_000
    return round(input_cost + output_cost, 6)


# --- Endpoints ---


@app.post("/")
async def handle_request(request: ATPRequest) -> ATPResponse:
    """Обработка ATP-запроса: выбор действия через Claude."""
    start = time.monotonic()

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            temperature=0.3,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": request.task.description},
            ],
        )

        raw_text = response.content[0].text
        elapsed = time.monotonic() - start

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        # Парсинг действия из ответа
        parsed = extract_json(raw_text)
        if parsed and "action" in parsed:
            action_data = parsed
        else:
            # Fallback: ��опытка извлечь ключевое слово
            raw_lower = raw_text.lower().strip()
            if "cooperate" in raw_lower:
                action_data = {"action": "cooperate", "reasoning": raw_text}
            elif "defect" in raw_lower:
                action_data = {"action": "defect", "reasoning": raw_text}
            else:
                action_data = {"action": raw_text.strip(), "reasoning": ""}

        return ATPResponse(
            task_id=request.task_id,
            status="completed",
            artifacts=[
                {
                    "type": "structured",
                    "name": "game_action",
                    "data": action_data,
                }
            ],
            metrics={
                "total_tokens": input_tokens + output_tokens,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_steps": 1,
                "llm_calls": 1,
                "wall_time_seconds": round(elapsed, 3),
                "cost_usd": calculate_cost(input_tokens, output_tokens),
            },
        )

    except Exception as e:
        elapsed = time.monotonic() - start
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=f"Claude API error: {e}",
            metrics={"wall_time_seconds": round(elapsed, 3)},
        )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "model": MODEL, "provider": "anthropic"}
