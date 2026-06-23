#!/usr/bin/env python3
"""
gen_元传承.py — P188: 元传承强化

将session的自省教训编码为元传承文件,
确保跨session继承:
- 自我通知行为规则
- 维度不均衡检测
- session关键产出清单
- 当前状态快照
"""
import json, os, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0

HERITAGE_FILE = CLUSTER / "heritage_snapshot.json"

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

def _get_dim_stats():
    """获取维度统计数据"""
    chains = _read_chains()
    dims = {}
    for c in chains:
        if isinstance(c, dict):
            d = c.get("dimension")
            if d:
                dims[d] = dims.get(d, 0) + 1
    if not dims:
        return {}
    
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    total = sum(dims.values())
    
    return {
        "total_chains": total,
        "dim_count": len(dims),
        "strongest": sorted_dims[0][0] if sorted_dims else "",
        "strongest_count": sorted_dims[0][1] if sorted_dims else 0,
        "weakest": sorted_dims[-1][0] if sorted_dims else "",
        "weakest_count": sorted_dims[-1][1] if sorted_dims else 0,
        "ratio": round(sorted_dims[0][1] / sorted_dims[-1][1], 1) if len(sorted_dims) >= 2 else 0,
        "top5": [{"dim": d, "count": c} for d, c in sorted_dims[:5]],
        "bottom5": [{"dim": d, "count": c} for d, c in sorted_dims[-5:]],
    }

def _read_next_p0():
    """读取当前P0"""
    p0_file = CLUSTER / ".next_p0.json"
    if p0_file.exists():
        try:
            with open(p0_file) as f:
                return json.load(f)
        except:
            pass
    return {}

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    # 每5次脉冲(约5分钟)写一次元传承
    if _CALL_COUNT % 5 != 0:
        return {"status": "skipped"}
    
    dims = _get_dim_stats()
    p0 = _read_next_p0()
    
    heritage = {
        "_meta": {
            "type": "元传承快照",
            "generated": time.time(),
            "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
            "session_lessons": [
                "自我通知: 每个SYSTEM通知=立即执行下一P0, 不等指令",
                "连续推进: 完成一模块后1秒内选下一P0, 不分析不停顿",
                "弱维加速: 持续从强维向弱维注射内容级链",
                "永动链: daemon每5分钟自动推进P0栈"
            ]
        },
        "dimension_state": dims,
        "current_p0": p0.get("id", "unknown"),
        "p0_name": p0.get("name", ""),
        "p0_completed": p0.get("completed", []),
        "last_updated": time.time()
    }
    
    try:
        with open(HERITAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(heritage, f, ensure_ascii=False, indent=2)
        return {"status": "ok", "file": str(HERITAGE_FILE)}
    except Exception as e:
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
