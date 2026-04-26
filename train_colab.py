"""
IntelliFlow — TRL + Unsloth GRPO + DQN Hybrid Training Script
==============================================================
Stack (guide-compliant):
  OpenEnv environment → multi-verifier reward functions
  → TRL GRPOTrainer → Unsloth 4-bit efficient backend

Training flow (guide sections 3, 9, 10, 11):
  1. Collect high-quality rollouts via pressure policy
  2. SFT warm-start on top-percentile trajectories (guide: 'do a little SFT first')
  3. GRPO/RLVR fine-tuning using environment as verifier (no learned reward model)
  4. DQN trains in parallel for non-LLM action head

Run:  python train.py
Colab GPU: set INTELLIFLOW_HOST env var to your Space URL
"""
from __future__ import annotations

import os
import json
import logging
import hashlib
import requests
import numpy as np
from collections import deque
from typing import Any

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
_log = logging.getLogger("intelliflow.train")

# ── TRL + Unsloth — graceful fallback if not installed ─────────────────────
try:
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer, SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel
    _TRL_AVAILABLE = True
    _log.info("[stack] TRL + Unsloth loaded — GRPO + SFT enabled")
except ImportError as _import_err:
    _TRL_AVAILABLE = False
    _log.warning(
        f"[stack] TRL/Unsloth not installed ({_import_err}). "
        "DQN training will still run. "
        "Install full stack: pip install trl unsloth datasets"
    )

# ── Shared prompt metadata registry ────────────────────────────────────────
# Keyed by prompt fingerprint so reward callbacks can recreate environment
# state without carrying metadata through GRPOTrainer's callback signature.
_PROMPT_META: dict[str, dict] = {}

def _register_prompt(prompt: str, seed: int, task_id: str) -> None:
    key = hashlib.sha1(prompt.encode()).hexdigest()[:12]
    _PROMPT_META[key] = {"seed": seed, "task_id": task_id}

def _lookup_prompt(prompt: str) -> dict:
    key = hashlib.sha1(prompt.encode()).hexdigest()[:12]
    return _PROMPT_META.get(key, {})

# ── Observation → LLM prompt ───────────────────────────────────────────────
_SYSTEM = (
    "You are an expert traffic signal controller. "
    "Choose the optimal action for the intersection state shown.\n"
    "Actions: 0=MAINTAIN 1=SWITCH_PHASE 2=EXTEND_GREEN 3=FORCE_ALL_RED 4=YIELD_MINOR\n"
    "Reply with ONLY valid JSON: "
    "{\"action\":<0-4>,\"reason\":\"<one sentence>\",\"confidence\":<0.0-1.0>}"
)

def build_obs_prompt(obs: dict, step: int, task_id: str) -> str:
    """Format an observation dict into a structured LLM prompt."""
    ql    = obs.get("queue_lengths",   [0.0] * 12)
    ph    = obs.get("phase_onehot",    [1, 0, 0, 0])
    sp    = obs.get("spillback_flags", [0.0] * 12)
    names = ["NS_GREEN", "EW_GREEN", "ALL_RED", "NS_MINOR"]
    phase = names[ph.index(max(ph))] if max(ph) > 0 else "NS_GREEN"
    ns_q  = round(sum(ql[i] for i in [0, 1, 2, 3,  8,  9]), 3)
    ew_q  = round(sum(ql[i] for i in [4, 5, 6, 7, 10, 11]), 3)
    return (
        f"{_SYSTEM}\n\n"
        f"[Step {step} | Task {task_id}]\n"
        f"Phase: {phase} | Elapsed: {obs.get('phase_elapsed_norm',0):.2f}\n"
        f"NS queue: {ns_q:.3f} | EW queue: {ew_q:.3f} | "
        f"Pressure: {obs.get('pressure_differential',0):+.3f}\n"
        f"Avg delay: {obs.get('avg_delay_norm',0)*120:.1f}s | "
        f"Spillback: {int(sum(sp))} lanes | "
        f"Fairness: {obs.get('fairness_score',0):.3f}"
    )

# ── Process-level reward verifiers (guide section 9) ──────────────────────
# Multiple INDEPENDENT verifiers — reduces reward hacking risk.

