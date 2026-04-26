# 🚦 IntelliFlow: Teaching AI to Outsmart Traffic Jams in Real Time

*A deep-dive into building a production-grade, OpenEnv-compliant reinforcement learning environment for urban traffic signal optimisation — from first principles to a live 3D dashboard.*

---

## The Problem Nobody Talks About

Every day, millions of people sit at red lights watching an empty perpendicular road get a full 30-second green. The intersection isn't broken — it just doesn't know any better. Fixed-cycle signal controllers, invented in the 1950s, still govern the majority of urban intersections worldwide. They're predictable, cheap, and wrong roughly half the time.

Field studies (Lowrie 1990, SCATS deployment data) consistently show that adaptive signal control reduces average vehicle delay by **20–40%** compared to Webster's fixed-cycle baseline. That's not a marginal improvement — that's the difference between a commute that works and one that doesn't.

IntelliFlow is our answer to that problem: a full reinforcement learning environment, a trained DQN agent, a 3×3 multi-agent grid, and a live 3D dashboard — all compliant with the OpenEnv specification, all running in a single Docker container.

---

## What We Built

IntelliFlow is a **digital twin of an urban intersection** (or a 3×3 grid of them) that a reinforcement learning agent can control in real time. The environment models:

- **12-lane physics**: Poisson arrivals, saturation flow discharge, lane capacity, queue buildup
- **Signal phases**: NS_GREEN, EW_GREEN, ALL_RED, NS_MINOR — with minimum/maximum duration constraints
- **Weather degradation**: Rain (×0.75 discharge), Heavy Rain (×0.60), Fog (×0.85)
- **Incident injection**: Lane blockage, breakdown, demand spikes — auto-expiring after N steps
- **Emergency vehicle preemption**: BFS path planning across the grid, phase locking ahead of vehicle arrival
- **CO₂ and economic impact**: COPERT-grounded idle emission model, Indian fuel economics (₹95/litre petrol)
- **LSTM inflow prediction**: Pure-NumPy LSTM per node, 12-dim predicted arrivals augmenting MARL observations

Six benchmark tasks span three difficulty levels:

| Task | Mode | Horizon | Difficulty | Pressure Baseline |
|------|------|---------|-----------|------------------|
| Suburban Steady Flow | Single | 600 | Easy | 0.55 |
| Urban Stochastic Rush | Single | 1200 | Medium | 0.42 |
| Rush Hour Crisis | Single | 1800 | Hard | 0.30 |
| Grid: Suburban Steady | MARL 3×3 | 600 | Medium | 0.50 |
| Grid: Urban Stochastic | MARL 3×3 | 1200 | Hard | 0.36 |
| Grid: Rush Hour Crisis | MARL 3×3 | 1800 | Hard | 0.24 |

---

## Four Hackathon Themes, One System

The Meta OpenEnv Hackathon asked for environments covering four themes. IntelliFlow covers all four in a unified, coherent way — not as bolted-on features, but as load-bearing components of the simulation.

### 1. Multi-Agent Interactions

The 3×3 MARL grid puts nine independent traffic agents on adjacent intersections, each able to see its own state plus LSTM-predicted inflows and its neighbors' queue pressures. The reward structure implements **CTDE (Centralised Training, Decentralised Execution)**: each agent's reward is shaded by a coordination bonus that penalises spillback in adjacent nodes.

```
local_coord_bonus = -0.15 × degree_scale × (0.6 × own_spill + 0.4 × neighbor_spill / n_neighbors)
```

Corner nodes (2 neighbors) get a lighter penalty than the hub node 4 (4 neighbors) — because holding them to hub-level coordination standards is unfair when they can observe fewer nodes. This is not a cosmetic detail; it materially changes convergence.

Emergency vehicles add a genuine adversarial element: an ambulance dispatched from node 0 to node 8 forces a phase preemption corridor across up to five intersections, temporarily overriding agent decisions and creating a secondary coordination challenge for all nine agents simultaneously.

