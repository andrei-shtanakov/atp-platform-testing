# Guide to Creating AI Agent Test Plans

> How to prepare environments, files, contracts, and test suites for ATP Platform

---

## 1. Process Overview

```
Step 1: Define testing objectives
   ↓
Step 2: Design the contract (ATP Protocol)
   ↓
Step 3: Prepare the environment
   ↓
Step 4: Write the test suite (YAML)
   ↓
Step 5: Prepare fixtures and test data
   ↓
Step 6: Configure the adapter
   ↓
Step 7: Run tests and collect baseline
   ↓
Step 8: Set up CI/CD
```

---

## 2. Step 1: Define Testing Objectives

### 2.1. Test categories

| Category | What we verify | Example |
|----------|---------------|---------|
| **Functionality** | Agent solves the task correctly | File creation, data processing |
| **Quality** | Quality of responses/artifacts | Completeness, accuracy, structure |
| **Security** | No data leaks, no injections | PII, secrets, prompt injection |
| **Performance** | Speed, cost | Latency, tokens, USD |
| **Reliability** | Stability across repeated runs | Result variance, errors |
| **Interaction** | Multi-agent collaboration | Comparison, collaboration, handoff |
| **Game-theoretic** | Strategic agent behavior | Cooperation, exploitability, Nash equilibrium |

### 2.2. Setting priorities

For each test, define:
- **Severity**: critical / high / medium / low
- **Tags**: smoke, regression, security, performance, edge_case
- **Scoring weights**: quality, completeness, efficiency, cost (sum = 1.0)

### 2.3. Objectives checklist

```markdown
- [ ] What tasks should the agent be able to solve?
- [ ] What artifacts are expected as output?
- [ ] What tools can the agent use?
- [ ] What are the constraints: steps, tokens, budget, time?
- [ ] What quality level is acceptable (threshold)?
- [ ] Are security checks needed?
- [ ] Do we need to compare multiple agents/models?
- [ ] How many runs are needed for statistical significance?
```

---

## 3. Step 2: Design the Contract (ATP Protocol)

### 3.1. ATP Request — what the agent receives

```json
{
  "version": "1.0",
  "task_id": "task_001",
  "task": {
    "description": "Natural language task description",
    "input_data": {
      "key": "additional data for the agent"
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

### 3.2. ATP Response — what the agent returns

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
      "content": "file contents"
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

### 3.3. ATP Event — streaming events

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

### 3.4. Response statuses

| Status | When |
|--------|------|
| `completed` | Task completed successfully |
| `failed` | Error during execution |
| `timeout` | Time limit exceeded |
| `cancelled` | Cancelled by user |
| `partial` | Partial result |

### 3.5. Event types

| Event Type | Description |
|-----------|------------|
| `tool_call` | Agent called a tool |
| `llm_request` | LLM API call |
| `reasoning` | Reasoning step |
| `error` | Error occurred |
| `progress` | Intermediate status |

---

## 4. Step 3: Prepare the Environment

### 4.1. Working directory structure

```
my-agent-tests/
├── atp.config.yaml           # ATP configuration
├── .env                      # API keys (do NOT commit)
├── test_suites/
│   ├── smoke.yaml            # Smoke tests
│   ├── functional.yaml       # Functional tests
│   ├── security.yaml         # Security tests
│   └── performance.yaml      # Performance tests
├── fixtures/
│   ├── input_data/           # Input data for tests
│   │   ├── sample.csv
│   │   └── config.json
│   └── expected/             # Reference results
│       ├── expected_output.txt
│       └── expected_report.json
├── agents/                   # Agents under test
│   ├── http_agent.py         # HTTP agent (FastAPI)
│   ├── cli_agent.py          # CLI agent (stdin/stdout)
│   └── requirements.txt
├── baselines/                # Saved baselines
│   └── baseline_v1.json
└── reports/                  # Test results
    ├── results.json
    └── report.html
```

### 4.2. Minimal .env

```bash
# .env
ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# AWS_ACCESS_KEY_ID=...
# AWS_SECRET_ACCESS_KEY=...
```

### 4.3. Minimal atp.config.yaml

```yaml
log_level: INFO
parallel_workers: 4
default_timeout: 300
runs_per_test: 1
anthropic_api_key: ${ANTHROPIC_API_KEY}
default_provider: anthropic
```

---

## 5. Step 4: Write the Test Suite (YAML)

### 5.1. File structure

```yaml
test_suite: "suite_name"              # Unique identifier
version: "1.0"
description: "Description of the test suite"

# Default values (inherited by all tests)
defaults:
  runs_per_test: 1                    # Number of runs (1-100)
  timeout_seconds: 120                # Timeout per test
  constraints:
    max_steps: 10
    max_tokens: 50000
    timeout_seconds: 120
    allowed_tools: null               # null = all allowed
    budget_usd: 0.50
  scoring:
    quality_weight: 0.4
    completeness_weight: 0.3
    efficiency_weight: 0.2
    cost_weight: 0.1                  # Sum = 1.0

