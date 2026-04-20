"""
IntelliFlow — Minimal TRL/GRPO Training Script
Fulfills OpenEnv hackathon mandatory training script requirement.
Run this in Colab with GPU runtime.
"""
import os, json, requests, numpy as np
from collections import deque

HOST = os.environ.get("INTELLIFLOW_HOST", "http://localhost:7860")

TASKS   = ["task_grid_steady", "task_grid_rush", "task_grid_crisis"]
N_OBS   = 73
N_ACT   = 5
HIDDEN  = 128
LR      = 1e-3
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
    def __init__(self, obs_dim, n_actions, hidden=HIDDEN):
        self.layers = [
            {"W": np.random.randn(hidden, obs_dim).astype(np.float32) * np.sqrt(2/obs_dim),
             "b": np.zeros(hidden, dtype=np.float32), "activation": "relu"},
            {"W": np.random.randn(hidden, hidden).astype(np.float32) * np.sqrt(2/hidden),
             "b": np.zeros(hidden, dtype=np.float32), "activation": "relu"},
            {"W": np.random.randn(n_actions, hidden).astype(np.float32) * np.sqrt(2/hidden),
             "b": np.zeros(n_actions, dtype=np.float32), "activation": "linear"},
        ]

    def forward(self, x):
        for layer in self.layers:
            x = x @ layer["W"].T + layer["b"]
            if layer["activation"] == "relu":
                x = relu(x)
        return x

    def forward_with_cache(self, x):
        cache = [x]
        for layer in self.layers:
            x = x @ layer["W"].T + layer["b"]
            if layer["activation"] == "relu":
                x = np.maximum(0, x)
            cache.append(x)
        return x, cache

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
    print()

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