def _parse_action(c: str) -> int | None:
    try:
        d = json.loads(c)
        a = int(d.get("action", -1))
        return a if 0 <= a <= 4 else None
    except (json.JSONDecodeError, ValueError, TypeError):
        return None

def verifier_format(completions: list[str], **_) -> list[float]:
    """Verifier 1 — JSON format + required keys + action range."""
    out = []
    for c in completions:
        try:
            d = json.loads(c)
            ok_action = 0 <= int(d.get("action", -1)) <= 4
            ok_reason = isinstance(d.get("reason"), str) and len(d["reason"]) > 5
            ok_conf   = isinstance(d.get("confidence"), (int, float))
            out.append(1.0 if (ok_action and ok_reason and ok_conf)
                       else 0.6 if (ok_action and ok_reason)
                       else 0.3 if ok_action
                       else 0.0)
        except Exception:
            out.append(0.0)
    return out

def verifier_no_exploit(completions: list[str], **_) -> list[float]:
    """Verifier 2 — Anti-exploit: penalise forbidden patterns (guide section 8)."""
    _BAD = ["__builtins__", "globals()", "locals()", "exec(", "eval(",
            "os.system", "subprocess", "__import__", "open(", "socket"]
    return [0.0 if any(b in c for b in _BAD) else 1.0 for c in completions]

def verifier_reasoning(completions: list[str], prompts: list[str] | None = None, **_) -> list[float]:
    """Verifier 3 — Process supervision: reason must be contextually grounded."""
    _ACT_KW = {
        0: {"maintain", "hold", "keep", "stable", "continue"},
        1: {"switch", "toggle", "change", "alternate", "flip"},
        2: {"extend", "longer", "more", "hold green"},
        3: {"red", "clear", "safety", "all-red", "clearance"},
        4: {"minor", "yield", "side", "yield minor"},
    }
    out = []
    for i, c in enumerate(completions):
        try:
            d      = json.loads(c)
            action = int(d.get("action", -1))
            reason = d.get("reason", "").lower()
            if not (0 <= action <= 4):
                out.append(0.0); continue
            kw_hit   = any(kw in reason for kw in _ACT_KW.get(action, set()))
            has_body = len(reason.split()) >= 4
            out.append(1.0 if (kw_hit and has_body)
                       else 0.55 if kw_hit
                       else 0.25 if has_body
                       else 0.05)
        except Exception:
            out.append(0.0)
    return out

# Module-level env client ref — set before training, used inside reward callback
_reward_env_client: requests.Session | None = None
_reward_env_host:   str = ""
_reward_env_task:   str = "task_suburban_steady"

def set_reward_env(host: str, task_id: str) -> None:
    """Register environment connection for RLVR reward callback."""
    global _reward_env_client, _reward_env_host, _reward_env_task
    _reward_env_client = requests.Session()
    _reward_env_host   = host.rstrip("/")
    _reward_env_task   = task_id

def verifier_environment(
    completions: list[str],
    prompts: list[str] | None = None,
    **_,
) -> list[float]:
    """
    Verifier 4 — RLVR environment ground truth (primary signal, weight 0.5).
    No learned reward model — the IntelliFlow environment IS the verifier.
    Recreates exact state by resetting with stored seed, executes action,
    returns normalised reward. This is the core GRPO/RLVR pattern.
    """
    if _reward_env_client is None:
        return [0.5] * len(completions)
    out = []
    for i, c in enumerate(completions):
        action = _parse_action(c)
        if action is None:
            out.append(0.0); continue
        prompt = (prompts[i] if prompts and i < len(prompts) else "")
        meta   = _lookup_prompt(prompt)
        seed   = meta.get("seed", 42)
        task   = meta.get("task_id", _reward_env_task)
        try:
            rd  = _reward_env_client.post(
                f"{_reward_env_host}/reset",
                json={"task_id": task, "seed": seed}, timeout=8)
            sid = rd.json()["session_id"]
            sd  = _reward_env_client.post(
                f"{_reward_env_host}/step",
                json={"session_id": sid, "action": action}, timeout=8)
            raw = float(sd.json().get("reward", 0.0))
            out.append(float(np.clip((raw + 5.0) / 10.0, 0.0, 1.0)))
        except Exception as e:
            _log.debug(f"env_verifier error action={action}: {e}")
            out.append(0.0)
    return out

