#!/usr/bin/env python3
"""gen_行为注入 — 利用平衡态链指导daemon实际行为改变

区别于其他gen_模块(只写链到海马体), 本模块:
1. 读取最新合成报告
2. 计算各维度当前健康度
3. 直接写入.brain_focus.json改变daemon聚焦方向
4. 写入.brain_goal.json设定新目标

每5cycle运行, 确保daemon行为随系统状态动态调整。
"""
import json
from pathlib import Path
from collections import Counter

BRAIN = Path(__file__).parent
ROOT = BRAIN.parent
HIP_FILE = ROOT / "hippocampus_memory.json"
FOCUS_FILE = ROOT / ".brain_focus.json"
GOAL_FILE = ROOT / ".brain_goal.json"
SYNTHESIS_DIR = ROOT / "synthesis_reports"
LATEST_SYNTH = SYNTHESIS_DIR / "latest_synthesis.txt"

_CALL_COUNT = 0
_RUN_EVERY = 5

def _read_focus():
    """读取当前聚焦文件"""
    if FOCUS_FILE.exists():
        try:
            return json.loads(FOCUS_FILE.read_text())
        except:
            pass
    return {"focus": "deepen", "dimension": None, "cycle": 0}


def _read_goal():
    """读取当前目标文件(daemon格式)"""
    if GOAL_FILE.exists():
        try:
            return json.loads(GOAL_FILE.read_text())
        except:
            pass
    return {"goal_type": "synthesize", "focus_dim": None, "set_cycle": 0, "description": "automatic balance"}


def _write_focus(data):
    FOCUS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _write_goal(data):
    GOAL_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _CALL_COUNT % _RUN_EVERY != 1:
        return {"status": "skipped", "pulse": _CALL_COUNT}

    if not HIP_FILE.exists():
        return {"status": "error", "msg": "无海马体"}

    try:
        hip = json.loads(HIP_FILE.read_text())
    except:
        return {"status": "error", "msg": "海马体损坏"}

    chains = hip.get("causal_chains", [])
    dim_counts = Counter(c.get("dimension", "未分类") for c in chains)

    if not dim_counts:
        return {"status": "error", "msg": "无维度数据"}

    # 计算平衡度
    max_c = max(dim_counts.values())
    min_c = min(dim_counts.values())
    ratio = max_c / max(min_c, 1)
    avg = sum(dim_counts.values()) / len(dim_counts)

    # 找最弱维度
    weakest_dim = min(dim_counts, key=dim_counts.get)
    weakest_val = dim_counts[weakest_dim]

    # 找最强维度
    strongest_dim = max(dim_counts, key=dim_counts.get)
    strongest_val = dim_counts[strongest_dim]

    # 找最近合成报告中的建议
    synthesis_insight = None
    if LATEST_SYNTH.exists():
        synth_text = LATEST_SYNTH.read_text()
        state_line = __import__("re").search(r"系统当前状态: ([^\n]+)", synth_text)
        if state_line:
            synthesis_insight = state_line.group(1)

    # 读取当前daemon cycle数
    focus = _read_focus()
    current_cycle = focus.get("cycle", 0)
    new_cycle = current_cycle + 1

    # ── 写入.brain_focus.json (daemon格式) ──
    new_focus = {
        "focus": "deepen",
        "dimension": weakest_dim,
        "insight": synthesis_insight or f"{weakest_dim}维度持续弱势，需通过跨维刺激提升",
        "action": f"cross_dim_injection: {weakest_dim} ← {strongest_dim}",
        "cycle": new_cycle,
        "timestamp": __import__("time").time(),
    }
    # ── 仅写.brain_focus.json, 不碰.brain_goal.json ──
    # goal.py独立管理目标, gen_行为注入只提供聚焦建议
    _write_focus(new_focus)

    return {
        "status": "ok",
        "focus_dim": weakest_dim,
        "action": f"{weakest_dim} ← {strongest_dim}",
        "ratio": round(ratio, 2),
        "mode": "deepening",
        "pulse": _CALL_COUNT,
    }


if __name__ == "__main__":
    _CALL_COUNT = _RUN_EVERY
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
