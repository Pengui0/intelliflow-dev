"""
IntelliFlow LSTM Inflow Predictor  v1.2.0
==========================================

Fixes in v1.2.0
---------------
- train_offline() called random.shuffle(indices) without a seeded RNG,
  making episode-end training non-reproducible across runs with the same
  seed.  Now uses a dedicated numpy-seeded RNG derived from the episode
  arrival data length so shuffles are deterministic given the same data.
- _save_weights() now writes to a temp file then renames atomically to
  avoid corrupt JSON if the process is interrupted mid-write.
- Minor: removed bare `import random` at module level — only used inside
  train_offline where the seeded rng is now explicit.
"""

from __future__ import annotations

import json
import math
import os
import tempfile
from typing import List, Optional, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_WEIGHTS_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "api", "lstm_weights.json")
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

N_LANES: int   = 12
SEQ_LEN: int   = 20
HIDDEN:  int   = 64
LR:      float = 0.001
EPOCHS:  int   = 12
BATCH:   int   = 16
CLIP:    float = 1.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sigmoid(x: np.ndarray) -> np.ndarray:
    return np.where(
        x >= 0,
        1.0 / (1.0 + np.exp(-x)),
        np.exp(x) / (1.0 + np.exp(x)),
    )


def _tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


# ---------------------------------------------------------------------------
# LSTM cell
# ---------------------------------------------------------------------------

