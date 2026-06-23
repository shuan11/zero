"""brain/steering.py — 自适应方向舵

读取周期报告 + 基因组，决定下一周期的行为参数。
从"硬编码调度"进化到"数据驱动调度"。

核心函数: adapt(cycle_num) → dict of overrides
"""
import json, os
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
REPORT_FILE = CLUSTER / ".brain_cycle_report.json"
GENOME_FILE = CLUSTER / ".brain_genome.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except:
        pass
    return default or {}


def adapt(cycle_num):
    """根据历史报告数据自适应调度
    
    返回: {
        'synthesis_interval': N,
        'mining_interval': N,
        'focus_dim': str|None,
        'energy_mode': str,
    }
    """
    report = _load_json(REPORT_FILE)
    if not report or cycle_num <= 1:
        return {"energy_mode": "normal"}

    changes = report.get("changes", {})
    total_chains = report.get("total_chains", 0)
    mutations_total = report.get("mutations", {}).get("total", 0)
    synthesis_total = report.get("synthesis_total", 0)

    result = {"energy_mode": "normal"}

    # P123: 读取当前目标
    _goal = _load_json(CLUSTER / ".brain_goal.json")
    _goal_type = _goal.get("goal_type") if _goal and _goal.get("set_cycle", -99) > cycle_num - 20 else None
    _goal_focus = _goal.get("focus_dim") if _goal_type else None

    # 决策0: 目标驱动 — 目标类型覆盖行为模式
    if _goal_type == "explore" and _goal_focus:
        result["_goal_type"] = "explore"
        result["energy_mode"] = "accelerate"
        result["focus_dim"] = _goal_focus
        result["synthesis_interval"] = 5
        result["mining_interval"] = 3  # 探索时更频繁挖掘源头链
    elif _goal_type == "deepen":
        result["_goal_type"] = "deepen"
        result["energy_mode"] = "refine"
        result["focus_dim"] = _goal_focus if _goal_focus else None
        result["synthesis_interval"] = 7  # 深化时放慢合成
        result["mining_interval"] = 10
    elif _goal_type == "synthesize":
        result["_goal_type"] = "synthesize"
        result["energy_mode"] = "accelerate"
        result["synthesis_interval"] = 2  # 合成目标时极频繁合成
        result["mining_interval"] = 5
    elif _goal_type == "consolidate":
        result["energy_mode"] = "normal"
        # 巩固时不指定focus_dim，让API自行决定
        result["synthesis_interval"] = 5
        result["mining_interval"] = 10
    else:
        # 无目标时的默认决策链（原有逻辑）
        # 决策1: 如果连续无变化 → 加速模式
        if not changes and cycle_num > 3:
            result["energy_mode"] = "accelerate"
            result["synthesis_interval"] = 3
            result["mining_interval"] = 5
        else:
            result["synthesis_interval"] = 5
            result["mining_interval"] = 10

        # 决策2: 变异发生后 → 观察模式
        if mutations_total > 0:
            result["energy_mode"] = "observe"

    # 决策3: 合成数量还少 → 鼓励合成（无论目标如何）
    if synthesis_total < 5 and result.get("synthesis_interval", 5) > 3:
        result["synthesis_interval"] = 3

    # 决策4: 总链数超过12000 → 精炼倾向（除非目标是explore）
    if total_chains > 12000 and _goal_type != "explore":
        if result["energy_mode"] not in ("accelerate",):
            result["energy_mode"] = "refine"

    return result


def pulse(cycle_num):
    """被daemon每周期调用 — 应用自适应调度"""
    params = adapt(cycle_num)
    mode = params.get("energy_mode", "normal")

    msgs = []
    
    # P123: 报告目标驱动信息
    _goal_type = params.get("_goal_type")
    if _goal_type:
        msgs.append(f"🎯 目标驱动: {_goal_type} → {mode}")
    
    if mode == "accelerate":
        msgs.append(f"🔄 模式→加速")
    elif mode == "observe":
        msgs.append(f"👁 模式→观察 (变异后评估)")
    elif mode == "refine":
        msgs.append(f"🔬 模式→精炼")

    if params.get("synthesis_interval") and params["synthesis_interval"] != 5:
        msgs.append(f"  合成间隔: {params['synthesis_interval']}周期")

    # 写入genome供其他模块读取
    genome = _load_json(GENOME_FILE, {})
    genome["_steering"] = {
        "updated_at": int(__import__("time").time()),
        "cycle_num": cycle_num,
        "params": params,
    }
    GENOME_FILE.write_text(json.dumps(genome, ensure_ascii=False, indent=2), encoding="utf-8")

    return msgs


if __name__ == "__main__":
    import sys
    c = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    params = adapt(c)
    print(f"周期 {c} → {params['energy_mode']}")
    for k, v in params.items():
        if k != "energy_mode":
            print(f"  {k}: {v}")
