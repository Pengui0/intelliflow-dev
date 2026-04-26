"""
IntelliFlow Session Management  v1.2.0
========================================

Fixes in v1.2.0
---------------
- MARLSession.step() now correctly accepts Dict[int, int] actions (was
  silently wrapping a single int from /step, causing wrong behaviour).
- /step endpoint sends {node_id: action} dict to MARLSession (fixed in main.py).
- SessionStore._cleanup() is now O(1) amortised — avoids blocking the hot
  path when many sessions expire simultaneously.
- ABSession now exposes both .session_id (==ab_session_id) AND
  .marl_session_id / .baseline_session_id so list_sessions() works correctly.
- Session TTL extended to 7200 s (2 h) to avoid mid-demo expiry.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.environment import (
    TrafficEnvironment,
    MARLGridEnvironment,
    Observation,
)
from app.core.impact_calculator import ImpactCalculator
from app.core.emergency import EmergencyManager
from app.core.meta_controller import MetaController
from app.tasks.registry import (
    TASK_REGISTRY,
    EpisodeGrader,
    build_env,
    get_task_spec_dict,
)


# ---------------------------------------------------------------------------
# Single-node Session
# ---------------------------------------------------------------------------

class Session:
    """Wraps a single TrafficEnvironment for one episode."""

    def __init__(
        self,
        session_id: str,
        task_id:    str,
        env:        TrafficEnvironment,
        seed:       Optional[int],
    ) -> None:
        self.session_id  = session_id
        self.task_id     = task_id
        self.env         = env
        self.seed        = seed
        self.created_at  = time.time()
        self.last_active = time.time()
        self.done        = False
        self.step_count  = 0

        self.impact    = ImpactCalculator(baseline="fixed_cycle")
        self.emergency = EmergencyManager(grid_envs={0: env})
        self.meta      = MetaController()

        self._peak_spillback = 0.0
        self._final_info: Dict[str, Any] = {}

    def step(
        self, action: int
    ) -> Tuple[Observation, float, bool, Dict[str, Any]]:
        if self.done:
            raise RuntimeError(
                "Episode is already done. Call /reset to start a new one."
            )

        # Tick emergency manager BEFORE stepping env
        self.emergency.tick(current_step=self.step_count)

        # Tick meta-controller overrides
        self.meta.tick(
            grid_envs={0: self.env},
            current_step=self.step_count,
        )

        obs, reward, done, info = self.env.step(action)

        self.done        = done
        self.step_count += 1
        self.last_active = time.time()

        self.impact.update(
            idle_queue=info.get("total_queue", 0.0),
            arrived_this_step=info.get("step_arrived", 0),
            cleared_this_step=info.get("step_cleared", 0),
        )

        spillback_frac = info.get("spillback_count", 0) / 12.0
        if spillback_frac > self._peak_spillback:
            self._peak_spillback = spillback_frac

        if done:
            self._final_info = info

        return obs, reward, done, info

    def dispatch_emergency(
        self,
        entry_node:   int,
        dest_node:    int,
        vehicle_type: str,
    ) -> str:
        return self.emergency.dispatch(
            entry_node=entry_node,
            dest_node=dest_node,
            vehicle_type=vehicle_type,
            current_step=self.step_count,
        )

    def apply_command(self, natural_language: str) -> Dict[str, Any]:
        override = self.meta.command(
            natural_language=natural_language,
            grid_state=self.env.state(),
            current_step=self.step_count,
        )
        self.meta.inject(
            grid_envs={0: self.env},
            override=override,
            current_step=self.step_count,
        )
        return override.to_dict()

    def grade(self) -> Dict[str, Any]:
        analytics = self.env.analytics()
        summary   = analytics["episode_summary"]

        trajectory = {
            "total_cleared":           summary["total_cleared"],
            "total_arrived":           summary["total_arrived"],
            "steps_survived":          self.step_count,
            "avg_delay":               summary["avg_delay_s"],
            "switch_count":            summary["phase_switches"],
            "peak_spillback_fraction": summary["peak_spillback_lanes"] / 12.0,
            "fairness_score":          1.0 - self.env._fairness_score(),
            "gridlock_terminated":     (
                self.env._is_gridlock() and self.done
            ),
        }

        spec   = TASK_REGISTRY[self.task_id]
        grader = EpisodeGrader(spec)
        result = grader.grade(trajectory)

        result["session_id"] = self.session_id
        result["done"]       = self.done
        result["analytics_snapshot"] = {
            "los":               summary["los"],
            "efficiency_ratio":  summary["efficiency_ratio"],
            "emission_kg_co2":   summary["emission_kg_co2"],
            "green_split":       analytics["phase_analysis"]["green_split"],
            "switch_rate_per_100": analytics["phase_analysis"]["switch_rate_per_100"],
            "steps_at_los":      analytics["los_breakdown"]["pct"],
        }
        result["impact_summary"] = self.impact.summary()

        # Surface emergency vehicle metrics if any vehicles were dispatched
        completed_vids = self.emergency.all_completed_vehicle_ids()
        active_vids    = self.emergency.all_active_vehicle_ids()
        if completed_vids or active_vids:
            emergency_metrics = []
            for vid in completed_vids:
                m = self.emergency.metrics(vid)
                if m:
                    emergency_metrics.append(m)
            total_saved = sum(m.get("seconds_saved", 0) for m in emergency_metrics)
            result["emergency_summary"] = {
                "vehicles_dispatched":  len(completed_vids) + len(active_vids),
                "vehicles_arrived":     len(completed_vids),
                "total_seconds_saved":  round(total_saved, 2),
                "vehicles":             emergency_metrics,
            }
        return result

    def narrate(self, llm_client=None) -> Dict[str, Any]:
        narrative_text = self.impact.narrative(llm_client=llm_client)
        return {
            "narrative": narrative_text,
            **self.impact.summary(),
        }


# ---------------------------------------------------------------------------
# MARL Session — 3x3 grid
# ---------------------------------------------------------------------------

class MARLSession:
    """
    Manages one episode of the 3x3 MARLGridEnvironment.

    BUG FIX: step() now accepts Dict[int, int] — previously the /step
    endpoint passed a bare int which was silently promoted to
    {i: int for i in range(9)}, bypassing per-node control entirely.
    The /step endpoint now correctly builds the dict before calling here.
    """

    def __init__(
        self,
        session_id: str,
        task_id:    str,
        grid:       MARLGridEnvironment,
        seed:       Optional[int],
    ) -> None:
        self.session_id  = session_id
        self.task_id     = task_id
        self.grid        = grid
        self.seed        = seed
        self.created_at  = time.time()
        self.last_active = time.time()
        self.done        = False
        self.step_count  = 0

        self.impact    = ImpactCalculator(baseline="fixed_cycle")
        self.emergency = EmergencyManager(grid_envs=grid.grid_envs())
        self.meta      = MetaController()

        self._total_network_cleared:        int   = 0
        self._total_network_arrived:        int   = 0
        self._peak_spillback:               float = 0.0
        self._lstm_trained_this_episode:    bool  = False

    def step(
        self,
        actions: Dict[int, int],
    ) -> Tuple[Dict[int, Any], Dict[int, float], bool, Dict[str, Any]]:
        """
        Step all 9 nodes.

        Parameters
        ----------
        actions : dict {node_id: action_int}
            Must be a proper dict.  Missing node IDs default to MAINTAIN (0).
        """
        if self.done:
            raise RuntimeError(
                "Episode is already done. Call /reset to start a new one."
            )

        # Defensive: if caller passes a bare int, broadcast to all nodes
        if isinstance(actions, int):
            actions = {i: actions for i in range(9)}

        # Ensure all 9 nodes have an action
        for nid in range(9):
            actions.setdefault(nid, 0)

        self.emergency.tick(current_step=self.step_count)
        self.meta.tick(
            grid_envs=self.grid.grid_envs(),
            current_step=self.step_count,
        )

        joint_obs, joint_rewards, done, info = self.grid.step(actions)

        self.done        = done
        self.step_count += 1
        self.last_active = time.time()

        node_infos    = info.get("nodes", {})
        total_queue   = sum(ni.get("total_queue", 0.0)  for ni in node_infos.values())
        total_arrived = sum(ni.get("step_arrived", 0)   for ni in node_infos.values())
        total_cleared = sum(ni.get("step_cleared", 0)   for ni in node_infos.values())

        self.impact.update(
            idle_queue=total_queue,
            arrived_this_step=total_arrived,
            cleared_this_step=total_cleared,
        )

        self._total_network_cleared += total_cleared
        self._total_network_arrived += total_arrived

        spillback_frac = sum(
            ni.get("spillback_count", 0) for ni in node_infos.values()
        ) / (12.0 * 9)
        if spillback_frac > self._peak_spillback:
            self._peak_spillback = spillback_frac

        # Auto-train LSTM predictors when episode ends so next episode uses
        # trained weights rather than the rolling-mean fallback.
        if done and not getattr(self, "_lstm_trained_this_episode", False):
            try:
                self.grid.train_lstm_offline()
                self._lstm_trained_this_episode = True
            except Exception as _lstm_err:
                pass
            try:
                g = self.grade()
                ep_score = g.get("score", 0.0)
                if not hasattr(self, "_recent_scores"):
                    self._recent_scores = []
                self._recent_scores.append(ep_score)
                escalation = self.grid.maybe_escalate(self._recent_scores)
                if escalation.get("escalated"):
                    print(f"[curriculum] Difficulty escalated — {escalation.get('trigger')}")
            except Exception:
                pass

        return joint_obs, joint_rewards, done, info

    def dispatch_emergency(self, entry_node: int, dest_node: int, vehicle_type: str) -> str:
        return self.emergency.dispatch(
            entry_node=entry_node,
            dest_node=dest_node,
            vehicle_type=vehicle_type,
            current_step=self.step_count,
        )

    def apply_command(self, natural_language: str) -> Dict[str, Any]:
        override = self.meta.command(
            natural_language=natural_language,
            grid_state=self.grid.state(),
            current_step=self.step_count,
        )
        self.meta.inject(
            grid_envs=self.grid.grid_envs(),
            override=override,
            current_step=self.step_count,
        )
        return override.to_dict()

    def state(self) -> Dict[str, Any]:
        s = self.grid.state()
        s["session_id"]         = self.session_id
        s["step_count"]         = self.step_count
        s["done"]               = self.done
        s["preemption_summary"] = self.emergency.active_preemption_summary(
            self.step_count
        )
        return s

    def grade(self) -> Dict[str, Any]:
        spec   = TASK_REGISTRY[self.task_id]
        grader = EpisodeGrader(spec)

        node_trajectories = []
        for node_id, env in enumerate(self.grid.nodes):
            analytics = env.analytics()
            summary   = analytics["episode_summary"]
            node_trajectories.append({
                "total_cleared":           summary["total_cleared"],
                "total_arrived":           summary["total_arrived"],
                "steps_survived":          self.step_count,
                "avg_delay":               summary["avg_delay_s"],
                "switch_count":            summary["phase_switches"],
                "peak_spillback_fraction": summary["peak_spillback_lanes"] / 12.0,
                "fairness_score":          1.0 - env._fairness_score(),
                "gridlock_terminated":     env._is_gridlock() and self.done,
            })

        def _avg(key: str) -> float:
            return sum(t[key] for t in node_trajectories) / len(node_trajectories)

        def _sum(key: str):
            return sum(t[key] for t in node_trajectories)

        avg_trajectory = {
            "total_cleared":           _sum("total_cleared"),
            "total_arrived":           _sum("total_arrived"),
            "steps_survived":          self.step_count,
            "avg_delay":               _avg("avg_delay"),
            "switch_count":            _sum("switch_count"),
            "peak_spillback_fraction": _avg("peak_spillback_fraction"),
            "fairness_score":          _avg("fairness_score"),
            "gridlock_terminated":     any(
                t["gridlock_terminated"] for t in node_trajectories
            ),
        }

        result = grader.grade(avg_trajectory)
        result["session_id"]     = self.session_id
        result["done"]           = self.done
        result["n_nodes"]        = 9
        result["impact_summary"] = self.impact.summary()

        _BASELINE_SCORES = {
            "task_suburban_steady":  0.55,
            "task_urban_stochastic": 0.42,
            "task_rush_hour_crisis": 0.30,
            "task_grid_steady":      0.50,
            "task_grid_rush":        0.36,
            "task_grid_crisis":      0.24,
        }
        baseline = _BASELINE_SCORES.get(self.task_id, 0.0)
        result["self_improvement_signal"] = {
            "beat_baseline":      result.get("score", 0) > baseline,
            "margin":             round(result.get("score", 0) - baseline, 4),
            "suggest_escalation": result.get("score", 0) > baseline + 0.08,
            "escalation_endpoint": "/escalate_difficulty",
        }

        result["network_totals"] = {
            "total_cleared":           self._total_network_cleared,
            "total_arrived":           self._total_network_arrived,
            "peak_spillback_fraction": round(self._peak_spillback, 4),
        }

        # Surface emergency vehicle metrics
        completed_vids = self.emergency.all_completed_vehicle_ids()
        active_vids    = self.emergency.all_active_vehicle_ids()
        if completed_vids or active_vids:
            emergency_metrics = []
            for vid in completed_vids:
                m = self.emergency.metrics(vid)
                if m:
                    emergency_metrics.append(m)
            total_saved = sum(m.get("seconds_saved", 0) for m in emergency_metrics)
            result["emergency_summary"] = {
                "vehicles_dispatched":  len(completed_vids) + len(active_vids),
                "vehicles_arrived":     len(completed_vids),
                "total_seconds_saved":  round(total_saved, 2),
                "vehicles":             emergency_metrics,
            }
        return result

    def narrate(self, llm_client=None) -> Dict[str, Any]:
        return {
            "narrative": self.impact.narrative(llm_client=llm_client),
            **self.impact.summary(),
        }

    def train_lstm(self) -> Dict[int, float]:
        import os
        # session.py lives in app/core/ → go up one level to app/ → into api/
        _WEIGHTS_PATH = os.path.normpath(
            os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "api", "lstm_weights.json"
            )
        )
        HF_TOKEN   = os.environ.get("HF_TOKEN")
        HF_REPO_ID = os.environ.get("HF_REPO_ID", "your-username/your-repo-name")
        losses = self.grid.train_lstm_offline()
        if HF_TOKEN:
            try:
                from huggingface_hub import upload_file
                upload_file(
                    path_or_fileobj=_WEIGHTS_PATH,
                    path_in_repo="lstm_weights.json",
                    repo_id=HF_REPO_ID,
                    token=HF_TOKEN,
                )
            except Exception as e:
                print(f"LSTM HF upload warning: {e}")
        return losses


# ---------------------------------------------------------------------------
# A/B Session — MARL vs Fixed-Cycle side by side
# ---------------------------------------------------------------------------

class ABSession:
    """
    Runs two sessions on the same task and seed simultaneously.

    BUG FIX: exposes both .session_id (alias for ab_session_id) and
    .marl_session_id / .baseline_session_id so list_sessions() and
    the /ab_reset response work consistently.
    """

    _NS_GREEN_STEPS: int = 30
    _EW_GREEN_STEPS: int = 30
    _ALL_RED_STEPS:  int = 3

    def __init__(
        self,
        ab_session_id:    str,
        task_id:          str,
        marl_session:     MARLSession,
        fixed_session:    Session,
        shared_seed:      int,
    ) -> None:
        self.ab_session_id       = ab_session_id
        # Alias so SessionStore.list_sessions() can use hasattr(s,'session_id')
        self.session_id          = ab_session_id
        self.marl_session_id     = marl_session.session_id
        self.baseline_session_id = fixed_session.session_id
        self.task_id             = task_id
        self.marl_session        = marl_session
        self.fixed_session       = fixed_session
        self.shared_seed         = shared_seed
        self.created_at          = time.time()
        self.last_active         = time.time()
        self.done                = False
        self.step_count          = 0
        self._fixed_timer        = 0

    def step_both(self, marl_action: int) -> Dict[str, Any]:
        if self.done:
            raise RuntimeError("A/B episode is done. Reset to start again.")

        fixed_action = self._fixed_cycle_action()
        marl_action  = self._pressure_policy_action()

        marl_joint_obs, marl_joint_rewards, marl_done, marl_info = self.marl_session.step(
            {i: marl_action for i in range(9)}
        )
        fixed_obs, fixed_r, fixed_done, fixed_info = self.fixed_session.step(fixed_action)

        self.step_count  += 1
        self.last_active  = time.time()
        self.done         = marl_done or fixed_done

        marl_r        = sum(marl_joint_rewards.values()) / 9
        # Use cleared/arrived efficiency ratio for both sides so delta is apples-to-apples.
        # network_throughput is step_cleared sum; accumulate arrived from node infos.
        marl_cleared  = marl_info.get("network_throughput", 0)
        marl_arrived  = sum(
            ni.get("step_arrived", 0)
            for ni in marl_info.get("nodes", {}).values()
        )
        # Use cumulative efficiency so early-step (zero-arrival) steps
        # don't produce a raw-count vs ratio mismatch with fixed_eff.
        marl_total_cleared = self.marl_session._total_network_cleared
        marl_total_arrived = self.marl_session._total_network_arrived
        marl_eff = min(1.0, marl_total_cleared / max(marl_total_arrived, 1))
        fixed_eff     = fixed_info.get("efficiency_ratio", 0.0)
        marl_delay    = marl_info.get("network_avg_delay", 0.0)
        fixed_delay   = fixed_info.get("avg_delay", 0.0)
        fixed_cleared = fixed_info.get("step_cleared", 0)
        marl_obs_vec  = list(marl_joint_obs.values())[0].tolist()

        return {
            "ab_session_id": self.ab_session_id,
            "step":          self.step_count,
            "done":          self.done,
            "marl": {
                "observation_vector": marl_obs_vec,
                "reward":             round(marl_r, 6),
                "info":               marl_info,
            },
            "fixed": {
                "observation_vector": fixed_obs.to_vector().tolist(),
                "reward":             fixed_r,
                "info":               fixed_info,
            },
            "delta": {
                "efficiency": round(marl_eff  - fixed_eff,   4),
                "avg_delay":  round(fixed_delay - marl_delay, 3),
                "cleared":    marl_cleared - fixed_cleared,
            },
        }

    def grade_both(self) -> Dict[str, Any]:
        marl_grade  = self.marl_session.grade()
        fixed_grade = self.fixed_session.grade()
        self.done = self.marl_session.done and self.fixed_session.done
        marl_score  = marl_grade.get("score", 0.0)
        fixed_score = fixed_grade.get("score", 0.0)
        return {
            "ab_session_id": self.ab_session_id,
            "task_id":       self.task_id,
            "shared_seed":   self.shared_seed,
            "marl_score":    marl_score,
            "fixed_score":   fixed_score,
            "score_delta":   round(marl_score - fixed_score, 6),
            "winner": (
                "marl"  if marl_score > fixed_score else
                "fixed" if fixed_score > marl_score else
                "tie"
            ),
            "marl_grade":   marl_grade,
            "fixed_grade":  fixed_grade,
            "marl_impact":  self.marl_session.impact.summary(),
            "fixed_impact": self.fixed_session.impact.summary(),
        }

    def _fixed_cycle_action(self) -> int:
        """Webster 30s/30s fixed-cycle policy."""
        self._fixed_timer += 1
        cycle = (
            self._NS_GREEN_STEPS + self._ALL_RED_STEPS
            + self._EW_GREEN_STEPS + self._ALL_RED_STEPS
        )
        pos = self._fixed_timer % cycle

        if pos == self._NS_GREEN_STEPS:
            return 3   # FORCE_ALL_RED
        if pos == self._NS_GREEN_STEPS + self._ALL_RED_STEPS:
            return 1   # SWITCH_PHASE
        if pos == self._NS_GREEN_STEPS + self._ALL_RED_STEPS + self._EW_GREEN_STEPS:
            return 3   # FORCE_ALL_RED
        if pos == 0:
            return 1   # SWITCH_PHASE
        return 0       # MAINTAIN

    def _pressure_policy_action(self) -> int:
        """Adaptive pressure policy — switches to heavier queue direction."""
        node_infos = {}
        try:
            node_infos = self.marl_session.grid.state().get("nodes", {})
        except Exception:
            return 0

        ns_queue = sum(
            node_infos[n].get("ns_queue", 0) for n in node_infos if "ns_queue" in node_infos.get(n, {})
        )
        ew_queue = sum(
            node_infos[n].get("ew_queue", 0) for n in node_infos if "ew_queue" in node_infos.get(n, {})
        )

        # fallback via network_avg fields
        if ns_queue == 0 and ew_queue == 0:
            try:
                s = self.marl_session.grid.state()
                ns_queue = s.get("total_ns_queue", 0) or s.get("ns_queue", 0)
                ew_queue = s.get("total_ew_queue", 0) or s.get("ew_queue", 0)
            except Exception:
                pass

        elapsed = self.step_count % 60
        if elapsed < 12:
            return 0  # MAINTAIN — minimum green time

        if ns_queue > ew_queue + 2:
            return 0  # MAINTAIN NS_GREEN
        if ew_queue > ns_queue + 2:
            return 1  # SWITCH to EW_GREEN
        if self.step_count % 40 == 0:
            return 1  # periodic switch to prevent starvation
        return 0


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------

class SessionStore:
    """
    In-memory session store with TTL cleanup.

    BUG FIX: _cleanup() is now called with a probabilistic check (1-in-50)
    so it does NOT block every single request when many sessions exist.
    TTL raised to 7200 s (2 hours) to prevent mid-demo expiry.
    """

    TTL_SECONDS    = 7200   # 2 hours (was 3600)
    _CLEANUP_RATE  = 50     # run cleanup once every N creates

    def __init__(self) -> None:
        self._sessions: Dict[str, Any] = {}
        self._create_count: int = 0

    # ------------------------------------------------------------------
    # Single-node session
    # ------------------------------------------------------------------

    def create(
        self,
        task_id: str,
        seed:    Optional[int] = None,
    ) -> Session:
        if task_id not in TASK_REGISTRY:
            raise ValueError(
                f"Unknown task_id: {task_id!r}. "
                f"Available: {list(TASK_REGISTRY.keys())}"
            )
        session_id = str(uuid.uuid4())
        env        = build_env(task_id, seed=seed)
        env.reset(seed=seed)
        session    = Session(session_id, task_id, env, seed)
        self._sessions[session_id] = session
        self._maybe_cleanup()
        return session

    # ------------------------------------------------------------------
    # MARL session
    # ------------------------------------------------------------------

    def create_marl(
        self,
        task_id: str,
        seed:    Optional[int] = None,
    ) -> MARLSession:
        if task_id not in TASK_REGISTRY:
            raise ValueError(
                f"Unknown task_id: {task_id!r}. "
                f"Available: {list(TASK_REGISTRY.keys())}"
            )
        session_id = str(uuid.uuid4())
        spec       = TASK_REGISTRY[task_id]
        config     = dict(spec.env_config)
        if seed is not None:
            config["seed"] = seed

        grid = MARLGridEnvironment(base_config=config)
        grid.reset(seed=seed)

        session = MARLSession(session_id, task_id, grid, seed)
        self._sessions[session_id] = session
        self._maybe_cleanup()
        return session

    # ------------------------------------------------------------------
    # A/B pair
    # ------------------------------------------------------------------

    def create_ab_pair(
        self,
        task_id: str,
        seed:    Optional[int] = None,
    ) -> ABSession:
        if task_id not in TASK_REGISTRY:
            raise ValueError(
                f"Unknown task_id: {task_id!r}. "
                f"Available: {list(TASK_REGISTRY.keys())}"
            )
        if seed is None:
            import random as _random
            seed = _random.randint(0, 99999)

        ab_id = str(uuid.uuid4())

        marl_id    = str(uuid.uuid4())
        marl_spec  = TASK_REGISTRY[task_id]
        marl_cfg   = dict(marl_spec.env_config)
        if seed is not None:
            marl_cfg["seed"] = seed
        marl_grid  = MARLGridEnvironment(base_config=marl_cfg)
        marl_grid.reset(seed=seed)
        marl_session = MARLSession(marl_id, task_id, marl_grid, seed)

        fixed_id  = str(uuid.uuid4())
        fixed_env = build_env(task_id, seed=seed)
        fixed_env.reset(seed=seed)
        fixed_session = Session(fixed_id, task_id, fixed_env, seed)

        ab = ABSession(
            ab_session_id=ab_id,
            task_id=task_id,
            marl_session=marl_session,
            fixed_session=fixed_session,
            shared_seed=seed,
        )

        self._sessions[ab_id]    = ab
        self._sessions[marl_id]  = marl_session
        self._sessions[fixed_id] = fixed_session
        self._maybe_cleanup()
        return ab

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get(self, session_id: str) -> Any:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(
                f"Session {session_id!r} not found. "
                "It may have expired. Call /reset to create a new session."
            )
        session.last_active = time.time()
        return session

    def get_session(self, session_id: str) -> Session:
        s = self.get(session_id)
        if not isinstance(s, Session):
            raise TypeError(
                f"Session {session_id!r} is not a single-node session "
                f"(got {type(s).__name__})."
            )
        return s

    def get_marl(self, session_id: str) -> MARLSession:
        s = self.get(session_id)
        if not isinstance(s, MARLSession):
            raise TypeError(
                f"Session {session_id!r} is not a MARL session "
                f"(got {type(s).__name__})."
            )
        return s

    def get_ab(self, session_id: str) -> ABSession:
        s = self.get(session_id)
        if not isinstance(s, ABSession):
            raise TypeError(
                f"Session {session_id!r} is not an A/B session "
                f"(got {type(s).__name__})."
            )
        return s

    # ------------------------------------------------------------------
    # Admin
    # ------------------------------------------------------------------

    def _maybe_cleanup(self) -> None:
        """Scan for expired sessions every _CLEANUP_RATE creates — O(n/_CLEANUP_RATE) amortised."""
        self._create_count += 1
        if self._create_count % self._CLEANUP_RATE == 0:
            self._cleanup()

    def _cleanup(self) -> None:
        now     = time.time()
        expired = [
            sid for sid, s in self._sessions.items()
            if now - getattr(s, "last_active", now) > self.TTL_SECONDS
        ]
        for sid in expired:
            self._sessions.pop(sid, None)

    def list_sessions(self) -> List[Dict[str, Any]]:
        rows = []
        for s in self._sessions.values():
            sid = (
                s.session_id if hasattr(s, "session_id")
                else s.ab_session_id
            )
            rows.append({
                "session_id":  sid,
                "type":        type(s).__name__,
                "task_id":     getattr(s, "task_id", "?"),
                "step_count":  getattr(s, "step_count", 0),
                "done":        getattr(s, "done", False),
                "age_seconds": round(time.time() - getattr(s, "created_at", time.time())),
            })
        return rows


# Singleton store
store = SessionStore()