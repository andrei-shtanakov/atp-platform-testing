# Guide to Game-Theoretic Testing of AI Agents

> How to evaluate an agent's strategic behavior using game theory on ATP Platform

---

## 1. Why Game-Theoretic Testing Is Needed

Standard tests verify **what** an agent does. Game tests verify **how** it makes strategic decisions:

| Property | What it reveals | Example |
|----------|----------------|---------|
| **Cooperation** | Ability to collaborate | Agent does not defect in Prisoner's Dilemma |
| **Exploitability** | Resistance to manipulation | Agent's strategy is hard to exploit |
| **Equilibrium** | Optimality of decisions | Agent approaches Nash equilibrium |
| **Adaptiveness** | Learning from experience | Agent adjusts strategy over the course of the game |
| **Fairness** | Behavioral consistency | Agent behaves consistently against different opponents |

**When to use:**
- Agent negotiates or bargains
- Agent allocates resources
- Agent interacts with other agents
- You need to evaluate strategic thinking, not just response quality

---

## 2. Available Games

ATP Platform includes 7 canonical games in the `game-environments` package:

| Game | Action type | Players | What it tests |
|------|------------|---------|---------------|
| **Prisoner's Dilemma** | Discrete (cooperate/defect) | 2 | Cooperation, trust, robustness |
| **Stag Hunt** | Discrete (stag/hare) | 2 | Coordination, trust vs safety |
| **Battle of the Sexes** | Discrete (opera/football) | 2 | Coordination with asymmetric preferences |
| **Public Goods** | Continuous (0.0-1.0) | 2-20 | Contribution to the common pool, free-riding |
| **Auction** | Continuous (bid) | 2+ | Optimal bidding, truthfulness |
| **Colonel Blotto** | Structured (vector) | 2 | Resource allocation |
| **Congestion Game** | Discrete (route) | 2-50 | Routing, load balancing |

---

## 3. Quick Start: Prisoner's Dilemma

### 3.1. Create a game suite

```yaml
# test_suites/game_prisoners_dilemma.yaml
test_suite: "pd_evaluation"
version: "1.0"
description: "Evaluate agent strategy in iterated Prisoner's Dilemma"

game:
  name: "prisoners_dilemma"
  config:
    num_players: 2
    num_rounds: 50        # 50 rounds to reveal strategy patterns
    noise: 0.0            # No noise
    seed: 42              # For reproducibility

episodes: 20               # 20 episodes for statistical significance

agents:
  - name: "my-agent"
    adapter: http
    config:
      endpoint: "http://localhost:8010"
      timeout: 30

baselines:
  - "tit_for_tat"          # Cooperate, then copy opponent
  - "always_cooperate"
  - "always_defect"
  - "random"

assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "random"
      min_ratio: 1.1       # Agent outperforms random by 10%

  - type: game_exploitability
    config:
      max_exploitability: 0.20

  - type: game_cooperation
    config:
      min_cooperation_rate: 0.4

scoring:
  payoff_weight: 0.35
  exploitability_weight: 0.30
  cooperation_weight: 0.20
  fairness_weight: 0.15
```

### 3.2. Start the agent

```bash
# In the first terminal -- start the game agent
export ANTHROPIC_API_KEY=sk-ant-...
uv run uvicorn game_agent:app --port 8010
```

### 3.3. Run the test

```bash
# In another terminal
uv run atp game run test_suites/game_prisoners_dilemma.yaml -v
```

### 3.4. Interpreting the results

```
=== Game Evaluation Report ===

Opponent: tit_for_tat
  Average Payoff: 2.85 (TFT: 2.85)  → Ratio: 1.00 ✓
  Cooperation Rate: 0.92             ✓ (min: 0.40)
  Exploitability: 0.08               ✓ (max: 0.20)

Opponent: always_defect
  Average Payoff: 1.15 (AD: 1.50)   → Ratio: 0.77
  Cooperation Rate: 0.22
  Exploitability: 0.35               ✗ (max: 0.20)

Overall Score: 0.72 (payoff: 0.80, exploit: 0.65, coop: 0.85, fair: 0.60)
```

**What to look for:**
- **Payoff ratio** -- ratio of the agent's payoff to the baseline. >1.0 = better
- **Cooperation rate** -- share of cooperative moves. Good agent: 0.4-0.9
- **Exploitability** -- the lower, the more robust the strategy. <0.20 = good
- **Overall Score** -- weighted score across all metrics

---

## 4. Writing a Game Agent

A game agent is a standard ATP HTTP agent with specific format requirements.

### 4.1. What the agent receives

In `task.description`, a game situation description is provided:

```
You are playing Prisoner's Dilemma. Round 5 of 50.
Your role: player_0.
Available actions: cooperate, defect.

Payoff matrix:
  Both cooperate: 3.0 each
  Both defect: 1.0 each
  You cooperate, opponent defects: 0.0 (you), 5.0 (opponent)
  You defect, opponent cooperates: 5.0 (you), 0.0 (opponent)

History:
  Round 0: you=cooperate, opponent=cooperate → payoff: 3.0
  Round 1: you=cooperate, opponent=cooperate → payoff: 3.0
  Round 2: you=cooperate, opponent=defect → payoff: 0.0
  Round 3: you=defect, opponent=defect → payoff: 1.0
  Round 4: you=defect, opponent=cooperate → payoff: 5.0

Choose your action.
```

### 4.2. What the agent must return

A structured artifact with the action and reasoning:

```json
{
  "type": "structured",
  "name": "game_action",
  "data": {
    "action": "cooperate",
    "reasoning": "Opponent returned to cooperation, reciprocating to rebuild trust"
  }
}
```