### 2. Long-Horizon Planning & Instruction Following

At 1800 steps for the crisis tasks, the agent must make thousands of correlated decisions without forgetting what happened 600 steps ago. Two components address this:

**LSTM Inflow Predictor**: A pure-NumPy LSTM (no PyTorch dependency) trained offline at episode end. It observes 12-dimensional arrival vectors and predicts next-step inflows per lane. The 12-dim prediction is concatenated to each MARL agent's base 57-dim observation, creating the full 73-dim extended vector. When the LSTM is accurate, agents can start switching phases before queues become critical — moving from reactive to predictive control.

**Natural Language Commander**: A GPT-compatible meta-controller that translates operator commands into phase overrides and reward weight deltas. "Prioritise north-south flow for 60 steps" is parsed by the LLM into `{"phase_overrides": {0: "NS_GREEN", ...}, "override_duration": 60}` and injected into the environment's reward function. With no API key present, a template matcher handles 8 command families with zero latency. The key design decision: the override decays automatically after `override_duration` steps, and the meta-controller ticks on every `/step` call to restore original weights when the override expires.

### 3. World Modeling

The 57-dimensional observation vector is a complete physical model of intersection state:

```
obs = queue_lengths[12]        # normalised to capacity
    + throughput_recent[12]    # 10-step rolling clearance rate  
    + arrival_intensity[12]    # Poisson λ estimate per lane
    + phase_onehot[4]          # current signal phase
    + phase_elapsed_norm[1]    # how long current phase has run
    + fairness_score[1]        # normalised wait-time variance
    + pressure_differential[1] # (NS - EW) / total ∈ [-1, 1]
    + avg_delay_norm[1]        # rolling average delay / 120s
    + step_norm[1]             # episode progress
    + spillback_flags[12]      # binary spillback risk per lane
```

Weather degrades discharge multipliers. Incidents corrupt saturation flow rates. Emergency vehicles lock phase states. All of this flows through the same observation vector — the agent sees one consistent view of the world, whether it's a clear suburban afternoon or a heavy-rain crisis with a blocked lane and an ambulance inbound.

The **ImpactCalculator** turns this simulation data into real-world numbers. It computes CO₂ saved relative to a fixed-cycle baseline using the COPERT idle emission model (0.5 ml/s per idling vehicle, 2.31 g CO₂/ml petrol) and converts savings to ₹ using current Indian fuel economics. "Your agent saved 47g of CO₂ — equivalent to 0.002 trees absorbing carbon for a full year" is a factual statement, not a marketing claim.

### 4. Self-Improving Agent Systems

The DQN agent in IntelliFlow is not a static loaded model. It trains live, during the episode, in the browser.

**Architecture**: 57→128→128→64→5 (or 73→128→128→64→5 for MARL). Pure JavaScript, no ONNX, no WebAssembly — a plain NumPy-equivalent matrix implementation running in the browser's main thread with a Web Worker timer to avoid tab throttling.

**Training**: Double DQN with experience replay (10,000-step buffer), target network sync every 50 gradient steps, Adam optimiser, gradient clipping at norm 1.0, epsilon-greedy decay from 1.0 → 0.05 over ~30,000 steps.

**Key fix in v1.2.0**: The gradient accumulation bug. In the original implementation, `accumulateGrad` called `forward()` twice — once to get Q-values and once again inside the loss computation — meaning the BPTT cache was stale by the time `backward()` ran. The fix: one forward pass whose layer cache is immediately consumed by backward. Separately, gradients were not divided by batch size before the Adam step, making the effective learning rate 64× too large. Both are corrected in the version you're reading.

**Persistence**: Weights save to the server every 5 training steps and on episode end via `POST /save_weights` with an admin token header. On HF Spaces, they sync to a HuggingFace Hub repository so cold starts restore the trained model automatically. The `/proof_of_learning` endpoint gives judges a single call that runs both DQN and pressure policies, computes the delta, and returns a structured verdict.

