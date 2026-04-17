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
uv sync --extra cloud       # boto3, google-cloud, openai (all cloud adapters)
uv sync --extra bedrock     # AWS Bedrock only
uv sync --extra vertex      # Google Vertex AI only
uv sync --extra azure-openai # Azure OpenAI only
uv sync --extra dashboard   # FastAPI dashboard + benchmark/tournament APIs
uv sync --extra enterprise  # SSO/SAML, Redis storage for dashboard
uv sync --extra analytics   # dashboard analytics (cost tracking, Excel export)
uv sync --extra llm         # anthropic SDK (for LLM evaluator)
uv sync --extra tui         # Terminal UI
uv sync --extra all         # everything at once
```

> **Note:** `game-environments` and `atp-games` are workspace members and are installed automatically by `uv sync`. There is no separate `--extra games`.

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
dashboard_debug: false
```

### 3.2. Environment variables

```bash
# Required (if using LLM evaluator)
export ANTHROPIC_API_KEY="sk-ant-..."
# or
export OPENAI_API_KEY="sk-..."

# Optional — core
export ATP_LOG_LEVEL=DEBUG
export ATP_PARALLEL_WORKERS=8
export ATP_FAIL_FAST=true
export ATP_DEFAULT_TIMEOUT=300
export ATP_SANDBOX_ENABLED=false

# Optional — dashboard authentication
export ATP_SECRET_KEY="your-jwt-secret"          # Required in production
export ATP_DATABASE_URL="sqlite:///atp.db"       # SQLite default, supports PostgreSQL
export ATP_DISABLE_AUTH=false                     # Set true for dev only
export ATP_GITHUB_CLIENT_ID="..."                # GitHub OAuth OIDC
export ATP_GITHUB_CLIENT_SECRET="..."
export ATP_TOKEN_EXPIRE_MINUTES=60
export ATP_CORS_ORIGINS=""

# Optional — rate limiting
export ATP_RATE_LIMIT_ENABLED=true
export ATP_RATE_LIMIT_DEFAULT="60/minute"
export ATP_RATE_LIMIT_AUTH="5/minute"
export ATP_RATE_LIMIT_API="120/minute"
export ATP_RATE_LIMIT_UPLOAD="10/minute"
export ATP_RATE_LIMIT_STORAGE="memory://"         # or redis://host:port

# Optional — batch & upload
export ATP_BATCH_MAX_SIZE=10
export ATP_UPLOAD_MAX_SIZE_MB=1
```

### 3.3. Configuration priority

```
CLI flags > Environment variables (ATP_*) > atp.config.yaml > Defaults
```

---

## 4. First Run

### 4.1. Quick start (quickstart)

```bash
uv run atp quickstart
```

Creates a minimal project with an `atp-suite.yaml` and a sample smoke test -- the fastest way to get started.

### 4.2. Initialize project (full)

```bash
uv run atp init
```

Creates the full initial structure with examples.

### 4.3. Validate a test suite

```bash
uv run atp validate --suite=examples/test_suites/01_smoke_tests.yaml
```

### 4.4. List tests without running

```bash
uv run atp test examples/test_suites/01_smoke_tests.yaml --list-only
```

### 4.5. Run smoke tests

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

# JUnit XML (for CI/CD)
uv run atp test suite.yaml --output=junit --output-file=results.xml
```

> **Note**: The CLI supports `console`, `json`, and `junit` output formats.
> HTML reports are generated via the Python SDK or reporter API.

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

The dashboard includes:
- **Pages**: Benchmarks, Runs (list + detail), Leaderboard, Games, Suites, Analytics
- **Real-time updates** via HTMX auto-refresh on run detail pages
- **Authentication**: GitHub OAuth (OIDC) + Device Flow for CLI login
- **Authorization**: JWT tokens, RBAC (first user auto-promoted to admin)
- **Multi-tenant** support with tenant-scoped data isolation
- **Rate limiting** (slowapi): configurable per endpoint via `ATP_RATE_LIMIT_*` env vars

**Benchmark API** (REST):
```bash
# Create a benchmark
curl -X POST http://localhost:8080/api/v1/benchmarks \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "my-bench", "suite": {...}}'

# Start a run
curl -X POST http://localhost:8080/api/v1/runs \
  -d '{"benchmark_id": "...", "agent_name": "my-agent"}'

# Get next task (pull model)
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/next-task

# Submit result
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/submit \
  -d '{"score": 0.95, "response": {...}}'

# Stream events (max 1000 per run)
curl -X POST http://localhost:8080/api/v1/runs/$RUN_ID/events \
  -d '[{"event_type": "progress", "payload": {...}}]'

# Leaderboard
curl http://localhost:8080/api/v1/leaderboard
```

**Webhooks**: configure `webhook_url` on a benchmark to receive POST notifications when runs complete (SSRF-protected, retry with backoff).

### 6.6. Game-theoretic evaluation

```bash
# Run a game scenario
uv run atp game run test_suites/game_prisoners_dilemma.yaml

# List available games
uv run atp game list
# prisoners_dilemma, stag_hunt, battle_of_sexes,
# public_goods, auction, colonel_blotto, congestion, el_farol_bar

# Game information
uv run atp game info prisoners_dilemma

# Tournament (all strategies against each other)
uv run atp game tournament test_suites/game_prisoners_dilemma.yaml

