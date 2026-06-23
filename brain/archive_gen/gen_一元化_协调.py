"""
gen_一元化_协调.py — 一元化协调模块

从各维最新链提取模式, 生成跨维统一链增强耦合.
"""

import json, random
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = Counter(c.get("dimension", "?") for c in chains)
        # 随机选2个维度,各取1条最新链,统一注入
        all_dims = [d for d in dims if d != "一元化" and dims[d] > 0]
        if len(all_dims) < 2:
            msgs.append("一元化: 维度不足2")
            return msgs
        picks = random.sample(all_dims, min(3, len(all_dims)))
        pairs = []
        for i in range(len(picks)-1):
            d1 = picks[i]
            d2 = picks[i+1]
            # 各取1条链
            c1 = random.choice([c for c in chains if c.get("dimension") == d1])
            c2 = random.choice([c for c in chains if c.get("dimension") == d2])
            if c1 and c2:
                content1 = c1.get("content", "")[:60]
                content2 = c2.get("content", "")[:60]
                write_chain({
                    "src": d1,
                    "rel": "统一",
                    "dst": "一元化",
                    "content": f"【一元化·{d1}↔{d2}】{content1} ‖ {content2}",
                    "strength": 0.55,
                    "dimension": "一元化"
                })
                pairs.append(f"{d1}↔{d2}")
        msgs.append(f"一元化: {' | '.join(pairs)}")
    except Exception as e:
        msgs.append(f"一元化: ! {e}")
    return msgs
