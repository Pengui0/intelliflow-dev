"""
IntelliFlow Task Registry
Three progressively challenging benchmark tasks with programmatic graders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import math

from app.core.environment import (
    TrafficEnvironment, N_LANES, N_ACTIONS, OBS_DIM, Action, LANE_NAMES
)


# ---------------------------------------------------------------------------
# Task metadata schema
# ---------------------------------------------------------------------------

@dataclass
class TaskSpec:
    task_id: str
    name: str
    description: str
    difficulty: str          # easy | medium | hard
    horizon: int
    n_actions: int
    obs_dim: int
    action_descriptions: Dict[int, str]
    env_config: Dict[str, Any]
    grader_description: str
    theoretical_max_throughput: float   # vehicles/step upper bound
    acceptable_avg_delay: float         # seconds, threshold for full score


# ---------------------------------------------------------------------------
# Task 1: Suburban Steady Flow (EASY)
# ---------------------------------------------------------------------------

TASK_SUBURBAN = TaskSpec(
    task_id="task_suburban_steady",
    name="Suburban Steady Flow",
    description=(
        "A single four-way intersection in a quiet suburb with low, "
        "symmetric vehicle arrivals. Inflow is nearly deterministic and "
        "balanced across all approaches. The optimal policy is to maintain "
        "fair green time allocation. Good baseline for verifying basic "
        "signal timing logic."
    ),
    difficulty="easy",
    horizon=600,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions={i: d for i, d in enumerate([
        "Maintain current phase",
        "Switch to orthogonal phase",
        "Extend green by 5s",
        "Force all-red safety interval",
        "Yield to minor roads",
    ])},
    env_config={
        "horizon": 600,
        "arrival_lambdas": [0.20, 0.05, 0.20, 0.05,
                            0.20, 0.05, 0.20, 0.05,
                            0.05, 0.05, 0.05, 0.05],
        "sat_flows": [0.95] * N_LANES,
        "min_phase_duration": 5,
        "max_phase_duration": 60,
        "all_red_duration": 3,
        "lane_capacity": 30,
        "stochastic_lambdas": False,
        "weather": "clear",
        "gridlock_threshold": 0.95,
        "w_throughput": 1.2,   # normalised: max ~+1.2 per step
        "w_wait":       -0.8,  # queue-delta penalty (normalised to [-1,1])
        "w_fairness":   -0.4,  # max-deviation starvation
        "w_switch":     -0.25, # oscillation penalty
        "w_spillback":  -0.6,  # escalating spillback severity
        "w_emission":    0.0,  # merged into congestion_penalty (no longer separate)
    },
    grader_description=(
        "Score = 0.4*(throughput_efficiency) + 0.3*(delay_score) "
        "+ 0.2*(fairness_score) + 0.1*(stability_score). "
        "throughput_efficiency = min(actual_throughput / theoretical_max, 1.0). "
        "delay_score = max(0, 1 - avg_delay / acceptable_delay). "
        "fairness_score = 1 - normalised_wait_variance. "
        "stability_score = 1 - min(switch_rate / max_switch_rate, 1)."
    ),
    theoretical_max_throughput=0.85,  # vehicles per step (sum over all lanes)
    acceptable_avg_delay=25.0,
)


# ---------------------------------------------------------------------------
# Task 2: Urban Stochastic Rush (MEDIUM)
# ---------------------------------------------------------------------------

TASK_URBAN = TaskSpec(
    task_id="task_urban_stochastic",
    name="Urban Stochastic Rush",
    description=(
        "A busy urban intersection with bursty, asymmetric inflows. "
        "Morning rush creates heavy North-South flow while East-West traffic "
        "varies stochastically. Lambda values are perturbed each episode. "
        "The agent must adapt timing dynamically and predict flow intensities "
        "to prevent queue starvation on any approach."
    ),
    difficulty="medium",
    horizon=1200,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions={i: d for i, d in enumerate([
        "Maintain current phase",
        "Switch to orthogonal phase",
        "Extend green by 5s",
        "Force all-red safety interval",
        "Yield to minor roads",
    ])},
    env_config={
        "horizon": 1200,
        "arrival_lambdas": [0.45, 0.10, 0.45, 0.10,
                            0.25, 0.08, 0.25, 0.08,
                            0.12, 0.12, 0.08, 0.08],
        "sat_flows": [0.90] * N_LANES,
        "min_phase_duration": 5,
        "max_phase_duration": 90,
        "all_red_duration": 3,
        "lane_capacity": 40,
        "stochastic_lambdas": True,   # perturb each episode
        "weather": "clear",
        "gridlock_threshold": 0.92,
        "w_throughput": 1.0,
        "w_wait":       -0.9,  # higher wait penalty — stochastic surges punish delay
        "w_fairness":   -0.5,  # starvation matters more with asymmetric load
        "w_switch":     -0.25,
        "w_spillback":  -0.7,
        "w_emission":    0.0,
    },
    grader_description=(
        "Score = 0.35*(throughput_efficiency) + 0.30*(delay_score) "
        "+ 0.20*(fairness_score) + 0.15*(spillback_resilience). "
        "spillback_resilience = 1 - min(peak_spillback_fraction, 1.0). "
        "Higher weights on throughput efficiency vs task 1."
    ),
    theoretical_max_throughput=1.40,
    acceptable_avg_delay=40.0,
)


# ---------------------------------------------------------------------------
# Task 3: Rush Hour Crisis (HARD)
# ---------------------------------------------------------------------------

TASK_CRISIS = TaskSpec(
    task_id="task_rush_hour_crisis",
    name="Rush Hour Crisis",
    description=(
        "Maximum load scenario simulating peak rush hour with heavy skew, "
        "high arrival rates near saturation, rain reducing discharge by 25%, "
        "and a blocked lane simulating an incident. The agent must survive "
        "congestion cascades, prevent gridlock, and maintain minimum viable "
        "throughput under extreme pressure. Episode terminates early on "
        "sustained gridlock. Scores are calibrated against theoretical maximums "
        "under these adverse conditions."
    ),
    difficulty="hard",
    horizon=1800,
    n_actions=N_ACTIONS,
    obs_dim=OBS_DIM,
    action_descriptions={i: d for i, d in enumerate([
        "Maintain current phase",
        "Switch to orthogonal phase",
        "Extend green by 5s",
        "Force all-red safety interval",
        "Yield to minor roads",
    ])},
    env_config={
        "horizon": 1800,
        "arrival_lambdas": [0.70, 0.18, 0.70, 0.18,
                            0.55, 0.15, 0.55, 0.15,
                            0.20, 0.20, 0.15, 0.15],
        "sat_flows": [0.85] * N_LANES,   # degraded by congestion
        "min_phase_duration": 5,
        "max_phase_duration": 90,
        "all_red_duration": 3,
        "lane_capacity": 40,
        "stochastic_lambdas": True,
        "weather": "rain",               # 25% discharge reduction
        "incident_lane": 0,              # N_through blocked
        "gridlock_threshold": 0.90,
        "w_throughput": 1.0,
        "w_wait":       -1.0,  # maximum pressure: near-saturated arrivals make delay very costly
        "w_fairness":   -0.45,
        "w_switch":     -0.20, # slightly lower: sometimes rapid adaptation is necessary
        "w_spillback":  -0.85, # heaviest: spillback cascade = episode failure
        "w_emission":    0.0,
    },
    grader_description=(
        "Score = 0.30*(throughput_efficiency) + 0.25*(delay_score) "
        "+ 0.20*(survival_bonus) + 0.15*(fairness_score) + 0.10*(stability_score). "
        "survival_bonus = steps_survived / horizon (rewards not gridlocking). "
        "Calibrated against rain+incident baselines."
    ),
    theoretical_max_throughput=1.80,   # unadjusted; actual effective ~1.2
    acceptable_avg_delay=70.0,
)


TASK_REGISTRY: Dict[str, TaskSpec] = {
    t.task_id: t for t in [TASK_SUBURBAN, TASK_URBAN, TASK_CRISIS]
}


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

class EpisodeGrader:
    """
    Computes a scalar score in [0, 1] for a completed episode.
    """

    def __init__(self, task_spec: TaskSpec):
        self.spec = task_spec

    def grade(self, trajectory_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Args:
            trajectory_info: dict with keys:
                total_cleared, total_arrived, steps_survived,
                avg_delay, switch_count, peak_spillback_fraction,
                fairness_score, gridlock_terminated
        Returns:
            dict with 'score' (float in [0,1]) and sub-scores
        """
        spec = self.spec
        ti = trajectory_info

        total_cleared     = float(ti.get("total_cleared", 0))
        total_arrived     = float(ti.get("total_arrived", 1))
        steps_survived    = float(ti.get("steps_survived", spec.horizon))
        avg_delay         = float(ti.get("avg_delay", 999))
        switch_count      = float(ti.get("switch_count", 0))
        peak_spillback    = float(ti.get("peak_spillback_fraction", 0))
        fairness_raw      = float(ti.get("fairness_score", 1.0))
        gridlock_term     = bool(ti.get("gridlock_terminated", False))

        # --- Sub-scores ---

        # Throughput efficiency
        theoretical_max = spec.theoretical_max_throughput * steps_survived
        throughput_eff = min(total_cleared / max(theoretical_max, 1), 1.0)
        throughput_eff = max(throughput_eff, 0.0)

        # Delay score (lower delay = better)
        # Use acceptable_avg_delay as the 0.5-score point; 0 delay = 1.0 score
        delay_score = max(0.0, 1.0 - avg_delay / max(spec.acceptable_avg_delay * 3.0, 1))
        delay_score = min(delay_score, 1.0)

        # Fairness score (lower variance = better)
        # fairness_raw from grader input is already 1-fairness_metric (higher=better)
        fairness_score = max(0.0, min(float(ti.get("fairness_score", 0.0)), 1.0))

        # Stability: penalise excessive phase switching
        max_switches = steps_survived / max(spec.env_config.get("min_phase_duration", 5), 1)
        stability_score = max(0.0, 1.0 - switch_count / max(max_switches, 1))

        # Spillback resilience
        spillback_resilience = max(0.0, 1.0 - peak_spillback)

        # Survival bonus
        survival_bonus = steps_survived / max(spec.horizon, 1)
        if gridlock_term:
            survival_bonus *= 0.5   # penalise gridlock termination

        # --- Weighted composite ---
        task_id = spec.task_id

        if task_id == "task_suburban_steady":
            score = (
                0.40 * throughput_eff
                + 0.30 * delay_score
                + 0.20 * fairness_score
                + 0.10 * stability_score
            )
        elif task_id == "task_urban_stochastic":
            score = (
                0.35 * throughput_eff
                + 0.30 * delay_score
                + 0.20 * fairness_score
                + 0.15 * spillback_resilience
            )
        else:  # rush hour crisis
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
            "score": score,
            "sub_scores": {
                "throughput_efficiency": round(throughput_eff, 4),
                "delay_score": round(delay_score, 4),
                "fairness_score": round(fairness_score, 4),
                "stability_score": round(stability_score, 4),
                "spillback_resilience": round(spillback_resilience, 4),
                "survival_bonus": round(survival_bonus, 4),
            },
            "trajectory_summary": {
                "total_cleared": int(total_cleared),
                "total_arrived": int(total_arrived),
                "steps_survived": int(steps_survived),
                "avg_delay_seconds": round(avg_delay, 2),
                "switch_count": int(switch_count),
                "gridlock_terminated": gridlock_term,
            }
        }


