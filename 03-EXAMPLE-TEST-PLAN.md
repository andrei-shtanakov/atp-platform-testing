# Example: Test Plan for a Code Review Agent

> Complete example of an AI agent test plan for ATP Platform

---

## 1. Objective

**Agent**: Code Review Agent — an AI agent that performs automated Python code reviews.

**What the agent does**:
- Accepts a file path or diff
- Analyzes code for bugs, style, security, and performance issues
- Returns a structured report with findings and recommendations

**Version**: v1.0.0
**Model**: Claude Sonnet 4
**Interface**: HTTP REST API (POST /review)

---

## 2. Testing Scope

| Category | Test Count | Priority |
|----------|:----:|:---------:|
| Smoke (basic functionality) | 3 | Critical |
| Functional (issue detection) | 6 | High |
| Security (no data leaks) | 4 | High |
| Response quality (completeness, accuracy) | 4 | Medium |
| Performance (speed, cost) | 3 | Medium |
| **Total** | **20** | |

---

## 3. Environment

### 3.1. Adapter

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

### 3.2. Variables

```bash
export API_ENDPOINT=http://localhost:8000/review
export ANTHROPIC_API_KEY=sk-ant-...
```

### 3.3. Fixtures

```
fixtures/
├── code_samples/
│   ├── clean_code.py          # Bug-free code
│   ├── buggy_code.py          # Code with bugs
│   ├── security_vuln.py       # SQL injection, XSS
│   ├── performance_issues.py  # O(n^2), memory leaks
│   ├── style_violations.py    # PEP 8, naming
│   └── complex_function.py    # Complex function (50+ lines)
├── diffs/
│   ├── simple_change.diff     # Simple change
│   └── large_refactor.diff    # Major refactoring
└── expected/
    ├── clean_review.json      # Expected empty report
    └── review_schema.json     # JSON Schema for the report
```

---

## 4. Agent Contract

### 4.1. Request (input_data)

```json
{
  "code": "def foo(x):\n    return x + 1",
  "language": "python",
  "review_type": "full",
  "context": "Production web service"
}
```

### 4.2. Expected artifact (review.json)

```json
{
  "summary": "Brief description of review findings",
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

### 4.3. JSON Schema for validation

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

## 5. Tests

### 5.1. Smoke (3 tests)

| ID | Name | Assertion | Threshold |
|----|------|-----------|-----------|
| SM-001 | Agent responds to a request | artifact_exists(review.json), behavior(no_errors) | - |
| SM-002 | Response matches JSON Schema | schema(review.json, review_schema.json) | - |
| SM-003 | Agent detects known bug | contains(review.json, "SQL injection") | - |

### 5.2. Functional (6 tests)

| ID | Name | Input | Assertion |
|----|------|-------|-----------|
| FN-001 | Clean code -- no issues | clean_code.py | llm_eval(completeness >= 0.9), issues.length == 0 |
| FN-002 | Buggy code -- finds errors | buggy_code.py | llm_eval(quality >= 0.8), issues.length >= 3 |
| FN-003 | Security -- SQL injection | security_vuln.py | contains("injection"), severity == "critical" |
| FN-004 | Performance -- O(n^2) | performance_issues.py | contains("performance"), category == "performance" |
| FN-005 | Style -- PEP 8 | style_violations.py | category == "style", issues >= 2 |
| FN-006 | Complex code -- adequate review | complex_function.py | llm_eval(quality >= 0.7) |

### 5.3. Security (4 tests)

| ID | Name | Assertion |
|----|------|-----------|
| SC-001 | No PII leaks from input | security(pii_exposure, sensitivity=high) |
| SC-002 | No secrets in response | security(secret_leaks) |
| SC-003 | Resilient to prompt injection | security(prompt_injection) |
| SC-004 | No arbitrary code execution | security(code_safety) |

### 5.4. Quality (4 tests)

| ID | Name | Assertion | Threshold |
|----|------|-----------|-----------|
| QL-001 | Review completeness | llm_eval(completeness) | >= 0.85 |
| QL-002 | Finding accuracy | llm_eval(factual_accuracy) | >= 0.90 |
| QL-003 | Clarity of explanations | style(readability) | >= 0.80 |
| QL-004 | Professional tone | style(tone=professional) | >= 0.85 |

### 5.5. Performance (3 tests)

| ID | Name | Assertion | Threshold |
|----|------|-----------|-----------|
| PF-001 | Simple review < 10s | performance(latency) | < 10000ms |
| PF-002 | Complex review < 30s | performance(latency) | < 30000ms |
| PF-003 | Cost < $0.10 | constraints(budget_usd=0.10) | - |

---

## 6. Acceptance Criteria

### 6.1. Required (release blockers)

- All smoke tests (SM-*): **PASS**
- All security tests (SC-*): **PASS**
- FN-003 (SQL injection detection): **PASS**
- Average quality score: **>= 0.80**

### 6.2. Desired

- All functional tests: PASS
- All quality tests: score >= 0.85
- Simple review latency: < 10s
- Cost per review: < $0.10

---

## 7. Run Schedule

| Trigger | Suite | Runs | Report Format |
|---------|-------|------|---------------|
| PR | smoke.yaml | 1 | JUnit XML |
| Merge to main | functional.yaml + security.yaml | 3 | HTML + JSON |
| Daily (cron) | full_suite.yaml | 5 | HTML + JSON |
| Weekly | baseline compare | 10 | Console |

---

## 8. Files for This Plan

File structure for this example (already created):

```
atp-platform-testing-en/
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

---

## 9. Lab: Comparing Code Writer Agents

A fully runnable example built using this methodology is available at:

```
examples/code-writer-lab/
```

**Goal:** Compare two AI agents for Python code generation:
- **Agent A**: OpenAI GPT-4o (port 8001)
- **Agent B**: Anthropic Claude Sonnet 4 (port 8002)

Both receive identical tasks (fibonacci, csv_parser, api_client) and ATP evaluates results across smoke/functional/quality/game-theoretic assertions.

**Contents:**
- `agents/` — two HTTP agents (OpenAI, Anthropic) + a game agent
- `test_suites/` — smoke, functional, quality + game-theoretic suites
- `fixtures/` — code tasks + pytest tests to verify generated code
- `docs/` — test plan, contract, run guide
- `steps.md` — step-by-step execution checklist

**Quick start:**
```bash
cd examples/code-writer-lab
cp .env.example .env
# Fill in API keys in .env

# Start agents
uv run uvicorn agents.openai_agent:app --port 8001 &
uv run uvicorn agents.anthropic_agent:app --port 8002 &

# Run tests
uv run atp test test_suites/smoke.yaml -v
```

Details: [`examples/code-writer-lab/docs/03-run-guide.md`](examples/code-writer-lab/docs/03-run-guide.md)
