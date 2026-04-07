"""
IntelliFlow FastAPI Application
OpenEnv-compliant REST API for Urban Traffic Control Environment.
"""

from __future__ import annotations

import json
from fastapi import Request
from fastapi.responses import JSONResponse
import os
import time
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.core.session import store
from app.tasks.registry import TASK_REGISTRY, get_task_spec_dict

WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "dqn_weights.json")


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="IntelliFlow Urban Traffic Control",
    description=(
        "A production-grade reinforcement learning simulation environment "
        "for intelligent urban traffic signal optimisation. "
        "Implements the OpenEnv specification with 3 progressive tasks."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

WEIGHTS_FILE = os.path.join(os.path.dirname(__file__), "dqn_weights.json")



app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

_start_time = time.time()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ResetRequest(BaseModel):
    task_id: str = Field(
        default="task_suburban_steady",
        description="Task identifier. One of: task_suburban_steady, task_urban_stochastic, task_rush_hour_crisis"
    )
    seed: Optional[int] = Field(
        default=None,
        description="Random seed for reproducibility. If None, a random seed is used."
    )

class StepRequest(BaseModel):
    session_id: str = Field(description="Session ID returned by /reset")
    action: int = Field(description="Action integer: 0=MAINTAIN, 1=SWITCH_PHASE, 2=EXTEND_GREEN, 3=FORCE_ALL_RED, 4=YIELD_MINOR")

class GraderRequest(BaseModel):
    session_id: str = Field(description="Session ID to grade")

class BaselineRequest(BaseModel):
    task_id: str = Field(
        default="task_suburban_steady",
        description="Task to evaluate baseline on"
    )
    policy: str = Field(
        default="pressure",
        description="Baseline policy: 'pressure' (Webster/pressure heuristic), 'fixed_cycle', 'random'"
    )
    seed: int = Field(default=42, description="Seed for reproducibility")
    use_llm: bool = Field(
        default=False,
        description="If True, uses OpenAI API for action selection (requires OPENAI_API_KEY)"
    )


# ---------------------------------------------------------------------------
# Health & Info
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse, tags=["Info"])
async def root():
    """Landing page with API overview."""
    uptime = int(time.time() - _start_time)
    return f"""
    <html>
    <head>
        <title>IntelliFlow Traffic Control</title>
        <style>
            body {{ font-family: 'Courier New', monospace; background: #0a0e1a; color: #00ff88;
                   padding: 40px; max-width: 900px; margin: 0 auto; }}
            h1 {{ color: #00d4ff; font-size: 2em; border-bottom: 1px solid #00ff88; }}
            h2 {{ color: #ffaa00; }}
            code {{ background: #1a2030; padding: 2px 8px; border-radius: 3px; color: #ff6688; }}
            .endpoint {{ background: #0d1525; border-left: 3px solid #00ff88;
                         padding: 10px 15px; margin: 8px 0; border-radius: 0 5px 5px 0; }}
            .tag {{ color: #888; font-size: 0.85em; }}
            a {{ color: #00d4ff; }}
        </style>
    </head>
    <body>
        <h1>🚦 IntelliFlow Urban Traffic Control</h1>
        <p>OpenEnv-compliant RL environment for intelligent traffic signal optimisation.</p>
        <p class="tag">Uptime: {uptime}s | Version: 1.0.0 | Tasks: {len(TASK_REGISTRY)}</p>

        <h2>Quick Start</h2>
        <div class="endpoint">POST <code>/reset</code> — Create new episode session</div>
        <div class="endpoint">POST <code>/step</code> — Apply action, advance simulation</div>
        <div class="endpoint">GET <code>/state?session_id=...</code> — Current observation + rich metrics</div>
        <div class="endpoint">GET <code>/tasks</code> — List all tasks + action schemas</div>
        <div class="endpoint">POST <code>/grader</code> — Score current/completed episode (0.0–1.0)</div>
        <div class="endpoint">GET <code>/analytics?session_id=...</code> — Phase stats, LOS, time-series, emissions</div>
        <div class="endpoint">POST <code>/baseline</code> — Run baseline policy evaluation</div>
        <div class="endpoint">POST <code>/benchmark?task_id=...&seeds=42,43,44</code> — Multi-seed reproducibility stats</div>
        <div class="endpoint">GET <code>/health</code> — Service health check</div>
        <div class="endpoint">GET <code>/docs</code> — Full OpenAPI documentation</div>
        <div class="endpoint">GET <code>/viz</code> — Live visualisation dashboard</div>

        <h2>Tasks</h2>
        {"".join(f'<div class="endpoint"><b>{t.task_id}</b> [{t.difficulty.upper()}] — {t.name}</div>' for t in TASK_REGISTRY.values())}

        <p>Full API docs: <a href="/docs">/docs</a> | <a href="/redoc">/redoc</a></p>
    </body>
    </html>
    """