# Cross-play results table
uv run atp game crossplay test_suites/game_prisoners_dilemma.yaml
```

The report includes: average payoffs, cooperation rate, exploitability, distance to Nash equilibrium. Report format is `game` (GameReporter), supporting JSON, HTML, and CSV export.

> See also: [05-GAME-TESTING-GUIDE.md](docs/05-GAME-TESTING-GUIDE.md)

### 6.7. Test Catalog

```bash
# Browse the catalog of curated test suites
uv run atp catalog list

# Information about a specific suite
uv run atp catalog info smoke/basic

# Run a suite from the catalog
uv run atp catalog run smoke/basic \
  --adapter=http \
  --adapter-config='endpoint=http://localhost:8000'

# Publish your own suite to the catalog
uv run atp catalog publish test_suites/my_suite.yaml
```

The catalog contains curated test scenarios (smoke, functional, security) -- a convenient starting point before writing your own tests.

---

### 6.8. Additional CLI Commands

```bash
# Compare multiple models/agents
uv run atp compare suite.yaml --agents=agent1,agent2

# Estimate run cost
uv run atp estimate suite.yaml

# Generate test suites
uv run atp generate

# Benchmarks
uv run atp benchmark

# Trace management
uv run atp traces list
uv run atp replay <trace-id>

# Plugins
uv run atp plugins list

# Terminal UI (requires [tui] extra)
uv run atp tui

# Budget management (cost tracking and limits)
uv run atp budget

# Experiments (A/B testing, comparisons)
uv run atp experiment

# Trend analysis (detect gradual regressions over time)
uv run atp trend

# Suite sync with remote server
uv run atp push suite.yaml --server=https://atp.example.com
uv run atp pull --server=https://atp.example.com
uv run atp sync --server=https://atp.example.com
```

### 6.9. SDK (Programmatic Access)

ATP provides a Python SDK (`atp-platform-sdk` on PyPI) for benchmark participants and programmatic integration:

```bash
uv add atp-platform-sdk
```

**Async client:**
```python
from atp_sdk import AsyncATPClient

async with AsyncATPClient(base_url="http://localhost:8080") as client:
    # Start a benchmark run
    run = await client.start_run(benchmark_id="bench-001", agent_name="my-agent")

    # Pull tasks and submit results
    async for task in run:
        result = await my_agent(task)
        await run.submit(score=result.score, response=result.data)

    # Check status
    status = await run.status()
    print(f"Total score: {status.total_score}")
```

**Sync wrapper:**
```python
from atp_sdk import ATPClient

client = ATPClient(base_url="http://localhost:8080")
run = client.start_run_sync(benchmark_id="bench-001", agent_name="my-agent")

# Batch API: get N tasks at once
tasks = run.next_batch_sync(n=5)
for task in tasks:
    result = my_agent(task)
    run.submit_sync(score=result.score, response=result.data)
```

**Features:**
- `BenchmarkRun` iterator with `submit()`, `status()`, `cancel()`
- Event streaming: `run.emit(event_type="progress", payload={...})`
- Batch API: `next_batch(n)` for pulling multiple tasks
- Device Flow auth for CLI login
- Exponential-backoff retry logic built in

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
| `game-environments not found` | Workspace not synced | `uv sync` (game-environments + atp-games are pulled in automatically as workspace members) |
| `ModuleNotFoundError: atp_sdk` | SDK not installed | `uv add atp-platform-sdk` (or `uv sync --extra all`) |

---

## 8. Project Structure (Reference)

```
atp-platform/
├── atp/                           # Main namespace (symlinks + local modules)
│   ├── cli/                       # CLI commands (entry point)
│   ├── runner/                    # Test orchestration, sandbox
│   ├── evaluators/                # 13 types of result checks
│   ├── reporters/                 # 5 report formats (console, JSON, JUnit, HTML, game)
│   ├── baseline/                  # Baseline management, regression detection
│   ├── benchmarks/                # Benchmark suites
│   ├── catalog/                   # Test catalog browser
│   ├── generator/                 # Test suite generation
│   ├── plugins/                   # Plugin ecosystem
│   ├── sdk/                       # Programmatic SDK
│   ├── tracing/                   # Trace replay
│   ├── tui/                       # Terminal UI (optional)
│   ├── performance/               # Profiling, caching
│   └── mock_tools/                # Mock tool server
│
├── packages/                      # Extracted workspace members
│   ├── atp-core/                  # Protocol, loader, scoring, statistics, streaming, chaos
│   ├── atp-adapters/              # 10 agent adapters (http, cli, container, langgraph, crewai, autogen, mcp, bedrock, vertex, azure_openai) + SDK-pull adapter
│   ├── atp-dashboard/             # FastAPI backend, benchmark/tournament APIs, auth, MCP tournament server
│   └── atp-sdk/                   # Python SDK (PyPI: atp-platform-sdk) for benchmark participants
│
├── game-environments/             # Standalone game theory library (8 games, 25+ strategies)
├── atp-games/                     # ATP plugin for game-theoretic evaluation
│
├── tests/                         # 80%+ coverage
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── examples/
│   └── test_suites/               # 20+ example YAML test suites
├── docs/                          # Documentation
├── deploy/                        # Deployment configs
└── pyproject.toml                 # Dependencies and configuration (uv workspace)
```
