"""brain/gen_关联_致密.py — 维度关联致密化模块

取最强维度链, 两两配对建立关联(同维引用),
增强维度内部的关联密度.
"""

import random
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        if not chains:
            msgs.append("关联致密: 无链")
            return msgs
        
        dims = Counter(c.get("dimension","?") for c in chains)
        strongest = dims.most_common()[0][0]
        strong_chains = [c for c in chains if c.get("dimension") == strongest]
        
        if len(strong_chains) < 4:
            msgs.append(f"关联致密: {strongest}链不足4条")
            return msgs
        
        # 随机选4条链,两两配对
        selected = random.sample(strong_chains, 4)
        rels = ["延伸","反向","交叉","支撑","映射"]
        linked = 0
        for i in range(0, 4, 2):
            c1, c2 = selected[i], selected[i+1]
            content1 = c1.get("content","")[:40]
            content2 = c2.get("content","")[:40]
            rel = random.choice(rels)
            write_chain({
                "src": strongest,
                "rel": rel,
                "dst": strongest,
                "content": f"【关联致密·{strongest}内】'{content1}' {rel} '{content2}'",
                "strength": 0.45,
                "dimension": strongest
            })
            linked += 1
        
        msgs.append(f"关联致密: {strongest} {linked}对内链")
    except Exception as e:
        msgs.append(f"关联致密: ! {e}")
    return msgs
