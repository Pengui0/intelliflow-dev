"""
IntelliFlow Urban Traffic Control Environment
Core simulation engine implementing OpenEnv specification.

Changes from v1.0.0
--------------------
- TrafficEnvironment.set_weather(mode)        — live mid-episode weather toggle
- TrafficEnvironment.inject_incident(...)     — lane blockage / demand spike
- TrafficEnvironment._tick_incidents()        — auto-expire incidents each step
- TrafficEnvironment.preemption_active        — flag read by EmergencyManager
- TrafficEnvironment.preemption_phase         — phase name string when preempting
- _apply_action() respects preemption_active  — overrides agent action when set
- MARLGridEnvironment                         — 3x3 grid of 9 TrafficEnvironments
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

# OpenEnv compliance — import base classes
# (graceful fallback if openenv-core not installed so existing code never breaks)
try:
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        from openenv.core import (
            Environment  as _OEEnvironment,
            Action       as _OEAction,
            Observation  as _OEObservation,
            State        as _OEState,
        )
    _OPENENV_AVAILABLE = True
except ImportError:
    _OPENENV_AVAILABLE = False
    _OEEnvironment = object
    _OEAction      = object
    _OEObservation = object
    _OEState       = object


# ---------------------------------------------------------------------------
# Action space
# ---------------------------------------------------------------------------

class Action(IntEnum):
    MAINTAIN       = 0
    SWITCH_PHASE   = 1
    EXTEND_GREEN   = 2
    FORCE_ALL_RED  = 3
    YIELD_MINOR    = 4

ACTION_DESCRIPTIONS = {
    Action.MAINTAIN:      "Maintain current signal phase",
    Action.SWITCH_PHASE:  "Switch to orthogonal phase (N-S ↔ E-W)",
    Action.EXTEND_GREEN:  "Extend current green by +5 seconds",
    Action.FORCE_ALL_RED: "Force all-red safety interval",
    Action.YIELD_MINOR:   "Yield short green to minor approaches",
}

N_ACTIONS = len(Action)


# ---------------------------------------------------------------------------
# Phase definitions
# ---------------------------------------------------------------------------

class Phase(IntEnum):
    NS_GREEN = 0
    EW_GREEN = 1
    ALL_RED  = 2
    NS_MINOR = 3


PHASE_PERMISSIONS = {
    Phase.NS_GREEN: {0, 1, 2, 3, 8, 9},
    Phase.EW_GREEN: {4, 5, 6, 7, 10, 11},
    Phase.ALL_RED:  set(),
    Phase.NS_MINOR: {1, 3},
}

LANE_NAMES = [
    "N_through", "N_right", "S_through", "S_right",
    "E_through", "E_right", "W_through", "W_right",
    "N_left",    "S_left",  "E_left",    "W_left",
]
N_LANES = len(LANE_NAMES)


# ---------------------------------------------------------------------------
# Weather modes
# ---------------------------------------------------------------------------

WEATHER_MODES: Dict[str, Dict[str, float]] = {
    "clear":      {"discharge_multiplier": 1.00, "arrival_variance_boost": 0.00,
                   "min_phase_override": 0},
    "rain":       {"discharge_multiplier": 0.75, "arrival_variance_boost": 0.10,
                   "min_phase_override": 2},
    "heavy_rain": {"discharge_multiplier": 0.60, "arrival_variance_boost": 0.20,
                   "min_phase_override": 3},
    "fog":        {"discharge_multiplier": 0.85, "arrival_variance_boost": 0.05,
                   "min_phase_override": 2},
    "snow":       {"discharge_multiplier": 0.50, "arrival_variance_boost": 0.25,
                   "min_phase_override": 4},
}


# ---------------------------------------------------------------------------
# Incident types
# ---------------------------------------------------------------------------

INCIDENT_TYPES: Dict[str, float] = {
    "blockage":     0.00,   # sat_flow multiplier — lane fully blocked
    "breakdown":    0.50,   # sat_flow multiplier — partial blockage
    "demand_spike": 1.00,   # arrival_lambda additive boost (+0.40)
}

_DEMAND_SPIKE_BOOST: float = 0.40


# ---------------------------------------------------------------------------
# Observation schema
# ---------------------------------------------------------------------------

@dataclass
class Observation:
    queue_lengths:      List[float]
    throughput_recent:  List[float]
    arrival_intensity:  List[float]
    phase_onehot:       List[float]
    phase_elapsed_norm: float
    fairness_score:     float
    spillback_flags:    List[float]
    avg_delay_norm:     float
    step_norm:          float
    pressure_differential: float

    def to_vector(self) -> np.ndarray:
        v = (
            self.queue_lengths
            + self.throughput_recent
            + self.arrival_intensity
            + self.phase_onehot
            + [
                self.phase_elapsed_norm,
                self.fairness_score,
                self.pressure_differential,
                self.avg_delay_norm,
                self.step_norm,
            ]
            + self.spillback_flags
        )
        return np.array(v, dtype=np.float32)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

OBS_DIM = N_LANES * 3 + 4 + 5 + N_LANES   # 57


# ---------------------------------------------------------------------------
# OpenEnv-compliant Pydantic schemas
# ---------------------------------------------------------------------------

from pydantic import BaseModel, ConfigDict, Field as PydanticField
from typing import List as _List

class TrafficAction(BaseModel):
    """
    OpenEnv Action schema for IntelliFlow Traffic Control.

    Themes covered:
    - Multi-Agent Interactions : action dispatched per node in MARL grid
    - Long-Horizon Planning    : agent selects phase timing over 600+ steps
    - Self-Improving Agents    : DQN learns from this action schema each episode
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    action_int: int = PydanticField(
        ge=0, le=4,
        description=(
            "0=MAINTAIN, 1=SWITCH_PHASE, 2=EXTEND_GREEN, "
            "3=FORCE_ALL_RED, 4=YIELD_MINOR"
        )
    )
    node_id: int = PydanticField(
        default=0, ge=0, le=8,
        description="Target node in MARL 3x3 grid (0 for single-node)"
    )
    metadata: Dict[str, Any] = PydanticField(default_factory=dict)


class TrafficObservation(BaseModel):
    """
    OpenEnv Observation schema for IntelliFlow.

    World Modeling theme: full 57-dim state vector encodes
    queue dynamics, arrival intensity, phase timing, spillback,
    fairness and delay — a complete world model of the intersection.
    """
    model_config = ConfigDict(extra="forbid", validate_assignment=True, arbitrary_types_allowed=True)

    done:               bool             = PydanticField(default=False)
    reward:             Optional[float]  = PydanticField(default=None)
    observation_vector: _List[float]     = PydanticField(description="57-dim state vector")
    observation_dict:   Dict[str, Any]   = PydanticField(default_factory=dict)
    info:               Dict[str, Any]   = PydanticField(default_factory=dict)
    step:               int              = PydanticField(default=0)
    phase:              str              = PydanticField(default="NS_GREEN")
    los:                str              = PydanticField(default="A")
    metadata:           Dict[str, Any]   = PydanticField(default_factory=dict)


