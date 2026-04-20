"""
IntelliFlow LLM Meta-Controller  v1.2.0
==========================================

Fixes in v1.2.0
---------------
- _template_match() reasoning string was ALWAYS showing keywords from
  _TEMPLATES[0][0] (the ambulance template) regardless of which template
  actually matched.  Fixed to iterate over the matched template's own
  keywords.
- Template matching now scores ALL templates and picks the highest, then
  correctly extracts the matched keywords for the reasoning string.
- Minor: _noop reasoning truncated to 200 chars to keep responses tidy.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEFAULT_OVERRIDE_DURATION: int   = 60
_MAX_OVERRIDE_DURATION:     int   = 300
_MIN_OVERRIDE_DURATION:     int   = 10
_API_TIMEOUT_S:             float = 8.0

_WEIGHT_MIN: float = -5.0
_WEIGHT_MAX: float =  5.0


# ---------------------------------------------------------------------------
# PolicyOverride
# ---------------------------------------------------------------------------

@dataclass
class PolicyOverride:
    phase_overrides:      Dict[int, str]   = field(default_factory=dict)
    reward_weight_deltas: Dict[str, float] = field(default_factory=dict)
    override_duration:    int              = _DEFAULT_OVERRIDE_DURATION
    affected_nodes:       List[int]        = field(default_factory=list)
    reasoning:            str              = ""
    source:               str              = "noop"
    expires_at_step:      int              = -1

    def is_active(self, current_step: int) -> bool:
        return self.expires_at_step > 0 and current_step <= self.expires_at_step

    def to_dict(self) -> dict:
        return {
            "phase_overrides":      self.phase_overrides,
            "reward_weight_deltas": self.reward_weight_deltas,
            "override_duration":    self.override_duration,
            "affected_nodes":       self.affected_nodes,
            "reasoning":            self.reasoning,
            "source":               self.source,
            "expires_at_step":      self.expires_at_step,
        }


# ---------------------------------------------------------------------------
# Template matcher — zero-shot fallback (no API key needed)
# ---------------------------------------------------------------------------

# Each entry: (keywords, phase_override_or_None, weight_deltas, duration)
_TEMPLATES = [
    (
        ["ambulance", "emergency", "hospital", "fire truck", "police", "preempt"],
        None,
        {"w_throughput": 1.0, "w_spillback": -0.5},
        40,
    ),
    (
        ["rush hour", "rush", "peak", "surge", "heavy traffic"],
        None,
        {"w_throughput": 0.5, "w_wait": -0.3},
        90,
    ),
    (
        ["north", "south", "ns", "n-s", "north-south"],
        "NS_GREEN",
        {"w_throughput": 0.3},
        30,
    ),
    (
        ["east", "west", "ew", "e-w", "east-west"],
        "EW_GREEN",
        {"w_throughput": 0.3},
        30,
    ),
    (
        ["fair", "balance", "equal", "starvation"],
        None,
        {"w_fairness": -0.8, "w_wait": -0.4},
        60,
    ),
    (
        ["gridlock", "jam", "blocked", "stuck", "congestion"],
        None,
        {"w_spillback": -1.0, "w_throughput": 0.6},
        50,
    ),
    (
        ["rain", "wet", "weather", "fog", "slow down"],
        None,
        {"w_spillback": -0.8, "w_switch": -0.3},
        80,
    ),
    (
        ["clear", "reset", "normal", "default", "stop override"],
        None,
        {},
        0,
    ),
]


def _template_match(command: str) -> Optional[PolicyOverride]:
    """
    Rule-based command parser.  Returns a PolicyOverride or None.

    BUG FIX: previously the reasoning string always showed the keywords from
    _TEMPLATES[0] (ambulance) regardless of which template matched.
    Now it correctly captures the matched keywords from the winning template.
    """
    command_lower = command.lower()
    best_score    = 0
    best_idx      = -1

    for idx, (keywords, _phase, _weight_deltas, _duration) in enumerate(_TEMPLATES):
        score = sum(1 for kw in keywords if kw in command_lower)
        if score > best_score:
            best_score = score
            best_idx   = idx

    if best_score == 0 or best_idx < 0:
        return None

    keywords, phase, weight_deltas, duration = _TEMPLATES[best_idx]

    # Collect only the keywords that actually matched
    matched_kws = [kw for kw in keywords if kw in command_lower]

    # Extract node IDs mentioned in command (digits 0-8)
    mentioned_nodes = [int(d) for d in re.findall(r'\b[0-8]\b', command)]
    if not mentioned_nodes:
        mentioned_nodes = list(range(9))

    phase_overrides: Dict[int, str] = {}
    if phase:
        for n in mentioned_nodes:
            phase_overrides[n] = phase

    if duration == 0:
        return PolicyOverride(
            phase_overrides={},
            reward_weight_deltas={},
            override_duration=0,
            affected_nodes=[],
            reasoning="Override cancelled by operator command.",
            source="template",
        )

    return PolicyOverride(
        phase_overrides=phase_overrides,
        reward_weight_deltas={
            k: max(_WEIGHT_MIN, min(_WEIGHT_MAX, v))
            for k, v in weight_deltas.items()
        },
        override_duration=max(_MIN_OVERRIDE_DURATION,
                              min(_MAX_OVERRIDE_DURATION, duration)),
        affected_nodes=mentioned_nodes,
        # BUG FIX: use matched_kws, not _TEMPLATES[0][0]
        reasoning=f"Template match (score={best_score}) — keywords: {matched_kws}",
        source="template",
    )


# ---------------------------------------------------------------------------
# LLM prompt builder
# ---------------------------------------------------------------------------

def _build_system_prompt() -> str:
    return (
        "You are the AI brain of IntelliFlow, an adaptive urban traffic control system "
        "managing a 3x3 grid of 9 intersections (nodes 0-8, row-major: 0=top-left, 8=bottom-right).\n\n"
        "The operator has issued a natural language command. Your job is to:\n"
        "1. Reason step by step about the current traffic state.\n"
        "2. Decide which nodes to override and with what signal phase.\n"
        "3. Decide which reward weights to temporarily adjust.\n"
        "4. Decide how long the override should last (in simulation steps, 1 step = 1 second).\n\n"
        "Available phases: NS_GREEN, EW_GREEN, ALL_RED\n"
        "Adjustable reward weights: w_throughput, w_wait, w_fairness, w_switch, w_spillback\n"
        "Weight delta range: [-2.0, +2.0]\n"
        "Duration range: [10, 300] steps\n\n"
        "You MUST respond with ONLY valid JSON. No prose before or after. No markdown. "
        "Schema:\n"
        "{\n"
        '  "reasoning": "<2-3 sentence chain of thought>",\n'
        '  "phase_overrides": {"<node_id_int>": "<phase_name>"},\n'
        '  "reward_weight_deltas": {"<weight_name>": <float_delta>},\n'
        '  "override_duration": <int_steps>,\n'
        '  "affected_nodes": [<int>, ...]\n'
        "}\n\n"
        "If the command is unclear or contradictory, return an empty override with "
        'reasoning explaining why. Never return null. Always return valid JSON.'
    )


def _build_user_prompt(command: str, grid_state: dict) -> str:
    if "lanes" in grid_state:
        lanes   = grid_state.get("lanes", [])
        metrics = grid_state.get("metrics", {})
        phase   = grid_state.get("phase", "?")
        step    = grid_state.get("step", 0)
        lane_summary = {l["name"]: round(l.get("queue_pct", 0), 1) for l in lanes}
        context = {
            "mode":        "single_node",
            "step":        step,
            "phase":       phase,
            "lane_pct":    lane_summary,
            "avg_delay_s": metrics.get("avg_delay", 0),
            "efficiency":  metrics.get("efficiency_ratio", 0),
            "los":         metrics.get("los", "?"),
            "spillback":   metrics.get("spillback_count", 0),
        }
    elif "nodes" in grid_state:
        nodes_raw = grid_state.get("nodes", {})
        context   = {"mode": "marl_grid", "nodes": {}}
        for node_id, nstate in nodes_raw.items():
            m = nstate.get("metrics", {})
            context["nodes"][str(node_id)] = {
                "phase":     nstate.get("phase", "?"),
                "ns_queue":  round(nstate.get("direction_summary", {}).get("NS", {}).get("queue", 0), 1),
                "ew_queue":  round(nstate.get("direction_summary", {}).get("EW", {}).get("queue", 0), 1),
                "avg_delay": round(m.get("avg_delay", 0), 1),
                "spillback": m.get("spillback_count", 0),
                "los":       m.get("los", "?"),
            }
    else:
        context = {"mode": "unknown", "raw": str(grid_state)[:400]}

    return (
        f"Operator command: \"{command}\"\n\n"
        f"Current traffic state:\n{json.dumps(context, indent=2)}\n\n"
        "Respond with ONLY the JSON override object."
    )


# ---------------------------------------------------------------------------
# MetaController
# ---------------------------------------------------------------------------

class MetaController:
    def __init__(
        self,
        api_key:  Optional[str] = None,
        model:    str           = "gpt-4o-mini",
        base_url: Optional[str] = None,
    ) -> None:
        self.model      = model
        self._client    = None
        self._available = False

        self._active_overrides:  List[PolicyOverride]       = []
        self.last_reasoning:     str                        = "No commands issued yet."
        self._original_weights:  Dict[int, Dict[str, float]] = {}

        key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY")
        if key:
            try:
                import openai
                self._client = openai.OpenAI(
                    api_key=key,
                    base_url=base_url or os.environ.get("API_BASE_URL") or None,
                    timeout=_API_TIMEOUT_S,
                )
                self._available = True
            except ImportError:
                pass

    # ------------------------------------------------------------------
    # Primary interface
    # ------------------------------------------------------------------

    def command(
        self,
        natural_language: str,
        grid_state:       dict,
        current_step:     int,
    ) -> PolicyOverride:
        natural_language = natural_language.strip()
        if not natural_language:
            return self._noop("Empty command received.")

        if self._available:
            override = self._llm_command(natural_language, grid_state)
            if override is not None:
                override.expires_at_step = current_step + override.override_duration
                self.last_reasoning = override.reasoning
                return override

        override = _template_match(natural_language)
        if override is not None:
            override.expires_at_step = current_step + override.override_duration
            self.last_reasoning = override.reasoning
            return override

        return self._noop(
            f"Command not understood: '{natural_language[:80]}'. "
            "Try keywords like 'prioritise north', 'rush hour', 'gridlock', 'clear'."
        )

    def inject(
        self,
        grid_envs:    Dict[int, Any],
        override:     PolicyOverride,
        current_step: int,
    ) -> None:
        if override.override_duration == 0:
            self._restore_all_weights(grid_envs)
            self._active_overrides.clear()
            return

        if override.expires_at_step <= 0:
            override.expires_at_step = current_step + override.override_duration

        for node_id, env in grid_envs.items():
            if node_id not in self._original_weights:
                self._original_weights[node_id] = self._read_weights(env)

        for node_id, phase_name in override.phase_overrides.items():
            env = grid_envs.get(node_id)
            if env is None:
                continue
            try:
                from app.core.environment import Phase
                env._transition_to(Phase[phase_name])
            except Exception:
                pass

        for node_id, env in grid_envs.items():
            for weight_name, delta in override.reward_weight_deltas.items():
                current_val = getattr(env, weight_name, None)
                if current_val is not None:
                    new_val = max(_WEIGHT_MIN, min(_WEIGHT_MAX, current_val + delta))
                    setattr(env, weight_name, new_val)

        self._active_overrides.append(override)

    def tick(self, grid_envs: Dict[int, Any], current_step: int) -> None:
        still_active = []
        for override in self._active_overrides:
            if override.is_active(current_step):
                still_active.append(override)
            else:
                # Restore weights — fall back to ALL nodes if affected_nodes
                # is empty (prevents silent weight-leak when LLM returns no nodes)
                restore_targets = (
                    override.affected_nodes
                    if override.affected_nodes
                    else list(grid_envs.keys())
                )
                self._restore_weights_for(grid_envs, restore_targets)
        self._active_overrides = still_active

    def is_override_active(self, current_step: int) -> bool:
        return any(o.is_active(current_step) for o in self._active_overrides)

    def active_override_summary(self, current_step: int) -> List[dict]:
        return [
            o.to_dict() for o in self._active_overrides
            if o.is_active(current_step)
        ]

    # ------------------------------------------------------------------
    # LLM call
    # ------------------------------------------------------------------

    def _llm_command(
        self,
        natural_language: str,
        grid_state:       dict,
    ) -> Optional[PolicyOverride]:
        try:
            t0 = time.time()
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _build_system_prompt()},
                    {"role": "user",   "content": _build_user_prompt(natural_language, grid_state)},
                ],
                max_tokens=400,
                temperature=0.2,
            )
            latency = round(time.time() - t0, 2)
            raw = response.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            parsed = json.loads(raw)
            return self._parse_override(parsed, source="llm", latency=latency)

        except json.JSONDecodeError:
            return None
        except Exception:
            return None

    def _parse_override(
        self,
        parsed:  dict,
        source:  str   = "llm",
        latency: float = 0.0,
    ) -> Optional[PolicyOverride]:
        if not isinstance(parsed, dict):
            return None

        raw_phases   = parsed.get("phase_overrides", {})
        valid_phases = {"NS_GREEN", "EW_GREEN", "ALL_RED", "NS_MINOR"}
        phase_overrides: Dict[int, str] = {}
        for k, v in raw_phases.items():
            try:
                node_id = int(k)
                if 0 <= node_id <= 8 and v in valid_phases:
                    phase_overrides[node_id] = v
            except (ValueError, TypeError):
                continue

        raw_weights       = parsed.get("reward_weight_deltas", {})
        valid_weight_names = {
            "w_throughput", "w_wait", "w_fairness",
            "w_switch", "w_spillback", "w_emission",
        }
        reward_weight_deltas: Dict[str, float] = {}
        for k, v in raw_weights.items():
            if k in valid_weight_names:
                try:
                    delta = float(v)
                    reward_weight_deltas[k] = max(_WEIGHT_MIN, min(_WEIGHT_MAX, delta))
                except (ValueError, TypeError):
                    continue

        try:
            duration = int(parsed.get("override_duration", _DEFAULT_OVERRIDE_DURATION))
            duration = max(_MIN_OVERRIDE_DURATION, min(_MAX_OVERRIDE_DURATION, duration))
        except (ValueError, TypeError):
            duration = _DEFAULT_OVERRIDE_DURATION

        raw_nodes      = parsed.get("affected_nodes", [])
        affected_nodes = []
        for n in raw_nodes:
            try:
                node_id = int(n)
                if 0 <= node_id <= 8:
                    affected_nodes.append(node_id)
            except (ValueError, TypeError):
                continue
        if not affected_nodes:
            affected_nodes = list(phase_overrides.keys())

        reasoning = str(parsed.get("reasoning", ""))[:500]
        if latency > 0:
            reasoning += f" [LLM latency: {latency}s]"

        return PolicyOverride(
            phase_overrides=phase_overrides,
            reward_weight_deltas=reward_weight_deltas,
            override_duration=duration,
            affected_nodes=affected_nodes,
            reasoning=reasoning,
            source=source,
        )

    # ------------------------------------------------------------------
    # Weight helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _read_weights(env: Any) -> Dict[str, float]:
        names = ["w_throughput", "w_wait", "w_fairness", "w_switch", "w_spillback", "w_emission"]
        return {name: getattr(env, name, 0.0) for name in names if hasattr(env, name)}

    def _restore_weights_for(self, grid_envs: Dict[int, Any], affected_nodes: List[int]) -> None:
        for node_id in affected_nodes:
            env      = grid_envs.get(node_id)
            original = self._original_weights.get(node_id)
            if env is None or original is None:
                continue
            for name, val in original.items():
                setattr(env, name, val)

    def _restore_all_weights(self, grid_envs: Dict[int, Any]) -> None:
        self._restore_weights_for(grid_envs, list(grid_envs.keys()))
        self._original_weights.clear()

    @staticmethod
    def _noop(reason: str) -> PolicyOverride:
        return PolicyOverride(
            phase_overrides={},
            reward_weight_deltas={},
            override_duration=0,
            affected_nodes=[],
            reasoning=reason[:200],
            source="noop",
            expires_at_step=-1,
        )

    def __repr__(self) -> str:
        return (
            f"MetaController(model={self.model!r}, "
            f"available={self._available}, "
            f"active_overrides={len(self._active_overrides)})"
        )