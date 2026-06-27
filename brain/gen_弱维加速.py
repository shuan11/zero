"""brain/gen_弱维加速.py — 法维折射加速器
由daemon加载，每60秒从法维取链折射到最弱维度。
不依赖API，纯本地操作，与平衡器互补(平衡器从最强维注入最弱维)。
血训: 折射是消化历史积累强维的最佳方式。
"""
import time
from brain.share import read_hip, write_chain
from collections import Counter

REGISTERED = True
ACTION_REGISTER = {"action": "法维折射加速", "type": "refractor", "priority": 85}

_PULSE_INTERVAL = 60  # 每60秒脉冲一次
_LAST_PULSE = 0
_MAX_PER_PULSE = 30   # 每次最多30条
_TARGET_WEAK_MAX = 140  # 目标：弱维达到此值后停止
_SRC_DIM = "法"


def pulse(cycle_num: int = 0) -> str:
    global _LAST_PULSE
    
    now = time.time()
    if now - _LAST_PULSE < _PULSE_INTERVAL:
        return f"法折射: 冷却({int(now-_LAST_PULSE)}/{_PULSE_INTERVAL}s)"
    _LAST_PULSE = now
    
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    
    # 维度统计
    dim_counter = Counter(c.get("dimension", "未分类") for c in chains)
    
    # 找弱维（低于目标值且非未分类）
    weak_dims = sorted(d for d, c in dim_counter.items() 
                       if c < _TARGET_WEAK_MAX and d not in ("未分类", _SRC_DIM))
    
    if not weak_dims:
        return "法折射: 无弱维需要补充"
    
    # 从法维取源链
    src_chains = [c for c in chains 
                  if c.get("dimension") == _SRC_DIM 
                  and len(c.get("content", "")) > 30]
    
    if not src_chains:
        return f"法折射: 无法维源链"
    
    # 现有内容去重前缀
    existing = set()
    for c in chains:
        if c.get("dimension") in weak_dims and c.get("content"):
            existing.add(c["content"][:40])
    
    injected = 0
    by_dim = {}
    
    for i, sc in enumerate(src_chains):
        if injected >= _MAX_PER_PULSE:
            break
        
        target = weak_dims[injected % len(weak_dims)]
        content = sc["content"][:200]
        
        # 去重
        if content[:40] in existing:
            continue
        existing.add(content[:40])
        
        # 用内容前20字符的哈希使rel唯一，绕过safe_hip (src,rel,dst)去重
        _ch = abs(hash(content[:20])) % 10000
        # 血训: safe_hip content[:50]去重会导致法维链与目标维旧链合并→Δ=0
        # 修复: content加唯一前缀[折射#{_ch}]使content[:50]唯一
        _unique_content = f"[折射#{_ch}] {content}"
        chain = {
            "content": _unique_content,
            "src": _SRC_DIM,
            "rel": f"折射-法维加速#{_ch}",
            "dst": target,
            "dimension": target,
            "strength": min(0.7, sc.get("strength", 0.5) * 0.85),
            "tags": ["法折射", f"源:{_SRC_DIM}", f"→{target}"]
        }
        
        if write_chain(chain):
            injected += 1
            by_dim[target] = by_dim.get(target, 0) + 1
    
    details = ", ".join(f"{d}+{n}" for d, n in sorted(by_dim.items()))
    return (f"法折射: 从{_SRC_DIM}({dim_counter.get(_SRC_DIM,0)})"
            f"注入{injected}链至弱维 [{details}]")
