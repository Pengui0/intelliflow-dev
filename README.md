---
title: IntelliFlow Openenv
emoji: 🚦
colorFrom: red
colorTo: green
sdk: docker
pinned: false
---

### Team: Neural Ninjas 🥷
# 🚦 IntelliFlow Urban Traffic Control

> **OpenEnv-compliant reinforcement learning environment for intelligent urban traffic signal optimisation.**  
> A production-grade digital twin of a 4-way intersection with dense reward shaping, 3 progressive tasks, and a live visualisation dashboard.

---

## Motivation

Traffic signal control is one of the highest-impact, underdigitised optimisation problems in urban infrastructure. In a typical city, poorly timed signals account for 5–10% of total vehicle delay and significant idle-emission overhead. Adaptive signal control — directing green phases based on real-time queue pressure — can reduce average vehicle delay by 20–40% compared to fixed-cycle timers.

This environment models that decision problem as a formal RL task: an agent observes the intersection state and selects signal actions each second, with dense reward feedback that reflects throughput, fairness, and congestion avoidance simultaneously.

---

## Architecture

```
intelliflow/
├── app/
|   ├──__init__.py   
│   ├── core/
|   ├── ├──__init__.py 
│   │   ├── environment.py    # Core simulation engine (TrafficEnvironment, Observation, Action)
│   │   └── session.py        # Session management for stateful API
│   ├── tasks/
|   |   ├──  __init__.py  
│   │   └── registry.py       # Task specs, graders (TaskSpec, EpisodeGrader)
│   ├── api/
|   |   ├── __init__.py
│   │   └── main.py           # FastAPI application, all REST endpoints
|   |   └── dqn_weights.json  # Pre-trained dqn agent
│   ├── baseline/
|   |   ├── __init__.py 
│   │   └── policies.py       # PressurePolicy, FixedCycle, Random, LLMPolicy
│   └── viz/
|       ├── __init__.py
│       └── dashboard.py      # Live HTML visualisation dashboard
├── inference.py              # Standalone CLI baseline evaluation script
├── openenv.yaml              # OpenEnv specification metadata
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Quick Start

### Docker (recommended)

```bash
docker build -t intelliflow .
docker run -p 7860:7860 intelliflow
# Open http://localhost:7860
```

### Local dev

```bash
pip install -r requirements.txt
uvicorn app.api.main:app --port 7860 --reload
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/`      | Landing page |
| `GET`  | `/health`| Service health check |
| `POST` | `/reset` | Create new episode session |
| `POST` | `/step`  | Apply action, advance simulation |
| `GET`  | `/state` | Full current environment state |
| `GET`  | `/tasks` | List all tasks + action/observation schemas |
| `GET`  | `/tasks/{task_id}` | Specific task specification |
| `POST` | `/grader`| Score current/completed episode |
| `POST` | `/baseline` | Run baseline policy evaluation |
| `GET`  | `/viz`   | Live visualisation dashboard |
| `GET`  | `/docs`  | OpenAPI documentation |

### Example flow

```python
import requests

BASE = "http://localhost:7860"

# 1. Reset
session = requests.post(f"{BASE}/reset", json={
    "task_id": "task_suburban_steady",
    "seed": 42
}).json()
sid = session["session_id"]
obs = session["observation"]

# 2. Step loop
for _ in range(600):
    result = requests.post(f"{BASE}/step", json={
        "session_id": sid,
        "action": 0  # MAINTAIN
    }).json()
    if result["done"]:
        break

# 3. Grade
score = requests.post(f"{BASE}/grader", json={"session_id": sid}).json()
print(f"Score: {score['score']:.4f}")
```

---

## Observation Space (57-dim float32)

| Component | Indices | Dim | Description |
|-----------|---------|-----|-------------|
| `queue_lengths` | 0–11 | 12 | Normalised queue per lane [0,1] |
| `throughput_recent` | 12–23 | 12 | 10-step rolling throughput per lane |
| `arrival_intensity` | 24–35 | 12 | Estimated Poisson λ per lane (normalised) |
| `phase_onehot` | 36–39 | 4 | One-hot: [NS_GREEN, EW_GREEN, ALL_RED, NS_MINOR] |
| `phase_elapsed_norm` | 40 | 1 | Elapsed phase time / max_duration |
| `fairness_score` | 41 | 1 | Normalised wait-time variance |
| `pressure_differential` | 42 | 1 | (NS − EW pressure) / total ∈ [−1, 1] |
| `avg_delay_norm` | 43 | 1 | Rolling avg delay / 120s |
| `step_norm` | 44 | 1 | Episode progress [0, 1] |
| `spillback_flags` | 45–56 | 12 | Binary spillback risk per lane |

---

## Action Space (Discrete, 5 actions)

| ID | Name | Description |
|----|------|-------------|
| 0 | MAINTAIN | Hold current phase |
| 1 | SWITCH_PHASE | Toggle N-S ↔ E-W green |
| 2 | EXTEND_GREEN | Signal intent to hold green (delay auto-switch) |
| 3 | FORCE_ALL_RED | Immediate all-red safety interval |
| 4 | YIELD_MINOR | Brief green for minor road right-turns |

---

## Reward Function (dense, every step)

```
R = w_throughput × vehicles_cleared
  + w_wait       × (−total_queue)
  + w_fairness   × (−fairness_variance)
  + w_switch     × (−phase_switched)
  + w_spillback  × (−spillback_count)
  + w_emission   × (−total_queue)         # emission proxy
  − 10.0          × gridlock_active
