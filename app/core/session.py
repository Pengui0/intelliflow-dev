"""
Session management for stateful environment instances.
Each /reset call creates a new session with a UUID.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.core.environment import TrafficEnvironment, Observation
from app.tasks.registry import (
    TASK_REGISTRY, EpisodeGrader, build_env, get_task_spec_dict
)


class Session:
    def __init__(
        self,
        session_id: str,
        task_id: str,
        env: TrafficEnvironment,
        seed: Optional[int],
    ):
        self.session_id  = session_id
        self.task_id     = task_id
        self.env         = env
        self.seed        = seed
        self.created_at  = time.time()
        self.last_active = time.time()
        self.done        = False
        self.step_count  = 0

        # For grading
        self._peak_spillback = 0.0
        self._final_info: Dict[str, Any] = {}

    def step(self, action: int) -> Tuple[Observation, float, bool, Dict]:
        if self.done:
            raise RuntimeError("Episode is already done. Call /reset to start a new one.")
        obs, reward, done, info = self.env.step(action)
        self.done = done
        self.step_count += 1
        self.last_active = time.time()

        # track peak spillback
        spillback_frac = info.get("spillback_count", 0) / 12.0
        if spillback_frac > self._peak_spillback:
            self._peak_spillback = spillback_frac

        if done:
            self._final_info = info

        return obs, reward, done, info

    def grade(self) -> Dict[str, Any]:
        """Compute episode score. Can be called at any time (mid or end)."""
        analytics = self.env.analytics()
        summary   = analytics["episode_summary"]

        trajectory = {
            "total_cleared":            summary["total_cleared"],
            "total_arrived":            summary["total_arrived"],
            "steps_survived":           self.step_count,
            "avg_delay":                summary["avg_delay_s"],
            "switch_count":             summary["phase_switches"],
            "peak_spillback_fraction":  summary["peak_spillback_lanes"] / 12.0,
            "fairness_score":           1.0 - self.env._fairness_score(),
            "gridlock_terminated":      (self.env._is_gridlock() and self.done),
        }

        spec = TASK_REGISTRY[self.task_id]
        grader = EpisodeGrader(spec)
        result = grader.grade(trajectory)
        result["session_id"] = self.session_id
        result["done"]       = self.done
        result["analytics_snapshot"] = {
            "los":              summary["los"],
            "efficiency_ratio": summary["efficiency_ratio"],
            "emission_kg_co2":  summary["emission_kg_co2"],
            "green_split":      analytics["phase_analysis"]["green_split"],
            "switch_rate_per_100": analytics["phase_analysis"]["switch_rate_per_100"],
            "steps_at_los": analytics["los_breakdown"]["pct"],
        }
        return result


class SessionStore:
    """In-memory session store with TTL cleanup."""

    TTL_SECONDS = 3600  # sessions expire after 1 hour

    def __init__(self):
        self._sessions: Dict[str, Session] = {}

    def create(self, task_id: str, seed: Optional[int] = None) -> Session:
        if task_id not in TASK_REGISTRY:
            raise ValueError(f"Unknown task_id: {task_id!r}. "
                             f"Available: {list(TASK_REGISTRY.keys())}")
        session_id = str(uuid.uuid4())
        env = build_env(task_id, seed=seed)
        env.reset(seed=seed)
        session = Session(session_id, task_id, env, seed)
        self._sessions[session_id] = session
        self._cleanup()
        return session

    def get(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Session {session_id!r} not found. "
                           "It may have expired. Call /reset to create a new session.")
        session.last_active = time.time()
        return session

    def _cleanup(self):
        now = time.time()
        expired = [sid for sid, s in self._sessions.items()
                   if now - s.last_active > self.TTL_SECONDS]
        for sid in expired:
            del self._sessions[sid]

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [
            {
                "session_id": s.session_id,
                "task_id": s.task_id,
                "step_count": s.step_count,
                "done": s.done,
                "age_seconds": round(time.time() - s.created_at),
            }
            for s in self._sessions.values()
        ]


# Singleton store
store = SessionStore()