class _LSTMCell:
    def __init__(self, input_dim: int, hidden_dim: int) -> None:
        self.input_dim  = input_dim
        self.hidden_dim = hidden_dim
        d     = input_dim + hidden_dim
        scale = math.sqrt(2.0 / (input_dim + hidden_dim))

        self.W  = np.random.randn(4 * hidden_dim, d).astype(np.float32) * scale
        self.b  = np.zeros(4 * hidden_dim, dtype=np.float32)
        self.b[hidden_dim: 2 * hidden_dim] = 1.0   # forget-gate bias trick

        self.mW = np.zeros_like(self.W)
        self.vW = np.zeros_like(self.W)
        self.mb = np.zeros_like(self.b)
        self.vb = np.zeros_like(self.b)
        self.adam_t: int = 0

        self._cache: List[dict] = []

    def zero_cache(self) -> None:
        self._cache = []

    def forward(
        self,
        x: np.ndarray,
        h: np.ndarray,
        c: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        xh    = np.concatenate([x, h])
        gates = self.W @ xh + self.b
        H     = self.hidden_dim
        i_gate = _sigmoid(gates[0*H: 1*H])
        f_gate = _sigmoid(gates[1*H: 2*H])
        g_gate = _tanh(  gates[2*H: 3*H])
        o_gate = _sigmoid(gates[3*H: 4*H])

        c_next = f_gate * c + i_gate * g_gate
        h_next = o_gate * _tanh(c_next)

        self._cache.append({
            "x": x, "h": h, "c": c, "xh": xh,
            "i": i_gate, "f": f_gate, "g": g_gate, "o": o_gate,
            "c_next": c_next, "h_next": h_next,
        })
        return h_next, c_next

    def backward(
        self,
        dh_next: np.ndarray,
        dc_next: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not self._cache:
            H = self.hidden_dim
            return (
                np.zeros(self.input_dim,  dtype=np.float32),
                np.zeros(H,              dtype=np.float32),
                np.zeros(H,              dtype=np.float32),
            )

        cache = self._cache.pop()
        i, f, g, o = cache["i"], cache["f"], cache["g"], cache["o"]
        c, c_next   = cache["c"], cache["c_next"]
        xh          = cache["xh"]
        H           = self.hidden_dim

        tanh_c_next = _tanh(c_next)
        do  = dh_next * tanh_c_next
        dc  = dh_next * o * (1.0 - tanh_c_next ** 2) + dc_next

        di      = dc * g
        df      = dc * c
        dg      = dc * i
        dc_prev = dc * f

        di_pre = di * i * (1.0 - i)
        df_pre = df * f * (1.0 - f)
        dg_pre = dg * (1.0 - g ** 2)
        do_pre = do * o * (1.0 - o)

        d_gates = np.concatenate([di_pre, df_pre, dg_pre, do_pre])

        dW  = np.outer(d_gates, xh)
        db  = d_gates
        dxh = self.W.T @ d_gates

        if not hasattr(self, "_dW"):
            self._dW = np.zeros_like(self.W)
            self._db = np.zeros_like(self.b)
        self._dW += dW
        self._db += db

        dx      = dxh[: self.input_dim]
        dh_prev = dxh[self.input_dim:]
        return dx, dh_prev, dc_prev

    def apply_gradients(self, lr: float, clip: float, batch_size: int) -> None:
        if not hasattr(self, "_dW"):
            return
        dW = self._dW / max(batch_size, 1)
        db = self._db / max(batch_size, 1)

        norm = math.sqrt(float(np.sum(dW ** 2) + np.sum(db ** 2)))
        if norm > clip:
            scale = clip / norm
            dW   *= scale
            db   *= scale

        self.adam_t += 1
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        bc1 = 1.0 - beta1 ** self.adam_t
        bc2 = 1.0 - beta2 ** self.adam_t

        self.mW = beta1 * self.mW + (1 - beta1) * dW
        self.vW = beta2 * self.vW + (1 - beta2) * dW ** 2
        self.W -= lr * (self.mW / bc1) / (np.sqrt(self.vW / bc2) + eps)

        self.mb = beta1 * self.mb + (1 - beta1) * db
        self.vb = beta2 * self.vb + (1 - beta2) * db ** 2
        self.b -= lr * (self.mb / bc1) / (np.sqrt(self.vb / bc2) + eps)

        del self._dW, self._db

    def to_dict(self) -> dict:
        return {
            "W": self.W.tolist(), "b": self.b.tolist(),
            "mW": self.mW.tolist(), "vW": self.vW.tolist(),
            "mb": self.mb.tolist(), "vb": self.vb.tolist(),
            "adam_t": self.adam_t,
            "input_dim": self.input_dim,
            "hidden_dim": self.hidden_dim,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "_LSTMCell":
        cell        = cls(d["input_dim"], d["hidden_dim"])
        cell.W      = np.array(d["W"],  dtype=np.float32)
        cell.b      = np.array(d["b"],  dtype=np.float32)
        cell.mW     = np.array(d["mW"], dtype=np.float32)
        cell.vW     = np.array(d["vW"], dtype=np.float32)
        cell.mb     = np.array(d["mb"], dtype=np.float32)
        cell.vb     = np.array(d["vb"], dtype=np.float32)
        cell.adam_t = int(d["adam_t"])
        return cell


# ---------------------------------------------------------------------------
# Linear output layer
# ---------------------------------------------------------------------------

class _LinearLayer:
    def __init__(self, in_dim: int, out_dim: int) -> None:
        scale   = math.sqrt(2.0 / (in_dim + out_dim))
        self.W  = np.random.randn(out_dim, in_dim).astype(np.float32) * scale
        self.b  = np.zeros(out_dim, dtype=np.float32)
        self.mW = np.zeros_like(self.W)
        self.vW = np.zeros_like(self.W)
        self.mb = np.zeros_like(self.b)
        self.vb = np.zeros_like(self.b)
        self.adam_t: int = 0
        self._last_x: Optional[np.ndarray] = None
        self._dW = np.zeros_like(self.W)
        self._db = np.zeros_like(self.b)

    def forward(self, x: np.ndarray) -> np.ndarray:
        self._last_x = x
        return self.W @ x + self.b

    def backward(self, d_out: np.ndarray) -> np.ndarray:
        self._dW += np.outer(d_out, self._last_x)
        self._db += d_out
        return self.W.T @ d_out

    def apply_gradients(self, lr: float, clip: float, batch_size: int) -> None:
        dW = self._dW / max(batch_size, 1)
        db = self._db / max(batch_size, 1)

        norm = math.sqrt(float(np.sum(dW ** 2) + np.sum(db ** 2)))
        if norm > clip:
            scale = clip / norm
            dW   *= scale
            db   *= scale

        self.adam_t += 1
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        bc1 = 1.0 - beta1 ** self.adam_t
        bc2 = 1.0 - beta2 ** self.adam_t

        self.mW = beta1 * self.mW + (1 - beta1) * dW
        self.vW = beta2 * self.vW + (1 - beta2) * dW ** 2
        self.W -= lr * (self.mW / bc1) / (np.sqrt(self.vW / bc2) + eps)

        self.mb = beta1 * self.mb + (1 - beta1) * db
        self.vb = beta2 * self.vb + (1 - beta2) * db ** 2
        self.b -= lr * (self.mb / bc1) / (np.sqrt(self.vb / bc2) + eps)

        self._dW = np.zeros_like(self.W)
        self._db = np.zeros_like(self.b)

    def to_dict(self) -> dict:
        return {
            "W": self.W.tolist(), "b": self.b.tolist(),
            "mW": self.mW.tolist(), "vW": self.vW.tolist(),
            "mb": self.mb.tolist(), "vb": self.vb.tolist(),
            "adam_t": self.adam_t,
            "in_dim": self.W.shape[1], "out_dim": self.W.shape[0],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "_LinearLayer":
        layer        = cls(d["in_dim"], d["out_dim"])
        layer.W      = np.array(d["W"],  dtype=np.float32)
        layer.b      = np.array(d["b"],  dtype=np.float32)
        layer.mW     = np.array(d["mW"], dtype=np.float32)
        layer.vW     = np.array(d["vW"], dtype=np.float32)
        layer.mb     = np.array(d["mb"], dtype=np.float32)
        layer.vb     = np.array(d["vb"], dtype=np.float32)
        layer.adam_t = int(d["adam_t"])
        return layer


# ---------------------------------------------------------------------------
# LSTMPredictor — public API
# ---------------------------------------------------------------------------

class LSTMPredictor:
    """
    Wraps the LSTM cell + linear output into a clean predictor API.
    """

    def __init__(self, weights_path: str = _WEIGHTS_PATH) -> None:
        self._weights_path = weights_path
        self._cell   = _LSTMCell(N_LANES, HIDDEN)
        self._output = _LinearLayer(HIDDEN, N_LANES)

        self._history:          List[np.ndarray] = []
        self._h = np.zeros(HIDDEN, dtype=np.float32)
        self._c = np.zeros(HIDDEN, dtype=np.float32)
        self._episode_arrivals: List[np.ndarray] = []
        self._trained: bool = False

        self._load_weights()

    # ------------------------------------------------------------------
    # Online inference
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._h = np.zeros(HIDDEN, dtype=np.float32)
        self._c = np.zeros(HIDDEN, dtype=np.float32)
        self._history.clear()
        self._episode_arrivals.clear()
        self._cell.zero_cache()

    def observe(self, arrival_vector: np.ndarray) -> None:
        arr = np.asarray(arrival_vector, dtype=np.float32).flatten()
        if arr.shape[0] != N_LANES:
            arr = np.resize(arr, N_LANES)

        norm = self._normalise(arr)
        self._history.append(norm)
        if len(self._history) > SEQ_LEN:
            self._history.pop(0)

        self._episode_arrivals.append(arr.copy())

        if self._trained:
            self._h, self._c = self._cell.forward(norm, self._h, self._c)
            self._cell.zero_cache()

    def predict(self) -> np.ndarray:
        if not self._trained or len(self._history) < 4:
            return self._rolling_mean_fallback()
        raw_out    = self._output.forward(self._h)
        prediction = np.clip(raw_out, 0.0, 1.0)
        return prediction.astype(np.float32)

    # ------------------------------------------------------------------
    # Offline training
    # ------------------------------------------------------------------

    def train_offline(
        self,
        arrival_history: Optional[List[np.ndarray]] = None,
        epochs:     int   = EPOCHS,
        batch_size: int   = BATCH,
        lr:         float = LR,
    ) -> float:
        """
        Train on the episode's arrival history using TBPTT.

        BUG FIX: shuffle now uses a seeded numpy RNG derived from the data
        length so results are reproducible when called with the same data.
        """
        data = arrival_history if arrival_history is not None \
               else self._episode_arrivals

        if len(data) < SEQ_LEN + 1:
            return 0.0

        normed = [self._normalise(v) for v in data]
        X, Y   = [], []
        for i in range(len(normed) - SEQ_LEN):
            X.append(np.stack(normed[i: i + SEQ_LEN]))
            Y.append(normed[i + SEQ_LEN])

        if not X:
            return 0.0

        # BUG FIX: seeded RNG so training is reproducible
        rng = np.random.default_rng(seed=len(data))

        total_loss = 0.0
        n_batches  = 0

        for epoch in range(epochs):
            indices = list(range(len(X)))
            # Use numpy rng for reproducible shuffling
            rng.shuffle(indices)

            for b_start in range(0, len(indices), batch_size):
                b_idx      = indices[b_start: b_start + batch_size]
                batch_loss = 0.0

                for idx in b_idx:
                    seq    = X[idx]
                    target = Y[idx]

                    h = np.zeros(HIDDEN, dtype=np.float32)
                    c = np.zeros(HIDDEN, dtype=np.float32)
                    self._cell.zero_cache()

                    # Forward pass — keep cache intact for TBPTT backprop
                    self._cell.zero_cache()
                    for t in range(SEQ_LEN):
                        h, c = self._cell.forward(seq[t], h, c)

                    pred         = self._output.forward(h)
                    pred_clamped = np.clip(pred, 0.0, 1.0)

                    diff       = pred_clamped - target
                    loss       = float(np.mean(diff ** 2))
                    batch_loss += loss

                    # Backprop through time — cache must be intact from forward pass
                    d_pred = (2.0 / N_LANES) * diff
                    dh     = self._output.backward(d_pred)
                    dc     = np.zeros(HIDDEN, dtype=np.float32)

                    # Unroll exactly SEQ_LEN steps matching forward pass
                    for t in range(SEQ_LEN - 1, -1, -1):
                        _, dh, dc = self._cell.backward(dh, dc)

                bs = len(b_idx)
                self._cell.apply_gradients(lr, CLIP, bs)
                self._output.apply_gradients(lr, CLIP, bs)

                total_loss += batch_loss / max(bs, 1)
                n_batches  += 1

        avg_loss      = total_loss / max(n_batches, 1)
        self._trained = True
        self._save_weights()
        return avg_loss

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _save_weights(self) -> None:
        """Atomic write — temp file + rename to avoid corrupt JSON."""
        try:
            payload = {
                "cell":    self._cell.to_dict(),
                "output":  self._output.to_dict(),
                "trained": True,
                "version": 1,
            }
            dirpath = os.path.dirname(self._weights_path)
            os.makedirs(dirpath, exist_ok=True)

            # Write to temp file in same directory, then rename atomically
            fd, tmp_path = tempfile.mkstemp(dir=dirpath, suffix=".json.tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(payload, f)
                os.replace(tmp_path, self._weights_path)
            except Exception:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
        except Exception as e:
            print(f"[LSTMPredictor] Weight save failed: {e}")

    def _load_weights(self) -> None:
        try:
            if not os.path.exists(self._weights_path):
                return
            with open(self._weights_path, "r") as f:
                payload = json.load(f)
            if payload.get("version", 0) != 1:
                return
            self._cell    = _LSTMCell.from_dict(payload["cell"])
            self._output  = _LinearLayer.from_dict(payload["output"])
            self._trained = bool(payload.get("trained", False))
        except Exception as e:
            print(f"[LSTMPredictor] Weight load failed (starting fresh): {e}")
            self._trained = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _normalise(self, v: np.ndarray) -> np.ndarray:
        mx = float(np.max(v))
        if mx < 1e-6:
            return np.zeros(N_LANES, dtype=np.float32)
        return (v / mx).astype(np.float32)

    def _rolling_mean_fallback(self) -> np.ndarray:
        if not self._history:
            return np.zeros(N_LANES, dtype=np.float32)
        return np.mean(np.stack(self._history), axis=0).astype(np.float32)

    def __repr__(self) -> str:
        return (
            f"LSTMPredictor("
            f"trained={self._trained}, "
            f"history_len={len(self._history)}, "
            f"episode_steps={len(self._episode_arrivals)})"
        )