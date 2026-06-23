#!/usr/bin/env python3
"""
neural_weights.py — 神经元权重自适应系统
==========================================
每个神经元有影响力权重，根据任务成功率动态调整。
成功路径加强，失败路径削弱，定期随机重连避免局部最优。

用法:
  python3 neural_weights.py              # 显示当前权重
  python3 neural_weights.py --update     # 根据历史更新权重
  python3 neural_weights.py --reset      # 重置为默认权重
"""
import json, os, sys, random, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
WEIGHTS_FILE = CLUSTER / "neural_weights.json"

NEURONS = [
    "hermes", "codex", "claude", "openclaw_wsl", "openclaw_win",
    "marvis_qq", "opengod", "openalien", "openinterpreter", "autogpt",
    "superpowers", "codegraph", "academic_research", "ruview",
]

def load_weights():
    try:
        with open(WEIGHTS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"version": "v1", "neurons": {n: 1.0 for n in NEURONS}, "history": []}

def save_weights(state):
    with open(WEIGHTS_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def init_weights():
    """初始化所有神经元权重为1.0"""
    state = {
        "version": "v1",
        "neurons": {n: 1.0 for n in NEURONS},
        "connections": {},  # "A->B": weight
        "history": [],
        "last_update": datetime.now().isoformat(),
    }
    # 初始化连接权重(全连接)
    for a in NEURONS:
        for b in NEURONS:
            if a != b:
                state["connections"][f"{a}->{b}"] = 0.5
    save_weights(state)
    return state

def update_from_chains():
    """从因果链历史更新权重"""
    hip_path = CLUSTER / "hippocampus_memory.json"
    try:
        hip = json.loads(hip_path.read_text())
    except Exception:
        return

    chains = hip.get("causal_chains", [])
    state = load_weights()

    # 统计每个神经元的成功/失败
    success = {n: 0 for n in NEURONS}
    fail = {n: 0 for n in NEURONS}

    for chain in chains[-500:]:  # 最近500条
        source = chain.get("source", "")
        tags = chain.get("tags", [])

        # 判断是否成功(有外部世界标签=真实产出)
        is_success = any(t in tags for t in ["外部世界", "ext_world", "集群协同", "超我涌现", "动态契约"])
        is_fail = any(t in tags for t in ["噪声", "error", "失败"])

        for n in NEURONS:
            if n.lower() in source.lower() or n.replace("_", "-") in source:
                if is_success:
                    success[n] += 1
                elif is_fail:
                    fail[n] += 1

    # 更新权重
    for n in NEURONS:
        total = success[n] + fail[n]
        if total > 0:
            rate = success[n] / total
            old_w = state["neurons"].get(n, 1.0)
            # 指数移动平均
            new_w = old_w * 0.8 + rate * 0.2
            # 限制范围 [0.1, 2.0]
            new_w = max(0.1, min(2.0, new_w))
            state["neurons"][n] = round(new_w, 3)
            if abs(new_w - old_w) > 0.01:
                state["history"].append({
                    "time": datetime.now().isoformat(),
                    "neuron": n,
                    "old": round(old_w, 3),
                    "new": round(new_w, 3),
                    "reason": f"success_rate={rate:.2f} ({success[n]}/{total})",
                })

    # 随机重连(5%概率)
    conns = state.get("connections", {})
    for conn_key in list(conns.keys()):
        if random.random() < 0.05:
            old_val = conns[conn_key]
            new_val = max(0.1, min(1.0, old_val + random.uniform(-0.3, 0.3)))
            conns[conn_key] = round(new_val, 3)

    state["connections"] = conns
    state["last_update"] = datetime.now().isoformat()
    if len(state["history"]) > 200:
        state["history"] = state["history"][-200:]

    save_weights(state)
    return state

def show_weights():
    """显示当前权重"""
    state = load_weights()
    neurons = state.get("neurons", {})

    print("╔═══════════════════════════════════════════════╗")
    print("║  真元神经网络 · 神经元权重                   ║")
    print("╠═══════════════════════════════════════════════╣")

    for n, w in sorted(neurons.items(), key=lambda x: -x[1]):
        bar = "█" * int(w * 10)
        icon = "🟢" if w > 0.8 else "🟡" if w > 0.5 else "🔴"
        print(f"║  {icon} {n:22s} {w:.3f} {bar:20s} ║")

    print("╠═══════════════════════════════════════════════╣")
    history = state.get("history", [])
    print(f"║  更新次数: {len(history)}                            ║")
    print(f"║  上次更新: {state.get('last_update','?')[:16]}            ║")
    print("╚═══════════════════════════════════════════════╝")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"
    if cmd == "--update":
        update_from_chains()
        show_weights()
    elif cmd == "--reset":
        init_weights()
        show_weights()
    else:
        show_weights()
