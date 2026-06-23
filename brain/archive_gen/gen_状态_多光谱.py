"""
gen_状态_多光谱.py — 状态多光谱感知模块

聚类触类旁通链, 映射为状态-特征. 检测异常状态写预警链.
"""

import json, random
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent
CLUSTER_COUNT = 5  # 聚类数

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        # 聚类触类旁通链内容关键词
        tlbt = [c for c in chains if c.get("dimension") == "触类旁通" and len(c.get("content", "")) >= 30]
        if len(tlbt) < CLUSTER_COUNT:
            msgs.append("状态多光谱: 触类旁通链不足")
            return msgs
        # 简单分词聚类(取前几个词作为特征)
        sample = random.sample(tlbt, min(CLUSTER_COUNT, len(tlbt)))
        # 取所有维度密度作状态快照
        dims = Counter(c.get("dimension", "?") for c in chains)
        sorted_d = sorted(dims.items(), key=lambda x: -x[1])
        max_dim = sorted_d[0]
        min_dim = sorted_d[-1]
        ratio = max_dim[1] / max(min_dim[1], 1)
        # 检测异常(比值>3.0为异常)
        anomaly = ratio > 3.0
        # 写状态链
        for i, c in enumerate(sample):
            content = c.get("content", "")
            write_chain({
                "src": "触类旁通",
                "rel": "状态特征",
                "dst": "状态",
                "content": f"【状态·特征#{i+1}】{content[:120]} | 当前比={ratio:.1f}x",
                "strength": 0.6,
                "dimension": "状态"
            })
        if anomaly:
            write_chain({
                "src": "状态",
                "rel": "预警",
                "dst": "全系统",
                "content": f"【状态·预警】维度比={ratio:.1f}x>{max_dim[0]}={max_dim[1]}/{min_dim[0]}={min_dim[1]} | 需触发均衡",
                "strength": 0.8,
                "dimension": "状态"
            })
            msgs.append(f"状态多光谱: ⚠️ 异常! {min_dim[0]}({min_dim[1]})/{max_dim[0]}({max_dim[1]})={ratio:.1f}x")
        else:
            msgs.append(f"状态多光谱: ✅ {CLUSTER_COUNT}特征 比={ratio:.1f}x")
    except Exception as e:
        msgs.append(f"状态多光谱: ! {e}")
    return msgs