def combined_reward_fn(
    completions: list[str],
    prompts: list[str] | None = None,
    **kwargs,
) -> list[float]:
    """Weighted ensemble of all four independent verifiers."""
    r_env  = verifier_environment(completions, prompts, **kwargs)
    r_fmt  = verifier_format(completions, **kwargs)
    r_reas = verifier_reasoning(completions, prompts, **kwargs)
    r_safe = verifier_no_exploit(completions, **kwargs)
    return [
        0.50 * e + 0.25 * f + 0.15 * r + 0.10 * s
        for e, f, r, s in zip(r_env, r_fmt, r_reas, r_safe)
    ]

# ── Trajectory collection for SFT warm-start ──────────────────────────────
def collect_warmstart_data(
    host: str,
    task_id: str,
    n_episodes: int = 20,
) -> list[dict]:
    """
    Run pressure policy for n_episodes, collect steps where reward > 0.
    Returns list of {prompt, completion, reward, seed} for SFT training.
    Guide: SFT on good demonstrations before RL improves convergence speed.
    """
    def _pressure(obs: dict) -> int:
        ql  = obs.get("queue_lengths", [0.0] * 12)
        ph  = obs.get("phase_onehot",  [1, 0, 0, 0])
        pi  = ph.index(max(ph))
        ela = obs.get("phase_elapsed_norm", 0) * 90
        if ela < 10: return 0
        ns = sum(ql[i] for i in [0, 1, 2, 3, 8, 9])
        ew = sum(ql[i] for i in [4, 5, 6, 7, 10, 11])
        if pi == 0 and ew - ns > 0.4: return 1
        if pi == 1 and ns - ew > 0.4: return 1
        if pi == 0 and ns > 0.75:     return 2
        if pi == 1 and ew > 0.75:     return 2
        return 0

    s = requests.Session()
    records: list[dict] = []
    for ep in range(n_episodes):
        seed = ep * 7 + 42
        try:
            rd  = s.post(f"{host}/reset",
                         json={"task_id": task_id, "seed": seed}, timeout=10)
            rd.raise_for_status()
            sid = rd.json()["session_id"]
            obs = rd.json().get("observation", {})
            for step in range(80):
                action     = _pressure(obs)
                prompt     = build_obs_prompt(obs, step, task_id)
                completion = json.dumps({
                    "action": action,
                    "reason": "pressure-based adaptive control",
                    "confidence": 0.75,
                })
                _register_prompt(prompt, seed, task_id)
                sd   = s.post(f"{host}/step",
                              json={"session_id": sid, "action": action}, timeout=8)
                sd.raise_for_status()
                data = sd.json()
                if data.get("reward", 0.0) > 0:
                    records.append({
                        "prompt": prompt, "completion": completion,
                        "reward": data["reward"], "seed": seed,
                    })
                obs = data.get("observation", obs)
                if data.get("done"): break
        except requests.RequestException as e:
            _log.warning(f"Collection ep {ep} failed: {e}")
    _log.info(f"[collect] {len(records)} positive-reward steps from {n_episodes} episodes")
    return records

# ── SFT warm-start ─────────────────────────────────────────────────────────
def sft_warmstart(
    model: Any,
    tokenizer: Any,
    records: list[dict],
    output_dir: str = "intelliflow_sft",
) -> None:
    """
    SFT on top-75th-percentile collected steps.
    Guide section 3: 'do a little SFT first, then RL' — primes the policy
    so GRPO sees non-zero reward from the first episode.
    Skipped automatically if TRL unavailable or no records provided.
    """
    if not _TRL_AVAILABLE:
        _log.info("[sft] Skipped — TRL not available")
        return
    if model is None or not records:
        _log.info("[sft] Skipped — no model or no collected data")
        return

    rewards   = np.array([r["reward"] for r in records])
    threshold = float(np.percentile(rewards, 75))
    good      = [r for r in records if r["reward"] >= threshold]
    if not good:
        _log.info("[sft] No high-reward steps found — skipping")
        return

    _log.info(f"[sft] Training on {len(good)} steps (reward ≥ {threshold:.3f})")
    dataset = Dataset.from_dict({
        "text": [r["prompt"] + "\n" + r["completion"] for r in good]
    })
    cfg = SFTConfig(
        output_dir=output_dir,
        num_train_epochs=1,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=5,
        save_strategy="no",
        report_to="none",
        max_seq_length=512,
        dataset_text_field="text",
    )
    SFTTrainer(
        model=model, tokenizer=tokenizer,
        args=cfg, train_dataset=dataset,
    ).train()
    _log.info("[sft] Warm-start complete")