@app.get("/health", tags=["Info"])
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "uptime_seconds": round(time.time() - _start_time),
        "active_sessions": len(store._sessions),
        "tasks_available": list(TASK_REGISTRY.keys()),
        "version": "1.0.0",
    }


# ---------------------------------------------------------------------------
# Core OpenEnv endpoints
# ---------------------------------------------------------------------------

@app.post("/reset", tags=["OpenEnv"])
async def reset(req: ResetRequest):
    """
    Initialize a new episode session.
    Returns session_id, initial observation, and task metadata.
    """
    try:
        session = store.create(req.task_id, seed=req.seed)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    obs = session.env._build_observation()
    spec = TASK_REGISTRY[req.task_id]

    return {
        "session_id": session.session_id,
        "task_id": req.task_id,
        "seed": req.seed,
        "observation": obs.to_dict(),
        "observation_vector": obs.to_vector().tolist(),
        "action_space": {
            "type": "Discrete",
            "n": spec.n_actions,
            "actions": {str(i): d for i, d in spec.action_descriptions.items()},
        },
        "horizon": spec.horizon,
        "obs_dim": spec.obs_dim,
    }


@app.post("/step", tags=["OpenEnv"])
async def step(req: StepRequest):
    """
    Apply action to environment, advance simulation by one step.
    Returns next observation, reward, done flag, and info dict.
    """
    try:
        session = store.get(req.session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    try:
        obs, reward, done, info = session.step(req.action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except AssertionError as e:
        raise HTTPException(status_code=422, detail=f"Invalid action: {e}")

    return {
        "session_id": req.session_id,
        "observation": obs.to_dict(),
        "observation_vector": obs.to_vector().tolist(),
        "reward": reward,
        "done": done,
        "info": info,
        "step": session.step_count,
    }


@app.get("/state", tags=["OpenEnv"])
async def state(session_id: str):
    """
    Return full current environment state including lane details,
    metrics, and structured observation.
    """
    try:
        session = store.get(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    state_dict = session.env.state()
    obs = session.env._build_observation()
    state_dict["observation_vector"] = obs.to_vector().tolist()
    state_dict["session_id"] = session_id
    state_dict["done"] = session.done
    return state_dict


# ---------------------------------------------------------------------------
# Task registry
# ---------------------------------------------------------------------------

@app.get("/tasks", tags=["Tasks"])
async def list_tasks():
    """List all available tasks with full specifications and action schemas."""
    return {
        "tasks": [get_task_spec_dict(tid) for tid in TASK_REGISTRY],
        "count": len(TASK_REGISTRY),
    }


@app.get("/tasks/{task_id}", tags=["Tasks"])
async def get_task(task_id: str):
    """Get specification for a specific task."""
    if task_id not in TASK_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Task {task_id!r} not found. Available: {list(TASK_REGISTRY.keys())}"
        )
    return get_task_spec_dict(task_id)


# ---------------------------------------------------------------------------
# Grader
# ---------------------------------------------------------------------------

@app.post("/grader", tags=["Evaluation"])
async def grader(req: GraderRequest):
    """
    Compute episode score for a session.
    Can be called mid-episode or after completion.
    Returns score in [0.0, 1.0] with sub-score breakdown.
    """
    try:
        session = store.get(req.session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return session.grade()


# ---------------------------------------------------------------------------
# Baseline evaluation
# ---------------------------------------------------------------------------

@app.post("/baseline", tags=["Evaluation"])
async def baseline(req: BaselineRequest):
    """
    Run a complete episode with a baseline policy and return score.
    Policies: 'pressure' (Webster heuristic), 'fixed_cycle', 'random'.
    Optionally uses OpenAI API if use_llm=True.
    """
    from app.baseline.policies import run_baseline_episode

    try:
        result = await run_baseline_episode(
            task_id=req.task_id,
            policy=req.policy,
            seed=req.seed,
            use_llm=req.use_llm,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Baseline error: {e}")

    return result


# ---------------------------------------------------------------------------
# Visualisation
# ---------------------------------------------------------------------------

@app.get("/viz", response_class=HTMLResponse, tags=["Visualisation"])
async def visualisation():
    """Live traffic simulation visualisation dashboard."""
    from app.viz.dashboard import render_dashboard
    return render_dashboard()


@app.get("/viz/snapshot", tags=["Visualisation"])
async def viz_snapshot(session_id: str):
    """Get visualisation-ready data snapshot for a session."""
    try:
        session = store.get(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    state_dict = session.env.state()
    lanes = state_dict.get("lanes", [])

    return {
        "session_id": session_id,
        "step": session.step_count,
        "done": session.done,
        "phase": state_dict.get("phase"),
        "phase_elapsed": state_dict.get("phase_elapsed"),
        "lanes": [
            {
                "name": l["name"],
                "queue": l["queue"],
                "capacity": l["capacity"],
                "utilisation": round(l["queue"] / max(l["capacity"], 1), 3),
                "spillback": l["spillback"],
                "cleared": l["total_cleared"],
                "arrived": l["total_arrived"],
            }
            for l in lanes
        ],
        "metrics": state_dict.get("metrics", {}),
    }


# ---------------------------------------------------------------------------
# Analytics & Benchmark
# ---------------------------------------------------------------------------

@app.get("/analytics", tags=["Evaluation"])
async def analytics(session_id: str):
    """
    Rich episode analytics: phase statistics, LOS breakdown, time-series histories,
    emission estimates, green split, efficiency vs theoretical maximum.
    Use this for post-hoc analysis, visualisation, and judge review.
    """
    try:
        session = store.get(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return session.env.analytics()


@app.post("/benchmark", tags=["Evaluation"])
async def benchmark(task_id: str = "task_suburban_steady", seeds: str = "42,43,44"):
    """
    Run the pressure baseline across multiple seeds and return
    mean ± std score — demonstrates reproducibility and score variance.
    """
    from app.baseline.policies import run_baseline_episode

    if task_id not in TASK_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_id}")

    seed_list = [int(s.strip()) for s in seeds.split(",") if s.strip().isdigit()]
    if not seed_list or len(seed_list) > 10:
        raise HTTPException(status_code=400, detail="Provide 1–10 comma-separated seeds")

    results = []
    for seed in seed_list:
        r = await run_baseline_episode(task_id=task_id, policy="pressure", seed=seed)
        results.append(r)

    scores = [r["grade"]["score"] for r in results]
    mean_s = sum(scores) / len(scores)
    variance = sum((s - mean_s) ** 2 for s in scores) / max(len(scores), 1)
    std_s = variance ** 0.5

    return {
        "task_id": task_id,
        "policy": "pressure",
        "seeds": seed_list,
        "scores": [round(s, 4) for s in scores],
        "mean_score": round(mean_s, 4),
        "std_score":  round(std_s, 4),
        "min_score":  round(min(scores), 4),
        "max_score":  round(max(scores), 4),
        "reproducibility_note": (
            "Score variance across seeds reflects genuine stochastic task difficulty, "
            "not implementation instability. Higher std on harder tasks is expected."
        ),
        "per_seed_details": [
            {
                "seed": seed_list[i],
                "score": round(scores[i], 4),
                "metrics": results[i]["metrics"],
            }
            for i in range(len(seed_list))
        ],
    }


# ---------------------------------------------------------------------------
# Sessions management
# ---------------------------------------------------------------------------

@app.get("/sessions", tags=["Admin"])
async def list_sessions():
    """List all active sessions."""
    return {"sessions": store.list_sessions()}


# ---------------------------------------------------------------------------
# DQN Weight Persistence
# ---------------------------------------------------------------------------

@app.post("/save_weights", tags=["Admin"])
async def save_weights(request: Request):
    """Save DQN weights to disk — called automatically by the dashboard JS."""
    try:
        data = await request.json()
        with open(WEIGHTS_FILE, "w") as f:
            json.dump(data, f)
        return JSONResponse({"ok": True})
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/load_weights", tags=["Admin"])
async def load_weights():
    """Load DQN weights from disk — called on dashboard startup."""
    try:
        if not os.path.exists(WEIGHTS_FILE):
            return JSONResponse({"found": False})
        with open(WEIGHTS_FILE, "r") as f:
            data = json.load(f)
        return JSONResponse({"found": True, "data": data})
    except Exception as e:
        return JSONResponse({"found": False, "error": str(e)}, status_code=500)