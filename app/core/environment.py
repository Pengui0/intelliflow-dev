"""
IntelliFlow Urban Traffic Control Environment
Core simulation engine implementing OpenEnv specification.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np


# ---------------------------------------------------------------------------
# Action space
# ---------------------------------------------------------------------------

class Action(IntEnum):
    MAINTAIN       = 0   # Keep current phase, no change
    SWITCH_PHASE   = 1   # Toggle to orthogonal phase group
    EXTEND_GREEN   = 2   # Add fixed time increment to current green
    FORCE_ALL_RED  = 3   # Safety all-red interval (clears junction)
    YIELD_MINOR    = 4   # Give short green to minor side-roads

ACTION_DESCRIPTIONS = {
    Action.MAINTAIN:     "Maintain current signal phase",
    Action.SWITCH_PHASE: "Switch to orthogonal phase (N-S ↔ E-W)",
    Action.EXTEND_GREEN: "Extend current green by +5 seconds",
    Action.FORCE_ALL_RED:"Force all-red safety interval",
    Action.YIELD_MINOR:  "Yield short green to minor approaches",
}

N_ACTIONS = len(Action)


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------

class Phase(IntEnum):
    NS_GREEN  = 0   # North-South green, East-West red
    EW_GREEN  = 1   # East-West green, North-South red
    ALL_RED   = 2   # All approaches red (safety / transition)
    NS_MINOR  = 3   # Minor-road yielding for North-South


PHASE_PERMISSIONS = {
    # phase -> set of lane indices that may discharge
    # lanes: 0=N_through, 1=N_right, 2=S_through, 3=S_right,
    #        4=E_through, 5=E_right, 6=W_through, 7=W_right,
    #        8=N_left, 9=S_left, 10=E_left, 11=W_left
    Phase.NS_GREEN:  {0, 1, 2, 3, 8, 9},
    Phase.EW_GREEN:  {4, 5, 6, 7, 10, 11},
    Phase.ALL_RED:   set(),
    Phase.NS_MINOR:  {1, 3},   # right-turns only on minor approach
}

LANE_NAMES = [
    "N_through", "N_right", "S_through", "S_right",
    "E_through", "E_right", "W_through", "W_right",
    "N_left",    "S_left",  "E_left",    "W_left",
]
N_LANES = len(LANE_NAMES)


# ---------------------------------------------------------------------------
# Observation schema
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    # Queue lengths per lane (vehicles), normalised [0,1] by capacity
    queue_lengths: List[float]          # shape (N_LANES,)
    # Recent throughput (vehicles cleared in last 10 steps), normalised
    throughput_recent: List[float]      # shape (N_LANES,)
    # Estimated arrival intensity per lane (λ estimate), normalised
    arrival_intensity: List[float]      # shape (N_LANES,)
    # Current active phase one-hot
    phase_onehot: List[float]           # shape (4,)
    # Elapsed seconds in current phase, normalised by max_phase_duration
    phase_elapsed_norm: float
    # Fairness metric: normalised variance of per-lane wait times
    fairness_score: float
    # Congestion spillback flags per lane (0/1)
    spillback_flags: List[float]        # shape (N_LANES,)
    # Rolling average delay (s/vehicle) normalised
    avg_delay_norm: float
    # Step count in episode normalised by horizon
    step_norm: float
    # Pressure differential NS vs EW (for heuristic agents)
    pressure_differential: float

    def to_vector(self) -> np.ndarray:
        v = (
            self.queue_lengths
            + self.throughput_recent
            + self.arrival_intensity
            + self.phase_onehot
            + [self.phase_elapsed_norm,
               self.fairness_score,
               self.pressure_differential,
               self.avg_delay_norm,
               self.step_norm]
            + self.spillback_flags
        )
        return np.array(v, dtype=np.float32)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

OBS_DIM = N_LANES * 3 + 4 + 5 + N_LANES  # = 12*3 + 4 + 5 + 12 = 57


# ---------------------------------------------------------------------------
# Traffic lane model
# ---------------------------------------------------------------------------

@dataclass
class Lane:
    name: str
    capacity: int          # max vehicles that can queue
    sat_flow: float        # saturation discharge flow (veh/step at green)
    arrival_lambda: float  # Poisson arrival rate (veh/step)
    queue: float = 0.0
    wait_accum: float = 0.0   # cumulative wait (vehicle-steps)
    total_arrived: int = 0
    total_cleared: int = 0
    recent_arrivals: List[int] = field(default_factory=lambda: [0]*10)
    recent_cleared:  List[int] = field(default_factory=lambda: [0]*10)

    def arrive(self, rng: random.Random) -> int:
        """Simulate arrivals this step (Poisson)."""
        n = rng.random()
        # Poisson via inversion (works well for small λ)
        arrivals = 0
        p = math.exp(-self.arrival_lambda)
        cumul = p
        while n > cumul:
            arrivals += 1
            p *= self.arrival_lambda / arrivals
            cumul += p
            if arrivals > 50:
                break
        actual = min(arrivals, self.capacity - int(self.queue))
        actual = max(0, actual)
        self.queue += actual
        self.total_arrived += actual
        self.recent_arrivals.pop(0)
        self.recent_arrivals.append(actual)
        return actual

    def discharge(self, green: bool, weather_factor: float = 1.0, rng: random.Random = None) -> int:

        """Discharge vehicles this step if green."""
        if not green or self.queue <= 0:
            self.recent_cleared.pop(0)
            self.recent_cleared.append(0)
            return 0
        max_discharge = self.sat_flow * weather_factor
        cleared_float = min(self.queue, max_discharge)
        cleared_float = max(0.0, cleared_float)
        floor_n = int(cleared_float)
        frac = cleared_float - floor_n
        bonus = 1 if (rng.random() if rng else random.random()) < frac else 0
        n = min(floor_n + bonus, int(self.queue) + 1)
        n = max(0, n)
        self.queue = max(0.0, self.queue - cleared_float)
        self.total_cleared += n
        self.recent_cleared.pop(0)
        self.recent_cleared.append(n)
        return n

    def accumulate_wait(self) -> None:
        self.wait_accum += self.queue

    @property
    def estimated_lambda(self) -> float:
        return sum(self.recent_arrivals) / max(len(self.recent_arrivals), 1)

    @property
    def recent_throughput(self) -> float:
        return sum(self.recent_cleared) / max(self.capacity, 1)

    @property
    def spillback_risk(self) -> bool:
        return self.queue / max(self.capacity, 1) >= 0.85


# ---------------------------------------------------------------------------
# Main environment
# ---------------------------------------------------------------------------

class TrafficEnvironment:
    """
    OpenEnv-compliant Urban Traffic Signal Control Environment.

    Observation dim : 57 floats
    Action space    : Discrete(5)
    Reward          : Dense, multi-objective
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.horizon: int           = config.get("horizon", 1800)
        self.min_phase_duration: int = config.get("min_phase_duration", 5)
        self.max_phase_duration: int = config.get("max_phase_duration", 90)
        self.all_red_duration: int  = config.get("all_red_duration", 3)
        self.extend_increment: int  = config.get("extend_increment", 5)
        self.lane_capacity: int     = config.get("lane_capacity", 20)
        self.seed: Optional[int]    = config.get("seed", None)
        self.weather: str           = config.get("weather", "clear")
        self.incident_lane: int     = config.get("incident_lane", -1)

        # reward weights
        self.w_throughput   = config.get("w_throughput",   1.0)
        self.w_wait         = config.get("w_wait",        -0.05)
        self.w_fairness     = config.get("w_fairness",    -0.3)
        self.w_switch       = config.get("w_switch",      -0.2)
        self.w_spillback    = config.get("w_spillback",   -0.5)
        self.w_emission     = config.get("w_emission",    -0.01)

        self._rng = random.Random(self.seed)
        self._np_rng = np.random.default_rng(self.seed)
        self.lanes: List[Lane] = []
        self._reset_state()

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self, seed: Optional[int] = None) -> Observation:
        if seed is not None:
            self.seed = seed
            self._rng = random.Random(seed)
            self._np_rng = np.random.default_rng(seed)
        self._reset_state()
        return self._build_observation()

    def step(self, action: int) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        assert 0 <= action < N_ACTIONS, f"Invalid action {action}"
        self._step_count += 1

        prev_phase = self._current_phase
        reward = 0.0
        info: Dict[str, Any] = {}

        # --- Apply action ---
        switched = self._apply_action(Action(action))

        # --- Arrivals ---
        weather_factor = self._weather_factor()
        for lane in self.lanes:
            lane.arrive(self._rng)

        # --- Discharge ---
        permissions = PHASE_PERMISSIONS[self._current_phase]
        total_cleared = 0
        amber_dur = self.config.get("amber_duration", 2)
        for i, lane in enumerate(self.lanes):
            green = (i in permissions) and (self._phase_elapsed >= amber_dur)
            if i == self.incident_lane:
                green = False
            n = lane.discharge(green, weather_factor, self._rng)
            total_cleared += n

        # --- Wait accumulation ---
        for lane in self.lanes:
            lane.accumulate_wait()

        # --- Phase timer ---
        self._phase_elapsed += 1
        if self._current_phase == Phase.ALL_RED and self._phase_elapsed >= self.all_red_duration:
            self._transition_to(self._next_major_phase())

        # --- Reward computation ---
        reward = self._compute_reward(total_cleared, switched, prev_phase)

        # --- Core metrics update ---
        self._total_cleared  += total_cleared
        self._switch_count   += int(switched)
        total_arrived_step    = sum(l.total_arrived for l in self.lanes)
        step_arrived          = total_arrived_step - self._total_arrived_all
        self._total_arrived_all = total_arrived_step

        total_wait = sum(l.wait_accum for l in self.lanes)
        if self._total_cleared > 0:
            self._avg_delay = total_wait / max(self._total_cleared, 1)

        # --- Rich analytics tracking ---
        ns_queue  = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
        ew_queue  = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
        total_queue_now  = ns_queue + ew_queue
        spillback_now    = sum(1 for l in self.lanes if l.spillback_risk)

        self._reward_history.append(reward)
        self._throughput_history.append(total_cleared)
        self._arrival_history.append(step_arrived)
        self._queue_ns_history.append(ns_queue)
        self._queue_ew_history.append(ew_queue)
        self._delay_history.append(self._avg_delay)
        self._spillback_history.append(spillback_now)

        # Emission proxy: 0.5 g CO2/s per idling vehicle (COPERT idle model)
        self._total_emission_g += total_queue_now * 0.5

        # Peak tracking
        if total_queue_now > self._peak_queue:
            self._peak_queue = total_queue_now
        if self._avg_delay > self._peak_delay:
            self._peak_delay = self._avg_delay
        if spillback_now > self._peak_spillback:
            self._peak_spillback = spillback_now

        # Phase transition log
        if switched:
            duration = self._step_count - self._phase_start_step
            self._phase_durations[prev_phase.name].append(duration)
            self._phase_log.append({
                "step": self._step_count,
                "from": prev_phase.name,
                "to": self._current_phase.name,
                "duration_held": duration,
            })
            self._phase_start_step = self._step_count

        # Trim history to rolling window
        for buf in [self._reward_history, self._throughput_history,
                    self._arrival_history, self._queue_ns_history,
                    self._queue_ew_history, self._delay_history,
                    self._spillback_history]:
            if len(buf) > self._window * 5:
                buf.pop(0)

        # --- Termination ---
        done = self._check_termination()

        # --- Level of Service (HCM 2010 standard, Table 18-3) ---
        los = self._level_of_service(self._avg_delay)

        # --- Efficiency ratio ---
        efficiency = (self._total_cleared / max(self._total_arrived_all, 1))

        info = {
            "step":            self._step_count,
            "phase":           self._current_phase.name,
            "phase_elapsed":   self._phase_elapsed,
            "total_cleared":   self._total_cleared,
            "total_arrived":   self._total_arrived_all,
            "avg_delay":       round(self._avg_delay, 3),
            "switch_count":    self._switch_count,
            "spillback_count": spillback_now,
            "gridlock":        self._is_gridlock(),
            "step_cleared":    total_cleared,
            "step_arrived":    step_arrived,
            "step_reward":     round(reward, 6),
            "ns_queue":        round(ns_queue, 2),
            "ew_queue":        round(ew_queue, 2),
            "total_queue":     round(total_queue_now, 2),
            "efficiency_ratio":round(efficiency, 4),
            "los":             los,
            "los_numeric":     "ABCDEF".index(los),
            "emission_kg_co2": round(self._total_emission_g / 1000, 4),
            "peak_queue":      round(self._peak_queue, 2),
            "peak_delay":      round(self._peak_delay, 3),
            "peak_spillback":  self._peak_spillback,
            "fairness_score":  round(self._fairness_score(), 4),
            "rolling_throughput_rate": round(
                sum(self._throughput_history[-self._window:]) / max(self._window, 1), 4),
            "rolling_arrival_rate":    round(
                sum(self._arrival_history[-self._window:]) / max(self._window, 1), 4),
        }

        obs = self._build_observation()
        return obs, round(reward, 6), done, info

    def state(self) -> Dict[str, Any]:
        obs = self._build_observation()
        ns_queue = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
        ew_queue = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
        dominant_direction = "NS" if ns_queue > ew_queue else "EW"
        efficiency = self._total_cleared / max(self._total_arrived_all, 1)
        los = self._level_of_service(self._avg_delay)
        return {
            "observation": obs.to_dict(),
            "observation_vector": obs.to_vector().tolist(),
            "vector_dim": OBS_DIM,
            "step": self._step_count,
            "dominant_flow": dominant_direction,
            "horizon": self.horizon,
            "progress_pct": round(self._step_count / max(self.horizon, 1) * 100, 1),
            "phase": self._current_phase.name,
            "phase_elapsed": self._phase_elapsed,
            "lanes": [
                {
                    "name": l.name,
                    "queue": round(l.queue, 2),
                    "capacity": l.capacity,
                    # FIX: queue_pct is the true queue occupancy (0-100%)
                    "queue_pct": round(l.queue / max(l.capacity, 1) * 100, 1),
                    # occupancy_pct: same as queue_pct — no artificial cap
                    "occupancy_pct": round(l.queue / max(l.capacity, 1) * 100, 1),
                    "wait_accum": round(l.wait_accum, 1),
                    "total_cleared": l.total_cleared,
                    "total_arrived": l.total_arrived,
                    "efficiency": round(l.total_cleared / max(l.total_arrived, 1), 3),
                    "lambda_est": round(l.estimated_lambda, 3),
                    "spillback": l.spillback_risk,
                    "recent_throughput_rate": round(l.recent_throughput, 3),
                }
                for l in self.lanes
            ],
            "direction_summary": {
                "NS": {
                    "queue": round(sum(self.lanes[i].queue for i in [0,1,2,3,8,9]), 2),
                    "cleared": sum(self.lanes[i].total_cleared for i in [0,1,2,3,8,9]),
                    "arrived": sum(self.lanes[i].total_arrived for i in [0,1,2,3,8,9]),
                },
                "EW": {
                    "queue": round(sum(self.lanes[i].queue for i in [4,5,6,7,10,11]), 2),
                    "cleared": sum(self.lanes[i].total_cleared for i in [4,5,6,7,10,11]),
                    "arrived": sum(self.lanes[i].total_arrived for i in [4,5,6,7,10,11]),
                },
            },
            "metrics": {
                "throughput_rate":     round(self._total_cleared / max(self._step_count, 1), 4),
                "avg_delay":           round(self._avg_delay, 3),
                "peak_delay":          round(self._peak_delay, 3),
                "switch_count":        self._switch_count,
                "fairness_score":      round(self._fairness_score(), 4),
                "efficiency_ratio":    round(efficiency, 4),
                "los":                 los,
                "spillback_count":     sum(1 for l in self.lanes if l.spillback_risk),
                "peak_spillback":      self._peak_spillback,
                "emission_kg_co2":     round(self._total_emission_g / 1000, 4),
                "total_cleared":       self._total_cleared,
                "total_arrived":       self._total_arrived_all,
            }
        }

    def analytics(self) -> Dict[str, Any]:
        """Rich episode analytics for dashboard, judges, and post-hoc analysis."""
        w = self._window
        steps = max(self._step_count, 1)

        recent_tp  = self._throughput_history[-w:]
        recent_arr = self._arrival_history[-w:]
        recent_delay = self._delay_history[-w:]
        recent_ns  = self._queue_ns_history[-w:]
        recent_ew  = self._queue_ew_history[-w:]

        def downsample(lst, n=5):
            return [round(lst[i], 4) for i in range(0, len(lst), n)]

        ns_green_steps = sum(self._phase_durations.get("NS_GREEN", []))
        ew_green_steps = sum(self._phase_durations.get("EW_GREEN", []))
        total_green = max(ns_green_steps + ew_green_steps, 1)
        green_split = {
            "NS_pct": round(ns_green_steps / total_green * 100, 1),
            "EW_pct": round(ew_green_steps / total_green * 100, 1),
        }

        avg_phase_dur = {}
        for phase_name, durations in self._phase_durations.items():
            if durations:
                avg_phase_dur[phase_name] = round(sum(durations) / len(durations), 1)
            else:
                avg_phase_dur[phase_name] = 0

        efficiency_series = []
        for i in range(len(self._throughput_history)):
            cl = sum(self._throughput_history[max(0,i-w):i+1])
            ar = sum(self._arrival_history[max(0,i-w):i+1])
            efficiency_series.append(round(cl / max(ar, 1), 4))

        los_counts: Dict[str, int] = {g: 0 for g in "ABCDEF"}
        for d in self._delay_history:
            los_counts[self._level_of_service(d)] += 1

        emission_kg = self._total_emission_g / 1000
        emission_rate_kg_hr = emission_kg / max(steps / 3600, 1/3600)

        sat = self.config.get("sat_flows", [0.9])[0]
        weather_factor = self._weather_factor()
        theoretical_max_per_step = N_LANES * sat * weather_factor
        theoretical_total = theoretical_max_per_step * steps
        actual_efficiency_vs_theory = round(
            self._total_cleared / max(theoretical_total, 1), 4
        )

        return {
            "episode_summary": {
                "steps_run":           self._step_count,
                "horizon":             self.horizon,
                "completion_pct":      round(self._step_count / self.horizon * 100, 1),
                "total_cleared":       self._total_cleared,
                "total_arrived":       self._total_arrived_all,
                "efficiency_ratio":    round(self._total_cleared / max(self._total_arrived_all, 1), 4),
                "avg_delay_s":         round(self._avg_delay, 3),
                "peak_delay_s":        round(self._peak_delay, 3),
                "los":                 self._level_of_service(self._avg_delay),
                "phase_switches":      self._switch_count,
                "peak_spillback_lanes":self._peak_spillback,
                "emission_kg_co2":     round(emission_kg, 4),
                "emission_rate_kg_hr": round(emission_rate_kg_hr, 4),
                "vs_theoretical_max":  actual_efficiency_vs_theory,
            },
            "phase_analysis": {
                "green_split":         green_split,
                "avg_phase_duration":  avg_phase_dur,
                "total_switches":      self._switch_count,
                "switch_rate_per_100": round(self._switch_count / max(steps, 1) * 100, 2),
                "recent_transitions":  self._phase_log[-10:],
            },
            "los_breakdown": {
                "counts": los_counts,
                "pct": {
                    g: round(c / max(steps, 1) * 100, 1)
                    for g, c in los_counts.items()
                },
                "description": {
                    "A": "≤10s delay — free flow",
                    "B": "≤20s delay — stable",
                    "C": "≤35s delay — acceptable",
                    "D": "≤55s delay — approaching unstable",
                    "E": "≤80s delay — unstable",
                    "F": ">80s delay — forced/breakdown",
                }
            },
            "rolling_window": {
                "window_steps": w,
                "throughput":  round(sum(recent_tp) / max(len(recent_tp), 1), 4),
                "arrival_rate":round(sum(recent_arr) / max(len(recent_arr), 1), 4),
                "avg_delay":   round(sum(recent_delay) / max(len(recent_delay), 1), 3),
                "ns_queue":    round(sum(recent_ns) / max(len(recent_ns), 1), 2),
                "ew_queue":    round(sum(recent_ew) / max(len(recent_ew), 1), 2),
            },
            "time_series": {
                "description": "Downsampled every 5 steps for bandwidth efficiency",
                "sample_interval": 5,
                "reward":          downsample(self._reward_history),
                "throughput":      downsample(self._throughput_history),
                "arrivals":        downsample(self._arrival_history),
                "ns_queue":        downsample(self._queue_ns_history),
                "ew_queue":        downsample(self._queue_ew_history),
                "delay":           downsample(self._delay_history),
                "spillback":       downsample(self._spillback_history),
                "efficiency":      downsample(efficiency_series),
            },
            "direction_summary": {
                "NS": {
                    "queue_now":  round(sum(self.lanes[i].queue for i in [0,1,2,3,8,9]), 2),
                    "cleared":    sum(self.lanes[i].total_cleared for i in [0,1,2,3,8,9]),
                    "arrived":    sum(self.lanes[i].total_arrived for i in [0,1,2,3,8,9]),
                    "green_pct":  green_split["NS_pct"],
                },
                "EW": {
                    "queue_now":  round(sum(self.lanes[i].queue for i in [4,5,6,7,10,11]), 2),
                    "cleared":    sum(self.lanes[i].total_cleared for i in [4,5,6,7,10,11]),
                    "arrived":    sum(self.lanes[i].total_arrived for i in [4,5,6,7,10,11]),
                    "green_pct":  green_split["EW_pct"],
                },
            },
            "lane_details": [
                {
                    "name":           l.name,
                    "occupancy_pct":  round(l.queue / max(l.capacity, 1) * 100, 1),
                    "total_cleared":  l.total_cleared,
                    "total_arrived":  l.total_arrived,
                    "efficiency":     round(l.total_cleared / max(l.total_arrived, 1), 3),
                    "wait_per_veh":   round(l.wait_accum / max(l.total_cleared, 1), 2),
                    "spillback":      l.spillback_risk,
                    "avg_lambda":     round(l.estimated_lambda, 4),
                }
                for l in self.lanes
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_state(self):
        base_lambdas = self.config.get("arrival_lambdas", [
            0.65, 0.25,
            0.60, 0.25,
            0.25, 0.10,
            0.25, 0.10,
            0.30, 0.30,
            0.12, 0.12
        ])
        sat_flows    = self.config.get("sat_flows", [0.9] * N_LANES)
        perturb      = self.config.get("stochastic_lambdas", False)

        self.lanes = []
        for i, name in enumerate(LANE_NAMES):
            lam = base_lambdas[i % len(base_lambdas)]
            if perturb:
                lam = lam * (0.7 + self._rng.random() * 0.6)
            sf = sat_flows[i % len(sat_flows)]
            cap = self.lane_capacity
            self.lanes.append(Lane(
                name=name, capacity=cap, sat_flow=sf, arrival_lambda=lam,
            ))

        self._current_phase      = Phase.NS_GREEN
        self._phase_elapsed      = 0
        self._phase_green_start  = self.config.get("amber_duration", 2)
        self._step_count         = 0
        self._total_cleared      = 0
        self._switch_count       = 0
        self._avg_delay          = 0.0
        self._episode_reward     = 0.0
        self._prev_action        = -1
        self._forced_switch      = False
        self._gridlock_steps     = 0
        self._prev_total_queue   = 0.0
        self._last_pressure_diff = 0.0

        self._window = 60
        self._reward_history:     List[float] = []
        self._throughput_history: List[int]   = []
        self._arrival_history:    List[int]   = []
        self._queue_ns_history:   List[float] = []
        self._queue_ew_history:   List[float] = []
        self._delay_history:      List[float] = []
        self._phase_log:          List[Dict]  = []
        self._spillback_history:  List[int]   = []

        self._total_emission_g   = 0.0
        self._peak_queue         = 0.0
        self._peak_delay         = 0.0
        self._peak_spillback     = 0
        self._total_arrived_all  = 0

        self._phase_start_step   = 0
        self._phase_durations: Dict[str, List[int]] = {
            p.name: [] for p in Phase
        }

    def _apply_action(self, action: Action) -> bool:
        switched = False
        elapsed = self._phase_elapsed

        if action == Action.MAINTAIN:
            pass

        elif action == Action.SWITCH_PHASE:
            if elapsed >= self.min_phase_duration:
                self._transition_to(Phase.ALL_RED)
                self._forced_switch = True
                switched = True

        elif action == Action.EXTEND_GREEN:
            if self._current_phase not in (Phase.ALL_RED,):
                self._phase_elapsed = max(
                    self._phase_green_start,
                    self._phase_elapsed - self.extend_increment
                )

        elif action == Action.FORCE_ALL_RED:
            if self._current_phase != Phase.ALL_RED:
                self._transition_to(Phase.ALL_RED)
                self._forced_switch = False
                switched = True

        elif action == Action.YIELD_MINOR:
            if self._current_phase != Phase.NS_MINOR and elapsed >= self.min_phase_duration:
                self._transition_to(Phase.NS_MINOR)
                switched = True

        if (self._current_phase not in (Phase.ALL_RED,)
                and self._phase_elapsed >= self.max_phase_duration):
            self._transition_to(Phase.ALL_RED)
            self._forced_switch = True
            switched = True

        self._prev_action = int(action)
        return switched

    def _level_of_service(self, avg_delay_s: float) -> str:
        if avg_delay_s <= 10:  return "A"
        if avg_delay_s <= 20:  return "B"
        if avg_delay_s <= 35:  return "C"
        if avg_delay_s <= 55:  return "D"
        if avg_delay_s <= 80:  return "E"
        return "F"

    def _transition_to(self, phase: Phase):
        self._current_phase = phase
        self._phase_elapsed = 0
        self._forced_switch = False

    def _next_major_phase(self) -> Phase:
        if self._current_phase == Phase.ALL_RED:
            ns_pressure = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
            ew_pressure = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
            return Phase.NS_GREEN if ns_pressure >= ew_pressure else Phase.EW_GREEN
        return Phase.ALL_RED

    def _compute_reward(self, cleared: int, switched: bool, prev_phase: Phase) -> float:
        r = 0.0
        n_lanes = len(self.lanes)
        cap = max(self.lane_capacity, 1)

        permissions = PHASE_PERMISSIONS[self._current_phase]
        max_possible = len(permissions) * max(
            self.config.get("sat_flows", [0.9])[0], 0.1
        )
        throughput_norm = cleared / max(max_possible, 1)
        r += self.w_throughput * throughput_norm

        total_queue_now  = sum(l.queue for l in self.lanes)
        prev_queue       = getattr(self, "_prev_total_queue", total_queue_now)
        queue_delta      = prev_queue - total_queue_now
        queue_delta_norm = queue_delta / max(n_lanes * cap, 1)
        queue_delta_norm = max(-1.0, min(1.0, queue_delta_norm))
        r += self.w_wait * queue_delta_norm
        self._prev_total_queue = total_queue_now

        occupancy_rate = total_queue_now / max(n_lanes * cap, 1)
        congestion_penalty = -0.3 * (occupancy_rate ** 2)
        r += congestion_penalty

        main_lanes = [0, 2, 4, 6]
        main_queues = [self.lanes[i].queue / cap for i in main_lanes]
        mean_q = sum(main_queues) / max(len(main_queues), 1)
        max_deviation = max(abs(q - mean_q) for q in main_queues)
        starvation = max_deviation if max(main_queues) > 0.4 else 0.0
        r += self.w_fairness * starvation

        if switched:
            phase_was_all_red = (prev_phase == Phase.ALL_RED)
            pressure_diff = abs(getattr(self, "_last_pressure_diff", 0.0))
            premature = (self._phase_elapsed < 15 and not phase_was_all_red)
            justified = (pressure_diff > 0.25)

            if premature and not justified:
                r += self.w_switch
            elif premature:
                r += self.w_switch * 0.3

        spillback_severity = 0.0
        for lane in self.lanes:
            occ = lane.queue / cap
            if occ >= 0.85:
                spillback_severity += (occ - 0.85) / 0.15
        spillback_severity /= max(n_lanes, 1)
        r += self.w_spillback * spillback_severity

        if self._is_gridlock():
            gridlock_frac = sum(
                1 for l in self.lanes
                if l.queue / cap >= self.config.get("gridlock_threshold", 0.95)
            ) / n_lanes
            r += -8.0 * gridlock_frac

        if switched and not (prev_phase == Phase.ALL_RED):
            ns_q = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
            ew_q = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
            total_q = max(ns_q + ew_q, 1)
            self._last_pressure_diff = (ns_q - ew_q) / total_q
            pressure_diff = abs(self._last_pressure_diff)
            if pressure_diff > 0.3:
                r += 0.2 * pressure_diff
        else:
            ns_q = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
            ew_q = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
            total_q = max(ns_q + ew_q, 1)
            self._last_pressure_diff = (ns_q - ew_q) / total_q

        self._episode_reward += r
        return r

    def _fairness_score(self) -> float:
        waits = [l.wait_accum / max(l.total_arrived, 1) for l in self.lanes]
        if len(waits) < 2:
            return 0.0
        mean = sum(waits) / len(waits)
        var = sum((w - mean) ** 2 for w in waits) / len(waits)
        return min(var / (max(waits) ** 2 + 1e-9), 1.0)

    def _is_gridlock(self) -> bool:
        gridlock_threshold = self.config.get("gridlock_threshold", 0.95)
        blocked = sum(1 for l in self.lanes
                      if l.queue / max(l.capacity, 1) >= gridlock_threshold)
        return blocked >= N_LANES * 0.7

    def _check_termination(self) -> bool:
        if self._step_count >= self.horizon:
            return True
        if self._is_gridlock():
            if not hasattr(self, "_gridlock_steps"):
                self._gridlock_steps = 0
            self._gridlock_steps += 1
            if self._gridlock_steps >= 20:
                return True
        else:
            self._gridlock_steps = 0
        return False

    def _weather_factor(self) -> float:
        factors = {"clear": 1.0, "rain": 0.75, "fog": 0.6, "snow": 0.5}
        return factors.get(self.weather, 1.0)

    def _build_observation(self) -> Observation:
        ql = [l.queue / max(l.capacity, 1) for l in self.lanes]
        tp = [l.recent_throughput for l in self.lanes]
        ai = [min(l.estimated_lambda / max(l.sat_flow, 0.1), 1.0) for l in self.lanes]

        phase_oh = [0.0] * 4
        phase_oh[int(self._current_phase)] = 1.0

        elapsed_norm = self._phase_elapsed / max(self.max_phase_duration, 1)
        fs = self._fairness_score()
        spillback = [1.0 if l.spillback_risk else 0.0 for l in self.lanes]
        avg_delay_norm = min(self._avg_delay / 120.0, 1.0)
        step_norm = self._step_count / max(self.horizon, 1)

        ns_pressure = sum(self.lanes[i].queue for i in [0,1,2,3,8,9])
        ew_pressure = sum(self.lanes[i].queue for i in [4,5,6,7,10,11])
        max_p = max(ns_pressure + ew_pressure, 1)
        pressure_diff = (ns_pressure - ew_pressure) / max_p

        return Observation(
            queue_lengths=ql,
            throughput_recent=tp,
            arrival_intensity=ai,
            phase_onehot=phase_oh,
            phase_elapsed_norm=elapsed_norm,
            fairness_score=fs,
            spillback_flags=spillback,
            avg_delay_norm=avg_delay_norm,
            step_norm=step_norm,
            pressure_differential=pressure_diff,
        )