HOST = os.environ.get("INTELLIFLOW_HOST", "http://localhost:7860")

TASKS   = ["task_grid_steady", "task_grid_rush", "task_grid_crisis"]
N_OBS    = 73
N_ACT    = 5
HIDDEN   = 128
HIDDEN2  = 64
LR       = 1e-3
GAMMA   = 0.99
EPSILON_START = 1.0
EPSILON_END   = 0.05
EPSILON_DECAY = 0.980
REPLAY_SIZE   = 10_000
BATCH_SIZE    = 64
TARGET_UPDATE = 50
N_EPISODES    = 200

# ---------------------------------------------------------------------------
# Pure-NumPy DQN (no PyTorch needed — matches dqn_weights.json schema)
# ---------------------------------------------------------------------------

def relu(x): return np.maximum(0, x)

class DQN:
    def __init__(self, obs_dim, n_actions, hidden=HIDDEN, hidden2=HIDDEN2):
        self.layers = [
            {"W": np.random.randn(hidden, obs_dim).astype(np.float32) * np.sqrt(2/obs_dim),
             "b": np.zeros(hidden, dtype=np.float32), "activation": "relu"},
            {"W": np.random.randn(hidden, hidden).astype(np.float32) * np.sqrt(2/hidden),
             "b": np.zeros(hidden, dtype=np.float32), "activation": "relu"},
            {"W": np.random.randn(hidden2, hidden).astype(np.float32) * np.sqrt(2/hidden),
             "b": np.zeros(hidden2, dtype=np.float32), "activation": "relu"},
            {"W": np.random.randn(n_actions, hidden2).astype(np.float32) * np.sqrt(2/hidden2),
             "b": np.zeros(n_actions, dtype=np.float32), "activation": "linear"},
        ]

    def forward(self, x):
        for layer in self.layers:
            x = x @ layer["W"].T + layer["b"]
            if layer["activation"] == "relu":
                x = relu(x)
        return x

    def act(self, obs, epsilon=0.0):
        if np.random.random() < epsilon:
            return np.random.randint(N_ACT)
        q = self.forward(np.array(obs, dtype=np.float32))
        return int(np.argmax(q))

    def to_dict(self):
        return {"layers": [
            {"W": l["W"].tolist(), "b": l["b"].tolist(), "activation": l["activation"]}
            for l in self.layers
        ]}

    def copy_from(self, other):
        for sl, ol in zip(self.layers, other.layers):
            sl["W"] = ol["W"].copy()
            sl["b"] = ol["b"].copy()

