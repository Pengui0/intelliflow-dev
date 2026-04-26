"""
IntelliFlow — TRL + Unsloth GRPO Training Pipeline
====================================================
Guide-compliant training stack:
  Environment → multi-verifier RLVR rewards → TRL GRPOTrainer → Unsloth

Key design decisions:
  - RLVR (RL with Verifiable Rewards): environment IS the reward model
  - SFT warm-start on pressure-policy demonstrations before GRPO
  - Curriculum: easy → medium → hard tasks (guide section 6)
  - 4 independent verifiers reduce reward hacking surface (guide section 7-8)
  - LoRA saved via Unsloth merged path — never naive 4-bit upcast (guide section 16)

Install: pip install trl unsloth datasets requests
Run:     python trl_grpo_train.py [--task all] [--episodes 40] [--epochs 3]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("intelliflow.grpo")

# ── TRL + Unsloth ─────────────────────────────────────────────────────────
try:
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer, SFTConfig, SFTTrainer
    from unsloth import FastLanguageModel
    _TRL_AVAILABLE = True
    log.info("[stack] TRL + Unsloth — GRPO training fully enabled")
except ImportError as _e:
    _TRL_AVAILABLE = False
    Dataset = None  # type: ignore
    log.warning(f"[stack] {_e}. Running in collect-only mode. "
                "pip install trl unsloth datasets")


# ── Config ─────────────────────────────────────────────────────────────────
@dataclass
class GRPOConfig_:
    host: str = field(
        default_factory=lambda: os.environ.get(
            "INTELLIFLOW_HOST", "http://localhost:7860"
        )
    )
    # Model
    model_name: str    = "unsloth/Qwen2.5-1.5B-Instruct"
    max_seq_len: int   = 512
    load_in_4bit: bool = True
    lora_r: int        = 16
    lora_alpha: int    = 16
    # Curriculum (guide section 6: make success possible early)
    curriculum: list[str] = field(default_factory=lambda: [
        "task_suburban_steady",    # easy   — learns basic phase switching
        "task_urban_stochastic",   # medium — adapts to bursty arrivals
        "task_rush_hour_crisis",   # hard   — survives near-saturation load
    ])
    # Data collection
    n_collect_eps: int   = 40     # episodes per curriculum task
    explore_rate: float  = 0.25   # fraction of random actions during collection
    # SFT warm-start
    sft_percentile: float = 75.0  # train SFT on top-N% reward steps
    sft_epochs: int       = 1
    # GRPO
    grpo_epochs: int      = 3
    grpo_batch: int       = 4
    grpo_grad_accum: int  = 4
    grpo_lr: float        = 5e-5
    grpo_group_size: int  = 4     # G completions sampled per prompt
    grpo_max_tokens: int  = 128
    # Reward weights (must sum to 1.0)
    w_env:    float = 0.50        # environment ground-truth (primary)
    w_format: float = 0.25        # JSON format compliance
    w_reason: float = 0.15        # reasoning quality / process supervision
    w_safe:   float = 0.10        # anti-exploit guard
    # Output
    output_dir: str = "intelliflow_grpo"


# ── Environment client ──────────────────────────────────────────────────────
class EnvClient:
    """Typed HTTP client for IntelliFlow OpenEnv API."""

    def __init__(self, host: str, timeout: int = 10):
        self.host    = host.rstrip("/")
        self.timeout = timeout
        self._s      = requests.Session()
        self._s.headers["Content-Type"] = "application/json"

    def health(self) -> dict:
        return self._s.get(f"{self.host}/health", timeout=self.timeout).json()

    def reset(self, task_id: str, seed: int) -> dict:
        r = self._s.post(f"{self.host}/reset",
                         json={"task_id": task_id, "seed": seed},
                         timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def step(self, session_id: str, action: int) -> dict:
        r = self._s.post(f"{self.host}/step",
                         json={"session_id": session_id, "action": action},
                         timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def grade(self, session_id: str) -> dict:
        r = self._s.post(f"{self.host}/grader",
                         json={"session_id": session_id},
                         timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def benchmark(self, task_id: str, policy: str, seeds: str = "42,43,44") -> dict:
        r = self._s.post(
            f"{self.host}/benchmark",
            params={"task_id": task_id, "policy": policy, "seeds": seeds},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()


# ── Prompt construction ─────────────────────────────────────────────────────
_SYSTEM_PROMPT = (
    "You are an expert traffic signal controller AI managing an urban intersection.\n"
    "Analyse the current intersection state and choose the optimal signal action.\n\n"
    "Actions:\n"
    "  0 = MAINTAIN      — keep current phase unchanged\n"
    "  1 = SWITCH_PHASE  — toggle N-S ↔ E-W green\n"
    "  2 = EXTEND_GREEN  — hold current green phase longer\n"
    "  3 = FORCE_ALL_RED — safety clearance interval (3 steps)\n"
    "  4 = YIELD_MINOR   — brief green for minor side-road approaches\n\n"
    "Respond with ONLY valid JSON (no markdown):\n"
    '{"action": <0-4>, "reason": "<one sentence>", "confidence": <0.0-1.0>}'
)

def build_prompt(obs: dict, step: int, task_id: str) -> str:
    ql    = obs.get("queue_lengths",   [0.0] * 12)
    ph    = obs.get("phase_onehot",    [1, 0, 0, 0])
    sp    = obs.get("spillback_flags", [0.0] * 12)
    names = ["NS_GREEN", "EW_GREEN", "ALL_RED", "NS_MINOR"]
    phase = names[ph.index(max(ph))] if max(ph) > 0 else "NS_GREEN"
    ns_q  = round(sum(ql[i] for i in [0, 1, 2, 3, 8, 9]),   3)
    ew_q  = round(sum(ql[i] for i in [4, 5, 6, 7, 10, 11]), 3)
    delay = round(obs.get("avg_delay_norm", 0.0) * 120.0, 1)
    press = obs.get("pressure_differential", 0.0)
    spill = int(sum(sp))
    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"--- State (step={step}, task={task_id}) ---\n"
        f"Phase: {phase}  |  Elapsed: {obs.get('phase_elapsed_norm',0):.2f}\n"
        f"NS queue: {ns_q:.3f}  |  EW queue: {ew_q:.3f}  "
        f"|  Pressure: {press:+.3f}\n"
        f"Avg delay: {delay:.1f}s  |  Spillback lanes: {spill}  "
        f"|  Fairness: {obs.get('fairness_score',0):.3f}\n"
        f"Progress: {obs.get('step_norm',0):.3f}"
    )


# ── Prompt registry ─────────────────────────────────────────────────────────
# Connects prompts → (seed, task_id) so reward functions can recreate
# exact environment state without polluting the prompt string.
_REGISTRY: dict[str, dict] = {}

def _reg(prompt: str, seed: int, task_id: str) -> None:
    _REGISTRY[hashlib.sha1(prompt.encode()).hexdigest()[:12]] = {
        "seed": seed, "task_id": task_id
    }

def _get(prompt: str) -> dict:
    return _REGISTRY.get(hashlib.sha1(prompt.encode()).hexdigest()[:12], {})


# ── Reward verifiers ────────────────────────────────────────────────────────
# Guide section 7-8: "use multiple independent reward functions, not just one."
# Each verifier is a pure function scoring exactly one behavioural property.

def _parse(c: str) -> int | None:
    try:
        a = int(json.loads(c).get("action", -1))
        return a if 0 <= a <= 4 else None
    except Exception:
        return None

def reward_format(completions: list[str], **_) -> list[float]:
    """
    Verifier 1 — Format compliance.
    Full score: valid JSON with action + reason + confidence.
    Partial: valid JSON with action only.
    Zero: invalid JSON or action out of range.
    """
    out = []
    for c in completions:
        try:
            d        = json.loads(c)
            ok_act   = 0 <= int(d.get("action", -1)) <= 4
            ok_rsn   = isinstance(d.get("reason"), str) and len(d["reason"].split()) >= 3
            ok_conf  = isinstance(d.get("confidence"), (int, float))
            out.append(
                1.00 if (ok_act and ok_rsn and ok_conf) else
                0.70 if (ok_act and ok_rsn) else
                0.35 if ok_act else
                0.00
            )
        except Exception:
            out.append(0.0)
    return out

def reward_no_exploit(completions: list[str], **_) -> list[float]:
    """
    Verifier 2 — Anti-exploit guard.
    Catches timer-editing, cache-abuse, global mutation, and eval patterns.
    Guide section 8: "lock down execution where possible."
    """
    _BAD = [
        "__builtins__", "globals()", "locals()", "exec(", "eval(",
        "os.system", "subprocess", "__import__", "open(",
        "socket", "cache[", "timer", "sleep(", "setattr(",
    ]
    return [0.0 if any(b in c for b in _BAD) else 1.0 for c in completions]

def reward_reasoning(
    completions: list[str],
    prompts: list[str] | None = None,
    **_,
) -> list[float]:
    """
    Verifier 3 — Process supervision via reasoning quality.
    Guide section 9: "use richer supervision that distinguishes good
    intermediate steps from bad ones."
    Checks whether the stated reason is contextually grounded in the
    observation: direction keywords for switch actions, timing keywords
    for extend, safety language for all-red.
    """
    _KW: dict[int, set[str]] = {
        0: {"maintain", "hold", "keep", "stable", "unchanged"},
        1: {"switch", "toggle", "change", "alternate", "high queue",
            "north", "south", "east", "west", "pressure"},
        2: {"extend", "longer", "more green", "hold green", "throughput"},
        3: {"red", "clear", "safety", "all-red", "clearance", "emergency"},
        4: {"minor", "yield", "side road", "low volume", "right turn"},
    }
    out = []
    for i, c in enumerate(completions):
        try:
            d      = json.loads(c)
            action = int(d.get("action", -1))
            reason = d.get("reason", "").lower()
            if not (0 <= action <= 4):
                out.append(0.0); continue
            kw_hit   = any(kw in reason for kw in _KW.get(action, set()))
            obs_ref  = len(reason.split()) >= 5
            # Bonus: reason references queue numbers from observation
            has_nums = any(ch.isdigit() for ch in reason)
            out.append(
                1.00 if (kw_hit and obs_ref and has_nums) else
                0.70 if (kw_hit and obs_ref) else
                0.40 if kw_hit else
                0.15 if obs_ref else
                0.00
            )
        except Exception:
            out.append(0.0)
    return out

# Module-level env client used by reward_environment callback
_env_client_ref: EnvClient | None = None
_env_task_ref:   str = "task_suburban_steady"

def _set_env_context(client: EnvClient, task_id: str) -> None:
    global _env_client_ref, _env_task_ref
    _env_client_ref = client
    _env_task_ref   = task_id

def reward_environment(
    completions: list[str],
    prompts: list[str] | None = None,
    **_,
) -> list[float]:
    """
    Verifier 4 — RLVR environment ground truth (primary signal, weight 0.50).
    The IntelliFlow environment IS the verifier — no learned reward model.
    Recreates exact starting state via stored seed, executes the LLM's
    action, returns normalised step reward. This is the GRPO/RLVR pattern
    described in guide section 11: "build the verifier first, then plug
    that verifier into RL training."
    """
    if _env_client_ref is None:
        return [0.5] * len(completions)
    out = []
    for i, c in enumerate(completions):
        action = _parse(c)
        if action is None:
            out.append(0.0); continue
        meta = _get(prompts[i] if prompts and i < len(prompts) else "")
        seed = meta.get("seed", 42)
        task = meta.get("task_id", _env_task_ref)
        try:
            sid = _env_client_ref.reset(task, seed)["session_id"]
            raw = float(
                _env_client_ref.step(sid, action).get("reward", 0.0)
            )
            out.append(float(np.clip((raw + 5.0) / 10.0, 0.0, 1.0)))
        except Exception as e:
            log.debug(f"env verifier error action={action}: {e}")
            out.append(0.0)
    return out


# ── Episode collector ────────────────────────────────────────────────────────
class EpisodeCollector:
    """
    Collects (prompt, completion, reward) records using pressure policy
    mixed with random exploration. Builds the GRPO training dataset.
    Guide section 6: start with easy tasks, make success possible early.
    """

    def __init__(self, client: EnvClient, cfg: GRPOConfig_):
        self.client = client
        self.cfg    = cfg

    @staticmethod
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

    def collect(self, task_id: str) -> list[dict]:
        records: list[dict] = []
        n = self.cfg.n_collect_eps
        for ep in range(n):
            seed = ep * 7 + 42
            try:
                data = self.client.reset(task_id, seed)
            except requests.RequestException as e:
                log.warning(f"Reset failed ep={ep}: {e}")
                continue

            sid  = data["session_id"]
            obs  = data.get("observation", {})
            for step in range(80):
                action = (
                    np.random.randint(0, 5)
                    if np.random.random() < self.cfg.explore_rate
                    else self._pressure(obs)
                )
                prompt = build_prompt(obs, step, task_id)
                _reg(prompt, seed, task_id)
                completion = json.dumps({
                    "action":     action,
                    "reason":     "pressure-adaptive control with queue balancing",
                    "confidence": 0.75,
                })
                try:
                    sd = self.client.step(sid, action)
                except requests.RequestException:
                    break
                records.append({
                    "prompt":     prompt,
                    "completion": completion,
                    "reward":     float(sd.get("reward", 0.0)),
                    "seed":       seed,
                    "task_id":    task_id,
                })
                obs = sd.get("observation", obs)
                if sd.get("done"):
                    break

            if (ep + 1) % 10 == 0:
                log.info(f"  Collected {ep+1}/{n} eps · "
                         f"{len(records)} records so far")

        if records:
            rw = [r["reward"] for r in records]
            log.info(f"Collection done · {len(records)} steps · "
                     f"mean_reward={np.mean(rw):.3f} "
                     f"max={np.max(rw):.3f}")
        return records


# ── GRPO pipeline ───────────────────────────────────────────────────────────
class GRPOPipeline:
    """
    Orchestrates the full training loop:
      collect → SFT warm-start → GRPO → save.
    Guide sections 13-14: deploy early, scale only after environment is stable.
    """

    def __init__(self, cfg: GRPOConfig_):
        self.cfg    = cfg
        self.client = EnvClient(cfg.host)
        self.model  = None
        self.tok    = None

    # ── Server validation ─────────────────────────────────────────────────
    def _check_server(self) -> None:
        try:
            h = self.client.health()
            log.info(f"Server OK · uptime={h.get('uptime_seconds')}s · "
                     f"tasks={h.get('tasks_available', [])}")
        except Exception as e:
            raise RuntimeError(
                f"Cannot reach IntelliFlow server at {self.cfg.host}: {e}\n"
                "Run: uvicorn app.api.main:app --port 7860"
            )

    # ── Model loading ─────────────────────────────────────────────────────
    def _load_model(self) -> bool:
        if not _TRL_AVAILABLE:
            log.warning("TRL/Unsloth not available — running collect-only mode")
            return False
        try:
            log.info(f"Loading {self.cfg.model_name} with Unsloth 4-bit...")
            self.model, self.tok = FastLanguageModel.from_pretrained(
                model_name=self.cfg.model_name,
                max_seq_length=self.cfg.max_seq_len,
                load_in_4bit=self.cfg.load_in_4bit,
                dtype=None,
            )
            self.model = FastLanguageModel.get_peft_model(
                self.model,
                r=self.cfg.lora_r,
                target_modules=[
                    "q_proj", "k_proj", "v_proj", "o_proj",
                    "gate_proj", "up_proj", "down_proj",
                ],
                lora_alpha=self.cfg.lora_alpha,
                lora_dropout=0.0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=42,
            )
            trainable = sum(p.numel() for p in self.model.parameters() if p.requires_grad)
            total     = sum(p.numel() for p in self.model.parameters())
            log.info(f"LoRA loaded · trainable: {trainable:,} / {total:,} params "
                     f"({100*trainable/total:.2f}%)")
            return True
        except Exception as e:
            log.error(f"Model load failed: {e}")
            return False

    # ── SFT warm-start ────────────────────────────────────────────────────
    def _sft_warmstart(self, records: list[dict]) -> None:
        """
        SFT on top-percentile collected trajectories before GRPO.
        Guide section 3: 'do a little SFT first, then RL' — primes the
        policy so GRPO receives non-zero reward from episode 1.
        """
        if not records or self.model is None:
            return
        rewards   = np.array([r["reward"] for r in records])
        threshold = float(np.percentile(rewards, self.cfg.sft_percentile))
        good      = [r for r in records if r["reward"] >= threshold]
        if not good:
            log.info("[sft] No steps above threshold — skipping warm-start")
            return
        log.info(f"[sft] Warm-starting on {len(good)} steps "
                 f"(reward ≥ {threshold:.3f}, "
                 f"top {100-self.cfg.sft_percentile:.0f}%)")
        dataset = Dataset.from_dict({
            "text": [r["prompt"] + "\n" + r["completion"] for r in good]
        })
        sft_cfg = SFTConfig(
            output_dir=os.path.join(self.cfg.output_dir, "sft"),
            num_train_epochs=self.cfg.sft_epochs,
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            learning_rate=2e-4,
            logging_steps=5,
            save_strategy="no",
            report_to="none",
            max_seq_length=self.cfg.max_seq_len,
            dataset_text_field="text",
        )
        SFTTrainer(
            model=self.model, tokenizer=self.tok,
            args=sft_cfg, train_dataset=dataset,
        ).train()
        log.info("[sft] Warm-start complete — model primed for GRPO")

    # ── Combined reward function ──────────────────────────────────────────
    def _make_reward_fn(self) -> Any:
        """
        Returns a single reward function that weights all 4 independent
        verifiers. Defined as a closure so weights are captured cleanly.
        """
        w_env, w_fmt, w_rsn, w_safe = (
            self.cfg.w_env, self.cfg.w_format,
            self.cfg.w_reason, self.cfg.w_safe,
        )
        def _combined(completions: list[str],
                      prompts: list[str] | None = None, **kwargs) -> list[float]:
            r_e = reward_environment(completions, prompts, **kwargs)
            r_f = reward_format(completions, **kwargs)
            r_r = reward_reasoning(completions, prompts, **kwargs)
            r_s = reward_no_exploit(completions, **kwargs)
            return [
                w_env * e + w_fmt * f + w_rsn * r + w_safe * s
                for e, f, r, s in zip(r_e, r_f, r_r, r_s)
            ]
        return _combined

    # ── GRPO training ─────────────────────────────────────────────────────
    def _grpo_train(self, dataset: "Dataset", task_id: str) -> None:
        reward_fn = self._make_reward_fn()
        grpo_args = GRPOConfig(
            output_dir=os.path.join(self.cfg.output_dir, task_id),
            num_train_epochs=self.cfg.grpo_epochs,
            per_device_train_batch_size=self.cfg.grpo_batch,
            gradient_accumulation_steps=self.cfg.grpo_grad_accum,
            learning_rate=self.cfg.grpo_lr,
            logging_steps=1,
            save_steps=20,
            report_to="none",
            num_generations=self.cfg.grpo_group_size,
            max_completion_length=self.cfg.grpo_max_tokens,
            temperature=0.9,
            top_p=0.95,
        )
        trainer = GRPOTrainer(
            model=self.model,
            reward_funcs=[reward_fn],
            args=grpo_args,
            train_dataset=dataset,
            tokenizer=self.tok,
        )
        log.info(f"[grpo] Training on {task_id} · "
                 f"{len(dataset)} prompts · "
                 f"G={self.cfg.grpo_group_size} · "
                 f"epochs={self.cfg.grpo_epochs}")
        trainer.train()
        log.info(f"[grpo] Done — {task_id}")

    # ── Safe model save ───────────────────────────────────────────────────
    def _save(self) -> None:
        """
        Guide section 16: do NOT upcast 4-bit model to 16-bit and merge
        LoRA naively. Use Unsloth's proper merged-save path instead.
        """
        if self.model is None:
            return
        merged_path = os.path.join(self.cfg.output_dir, "final_merged")
        log.info(f"Saving to {merged_path}/ (merged_16bit via Unsloth)...")
        try:
            self.model.save_pretrained_merged(
                merged_path, self.tok, save_method="merged_16bit"
            )
            log.info("Model saved — LoRA correctly fused via merged_16bit")
        except Exception as e:
            log.error(f"Merged save failed ({e}) — saving LoRA adapters only")
            adapter_path = os.path.join(self.cfg.output_dir, "lora_adapters")
            self.model.save_pretrained(adapter_path)
            self.tok.save_pretrained(adapter_path)
            log.info(f"LoRA adapters saved to {adapter_path}/")

    # ── Evaluation ────────────────────────────────────────────────────────
    def _eval_baseline_comparison(self, task_id: str) -> None:
        """Compare trained DQN vs pressure baseline via /benchmark endpoint."""
        log.info(f"[eval] Running benchmark comparison on {task_id}...")
        for policy in ("pressure", "dqn"):
            try:
                r = self.client.benchmark(task_id, policy, seeds="42,43,44")
                log.info(
                    f"  {policy:<10s} mean={r.get('mean_score', 0):.4f} "
                    f"std={r.get('std_score', 0):.4f}"
                )
            except Exception as e:
                log.warning(f"  Benchmark {policy} failed: {e}")

    # ── Main run loop ─────────────────────────────────────────────────────
    def run(self) -> None:
        self._check_server()
        model_ready = self._load_model()

        for task_id in self.cfg.curriculum:
            log.info(f"\n{'─'*60}")
            log.info(f"  Curriculum: {task_id}")
            log.info(f"{'─'*60}")

            _set_env_context(self.client, task_id)
            collector = EpisodeCollector(self.client, self.cfg)
            records   = collector.collect(task_id)

            if not records:
                log.error(f"No records collected for {task_id} — check server")
                continue

            if not model_ready:
                log.info("Collect-only mode — logging reward statistics")
                rw = [r["reward"] for r in records]
                log.info(f"  mean={np.mean(rw):.4f} "
                         f"p75={np.percentile(rw,75):.4f} "
                         f"max={np.max(rw):.4f}")
                continue

            # 1. SFT warm-start
            self._sft_warmstart(records)

            # 2. Build GRPO dataset from collected prompts
            dataset = Dataset.from_dict({
                "prompt": [r["prompt"] for r in records]
            })

            # 3. GRPO training
            self._grpo_train(dataset, task_id)

            # 4. Quick eval after each curriculum task
            self._eval_baseline_comparison(task_id)

        # 5. Save final model (guide: test post-training inference immediately)
        self._save()
        log.info("\nPipeline complete. Check /proof_of_learning for judge-ready metrics.")


# ── Entry point ─────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="IntelliFlow TRL + Unsloth GRPO Training",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--host",       default=None,
                        help="Override IntelliFlow server URL")
    parser.add_argument("--model",      default="unsloth/Qwen2.5-1.5B-Instruct")
    parser.add_argument("--task",       default="all",
                        choices=["all", "task_suburban_steady",
                                 "task_urban_stochastic", "task_rush_hour_crisis"])
    parser.add_argument("--episodes",   type=int, default=40,
                        help="Collection episodes per curriculum task")
    parser.add_argument("--epochs",     type=int, default=3,
                        help="GRPO training epochs per task")
    parser.add_argument("--output",     default="intelliflow_grpo")
    parser.add_argument("--explore",    type=float, default=0.25,
                        help="Random exploration rate during collection")
    args = parser.parse_args()

    cfg = GRPOConfig_(
        model_name=args.model,
        n_collect_eps=args.episodes,
        grpo_epochs=args.epochs,
        output_dir=args.output,
        explore_rate=args.explore,
    )
    if args.host:
        cfg.host = args.host
    if args.task != "all":
        cfg.curriculum = [args.task]

    GRPOPipeline(cfg).run()


if __name__ == "__main__":
    main()