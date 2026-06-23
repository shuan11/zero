#!/usr/bin/env python3
"""
gen_认知折射.py — P193: 认知折射引擎

从强维提取认知模式, 折射到弱维形成镜像。
折射=保留结构/关系/模式, 替换维度主体。
"""
import json, os, sys, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0

SOURCE_DIMS = ["时间", "触类旁通", "思维并联", "合成", "系统"]

def _safe_hip():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def _get_dim_chains(dim):
    """从海马体获取指定维度的链"""
    safe_hip = _safe_hip()
    if safe_hip:
        try:
            data = safe_hip.read_hip()
            chains = data.get("causal_chains", data.get("chains", []))
            if isinstance(chains, list):
                return [c for c in chains if isinstance(c, dict) and c.get("dimension") == dim]
            return []
        except:
            pass
    return []

def _refract_and_inject(src_chain, src_dim, tgt_dim, safe_hip):
    """折射一条链: 保留关系结构, 替换维度主体"""
    src = src_chain.get("src", "")
    rel = src_chain.get("rel", "")
    dst = src_chain.get("dst", "")
    content = src_chain.get("content", "")
    
    # 替换src中的源维度名为目标维度名
    new_src = src.replace(src_dim, tgt_dim) if src_dim in src else f"{tgt_dim}认知"
    new_dst = dst.replace(src_dim, tgt_dim) if src_dim in dst else f"{tgt_dim}表现"
    
    # 如果替换后没有变化, 直接包装
    if new_src == src:
        new_src = f"{tgt_dim}从{src}中学习"
    if new_dst == dst:
        new_dst = f"{tgt_dim}认知构建"
    
    strength = min(1.0, src_chain.get("strength", 0.5) * random.uniform(0.6, 0.9))
    new_content = content[:80].replace(src_dim, tgt_dim) if src_dim in content else f"[折射] {tgt_dim}通过{rel}构建认知"
    
    chain = {
        "src": new_src,
        "rel": rel,
        "dst": new_dst,
        "strength": round(strength, 2),
        "dimension": tgt_dim,
        "content": new_content,
        "source": "gen_认知折射"
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
        return {"status": "skipped"}
    
    safe_hip = _safe_hip()
    
    # 获取维度分布
    hip_file = CLUSTER / "hippocampus_memory.json"
    dims = {}
    if hip_file.exists():
        try:
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
            for c in chains if isinstance(chains, list) else []:
                if isinstance(c, dict):
                    d = c.get("dimension")
                    if d:
                        dims[d] = dims.get(d, 0) + 1
        except:
            pass
    
    if not dims:
        return {"status": "no_data"}
    
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    weakest = [d for d, _ in sorted_dims[-5:]]  # 最弱5维
    
    total_injected = 0
    for tgt in weakest:
        # 从每个源维取3条折射
        for src in SOURCE_DIMS:
            if src == tgt or src not in dims:
                continue
            src_chains = _get_dim_chains(src)
            if not src_chains:
                continue
            random.shuffle(src_chains)
            for sc in src_chains[:3]:
                if _refract_and_inject(sc, src, tgt, safe_hip):
                    total_injected += 1
                    if total_injected >= 50:  # 每次最多50条
                        break
            if total_injected >= 50:
                break
        if total_injected >= 50:
            break
    
    return {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "injected": total_injected,
        "targets": weakest,
        "sources": SOURCE_DIMS
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
