"""
gen_状态_感知注入.py — 状态感知注入: 外部信号→状态链

将系统运行时信号(daemon心跳/维度变化率)翻译为状态链.
"""

import json, time
from pathlib import Path
from brain.share import write_chain, read_hip, log

CLUSTER = Path(__file__).resolve().parent.parent

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = {}
        for c in chains:
            d = c.get("dimension", "?")
            dims[d] = dims.get(d, 0) + 1
        sorted_d = sorted(dims.items(), key=lambda x: -x[1])
        # 从系统运行时信号翻译为状态链
        if len(sorted_d) >= 2:
            strong = sorted_d[0]
            weak = sorted_d[-1]
            ratio = strong[1] / max(weak[1], 1)
            write_chain({
                "src": "感知",
                "rel": "状态注入",
                "dst": "状态",
                "content": f"【状态·感知注入】最强={strong[0]}({strong[1]}) 最弱={weak[0]}({weak[1]}) 比={ratio:.1f}x) | 状态维={dims.get('状态',0)}",
                "strength": 0.5,
                "dimension": "状态"
            })
            msgs.append(f"状态感知注入: {strong[0]}→{weak[0]} 比={ratio:.1f}x")
    except Exception as e:
        msgs.append(f"状态感知注入: ! {e}")
    return msgs
