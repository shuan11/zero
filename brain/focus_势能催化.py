"""focus_势能催化.py — 势维催化模块

焦点: 势维停滞，嫁接触类旁通催化势能涌现
策略: 从触类旁通(最强67链)抽取高活性模式 → 注入势维(48链)作为催化种子
"""

import json, random, time
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"

def _load_hip():
    try:
        return json.loads(HIP_FILE.read_text())
    except:
        return {"causal_chains": []}

def _write_chain(src, rel, dst, content, dimension="势"):
    from brain.share import write_chain as _wc
    try:
        _wc({"src": src, "rel": rel, "dst": dst, "content": content, "dimension": dimension, "strength": 0.55})
        return True
    except:
        return False

def _extract_high_energy_patterns(chains, target_dim="触类旁通", min_count=3):
    """从目标维度抽取高频模式作为催化种子"""
    target = [c for c in chains if c.get("dimension") == target_dim]
    if len(target) < min_count:
        return []
    # 找rel出现最多的模式
    rels = Counter(c.get("rel", "") for c in target)
    common_rels = [r for r, n in rels.most_common(5) if n >= min_count]
    # 随机取几条链内容作种子
    samples = random.sample(target, min(5, len(target)))
    patterns = []
    for c in samples:
        content = c.get("content", "")
        rel = c.get("rel", "类比")
        if content:
            patterns.append({"content": content[:60], "rel": rel})
    return patterns

def pulse(cycle_num=0):
    """每6周期从触类旁通抽模式→注入势维"""
    if cycle_num % 6 != 0:
        return []
    
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    
    patterns = _extract_high_energy_patterns(chains)
    if not patterns:
        return ["势催化: 触类旁通素材不足"]
    
    injected = 0
    for p in patterns:
        content = f"势能催化: 借触类旁通模式「{p['content']}...」→势维衍生{random.choice(['势能积累','动能转化','势阱突破','势差驱动','位能跃迁'])}"
        ok = _write_chain("势催化", p["rel"], "势维渗透", content)
        if ok:
            injected += 1
    
    return [f"势催化: 从触类旁通抽取{len(patterns)}模式→{injected}条势能链注入"]

if __name__ == "__main__":
    r = pulse(6)
    print("\n".join(r))
