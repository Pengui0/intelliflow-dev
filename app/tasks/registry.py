"""
IntelliFlow Task Registry  v1.2.0
Three single-node + three grid benchmark tasks with programmatic graders.

Fixes in v1.2.0
---------------
- theoretical_max_throughput recalibrated so scores are NOT inflated to 1.0
  on the first step.  Values are now per-step vehicle rates, not total counts.
- EpisodeGrader.grade() throughput normalisation uses
  spec.theoretical_max_throughput * steps_survived  (was already correct)
  but the spec values were set so low that even a random policy scored 1.0
  on throughput_efficiency.  Values tripled/quadrupled to realistic levels.
- Grader formula doc-strings corrected (no more phantom ×3 factor comment).
- build_env() guard for grid tasks unchanged (still raises ValueError).
- TASK_REGISTRY ordering preserved.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from app.core.environment import (
    TrafficEnvironment, N_LANES, N_ACTIONS, OBS_DIM, MARL_OBS_DIM,
)


# ---------------------------------------------------------------------------
# Task metadata schema
# ---------------------------------------------------------------------------

@dataclass
class TaskSpec:
    task_id:    str
    name:       str
    description: str
    difficulty: str          # easy | medium | hard
    horizon:    int
    n_actions:  int
    obs_dim:    int
    action_descriptions: Dict[int, str]
    env_config: Dict[str, Any]
    grader_description: str
    theoretical_max_throughput: float   # vehicles/step upper bound (per node)
    acceptable_avg_delay: float         # seconds, threshold for full score


# ---------------------------------------------------------------------------
# Shared action descriptions
# ---------------------------------------------------------------------------

_ACTION_DESC: Dict[int, str] = {i: d for i, d in enumerate([
    "Maintain current phase",
    "Switch to orthogonal phase",
    "Extend green by 5s",
    "Force all-red safety interval",
    "Yield to minor roads",
])}


# ---------------------------------------------------------------------------
# Task 1: Suburban Steady Flow (EASY)
# ---------------------------------------------------------------------------

TASK_SUBURBAN = TaskSpec(
    task_id="task_suburban_steady",
    name="Suburban Steady Flow",
    description=(
        "A single four-way intersection in a quiet suburb with low, symmetric "
        "vehicle arrivals (~1.12 veh/step total demand). Inflow is nearly "
        "deterministic and balanced across all approaches. The optimal policy "
        "maintains fair green-time allocation with minimal phase thrashing. "
        "Calibrated so a competent agent reaches ~90-100% throughput efficiency, "
        "and a random agent stays around 50-60%."
    ),
    difficulty="easy",
    horizon=600,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions=_ACTION_DESC,
    env_config={
        "horizon": 600,
        # Total demand 1.12/step. Symmetric NS=EW=0.56 — fair-split optimal.
        "arrival_lambdas": [0.18, 0.05, 0.18, 0.05,
                            0.18, 0.05, 0.18, 0.05,
                            0.05, 0.05, 0.05, 0.05],
        "sat_flows":            [0.95] * N_LANES,
        "min_phase_duration":   5,
        "max_phase_duration":   60,
        "all_red_duration":     3,
        "lane_capacity":        30,
        "stochastic_lambdas":   False,
        "weather":              "clear",
        "gridlock_threshold":   0.95,
        "w_throughput":  1.2,
        "w_wait":       -0.8,
        "w_fairness":   -0.4,
        "w_switch":     -0.25,
        "w_spillback":  -0.6,
        "w_emission":    0.0,
    },
    grader_description=(
        "Score = 0.40*(throughput_efficiency) + 0.30*(delay_score) "
        "+ 0.20*(fairness_score) + 0.10*(stability_score). "
        "theoretical_max_throughput=1.10 veh/step calibrated to the 1.12 veh/step "
        "arrival rate, so a perfect agent that clears every arrival reaches ~100% "
        "throughput score. Random/baseline agents score 40-60%."
    ),
    # arrivals=1.12/step, theo_max=1.10 → max achievable ratio ~101.8% (clamped to 1.0).
    # A perfect agent can score 1.0 on throughput; baseline ~0.5; random ~0.3.
    theoretical_max_throughput=1.10,
    acceptable_avg_delay=25.0,
)


# ---------------------------------------------------------------------------
# Task 2: Urban Stochastic Rush (MEDIUM)
# ---------------------------------------------------------------------------

TASK_URBAN = TaskSpec(
    task_id="task_urban_stochastic",
    name="Urban Stochastic Rush",
    description=(
        "A busy urban intersection with bursty, asymmetric inflows "
        "(~1.92 veh/step total, NS-dominant 1.16 vs EW 0.76). Morning rush "
        "creates heavy North-South flow while East-West varies stochastically. "
        "Lambda values are perturbed ±30% each episode. The agent must adapt "
        "timing dynamically — fixed-cycle baselines are penalised for not "
        "favouring the heavier axis. Solvable but requires real adaptation; "
        "random agents start to spillback in the second half."
    ),
    difficulty="medium",
    horizon=1200,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions=_ACTION_DESC,
    env_config={
        "horizon": 1200,
        # Total 1.92/step. NS=1.16 (heavy), EW=0.76 (light). 60-40 split required.
        "arrival_lambdas": [0.38, 0.10, 0.38, 0.10,
                            0.22, 0.08, 0.22, 0.08,
                            0.10, 0.10, 0.08, 0.08],
        "sat_flows":           [0.90] * N_LANES,
        "min_phase_duration":  5,
        "max_phase_duration":  90,
        "all_red_duration":    3,
        "lane_capacity":       40,
        "stochastic_lambdas":  True,
        "weather":             "clear",
        "gridlock_threshold":  0.92,
        "w_throughput":  1.0,
        "w_wait":       -0.9,
        "w_fairness":   -0.5,
        "w_switch":     -0.25,
        "w_spillback":  -0.7,
        "w_emission":    0.0,
    },
    grader_description=(
        "Score = 0.35*(throughput_efficiency) + 0.30*(delay_score) "
        "+ 0.20*(fairness_score) + 0.15*(spillback_resilience). "
        "theoretical_max_throughput=1.85 veh/step (calibrated to 1.92 arrival rate, "
        "leaving ~4% headroom for lost cycles during phase switches). "
        "spillback_resilience = 1 - min(peak_spillback_fraction, 1.0)."
    ),
    # arrivals=1.92/step, theo_max=1.85 → max ratio ~104%. Adaptive policies score
    # ~0.85+, fixed-cycle ~0.55-0.65 (no asymmetric advantage), random ~0.35.
    theoretical_max_throughput=1.85,
    acceptable_avg_delay=40.0,
)


# ---------------------------------------------------------------------------
# Task 3: Rush Hour Crisis (HARD)
# ---------------------------------------------------------------------------

TASK_CRISIS = TaskSpec(
    task_id="task_rush_hour_crisis",
    name="Rush Hour Crisis",
    description=(
        "High-pressure rush hour with rain (×0.80 discharge), one blocked "
        "northbound lane simulating an incident, and 2.40 veh/step demand. "
        "Margin is tight: oracle drain is 3.52 veh/step, so the agent has "
        "~30% headroom. Random and fixed-cycle policies WILL gridlock — only "
        "an agent that tracks NS pressure asymmetry and adapts phase length "
        "survives all 1800 steps. Mathematically solvable; demonstrably hard."
    ),
    difficulty="hard",
    horizon=1800,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions=_ACTION_DESC,
    env_config={
        "horizon": 1800,
        # Total 2.40/step. NS=1.36 EW=1.04 — moderate skew, blocked lane 0
        # makes NS effectively only 5 lanes active during NS green.
        "arrival_lambdas": [0.42, 0.12, 0.42, 0.12,
                            0.32, 0.10, 0.32, 0.10,
                            0.14, 0.14, 0.10, 0.10],
        "sat_flows":           [0.88] * N_LANES,
        "min_phase_duration":  6,
        "max_phase_duration":  75,
        "all_red_duration":    3,
        "lane_capacity":       45,
        "stochastic_lambdas":  True,
        "weather":             "rain",
        "incident_lane":       0,
        "gridlock_threshold":  0.92,
        "w_throughput":  1.0,
        "w_wait":       -1.0,
        "w_fairness":   -0.45,
        "w_switch":     -0.20,
        "w_spillback":  -0.85,
        "w_emission":    0.0,
    },
    grader_description=(
        "Score = 0.30*(throughput_efficiency) + 0.25*(delay_score) "
        "+ 0.20*(survival_bonus) + 0.15*(fairness_score) + 0.10*(stability_score). "
        "theoretical_max_throughput=2.15 veh/step (calibrated to 2.40 arrival rate "
        "minus inevitable 10% loss to rain + blocked lane + phase-switch overhead). "
        "survival_bonus = steps_survived / horizon × (0.5 if gridlocked). "
        "An adaptive agent that exploits NS pressure asymmetry can survive."
    ),
    # arrivals=2.40, theo_max=2.15 → max ratio ~112% (clamped to 1.0).
    # Trained DQN: 0.65-0.75. Pressure baseline: ~0.45. Random: gridlocks ~0.20.
    theoretical_max_throughput=2.15,
    acceptable_avg_delay=70.0,
)


# ---------------------------------------------------------------------------
# Grid Tasks — 3×3 MARL versions of the three single-node tasks
# ---------------------------------------------------------------------------

def _grid_config(base_env_config: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of base_env_config with grid_mode flag set."""
    cfg = dict(base_env_config)
    cfg["grid_mode"] = True
    return cfg


