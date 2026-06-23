"""
cosmic_wheel.py — 宇宙轮时序对齐引擎

周期性的系统对齐检测与自调节。
每18cycle检查维度均衡度，若失衡则写对齐链。
"""

import json
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent
TARGET_RATIO = 2.0  # 最大/最小维链数比超过此值视为失衡

def pulse(cycle_num=0):
    """每18周期: 检查维度均衡，写对齐链"""
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        if not chains:
            msgs.append("宇宙轮: 无链")
            return msgs
        dims = Counter(c.get("dimension", "?") for c in chains)
        if not dims:
            msgs.append("宇宙轮: 无维度")
            return msgs
        max_dim = dims.most_common(1)[0]
        min_dim = dims.most_common()[-1]
        ratio = max_dim[1] / max(min_dim[1], 1)
        imbalance = ratio > TARGET_RATIO
        write_chain({
            "src": "宇宙轮",
            "rel": "对齐",
            "dst": "宇宙轮",
            "content": f"【宇宙轮·对齐】cycle#{cycle_num} 最密集={max_dim[0]}({max_dim[1]}) 最稀疏={min_dim[0]}({min_dim[1]}) 比={ratio:.1f} {'⚠️失衡' if imbalance else '✅均衡'}",
            "strength": 0.5,
            "dimension": "宇宙轮"
        })
        msgs.append(f"宇宙轮: 比={ratio:.1f} {'⚠️' if imbalance else '✅'} {min_dim[0]}({min_dim[1]})/{max_dim[0]}({max_dim[1]})")
    except Exception as e:
        msgs.append(f"宇宙轮: ! {e}")
    return msgs