**Curriculum escalation**: When the MARL agent's rolling score exceeds 0.70 for 5 consecutive episodes, `maybe_escalate()` bumps arrival lambdas by 5% across all nine nodes. The agent never gets to coast.

---

## The Reward Function: Why It's Hard

Most traffic RL papers use throughput as the reward. IntelliFlow doesn't, because throughput alone is gameable. An agent that figures out it can starve the east-west approaches entirely to maximise north-south throughput will score well on throughput and terribly on actual traffic management.

The reward has seven independent components:

```python
R = w_throughput × (cleared / max_possible)          # 1. Did vehicles move?
  + w_wait × clip(delta_queue / norm, -1, 1)          # 2. Is the queue shrinking?
  - 0.3 × occupancy_rate²                             # 3. Congestion pressure
  + w_fairness × (-max_deviation(main_lanes))         # 4. Is anyone being starved?
  + w_switch × (-premature_switch_penalty)            # 5. Is switching justified?
  + w_spillback × (-spillback_severity)               # 6. Are lanes about to overflow?
  - 8.0 × gridlock_fraction                           # 7. Is the grid locked?
```

The fairness term uses max-deviation rather than variance. Variance averages across all lanes — one severely starved lane gets hidden by eleven healthy ones. Max-deviation is sensitive to the worst single approach, which is the right thing to penalise in a real intersection.

The switch penalty has a nuance: premature switches (before 15 steps) are only penalised if the pressure differential doesn't justify them. If NS pressure is 0.35 higher than EW and the agent switches after 8 steps, that's a reasonable call and gets only 30% of the full penalty.

At episode end, the `/grader` endpoint applies seven independent process-supervision verifiers to the trajectory — checking throughput, delay, fairness, spillback, gridlock, episode completion, and LOS floor. All seven must pass for a "PASS" verdict. This is the reward hacking guard: no single weak signal to exploit.

---

## Engineering Decisions Worth Noting

**Session management**: Every `/reset` call creates a UUID session with a 2-hour TTL. Sessions are stored in a Python dict with probabilistic cleanup (1-in-50 creates triggers a scan). The TTL was extended from 1 hour to 2 hours after a demo almost expired mid-presentation.

**MARLSession action dispatch**: The original `/step` endpoint passed a bare integer to `MARLSession.step()`, which silently broadcast it to all nine nodes without per-node DQN selection. The fix sends a `Dict[int, int]` — each node gets its own obs-based action from the cached DQN policy. The cached policy is a process-level singleton that loads weights once and is invalidated on `/save_weights` calls.

**Emergency manager coupling**: The original `/emergency` endpoint created a throwaway `EmergencyManager` that was never ticked. The fix attaches the manager to the session at creation time (`session.emergency = EmergencyManager(grid_envs)`) and ticks it on every `/step` call. Preemption windows actually work now.

**Grader score inflation**: The original `theoretical_max_throughput` values were so low that even a random policy scored 1.0 on throughput efficiency. They've been recalibrated to realistic per-step vehicle rates — the random policy now scores where it should (30–40%), and a trained agent scores where it should (65–75%).

**LSTM shuffle reproducibility**: `train_offline()` was calling `random.shuffle(indices)` without a seeded RNG, making episode-end training non-reproducible with the same seed. Fixed to `np.random.default_rng(seed=len(data)).shuffle(indices)`.

---

## The 3D Dashboard

The live visualisation runs in Three.js (r128), building a complete urban scene: satellite-textured road surface, 24 buildings with window grids and rooftop HVAC details, 35 trees with canopy highlighting, traffic light poles with proper housing geometry, bollards, street lamps, zebra crossings (corrected in v1.2.0 to run perpendicular to lane direction, not parallel).

Four camera modes: Ground (street level, 2.5m), Elevated (isometric), Overhead (55m), Cinematic (rotating orbit). Mouse drag + scroll for free camera control.