TASK_GRID_STEADY = TaskSpec(
    task_id="task_grid_steady",
    name="Grid: Suburban Steady Flow (3×3)",
    description=(
        "A 3×3 grid of nine suburban intersections under steady, symmetric "
        "flow. Agents must coordinate across nodes to prevent queue cascade. "
        "Per-node dynamics mirror task_suburban_steady; each agent's "
        "observation is extended with LSTM inflow predictions and neighbor "
        "queue pressures."
    ),
    difficulty="medium",
    horizon=600,
    n_actions=N_ACTIONS,
    obs_dim=MARL_OBS_DIM,          # 73 = 57 base + 12 LSTM + 4 neighbor
    action_descriptions=_ACTION_DESC,
    env_config=_grid_config(TASK_SUBURBAN.env_config),
    grader_description=(
        "Same formula as task_suburban_steady applied per node; "
        "composite score = mean across 9 nodes. "
        "Throughput is divided by 9 before normalisation to keep score in [0,1]."
    ),
    theoretical_max_throughput=TASK_SUBURBAN.theoretical_max_throughput,
    acceptable_avg_delay=TASK_SUBURBAN.acceptable_avg_delay,
)

TASK_GRID_RUSH = TaskSpec(
    task_id="task_grid_rush",
    name="Grid: Urban Stochastic Rush (3×3)",
    description=(
        "A 3×3 grid of nine urban intersections under stochastic, asymmetric "
        "rush-hour flow. Per-node dynamics mirror task_urban_stochastic. "
        "Agents must coordinate green corridors to pass peak demand waves "
        "across the network without inducing cascade spillback."
    ),
    difficulty="hard",
    horizon=1200,
    n_actions=N_ACTIONS,
    obs_dim=MARL_OBS_DIM,
    action_descriptions=_ACTION_DESC,
    env_config=_grid_config(TASK_URBAN.env_config),
    grader_description=(
        "Same formula as task_urban_stochastic applied per node; "
        "composite score = mean across 9 nodes. "
        "Throughput is divided by 9 before normalisation."
    ),
    theoretical_max_throughput=TASK_URBAN.theoretical_max_throughput,
    acceptable_avg_delay=TASK_URBAN.acceptable_avg_delay,
)

