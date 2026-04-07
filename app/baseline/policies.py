#!/usr/bin/env python3
"""
IntelliFlow Baseline Inference Script
=====================================
Runs the OpenAI-powered LLM agent (and pressure/fixed-cycle baselines)
across all three tasks and outputs reproducible baseline scores.

Usage:
    python baseline_inference.py [--task all|<task_id>] [--policy pressure|fixed_cycle|random|llm]
                                  [--seed 42] [--host http://localhost:7860]

Requirements:
    pip install openai requests

Environment variables:
    OPENAI_API_KEY  — required for --policy llm
    INTELLIFLOW_HOST — optional override for API host
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import random
import math
from typing import Any, Dict, List, Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' package not found. Install with: pip install requests")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_HOST = os.environ.get("INTELLIFLOW_HOST", "http://localhost:7860")

TASKS = [
    "task_suburban_steady",
    "task_urban_stochastic",
    "task_rush_hour_crisis",
]

LANE_NAMES = [
    "N_through", "N_right", "S_through", "S_right",
    "E_through", "E_right", "W_through", "W_right",
    "N_left",    "S_left",  "E_left",    "W_left",
]


# ---------------------------------------------------------------------------
# Inline policies (no server dependency for action selection)
# ---------------------------------------------------------------------------

class PressurePolicy:
    def __init__(self, switch_threshold: float = 3.0, min_steps: int = 5):
        self.threshold = switch_threshold
        self.min_steps = min_steps
        self._steps = 0

    def act(self, obs: Dict) -> int:
        self._steps += 1
        ql = obs.get("queue_lengths", [0.0]*12)
        phase_oh = obs.get("phase_onehot", [1,0,0,0])
        idx = phase_oh.index(max(phase_oh))
        elapsed_norm = obs.get("phase_elapsed_norm", 0)
        elapsed = elapsed_norm * 90

        if elapsed < self.min_steps:
            return 0  # MAINTAIN

        ns = sum(ql[i] for i in [0,1,2,3,8,9])
        ew = sum(ql[i] for i in [4,5,6,7,10,11])

        if idx == 2:  # ALL_RED
            return 0
        if idx == 0 and ew - ns > self.threshold * 0.1:
            self._steps = 0
            return 1
        if idx == 1 and ns - ew > self.threshold * 0.1:
            self._steps = 0
            return 1
        # Extend if high pressure on current
        if idx == 0 and ns > 0.75:
            return 2
        if idx == 1 and ew > 0.75:
            return 2
        return 0


class FixedCyclePolicy:
    def __init__(self, ns_green: int = 30, ew_green: int = 30):
        self.ns_green = ns_green
        self.ew_green = ew_green
        self._step = 0

    def act(self, obs: Dict) -> int:
        self._step += 1
        cycle = self.ns_green + 3 + self.ew_green + 3
        pos = self._step % cycle
        if pos == self.ns_green: return 3       # FORCE_ALL_RED
        if pos == self.ns_green + 3: return 1   # SWITCH
        if pos == self.ns_green + 3 + self.ew_green: return 3
        if pos == 0: return 1
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

    def __init__(self, model: str = "gpt-4o-mini"):
        self.model = model
        self._fallback = PressurePolicy()
        self.calls = 0
        self.latencies: List[float] = []

        try:
            import openai
            self._client = openai.OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY", "")
            )
            self._available = True
        except ImportError:
            print("WARNING: openai package not installed. Falling back to pressure policy.")
            self._available = False

    def act(self, obs: Dict) -> int:
        if not self._available or not os.environ.get("OPENAI_API_KEY"):
            return self._fallback.act(obs)

        try:
            ql = obs.get("queue_lengths", [])
            phase_oh = obs.get("phase_onehot", [1,0,0,0])
            phase_names = ["NS_GREEN","EW_GREEN","ALL_RED","NS_MINOR"]
            phase = phase_names[phase_oh.index(max(phase_oh))]
            queue_map = {LANE_NAMES[i]: round(ql[i], 2) for i in range(min(len(ql),12))}

            msg = (
                f"Phase: {phase} | "
                f"Elapsed(norm): {obs.get('phase_elapsed_norm',0):.2f} | "
                f"Queues: {json.dumps(queue_map)} | "
                f"Pressure NS-EW: {obs.get('pressure_differential',0):.3f} | "
                f"Fairness: {obs.get('fairness_score',0):.3f}"
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
        except Exception as e:
            return self._fallback.act(obs)


# ---------------------------------------------------------------------------
# Episode runner (direct API calls)
# ---------------------------------------------------------------------------

class IntelliFlowClient:
    def __init__(self, host: str):
        self.host = host.rstrip("/")
        self.session = requests.Session()

    def health(self) -> Dict:
        return self.session.get(f"{self.host}/health", timeout=10).json()

    def reset(self, task_id: str, seed: Optional[int] = None) -> Dict:
        body = {"task_id": task_id}
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


def run_episode(
    client: IntelliFlowClient,
    task_id: str,
    policy_name: str,
    seed: int,
    verbose: bool = True,
) -> Dict[str, Any]:
    """Run one complete episode, return scored result."""

    # Reset
    reset_data = client.reset(task_id, seed=seed)
    session_id = reset_data["session_id"]
    horizon = reset_data.get("horizon", 600)

    # Build policy
    if policy_name == "pressure":
        policy = PressurePolicy()
    elif policy_name == "fixed_cycle":
        policy = FixedCyclePolicy()
    elif policy_name == "random":
        policy = RandomPolicy(seed=seed)
    elif policy_name == "llm":
        policy = LLMPolicy()
    else:
        raise ValueError(f"Unknown policy: {policy_name}")

    total_reward = 0.0
    step_count = 0
    done = False
    obs = reset_data.get("observation", {})
    rewards = []

    t_start = time.time()

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

        if verbose and step_count % 100 == 0:
            print(f"  Step {step_count:4d}/{horizon} | "
                  f"Reward: {reward:+7.3f} | "
                  f"Cleared: {info.get('total_cleared',0):5d} | "
                  f"Phase: {info.get('phase','?'):<10s} | "
                  f"Delay: {info.get('avg_delay',0):.1f}s")

    elapsed = time.time() - t_start

    # Grade
    grade_data = client.grade(session_id)

    result = {
        "task_id": task_id,
        "policy": policy_name,
        "seed": seed,
        "steps": step_count,
        "total_reward": round(total_reward, 4),
        "reward_mean": round(sum(rewards)/max(len(rewards),1), 4),
        "reward_std": round(
            (sum((r - sum(rewards)/len(rewards))**2 for r in rewards)/max(len(rewards),1))**0.5, 4
        ) if rewards else 0,
        "score": grade_data.get("score", 0.0),
        "sub_scores": grade_data.get("sub_scores", {}),
        "trajectory_summary": grade_data.get("trajectory_summary", {}),
        "wall_time_seconds": round(elapsed, 2),
    }

    if policy_name == "llm" and hasattr(policy, "calls"):
        result["llm_calls"] = policy.calls
        result["llm_avg_latency_ms"] = round(
            sum(policy.latencies)/max(len(policy.latencies),1)*1000, 1
        )

    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="IntelliFlow baseline inference script"
    )
    parser.add_argument(
        "--task", default="all",
        help="Task ID or 'all' (default: all)"
    )
    parser.add_argument(
        "--policy", default="pressure",
        choices=["pressure", "fixed_cycle", "random", "llm"],
        help="Policy to evaluate (default: pressure)"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument(
        "--host", default=DEFAULT_HOST,
        help=f"API host (default: {DEFAULT_HOST})"
    )
    parser.add_argument("--verbose", action="store_true", default=True)
    parser.add_argument("--output", default=None, help="JSON output file path")
    args = parser.parse_args()

    client = IntelliFlowClient(args.host)

    # Health check
    print(f"\n{'='*60}")
    print("  IntelliFlow Baseline Inference")
    print(f"{'='*60}")
    print(f"  Host   : {args.host}")
    print(f"  Policy : {args.policy}")
    print(f"  Seed   : {args.seed}")
    print()

    try:
        health = client.health()
        print(f"  ✓ Service online | Uptime: {health.get('uptime_seconds',0)}s")
        print(f"  ✓ Tasks: {', '.join(health.get('tasks_available', []))}")
    except Exception as e:
        print(f"  ✗ Health check failed: {e}")
        print("  Make sure the server is running: python -m uvicorn app.api.main:app --port 7860")
        sys.exit(1)

    tasks = TASKS if args.task == "all" else [args.task]
    all_results = []

    for task_id in tasks:
        print(f"\n{'─'*60}")
        print(f"  Task: {task_id}")
        print(f"{'─'*60}")

        try:
            result = run_episode(
                client, task_id, args.policy, args.seed, args.verbose
            )
            all_results.append(result)

            score = result["score"]
            bar = "█" * int(score * 30) + "░" * (30 - int(score * 30))
            print(f"\n  ┌─ RESULT ─────────────────────────────")
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
            print(f"  └──────────────────────────────────────")

        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback; traceback.print_exc()

    # Summary table
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

    # Output JSON
    output_path = args.output
    if output_path:
        with open(output_path, "w") as f:
            json.dump({"results": all_results, "policy": args.policy, "seed": args.seed}, f, indent=2)
        print(f"  Results written to: {output_path}")
    else:
        print("\n  Full JSON results:")
        print(json.dumps({"results": all_results}, indent=2))


if __name__ == "__main__":
    main()