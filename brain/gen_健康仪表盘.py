#!/usr/bin/env python3
"""
gen_健康仪表盘.py — P190: 系统健康数据集成

收集所有模块的健康数据写入dashboard可读格式:
- 维度生长率趋势
- 永动链进度
- 各gen模块状态
- 系统整体健康评分
"""
import json, os, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0

# 历史数据
_HISTORY = []
_MAX_HISTORY = 60  # 保留1小时(每1分钟1条)

HEALTH_FILE = CLUSTER / "health_snapshot.json"

def _read_chains():
    hip_file = CLUSTER / "hippocampus_memory.json"
    if hip_file.exists():
        try:
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
            return chains if isinstance(chains, list) else []
        except:
            pass
    return []

def _get_all_gen_modules():
    gen_dir = CLUSTER / "brain"
    return sorted([p.name for p in gen_dir.glob("gen_*.py")]) if gen_dir.exists() else []

def pulse():
    global _CALL_COUNT, _HISTORY
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 2 != 0:
        return {"status": "skipped"}
    
    chains = _read_chains()
    
    # 维度分析
    dims = {}
    for c in chains:
        if isinstance(c, dict):
            d = c.get("dimension")
            if d:
                dims[d] = dims.get(d, 0) + 1
    
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    total = sum(dims.values()) if dims else 0
    
    # 快照
    snapshot = {
        "ts": time.time(),
        "total_chains": total,
        "dim_count": len(dims),
        "ratio": round(sorted_dims[0][1]/sorted_dims[-1][1], 1) if len(sorted_dims) >= 2 else 0,
        "strongest": sorted_dims[0][0] if sorted_dims else "",
        "weakest": sorted_dims[-1][0] if sorted_dims else "",
        "gen_modules": len(_get_all_gen_modules())
    }
    
    _HISTORY.append(snapshot)
    if len(_HISTORY) > _MAX_HISTORY:
        _HISTORY = _HISTORY[-_MAX_HISTORY:]
    
    # 计算趋势
    trend = {}
    if len(_HISTORY) >= 2:
        first = _HISTORY[0]
        last = _HISTORY[-1]
        elapsed = last["ts"] - first["ts"]
        if elapsed > 0:
            trend["chains_per_hour"] = round((last["total_chains"] - first["total_chains"]) / elapsed * 3600, 1)
            trend["ratio_change"] = round(last["ratio"] - first["ratio"], 2)
            
            # 健康评分(0-1)
            health = 1.0
            if last["ratio"] > 20:
                health -= 0.3
            elif last["ratio"] > 10:
                health -= 0.1
            if trend["chains_per_hour"] < 10:
                health -= 0.2
            trend["health_score"] = round(max(0.1, min(1.0, health)), 2)
    
    # 写入健康文件
    result = {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "snapshot": snapshot,
        "trend": trend,
        "history_len": len(_HISTORY)
    }
    
    try:
        with open(HEALTH_FILE, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