TASK_GRID_CRISIS = TaskSpec(
    task_id="task_grid_crisis",
    name="Grid: Rush Hour Crisis (3×3)",
    description=(
        "A 3×3 grid under maximum load — rain, a blocked lane per node, "
        "and near-saturation arrivals. Per-node dynamics mirror "
        "task_rush_hour_crisis. Surviving gridlock across all 9 nodes "
        "simultaneously is the primary challenge. Early termination fires "
        "if any node sustains gridlock for 20 consecutive steps."
    ),
    difficulty="hard",
    horizon=1800,
    n_actions=N_ACTIONS,
    obs_dim=MARL_OBS_DIM,
    action_descriptions=_ACTION_DESC,
    env_config=_grid_config(TASK_CRISIS.env_config),
    grader_description=(
        "Same formula as task_rush_hour_crisis applied per node; "
        "composite score = mean across 9 nodes. "
        "Throughput is divided by 9 before normalisation."
    ),
    theoretical_max_throughput=TASK_CRISIS.theoretical_max_throughput,
    acceptable_avg_delay=TASK_CRISIS.acceptable_avg_delay,
)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TASK_REGISTRY: Dict[str, TaskSpec] = {
    t.task_id: t for t in [
        TASK_SUBURBAN,
        TASK_URBAN,
        TASK_CRISIS,
        TASK_GRID_STEADY,
        TASK_GRID_RUSH,
        TASK_GRID_CRISIS,
    ]
}


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

