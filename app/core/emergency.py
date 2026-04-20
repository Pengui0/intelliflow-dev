"""
IntelliFlow Emergency Vehicle Preemption
==========================================
BFS-based path planning across the 3x3 MARL grid with step-accurate
preemption scheduling. Works for single-node mode too (trivial 1-node path).

Components
----------
EmergencyVehicle   — dataclass tracking vehicle state across the grid
EmergencyRouter    — BFS path planner on the 3x3 adjacency map
PreemptionScheduler — maps path + speed to per-node preemption windows
EmergencyManager   — top-level coordinator; attach one per session

Usage (inside session.py)
--------------------------
    manager = EmergencyManager(grid_envs)   # dict {node_id: TrafficEnvironment}
    vehicle_id = manager.dispatch(
        entry_node=0, dest_node=8,
        vehicle_type="ambulance"
    )
    # Each step:
    manager.tick(current_step)
    metrics = manager.metrics(vehicle_id)
"""

from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Grid topology — 3x3, row-major
# ---------------------------------------------------------------------------
#
#   0 — 1 — 2
#   |   |   |
#   3 — 4 — 5
#   |   |   |
#   6 — 7 — 8
#
# Node 4 is the centre intersection.

GRID_ADJACENCY: Dict[int, List[int]] = {
    0: [1, 3],
    1: [0, 2, 4],
    2: [1, 5],
    3: [0, 4, 6],
    4: [1, 3, 5, 7],
    5: [2, 4, 8],
    6: [3, 7],
    7: [4, 6, 8],
    8: [5, 7],
}

# Which signal phase must be green for a vehicle approaching from each
# cardinal direction between two adjacent nodes.
# Key: (from_node, to_node) → required phase name
_REQUIRED_PHASE: Dict[Tuple[int, int], str] = {}

def _build_phase_map() -> None:
    """
    Populate _REQUIRED_PHASE based on grid geometry.
    Nodes in the same row (same row index) require EW_GREEN.
    Nodes in the same column require NS_GREEN.
    """
    for node, neighbors in GRID_ADJACENCY.items():
        row_n = node // 3
        col_n = node % 3
        for nb in neighbors:
            row_nb = nb // 3
            col_nb = nb % 3
            if row_n == row_nb:
                # Same row → East-West movement
                _REQUIRED_PHASE[(node, nb)] = "EW_GREEN"
            else:
                # Same column → North-South movement
                _REQUIRED_PHASE[(node, nb)] = "NS_GREEN"

_build_phase_map()


# ---------------------------------------------------------------------------
# Vehicle types and speeds
# ---------------------------------------------------------------------------

# Steps (seconds) a vehicle spends traversing one intersection's zone
_VEHICLE_TRANSIT_STEPS: Dict[str, int] = {
    "ambulance": 8,
    "fire":      10,
    "police":    6,
}

_DEFAULT_TRANSIT_STEPS: int = 8


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class EmergencyVehicle:
    """Tracks state of one emergency vehicle across the grid."""
    vehicle_id:    str
    vehicle_type:  str
    entry_node:    int
    dest_node:     int
    path:          List[int]          # ordered list of node IDs to traverse

    # Mutable state
    path_index:    int   = 0          # index into path[] for current node
    arrived:       bool  = False
    step_entered:  int   = 0          # sim step when dispatched
    step_arrived:  int   = -1         # sim step when dest reached

    # Per-node timing: {node_id: (preempt_start_step, preempt_end_step)}
    preemption_windows: Dict[int, Tuple[int, int]] = field(default_factory=dict)

    @property
    def current_node(self) -> int:
        if self.path_index >= len(self.path):
            return self.dest_node
        return self.path[self.path_index]

    @property
    def progress_pct(self) -> float:
        if not self.path:
            return 100.0
        return round(self.path_index / len(self.path) * 100.0, 1)


@dataclass
class PreemptionWindow:
    """
    Describes when a specific node should be under preemption.
    """
    node_id:      int
    phase:        str    # "NS_GREEN" or "EW_GREEN"
    start_step:   int
    end_step:     int    # inclusive

    def is_active(self, current_step: int) -> bool:
        return self.start_step <= current_step <= self.end_step


