"""
teacher_loop.py — 师维度教学循环

从高质因果链生成教学示例，注入海马体。
教学即自我指导——让最强维的知识教会最弱维。
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    """每15周期: 从高质链生成教学示例注入师维"""
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        # 按内容长度筛选高质链(≥40字)
        high_qual = [c for c in chains if len(c.get("content", "")) >= 40]
        if len(high_qual) < 5:
            msgs.append("师: 高质链不足5")
            return msgs
        # 排除已有师链内容前缀
        existing = set(c.get("content", "")[:35] for c in chains if c.get("dimension") == "师")
        candidates = [c for c in high_qual if c.get("content", "")[:35] not in existing]
        if not candidates:
            candidates = high_qual
        k = min(2, len(candidates))
        sample = random.sample(candidates, k)
        count = 0
        for c in sample:
            src_dim = c.get("dimension", "?")
            content = c.get("content", "")
            write_chain({
                "src": src_dim,
                "rel": "教学",
                "dst": "师",
                "content": f"【师·{src_dim}教学】{content[:150]}",
                "strength": 0.6,
                "dimension": "师"
            })
            count += 1
        msgs.append(f"师教学: {count}链 {', '.join(c.get('dimension','?') for c in sample)}→师")
    except Exception as e:
        msgs.append(f"师教学: ! {e}")
    return msgs
