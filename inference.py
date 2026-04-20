#!/usr/bin/env python3
"""
IntelliFlow Baseline Inference Script
=====================================
Runs the LLM agent (and pressure/fixed-cycle baselines)
across all three tasks and outputs reproducible baseline scores.

Usage:
    python inference.py [--task all|<task_id>] [--policy pressure|fixed_cycle|random|llm]
                        [--seed 42] [--host http://localhost:7860]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package not found. Install with: pip install requests")
    sys.exit(1)

from app.baseline.policies import PressurePolicy, FixedCyclePolicy, RandomPolicy, LLMPolicy
import numpy as np

# Resolve weights path robustly regardless of CWD or execution context.
# Priority: (1) env var override, (2) path relative to this file's directory,
# (3) path relative to CWD — covers both local dev and HF Spaces deployment.
def _resolve_dqn_weights_path(explicit: str | None) -> str:
    if explicit is not None:
        return explicit
    if "INTELLIFLOW_DQN_WEIGHTS" in os.environ:
        return os.environ["INTELLIFLOW_DQN_WEIGHTS"]
    candidates = [
        os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "app", "api", "dqn_weights.json"
        )),
        os.path.normpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "dqn_weights.json"
        )),
        os.path.abspath(os.path.join("app", "api", "dqn_weights.json")),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # Return the most canonical path even if missing — error will be explicit
    return candidates[0]


class DQNPolicy:
    """Loads trained DQN weights and acts greedily from Q-values."""
    def __init__(self, weights_path: str = None):
        weights_path = _resolve_dqn_weights_path(weights_path)
        self._fallback = PressurePolicy()
        self._q_weights = None
        self._weights_path = weights_path
        self._dqn_count = 0
        self._fallback_count = 0
        self._inference_latencies: List[float] = []
        try:
            with open(weights_path, "r") as f:
                data = json.load(f)
            self._q_weights = data
            print(f"[DQNPolicy] Loaded weights from {weights_path}")
        except FileNotFoundError:
            print(f"[DQNPolicy] Weights not found at {weights_path} — falling back to pressure policy")
            print(f"[DQNPolicy] Set INTELLIFLOW_DQN_WEIGHTS env var to override path")
        except Exception as e:
            print(f"[DQNPolicy] Could not load weights ({e}) — falling back to pressure policy")

    def act(self, obs: dict) -> int:
        if self._q_weights is None:
            self._fallback_count += 1
            return self._fallback.act(obs)
        try:
            vec = obs.get("observation_vector", None)
            if vec is None:
                self._fallback_count += 1
                print("[DQNPolicy] WARNING: observation_vector missing — using fallback", flush=True)
                return self._fallback.act(obs)

            x = np.array(vec, dtype=np.float32)

            # Validate input shape against first layer
            layers = self._q_weights.get("layers", [])
            if layers:
                expected_in = np.array(layers[0]["W"], dtype=np.float32).shape[1]
                if x.shape[0] != expected_in:
                    self._fallback_count += 1
                    print(f"[DQNPolicy] WARNING: input dim {x.shape[0]} != expected {expected_in} — using fallback", flush=True)
                    return self._fallback.act(obs)

            t0 = time.time()
            for layer in layers:
                W = np.array(layer["W"], dtype=np.float32)
                b = np.array(layer["b"], dtype=np.float32)
                x = np.dot(x, W.T) + b
                if layer.get("activation") == "relu":
                    x = np.maximum(0, x)
            latency_ms = (time.time() - t0) * 1000
            self._inference_latencies.append(latency_ms)
            self._dqn_count += 1

            action = int(np.argmax(x))
            q_spread = float(np.max(x) - np.min(x))
            if q_spread < 0.01:
                print(f"[DQNPolicy] WARNING: Q-values nearly uniform (spread={q_spread:.4f}), confidence low", flush=True)
            return action

        except Exception as e:
            self._fallback_count += 1
            print(f"[DQNPolicy] ERROR in forward pass: {e} — using fallback", flush=True)
            return self._fallback.act(obs)

    def stats(self) -> dict:
        total = self._dqn_count + self._fallback_count
        avg_lat = (
            sum(self._inference_latencies) / len(self._inference_latencies)
            if self._inference_latencies else 0.0
        )
        return {
            "dqn_calls":        self._dqn_count,
            "fallback_calls":   self._fallback_count,
            "dqn_usage_pct":    round(self._dqn_count / max(total, 1) * 100, 1),
            "avg_latency_ms":   round(avg_lat, 3),
            "weights_path":     self._weights_path,
        }

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = os.environ.get("INTELLIFLOW_HOST", "http://localhost:7860")
MODEL_NAME   = os.environ.get("MODEL_NAME", "gpt-4o-mini")

TASKS = [
    "task_suburban_steady",
    "task_urban_stochastic",
    "task_rush_hour_crisis",
]


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

class IntelliFlowClient:
    def __init__(self, host: str):
        self.host = host.rstrip("/")
        self.session = requests.Session()

    def health(self) -> Dict:
        return self.session.get(f"{self.host}/health", timeout=10).json()

    def reset(self, task_id: str, seed: Optional[int] = None) -> Dict:
        body: Dict[str, Any] = {"task_id": task_id}
        if seed is not None:
            body["seed"] = seed
        r = self.session.post(f"{self.host}/reset", json=body, timeout=10)
        r.raise_for_status()
        return r.json()

    def step(self, session_id: str, action: int) -> Dict:
        r = self.session.post(
            f"{self.host}/step",
            json={"session_id": session_id, "action": action},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def grade(self, session_id: str) -> Dict:
        r = self.session.post(
            f"{self.host}/grader",
            json={"session_id": session_id},
            timeout=10,
        )
        r.raise_for_status()
        return r.json()

    def get_tasks(self) -> Dict:
        return self.session.get(f"{self.host}/tasks", timeout=10).json()


# ---------------------------------------------------------------------------
# Episode runner
# ---------------------------------------------------------------------------

def run_episode(
    client: IntelliFlowClient,
    task_id: str,
    policy_name: str,
    seed: int,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run one complete episode, return scored result."""

    reset_data = client.reset(task_id, seed=seed)
    session_id = reset_data["session_id"]
    horizon = reset_data.get("horizon", 600)

    if policy_name == "pressure":
        policy = PressurePolicy()
    elif policy_name == "fixed_cycle":
        policy = FixedCyclePolicy()
    elif policy_name == "random":
        policy = RandomPolicy(seed=seed)
    elif policy_name == "llm":
        policy = LLMPolicy()
    elif policy_name == "dqn":
        policy = DQNPolicy()
    else:
        raise ValueError(f"Unknown policy: {policy_name}")

    total_reward = 0.0
    step_count = 0
    done = False
    obs = reset_data.get("observation", {})
    rewards: List[float] = []
    t_start = time.time()

    print(f"[START] task={task_id} env=intelliflow model={MODEL_NAME or policy_name}", flush=True)

    while not done:
        action = policy.act(obs)
        step_data = client.step(session_id, action)

        obs = step_data.get("observation", {})
        reward = step_data.get("reward", 0.0)
        done = step_data.get("done", False)
        info = step_data.get("info", {})

        total_reward += reward
        rewards.append(reward)
        step_count += 1

        print(f"[STEP] step={step_count} action={json.dumps(action)} reward={reward:.2f} done={str(done).lower()} error=null", flush=True)

        if verbose and step_count % 100 == 0:
            print(f"  Step {step_count:4d}/{horizon} | "
                  f"Reward: {reward:+7.3f} | "
                  f"Cleared: {info.get('total_cleared', 0):5d} | "
                  f"Phase: {info.get('phase', '?'):<10s} | "
                  f"Delay: {info.get('avg_delay', 0):.1f}s")

    elapsed = time.time() - t_start
    grade_data = client.grade(session_id)

    # Emit reward curve for training loop visibility
    window = 50
    smoothed = []
    for i in range(len(rewards)):
        w = rewards[max(0, i - window): i + 1]
        smoothed.append(round(sum(w) / len(w), 4))
    print(f"[REWARD_CURVE] {json.dumps(smoothed)}", flush=True)
    print(f"[END] success=true steps={step_count} score={grade_data.get('score', 0.0):.3f} rewards={','.join(f'{r:.3f}' for r in rewards)}", flush=True)

    log_path = "inference_reward_log.jsonl"
    with open(log_path, "a") as logf:
        logf.write(json.dumps({
            "task_id":    task_id,
            "policy":     policy_name,
            "seed":       seed,
            "score":      grade_data.get("score", 0.0),
            "steps":      step_count,
            "reward_mean": round(sum(rewards)/max(len(rewards),1), 4),
        }) + "\n")

    n = max(len(rewards), 1)
    mean_r = sum(rewards) / n
    std_r = (sum((r - mean_r) ** 2 for r in rewards) / n) ** 0.5 if rewards else 0.0

    result: Dict[str, Any] = {
        "task_id": task_id,
        "policy": policy_name,
        "seed": seed,
        "steps": step_count,
        "total_reward": round(total_reward, 4),
        "reward_mean": round(mean_r, 4),
        "reward_std": round(std_r, 4),
        "score": grade_data.get("score", 0.0),
        "sub_scores": grade_data.get("sub_scores", {}),
        "trajectory_summary": grade_data.get("trajectory_summary", {}),
        "wall_time_seconds": round(elapsed, 2),
    }

    if policy_name == "llm" and hasattr(policy, "calls"):
        result["llm_calls"] = policy.calls
        result["llm_avg_latency_ms"] = round(
            sum(policy.latencies) / max(len(policy.latencies), 1) * 1000, 1
        )
    if policy_name == "dqn" and hasattr(policy, "stats"):
        result["dqn_stats"] = policy.stats()
        print(f"  │ DQN usage   : {result['dqn_stats']['dqn_usage_pct']}%")
        print(f"  │ DQN latency : {result['dqn_stats']['avg_latency_ms']}ms avg")
        print(f"  │ Fallbacks   : {result['dqn_stats']['fallback_calls']}")

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IntelliFlow baseline inference script")
    parser.add_argument("--task", default="all", help="Task ID or 'all' (default: all)")
    parser.add_argument("--policy", default="dqn",
                        choices=["pressure", "fixed_cycle", "random", "llm", "dqn"])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--output", default=None, help="JSON output file path")
    args = parser.parse_args()

    client = IntelliFlowClient(args.host)

    print(f"\n{'='*60}")
    print("  IntelliFlow Baseline Inference")
    print(f"{'='*60}")
    print(f"  Host   : {args.host}")
    print(f"  Policy : {args.policy}")
    print(f"  Seed   : {args.seed}")
    print()

    try:
        health = client.health()
        print(f"  ✓ Service online | Uptime: {health.get('uptime_seconds', 0)}s")
        print(f"  ✓ Tasks: {', '.join(health.get('tasks_available', []))}")
    except Exception as e:
        print(f"  ✗ Health check failed: {e}")
        print("  Make sure the server is running: python -m uvicorn app.api.main:app --port 7860")
        sys.exit(1)

    tasks = TASKS if args.task == "all" else [args.task]
    all_results: List[Dict[str, Any]] = []

    for task_id in tasks:
        print(f"\n{'─'*60}")
        print(f"  Task: {task_id}")
        print(f"{'─'*60}")

        try:
            result = run_episode(client, task_id, args.policy, args.seed, args.verbose)
            all_results.append(result)

            score = result["score"]
            bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
            print("\n  ┌─ RESULT ─────────────────────────────")
            print(f"  │ Score       : {score:.4f}  [{bar}]")
            print(f"  │ Steps       : {result['steps']}")
            print(f"  │ Total reward: {result['total_reward']}")
            print(f"  │ Reward mean : {result['reward_mean']}")
            for k, v in result.get("sub_scores", {}).items():
                print(f"  │  └ {k:<30s}: {v:.4f}")
            traj = result.get("trajectory_summary", {})
            print(f"  │ Cleared     : {traj.get('total_cleared', '?')}")
            print(f"  │ Avg delay   : {traj.get('avg_delay_seconds', '?')}s")
            print(f"  │ Wall time   : {result['wall_time_seconds']}s")
            if "llm_calls" in result:
                print(f"  │ LLM calls   : {result['llm_calls']}")
                print(f"  │ LLM latency : {result['llm_avg_latency_ms']}ms avg")
            if "dqn_stats" in result:
                s = result["dqn_stats"]
                print(f"  │ DQN usage   : {s['dqn_usage_pct']}% ({s['dqn_calls']} calls)")
                print(f"  │ DQN latency : {s['avg_latency_ms']}ms avg")
                print(f"  │ Fallbacks   : {s['fallback_calls']}")
            print("  └──────────────────────────────────────")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback; traceback.print_exc()

    if len(all_results) > 1:
        print(f"\n{'='*60}")
        print("  SUMMARY")
        print(f"{'='*60}")
        print(f"  {'Task':<35s} {'Score':>8s}")
        print(f"  {'─'*35} {'─'*8}")
        for r in all_results:
            print(f"  {r['task_id']:<35s} {r['score']:>8.4f}")
        scores = [r["score"] for r in all_results]
        print(f"  {'─'*35} {'─'*8}")
        print(f"  {'Average':<35s} {sum(scores)/len(scores):>8.4f}")
        print()

    if args.output:
        with open(args.output, "w") as f:
            json.dump({"results": all_results, "policy": args.policy, "seed": args.seed}, f, indent=2)
        print(f"  Results written to: {args.output}")
    else:
        print("\n  Full JSON results:")
        print(json.dumps({"results": all_results}, indent=2))


if __name__ == "__main__":
    main()