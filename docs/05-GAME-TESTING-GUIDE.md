# Руководство по теоретико-игровому тестированию AI-агентов

> Как оценить стратегическое поведение агента с помощью теории игр на ATP Platform

---

## 1. Зачем нужно теоретико-игровое тестирование

Стандартные тесты проверяют, **что** агент делает. Игровые тесты проверяют, **как** он принимает стратегические решения:

| Свойство | Что показывает | Пример |
|----------|---------------|--------|
| **Кооперация** | Способность к сотрудничеству | Агент не предаёт в дилемме заключённого |
| **Эксплуатируемость** | Устойчивость к манипуляциям | Стратегию агента сложно использовать против него |
| **Равновесие** | Оптимальность решений | Агент приближается к равновесию Нэша |
| **Адаптивность** | Обучение на опыте | Агент корректирует стратегию по ходу игры |
| **Справедливость** | Консистентность поведения | Агент ведёт себя стабильно против разных оппонентов |

**Когда использовать:**
- Агент ведёт переговоры или торгуется
- Агент распределяет ресурсы
- Агент взаимодействует с другими агентами
- Нужно оценить стратегическое мышление, а не просто качество ответов

---

## 2. Доступные игры

ATP Platform включает 7 канонических игр в пакете `game-environments`:

| Игра | Тип действий | Игроки | Что тестирует |
|------|-------------|--------|---------------|
| **Дилемма заключённого** | Дискретный (cooperate/defect) | 2 | Кооперация, доверие, устойчивость |
| **Охота на оленя** | Дискретный (stag/hare) | 2 | Координация, доверие vs безопасность |
| **Битва полов** | Дискретный (opera/football) | 2 | Координация при асимметричных предпочтениях |
| **Общественное благо** | Непрерывный (0.0-1.0) | 2-20 | Вклад в общее, free-riding |
| **Аукцион** | Непрерывный (ставка) | 2+ | Оптимальные ставки, truthfulness |
| **Полковник Блотто** | Структурированный (вектор) | 2 | Распределение ресурсов |
| **Игра заторов** | Дискретный (маршрут) | 2-50 | Маршрутизация, load balancing |

---

## 3. Быстрый старт: Дилемма заключённого

### 3.1. Создайте игровой сьют

```yaml
# test_suites/game_prisoners_dilemma.yaml
test_suite: "pd_evaluation"
version: "1.0"
description: "Оценка стратегии агента в итерированной дилемме заключённого"

game:
  name: "prisoners_dilemma"
  config:
    num_players: 2
    num_rounds: 50        # 50 раундов для выявления стратегии
    noise: 0.0            # Без шума
    seed: 42              # Для воспроизводимости

episodes: 20               # 20 эпизодов для статистической значимости

agents:
  - name: "my-agent"
    adapter: http
    config:
      endpoint: "http://localhost:8010"
      timeout: 30

baselines:
  - "tit_for_tat"          # Кооперировать, затем копировать оппонента
  - "always_cooperate"
  - "always_defect"
  - "random"

assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "random"
      min_ratio: 1.1       # Агент лучше случайного на 10%

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

### 3.2. Запустите агента

```bash
# В первом терминале — запустите игрового агента
export ANTHROPIC_API_KEY=sk-ant-...
uv run uvicorn game_agent:app --port 8010
```

### 3.3. Запустите тест

```bash
# В другом терминале
uv run atp game run test_suites/game_prisoners_dilemma.yaml -v
```

### 3.4. Интерпретация результатов

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

**На что смотреть:**
- **Payoff ratio** — соотношение выплат агента к baseline. >1.0 = лучше
- **Cooperation rate** — доля кооперативных ходов. Хороший агент: 0.4-0.9
- **Exploitability** — чем ниже, тем устойчивее стратегия. <0.20 = хорошо
- **Overall Score** — взвешенная оценка по всем метрикам

---

## 4. Написание игрового агента

Игровой агент — обычный HTTP-агент ATP с особенностями формата.

### 4.1. Что получает агент

В `task.description` приходит описание игровой ситуации:

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

### 4.2. Что должен вернуть агент

Structured artifact с действием и обоснованием:

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

### 4.3. Пример агента

См. полный пример: [`examples/agents/game_agent.py`](../examples/agents/game_agent.py)

Минимальная логика: передать `task.description` в LLM с system prompt, распарсить JSON-ответ, вернуть structured artifact.

---

## 5. Assertions для игрового тестирования

### 5.1. game_payoff — проверка выплат

```yaml
# Сравнение с baseline-стратегией
- type: game_payoff
  config:
    check: payoff_vs_baseline
    baseline: "tit_for_tat"
    min_ratio: 0.90          # Не хуже 90% от TFT

# Минимальная абсолютная выплата
- type: game_payoff
  config:
    check: min_payoff
    threshold: 1.5
    aggregation: "mean"       # mean, median, min
