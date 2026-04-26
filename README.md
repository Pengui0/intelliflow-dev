# 🚦 IntelliFlow Urban Traffic Control

> **OpenEnv-compliant reinforcement learning environment for intelligent urban traffic signal optimisation.**
> A production-grade digital twin of a 4-way intersection and a 3×3 multi-agent grid, with a live 3D dashboard, trained DQN agent, LSTM inflow prediction, emergency vehicle preemption, and LLM meta-control.

**Team: Neural Ninjas 🥷 · Meta OpenEnv Hackathon Finals**

---

## Quick Start

```bash
# Docker (recommended)
docker build -t intelliflow .
docker run -p 7860:7860 intelliflow
# Open http://localhost:7860

# Local dev
pip install -r requirements.txt
uvicorn app.api.main:app --port 7860 --reload
```

---

## What's Inside

IntelliFlow is a complete RL training and evaluation platform for urban traffic signal control. It models:

- **12-lane physics** — Poisson arrivals, saturation flow discharge, spillback risk, gridlock detection
- **5 signal actions** — MAINTAIN, SWITCH_PHASE, EXTEND_GREEN, FORCE_ALL_RED, YIELD_MINOR
- **Weather degradation** — Rain (×0.75 discharge), Heavy Rain (×0.60), Fog (×0.85)
- **Incident injection** — lane blockage, breakdown, demand spikes with auto-expiry
- **Emergency vehicle preemption** — BFS path planning, phase locking ahead of vehicle arrival
- **LSTM inflow prediction** — pure-NumPy LSTM per node, 12-dim predicted arrivals
- **CO₂ and economic impact** — COPERT-grounded model, Indian fuel economics (₹95/litre)
- **LLM meta-controller** — GPT-compatible natural language traffic commands
- **Live DQN training** — Double DQN, experience replay, target network, epsilon-greedy, Adam — runs in the browser

---

## Hackathon Themes Covered

| Theme | Implementation |
|-------|---------------|
| Multi-Agent Interactions | 3×3 MARL grid with CTDE coordination, degree-aware spillback bonus, emergency vehicle preemption corridor |
| Long-Horizon Planning | 600–1800 step episodes, LSTM 12-step inflow forecasting per lane, NL Commander with duration-limited overrides |
| World Modeling | 57-dim physics sim (73-dim MARL): queues, arrivals, phase, weather, incidents, CO₂; COPERT emission model |
| Self-Improving Agent Systems | Live DQN with replay buffer, target network, weight persistence to disk + HF Hub, curriculum difficulty escalation |

---

## Tasks

### Single-Node Tasks

| Task ID | Name | Difficulty | Horizon | Baseline Score |
|---------|------|-----------|---------|---------------|
| `task_suburban_steady` | Suburban Steady Flow | Easy | 600 | ~0.55 |
| `task_urban_stochastic` | Urban Stochastic Rush | Medium | 1200 | ~0.42 |
| `task_rush_hour_crisis` | Rush Hour Crisis | Hard | 1800 | ~0.30 |

### MARL Grid Tasks (3×3, 9 agents, 73-dim obs)

| Task ID | Name | Difficulty | Horizon | Baseline Score |
|---------|------|-----------|---------|---------------|
| `task_grid_steady` | Grid: Suburban Steady | Medium | 600 | ~0.50 |
| `task_grid_rush` | Grid: Urban Stochastic | Hard | 1200 | ~0.36 |
| `task_grid_crisis` | Grid: Rush Hour Crisis | Hard | 1800 | ~0.24 |

---

## API Reference

### Core OpenEnv

```bash
POST /reset          # Create new episode session
POST /step           # Apply action, advance simulation (single-node)
POST /marl_step      # Apply per-node actions (MARL sessions)
GET  /state          # Full environment state + render_hints
GET  /tasks          # List all 6 tasks
GET  /tasks/{id}     # Specific task specification
POST /grader         # Score episode (0.0–1.0) with sub-scores + impact
POST /baseline       # Run baseline policy evaluation
GET  /analytics      # Rich episode analytics
POST /benchmark      # Multi-seed reproducibility benchmark
```

### MARL / A/B

```bash
POST /ab_reset       # Paired MARL vs fixed-cycle sessions
POST /ab_step        # Step both simultaneously, return deltas
POST /escalate_difficulty  # Increase arrival pressure (curriculum)
```

### Features

```bash
POST /weather        # Toggle weather mid-episode (CLEAR/RAIN/HEAVY_RAIN/FOG)
POST /incident       # Inject lane incident (BLOCKAGE/BREAKDOWN/DEMAND_SPIKE)
POST /emergency      # Dispatch emergency vehicle with BFS routing
POST /commander      # Natural language traffic command (LLM-powered)
POST /narrate        # Generate impact narrative (CO₂, fuel, economic value)
```