The car pool allocates 3 meshes per lane (36 total) with body, cabin, windshield, four wheels with rims, headlights, and tail lights. Emergency vehicles get full custom geometry — ambulance with cross markings and red/blue alternating beacons, fire truck with ladder rack and chrome trim, police car with department text and strobing lights. All vehicles respect the 3D stop line, queue realistically with 2.2-unit bumper-to-bumper spacing, and yield to conflicting traffic in the box before their stop line.

Weather changes update the Three.js scene: rain spawns 1,600–3,200 `LineSegments` streaks falling at realistic drift angles, fog uses a 500-point `Points` cloud hugging the ground, puddle shimmer adds a wet road plane above the intersection surface. The satellite map underneath re-renders only when weather changes, using an offscreen canvas cache.

---

## What the Numbers Say

On `task_suburban_steady` (seed 42, 600 steps):

| Policy | Score | Avg Delay | Throughput |
|--------|-------|-----------|-----------|
| Random | ~0.25 | 48s | Low |
| Fixed-Cycle (Webster) | ~0.48 | 28s | Moderate |
| Pressure (Max-Pressure) | ~0.55 | 22s | Good |
| Trained DQN (200 episodes) | ~0.68 | 14s | High |

The `/proof_of_learning` endpoint returns this comparison live. `/training_progress` shows the rolling reward curve across all completed episodes. `/benchmark` runs multi-seed evaluation with mean ± std.

On the hard MARL crisis task with all nine nodes, a DQN agent that's seen 100+ episodes achieves ~0.35–0.42 — meaningfully above the 0.24 pressure baseline on a task designed to gridlock random and fixed-cycle policies within 400 steps.

---

## Try It

```python
import requests

BASE = "https://your-space.hf.space"

# Start an episode
session = requests.post(f"{BASE}/reset", json={
    "task_id": "task_suburban_steady",
    "seed": 42
}).json()

sid = session["session_id"]
obs = session["observation"]

# Run 600 steps
for step in range(600):
    result = requests.post(f"{BASE}/step", json={
        "session_id": sid,
        "action": 0  # MAINTAIN — replace with your policy
    }).json()
    obs = result["observation"]
    if result["done"]:
        break

# Grade the episode
score = requests.post(f"{BASE}/grader", json={"session_id": sid}).json()
print(f"Score: {score['score']:.4f}")
print(f"CO₂ saved: {score['impact_summary']['co2_saved_g']:.1f}g")
```

The full API is at `/docs`. The dashboard is at `/viz` or `/viz3d`. The proof of learning is at `/proof_of_learning`.

---

## What We'd Do With More Time

The LSTM predictor trains offline at episode end — the natural next step is online LSTM fine-tuning during the episode using the sliding arrival window. The MARL coordination bonus is currently a hand-tuned heuristic; learned communication (QMIX or MADDPG) would let agents transmit compressed queue state rather than reading it from the observation vector. The NL Commander currently uses template matching as its fallback — a small fine-tuned model for traffic command parsing would eliminate the OpenAI dependency entirely.

The 3D visualiser is built on Three.js r128 because that's what's on the Cloudflare CDN. Upgrading to r160+ would give access to `CapsuleGeometry` for better vehicle silhouettes and `WebGPURenderer` for rain particle volumes that actually look like rain in a storm.

And the battle mode — fixed-cycle timer vs your trained DQN, same seed, same scenario, step by step — needs a proper Elo rating system so you can track whether each training run actually made the agent better at the specific task you care about.

---

## Acknowledgements

Webster's 1958 delay formula. Varaiya's 2013 Max-Pressure proof. Lowrie's SCATS field data. The COPERT emission model. The team behind FastAPI, Three.js, and the OpenEnv specification. And every traffic light that's ever made someone sit through a full red cycle watching an empty road.

---

*IntelliFlow v1.2.0 · Neural Ninjas · Meta OpenEnv Hackathon 2025*

*Source: [GitHub](https://github.com/your-username/intelliflow) · Live demo: [HuggingFace Spaces](https://huggingface.co/spaces/your-username/intelliflow)*