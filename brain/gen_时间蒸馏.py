#!/usr/bin/env python3
"""
gen_时间蒸馏.py — P194: 时间维度蒸馏引擎

时间维(2943链)是系统的极端强维(比其他维多11.6x)。
蒸馏=从时间维提取认知模式, 按比例注入所有其他弱维。
每次聚焦最弱5维, 从时间维提取10条有代表性链做结构映射。
"""
import json, os, sys, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_MAX_INJECT = 30

def _safe_hip():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def _get_dim_dist():
    """获取全维分布"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {}
    try:
        with open(hip_file) as f:
            data = json.load(f)
        chains = data.get("causal_chains", data.get("chains", []))
        dims = {}
        for c in chains if isinstance(chains, list) else []:
            if isinstance(c, dict):
                d = c.get("dimension")
                if d:
                    dims[d] = dims.get(d, 0) + 1
        return dims
    except:
        return {}

def _get_dim_chains(dim, max_c=50):
    """从海马体获取指定维度的链"""
    safe_hip = _safe_hip()
    if safe_hip:
        try:
            data = safe_hip.read_hip()
            chains = data.get("causal_chains", data.get("chains", []))
            if isinstance(chains, list):
                return [c for c in chains if isinstance(c, dict) and c.get("dimension") == dim][:max_c]
        except:
            pass
    return []

def _distill_chain(src_chain, src_dim, tgt_dim, safe_hip):
    """蒸馏: 保留时间认知的结构骨架, 映射到目标维"""
    rel = src_chain.get("rel", "")
    content = src_chain.get("content", "")
    strength = src_chain.get("strength", 0.5)
    
    # 映射rel: 如果rel包含时间概念, 映射为目标维关系
    time_keywords = ["时间", "持续", "演变", "递进", "顺序", "同时", "过程", "周期", "阶段"]
    for kw in time_keywords:
        if kw in rel:
            rel = rel.replace(kw, tgt_dim)
            break
    
    # 生成新链
    new_content = f"[蒸馏] 从时间维度提炼: {content[:60]}"
    if len(content) > 60:
        new_content += "..."
    new_content += f"→映射为{tgt_dim}维度认知"
    
    src_base = content.split("→")[0] if "→" in content else content[:30]
    chain = {
        "src": f"时间蒸馏:{src_base}",
        "rel": rel,
        "dst": f"{tgt_dim}认知",
        "strength": round(strength * random.uniform(0.5, 0.8), 2),
        "dimension": tgt_dim,
        "content": new_content[:120],
        "source": "gen_时间蒸馏"
    }
    
    if safe_hip:
        try:
            safe_hip.write_chain(chain)
            return True
        except:
            pass
    return False

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 2 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    dims = _get_dim_dist()
    if not dims:
        return {"status": "no_data"}
    
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    strongest = sorted_dims[0][0]  # 时间
    
    # 目标: 最弱5维 + 随机5维
    weakest = [d for d, _ in sorted_dims[-5:]]
    random.shuffle(weakest)
    
    # 从强维取样本
    time_chains = _get_dim_chains(strongest, 30)
    if not time_chains:
        return {"status": "no_source", "strongest": strongest}
    
    safe_hip = _safe_hip()
    if not safe_hip:
        return {"status": "no_safe_hip"}
    
    random.shuffle(time_chains)
    total = 0
    
    for tgt in weakest:
        for sc in time_chains[:5]:
            if _distill_chain(sc, strongest, tgt, safe_hip):
                total += 1
                if total >= _MAX_INJECT:
                    break
        if total >= _MAX_INJECT:
            break
    
    return {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "distilled": total,
        "source": strongest,
        "targets": weakest
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
