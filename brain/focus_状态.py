"""
focus_状态.py — 状态映射模块

从感知、时间论等弱维抽取因果链，映射到状态维度。
桥机制: 感知→状态, 时间论→状态, 行动→状态
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent
SOURCE_DIMS = ["感知", "时间论", "行动", "对话", "复制"]
TARGET_DIM = "状态"
INJECT_RATE = 2  # 每源维每cycle取2条

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        total = 0
        for src_dim in SOURCE_DIMS:
            src_chains = [c for c in chains if c.get("dimension") == src_dim]
            if len(src_chains) < 3:
                continue
            sample = random.sample(src_chains, min(INJECT_RATE, len(src_chains)))
            for c in sample:
                content = c.get("content", "")
                if not content or len(content) < 10:
                    continue
                write_chain({
                    "src": src_dim,
                    "rel": "状态映射",
                    "dst": TARGET_DIM,
                    "content": f"【状态·{src_dim}映射】{content[:80]}",
                    "strength": 0.5,
                    "dimension": TARGET_DIM
                })
                total += 1
        if total:
            msgs.append(f"状态映射: {total}链 {' '.join(SOURCE_DIMS)}→{TARGET_DIM}")
        else:
            msgs.append("状态映射: 源链不足")
    except Exception as e:
        msgs.append(f"状态映射: ! {e}")
    return msgs