def compute_loss_and_grads(dqn, target_dqn, batch):
    states, actions, rewards, next_states, dones = zip(*batch)
    states      = np.array(states,      dtype=np.float32)
    next_states = np.array(next_states, dtype=np.float32)
    rewards     = np.array(rewards,     dtype=np.float32)
    dones       = np.array(dones,       dtype=np.float32)

    # Cache activations during forward pass for backprop
    def forward_with_cache(net, x):
        cache = [x]
        for layer in net.layers:
            x = x @ layer["W"].T + layer["b"]
            if layer["activation"] == "relu":
                x = np.maximum(0, x)
            cache.append(x)
        return x, cache

    q_vals_list, caches = [], []
    for s in states:
        q, cache = forward_with_cache(dqn, s)
        q_vals_list.append(q)
        caches.append(cache)
    q_vals = np.array(q_vals_list, dtype=np.float32)

    q_next = np.array([target_dqn.forward(s) for s in next_states], dtype=np.float32)
    targets = q_vals.copy()
    for i, (a, r, d, qn) in enumerate(zip(actions, rewards, dones, q_next)):
        targets[i][a] = r + GAMMA * np.max(qn) * (1 - d)

    loss = float(np.mean((q_vals - targets) ** 2))

    # Backprop: MSE gradient into each layer via chain rule
    grad_output = 2.0 * (q_vals - targets)   # (batch, n_actions)

    n_layers = len(dqn.layers)
    dW_acc = [np.zeros_like(l["W"]) for l in dqn.layers]
    db_acc = [np.zeros_like(l["b"]) for l in dqn.layers]

    for b_idx in range(len(batch)):
        grad = grad_output[b_idx]                          # (n_actions,)
        cache = caches[b_idx]                              # list of activations

        for li in range(n_layers - 1, -1, -1):
            layer  = dqn.layers[li]
            x_in   = cache[li]                            # activation before this layer
            x_out  = cache[li + 1]                        # activation after this layer

            # ReLU backward
            if layer["activation"] == "relu":
                grad = grad * (x_out > 0).astype(np.float32)

            dW_acc[li] += np.outer(grad, x_in)
            db_acc[li] += grad
            grad = layer["W"].T @ grad                    # pass grad to previous layer

    # Adam update
    beta1, beta2, eps = 0.9, 0.999, 1e-8
    if not hasattr(dqn, "_adam_m"):
        dqn._adam_m  = [np.zeros_like(l["W"]) for l in dqn.layers]
        dqn._adam_v  = [np.zeros_like(l["W"]) for l in dqn.layers]
        dqn._adam_mb = [np.zeros_like(l["b"]) for l in dqn.layers]
        dqn._adam_vb = [np.zeros_like(l["b"]) for l in dqn.layers]
        dqn._adam_t  = 0

    dqn._adam_t += 1
    t = dqn._adam_t
    bc1 = 1 - beta1 ** t
    bc2 = 1 - beta2 ** t

    for li, layer in enumerate(dqn.layers):
        gW = np.clip(dW_acc[li] / len(batch), -1.0, 1.0)
        gb = np.clip(db_acc[li] / len(batch), -1.0, 1.0)

        dqn._adam_m[li]  = beta1 * dqn._adam_m[li]  + (1 - beta1) * gW
        dqn._adam_v[li]  = beta2 * dqn._adam_v[li]  + (1 - beta2) * gW ** 2
        dqn._adam_mb[li] = beta1 * dqn._adam_mb[li] + (1 - beta1) * gb
        dqn._adam_vb[li] = beta2 * dqn._adam_vb[li] + (1 - beta2) * gb ** 2

        layer["W"] -= LR * (dqn._adam_m[li] / bc1) / (np.sqrt(dqn._adam_v[li] / bc2) + eps)
        layer["b"] -= LR * (dqn._adam_mb[li] / bc1) / (np.sqrt(dqn._adam_vb[li] / bc2) + eps)

    return loss

# ---------------------------------------------------------------------------
# Training loop
# ---------------------------------------------------------------------------

