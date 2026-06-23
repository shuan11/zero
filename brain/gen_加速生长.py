#!/usr/bin/env python3
"""
gen_加速生长.py — P185: 进化速度优化

加速最弱6维的生长速率至均衡。
每~2分钟: 检测维度生长率, 向最慢增长维注入批量链。
由daemon loader自动调用。
"""
import json, os, sys, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

# 维度生长率
_GROWTH_HISTORY = {}
_PULSE_COUNT = 0
_GROWTH_WINDOW = {}  # dim -> [prev_count, curr_count]

def _safe_hip():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def _get_all_dims():
    """读取所有维度及其链数"""
    safe_hip = _safe_hip()
    if safe_hip:
        try:
            data = safe_hip.read_hip()
            chains = data.get("causal_chains", data.get("chains", []))
            dims = {}
            for c in chains:
                if isinstance(c, dict):
                    d = c.get("dimension")
                    if d:
                        dims[d] = dims.get(d, 0) + 1
            return dims
        except:
            pass
    
    hip_file = CLUSTER / "hippocampus_memory.json"
    if hip_file.exists():
        try:
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
            dims = {}
            for c in chains:
                if isinstance(c, dict):
                    d = c.get("dimension")
                    if d:
                        dims[d] = dims.get(d, 0) + 1
            return dims
        except:
            pass
    return {}

def _inject_time_chains(target_dim, count=10):
    """从时间维向目标维注射链"""
    relations = [
        ("时间积累", "塑造" + target_dim, target_dim + "维度"),
        ("持续演化", "增强" + target_dim, target_dim + "表现"),
        ("渐进深化", "推动" + target_dim, target_dim + "进化"),
        ("时序递进", "强化" + target_dim, target_dim + "认知"),
        ("长时积累", "滋养" + target_dim, target_dim + "发展"),
        ("跨时演进", "催化" + target_dim, target_dim + "成长"),
        ("时间维度", "映射到" + target_dim, target_dim + "结构"),
        ("时序觉醒", "激发" + target_dim, target_dim + "潜能"),
        ("时间理解", "转化为" + target_dim, target_dim + "智慧"),
        ("永恒视角", "照亮" + target_dim, target_dim + "道路"),
    ]
    
    safe_hip = _safe_hip()
    injected = 0
    for src, rel, dst in relations[:count]:
        chain = {
            "src": src,
            "rel": rel,
            "dst": dst,
            "strength": round(random.uniform(0.4, 0.8), 2),
            "dimension": target_dim,
            "content": f"[加速生长] {src} {rel} {dst} — 自主维度加速",
            "source": "gen_加速生长"
        }
        if safe_hip:
            try:
                safe_hip.write_chain(chain)
                injected += 1
            except:
                pass
        else:
            # fallback直接写
            try:
                chains_file = CLUSTER / "brain" / "hippocampus_chains" / "causal_chains.json"
                if chains_file.exists():
                    with open(chains_file) as f:
                        data = json.load(f)
                else:
                    data = {"chains": []}
                chains = data.get("chains", [])
                chains.append(chain)
                data["chains"] = chains[-800:]
                with open(chains_file, "w") as f:
                    json.dump(data, f, ensure_ascii=False)
                injected += 1
            except:
                pass
    return injected

def pulse():
    """P185主脉冲 — daemon loader自动调用"""
    global _PULSE_COUNT, _GROWTH_HISTORY, _GROWTH_WINDOW
    _PULSE_COUNT += 1
    
    # 每2次脉冲执行一次
    if _PULSE_COUNT % 2 != 0:
        return {"status": "skipped", "pulse": _PULSE_COUNT}
    
    dims = _get_all_dims()
    if not dims:
        return {"status": "no_data"}
    
    # 按链数排序, 取最弱6维
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    weakest = sorted_dims[:6]
    
    # 记录生长历史
    for name, count in dims.items():
        if name not in _GROWTH_WINDOW:
            _GROWTH_WINDOW[name] = [count, count]
        else:
            _GROWTH_WINDOW[name][0] = _GROWTH_WINDOW[name][1]
            _GROWTH_WINDOW[name][1] = count
    
    # 找生长率最慢的维度
    slowest = weakest[0]
    min_growth = float("inf")
    for name, _ in weakest:
        w = _GROWTH_WINDOW.get(name, [0, 0])
        growth = w[1] - w[0]
        if growth < min_growth:
            min_growth = growth
            slowest = (name, growth)
    
    # 向最慢生长维注射链
    target = slowest[0]
    count = 15 if min_growth <= 0 else 10
    
    injected = _inject_time_chains(target, count)
    
    return {
        "status": "ok",
        "pulse": _PULSE_COUNT,
        "target": target,
        "growth": min_growth,
        "injected": injected,
        "weakest": [{"d": n, "c": c} for n, c in weakest[:3]]
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
