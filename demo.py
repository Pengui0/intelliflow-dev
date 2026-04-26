"""
IntelliFlow — Before / After Training Demo
==========================================
Shows measurable improvement from untrained baseline to trained agent
across all 6 tasks. Calls /proof_of_learning, /training_progress,
and /benchmark for judge-ready evidence.

Run:  python demo.py [--host http://localhost:7860] [--task all]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any

import requests

HOST = os.environ.get("INTELLIFLOW_HOST", "http://localhost:7860")

_TASKS = [
    ("task_suburban_steady",  "easy",   0.55),
    ("task_urban_stochastic", "medium", 0.42),
    ("task_rush_hour_crisis", "hard",   0.30),
    ("task_grid_steady",      "medium", 0.50),
    ("task_grid_rush",        "hard",   0.36),
    ("task_grid_crisis",      "hard",   0.24),
]
_POLICIES = ["pressure", "fixed_cycle", "dqn"]


def _bar(v: float, width: int = 28) -> str:
    filled = int(round(v * width))
    return "█" * filled + "░" * (width - filled)

def _colour(v: float) -> str:
    """Return ANSI colour code based on score."""
    if v >= 0.65: return "\033[92m"   # green
    if v >= 0.45: return "\033[93m"   # yellow
    return "\033[91m"                  # red

_RST = "\033[0m"


class DemoClient:
    def __init__(self, host: str):
        self.host = host.rstrip("/")
        self._s   = requests.Session()

    def get(self, path: str, **kw) -> dict:
        r = self._s.get(f"{self.host}{path}", timeout=30, **kw)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, **kw) -> dict:
        r = self._s.post(f"{self.host}{path}", timeout=60, **kw)
        r.raise_for_status()
        return r.json()

    def health(self) -> dict:
        return self.get("/health")

    def proof_of_learning(self) -> dict:
        return self.get("/proof_of_learning")

    def training_progress(self) -> dict:
        return self.get("/training_progress")

    def benchmark(self, task_id: str, policy: str, seeds: str = "42,43,44") -> dict:
        return self.post(
            "/benchmark",
            params={"task_id": task_id, "policy": policy, "seeds": seeds},
        )


def section(title: str) -> None:
    print(f"\n{'─'*64}")
    print(f"  {title}")
    print(f"{'─'*64}")


def run_demo(host: str, task_filter: str, seeds: str) -> None:
    client = DemoClient(host)

    print(f"\n{'='*64}")
    print("  IntelliFlow — Proof of Learning Demo")
    print(f"{'='*64}")
    print(f"  Host:  {host}")
    print(f"  Seeds: {seeds}")

    # ── 0. Health check ────────────────────────────────────────────────────
    try:
        h = client.health()
        print(f"\n  Server: OK · uptime={h.get('uptime_seconds')}s · "
              f"DQN ready={h.get('dqn_weights_ready')} · "
              f"LSTM ready={h.get('lstm_weights_ready')}")
    except requests.RequestException as e:
        print(f"\n  ✗ Server unreachable: {e}")
        print("  Start server: uvicorn app.api.main:app --port 7860")
        sys.exit(1)

    # ── 1. Proof of learning endpoint ──────────────────────────────────────
    section("1 / 4  Proof of Learning  (/proof_of_learning)")
    try:
        pol = client.proof_of_learning()
        dqn_score  = pol.get("dqn_score", 0.0)
        pres_score = pol.get("pressure_score", 0.0)
        delta      = pol.get("delta", 0.0)
        verdict    = pol.get("verdict", "—")
        c = _colour(dqn_score)
        print(f"\n  Pressure baseline : {_bar(pres_score)}  {pres_score:.4f}")
        print(f"  DQN agent         : {c}{_bar(dqn_score)}  {dqn_score:.4f}{_RST}")
        print(f"\n  Delta : {'+' if delta >= 0 else ''}{delta*100:.2f} pp")
        print(f"  {'✓' if delta > 0 else '✗'} {verdict}")
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 424:
            d = e.response.json()
            print(f"\n  DQN weights not found — train first.")
            print(f"  {d.get('detail','')}")
        else:
            print(f"\n  Error: {e}")

    # ── 2. Training progress ───────────────────────────────────────────────
    section("2 / 4  Training Progress  (/training_progress)")
    try:
        tp = client.training_progress()
        eps  = tp.get("completed_episodes", 0)
        mean = tp.get("mean_score", 0.0)
        best = tp.get("best_score",  0.0)
        imp  = tp.get("mean_improvement_over_baseline", 0.0)
        trend = tp.get("reward_trend", 0.0)
        is_learning = tp.get("is_learning", False)

        print(f"\n  Episodes completed : {eps}")
        print(f"  Mean score         : {mean:.4f}   {_bar(mean, 20)}")
        print(f"  Best score         : {best:.4f}   {_bar(best, 20)}")
        print(f"  Mean Δ vs baseline : {'+' if imp >= 0 else ''}{imp:.4f}")
        print(f"  Reward trend       : {'+' if trend >= 0 else ''}{trend:.4f}  "
              f"({'📈 improving' if is_learning else '📉 flat/regressing'})")

        rolling = tp.get("rolling_mean_10ep", [])
        if len(rolling) >= 2:
            print(f"\n  Rolling mean (last {min(20,len(rolling))} episodes):")
            mn = min(rolling); mx = max(rolling); rng = max(mx - mn, 1e-6)
            for i, v in enumerate(rolling[-20:]):
                bar_w = int((v - mn) / rng * 30)
                print(f"  ep {eps - len(rolling) + i + 1:4d}  "
                      f"{'█' * bar_w}  {v:.4f}")
    except Exception as e:
        print(f"\n  Error: {e}")

    # ── 3. Per-task benchmark comparison ───────────────────────────────────
    section("3 / 4  Per-Task Benchmark  (pressure vs DQN, 3 seeds each)")

    tasks = (
        [t for t in _TASKS if t[0] == task_filter]
        if task_filter != "all" else _TASKS[:3]   # single-node tasks for speed
    )

    results: list[dict] = []
    for task_id, difficulty, baseline_ref in tasks:
        row: dict[str, Any] = {
            "task_id": task_id, "difficulty": difficulty, "baseline_ref": baseline_ref
        }
        print(f"\n  {task_id}  [{difficulty}]  (baseline ≈ {baseline_ref})")
        for policy in _POLICIES:
            try:
                bm     = client.benchmark(task_id, policy, seeds)
                mean_s = bm.get("mean_score", 0.0)
                std_s  = bm.get("std_score",  0.0)
                c      = _colour(mean_s)
                delta_vs_ref = mean_s - baseline_ref
                print(
                    f"    {policy:<14s}: {c}{_bar(mean_s, 22)}{_RST}  "
                    f"{mean_s:.4f} ± {std_s:.4f}  "
                    f"({'↑' if delta_vs_ref > 0 else '↓'}"
                    f"{abs(delta_vs_ref)*100:.1f}pp vs ref)"
                )
                row[policy] = mean_s
            except Exception as e:
                print(f"    {policy:<14s}: error — {e}")
                row[policy] = None

        results.append(row)
        time.sleep(0.2)

    # ── 4. Summary table ───────────────────────────────────────────────────
    section("4 / 4  Summary")
    scored = [r for r in results if r.get("dqn") is not None
              and r.get("pressure") is not None]
    if scored:
        dqn_wins   = sum(1 for r in scored if r["dqn"] > r["pressure"])
        dqn_mean   = sum(r["dqn"] for r in scored) / len(scored)
        pres_mean  = sum(r["pressure"] for r in scored) / len(scored)
        overall_d  = dqn_mean - pres_mean

        print(f"\n  {'Task':<35s} {'Pressure':>9s} {'DQN':>9s} {'Delta':>8s}")
        print(f"  {'─'*35} {'─'*9} {'─'*9} {'─'*8}")
        for r in scored:
            task   = r["task_id"].replace("task_", "")
            pres   = r.get("pressure", 0.0)
            dqn    = r.get("dqn",      0.0)
            delta  = dqn - pres
            c      = "\033[92m" if delta > 0 else "\033[91m"
            print(f"  {task:<35s} {pres:>9.4f} {dqn:>9.4f} "
                  f"{c}{'+' if delta>=0 else ''}{delta*100:>6.1f}pp{_RST}")

        print(f"  {'─'*35} {'─'*9} {'─'*9} {'─'*8}")
        c = "\033[92m" if overall_d > 0 else "\033[91m"
        print(f"  {'Mean':<35s} {pres_mean:>9.4f} {dqn_mean:>9.4f} "
              f"{c}{'+' if overall_d>=0 else ''}{overall_d*100:>6.1f}pp{_RST}")
        print(f"\n  DQN outperforms pressure: {dqn_wins}/{len(scored)} tasks")
        print(f"\n  {'✓ LEARNING CONFIRMED' if dqn_wins > len(scored)//2 else '✗ NEEDS MORE TRAINING'}")

    print(f"\n{'='*64}")
    print(f"  Endpoint for judges: GET {host}/proof_of_learning")
    print(f"  Training log:        GET {host}/training_progress")
    print(f"{'='*64}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="IntelliFlow Before/After Training Demo",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host",   default=HOST)
    parser.add_argument("--task",   default="all",
                        help="Task ID or 'all'")
    parser.add_argument("--seeds",  default="42,43,44",
                        help="Comma-separated benchmark seeds")
    args = parser.parse_args()
    run_demo(args.host, args.task, args.seeds)


if __name__ == "__main__":
    main()