def build_env(task_id: str, seed: Optional[int] = None) -> TrafficEnvironment:
    spec = TASK_REGISTRY[task_id]
    config = dict(spec.env_config)
    if seed is not None:
        config["seed"] = seed
    return TrafficEnvironment(config)


def get_task_spec_dict(task_id: str) -> Dict[str, Any]:
    spec = TASK_REGISTRY[task_id]
    return {
        "task_id": spec.task_id,
        "name": spec.name,
        "description": spec.description,
        "difficulty": spec.difficulty,
        "horizon": spec.horizon,
        "n_actions": spec.n_actions,
        "obs_dim": spec.obs_dim,
        "action_space": {
            "type": "Discrete",
            "n": spec.n_actions,
            "actions": spec.action_descriptions,
        },
        "observation_space": {
            "type": "Box",
            "dim": spec.obs_dim,
            "description": (
                "57-dimensional float32 vector: "
                "[queue_lengths(12), throughput_recent(12), arrival_intensity(12), "
                "phase_onehot(4), phase_elapsed_norm(1), fairness_score(1), "
                "pressure_differential(1), avg_delay_norm(1), step_norm(1), "
                "spillback_flags(12)]"
            ),
            "bounds": "[0.0, 1.0] for most; pressure_differential in [-1, 1]",
        },
        "reward": {
            "type": "dense",
            "range": "(-inf, +inf) per step, typically [-20, +15]",
            "description": spec.grader_description,
        },
        "grader_description": spec.grader_description,
        "env_config": spec.env_config,
    }