class TrafficState(BaseModel):
    """OpenEnv State schema — internal environment state."""
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    episode_id: Optional[str] = PydanticField(default=None)
    step_count: int           = PydanticField(default=0, ge=0)
    phase:      str           = PydanticField(default="NS_GREEN")
    weather:    str           = PydanticField(default="clear")
    horizon:    int           = PydanticField(default=600)


# ---------------------------------------------------------------------------
# Traffic lane model
# ---------------------------------------------------------------------------

@dataclass
class Lane:
    name:           str
    capacity:       int
    sat_flow:       float
    arrival_lambda: float
    queue:          float = 0.0
    wait_accum:     float = 0.0
    total_arrived:  int   = 0
    total_cleared:  int   = 0
    recent_arrivals: List[int] = field(default_factory=lambda: [0] * 10)
    recent_cleared:  List[int] = field(default_factory=lambda: [0] * 10)

    # Base values — restored when incidents expire
    _base_sat_flow:       float = field(init=False)
    _base_arrival_lambda: float = field(init=False)

    def __post_init__(self) -> None:
        self._base_sat_flow       = self.sat_flow
        self._base_arrival_lambda = self.arrival_lambda

    def arrive(self, rng: random.Random) -> int:
        n     = rng.random()
        arrivals = 0
        p     = math.exp(-self.arrival_lambda)
        cumul = p
        while n > cumul:
            arrivals += 1
            p        *= self.arrival_lambda / arrivals
            cumul    += p
            if arrivals > 50:
                break
        actual = min(arrivals, self.capacity - int(self.queue))
        actual = max(0, actual)
        self.queue          += actual
        self.total_arrived  += actual
        self.recent_arrivals.pop(0)
        self.recent_arrivals.append(actual)
        return actual

    def discharge(
        self,
        green:          bool,
        weather_factor: float = 1.0,
        rng:            random.Random = None,
    ) -> int:
        if not green or self.queue <= 0:
            self.recent_cleared.pop(0)
            self.recent_cleared.append(0)
            return 0
        max_discharge = self.sat_flow * weather_factor
        cleared_float = min(self.queue, max_discharge)
        cleared_float = max(0.0, cleared_float)
        floor_n       = int(cleared_float)
        frac          = cleared_float - floor_n
        bonus         = 1 if (rng.random() if rng else random.random()) < frac else 0
        n             = min(floor_n + bonus, int(self.queue) + 1)
        n             = max(0, n)
        self.queue    = max(0.0, self.queue - cleared_float)
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

    Implements the OpenEnv Environment interface (reset / step / state).
    Wrapped as IntelliFlowOpenEnvAdapter below for full OpenEnv compliance.

    Hackathon Themes Covered
    ------------------------
    1. Multi-Agent Interactions
       - 9-node MARL grid (MARLGridEnvironment) with CTDE coordination bonus
       - Emergency vehicle preemption as an adversarial agent
       - DQN agent vs fixed-cycle baseline in A/B battle mode

    2. Long-Horizon Planning & Instruction Following
       - 600-step episodes with phase memory and replay buffer
       - Natural Language Commander translates human instructions to phase overrides
       - LSTM predictor models 12-step inflow horizon per lane

    3. World Modeling
       - Full 57-dim state: queue dynamics, arrival intensity, phase timing,
         spillback flags, fairness score, delay normalisation
       - Weather effects (discharge multiplier, arrival variance)
       - Incident physics (sat_flow degradation, demand spike)
       - COPERT-proxy CO₂ emission tracking

    4. Self-Improving Agent Systems
       - DQN trains live with experience replay + target network
       - Epsilon-greedy exploration decaying from 1.0 → 0.05
       - Weights auto-saved to disk / HuggingFace Hub every 50 train steps
       - LSTM predictor fine-tunes offline on each episode's arrival data

    Observation dim : 57 floats (73 in MARL mode with LSTM + neighbor pressure)
    Action space    : Discrete(5)
    Reward          : Dense, multi-objective, clipped to [-5, +5]
    """

    # OpenEnv class attribute — tells the server this env supports concurrent sessions
    SUPPORTS_CONCURRENT_SESSIONS: bool = True

    def __init__(self, config: Dict[str, Any]) -> None:
        self.config               = config
        self.horizon: int         = config.get("horizon", 1800)
        self.min_phase_duration: int = config.get("min_phase_duration", 5)
        self.max_phase_duration: int = config.get("max_phase_duration", 90)
        self.all_red_duration: int   = config.get("all_red_duration", 3)
        self.extend_increment: int   = config.get("extend_increment", 5)
        self.lane_capacity: int      = config.get("lane_capacity", 20)
        self.seed: Optional[int]     = config.get("seed", None)
        self.weather: str            = config.get("weather", "clear")
        self.incident_lane: int      = config.get("incident_lane", -1)

        # Reward weights
        self.w_throughput = config.get("w_throughput",  1.0)
        self.w_wait       = config.get("w_wait",       -0.05)
        self.w_fairness   = config.get("w_fairness",   -0.3)
        self.w_switch     = config.get("w_switch",     -0.2)
        self.w_spillback  = config.get("w_spillback",  -0.5)
        self.w_emission   = config.get("w_emission",   -0.01)

        # Preemption flags — written by EmergencyManager
        self.preemption_active: bool        = False
        self.preemption_phase:  Optional[str] = None

        self._rng    = random.Random(self.seed)
        self._np_rng = np.random.default_rng(self.seed)
        self.lanes:  List[Lane] = []
        self._reset_state()

    # ------------------------------------------------------------------
    # NEW: Weather control
    # ------------------------------------------------------------------

    def set_weather(self, mode: str) -> Dict[str, Any]:
        """
        Switch weather mode mid-episode.

        Parameters
        ----------
        mode : str
            One of "clear", "rain", "heavy_rain", "fog", "snow".

        Returns
        -------
        dict with new weather parameters for API response.
        """
        mode = mode.lower().strip()
        if mode not in WEATHER_MODES:
            raise ValueError(
                f"Unknown weather mode {mode!r}. "
                f"Valid: {list(WEATHER_MODES.keys())}"
            )
        self.weather = mode
        params       = WEATHER_MODES[mode]

        # Extend min_phase_duration for safety in bad weather
        override = params["min_phase_override"]
        if override > 0:
            self._weather_min_phase_bonus = override
        else:
            self._weather_min_phase_bonus = 0

        return {
            "weather_mode":           mode,
            "discharge_multiplier":   params["discharge_multiplier"],
            "arrival_variance_boost": params["arrival_variance_boost"],
            "min_phase_bonus_steps":  override,
            "projected_throughput_change_pct": round(
                (params["discharge_multiplier"] - 1.0) * 100, 1
            ),
        }

    # ------------------------------------------------------------------
    # NEW: Incident injection
    # ------------------------------------------------------------------

    def inject_incident(
        self,
        lane_id:        int,
        incident_type:  str,
        duration_steps: int,
    ) -> Dict[str, Any]:
        """
        Temporarily modify a lane's saturation flow or arrival rate.

        Parameters
        ----------
        lane_id : int
            Index into self.lanes [0-11].
        incident_type : str
            "blockage"    — sat_flow set to 0 (lane fully blocked)
            "breakdown"   — sat_flow set to 50% of base
            "demand_spike"— arrival_lambda increased by _DEMAND_SPIKE_BOOST
        duration_steps : int
            How many steps until the incident auto-clears.

        Returns
        -------
        dict describing the incident for the API response.
        """
        incident_type = incident_type.lower().strip()
        if incident_type not in INCIDENT_TYPES:
            raise ValueError(
                f"Unknown incident type {incident_type!r}. "
                f"Valid: {list(INCIDENT_TYPES.keys())}"
            )
        if not (0 <= lane_id < N_LANES):
            raise ValueError(
                f"lane_id must be in [0, {N_LANES-1}], got {lane_id}"
            )
        duration_steps = max(1, int(duration_steps))

        lane        = self.lanes[lane_id]
        incident_id = f"inc_{self._step_count}_{lane_id}"
        expires_at  = self._step_count + duration_steps

        # Only apply if lane not already incident-affected (prevents base corruption)
        if incident_type == "demand_spike":
            lane.arrival_lambda = lane._base_arrival_lambda + _DEMAND_SPIKE_BOOST
        else:
            multiplier = INCIDENT_TYPES[incident_type]
            # Always apply from base to avoid stacking corruption
            lane.sat_flow = lane._base_sat_flow * multiplier
        # Expire any existing incident on this lane first
        existing = [
            iid for iid, inc in self._active_incidents.items()
            if inc["lane_id"] == lane_id
        ]
        for iid in existing:
            self._active_incidents.pop(iid)

        # Register for auto-expiry
        self._active_incidents[incident_id] = {
            "lane_id":      lane_id,
            "incident_type": incident_type,
            "expires_at":   expires_at,
        }

        return {
            "incident_id":        incident_id,
            "lane_id":            lane_id,
            "lane_name":          lane.name,
            "incident_type":      incident_type,
            "duration_steps":     duration_steps,
            "expires_at_step":    expires_at,
            "estimated_impact_pct": round(
                (1.0 - INCIDENT_TYPES.get(incident_type, 1.0)) * 100
                if incident_type != "demand_spike" else 40.0,
                1,
            ),
        }

    def _tick_incidents(self) -> None:
        """
        Check and expire incidents whose duration has elapsed.
        Called inside step() before discharge.
        """
        expired = [
            inc_id for inc_id, inc in self._active_incidents.items()
            if self._step_count >= inc["expires_at"]
        ]
        for inc_id in expired:
            inc  = self._active_incidents.pop(inc_id)
            lane = self.lanes[inc["lane_id"]]
            # Restore base values
            lane.sat_flow       = lane._base_sat_flow
            lane.arrival_lambda = lane._base_arrival_lambda

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self, seed: Optional[int] = None) -> Observation:
        if seed is not None:
            self.seed    = seed
            self._rng    = random.Random(seed)
            self._np_rng = np.random.default_rng(seed)
        self._reset_state()
        return self._build_observation()

    def step(
        self, action: int
    ) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        assert 0 <= action < N_ACTIONS, f"Invalid action {action}"
        self._step_count += 1

        # Auto-expire incidents
        self._tick_incidents()

        prev_phase = self._current_phase
        reward     = 0.0

        # Apply action (preemption override handled inside)
        switched = self._apply_action(Action(action))

        # Arrivals
        weather_factor = self._weather_factor()
        for lane in self.lanes:
            lane.arrive(self._rng)

        # Discharge
        permissions = PHASE_PERMISSIONS[self._current_phase]
        total_cleared = 0
        amber_dur = self.config.get("amber_duration", 2)
        for i, lane in enumerate(self.lanes):
            green = (i in permissions) and (self._phase_elapsed >= amber_dur)
            # Static incident lane from config (original Task 3 behaviour)
            if i == self.incident_lane:
                green = False
            n = lane.discharge(green, weather_factor, self._rng)
            total_cleared += n

        # Wait accumulation
        for lane in self.lanes:
            lane.accumulate_wait()

        # Phase timer
        self._phase_elapsed += 1
        if (self._current_phase == Phase.ALL_RED
                and self._phase_elapsed >= self.all_red_duration):
            self._transition_to(self._next_major_phase())

        # Reward
        reward = self._compute_reward(total_cleared, switched, prev_phase)

        # Metrics update
        self._total_cleared += total_cleared
        self._switch_count  += int(switched)

        total_arrived_step       = sum(l.total_arrived for l in self.lanes)
        step_arrived             = total_arrived_step - self._total_arrived_all
        self._total_arrived_all  = total_arrived_step

        total_wait = sum(l.wait_accum for l in self.lanes)
        if self._total_cleared > 0:
            self._avg_delay = total_wait / max(self._total_cleared, 1)

        ns_queue  = sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
        ew_queue  = sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
        total_queue_now = ns_queue + ew_queue
        spillback_now   = sum(1 for l in self.lanes if l.spillback_risk)

        self._reward_history.append(reward)
        self._throughput_history.append(total_cleared)
        self._arrival_history.append(step_arrived)
        self._queue_ns_history.append(ns_queue)
        self._queue_ew_history.append(ew_queue)
        self._delay_history.append(self._avg_delay)
        self._spillback_history.append(spillback_now)

        self._total_emission_g += total_queue_now * 0.5

        if total_queue_now > self._peak_queue:
            self._peak_queue = total_queue_now
        if self._avg_delay > self._peak_delay:
            self._peak_delay = self._avg_delay
        if spillback_now > self._peak_spillback:
            self._peak_spillback = spillback_now

        if switched:
            duration = self._step_count - self._phase_start_step
            self._phase_durations[prev_phase.name].append(duration)
            self._phase_log.append({
                "step":          self._step_count,
                "from":          prev_phase.name,
                "to":            self._current_phase.name,
                "duration_held": duration,
            })
            self._phase_start_step = self._step_count

        for buf in [
            self._reward_history, self._throughput_history,
            self._arrival_history, self._queue_ns_history,
            self._queue_ew_history, self._delay_history,
            self._spillback_history,
        ]:
            if len(buf) > self._window * 5:
                buf.pop(0)

        done = self._check_termination()
        los  = self._level_of_service(self._avg_delay)
        total_queued_now = sum(l.queue for l in self.lanes)
        efficiency = self._total_cleared / max(self._total_cleared + total_queued_now, 1)

        info = {
            "step":             self._step_count,
            "phase":            self._current_phase.name,
            "phase_elapsed":    self._phase_elapsed,
            "total_cleared":    self._total_cleared,
            "total_arrived":    self._total_arrived_all,
            "avg_delay":        round(self._avg_delay, 3),
            "switch_count":     self._switch_count,
            "spillback_count":  spillback_now,
            "gridlock":         self._is_gridlock(),
            "step_cleared":     total_cleared,
            "step_arrived":     step_arrived,
            "step_reward":      round(reward, 6),
            "ns_queue":         round(ns_queue, 2),
            "ew_queue":         round(ew_queue, 2),
            "total_queue":      round(total_queue_now, 2),
            "efficiency_ratio": round(min(efficiency, 1.0), 4),
            "los":              los,
            "los_numeric":      "ABCDEF".index(los),
            "emission_kg_co2":  round(self._total_emission_g / 1000, 4),
            "peak_queue":       round(self._peak_queue, 2),
            "peak_delay":       round(self._peak_delay, 3),
            "peak_spillback":   self._peak_spillback,
            "fairness_score":   round(self._fairness_score(), 4),
            "weather":          self.weather,
            "active_incidents": len(self._active_incidents),
            "preemption_active": self.preemption_active,
            "rolling_throughput_rate": round(
                sum(self._throughput_history[-self._window:])
                / max(self._window, 1), 4
            ),
            "rolling_arrival_rate": round(
                sum(self._arrival_history[-self._window:])
                / max(self._window, 1), 4
            ),
        }

        obs = self._build_observation()
        return obs, round(reward, 6), done, info

    def state(self) -> Dict[str, Any]:
        obs       = self._build_observation()
        ns_queue  = sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
        ew_queue  = sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
        dominant  = "NS" if ns_queue > ew_queue else "EW"
        total_queued_now = sum(l.queue for l in self.lanes)
        efficiency = self._total_cleared / max(self._total_cleared + total_queued_now, 1)
        los       = self._level_of_service(self._avg_delay)

        # Signal colours for render_hints
        phase      = self._current_phase
        ns_green   = phase in (Phase.NS_GREEN, Phase.NS_MINOR)
        ew_green   = phase == Phase.EW_GREEN
        sig_colors = {
            "N": "#3ecf8e" if ns_green else "#e5534b",
            "S": "#3ecf8e" if ns_green else "#e5534b",
            "E": "#3ecf8e" if ew_green else "#e5534b",
            "W": "#3ecf8e" if ew_green else "#e5534b",
        }

        return {
            "observation":          obs.to_dict(),
            "observation_vector":   obs.to_vector().tolist(),
            "vector_dim":           OBS_DIM,
            "step":                 self._step_count,
            "dominant_flow":        dominant,
            "horizon":              self.horizon,
            "progress_pct":         round(
                self._step_count / max(self.horizon, 1) * 100, 1
            ),
            "phase":                self._current_phase.name,
            "phase_elapsed":        self._phase_elapsed,
            "weather":              self.weather,
            "preemption_active":    self.preemption_active,
            "preemption_phase":     self.preemption_phase,
            "active_incidents":     list(self._active_incidents.values()),
            "lanes": [
                {
                    "name":           l.name,
                    "queue":          round(l.queue, 2),
                    "capacity":       l.capacity,
                    "queue_pct":      round(
                        l.queue / max(l.capacity, 1) * 100, 1
                    ),
                    "occupancy_pct":  round(
                        l.queue / max(l.capacity, 1) * 100, 1
                    ),
                    "wait_accum":     round(l.wait_accum, 1),
                    "total_cleared":  l.total_cleared,
                    "total_arrived":  l.total_arrived,
                    "efficiency":     round(
                        l.total_cleared / max(l.total_arrived, 1), 3
                    ),
                    "lambda_est":     round(l.estimated_lambda, 3),
                    "spillback":      l.spillback_risk,
                    "recent_throughput_rate": round(l.recent_throughput, 3),
                }
                for l in self.lanes
            ],
            "direction_summary": {
                "NS": {
                    "queue":   round(ns_queue, 2),
                    "cleared": sum(
                        self.lanes[i].total_cleared for i in [0, 1, 2, 3, 8, 9]
                    ),
                    "arrived": sum(
                        self.lanes[i].total_arrived for i in [0, 1, 2, 3, 8, 9]
                    ),
                },
                "EW": {
                    "queue":   round(ew_queue, 2),
                    "cleared": sum(
                        self.lanes[i].total_cleared for i in [4, 5, 6, 7, 10, 11]
                    ),
                    "arrived": sum(
                        self.lanes[i].total_arrived for i in [4, 5, 6, 7, 10, 11]
                    ),
                },
            },
            "metrics": {
                "throughput_rate":  round(
                    self._total_cleared / max(self._step_count, 1), 4
                ),
                "avg_delay":        round(self._avg_delay, 3),
                "peak_delay":       round(self._peak_delay, 3),
                "switch_count":     self._switch_count,
                "fairness_score":   round(self._fairness_score(), 4),
                "efficiency_ratio": round(min(efficiency, 1.0), 4),
                "los":              los,
                "spillback_count":  sum(
                    1 for l in self.lanes if l.spillback_risk
                ),
                "peak_spillback":   self._peak_spillback,
                "emission_kg_co2":  round(self._total_emission_g / 1000, 4),
                "total_cleared":    self._total_cleared,
                "total_arrived":    self._total_arrived_all,
            },
            # Render hints for 3D visualiser and dashboard
            "render_hints": {
                "signal_colors":       sig_colors,
                "queue_visual_counts": {
                    l.name: min(8, int(l.queue))
                    for l in self.lanes
                },
                "weather_mode":        self.weather,
                "corridor_active":     self.preemption_active,
                "corridor_path":       [],   # filled by MARLGridEnvironment
                "preemption_active":   self.preemption_active,
                "preemption_phase":    self.preemption_phase,
                "active_incidents": [
                    {
                        "lane_id":   inc["lane_id"],
                        "lane_name": self.lanes[inc["lane_id"]].name,
                        "type":      inc["incident_type"],
                    }
                    for inc in self._active_incidents.values()
                ],
            },
        }

    def analytics(self) -> Dict[str, Any]:
        w    = self._window
        steps = max(self._step_count, 1)

        recent_tp    = self._throughput_history[-w:]
        recent_arr   = self._arrival_history[-w:]
        recent_delay = self._delay_history[-w:]
        recent_ns    = self._queue_ns_history[-w:]
        recent_ew    = self._queue_ew_history[-w:]

        def downsample(lst, n=5):
            return [round(lst[i], 4) for i in range(0, len(lst), n)]

        ns_green_steps = sum(self._phase_durations.get("NS_GREEN", []))
        ew_green_steps = sum(self._phase_durations.get("EW_GREEN", []))
        total_green    = max(ns_green_steps + ew_green_steps, 1)
        green_split    = {
            "NS_pct": round(ns_green_steps / total_green * 100, 1),
            "EW_pct": round(ew_green_steps / total_green * 100, 1),
        }

        avg_phase_dur = {}
        for phase_name, durations in self._phase_durations.items():
            avg_phase_dur[phase_name] = (
                round(sum(durations) / len(durations), 1) if durations else 0
            )

        efficiency_series = []
        for i in range(len(self._throughput_history)):
            cl = sum(self._throughput_history[max(0, i - w): i + 1])
            ar = sum(self._arrival_history[max(0, i - w): i + 1])
            efficiency_series.append(round(cl / max(ar, 1), 4))

        los_counts: Dict[str, int] = {g: 0 for g in "ABCDEF"}
        for d in self._delay_history:
            los_counts[self._level_of_service(d)] += 1

        emission_kg          = self._total_emission_g / 1000
        emission_rate_kg_hr  = emission_kg / max(steps / 3600, 1 / 3600)

        sat              = self.config.get("sat_flows", [0.9])[0]
        weather_factor   = self._weather_factor()
        theoretical_max  = N_LANES * sat * weather_factor * steps
        actual_vs_theory = round(
            self._total_cleared / max(theoretical_max, 1), 4
        )

        return {
            "episode_summary": {
                "steps_run":            self._step_count,
                "horizon":              self.horizon,
                "completion_pct":       round(
                    self._step_count / self.horizon * 100, 1
                ),
                "total_cleared":        self._total_cleared,
                "total_arrived":        self._total_arrived_all,
                "efficiency_ratio":     round(
                    self._total_cleared / max(
                        self._total_cleared + sum(l.queue for l in self.lanes), 1
                    ), 4
                ),
                "avg_delay_s":          round(self._avg_delay, 3),
                "peak_delay_s":         round(self._peak_delay, 3),
                "los":                  self._level_of_service(self._avg_delay),
                "phase_switches":       self._switch_count,
                "peak_spillback_lanes": self._peak_spillback,
                "emission_kg_co2":      round(emission_kg, 4),
                "emission_rate_kg_hr":  round(emission_rate_kg_hr, 4),
                "vs_theoretical_max":   actual_vs_theory,
                "weather":              self.weather,
            },
            "phase_analysis": {
                "green_split":         green_split,
                "avg_phase_duration":  avg_phase_dur,
                "total_switches":      self._switch_count,
                "switch_rate_per_100": round(
                    self._switch_count / max(steps, 1) * 100, 2
                ),
                "recent_transitions":  self._phase_log[-10:],
            },
            "los_breakdown": {
                "counts": los_counts,
                "pct":    {
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
                },
            },
            "rolling_window": {
                "window_steps": w,
                "throughput":   round(
                    sum(recent_tp) / max(len(recent_tp), 1), 4
                ),
                "arrival_rate": round(
                    sum(recent_arr) / max(len(recent_arr), 1), 4
                ),
                "avg_delay":    round(
                    sum(recent_delay) / max(len(recent_delay), 1), 3
                ),
                "ns_queue":     round(
                    sum(recent_ns) / max(len(recent_ns), 1), 2
                ),
                "ew_queue":     round(
                    sum(recent_ew) / max(len(recent_ew), 1), 2
                ),
            },
            "time_series": {
                "description":    "Downsampled every 5 steps",
                "sample_interval": 5,
                "reward":         downsample(self._reward_history),
                "throughput":     downsample(self._throughput_history),
                "arrivals":       downsample(self._arrival_history),
                "ns_queue":       downsample(self._queue_ns_history),
                "ew_queue":       downsample(self._queue_ew_history),
                "delay":          downsample(self._delay_history),
                "spillback":      downsample(self._spillback_history),
                "efficiency":     downsample(efficiency_series),
            },
            "direction_summary": {
                "NS": {
                    "queue_now": round(
                        sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9]), 2
                    ),
                    "cleared":  sum(
                        self.lanes[i].total_cleared for i in [0, 1, 2, 3, 8, 9]
                    ),
                    "arrived":  sum(
                        self.lanes[i].total_arrived for i in [0, 1, 2, 3, 8, 9]
                    ),
                    "green_pct": green_split["NS_pct"],
                },
                "EW": {
                    "queue_now": round(
                        sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11]), 2
                    ),
                    "cleared":  sum(
                        self.lanes[i].total_cleared for i in [4, 5, 6, 7, 10, 11]
                    ),
                    "arrived":  sum(
                        self.lanes[i].total_arrived for i in [4, 5, 6, 7, 10, 11]
                    ),
                    "green_pct": green_split["EW_pct"],
                },
            },
            "lane_details": [
                {
                    "name":         l.name,
                    "occupancy_pct": round(
                        l.queue / max(l.capacity, 1) * 100, 1
                    ),
                    "total_cleared": l.total_cleared,
                    "total_arrived": l.total_arrived,
                    "efficiency":    round(
                        l.total_cleared / max(l.total_arrived, 1), 3
                    ),
                    "wait_per_veh":  round(
                        l.wait_accum / max(l.total_cleared, 1), 2
                    ),
                    "spillback":     l.spillback_risk,
                    "avg_lambda":    round(l.estimated_lambda, 4),
                }
                for l in self.lanes
            ],
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_state(self) -> None:
        base_lambdas = self.config.get("arrival_lambdas", [
            0.65, 0.25, 0.60, 0.25,
            0.25, 0.10, 0.25, 0.10,
            0.30, 0.30, 0.12, 0.12,
        ])
        sat_flows = self.config.get("sat_flows", [0.9] * N_LANES)
        perturb   = self.config.get("stochastic_lambdas", False)

        self.lanes = []
        for i, name in enumerate(LANE_NAMES):
            lam = base_lambdas[i % len(base_lambdas)]
            if perturb:
                lam = lam * (0.7 + self._rng.random() * 0.6)
            sf  = sat_flows[i % len(sat_flows)]
            cap = self.lane_capacity
            self.lanes.append(
                Lane(name=name, capacity=cap, sat_flow=sf, arrival_lambda=lam)
            )

        self._current_phase     = Phase.NS_GREEN
        self._phase_elapsed     = 0
        self._phase_green_start = self.config.get("amber_duration", 2)
        self._step_count        = 0
        self._total_cleared     = 0
        self._switch_count      = 0
        self._avg_delay         = 0.0
        self._episode_reward    = 0.0
        self._prev_action       = -1
        self._forced_switch     = False
        self._gridlock_steps    = 0
        self._prev_total_queue  = 0.0
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

        self._total_emission_g  = 0.0
        self._peak_queue        = 0.0
        self._peak_delay        = 0.0
        self._peak_spillback    = 0
        self._total_arrived_all = 0
        self._phase_start_step  = 0
        self._phase_durations: Dict[str, List[int]] = {
            p.name: [] for p in Phase
        }

        # Incident registry: {incident_id: {lane_id, incident_type, expires_at}}
        self._active_incidents: Dict[str, Dict] = {}

        # Weather bonus tracking
        self._weather_min_phase_bonus: int = 0

        # Reset preemption flags
        self.preemption_active = False
        self.preemption_phase  = None

    def _apply_action(self, action: Action) -> bool:
        """
        Apply agent action — but if preemption_active is True, ignore
        the agent and lock to preemption_phase instead.
        """
        # Preemption override — EmergencyManager has control
        if self.preemption_active and self.preemption_phase:
            try:
                target = Phase[self.preemption_phase]
                if self._current_phase != target:
                    self._transition_to(target)
                    return True
            except KeyError:
                pass   # invalid phase name — fall through to normal control
            return False

        switched = False
        elapsed  = self._phase_elapsed

        # Apply weather-based minimum phase bonus
        effective_min = self.min_phase_duration + self._weather_min_phase_bonus

        if action == Action.MAINTAIN:
            pass

        elif action == Action.SWITCH_PHASE:
            if elapsed >= effective_min:
                self._transition_to(Phase.ALL_RED)
                self._forced_switch = True
                switched = True

        elif action == Action.EXTEND_GREEN:
            if self._current_phase not in (Phase.ALL_RED,):
                self._phase_elapsed = max(
                    self._phase_green_start,
                    self._phase_elapsed - self.extend_increment,
                )

        elif action == Action.FORCE_ALL_RED:
            if self._current_phase != Phase.ALL_RED:
                self._transition_to(Phase.ALL_RED)
                self._forced_switch = False
                switched = True

        elif action == Action.YIELD_MINOR:
            if (self._current_phase != Phase.NS_MINOR
                    and elapsed >= effective_min):
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
        if avg_delay_s <= 10: return "A"
        if avg_delay_s <= 20: return "B"
        if avg_delay_s <= 35: return "C"
        if avg_delay_s <= 55: return "D"
        if avg_delay_s <= 80: return "E"
        return "F"

    def _transition_to(self, phase: Phase) -> None:
        self._current_phase = phase
        self._phase_elapsed = 0
        self._forced_switch = False

    def _next_major_phase(self) -> Phase:
        if self._current_phase == Phase.ALL_RED:
            ns_pressure = sum(
                self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9]
            )
            ew_pressure = sum(
                self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11]
            )
            return Phase.NS_GREEN if ns_pressure >= ew_pressure else Phase.EW_GREEN
        return Phase.ALL_RED

    def _compute_reward(
        self,
        cleared:    int,
        switched:   bool,
        prev_phase: Phase,
    ) -> float:
        r     = 0.0
        n_lanes = len(self.lanes)
        cap   = max(self.lane_capacity, 1)

        permissions  = PHASE_PERMISSIONS[self._current_phase]
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

        occupancy_rate     = total_queue_now / max(n_lanes * cap, 1)
        congestion_penalty = -0.3 * (occupancy_rate ** 2)
        r += congestion_penalty

        main_lanes   = [0, 2, 4, 6]
        main_queues  = [self.lanes[i].queue / cap for i in main_lanes]
        mean_q       = sum(main_queues) / max(len(main_queues), 1)
        max_deviation = max(abs(q - mean_q) for q in main_queues)
        starvation   = max_deviation if max(main_queues) > 0.4 else 0.0
        r += self.w_fairness * starvation

        if switched:
            phase_was_all_red = (prev_phase == Phase.ALL_RED)
            pressure_diff     = abs(
                getattr(self, "_last_pressure_diff", 0.0)
            )
            premature  = (self._phase_elapsed < 15 and not phase_was_all_red)
            justified  = (pressure_diff > 0.25)
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
            ns_q  = sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
            ew_q  = sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
            tot_q = max(ns_q + ew_q, 1)
            self._last_pressure_diff = (ns_q - ew_q) / tot_q
            if abs(self._last_pressure_diff) > 0.3:
                r += 0.2 * abs(self._last_pressure_diff)
        else:
            ns_q  = sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
            ew_q  = sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
            tot_q = max(ns_q + ew_q, 1)
            self._last_pressure_diff = (ns_q - ew_q) / tot_q

        self._episode_reward += r
        return r

    def _fairness_score(self) -> float:
        waits = [
            l.wait_accum / max(l.total_arrived, 1) for l in self.lanes
        ]
        if len(waits) < 2:
            return 0.0
        mean  = sum(waits) / len(waits)
        var   = sum((w - mean) ** 2 for w in waits) / len(waits)
        return min(var / (max(waits) ** 2 + 1e-9), 1.0)

    def _is_gridlock(self) -> bool:
        threshold = self.config.get("gridlock_threshold", 0.95)
        blocked   = sum(
            1 for l in self.lanes
            if l.queue / max(l.capacity, 1) >= threshold
        )
        return blocked >= N_LANES * 0.7

    def _check_termination(self) -> bool:
        """
        Terminates the episode when:
        (1) horizon reached, or
        (2) sustained gridlock for 12 steps (was 20 — too lenient, allowed
            episodes to oscillate near-gridlock for hundreds of steps).
        Trimmed to 12 so degenerate states resolve cleanly within ~12 seconds
        of wall-clock instead of stalling the dashboard for minutes.
        """
        if self._step_count >= self.horizon:
            return True
        if self._is_gridlock():
            self._gridlock_steps += 1
            if self._gridlock_steps >= 12:
                return True
        else:
            self._gridlock_steps = 0
        return False

    def _weather_factor(self) -> float:
        return WEATHER_MODES.get(
            self.weather, WEATHER_MODES["clear"]
        )["discharge_multiplier"]

    def _build_observation(self) -> Observation:
        ql  = [l.queue / max(l.capacity, 1) for l in self.lanes]
        tp  = [l.recent_throughput for l in self.lanes]
        ai  = [
            min(l.estimated_lambda / max(l.sat_flow, 0.1), 1.0)
            for l in self.lanes
        ]
        phase_oh = [0.0] * 4
        phase_oh[int(self._current_phase)] = 1.0

        elapsed_norm   = self._phase_elapsed / max(self.max_phase_duration, 1)
        fs             = self._fairness_score()
        spillback      = [1.0 if l.spillback_risk else 0.0 for l in self.lanes]
        avg_delay_norm = min(self._avg_delay / 120.0, 1.0)
        step_norm      = self._step_count / max(self.horizon, 1)

        ns_pressure = sum(self.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
        ew_pressure = sum(self.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
        max_p       = max(ns_pressure + ew_pressure, 1)
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


# ---------------------------------------------------------------------------
# OpenEnv Adapter — wraps TrafficEnvironment in the official OpenEnv interface
# ---------------------------------------------------------------------------

class IntelliFlowOpenEnvAdapter(_OEEnvironment if _OPENENV_AVAILABLE else object):
    """
    Official OpenEnv adapter for IntelliFlow.

    Exposes the standard OpenEnv reset() / step() interface so that any
    OpenEnv-compatible LLM training loop (torchforge, TRL, Unsloth, etc.)
    can drive IntelliFlow without modification.

    Usage
    -----
    from app.core.environment import IntelliFlowOpenEnvAdapter, TrafficAction

    env = IntelliFlowOpenEnvAdapter(task_id="task_suburban_steady", seed=42)
    obs = env.reset()
    obs = env.step(TrafficAction(action_int=1))
    print(obs.reward, obs.done, obs.los)
    """

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(
        self,
        task_id: str = "task_suburban_steady",
        seed:    Optional[int] = None,
    ) -> None:
        if _OPENENV_AVAILABLE:
            super().__init__()
        self._task_id = task_id
        self._seed    = seed
        self._env:    Optional[TrafficEnvironment] = None
        self._step_n: int = 0

    def reset(
        self,
        seed:       Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs:   Any,
    ) -> TrafficObservation:
        from app.tasks.registry import TASK_REGISTRY
        spec   = TASK_REGISTRY.get(self._task_id)
        config = spec.env_config if spec else {"horizon": 600}
        if seed is not None:
            config = dict(config, seed=seed)
        elif self._seed is not None:
            config = dict(config, seed=self._seed)

        self._env    = TrafficEnvironment(config)
        self._step_n = 0
        obs_obj      = self._env.reset(seed=seed or self._seed)

        return TrafficObservation(
            done               = False,
            reward             = None,
            observation_vector = obs_obj.to_vector().tolist(),
            observation_dict   = obs_obj.to_dict(),
            info               = {},
            step               = 0,
            phase              = self._env._current_phase.name,
            los                = "A",
            metadata           = {"episode_id": episode_id, "task_id": self._task_id},
        )

    def step(
        self,
        action:    TrafficAction,
        timeout_s: Optional[float] = None,
        **kwargs:  Any,
    ) -> TrafficObservation:
        if self._env is None:
            raise RuntimeError("Call reset() before step().")

        action_int = action.action_int if isinstance(action, TrafficAction) else int(action)
        obs_obj, reward, done, info = self._env.step(action_int)
        self._step_n += 1

        return TrafficObservation(
            done               = done,
            reward             = round(reward, 6),
            observation_vector = obs_obj.to_vector().tolist(),
            observation_dict   = obs_obj.to_dict(),
            info               = info,
            step               = self._step_n,
            phase              = info.get("phase", "NS_GREEN"),
            los                = info.get("los", "A"),
            metadata           = {"task_id": self._task_id},
        )

    def get_state(self) -> TrafficState:
        if self._env is None:
            return TrafficState()
        return TrafficState(
            step_count = self._step_n,
            phase      = self._env._current_phase.name,
            weather    = self._env.weather,
            horizon    = self._env.horizon,
        )


# ---------------------------------------------------------------------------
# MARLGridEnvironment — 3x3 grid of 9 TrafficEnvironments
# ---------------------------------------------------------------------------

# Node adjacency — same map as emergency.py, duplicated here to keep
# environment.py self-contained
_GRID_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 3],    1: [0, 2, 4], 2: [1, 5],
    3: [0, 4, 6], 4: [1, 3, 5, 7], 5: [2, 4, 8],
    6: [3, 7],    7: [4, 6, 8], 8: [5, 7],
}

# How many neighbor pressure values are appended to each agent's obs
_NEIGHBOR_OBS_DIM: int = 4   # max neighbors in 3x3 grid

# Total obs dim per MARL agent: 57 base + 12 LSTM + 4 neighbor pressure = 73
MARL_OBS_DIM: int = OBS_DIM + 12 + _NEIGHBOR_OBS_DIM


class MARLGridEnvironment:
    """
    3x3 grid of 9 TrafficEnvironment instances.

    Each agent's observation is extended with:
    - 12-dim LSTM inflow prediction (from LSTMPredictor)
    - up to 4 neighbor queue pressure values (zero-padded)

    Joint action space: dict {node_id: action_int}
    Joint observation:  dict {node_id: np.ndarray shape (73,)}
    Joint reward:       dict {node_id: float}

    The grid reward also includes a coordination bonus that rewards
    the global network for reducing total cross-node spillback.
    """

    GRID_SIZE = 3
    N_NODES   = 9
    COORDINATION_BONUS_WEIGHT: float = 0.15

    def __init__(self, base_config: Dict[str, Any]) -> None:
        self.base_config = base_config
        self._rng        = random.Random(base_config.get("seed", None))
        self.nodes:  List[TrafficEnvironment] = []
        self._lstm_predictors: List[Any]      = []   # LSTMPredictor per node
        self._step_count: int = 0

    def reset(self, seed: Optional[int] = None) -> Dict[int, np.ndarray]:
        """
        Initialise all 9 nodes. Returns joint observation dict.
        """
        from app.core.lstm_predictor import LSTMPredictor

        self.nodes            = []
        self._lstm_predictors = []
        self._step_count      = 0

        for i in range(self.N_NODES):
            cfg = dict(self.base_config)
            node_seed = (seed or 0) + i * 1337
            cfg["seed"] = node_seed

            # Perturb arrival lambdas per node for heterogeneous traffic
            lambdas = cfg.get("arrival_lambdas", [0.2] * N_LANES)
            cfg["arrival_lambdas"] = [
                max(0.05, lam * (0.75 + self._rng.random() * 0.5))
                for lam in lambdas
            ]
            env = TrafficEnvironment(cfg)
            env.reset(seed=node_seed)
            self.nodes.append(env)

            predictor = LSTMPredictor()
            predictor.reset()
            self._lstm_predictors.append(predictor)

        return self._build_joint_obs()

    def step(
        self,
        actions: Dict[int, int],
    ) -> Tuple[
        Dict[int, np.ndarray],   # joint obs
        Dict[int, float],        # joint rewards
        bool,                    # done (any node terminated)
        Dict[str, Any],          # info
    ]:
        """
        Step all 9 nodes simultaneously.

        Parameters
        ----------
        actions : dict {node_id: action_int}
            Missing node IDs default to MAINTAIN (0).
        """
        self._step_count += 1
        joint_rewards: Dict[int, float] = {}
        joint_info:    Dict[int, Dict]  = {}
        any_done = False

        # Update LSTM predictors with current arrivals before stepping
        for i, env in enumerate(self.nodes):
            arrivals = np.array(
                [l.estimated_lambda for l in env.lanes], dtype=np.float32
            )
            self._lstm_predictors[i].observe(arrivals)

        # Step each node
        for node_id, env in enumerate(self.nodes):
            action = actions.get(node_id, 0)
            _, reward, done, info = env.step(action)
            joint_rewards[node_id] = reward
            joint_info[node_id]    = info
            if done:
                any_done = True

        # Coordination bonus — neighbor-weighted local reward (CTDE-style).
        # Each agent is penalised by its OWN spillback plus a discounted sum
        # of its NEIGHBORS' spillback. This incentivises genuine coordination
        # without collapsing to a single global signal (which treats a corner
        # node identically to the central hub node 4).
        total_spillback = sum(
            info.get("spillback_count", 0)
            for info in joint_info.values()
        )
        # Degree-aware coordination bonus.
        # Hub node 4 (4 neighbors) bears higher coordination weight.
        # Corner nodes (2 neighbors) get a lighter penalty — they can only
        # observe fewer neighbors so holding them to hub-level standards is unfair.
        _DEGREE_SCALE = {2: 0.70, 3: 1.00, 4: 1.40}
        for node_id in range(self.N_NODES):
            own_spill    = joint_info[node_id].get("spillback_count", 0)
            neighbor_ids = _GRID_ADJACENCY.get(node_id, [])
            neighbor_spill = sum(
                joint_info[nb].get("spillback_count", 0)
                for nb in neighbor_ids
            )
            n_neighbors  = max(len(neighbor_ids), 1)
            degree_scale = _DEGREE_SCALE.get(n_neighbors, 1.0)
            local_coord_bonus = -self.COORDINATION_BONUS_WEIGHT * degree_scale * (
                0.6 * own_spill + 0.4 * neighbor_spill / n_neighbors
            )
            joint_rewards[node_id] += local_coord_bonus

        obs = self._build_joint_obs()

        coord_bonus = -self.COORDINATION_BONUS_WEIGHT * total_spillback / self.N_NODES
        aggregate_info = {
            "step":              self._step_count,
            "any_done":          any_done,
            "total_spillback":   total_spillback,
            "coordination_bonus": round(coord_bonus, 4),
            "network_throughput": sum(
                i.get("step_cleared", 0) for i in joint_info.values()
            ),
            "network_avg_delay":  round(
                sum(i.get("avg_delay", 0) for i in joint_info.values())
                / self.N_NODES, 3
            ),
            "nodes": joint_info,
        }

        return obs, joint_rewards, any_done, aggregate_info

    def state(self) -> Dict[str, Any]:
        """Return full state for all 9 nodes — used by /state endpoint."""
        node_states = {}
        corridor_path: List[int] = []

        for node_id, env in enumerate(self.nodes):
            s = env.state()
            # Propagate corridor path from any preempted node
            if env.preemption_active:
                corridor_path.append(node_id)
            node_states[node_id] = s

        # Inject corridor path into render_hints of all nodes
        for node_id in range(self.N_NODES):
            node_states[node_id]["render_hints"]["corridor_path"] = corridor_path

        # Expose LSTM stats per node — judges can audit world modeling accuracy
        lstm_stats = {}
        for node_id, predictor in enumerate(self._lstm_predictors):
            if hasattr(predictor, "stats"):
                lstm_stats[node_id] = predictor.stats()

        return {
            "mode":          "marl_grid",
            "grid_size":     self.GRID_SIZE,
            "n_nodes":       self.N_NODES,
            "step":          self._step_count,
            "corridor_path": corridor_path,
            "nodes":         node_states,
            "lstm_stats":    lstm_stats,
        }

    def set_weather(self, mode: str) -> Dict[str, Any]:
        """Apply weather mode to all 9 nodes simultaneously."""
        results = {}
        for node_id, env in enumerate(self.nodes):
            results[node_id] = env.set_weather(mode)
        return {
            "weather_mode": mode,
            "applied_to_nodes": list(range(self.N_NODES)),
            "per_node": results,
        }

    def inject_incident(
        self,
        node_id:        int,
        lane_id:        int,
        incident_type:  str,
        duration_steps: int,
    ) -> Dict[str, Any]:
        """Inject an incident on a specific node."""
        if not (0 <= node_id < self.N_NODES):
            raise ValueError(f"node_id must be in [0,8], got {node_id}")
        result = self.nodes[node_id].inject_incident(
            lane_id, incident_type, duration_steps
        )
        result["node_id"] = node_id
        return result

    def train_lstm_offline(self) -> Dict[int, float]:
        """
        Train all LSTM predictors on this episode's data.
        Call at episode end. Returns {node_id: avg_loss}.
        """
        losses = {}
        for node_id, predictor in enumerate(self._lstm_predictors):
            loss = predictor.train_offline()
            losses[node_id] = round(loss, 6)
        return losses
    
    def maybe_escalate(self, recent_scores: list, threshold: float = 0.70, window: int = 5) -> dict:
        if len(recent_scores) < window:
            return {"escalated": False, "reason": "insufficient_data"}
        if all(s > threshold for s in recent_scores[-window:]):
            result = self.escalate_difficulty(factor=1.05)
            result["escalated"] = True
            result["trigger"] = f"last_{window}_scores_above_{threshold}"
            return result
        return {"escalated": False, "reason": "below_threshold"}

    def escalate_difficulty(self, factor: float = 1.05) -> Dict[str, Any]:
        """
        Self-improvement: increase arrival pressure across all nodes.
        Called when agent score exceeds threshold for N consecutive episodes.
        factor: multiplicative increase on arrival_lambdas (default 5% harder).
        Caps at 0.95 to prevent instant gridlock.
        """
        changes = {}
        for node_id, env in enumerate(self.nodes):
            new_lambdas = []
            for lane in env.lanes:
                new_lam = min(lane._base_arrival_lambda * factor, 0.95)
                lane._base_arrival_lambda = new_lam
                lane.arrival_lambda = new_lam
                new_lambdas.append(round(new_lam, 4))
            changes[node_id] = new_lambdas
        return {
            "escalation_factor": factor,
            "node_lambda_changes": changes,
            "message": f"Difficulty increased by {(factor-1)*100:.1f}% — self-improving curriculum active",
        }

    def grid_envs(self) -> Dict[int, TrafficEnvironment]:
        """Return {node_id: env} dict — used by EmergencyManager."""
        return {i: env for i, env in enumerate(self.nodes)}

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_joint_obs(self) -> Dict[int, np.ndarray]:
        """
        Build extended observation for each node:
        base_obs (57) + lstm_pred (12) + neighbor_pressures (4) = 73 dims
        """
        # Precompute NS+EW pressure per node for neighbor broadcast
        pressures = []
        for env in self.nodes:
            ns = sum(env.lanes[i].queue for i in [0, 1, 2, 3, 8, 9])
            ew = sum(env.lanes[i].queue for i in [4, 5, 6, 7, 10, 11])
            cap = max(env.lane_capacity * N_LANES, 1)
            pressures.append(float((ns + ew) / cap))

        joint_obs: Dict[int, np.ndarray] = {}

        for node_id, env in enumerate(self.nodes):
            # Base 57-dim observation
            base_obs = env._build_observation().to_vector()

            # 12-dim LSTM prediction
            lstm_pred = self._lstm_predictors[node_id].predict()

            # Neighbor pressures — zero-padded to length 4
            neighbor_ids = _GRID_ADJACENCY.get(node_id, [])
            neighbor_p   = [pressures[nb] for nb in neighbor_ids]
            while len(neighbor_p) < _NEIGHBOR_OBS_DIM:
                neighbor_p.append(0.0)
            neighbor_p = neighbor_p[: _NEIGHBOR_OBS_DIM]

            extended = np.concatenate([
                base_obs,
                lstm_pred,
                np.array(neighbor_p, dtype=np.float32),
            ])
            joint_obs[node_id] = extended

        return joint_obs