class EpisodeGrader:
    """
    Computes a scalar score in [0, 1] for a completed episode.

    For grid tasks (env_config contains grid_mode: True), throughput is
    divided by 9 before normalisation so scores remain in [0, 1].
    """

    def __init__(self, task_spec: TaskSpec):
        self.spec = task_spec

    def grade(self, trajectory_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parameters
        ----------
        trajectory_info : dict
            Keys: total_cleared, total_arrived, steps_survived,
                  avg_delay, switch_count, peak_spillback_fraction,
                  fairness_score, gridlock_terminated

        Returns
        -------
        dict with 'score' (float in [0,1]) and sub-scores.
        """
        spec = self.spec
        ti   = trajectory_info

        total_cleared  = float(ti.get("total_cleared", 0))
        steps_survived = float(ti.get("steps_survived", spec.horizon))
        avg_delay      = float(ti.get("avg_delay", 999))
        switch_count   = float(ti.get("switch_count", 0))
        peak_spillback = float(ti.get("peak_spillback_fraction", 0))
        gridlock_term  = bool(ti.get("gridlock_terminated", False))

        # Detect grid mode — divide network throughput by 9 nodes
        grid_mode         = spec.env_config.get("grid_mode", False)
        n_nodes           = 9 if grid_mode else 1
        effective_cleared = total_cleared / n_nodes

        # --- Sub-scores ---

        # Throughput efficiency: cleared / (per-step-max × steps)
        theoretical_max = spec.theoretical_max_throughput * max(steps_survived, 1)
        throughput_eff  = min(effective_cleared / max(theoretical_max, 1), 1.0)
        throughput_eff  = max(throughput_eff, 0.0)

        # Delay score: 1 at zero delay, 0 when avg_delay reaches acceptable_avg_delay
        delay_score = max(
            0.0,
            1.0 - avg_delay / max(spec.acceptable_avg_delay, 1.0),
        )
        delay_score = min(delay_score, 1.0)

        # Fairness score supplied by caller in [0, 1] (1 = perfectly fair)
        fairness_score = max(0.0, min(float(ti.get("fairness_score", 0.0)), 1.0))

        # Stability: penalise excessive phase switching
        max_switches = steps_survived / max(
            spec.env_config.get("min_phase_duration", 5), 1
        )
        stability_score = max(0.0, 1.0 - switch_count / max(max_switches, 1))

        # Spillback resilience — for grid tasks the caller passes the mean
        # across 9 nodes (each in [0,1]), so the value is already normalised.
        # For single-node tasks, peak_spillback = spillback_lanes / 12 ∈ [0,1].
        spillback_resilience = max(0.0, 1.0 - min(peak_spillback, 1.0))

        # Survival bonus
        survival_bonus = steps_survived / max(spec.horizon, 1)
        if gridlock_term:
            survival_bonus *= 0.5

        # --- Weighted composite (task-specific) ---
        task_id = spec.task_id

        if task_id in ("task_suburban_steady", "task_grid_steady"):
            score = (
                0.40 * throughput_eff
                + 0.30 * delay_score
                + 0.20 * fairness_score
                + 0.10 * stability_score
            )
        elif task_id in ("task_urban_stochastic", "task_grid_rush"):
            score = (
                0.35 * throughput_eff
                + 0.30 * delay_score
                + 0.20 * fairness_score
                + 0.15 * spillback_resilience
            )
        else:  # task_rush_hour_crisis | task_grid_crisis
            score = (
                0.30 * throughput_eff
                + 0.25 * delay_score
                + 0.20 * survival_bonus
                + 0.15 * fairness_score
                + 0.10 * stability_score
            )

        score = round(max(0.0, min(score, 1.0)), 6)

        return {
            "task_id": task_id,
            "score":   score,
            "sub_scores": {
                "throughput_efficiency": round(throughput_eff, 4),
                "delay_score":           round(delay_score, 4),
                "fairness_score":        round(fairness_score, 4),
                "stability_score":       round(stability_score, 4),
                "spillback_resilience":  round(spillback_resilience, 4),
                "survival_bonus":        round(survival_bonus, 4),
            },
            "trajectory_summary": {
                "total_cleared":       int(total_cleared),
                "total_arrived":       int(ti.get("total_arrived", 0)),
                "steps_survived":      int(steps_survived),
                "avg_delay_seconds":   round(avg_delay, 2),
                "switch_count":        int(switch_count),
                "gridlock_terminated": gridlock_term,
                "grid_mode":           grid_mode,
                "n_nodes":             n_nodes,
            },
        }


# ---------------------------------------------------------------------------
# Environment builder
# ---------------------------------------------------------------------------

def build_env(task_id: str, seed: Optional[int] = None) -> TrafficEnvironment:
    """
    Build a single TrafficEnvironment for the given task.

    .. warning::
        Grid tasks raise ValueError — use SessionStore.create_marl() instead.
    """
    if task_id not in TASK_REGISTRY:
        raise ValueError(
            f"Unknown task_id {task_id!r}. Available: {list(TASK_REGISTRY.keys())}"
        )

    spec   = TASK_REGISTRY[task_id]
    config = dict(spec.env_config)

    if config.get("grid_mode", False):
        raise ValueError(
            f"Task {task_id!r} is a grid task. Use SessionStore.create_marl() "
            "to build a MARLGridEnvironment; build_env() is single-node only."
        )

    if seed is not None:
        config["seed"] = seed

    return TrafficEnvironment(config)


# ---------------------------------------------------------------------------
# Task spec serialiser (for /tasks endpoint)
# ---------------------------------------------------------------------------

def get_task_spec_dict(task_id: str) -> Dict[str, Any]:
    spec      = TASK_REGISTRY[task_id]
    grid_mode = spec.env_config.get("grid_mode", False)
    return {
        "task_id":     spec.task_id,
        "name":        spec.name,
        "description": spec.description,
        "difficulty":  spec.difficulty,
        "horizon":     spec.horizon,
        "n_actions":   spec.n_actions,
        "obs_dim":     spec.obs_dim,
        "grid_mode":   grid_mode,
        "action_space": {
            "type":    "Discrete",
            "n":       spec.n_actions,
            "actions": {str(k): v for k, v in spec.action_descriptions.items()},
        },
        "observation_space": {
            "type": "Box",
            "dim":  spec.obs_dim,
            "description": (
                "73-dimensional float32 vector (MARL grid tasks): "
                "[base_obs(57), lstm_predictions(12), neighbor_pressures(4)]"
                if grid_mode else
                "57-dimensional float32 vector: "
                "[queue_lengths(12), throughput_recent(12), arrival_intensity(12), "
                "phase_onehot(4), phase_elapsed_norm(1), fairness_score(1), "
                "pressure_differential(1), avg_delay_norm(1), step_norm(1), "
                "spillback_flags(12)]"
            ),
            "bounds": "[0.0, 1.0] for most; pressure_differential in [-1, 1]",
        },
        "reward": {
            "type":  "dense",
            "range": "(-inf, +inf) per step, typically [-20, +15]",
            "description": spec.grader_description,
        },
        "grader_description":        spec.grader_description,
        "theoretical_max_throughput": spec.theoretical_max_throughput,
        "acceptable_avg_delay":       spec.acceptable_avg_delay,
        "env_config":                 spec.env_config,
    }