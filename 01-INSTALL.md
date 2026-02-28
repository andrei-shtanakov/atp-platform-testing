# ATP Platform: Installation, Configuration, and Testing

> Step-by-step guide for working with the Agent Test Platform (atp-platform)

---

## 1. System Requirements

| Component | Requirement |
|-----------|-----------|
| Python | >= 3.12 |
| Package manager | uv (NOT pip) |
| OS | macOS / Linux / Windows (WSL) |
| Docker | Optional (for container adapter) |
| API keys | Anthropic / OpenAI (for LLM evaluator) |

### Installing uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## 2. Installing ATP Platform

### 2.1. Navigate to the project

```bash
cd /path/to/all_ai_orchestrators/atp-platform
```

### 2.2. Install dependencies

```bash
# Minimal installation (core + CLI)
uv sync

# Full installation (all extras)
uv sync --all-extras

# Specific extras as needed
uv sync --extra cloud       # boto3, google-cloud, openai
uv sync --extra dashboard   # FastAPI dashboard
uv sync --extra llm         # anthropic SDK (for LLM evaluator)
uv sync --extra tui         # Terminal UI
uv sync --extra analytics   # Excel export
```

### 2.3. Verify installation

```bash
uv run atp version
uv run atp list-agents      # list available adapters
```

Expected `list-agents` output:
```
Available adapters:
  http          HTTP/HTTPS REST endpoints
  cli           Command-line agents (stdin/stdout)
  container     Docker containers
  langgraph     LangGraph framework
  crewai        CrewAI framework
  autogen       AutoGen framework
  mcp           Model Context Protocol
  bedrock       AWS Bedrock
  vertex        Google Vertex AI
  azure_openai  Azure OpenAI
```

---

## 3. Configuration

### 3.1. Configuration file

Create `atp.config.yaml` in the working directory root:

```yaml
# atp.config.yaml
log_level: INFO
parallel_workers: 4
default_timeout: 300
fail_fast: false
sandbox_enabled: false
runs_per_test: 1

# LLM (for llm_eval assertions)
anthropic_api_key: ${ANTHROPIC_API_KEY}
default_llm_model: claude-sonnet-4-20250514
default_provider: anthropic
max_retries: 3
request_timeout: 60

# Dashboard (optional)
dashboard_host: 127.0.0.1
dashboard_port: 8080
```

### 3.2. Environment variables

```bash
# Required (if using LLM evaluator)
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export OPENAI_API_KEY="sk-..."

# Optional
export ATP_LOG_LEVEL=DEBUG
export ATP_PARALLEL_WORKERS=8
export ATP_FAIL_FAST=true
```

### 3.3. Configuration priority

```
CLI flags > Environment variables (ATP_*) > atp.config.yaml > Defaults
```

---

## 4. First Run

### 4.1. Initialize project

```bash
uv run atp init
```

Creates initial structure with examples.

### 4.2. Validate a test suite

```bash
uv run atp validate --suite=examples/test_suites/01_smoke_tests.yaml
```

### 4.3. List tests without running

```bash
uv run atp test examples/test_suites/01_smoke_tests.yaml --list-only
```

### 4.4. Run smoke tests

```bash
# Against an HTTP agent
uv run atp test examples/test_suites/01_smoke_tests.yaml \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'

# Against a CLI agent
uv run atp test examples/test_suites/01_smoke_tests.yaml \
  --adapter=cli \
  --adapter-config='command=python' \
  --adapter-config='args=["examples/demo_agent.py"]'
```

---

## 5. Running ATP Platform Tests

### 5.1. Internal platform tests (pytest)

```bash
# All tests with coverage
uv run pytest tests/ -v --cov=atp --cov-report=term-missing

# Unit tests only
uv run pytest tests/unit -v

# Fast tests (skip slow marker)
uv run pytest tests/ -v -m "not slow"

# Specific module
uv run pytest tests/unit/loader -v
uv run pytest tests/unit/evaluators -v

# HTML coverage report
uv run pytest --cov=atp --cov-report=html
# Open: htmlcov/index.html
```

### 5.2. Linting and formatting

```bash
uv run ruff format .          # Format code
uv run ruff check .           # Check style
uv run ruff check . --fix     # Auto-fix issues
pyrefly check                 # Type checking
```

---

## 6. Advanced Run Scenarios

### 6.1. Multiple runs with statistics

```bash
uv run atp test suite.yaml --runs=5 --parallel=4
# Outputs: mean, std, median, 95% CI, p-value
```

### 6.2. Baselines and regression

```bash
# Save baseline
uv run atp baseline save suite.yaml -o baseline.json --runs=10

# Compare against baseline (Welch's t-test)
uv run atp baseline compare suite.yaml -b baseline.json
```

### 6.3. Reports

```bash
# JSON report
uv run atp test suite.yaml --output=json --output-file=results.json

# HTML report (self-contained file)
uv run atp test suite.yaml --output=html --output-file=report.html

# JUnit XML (for CI/CD)
uv run atp test suite.yaml --output=junit --output-file=results.xml
```

### 6.4. Filtering by tags

```bash
# Smoke tests only
uv run atp test suite.yaml --tags=smoke

# Exclude slow tests
uv run atp test suite.yaml --tags='!slow'

# Combination
uv run atp test suite.yaml --tags=smoke,critical
```

### 6.5. Dashboard

```bash
uv run atp dashboard
# Open: http://127.0.0.1:8080
```

### 6.6. Game-theoretic evaluation

```bash
uv run atp game examples/test_suites/11_game_prisoners_dilemma.yaml
```

---

## 7. Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|---------|
| `ModuleNotFoundError: anthropic` | `llm` extra not installed | `uv sync --extra llm` |
| `ANTHROPIC_API_KEY not set` | Missing API key | `export ANTHROPIC_API_KEY=sk-ant-...` |
| `Connection refused` on endpoint | Agent not running | Start the agent on the specified port |
| `Timeout` during testing | Insufficient time | Increase `timeout_seconds` in the suite |
| `ValidationError: Duplicate test ID` | Two tests share an id | Make IDs unique |
| `Scoring weights must sum to 1.0` | Invalid weights | Check quality+completeness+efficiency+cost=1.0 |
| Dashboard won't start | `dashboard` extra missing | `uv sync --extra dashboard` |

---

## 8. Project Structure (Reference)

```
atp-platform/
├── atp/
│   ├── cli/              # CLI commands (entry point)
│   ├── core/             # Settings, security, telemetry
│   ├── protocol/         # ATP Protocol: Request/Response/Event
│   ├── loader/           # YAML test suite parsing
│   ├── runner/           # Test execution orchestration
│   ├── adapters/         # 10 adapters for connecting agents
│   ├── evaluators/       # 11 types of result checks
│   ├── reporters/        # 4 report formats
│   ├── scoring/          # Score aggregation
│   ├── statistics/       # Statistical analysis (mean, CI, t-test)
│   ├── baseline/         # Baseline management
│   ├── dashboard/        # Web UI (FastAPI)
│   ├── analytics/        # Cost tracking
│   ├── benchmarks/       # Benchmark suites
│   ├── chaos/            # Chaos testing
│   ├── tracing/          # Trace recording and replay
│   └── sdk/              # Python SDK for programmatic access
├── tests/
│   ├── unit/             # ~70% of tests
│   ├── integration/      # ~20% of tests
│   ├── e2e/              # ~10% of tests
│   └── fixtures/         # Test data
├── examples/
│   └── test_suites/      # 20+ example YAML test suites
├── docs/                 # Documentation
└── pyproject.toml        # Dependencies and configuration
```
