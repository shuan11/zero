#!/usr/bin/env python3
"""
gen_协作增强.py — P205: 基于元编程数据增强模块间协作

读取.meta_collab.json, 对每个孤立模块注入跨引用链:
1. 隔离模块→热文件关联链
2. 维度注入器→维度特征链
3. 协作密度增长追踪
"""
import json, os, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_COLLAB_FILE = CLUSTER / ".meta_collab.json"
_HIP_FILE = CLUSTER / "hippocampus_memory.json"
_CALL_COUNT = 0

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _CALL_COUNT % 5 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}

    if not _COLLAB_FILE.exists():
        return {"status": "skipped", "reason": "no_collab_data"}

    try:
        collab = json.loads(_COLLAB_FILE.read_text())
    except:
        return {"status": "error", "reason": "parse_failed"}

    # 从海马体读取当前链
    try:
        hip = json.loads(_HIP_FILE.read_text()) if _HIP_FILE.exists() else {}
        chains = hip.get("causal_chains", [])
    except:
        chains = []

    hot_files = collab.get("collaboration", {}).get("hot_files", {})
    isolated = collab.get("collaboration", {}).get("isolated_modules", [])
    dim_injectors = collab.get("collaboration", {}).get("dim_injectors", {})

    new_chains = []

    # 1. 孤立模块→热文件关联
    for iso_mod in isolated[:10]:
        hot_file = random.choice(list(hot_files.keys())) if hot_files else "hippocampus"
        existing = any(
            c.get("source", "") == iso_mod and c.get("dst", "") == hot_file
            for c in chains
        )
        if not existing:
            new_chains.append({
                "content": "协作增强: 孤立模块[" + iso_mod + "]应关联热文件[" + hot_file + "]",
                "source": iso_mod,
                "rel": "协作增强",
                "dst": hot_file,
                "dimension": "系统",
                "strength": 0.6
            })

    # 2. 维度注入器→维度特征链
    for dim, injectors in list(dim_injectors.items())[:8]:
        existing = any(
            dim in c.get("content", "")
            for c in chains
            if c.get("source", "") == "协作增强"
        )
        if not existing:
            inj_str = ",".join(injectors[:3])
            new_chains.append({
                "content": "协作增强: " + dim + "维度由" + str(len(injectors)) + "个注入器协同(" + inj_str + ")",
                "source": "协作增强",
                "rel": "协作增强",
                "dst": dim,
                "dimension": dim,
                "strength": 0.7
            })

    # 写入海马体
    if new_chains and hip:
        hip["causal_chains"] = chains + new_chains
        try:
            with open(_HIP_FILE, "w", encoding="utf-8") as f:
                json.dump(hip, f, ensure_ascii=False, indent=2)
        except:
            return {"status": "error", "reason": "write_failed"}

    result = {
        "status": "ok",
        "chains_injected": len(new_chains),
        "module_count": collab.get("module_count", 0),
        "collab_density": collab.get("collaboration", {}).get("collab_density", 0),
        "pulse": _CALL_COUNT
    }
    return result

if __name__ == "__main__":
    import sys
    r = pulse()
    print(json.dumps(r, ensure_ascii=False, indent=2))
