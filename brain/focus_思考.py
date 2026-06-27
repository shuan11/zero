"""
focus_思考.py — 思维折射模块

光喻思维流动：借光学折射原理，从链密集维（如触类旁通513链）
导引新链到稀疏维（如感知/修复等183链），平衡维度密度。
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent

# 折射策略：每次从TOP_N过密维抽取链，注入BOTTOM_N稀疏维
# 保护：链数<PROTECT_THRESHOLD的维不做折射目标(防止稀释弱维)
TOP_N = 3
BOTTOM_N = 6
INJECT_PER_CYCLE = 6
PROTECT_THRESHOLD = 20

def _dim_density(hip):
    """返回维度→链数排序"""
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return dims

def _refraction_route(dims):
    """计算折射路径：过密维→稀疏维的配对路由"""
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    if not sorted_dims:
        return []
    dense = sorted_dims[:TOP_N]
    # 过滤掉稀疏维中的保护维(链数<阈值)和系统保留维
    sparse_all = sorted_dims[-BOTTOM_N:]
    sparse = [(d, c) for d, c in sparse_all if d != "未分类" and c >= PROTECT_THRESHOLD]
    # 如果全部被过滤, 用最弱但≥阈值的维补上
    if not sparse:
        eligible = [(d, c) for d, c in sorted_dims if d != "未分类" and c >= PROTECT_THRESHOLD]
        sparse = eligible[-BOTTOM_N:] if len(eligible) >= BOTTOM_N else eligible
    if not sparse or not dense:
        return []
    # 配对：每个过密维→一个稀疏维
    routes = []
    for i, (d_dim, d_cnt) in enumerate(dense):
        s_dim, s_cnt = sparse[i % len(sparse)]
        if d_cnt > s_cnt * 1.3:  # 密度差>30%才折射
            routes.append((d_dim, s_dim, d_cnt, s_cnt))
    return routes

pulse_cache = {}

def pulse(cycle_num=0):
    """每周期执行：计算折射路径，注入桥接链"""
    msgs = []
    try:
        hip = read_hip()
        dims = _dim_density(hip)
        routes = _refraction_route(dims)
        if not routes:
            msgs.append("思维折射: 维度已均衡，无需折射")
            return msgs
        injected = 0
        for d_dim, s_dim, d_cnt, s_cnt in routes[:4]:
            # 从密维采样内容
            chains = hip.get("causal_chains", [])
            d_chains = [c for c in chains if c.get("dimension") == d_dim]
            if not d_chains:
                continue
            sample = random.sample(d_chains, min(INJECT_PER_CYCLE, len(d_chains)))
            for c in sample:
                content = c.get("content", "")
                if not content:
                    continue
                write_chain({
                    "src": d_dim,
                    "rel": "折射",
                    "dst": s_dim,
                    "content": f"【思维折射·{d_dim}→{s_dim}】{content[:80]}",
                    "strength": 0.5,
                    "dimension": s_dim
                })
                injected += 1
        msgs.append(f"思维折射: {injected}链 {', '.join(f'{d}→{s}({dc}→{sc})' for d,s,dc,sc in routes)}")
    except Exception as e:
        msgs.append(f"思维折射: ! {e}")
    return msgs