### Evaluation

```bash
GET  /proof_of_learning   # DQN vs pressure comparison for judges
GET  /training_progress   # Rolling reward curve across all episodes
```

### Visualisation

```bash
GET  /viz            # Live 2D dashboard
GET  /viz3d          # Three.js 3D WebGL ground view
GET  /viz/snapshot   # Lightweight data snapshot for external renderers
GET  /docs           # OpenAPI docs (Swagger UI)
```

---

## Observation Space

### Single-Node: 57-dim float32

| Component | Indices | Dim | Description |
|-----------|---------|-----|-------------|
| `queue_lengths` | 0–11 | 12 | Normalised queue per lane [0,1] |
| `throughput_recent` | 12–23 | 12 | 10-step rolling clearance rate |
| `arrival_intensity` | 24–35 | 12 | Estimated Poisson λ per lane (normalised) |
| `phase_onehot` | 36–39 | 4 | One-hot: [NS_GREEN, EW_GREEN, ALL_RED, NS_MINOR] |
| `phase_elapsed_norm` | 40 | 1 | Elapsed phase / max_duration |
| `fairness_score` | 41 | 1 | Normalised wait-time variance |
| `pressure_differential` | 42 | 1 | (NS − EW) / total ∈ [−1, 1] |
| `avg_delay_norm` | 43 | 1 | Rolling avg delay / 120s |
| `step_norm` | 44 | 1 | Episode progress [0, 1] |
| `spillback_flags` | 45–56 | 12 | Binary spillback risk per lane |

### MARL Extended: 73-dim float32 (base 57 + LSTM 12 + neighbors 4)

---

## Action Space (Discrete, 5 actions)

| ID | Name | Description |
|----|------|-------------|
| 0 | MAINTAIN | Hold current phase |
| 1 | SWITCH_PHASE | Toggle N-S ↔ E-W green |
| 2 | EXTEND_GREEN | Signal intent to hold green |
| 3 | FORCE_ALL_RED | Immediate all-red safety interval |
| 4 | YIELD_MINOR | Brief green for minor road right-turns |

---

## Example Usage

```python
import requests

BASE = "http://localhost:7860"

# 1. Start episode
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
        "action": 0  # replace with your policy
    }).json()
    obs = result["observation"]
    if result["done"]:
        break

# 3. Grade
score = requests.post(f"{BASE}/grader", json={"session_id": sid}).json()
print(f"Score:    {score['score']:.4f}")
print(f"CO₂ saved: {score['impact_summary']['co2_saved_g']:.1f}g")
print(f"Fuel saved: {score['impact_summary']['fuel_saved_ml']:.1f}ml")
```

---

## Baseline Policies

```bash
# Pressure (Max-Pressure, recommended baseline)
python inference.py --policy pressure --task all --seed 42

# Fixed-Cycle (Webster 30s/30s)
python inference.py --policy fixed_cycle --task all

# Random
python inference.py --policy random --task all

# DQN (requires dqn_weights.json)
python inference.py --policy dqn --task task_suburban_steady

# LLM (requires OPENAI_API_KEY)
export OPENAI_API_KEY=sk-...
python inference.py --policy llm --task task_suburban_steady
```

---

## Before/After Training Demo

```bash
# Run full proof-of-learning demo
python demo.py --host http://localhost:7860 --task all

# Or call the endpoint directly (judge-friendly)
curl http://localhost:7860/proof_of_learning
```

---

## Training

```bash
# DQN training (pure NumPy, no GPU required)
python train.py

# TRL + Unsloth GRPO (requires GPU, trl, unsloth)
pip install trl unsloth datasets
python trl_grpo_train.py --model unsloth/Qwen2.5-1.5B-Instruct --episodes 40
```

---

## Architecture

