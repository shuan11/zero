#!/usr/bin/env python3
"""
gen_维度趋势.py — P201: 维度增长趋势跟踪

逐周期记录每维链数, 计算增长率/加速度/饱和信号。
输出到.trend_data.json供仪表盘消费。
识别: 哪些维在加速增长, 哪些已饱和。
"""
import json, os, sys, time
from pathlib import Path
from collections import defaultdict

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_TREND_FILE = CLUSTER / ".trend_data.json"
_MAX_HISTORY = 50  # 保留最近50个快照

def _get_dim_dist():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        if isinstance(chains, list):
            dims = defaultdict(int)
            for c in chains:
                d = c.get("dimension") if isinstance(c, dict) else None
                if d:
                    dims[d] += 1
            return dict(dims)
    except:
        pass
    return {}

def _load_history():
    if _TREND_FILE.exists():
        try:
            return json.loads(_TREND_FILE.read_text())
        except:
            pass
    return {"snapshots": [], "version": 2}

def _save_history(data):
    try:
        with open(_TREND_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except:
        pass

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 4 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    dims = _get_dim_dist()
    if not dims:
        return {"status": "no_dim_data"}
    
    history = _load_history()
    now = time.time()
    
    # 追加当前快照
    snapshot = {
        "t": now,
        "t_str": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "dims": dims,
        "total": sum(dims.values()),
        "dim_count": len(dims)
    }
    history["snapshots"].append(snapshot)
    
    # 截断历史
    if len(history["snapshots"]) > _MAX_HISTORY:
        history["snapshots"] = history["snapshots"][-_MAX_HISTORY:]
    
    # 计算趋势
    snaps = history["snapshots"]
    trends = {}
    if len(snaps) >= 3:
        all_dims = set()
        for s in snaps:
            all_dims.update(s.get("dims", {}).keys())
        
        for dim in all_dims:
            values = [(s["t"], s["dims"].get(dim, 0)) for s in snaps if dim in s.get("dims", {})]
            if len(values) < 3:
                continue
            
            # 计算总增长率
            first_val = values[0][1]
            last_val = values[-1][1]
            duration = values[-1][0] - values[0][0]
            
            if first_val > 0 and duration > 0:
                growth_rate = (last_val - first_val) / first_val / (duration / 3600) * 100  # %/h
            else:
                growth_rate = 0
            
            # 计算近3个点加速度
            if len(values) >= 4:
                mid_idx = len(values) // 2
                early_vals = [(v[0], v[1]) for v in values[:mid_idx]]
                late_vals = [(v[0], v[1]) for v in values[mid_idx:]]
                
                early_rate = (early_vals[-1][1] - early_vals[0][1]) / max(early_vals[0][1], 1)
                late_rate = (late_vals[-1][1] - late_vals[0][1]) / max(late_vals[0][1], 1)
                acceleration = late_rate - early_rate
            else:
                acceleration = 0
            
            # 饱和信号: 增长率趋近0但链数高
            saturation = growth_rate < 1 and last_val > 100
            
            trends[dim] = {
                "current": last_val,
                "growth_rate_pct_h": round(growth_rate, 2),
                "acceleration": round(acceleration, 4),
                "saturated": saturation,
                "data_points": len(values)
            }
    
    history["trends"] = trends
    history["last_update"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    
    _save_history(history)
    
    # 提取加速和饱和列表
    accelerating = {d: info for d, info in trends.items() if info["acceleration"] > 0.05}
    saturating = {d: info for d, info in trends.items() if info.get("saturated")}
    
    return {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "snapshots": len(snaps),
        "accelerating": list(accelerating.keys())[:5],
        "saturating": list(saturating.keys())[:5],
        "total_chains": sum(dims.values())
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
