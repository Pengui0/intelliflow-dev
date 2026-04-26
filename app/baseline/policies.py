from __future__ import annotations

import json
import os
import time
import random
from typing import Dict, List

LANE_NAMES = [
    "N_through", "N_right", "S_through", "S_right",
    "E_through", "E_right", "W_through", "W_right",
    "N_left",    "S_left",  "E_left",    "W_left",
]


class PressurePolicy:
    POLICY_NAME = "pressure"

    def __init__(self, switch_threshold: float = 3.0, min_steps: int = 5):
        self.threshold = switch_threshold
        self.min_steps = min_steps
        self._steps = 0

    def act(self, obs: Dict) -> int:
        self._steps += 1
        ql = obs.get("queue_lengths", [0.0] * 12)
        phase_oh = obs.get("phase_onehot", [1, 0, 0, 0])
        idx = phase_oh.index(max(phase_oh))
        elapsed_norm = obs.get("phase_elapsed_norm", 0)
        elapsed = elapsed_norm * 90

        if elapsed < self.min_steps:
            return 0  # MAINTAIN

        ns = sum(ql[i] for i in [0, 1, 2, 3, 8, 9])
        ew = sum(ql[i] for i in [4, 5, 6, 7, 10, 11])

        # LSTM-augmented pressure: if obs_vector present (73-dim MARL obs),
        # blend predicted future inflows into current queue pressure.
        # Indices 57-68 are lstm_predictions (12 lanes, normalised 0-1).
        obs_vec = obs.get("observation_vector", [])
        if len(obs_vec) >= 69:
            lstm_pred = obs_vec[57:69]
            ns_pred = sum(lstm_pred[i] for i in [0, 1, 2, 3, 8, 9])
            ew_pred = sum(lstm_pred[i] for i in [4, 5, 6, 7, 10, 11])
            # Blend 70% current queue, 30% predicted future — forward-looking pressure
            ns = 0.7 * ns + 0.3 * ns_pred
            ew = 0.7 * ew + 0.3 * ew_pred

        if idx == 2:  # ALL_RED
            return 0
        if idx == 0 and ew - ns > self.threshold * 0.1:
            self._steps = 0
            return 1
        if idx == 1 and ns - ew > self.threshold * 0.1:
            self._steps = 0
            return 1
        if idx == 0 and ns > 0.75:
            return 2
        if idx == 1 and ew > 0.75:
            return 2
        return 0


class FixedCyclePolicy:
    def __init__(self, ns_green: int = 30, ew_green: int = 30, amber: int = 3):
        self.ns_green = ns_green
        self.ew_green = ew_green
        self.amber = amber
        self._step = 0

    def act(self, obs: Dict) -> int:
        self._step += 1
        cycle = self.ns_green + self.amber + self.ew_green + self.amber
        pos = self._step % cycle

        if pos == self.ns_green:
            return 3
        if pos == self.ns_green + self.amber:
            return 1
        if pos == self.ns_green + self.amber + self.ew_green:
            return 3
        if pos == 0:
            return 1
        return 0


class RandomPolicy:
    def __init__(self, seed: int = 42):
        self._rng = random.Random(seed)

    def act(self, obs: Dict) -> int:
        return self._rng.randint(0, 4)


