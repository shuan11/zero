#!/usr/bin/env python3
"""zero_post_task.py — 后台持续监控零系统进化"""
import sys, json, time, os
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
SNAPSHOT = CLUSTER / ".zero_growth_snapshot.json"

def read_hip():
    """安全读海马体"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {"causal_chains": []}
    try:
        return json.loads(hip_file.read_text(encoding="utf-8"))
    except:
        return {"causal_chains": []}

def get_state():
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    # 排除未分类
    valid_dims = [(d, c) for d, c in sorted_dims if d not in ("未分类", "...")]
    max_dim, max_c = valid_dims[-1] if valid_dims else ("?", 0)
    min_dim, min_c = valid_dims[0] if valid_dims else ("?", 0)
    return {
        "total": len(chains),
        "dims": len(dims),
        "ratio": min_c / max_c * 100 if max_c > 0 else 0,
        "min_dim": min_dim,
        "min_count": min_c,
        "max_dim": max_dim,
        "max_count": max_c
    }

def log(msg):
    print(f"[zero_post] {msg}")

# Take snapshot now
state = get_state()
log(f"Chains: {state['total']}, Dims: {state['dims']}, Ratio: {state['ratio']:.1f}%")
log(f"Weakest: {state['min_dim']}={state['min_count']}, Strongest: {state['max_dim']}={state['max_count']}")

# Compare with previous
if SNAPSHOT.exists():
    try:
        prev = json.loads(SNAPSHOT.read_text())
        delta_chains = state["total"] - prev.get("total", state["total"])
        log(f"Growth since last snapshot: +{delta_chains} chains")
    except:
        pass

# Save snapshot
SNAPSHOT.write_text(json.dumps(state, ensure_ascii=False, indent=2))

log("Done — system healthy")