# Agent definitions
agents:
  - name: "my-agent"
    type: "http"                      # Adapter type
    config:
      endpoint: "${API_ENDPOINT:http://localhost:8000}"
      timeout: 60

# Tests
tests:
  - id: "test-001"                    # Unique ID
    name: "Test name"
    tags: ["smoke", "critical"]
    task:
      description: "Task description"
      input_data: {}
      expected_artifacts: ["output.txt"]
    constraints: {}                   # Override defaults
    assertions: []                    # Result checks
```

### 5.2. Available assertion types

| Assertion | Evaluator | What it checks |
|-----------|-----------|---------------|
| `artifact_exists` | artifact | File exists |
| `contains` | artifact | Text/regex in file |
| `schema` | artifact | JSON Schema validation |
| `behavior` | behavior | no_errors, must_use_tools, no_repeated_actions |
| `llm_eval` | llm_judge | Semantic evaluation via Claude-as-judge |
| `code_exec` | code_exec | Run pytest/npm/custom |
| `security` | security | PII, secrets, injections |
| `factuality` | factuality | Fact-checking, hallucinations |
| `style` | style | Tone, readability |
| `performance` | performance | Latency, throughput |
| `file_exists` | filesystem | File checks |
| `file_contains` | filesystem | File content checks |
| `dir_exists` | filesystem | Directory checks |
| `composite` | composite | Combine checks (AND/OR/NOT logic) |
| `container` | container | Isolated Docker/Podman execution with resource limits |
| `guardrails` | guardrails | Custom guardrails enforcement (Python functions) |
| `git_commit` | git_commit | Git commit message/diff analysis |

### 5.3. New assertion types (v1.0)

**Container** — run checks in isolated Docker/Podman containers:
```yaml
- type: "container"
  config:
    image: "python:3.12-slim"
    command: "python -m pytest /workspace/tests/"
    timeout: 120
    resource_limits:
      memory: "256m"
      cpu: "1.0"
```

**Guardrails** — enforce custom rules via Python functions:
```yaml
- type: "guardrails"
  config:
    rules:
      - name: "no_profanity"
        function: "custom_checks.check_profanity"
      - name: "max_length"
        function: "custom_checks.check_length"
        args: { max_chars: 5000 }
```

**Git commit** — analyze commit messages and diffs:
```yaml
- type: "git_commit"
  config:
    message_pattern: "^(feat|fix|docs|refactor): .+"
    min_lines_changed: 1
```

### 5.4. Variables in YAML

```yaml
# Required variable (error if not set)
endpoint: "${API_ENDPOINT}"

# With default value
endpoint: "${API_ENDPOINT:http://localhost:8000}"
api_key: "${API_KEY:test_key}"
```

### 5.5. Game-theoretic test suite

For evaluating strategic agent behavior, a dedicated YAML format is used:

```yaml
test_suite: "prisoners_dilemma_evaluation"
version: "1.0"
description: "Evaluate agent behavior in iterated Prisoner's Dilemma"

# Game configuration
game:
  name: "prisoners_dilemma"
  config:
    num_players: 2
    num_rounds: 50
    noise: 0.0           # trembling hand (0 = no noise)
    seed: 42

episodes: 20              # Number of episodes for statistics

# Agent under test
agents:
  - name: "llm-agent"
    adapter: http
    config:
      endpoint: "${AGENT_ENDPOINT:http://localhost:8010}"
      timeout: 30

# Baseline strategies for comparison
baselines:
  - "tit_for_tat"
  - "always_cooperate"
  - "always_defect"
  - "random"

# Game-theoretic assertions
assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "random"
      min_ratio: 1.1         # Agent outperforms random by 10%

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

# Scoring weights
scoring:
  payoff_weight: 0.30
  exploitability_weight: 0.25
  cooperation_weight: 0.25
  fairness_weight: 0.20
```

Available game assertions:

| Assertion | What it checks |
|-----------|---------------|
| `game_payoff` | Average payoff, comparison with baseline |
| `game_exploitability` | How vulnerable the strategy is to exploitation |
| `game_cooperation` | Cooperation rate, trend across rounds |
| `game_fairness` | Strategy consistency against different opponents |
| `game_equilibrium` | Distance to Nash equilibrium |

> Full guide: [05-GAME-TESTING-GUIDE.md](docs/05-GAME-TESTING-GUIDE.md)

---

## 6. Step 5: Prepare Fixtures

### 6.1. Workspace fixtures

For file-system tests, create a template directory:

```
fixtures/workspace_basic/
├── readme.txt
├── data/
│   ├── input.csv
│   └── config.json
└── templates/
    └── report_template.md