class LLMPolicy:
    SYSTEM = (
        "You are an expert traffic signal controller AI. "
        "Control a 4-way intersection to maximise throughput and minimise delay.\n"
        "Actions: 0=MAINTAIN, 1=SWITCH_PHASE, 2=EXTEND_GREEN, 3=FORCE_ALL_RED, 4=YIELD_MINOR\n"
        "Respond ONLY with JSON: {\"action\": <0-4>}"
    )

    def __init__(self, model: str = None):
        self.model = model or os.environ.get("MODEL_NAME", "gpt-4o-mini")
        self._fallback = PressurePolicy()
        self.calls = 0
        self.latencies: List[float] = []

        try:
            import openai
            self._client = openai.OpenAI(
                api_key=os.environ.get("API_KEY") or os.environ.get("OPENAI_API_KEY", ""),
                base_url=os.environ.get("API_BASE_URL") or None,
            )
            self._available = True
        except ImportError:
            print("WARNING: openai package not installed. Falling back to pressure policy.")
            self._available = False

    def act(self, obs: Dict) -> int:
        if not self._available:
            return self._fallback.act(obs)

        try:
            ql = obs.get("queue_lengths", [])
            phase_oh = obs.get("phase_onehot", [1, 0, 0, 0])
            phase_names = ["NS_GREEN", "EW_GREEN", "ALL_RED", "NS_MINOR"]
            phase = phase_names[phase_oh.index(max(phase_oh))]
            queue_map = {LANE_NAMES[i]: round(ql[i], 2) for i in range(min(len(ql), 12))}

            msg = (
                f"Phase: {phase} | "
                f"Elapsed(norm): {obs.get('phase_elapsed_norm', 0):.2f} | "
                f"Queues: {json.dumps(queue_map)} | "
                f"Pressure NS-EW: {obs.get('pressure_differential', 0):.3f} | "
                f"Fairness: {obs.get('fairness_score', 0):.3f}"
            )

            t0 = time.time()
            resp = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM},
                    {"role": "user", "content": msg},
                ],
                max_tokens=50,
                temperature=0.0,
            )
            self.latencies.append(time.time() - t0)
            self.calls += 1

            content = resp.choices[0].message.content.strip()
            parsed = json.loads(content)
            action = int(parsed.get("action", 0))
            return max(0, min(4, action))
        except Exception:
            return self._fallback.act(obs)

    @property
    def avg_latency_ms(self) -> float:
        if not self.latencies:
            return 0.0
        return round(sum(self.latencies) / len(self.latencies) * 1000, 2)


class DQNInlinePolicy:
    """
    Minimal DQN forward-pass policy for use in /baseline and /benchmark.
    Loads dqn_weights.json from disk; falls back to pressure on any error.
    Reconstructs the full 57-dim observation vector from the obs dict
    so it works inside run_baseline_episode without observation_vector key.
    """
    def __init__(self) -> None:
        import numpy as np
        import json, os
        self._fallback = PressurePolicy()
        self._weights = None
        _candidates = [
            os.environ.get("INTELLIFLOW_DQN_WEIGHTS", ""),
            os.path.normpath(os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..", "api", "dqn_weights.json"
            )),
            os.path.join("app", "api", "dqn_weights.json"),
        ]
        for p in _candidates:
            if p and os.path.exists(p):
                try:
                    with open(p) as f:
                        self._weights = json.load(f)
                    print(f"[DQNInlinePolicy] Weights loaded from {p}")
                    break
                except Exception:
                    pass

    def act(self, obs: Dict) -> int:
        import numpy as np
        if self._weights is None:
            return self._fallback.act(obs)
        try:
            vec = obs.get("observation_vector")
            if vec is None:
                # Reconstruct 57-dim vector from observation dict fields
                ql  = obs.get("queue_lengths",     [0.0] * 12)
                tp  = obs.get("throughput_recent", [0.0] * 12)
                ai  = obs.get("arrival_intensity", [0.0] * 12)
                ph  = obs.get("phase_onehot",      [1, 0, 0, 0])
                sp  = obs.get("spillback_flags",   [0.0] * 12)
                vec = (
                    list(ql) + list(tp) + list(ai) + list(ph) + [
                        obs.get("phase_elapsed_norm",    0.0),
                        obs.get("fairness_score",        0.0),
                        obs.get("pressure_differential", 0.0),
                        obs.get("avg_delay_norm",        0.0),
                        obs.get("step_norm",             0.0),
                    ] + list(sp)
                )
            x = np.array(vec, dtype=np.float32)
            # Support both Python train.py format ({"layers":[...]}) and
            # raw JS format ({l1,l2,l3,l4}) in case normalize step was missed.
            raw = self._weights
            _acts = ["relu", "relu", "relu", "linear"]
            if "inference_layers" in raw:
                layers = raw["inference_layers"]
            elif "layers" in raw:
                layers = raw["layers"]
            elif "online" in raw and isinstance(raw.get("online"), dict):
                online = raw["online"]
                if "l1" in online:
                    layers = [{"W": online[k]["W"], "b": online[k]["b"], "activation": _acts[i]}
                              for i, k in enumerate(["l1","l2","l3","l4"]) if k in online]
                elif "layers" in online:
                    layers = online["layers"]
                else:
                    return self._fallback.act(obs)
            elif "l1" in raw:
                layers = [{"W": raw[k]["W"], "b": raw[k]["b"], "activation": _acts[i]}
                          for i, k in enumerate(["l1","l2","l3","l4"]) if k in raw]
            else:
                return self._fallback.act(obs)
            if not layers:
                return self._fallback.act(obs)
            for layer in layers:
                W = np.array(layer["W"], dtype=np.float32)
                b = np.array(layer["b"], dtype=np.float32)
                x = np.dot(x, W.T) + b
                if layer.get("activation") == "relu":
                    x = np.maximum(0, x)
            return int(np.argmax(x))
        except Exception:
            return self._fallback.act(obs)


