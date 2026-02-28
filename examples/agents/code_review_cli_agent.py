"""
Code Review CLI Agent для ATP Platform.

Читает ATPRequest из stdin, пишет ATPResponse в stdout.
Events отправляются в stderr.

Запуск из ATP:
    uv run atp test suite.yaml \
      --adapter=cli \
      --adapter-config='command=python' \
      --adapter-config='args=["examples/agents/code_review_cli_agent.py"]'

Зависимости:
    uv add anthropic
"""

import json
import os
import sys
import time
from datetime import datetime, timezone


def emit_event(
    task_id: str,
    event_type: str,
    payload: dict,
    sequence: int,
) -> None:
    """Отправить событие в stderr."""
    event = {
        "version": "1.0",
        "task_id": task_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence,
        "event_type": event_type,
        "payload": payload,
    }
    print(json.dumps(event), file=sys.stderr)


def review_code(code: str, language: str, review_type: str) -> str:
    """Выполнить code review через Claude API."""
    import anthropic

    client = anthropic.Anthropic(
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )

    system_prompt = """\
You are a senior code reviewer. Return a JSON object with this structure:
{
  "summary": "1-2 sentence summary",
  "issues": [{"severity": "...", "category": "...", "line": N, "message": "...", "suggestion": "..."}],
  "metrics": {"total_issues": N, "critical": N, "high": N, "medium": N, "low": N},
  "overall_quality": "excellent|good|acceptable|needs_improvement|poor"
}
Respond ONLY with valid JSON. Do NOT repeat secrets or PII from the code."""

    user_message = (
        f"Review type: {review_type}\n"
        f"Language: {language}\n\n"
        f"Code:\n```{language}\n{code}\n```"
    )

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_message}],
    )

    return response.content[0].text


def make_empty_review() -> str:
    """Ответ для пустого кода."""
    return json.dumps(
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


def main() -> None:
    """Точка входа CLI-агента."""
    start = time.monotonic()
    seq = 0

    # Читаем ATPRequest из stdin
    request_json = sys.stdin.read()
    request = json.loads(request_json)

    task_id = request["task_id"]
    task = request["task"]
    input_data = task.get("input_data") or {}

    code = input_data.get("code", "")
    language = input_data.get("language", "python")
    review_type = input_data.get("review_type", "full")

    seq += 1
    emit_event(task_id, "progress", {"message": "Starting code review"}, seq)

    try:
        if not code.strip():
            review_content = make_empty_review()
        else:
            seq += 1
            emit_event(
                task_id,
                "llm_request",
                {"model": "claude-sonnet-4-20250514", "purpose": "code_review"},
                seq,
            )
            review_content = review_code(code, language, review_type)

        elapsed = time.monotonic() - start

        seq += 1
        emit_event(
            task_id,
            "progress",
            {"message": "Review completed", "elapsed": elapsed},
            seq,
        )

        # Пишем ATPResponse в stdout
        response = {
            "version": "1.0",
            "task_id": task_id,
            "status": "completed",
            "artifacts": [
                {
                    "type": "file",
                    "path": "review.json",
                    "content_type": "application/json",
                    "content": review_content,
                }
            ],
            "metrics": {
                "total_tokens": 0,
                "total_steps": 1,
                "tool_calls": 0,
                "llm_calls": 1 if code.strip() else 0,
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
            "metrics": {
                "wall_time_seconds": time.monotonic() - start,
            },
            "error": f"{type(e).__name__}: {e}",
        }
        print(json.dumps(response))
        sys.exit(1)


if __name__ == "__main__":
    main()