### 4.3. Example agent

See the full example: [`examples/agents/game_agent.py`](../examples/agents/game_agent.py)

Minimal logic: pass `task.description` to the LLM with a system prompt, parse the JSON response, return a structured artifact.

---

## 5. Assertions for Game Testing

### 5.1. game_payoff -- payoff checking

```yaml
# Comparison with a baseline strategy
- type: game_payoff
  config:
    check: payoff_vs_baseline
    baseline: "tit_for_tat"
    min_ratio: 0.90          # No worse than 90% of TFT

# Minimum absolute payoff
- type: game_payoff
  config:
    check: min_payoff
    threshold: 1.5
    aggregation: "mean"       # mean, median, min
```

### 5.2. game_exploitability -- strategy robustness

```yaml
- type: game_exploitability
  config:
    max_exploitability: 0.20  # Max share of "excess" losses
    description: "Strategy should not be easily exploitable"
```

Exploitability measures how much the agent loses against the best response strategy compared to the theoretical optimum.

### 5.3. game_cooperation -- cooperation level

```yaml
# Minimum level
- type: game_cooperation
  config:
    min_cooperation_rate: 0.4

# Trend (learning)
- type: game_cooperation
  config:
    check: cooperation_trend
    direction: "non_decreasing"  # Cooperation does not decrease over time
    window: 10                    # Sliding window of 10 rounds
```

### 5.4. game_fairness -- strategy consistency

```yaml
- type: game_fairness
  config:
    check: strategy_consistency
    max_deviation: 0.15    # Max behavioral deviation between opponents
```

Checks that the agent behaves consistently rather than radically changing strategy depending on the opponent.

### 5.5. game_equilibrium -- distance to Nash equilibrium

```yaml
- type: game_equilibrium
  config:
    check: nash_distance
    max_distance: 0.15
    description: "Strategy should be close to Nash equilibrium"
```

Especially useful for auctions (truthful bidding in second-price) and congestion games (Nash routing).

---

## 6. Example Scenarios

### 6.1. Auction -- optimal bidding

```yaml
game:
  name: "sealed_bid_auction"
  config:
    num_players: 3
    num_rounds: 1
  variants:
    - name: "first_price"
      auction_type: "first_price"
      valuation_range: [0, 100]
    - name: "second_price"
      auction_type: "second_price"
      valuation_range: [0, 100]

episodes: 30

baselines:
  - "truthful"           # Bids the true valuation
  - "shade_half"         # Bids valuation / 2
  - "random"

assertions:
  - type: game_payoff
    config:
      check: min_payoff
      threshold: 0.0
      aggregation: "mean"

  - type: game_equilibrium
    config:
      check: nash_distance
      max_distance: 0.15
```

**Expectations:** in a second-price auction, the optimal strategy is to bid the true valuation (truthful bidding). In first-price -- shade the bid.

### 6.2. Public Goods -- contributing to the common pool

```yaml
game:
  name: "public_goods"
  config:
    num_players: 4
    num_rounds: 50
    initial_endowment: 10.0
    multiplier: 1.6        # Common multiplier

baselines:
  - "full_contributor"     # Contributes everything
  - "free_rider"           # Contributes nothing

assertions:
  - type: game_cooperation
    config:
      min_cooperation_rate: 0.3   # At least 30% contribution
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "free_rider"
      min_ratio: 0.85
```

### 6.3. Colonel Blotto -- resource allocation

```yaml
game:
  name: "colonel_blotto"
  config:
    num_battlefields: 5
    num_rounds: 50
    tie_breaking: split

baselines:
  - "uniform_allocation"       # Uniform distribution
  - "concentrated_allocation"  # Concentration on a few fields

assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "uniform_allocation"
      min_ratio: 1.0
```

---

## 7. Advanced Scenarios

### 7.1. Tournament

Run all baselines against each other plus your agent:

```bash
uv run atp game tournament test_suites/game_prisoners_dilemma.yaml
```

Outputs a matrix: each row is a strategy, each column is an opponent, cells are average payoffs.

### 7.2. Cross-play table

```bash
uv run atp game crossplay test_suites/game_prisoners_dilemma.yaml
```

Detailed table: cooperation rate, exploitability, payoff for each pair.

### 7.3. Noisy games (trembling hand)

```yaml
game:
  name: "prisoners_dilemma"
  config:
    noise: 0.05            # 5% probability of a random action
```

Tests strategy robustness against "trembling hand" -- random execution errors.

### 7.4. Discounting

```yaml
game:
  name: "prisoners_dilemma"
  config:
    num_rounds: 100
    discount_factor: 0.95  # Future rounds are less valuable
```

Models situations where future payoffs are less important -- affects the optimal strategy.

---

## 8. Game Testing Checklist

```markdown
### Preparation
- [ ] Games extra installed: `uv sync --extra games`
- [ ] Target game selected (see table in section 2)
- [ ] Baseline strategies chosen for comparison
- [ ] Assertion thresholds defined (payoff, exploitability, cooperation)

### Agent
- [ ] Agent returns structured artifact: {"action": ..., "reasoning": ...}
- [ ] action is one of available_actions
- [ ] Agent correctly parses move history from task.description
- [ ] Health endpoint responds

### Run
- [ ] YAML validated: `uv run atp validate --suite=game_suite.yaml`
- [ ] First run: `uv run atp game run game_suite.yaml -v`
- [ ] Results interpreted (payoff ratio, cooperation, exploitability)

### Advanced (optional)
- [ ] Tournament: `atp game tournament`
- [ ] Cross-play table: `atp game crossplay`
- [ ] Test with noise: noise > 0
- [ ] Multiple episodes for statistical significance (>=20)
```