```
intelliflow/
├── app/
│   ├── core/
│   │   ├── environment.py      # TrafficEnvironment, MARLGridEnvironment, Observation, Action
│   │   ├── session.py          # Session, MARLSession, ABSession, SessionStore
│   │   ├── emergency.py        # EmergencyManager, BFS router, PreemptionScheduler
│   │   ├── lstm_predictor.py   # Pure-NumPy LSTM (input 12, hidden 64, output 12)
│   │   ├── meta_controller.py  # LLM Commander, template matcher, PolicyOverride
│   │   └── impact_calculator.py # COPERT CO₂/fuel/economic impact model
│   ├── tasks/
│   │   └── registry.py         # TaskSpec, EpisodeGrader, TASK_REGISTRY
│   ├── baseline/
│   │   └── policies.py         # PressurePolicy, FixedCycle, Random, LLM, DQNInline
│   ├── api/
│   │   ├── main.py             # FastAPI app, all REST endpoints (v1.2.0)
│   │   ├── dqn_weights.json    # Pre-trained DQN weights
│   │   └── lstm_weights.json   # Pre-trained LSTM weights
│   └── viz/
│       ├── dashboard.py        # HTML loader
│       └── dashboard.html      # Three.js 3D + 2D dashboard (~4,000 lines JS)
|       └── babylon-builders.js
├── inference.py                # CLI baseline evaluation
├── Blog.md
├── train_colab.py              # DQN training loop (pure NumPy)
├── trl_grpo_train.py           # TRL + Unsloth GRPO pipeline
├── demo.py                     # Before/After training demo for judges
├── openenv.yaml                # OpenEnv specification metadata
├── requirements.txt
├── uv.lock
├── pyproject.toml
├── Dockerfile
└── README.md
```

---

## Key Fixes in v1.2.0

- **Grader score inflation**: `theoretical_max_throughput` recalibrated — random policy no longer scores 1.0 on throughput
- **MARL action dispatch**: `/step` now correctly sends `Dict[int, int]` to `MARLSession.step()` with per-node DQN inference
- **Emergency manager coupling**: manager is now attached to session at creation, ticked on every `/step`
- **DQN gradient bug**: fixed duplicate forward pass in `accumulateGrad`; gradients now divided by batch size before Adam step
- **LSTM shuffle reproducibility**: `train_offline()` uses seeded numpy RNG for deterministic training
- **Weight persistence security**: `/save_weights` requires `X-Admin-Token` header
- **LLM Commander reasoning**: template matcher now correctly extracts matched keywords (not always ambulance template)
- **LSTM atomic write**: `_save_weights()` writes to temp file then renames atomically

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | No | Enables `/commander` and `/narrate` LLM endpoints |
| `HF_TOKEN` | No | Enables DQN weight persistence to HuggingFace Hub |
| `HF_REPO_ID` | No | HF repo for weight storage (default: `your-username/your-repo-name`) |
| `INTELLIFLOW_ADMIN_TOKEN` | No | Auth token for `/save_weights` (default: `dev-token-intelliflow`) |
| `INTELLIFLOW_DQN_WEIGHTS` | No | Override path for DQN weights file |
| `INTELLIFLOW_HOST` | No | Override server URL for inference/training scripts |

---

## Reward Function

```
R = w_throughput × (cleared / max_possible)     # vehicles moved
  + w_wait × Δqueue_norm                         # queue shrinking?
  - 0.3 × occupancy_rate²                        # congestion pressure
  + w_fairness × (-max_lane_deviation)           # starvation guard
  + w_switch × (-premature_switch_penalty)       # oscillation guard
  + w_spillback × (-spillback_severity)          # overflow guard
  - 8.0 × gridlock_fraction                      # cliff penalty
```

Seven independent process-supervision verifiers are applied at episode end via `/grader`:
throughput nonzero, delay below random, fairness acceptable, spillback controlled, no sustained gridlock, episode completion, above random floor.

---

## Expected Scores (seed 42)

| Task | Random | Fixed-Cycle | Pressure | Trained DQN |
|------|--------|-------------|---------|-------------|
| Suburban Steady | ~0.25 | ~0.48 | ~0.55 | ~0.68 |
| Urban Stochastic | ~0.18 | ~0.36 | ~0.42 | ~0.58 |
| Rush Hour Crisis | ~0.11 | ~0.24 | ~0.30 | ~0.45 |
| Grid Steady | ~0.22 | ~0.42 | ~0.50 | ~0.63 |
| Grid Rush | ~0.16 | ~0.30 | ~0.36 | ~0.50 |
| Grid Crisis | ~0.10 | ~0.20 | ~0.24 | ~0.38 |

---

## References

- Webster, F.V. (1958). *Traffic signal settings*. Road Research Technical Paper No. 39.
- Varaiya, P. (2013). Max pressure control of a network of signalized intersections. *Transportation Research Part C*.
- Lowrie, P.R. (1990). *SCATS — Sydney Coordinated Adaptive Traffic System*.
- Hochreiter, S. & Schmidhuber, J. (1997). Long Short-Term Memory. *Neural Computation*.
- Sutton, R.S. & Barto, A.G. (2018). *Reinforcement Learning: An Introduction*. 2nd ed. MIT Press.

---

*IntelliFlow v1.2.0 · Neural Ninjas · Meta OpenEnv Hackathon 2026*