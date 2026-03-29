"""
Game Agent — Anthropic Claude Sonnet 4.

HTTP-агент для ATP Platform. Принимает игровое состояние (game state),
вызывает Anthropic API для выбора стратегического действия и возвращает
структурированный ответ с действием и обоснованием.

Запуск:
    export ANTHROPIC_API_KEY=sk-ant-...
    uv run uvicorn agents.game_agent:app --port 8010

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

app = FastAPI(title="Game Agent (Anthropic)")

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

MODEL = "claude-sonnet-4-20250514"

# Цены Claude Sonnet 4 (USD за 1M tokens), актуальные на март 2026
INPUT_PRICE_PER_M = 3.00
OUTPUT_PRICE_PER_M = 15.00

SYSTEM_PROMPT = """\
You are a strategic game-playing agent. You participate in game-theoretic
scenarios (e.g., Prisoner's Dilemma, auctions) and must choose optimal actions.

Rules:
1. Analyze the game state, history, and opponent behavior carefully.
2. Consider both short-term payoff and long-term strategic position.
3. In repeated games, adapt your strategy based on opponent's past actions.
4. In auctions, reason about valuations, expected competition, and bid optimality.
5. Always respond with a JSON object: {"action": <your_action>, "reasoning": "<brief_explanation>"}
6. For Prisoner's Dilemma, action is "cooperate" or "defect".
7. For auctions, action is a numeric bid value.
8. Keep reasoning concise (1-3 sentences).
"""


# --- Pydantic models (ATP Game Protocol) ---


class GameState(BaseModel):
    """Текущее состояние игры."""

    game_name: str
    round: int = 0
    total_rounds: int = 1
    history: list[dict] | None = None
    payoff_matrix: dict | None = None
    context: dict | None = None


class GameRequest(BaseModel):
    """Запрос к игровому агенту."""

    version: str = "1.0"
    task_id: str
    game_state: GameState
    metadata: dict | None = None


class Artifact(BaseModel):
    type: str = "game_action"
    content_type: str = "application/json"
    content: str | None = None


class Metrics(BaseModel):
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_steps: int = 0
    tool_calls: int = 0
    llm_calls: int = 0
    wall_time_seconds: float = 0
    cost_usd: float = 0


class GameResponse(BaseModel):
    """Ответ игрового агента."""

    version: str = "1.0"
    task_id: str
    status: str
    artifacts: list[Artifact] = []
    metrics: Metrics = Metrics()
    error: str | None = None


# --- Helpers ---


def calculate_cost(input_tokens: int, output_tokens: int) -> float:
    """Считает стоимость запроса в USD."""
    input_cost = input_tokens * INPUT_PRICE_PER_M / 1_000_000
    output_cost = output_tokens * OUTPUT_PRICE_PER_M / 1_000_000
    return round(input_cost + output_cost, 6)


def parse_game_action(text: str) -> dict:
    """Извлекает JSON-действие из ответа LLM с fallback."""
    text = text.strip()
    # Убираем markdown-обёртки если есть
    pattern = r"```(?:json)?\s*\n(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        text = match.group(1).strip()

    # Пробуем распарсить JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fallback: ищем JSON-объект в тексте
    json_pattern = r"\{[^{}]*\}"
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Последний fallback: ищем ключевые слова
    text_lower = text.lower()
    if "cooperate" in text_lower:
        return {"action": "cooperate", "reasoning": text[:200]}
    if "defect" in text_lower:
        return {"action": "defect", "reasoning": text[:200]}

    return {"action": "cooperate", "reasoning": "fallback: could not parse"}


def format_game_prompt(game_state: GameState) -> str:
    """Формирует промпт из игрового состояния."""
    parts = [
        f"Game: {game_state.game_name}",
        f"Round: {game_state.round}/{game_state.total_rounds}",
    ]

    if game_state.payoff_matrix:
        parts.append(f"Payoff matrix: {json.dumps(game_state.payoff_matrix)}")

    if game_state.history:
        recent = game_state.history[-10:]
        parts.append(f"Recent history (last {len(recent)} rounds):")
        for entry in recent:
            parts.append(f"  {json.dumps(entry)}")

    if game_state.context:
        parts.append(f"Context: {json.dumps(game_state.context)}")

    parts.append(
        "\nChoose your action. Respond with JSON: "
        '{"action": <value>, "reasoning": "<explanation>"}'
    )
    return "\n".join(parts)


# --- Endpoints ---


@app.post("/")
async def handle_request(request: GameRequest) -> GameResponse:
    """Обработка игрового запроса: выбор действия через Anthropic."""
    start = time.monotonic()

    try:
        user_message = format_game_prompt(request.game_state)

        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = response.content[0].text
        action_data = parse_game_action(raw_text)
        elapsed = time.monotonic() - start

        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens

        return GameResponse(
            task_id=request.task_id,
            status="completed",
            artifacts=[
                Artifact(
                    type="game_action",
                    content_type="application/json",
                    content=json.dumps(action_data),
                )
            ],
            metrics=Metrics(
                total_tokens=input_tokens + output_tokens,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_steps=1,
                llm_calls=1,
                wall_time_seconds=round(elapsed, 3),
                cost_usd=calculate_cost(input_tokens, output_tokens),
            ),
        )

    except Exception as e:
        elapsed = time.monotonic() - start
        return GameResponse(
            task_id=request.task_id,
            status="failed",
            error=f"Anthropic API error: {e}",
            metrics=Metrics(wall_time_seconds=round(elapsed, 3)),
        )


@app.get("/health")
async def health() -> dict:
    """Проверка здоровья агента."""
    return {"status": "ok", "model": MODEL, "provider": "anthropic", "role": "game"}