```

Typical range: **[−20, +15]** per step. No sparse terminal rewards — the agent receives meaningful gradient signal throughout the trajectory.

---

## Tasks

### Task 1: Suburban Steady Flow `[EASY]` — Horizon: 600 steps

Low, symmetric, near-deterministic arrivals (λ ≈ 0.2 veh/step/lane). The optimal policy is straightforward green time balancing. Useful for verifying basic signal timing logic and establishing performance baselines.

**Grader formula:**
```
Score = 0.40 × throughput_efficiency
      + 0.30 × delay_score
      + 0.20 × fairness_score
      + 0.10 × stability_score
```

Expected pressure-baseline score: **~0.55**

---

### Task 2: Urban Stochastic Rush `[MEDIUM]` — Horizon: 1200 steps

Heavy morning rush with asymmetric N-S dominance (λ_N ≈ 0.45). Lambda values are randomly perturbed each episode. The agent must adapt timing dynamically and predict inflow intensity to prevent starvation of minor approaches.

**Grader formula:**
```
Score = 0.35 × throughput_efficiency
      + 0.30 × delay_score
      + 0.20 × fairness_score
      + 0.15 × spillback_resilience
```

Expected pressure-baseline score: **~0.42**

---

### Task 3: Rush Hour Crisis `[HARD]` — Horizon: 1800 steps

Near-saturation arrivals, rain reducing discharge by 25%, one lane blocked by incident. Congestion cascades are likely. The agent must survive gridlock and maintain minimum viable throughput. Early termination on sustained gridlock.

**Grader formula:**
```
Score = 0.30 × throughput_efficiency
      + 0.25 × delay_score
      + 0.20 × survival_bonus
      + 0.15 × fairness_score
      + 0.10 × stability_score
```

Expected pressure-baseline score: **~0.30**

---

## Baseline Policies

### Pressure Policy (recommended baseline)

Implements Max-Pressure signal control (Varaiya, 2013): switch phase when pressure differential exceeds threshold, extend green when current approach is heavily loaded.

```bash
python inference.py --policy pressure --task all --seed 42
```

### Fixed-Cycle Controller

Webster's optimal fixed-time controller (30s N-S, 30s E-W, 3s amber).

```bash
python inference.py --policy fixed_cycle --task all
```

### LLM Agent (OpenAI)

```bash
export OPENAI_API_KEY=sk-...
python inference.py --policy llm --task task_suburban_steady --seed 42
```

### Using the `/baseline` endpoint

```bash
curl -X POST http://localhost:7860/baseline \
  -H "Content-Type: application/json" \
  -d '{"task_id": "task_suburban_steady", "policy": "pressure", "seed": 42}'
```

---

## Grader

```bash
# Via API
curl -X POST http://localhost:7860/grader \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<your-session-id>"}'
```

Returns:
```json
{
  "score": 0.5731,
  "sub_scores": {
    "throughput_efficiency": 0.6120,
    "delay_score": 0.5240,
    "fairness_score": 0.6800,
    "stability_score": 0.4900,
    "spillback_resilience": 0.7200,
    "survival_bonus": 1.0000
  },
  "trajectory_summary": {
    "total_cleared": 482,
    "total_arrived": 531,
    "steps_survived": 600,
    "avg_delay_seconds": 18.4
  }
}
```

---

## Visualisation

Open `http://localhost:7860/viz` for the live dashboard featuring:

- Real-time intersection queue map with colour-coded signal states
- Per-lane queue bar charts (green → amber → red as queues fill)
- Live reward trajectory chart
- Episode metrics: throughput, avg delay, fairness, score
- Run the pressure policy live from the browser
- ### Dashboard Preview

![Live Dashboard](assets/dashboard.png)

![Easy - Suburban Steady Flow](assets/Easy%20-%20suburban%20steady%20flow.png)

![Medium - Urban Stochastic Rush](assets/Medium%20-%20urban%20stochastic%20rush.png)

![Hard - Rush Hour Crisis](assets/Hard%20-%20rush%20hour%20crisis.png)
---

## Environment Design Notes

**Simulation model:** Discrete-time probabilistic digital twin. Each step = 1 second.  
**Arrivals:** Poisson sampling per lane with configurable λ, optionally perturbed per episode.  
**Discharge:** Constrained by saturation flow rate × weather factor × green permission.  
**Gridlock detection:** ≥70% of lanes at ≥90–95% capacity sustained for 20 steps triggers early termination.  
**Phase locking:** Minimum phase duration (5 steps) prevents oscillatory toggling — actions during lock are silently ignored.

---

## Expected Baseline Scores (seed=42)

| Task | Pressure | Fixed-Cycle | Random |
|------|----------|-------------|--------|
| Suburban Steady | ~0.55 | ~0.48 | ~0.25 |
| Urban Stochastic | ~0.42 | ~0.36 | ~0.18 |
| Rush Hour Crisis | ~0.30 | ~0.24 | ~0.11 |

LLM agents typically match or slightly exceed the pressure policy on tasks 1–2, and benefit from the pressure fallback on task 3.

---

## References

- Varaiya, P. (2013). Max pressure control of a network of signalized intersections. *Transportation Research Part C*, 36, 177–195.
- Webster, F.V. (1958). *Traffic signal settings*. Road Research Technical Paper No. 39. HMSO, London.
- Lowrie, P.R. (1990). *SCATS — Sydney Coordinated Adaptive Traffic System*. Roads and Traffic Authority NSW.
- Sutton, R.S. & Barto, A.G. (2018). *Reinforcement Learning: An Introduction*. 2nd ed. MIT Press.

---

*IntelliFlow v1.0.0 — OpenEnv Hackathon Submission*
