"""
engineer_术.py — 术维度引擎

从触类旁通链提取类比模式，映射为 术(方法/技术) 链。
触类旁通发现模式，术将其方法化。
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    """每周期: 从触类旁通提取模式映射到术链"""
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        # 取触类旁通链
        tlbt = [c for c in chains if c.get("dimension") == "触类旁通"]
        if len(tlbt) < 5:
            msgs.append("术: 触类旁通链不足5")
            return msgs
        # 取未映射到术的链
        existing_shu = set(c.get("content", "")[:40] for c in chains if c.get("dimension") == "术")
        candidates = [c for c in tlbt if c.get("content", "")[:40] not in existing_shu]
        if not candidates:
            candidates = tlbt
        # 取2-4条
        k = min(3, len(candidates))
        sample = random.sample(candidates, k)
        count = 0
        for c in sample:
            content = c.get("content", "")
            if not content or len(content) < 15:
                continue
            write_chain({
                "src": "触类旁通",
                "rel": "方法化",
                "dst": "术",
                "content": f"【术·触类旁通】{content[:120]}",
                "strength": 0.55,
                "dimension": "术"
            })
            count += 1
        msgs.append(f"术引擎: {count}链 触类旁通→术")
    except Exception as e:
        msgs.append(f"术引擎: ! {e}")
    return msgs
