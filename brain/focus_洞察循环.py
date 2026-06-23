"""
focus_洞察循环.py — 跨维信号注入→洞察循环增强

焦点动作: 从一元化、势、合成中抽取关联链注入洞察循环
每周期: 读强维链→注入洞察循环维→形成交叉注射闭环
"""

import json, random
from pathlib import Path
from brain.share import write_chain, log, read_hip

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SYNTH_SOURCES = ["一元化", "势", "合成"]
DIMS = ["道", "天", "地", "人", "法", "术", "器", "势", "一元化",
        "聚焦", "对话", "智慧", "感知", "行动", "状态", "系统",
        "师", "检查", "触类旁通", "交叉合成", "时间论", "思维并联",
        "海马体", "洞察循环", "启示录", "系统设计", "工程建设",
        "运行监控", "未分类"]

def _get_dim_chains(dim_filter):
    """返回指定维度的链（用dimension字段）"""
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        return [c for c in chains if c.get("dimension") == dim_filter]
    except:
        return []

def pulse(cycle_num=0):
    """每周期从强维抽取链注入洞察循环"""
    msgs = []
    try:
        total_injected = 0
        for src in SYNTH_SOURCES:
            src_chains = _get_dim_chains(src)
            if len(src_chains) < 3:
                continue
            sample = random.sample(src_chains, min(2, len(src_chains)))
            for c in sample:
                content = c.get("content", "")
                if not content or len(content) < 10:
                    continue
                write_chain({
                    "src": src,
                    "rel": "洞见注入",
                    "dst": "洞察循环",
                    "content": f"【洞察循环·{src}注入】{content[:80]}",
                    "strength": 0.6,
                    "dimension": "洞察循环"
                })
                total_injected += 1

        if total_injected > 0:
            msgs.append(f"洞察循环: {total_injected}链从{SYNTH_SOURCES}注入 ✓")
        else:
            msgs.append("洞察循环: 源链不足，跳过")
    except Exception as e:
        msgs.append(f"洞察循环: ! {e}")
    return msgs