async def run_baseline_episode(
    task_id: str,
    policy:  str  = "pressure",
    seed:    int  = 42,
    use_llm: bool = False,
) -> dict:
    """
    Run one full episode with the given policy inside the server process.
    Used by /baseline and /benchmark endpoints.
    """
    from app.tasks.registry import TASK_REGISTRY, EpisodeGrader, build_env
    from app.core.session import Session
    import uuid

    if task_id not in TASK_REGISTRY:
        raise ValueError(f"Unknown task_id {task_id!r}")

    spec = TASK_REGISTRY[task_id]
    if spec.env_config.get("grid_mode", False):
        raise ValueError(f"Task {task_id!r} is a grid task — use /reset with grid_mode=true")

    env = build_env(task_id, seed=seed)
    env.reset(seed=seed)

    if use_llm or policy == "llm":
        agent = LLMPolicy()
    elif policy == "fixed_cycle":
        agent = FixedCyclePolicy()
    elif policy == "random":
        agent = RandomPolicy(seed=seed)
    elif policy == "dqn":
        agent = DQNInlinePolicy()
    else:
        agent = PressurePolicy()

    from app.core.impact_calculator import ImpactCalculator
    impact = ImpactCalculator(baseline="fixed_cycle")

    total_reward = 0.0
    rewards      = []
    done         = False

    obs_obj = env._build_observation()
    obs     = obs_obj.to_dict()

    while not done:
        action              = agent.act(obs)
        obs_obj, reward, done, info = env.step(action)
        obs                 = obs_obj.to_dict()
        total_reward       += reward
        rewards.append(reward)
        impact.update(
            idle_queue=info.get("total_queue", 0.0),
            arrived_this_step=info.get("step_arrived", 0),
            cleared_this_step=info.get("step_cleared", 0),
        )

    analytics = env.analytics()
    summary   = analytics["episode_summary"]
    steps     = len(rewards)

    trajectory = {
        "total_cleared":           summary["total_cleared"],
        "total_arrived":           summary["total_arrived"],
        "steps_survived":          steps,
        "avg_delay":               summary["avg_delay_s"],
        "switch_count":            summary["phase_switches"],
        "peak_spillback_fraction": summary["peak_spillback_lanes"] / 12.0,
        "fairness_score":          1.0 - env._fairness_score(),
        "gridlock_terminated":     env._is_gridlock() and done,
    }

    grader = EpisodeGrader(spec)
    grade  = grader.grade(trajectory)

    n      = max(len(rewards), 1)
    mean_r = sum(rewards) / n

    return {
        "task_id":      task_id,
        "policy":       policy,
        "seed":         seed,
        "steps":        steps,
        "total_reward": round(total_reward, 4),
        "reward_mean":  round(mean_r, 4),
        "grade":        grade,
        "score":        grade["score"],
        "metrics": {
            "avg_delay_s":      summary["avg_delay_s"],
            "efficiency_ratio": summary["efficiency_ratio"],
            "los":              summary["los"],
            "total_cleared":    summary["total_cleared"],
            "emission_kg_co2":  summary["emission_kg_co2"],
        },
        "impact_summary": impact.summary(),
    }