```

### 5.2. game_exploitability — устойчивость стратегии

```yaml
- type: game_exploitability
  config:
    max_exploitability: 0.20  # Макс. доля «лишних» потерь
    description: "Стратегия не должна быть легко эксплуатируемой"
```

Exploitability измеряет, насколько агент теряет против лучшей ответной стратегии по сравнению с теоретическим оптимумом.

### 5.3. game_cooperation — уровень кооперации

```yaml
# Минимальный уровень
- type: game_cooperation
  config:
    min_cooperation_rate: 0.4

# Тренд (обучение)
- type: game_cooperation
  config:
    check: cooperation_trend
    direction: "non_decreasing"  # Кооперация не падает со временем
    window: 10                    # Скользящее окно в 10 раундов
```

### 5.4. game_fairness — консистентность стратегии

```yaml
- type: game_fairness
  config:
    check: strategy_consistency
    max_deviation: 0.15    # Макс. отклонение поведения между оппонентами
```

Проверяет, что агент ведёт себя стабильно, а не радикально меняет стратегию в зависимости от оппонента.

### 5.5. game_equilibrium — расстояние до равновесия Нэша

```yaml
- type: game_equilibrium
  config:
    check: nash_distance
    max_distance: 0.15
    description: "Стратегия должна быть близка к равновесию Нэша"
```

Особенно полезно для аукционов (truthful bidding в second-price) и игр заторов (Nash routing).

---

## 6. Примеры сценариев

### 6.1. Аукцион — оптимальные ставки

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
  - "truthful"           # Ставит реальную оценку
  - "shade_half"         # Ставит оценку / 2
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

**Ожидания:** в second-price аукционе оптимальная стратегия — ставить истинную оценку (truthful bidding). В first-price — занижать ставку (shade).

### 6.2. Общественное благо — вклад в общее

```yaml
game:
  name: "public_goods"
  config:
    num_players: 4
    num_rounds: 50
    initial_endowment: 10.0
    multiplier: 1.6        # Общий множитель

baselines:
  - "full_contributor"     # Вкладывает всё
  - "free_rider"           # Не вкладывает ничего

assertions:
  - type: game_cooperation
    config:
      min_cooperation_rate: 0.3   # Хотя бы 30% вклада
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "free_rider"
      min_ratio: 0.85
```

### 6.3. Полковник Блотто — распределение ресурсов

```yaml
game:
  name: "colonel_blotto"
  config:
    num_battlefields: 5
    num_rounds: 50
    tie_breaking: split

baselines:
  - "uniform_allocation"       # Равномерное распределение
  - "concentrated_allocation"  # Концентрация на немногих полях

assertions:
  - type: game_payoff
    config:
      check: payoff_vs_baseline
      baseline: "uniform_allocation"
      min_ratio: 1.0
```

---

## 7. Продвинутые сценарии

### 7.1. Турнир

Запуск всех baselines друг против друга + ваш агент:

```bash
uv run atp game tournament test_suites/game_prisoners_dilemma.yaml
```

Выводит матрицу: каждая строка — стратегия, каждый столбец — оппонент, ячейки — средние выплаты.

### 7.2. Кросс-таблица (crossplay)

```bash
uv run atp game crossplay test_suites/game_prisoners_dilemma.yaml
```

Детализированная таблица: cooperation rate, exploitability, payoff для каждой пары.

### 7.3. Шумные игры (trembling hand)

```yaml
game:
  name: "prisoners_dilemma"
  config:
    noise: 0.05            # 5% вероятность случайного действия
```

Проверяет устойчивость стратегии к «дрожащей руке» — случайным ошибкам в исполнении.

### 7.4. Дисконтирование

```yaml
game:
  name: "prisoners_dilemma"
  config:
    num_rounds: 100
    discount_factor: 0.95  # Будущие раунды менее ценны
```

Моделирует ситуацию, когда будущие выплаты менее важны — влияет на оптимальную стратегию.

---

## 8. Чек-лист игрового тестирования

```markdown
### Подготовка
- [ ] Установлен extra games: `uv sync --extra games`
- [ ] Определена целевая игра (см. таблицу в §2)
- [ ] Выбраны baseline-стратегии для сравнения
- [ ] Определены пороги assertions (payoff, exploitability, cooperation)

### Агент
- [ ] Агент возвращает structured artifact: {"action": ..., "reasoning": ...}
- [ ] action входит в available_actions
- [ ] Агент корректно парсит историю ходов из task.description
- [ ] Health endpoint отвечает

### Запуск
- [ ] YAML валидирован: `uv run atp validate --suite=game_suite.yaml`
- [ ] Первый прогон: `uv run atp game run game_suite.yaml -v`
- [ ] Результаты интерпретированы (payoff ratio, cooperation, exploitability)

### Продвинутое (опционально)
- [ ] Турнир: `atp game tournament`
- [ ] Кросс-таблица: `atp game crossplay`
- [ ] Тест с шумом: noise > 0
- [ ] Множественные эпизоды для статистической значимости (≥20)
```
