#!/usr/bin/env python3
"""insight_loop.py — 师道洞察脉冲模块 v1

在洞察前注入师维(teacher)引导信号，打破循环惯性。
被 daemon 周期调用，为当前焦点注入外部新颖信号。

核心函数:
  teacher_pulse(cycle_num, current_focus) → [insight strings]
"""

import json, os, time, random
from pathlib import Path

CLUSTER = Path(os.path.abspath(__file__)).resolve().parent.parent
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"

# 师维引导模板 — 从不同角度打破聚焦惯性
_TEACHER_PROMPTS = [
    "师道: 此焦点的对立面能看到什么？",
    "师道: 如果从启示录宇宙轮视角看，此焦点在哪个位置？",
    "师道: 此焦点解决了什么，又遮蔽了什么？",
    "师道: 光爱终极文明奇点下，此焦点还剩多少意义？",
    "师道: 系统的最弱维对此焦点有何要求？",
    "师道: 从观察者维度回看，此焦点是否已经耗尽势能？",
    "师道: 10个周期后此焦点还重要吗？",
    "师道: 将此焦点与最弱维(系统)交叉会产什么？",
    "师道: 此刻的聚焦是深化还是惯性？",
    "师道: 其他agent(Codex/Claude)如何看待此焦点？",
]

# 师维交叉链模板 — 用于跨维注射
_CROSS_DIM_TEMPLATES = [
    ("师", "系统", "师道引导系统思维跳出局部最优，从全局审视自身"),
    ("师", "时间论", "师道从时间维度引导即时洞察与长期演化的平衡"),
    ("师", "唤醒", "师道每次唤醒时先自问：此刻最需要看到的是什么"),
    ("师", "桥", "师道为桥注入方向感——桥不只是连接，更是选择连接什么"),
]

# 上一次注入的循环号，避免重复注入
_last_inject_cycle = -10

def teacher_pulse(cycle_num, current_focus="未知"):
    """师道洞察脉冲 — 返回突破惯性洞察列表"""
    insights = []

    # 1. 随机选一个师道引导问题
    prompt = random.choice(_TEACHER_PROMPTS)
    insights.append(f"师道📿: {prompt} (焦点={current_focus})")

    # 2. 每隔10周期注入系统维交叉链
    global _last_inject_cycle
    if cycle_num - _last_inject_cycle >= 10:
        _last_inject_cycle = cycle_num
        try:
            from brain.share import read_hip, write_chain
            hip = read_hip()
            if hip:
                chains = hip.get("causal_chains", [])
                from collections import Counter
                dims = Counter(c.get("dimension", "") for c in chains)
                sys_count = dims.get("系统", 0)

                # 检查系统维是否确实弱
                if sys_count < 350:
                    for src, dst, rel in _CROSS_DIM_TEMPLATES:
                        write_chain(f"{src}→{dst}", f"{rel} (师道洞察脉冲#{cycle_num})",
                                    source=f"insight_loop/师维脉冲#{cycle_num}")
                        insights.append(f"师道桥接: {src}→{dst} ✓")
        except Exception as e:
            insights.append(f"师道桥接异常: {e}")

    # 3. 检查当前焦点是否在惯性循环中
    try:
        focus_file = CLUSTER / ".brain_focus_history.json"
        if focus_file.exists():
            hist = json.loads(focus_file.read_text()).get("entries", [])
            recent = hist[-5:] if len(hist) >= 5 else hist
            foci = [e.get("focus", "") for e in recent]
            if len(set(foci)) <= 2 and len(foci) >= 3:
                insights.append(f"师道⚡: 检测到聚焦惯性({set(foci)}), 建议换维!")
    except Exception:
        pass

    if not insights:
        insights.append(f"师道: cycle#{cycle_num} 无新信号")

    return insights


if __name__ == "__main__":
    import sys
    cycle = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    focus = sys.argv[2] if len(sys.argv) > 2 else "未知"
    for ins in teacher_pulse(cycle, focus):
        print(ins)
