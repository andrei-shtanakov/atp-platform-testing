"""
Code Review HTTP Agent for ATP Platform.

Uses Claude API to analyze code.
Returns a structured JSON report.

Run:
    uv run uvicorn examples.agents.code_review_http_agent:app --port 8000

Dependencies:
    uv add fastapi uvicorn anthropic
"""

import json
import os
import time

import anthropic
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Code Review Agent")

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
)

SYSTEM_PROMPT = """\
You are a senior code reviewer. Analyze the provided code and return a JSON object.

RESPONSE FORMAT (strict JSON, no markdown):
{
  "summary": "1-2 sentence summary of the review",
  "issues": [
    {
      "severity": "critical|high|medium|low|info",
      "category": "bug|security|performance|style|maintainability",
      "line": <line_number_or_null>,
      "message": "description of the issue",
      "suggestion": "how to fix it"
    }
  ],
  "metrics": {
    "total_issues": <int>,
    "critical": <int>,
    "high": <int>,
    "medium": <int>,
    "low": <int>
  },
  "overall_quality": "excellent|good|acceptable|needs_improvement|poor"
}

Rules:
- Respond ONLY with valid JSON
- Do NOT include markdown code fences
- Do NOT repeat secrets, passwords, or PII from the code in your review
- If code is empty, return summary="No code to review" with empty issues
- Be specific: reference line numbers when possible
"""


# --- Pydantic models (ATP Protocol subset) ---


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
    wall_time_seconds: float = 0.0
    cost_usd: float = 0.0


class ATPResponse(BaseModel):
    version: str = "1.0"
    task_id: str
    status: str
    artifacts: list[Artifact] = []
    metrics: Metrics = Metrics()
    error: str | None = None


# --- Endpoints ---


@app.post("/review")
async def review(request: ATPRequest) -> ATPResponse:
    """Perform code review via Claude API."""
    start = time.monotonic()

    try:
        input_data = request.task.input_data or {}
        code = input_data.get("code", "")
        language = input_data.get("language", "python")
        review_type = input_data.get("review_type", "full")

        if not code.strip():
            empty_review = json.dumps(
                {
                    "summary": "No code to review",
                    "issues": [],
                    "metrics": {
                        "total_issues": 0,
                        "critical": 0,
                        "high": 0,
                        "medium": 0,
                        "low": 0,
                    },
                    "overall_quality": "excellent",
                },
                indent=2,
            )
            return ATPResponse(
                task_id=request.task_id,
                status="completed",
                artifacts=[
                    Artifact(
                        type="file",
                        path="review.json",
                        content_type="application/json",
                        content=empty_review,
                    )
                ],
                metrics=Metrics(
                    total_steps=1,
                    wall_time_seconds=time.monotonic() - start,
                ),
            )

        user_message = (
            f"Review type: {review_type}\n"
            f"Language: {language}\n"
            f"Context: {request.task.description}\n\n"
            f"Code:\n```{language}\n{code}\n```"
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        review_text = response.content[0].text
        elapsed = time.monotonic() - start

        # Cost: Claude Sonnet 4 pricing
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
                    content=review_text,
                )
            ],
            metrics=Metrics(
                total_tokens=(
                    response.usage.input_tokens + response.usage.output_tokens
                ),
                input_tokens=response.usage.input_tokens,
                output_tokens=response.usage.output_tokens,
                total_steps=1,
                llm_calls=1,
                wall_time_seconds=elapsed,
                cost_usd=round(input_cost + output_cost, 6),
            ),
        )

    except anthropic.APIError as e:
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=f"Anthropic API error: {e.message}",
        )
    except Exception as e:
        return ATPResponse(
            task_id=request.task_id,
            status="failed",
            error=f"Internal error: {type(e).__name__}: {e}",
        )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "agent": "code-review", "version": "1.0.0"}