# ---------------------------------------------------------------------------
# EmergencyRouter — BFS path planner
# ---------------------------------------------------------------------------

class EmergencyRouter:
    """
    Computes shortest path (fewest intersections) between two nodes
    in the 3x3 grid using BFS.

    For single-node mode (entry == dest), returns [entry_node].
    """

    @staticmethod
    def plan(entry_node: int, dest_node: int) -> List[int]:
        """
        Return ordered list of node IDs from entry_node to dest_node,
        inclusive of both endpoints.

        Raises ValueError if either node is outside [0, 8].
        """
        if not (0 <= entry_node <= 8 and 0 <= dest_node <= 8):
            raise ValueError(
                f"Nodes must be in [0,8]. Got entry={entry_node}, dest={dest_node}"
            )
        if entry_node == dest_node:
            return [entry_node]

        # BFS
        queue: deque = deque([[entry_node]])
        visited = {entry_node}

        while queue:
            path = queue.popleft()
            current = path[-1]

            for neighbor in GRID_ADJACENCY.get(current, []):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == dest_node:
                    return new_path
                visited.add(neighbor)
                queue.append(new_path)

        # Should never happen in a connected 3x3 grid
        raise RuntimeError(
            f"No path found from {entry_node} to {dest_node}. "
            "Grid topology may be corrupted."
        )

    @staticmethod
    def estimated_arrival_step(
        path: List[int],
        transit_steps: int,
        current_step: int,
    ) -> int:
        """
        Estimate the simulation step at which the vehicle reaches dest_node.
        """
        return current_step + len(path) * transit_steps


# ---------------------------------------------------------------------------
# PreemptionScheduler — maps path to per-node timing windows
# ---------------------------------------------------------------------------

class PreemptionScheduler:
    """
    Given a planned path and vehicle transit speed, computes exactly
    which sim step each node on the path should activate preemption,
    and for how long.

    Preemption window per node = transit_steps + 2 buffer steps.
    """

    _BUFFER_STEPS: int = 2   # extra steps of green before/after vehicle

    def __init__(
        self,
        path: List[int],
        transit_steps: int,
        dispatch_step: int,
    ) -> None:
        self.path           = path
        self.transit_steps  = transit_steps
        self.dispatch_step  = dispatch_step
        self.windows: List[PreemptionWindow] = self._compute_windows()

    def _compute_windows(self) -> List[PreemptionWindow]:
        windows = []
        buf = self._BUFFER_STEPS
        step_cursor = self.dispatch_step

        for i, node_id in enumerate(self.path):
            # Phase required to move from this node to the next
            if i < len(self.path) - 1:
                next_node = self.path[i + 1]
                phase = _REQUIRED_PHASE.get((node_id, next_node), "NS_GREEN")
            else:
                # Last node — keep same phase as arrival direction
                if i > 0:
                    prev_node = self.path[i - 1]
                    phase = _REQUIRED_PHASE.get((prev_node, node_id), "NS_GREEN")
                else:
                    phase = "NS_GREEN"

            start = max(0, step_cursor - buf)
            end   = step_cursor + self.transit_steps + buf

            windows.append(PreemptionWindow(
                node_id=node_id,
                phase=phase,
                start_step=start,
                end_step=end,
            ))
            step_cursor += self.transit_steps

        return windows

    def active_windows(self, current_step: int) -> List[PreemptionWindow]:
        """Return all windows that are currently active."""
        return [w for w in self.windows if w.is_active(current_step)]

    def estimated_arrival(self) -> int:
        if not self.windows:
            return self.dispatch_step
        return self.windows[-1].end_step

    def to_dict(self) -> List[dict]:
        return [
            {
                "node_id":    w.node_id,
                "phase":      w.phase,
                "start_step": w.start_step,
                "end_step":   w.end_step,
            }
            for w in self.windows
        ]


# ---------------------------------------------------------------------------
# EmergencyMetrics
# ---------------------------------------------------------------------------

