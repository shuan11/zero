"""brain/gen_智慧_整合.py — 智慧整合脉冲

从触类旁通/思考/法维度抽取高质链,
建立类比映射桥注入智慧维度.
"""

import json, random
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        # 从高质源维抽取
        src_dims = ["触类旁通", "思考", "法", "洞察循环"]
        high_quality = []
        for sd in src_dims:
            candidates = [c for c in chains if c.get("dimension") == sd 
                         and len(c.get("content", "")) > 25]
            if candidates:
                high_quality.extend(random.sample(candidates, min(2, len(candidates))))
        if not high_quality:
            msgs.append("智慧整合: 无高质源链")
            return msgs
        for hq in high_quality:
            content = hq.get("content", "")[:60]
            dim = hq.get("dimension", "?")
            write_chain({
                "src": dim,
                "rel": "类比→智慧",
                "dst": "智慧",
                "content": f"【智慧整合·{dim}→智慧】{content}",
                "strength": 0.55,
                "dimension": "智慧"
            })
        msgs.append(f"智慧整合: {len(high_quality)}条映射桥")
    except Exception as e:
        msgs.append(f"智慧整合: ! {e}")
    return msgs