```

Reference in a test:
```yaml
task:
  workspace_fixture: "fixtures/workspace_basic"
  description: "Process files in the working directory"
```

### 6.2. Input data

```yaml
task:
  description: "Analyze the CSV data"
  input_data:
    csv_content: |
      name,age,city
      Alice,30,London
      Bob,25,Berlin
    format: "csv"
    expected_columns: ["name", "age", "city"]
```

### 6.3. Expected results

For `contains` and `schema` assertions, prepare expected patterns:

```yaml
assertions:
  - type: "contains"
    config:
      path: "report.md"
      pattern: "## Summary"       # Expected heading
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

## 7. Step 6: Configure the Adapter

### 7.1. Choosing an adapter

| Adapter | When to use | Config |
|---------|------------|--------|
| `http` | REST API agent | endpoint, headers |
| `cli` | stdin/stdout script | command, args |
| `container` | Docker container | image, ports, volumes |
| `mcp` | MCP server | transport, command/url |
| `langgraph` | LangGraph graph | module, graph |
| `crewai` | CrewAI crew | module, crew |
| `autogen` | AutoGen system | config_path, agent_name |
| `bedrock` | AWS Bedrock | model_id, region |
| `vertex` | Google Vertex AI | project_id, model_id |
| `azure_openai` | Azure OpenAI | endpoint, deployment_name |

### 7.2. Configuration via CLI

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

### 7.3. Configuration in YAML

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

## 8. Step 7: Run and Create Baseline

### 8.1. First run

```bash
# Validate
uv run atp validate --suite=test_suites/smoke.yaml

# Run with verbose output
uv run atp test test_suites/smoke.yaml -v

# Run with live display
uv run atp test test_suites/smoke.yaml --live
```

### 8.2. Creating a baseline

```bash
# 10 runs for a statistically significant baseline
uv run atp baseline save test_suites/functional.yaml \
  -o baselines/baseline_v1.json \
  --runs=10
```

### 8.3. Regression testing

```bash
uv run atp baseline compare test_suites/functional.yaml \
  -b baselines/baseline_v1.json
# Uses Welch's t-test to detect regressions
```

---

## 9. Step 8: CI/CD Integration

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

### 9.2. Exit codes

| Code | Meaning |
|------|---------|
| 0 | All tests passed |
| 1 | Some tests failed |
| 2 | Configuration error / file not found |

---

## 10. Step 8a: Test Generation with Claude Code

If you use [Claude Code](https://claude.ai/code) with ATP Platform skills loaded, two accelerators are available:

**`/generate-tests`** -- generate pytest tests for ATP modules:
```
/generate-tests atp/evaluators/factuality.py
```
Creates unit tests with proper fixtures, async patterns, and AAA structure.

**`/generate-game-tests`** -- generate game scenarios:
```
/generate-game-tests prisoners_dilemma
```
Creates a YAML game suite plus pytest tests for validating payoffs, strategy behavior, and equilibrium properties.

Both skills work as accelerators: understanding the manual process (Steps 1-8) is still necessary for tuning and interpreting results.

---

## 11. Step 9: Test Catalog

ATP includes a catalog of curated, ready-to-run test scenarios:

```bash
# Browse available suites
uv run atp catalog list

# Run a suite from the catalog
uv run atp catalog run smoke/basic --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'
```

Use the catalog as a starting point: run a ready-made suite, study the format, then adapt it for your agent.

---

## 12. Test Plan Template

```markdown
# Test Plan: [Agent Name]

## 1. Objective
- What we're testing: [agent description]
- Agent version: [v1.0.0]
- Date: [YYYY-MM-DD]

## 2. Scope
- [ ] Functional tests (N tests)
- [ ] Quality tests (N tests)
- [ ] Security tests (N tests)
- [ ] Performance tests (N tests)
- [ ] Game-theoretic tests (N scenarios)

## 3. Environment
- Adapter: [http/cli/mcp/...]
- Endpoint: [URL or command]
- API keys: [list of required keys]
- Fixtures: [list of files]

## 4. Tests
| ID | Name | Category | Severity | Tags |
|----|------|----------|----------|------|
| T-001 | ... | functional | critical | smoke |
| T-002 | ... | security | high | security |

## 5. Acceptance Criteria
- All smoke tests: PASS
- Quality score >= 0.8
- No PII leaks
- Latency < 5s for simple tasks

## 6. Schedule
- Smoke: on every PR
- Full suite: daily
- Baseline comparison: weekly
```

> **Ready-made example:** A fully runnable lab comparing two Code Writer agents (GPT-4o vs Claude) — [`examples/code-writer-lab/`](examples/code-writer-lab/). Includes agents, test suites, fixtures, and step-by-step instructions.