@dataclass
class EmergencyMetrics:
    """Outcome metrics for a completed emergency run."""
    vehicle_id:         str
    vehicle_type:       str
    path:               List[int]
    path_length:        int
    steps_in_transit:   int          # actual steps from dispatch to arrival
    estimated_steps:    int          # predicted at dispatch time
    seconds_saved:      float        # vs no-preemption baseline
    delay_cost_imposed: float        # extra vehicle-steps imposed on cross traffic
    arrived:            bool


# ---------------------------------------------------------------------------
# EmergencyManager — top-level coordinator
# ---------------------------------------------------------------------------

class EmergencyManager:
    """
    Manages all active emergency vehicles for a session.
    Attach one instance to each Session or MARLSession.

    Parameters
    ----------
    grid_envs : dict {node_id: TrafficEnvironment}
        For single-intersection mode, pass {0: env}.
    """

    def __init__(self, grid_envs: Dict[int, object]) -> None:
        self._envs: Dict[int, object] = grid_envs

        # Active vehicles: vehicle_id → (EmergencyVehicle, PreemptionScheduler)
        self._active: Dict[str, Tuple[EmergencyVehicle, PreemptionScheduler]] = {}

        # Completed vehicles: vehicle_id → EmergencyMetrics
        self._completed: Dict[str, EmergencyMetrics] = {}

        # Cross-traffic delay accumulator per node
        # Counts extra red-light vehicle-steps imposed on non-emergency traffic
        self._delay_imposed: Dict[int, float] = {n: 0.0 for n in grid_envs}

    def dispatch(
        self,
        entry_node: int,
        dest_node: int,
        vehicle_type: str,
        current_step: int,
    ) -> str:
        """
        Plan route, build preemption schedule, register vehicle.
        Returns vehicle_id (UUID string).

        Parameters
        ----------
        entry_node : int
            Grid node where the vehicle enters [0-8]. Use 0 for single-node.
        dest_node : int
            Grid node the vehicle must reach.
        vehicle_type : str
            One of "ambulance", "fire", "police".
        current_step : int
            Current simulation step (from session.step_count).
        """
        vehicle_type = vehicle_type.lower()
        transit_steps = _VEHICLE_TRANSIT_STEPS.get(
            vehicle_type, _DEFAULT_TRANSIT_STEPS
        )

        path = EmergencyRouter.plan(entry_node, dest_node)
        scheduler = PreemptionScheduler(path, transit_steps, current_step)

        vehicle = EmergencyVehicle(
            vehicle_id=str(uuid.uuid4())[:8],
            vehicle_type=vehicle_type,
            entry_node=entry_node,
            dest_node=dest_node,
            path=path,
            path_index=0,
            arrived=False,
            step_entered=current_step,
            preemption_windows={
                w.node_id: (w.start_step, w.end_step)
                for w in scheduler.windows
            },
        )

        self._active[vehicle.vehicle_id] = (vehicle, scheduler)
        return vehicle.vehicle_id

    def tick(self, current_step: int) -> None:
        """
        Advance all active vehicles by one simulation step.
        Apply/release preemption flags on the appropriate environments.
        Call this every step inside session.step().
        """
        completed_ids = []

        for vid, (vehicle, scheduler) in self._active.items():
            active_windows = scheduler.active_windows(current_step)
            active_node_ids = {w.node_id for w in active_windows}

            # Apply preemption to active nodes
            for window in active_windows:
                env = self._envs.get(window.node_id)
                if env is None:
                    continue
                env.preemption_active = True
                env.preemption_phase  = window.phase

                # Accumulate delay cost: count vehicles held at red
                # on the cross-direction approaches
                try:
                    total_cross_queue = self._cross_queue(
                        env, window.phase
                    )
                    self._delay_imposed[window.node_id] = (
                        self._delay_imposed.get(window.node_id, 0.0)
                        + total_cross_queue
                    )
                except Exception:
                    pass

            # Release preemption on nodes no longer in active window
            for node_id, env in self._envs.items():
                if node_id not in active_node_ids:
                    # Only release if this manager set it
                    if getattr(env, "preemption_active", False):
                        env.preemption_active = False
                        env.preemption_phase  = None

            # Advance vehicle position along path
            for i, node_id in enumerate(vehicle.path):
                window = next(
                    (w for w in scheduler.windows if w.node_id == node_id),
                    None,
                )
                if window and current_step > window.end_step:
                    vehicle.path_index = max(vehicle.path_index, i + 1)

            # Check arrival
            if vehicle.path_index >= len(vehicle.path) and not vehicle.arrived:
                vehicle.arrived       = True
                vehicle.step_arrived  = current_step
                completed_ids.append(vid)

        # Move completed vehicles to history
        for vid in completed_ids:
            vehicle, scheduler = self._active.pop(vid)
            steps_in_transit = vehicle.step_arrived - vehicle.step_entered
            est_steps        = scheduler.estimated_arrival() - vehicle.step_entered

            # Seconds saved vs no-preemption baseline
            # Baseline: vehicle waits average 15s per intersection at red
            baseline_wait_per_node = 15.0
            saved = max(
                0.0,
                len(vehicle.path) * baseline_wait_per_node
                - max(0, steps_in_transit - len(vehicle.path)
                      * _VEHICLE_TRANSIT_STEPS.get(vehicle.vehicle_type, 8))
            )

            total_delay = sum(
                self._delay_imposed.get(n, 0.0) for n in vehicle.path
            )

            self._completed[vid] = EmergencyMetrics(
                vehicle_id=vid,
                vehicle_type=vehicle.vehicle_type,
                path=vehicle.path,
                path_length=len(vehicle.path),
                steps_in_transit=steps_in_transit,
                estimated_steps=est_steps,
                seconds_saved=round(saved, 2),
                delay_cost_imposed=round(total_delay, 2),
                arrived=True,
            )

    def metrics(self, vehicle_id: str) -> Optional[dict]:
        """
        Return metrics for a vehicle. Works for both active and completed.

        Returns None if vehicle_id not found.
        """
        if vehicle_id in self._completed:
            m = self._completed[vehicle_id]
            return {
                "vehicle_id":         m.vehicle_id,
                "vehicle_type":       m.vehicle_type,
                "path":               m.path,
                "path_length":        m.path_length,
                "steps_in_transit":   m.steps_in_transit,
                "estimated_steps":    m.estimated_steps,
                "seconds_saved":      m.seconds_saved,
                "delay_cost_imposed": m.delay_cost_imposed,
                "arrived":            m.arrived,
                "status":             "completed",
            }

        if vehicle_id in self._active:
            vehicle, scheduler = self._active[vehicle_id]
            return {
                "vehicle_id":   vehicle.vehicle_id,
                "vehicle_type": vehicle.vehicle_type,
                "path":         vehicle.path,
                "path_length":  len(vehicle.path),
                "current_node": vehicle.current_node,
                "path_index":   vehicle.path_index,
                "progress_pct": vehicle.progress_pct,
                "arrived":      vehicle.arrived,
                "status":       "active",
                "preemption_schedule": scheduler.to_dict(),
            }

        return None

    def all_active_vehicle_ids(self) -> List[str]:
        return list(self._active.keys())

    def all_completed_vehicle_ids(self) -> List[str]:
        return list(self._completed.keys())

    def active_preemption_summary(self, current_step: int) -> Dict[int, dict]:
        """
        Returns a dict {node_id: {phase, vehicle_id}} for all nodes
        currently under preemption. Used by /state render_hints.
        """
        result: Dict[int, dict] = {}
        for vid, (vehicle, scheduler) in self._active.items():
            for window in scheduler.active_windows(current_step):
                result[window.node_id] = {
                    "phase":      window.phase,
                    "vehicle_id": vid,
                    "vehicle_type": vehicle.vehicle_type,
                }
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cross_queue(env: object, green_phase: str) -> float:
        """
        Return total queue length on cross-direction lanes
        (the ones held at red during preemption).
        """
        try:
            lanes = env.lanes
            if green_phase == "NS_GREEN":
                # EW lanes are held red
                cross_indices = [4, 5, 6, 7, 10, 11]
            else:
                # NS lanes are held red
                cross_indices = [0, 1, 2, 3, 8, 9]
            return sum(lanes[i].queue for i in cross_indices
                       if i < len(lanes))
        except Exception:
            return 0.0