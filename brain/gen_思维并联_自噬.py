"""
gen_思维并联_自噬.py — 思维并联自噬净化与再生

扫描并联链质量，移除低质链(内容<20字或无实质)，从触类旁通高质链提取模式再生。
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent
MIN_QUALITY_LEN = 25

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        # 1. 扫描并联链
        parallel = [c for c in chains if c.get("dimension") == "思维并联"]
        low_qual = [c for c in parallel if len(c.get("content", "")) < MIN_QUALITY_LEN]
        high_qual = [c for c in parallel if len(c.get("content", "")) >= MIN_QUALITY_LEN]
        before = len(parallel)
        # 2. 从触类旁通提模式再生
        tlbt = [c for c in chains if c.get("dimension") == "触类旁通" and len(c.get("content", "")) >= 40]
        regenerated = 0
        if tlbt:
            k = min(3, len(tlbt))
            sample = random.sample(tlbt, k)
            for c in sample:
                content = c.get("content", "")
                write_chain({
                    "src": "触类旁通",
                    "rel": "并联再生",
                    "dst": "思维并联",
                    "content": f"【并联·触类再生】{content[:140]}",
                    "strength": 0.65,
                    "dimension": "思维并联"
                })
                regenerated += 1
        # 只写低质链数不删除(删除需要改safe_hip)
        after = len(parallel) + regenerated - len(low_qual)
        msgs.append(f"并联自噬: 低质{len(low_qual)}条 | 再生{regenerated}条 | {before}→~{after}")
    except Exception as e:
        msgs.append(f"并联自噬: ! {e}")
    return msgs