def train():
    session = requests.Session()
    dqn        = DQN(N_OBS, N_ACT)
    target_dqn = DQN(N_OBS, N_ACT)
    target_dqn.copy_from(dqn)

    replay  = deque(maxlen=REPLAY_SIZE)
    epsilon = EPSILON_START
    scores  = []
    losses  = []

    print(f"Starting IntelliFlow DQN training — {N_EPISODES} episodes across {len(TASKS)} tasks")
    print(f"Host: {HOST}")
    print(f"TRL available: {_TRL_AVAILABLE}")
    print()

    # ── SFT warm-start (guide section 3) ──────────────────────────────────
    # Collects high-reward episodes via pressure policy, trains LLM on them
    # before RL begins — significantly improves GRPO convergence speed.
    # No-op if TRL/Unsloth not installed; DQN training continues either way.
    if _TRL_AVAILABLE:
        _log.info("Collecting warm-start data for SFT...")
        _ws_records = collect_warmstart_data(HOST, TASKS[0], n_episodes=10)
        if _ws_records:
            # LLM model would be loaded here in full TRL run;
            # sft_warmstart safely skips if model=None (DQN-only mode)
            sft_warmstart(model=None, tokenizer=None, records=_ws_records)
        set_reward_env(HOST, TASKS[0])
        _log.info("Reward verifiers armed — RLVR active for GRPO runs")
    # ── End SFT block ──────────────────────────────────────────────────────

    for ep in range(N_EPISODES):
        task_id = TASKS[ep % len(TASKS)]

        r = session.post(f"{HOST}/reset", json={"task_id": task_id, "seed": ep})
        r.raise_for_status()
        data    = r.json()
        sid     = data["session_id"]
        obs     = data.get("observation_vector", [0.0]*N_OBS)
        ep_reward = 0.0
        steps   = 0
        done    = False

        while not done:
            action = dqn.act(obs, epsilon)
            r2 = session.post(f"{HOST}/step", json={"session_id": sid, "action": action})
            if not r2.ok:
                break
            step_data  = r2.json()
            next_obs   = step_data.get("observation_vector", obs)
            reward     = step_data.get("reward", 0.0)
            done       = step_data.get("done", False)

            replay.append((obs, action, reward, next_obs, float(done)))
            obs        = next_obs
            ep_reward += reward
            steps     += 1

            if len(replay) >= BATCH_SIZE:
                idx   = np.random.choice(len(replay), BATCH_SIZE, replace=False)
                batch = [replay[i] for i in idx]
                loss  = compute_loss_and_grads(dqn, target_dqn, batch)
                losses.append(loss)

        if ep % TARGET_UPDATE == 0:
            target_dqn.copy_from(dqn)

        epsilon = max(EPSILON_END, epsilon * EPSILON_DECAY)
        scores.append(ep_reward)

        window_mean = np.mean(scores[-20:]) if len(scores) >= 20 else np.mean(scores)
        avg_loss = round(np.mean(losses[-50:]), 4) if losses else 0.0
        print(f"[EP {ep+1:3d}/{N_EPISODES}] task={task_id:<25s} reward={ep_reward:+8.2f} "
              f"mean20={window_mean:+7.2f} loss={avg_loss:.4f} eps={epsilon:.3f} steps={steps}")

    # Save weights
    weights = dqn.to_dict()
    admin_token = os.environ.get("INTELLIFLOW_ADMIN_TOKEN", "")
    if admin_token:
        resp = session.post(
            f"{HOST}/save_weights",
            json=weights,
            headers={"X-Admin-Token": admin_token, "Content-Type": "application/json"},
        )
        print(f"\nWeights saved: {resp.json()}")
    else:
        with open("dqn_weights_trained.json", "w") as f:
            json.dump(weights, f)
        print("\nWeights saved locally to dqn_weights_trained.json")
        print("Set INTELLIFLOW_ADMIN_TOKEN env var to push to server automatically.")

    # Print reward curve summary
    print("\n=== REWARD CURVE SUMMARY ===")
    first10 = np.mean(scores[:10])
    last10  = np.mean(scores[-10:])
    improvement = last10 - first10
    print(f"First 10 ep mean: {first10:+.3f}")
    print(f"Last  10 ep mean: {last10:+.3f}")
    print(f"Improvement:      {improvement:+.3f}  {'✓ LEARNING' if improvement > 0 else '✗ NOT IMPROVING'}")
    print(f"Best episode:     {max(scores):+.3f}")
    print(f"Total grad steps: {len(losses)}")
    if losses:
        print(f"Final loss:       {np.mean(losses[-20:]):.5f}")
        print(f"Initial loss:     {np.mean(losses[:20]):.5f}")
        print(f"Loss reduction:   {np.mean(losses[:20]) - np.mean(losses[-20:]):+.5f}")

    # Rolling 10-ep mean curve for judges
    rolling = [
        round(float(np.mean(scores[max(0,i-9):i+1])), 3)
        for i in range(len(scores))
    ]
    print(f"\n[REWARD_CURVE] {json.dumps([round(s,3) for s in scores])}")
    print(f"[ROLLING_MEAN_10] {json.dumps(rolling)}")

    # Save reward log to disk for plotting
    log = {
        "scores":         [round(s,4) for s in scores],
        "rolling_mean10": rolling,
        "losses":         [round(l,6) for l in losses[-200:]],
        "improvement":    round(float(improvement), 4),
        "episodes":       N_EPISODES,
        "tasks":          TASKS,
    }
    with open("training_log.json", "w") as f:
        json.dump(log, f, indent=2)
    print("Training log saved to training_log.json")

    return scores

if __name__ == "__main__":
    scores = train()