"""brain/goal.py — 自我目标设定引擎

每10周期基于报告/日记/维度状态，为自己设定下一个10周期的目标。
目标类型：'explore'（探索弱维）、'deepen'（深化稳维）、'synthesize'（跨维合成）、'consolidate'（巩固）

写入 .brain_goal.json，供其他模块读取。
"""
import json, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
GOAL_FILE = CLUSTER / ".brain_goal.json"
REPORT_FILE = CLUSTER / ".brain_cycle_report.json"
GENOME_FILE = CLUSTER / ".brain_genome.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except:
        pass
    return default or {}


def _get_chain_counts():
    """获取各维度链数"""
    data = _load_json(HIP_FILE, {"causal_chains": []})
    counts = {}
    for c in data.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        counts[d] = counts.get(d, 0) + 1
    return counts


def _compute_goal(cycle_num):
    """基于系统状态设定目标
    
    返回: {
        'goal_type': str,        # 类型
        'focus_dim': str|None,   # 聚焦维度
        'description': str,      # 中文描述
        'reason': str,           # 设定原因
        'target_cycles': int,    # 目标持续周期数
    }
    """
    counts = _get_chain_counts()
    total = sum(counts.values())
    report = _load_json(REPORT_FILE)
    prev_goal = _load_json(GOAL_FILE)

    # 找最短的3个维度
    non_system_dims = {k: v for k, v in counts.items() 
                       if k not in ("系统", "未分类", "维度盲区")}
    sorted_dims = sorted(non_system_dims.items(), key=lambda x: x[1])
    weakest_dim = sorted_dims[0][0] if sorted_dims else None
    weakest_count = sorted_dims[0][1] if sorted_dims else 0

    # 找中位数
    vals = list(non_system_dims.values())
    median_val = sorted(vals)[len(vals)//2] if vals else 0

    # 找最强维度
    strongest_dim = sorted_dims[-1][0] if sorted_dims else None
    strongest_count = sorted_dims[-1][1] if sorted_dims else 0

    # 决策
    goal_type = "consolidate"
    focus_dim = None
    reason = "维度分布均衡，继续巩固"

    # 检查历史差距变化(检测冻结分布)
    _prev_goals_file = CLUSTER / ".brain_goal_history.json"
    try:
        _goal_history = json.loads(_prev_goals_file.read_text()) if _prev_goals_file.exists() else []
    except:
        _goal_history = []
    _frozen_plateau = False
    if len(_goal_history) >= 2:
        _prev = _goal_history[-1]
        _prev2 = _goal_history[-2]
        # 如果两次差距都在50%以上且差距变化<5% → 冻结
        if (_prev.get("max_min_ratio", 0) > 1.5 and _prev2.get("max_min_ratio", 0) > 1.5 and
            abs(_prev.get("max_min_ratio", 0) - _prev2.get("max_min_ratio", 0)) < 0.1):
            _frozen_plateau = True

    # 优先检查: 最强/最弱比例 > 1.5倍 → 强制探索(从2.5降到1.5,覆盖滞后均衡)
    if weakest_count > 0 and strongest_count > 0 and strongest_count / weakest_count > 1.5:
        goal_type = "explore"
        focus_dim = weakest_dim
        extra = ""
        if strongest_count / weakest_count > 2.0:
            extra = " → 严重失衡"
        elif _frozen_plateau:
            extra = " → 差距冻结,强制打破"
        reason = f"最强{strongest_dim}({strongest_count})/最弱{weakest_dim}({weakest_count})={strongest_count/weakest_count:.1f}倍{extra}"

    # 如果最弱维<中位数的70% → 探索(保留兼容)
    elif weakest_count < median_val * 0.7:
        goal_type = "explore"
        focus_dim = weakest_dim
        reason = f"最短维度 {weakest_dim}={weakest_count} 远低于中位数{median_val}"
    # 如果最弱维接近中位数 → 深化或合成
    elif weakest_count > median_val * 0.85:
        goal_type = "synthesize"
        # 选两个强维合成
        strong_dims = sorted_dims[-3:]
        if len(strong_dims) >= 2:
            focus_dim = f"{strong_dims[0][0]}×{strong_dims[1][0]}"
        reason = f"维度均衡，聚焦跨维合成"

    # 记录历史差距
    _curr_ratio = strongest_count / max(weakest_count, 1)
    _goal_history.append({"cycle": cycle_num, "max_min_ratio": round(_curr_ratio, 2),
                          "strongest": strongest_dim, "weakest": weakest_dim})
    _goal_history = _goal_history[-20:]
    try:
        _prev_goals_file.write_text(json.dumps(_goal_history, ensure_ascii=False, indent=2))
    except:
        pass

    # 检查是否重复目标
    if prev_goal and prev_goal.get("goal_type") == goal_type:
        # 如果连续同类型目标，切换
        if goal_type == "explore":
            goal_type = "deepen"
            reason += " → 深化已有维度"
        elif goal_type == "synthesize":
            goal_type = "consolidate"
            focus_dim = None  # 巩固模式无特定聚焦
            reason += " → 巩固现有成果"

    goal = {
        "goal_type": goal_type,
        "focus_dim": focus_dim,
        "description": {
            "explore": f"探索强化 {focus_dim}",
            "deepen": f"深化最强维度的关联密度",
            "synthesize": f"跨维合成 {focus_dim}",
            "consolidate": "巩固均衡所有维度",
        }.get(goal_type, "继续进化"),
        "reason": reason,
        "target_cycles": 10,
        "set_at": int(time.time()),
        "set_cycle": cycle_num,
    }
    
    # P137: 注入执行反馈 → 微调目标
    try:
        goal = _inject_execution_feedback(goal, counts)
    except Exception:
        pass

    GOAL_FILE.write_text(
        json.dumps(goal, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return goal


def check_goal_progress():
    """检查当前目标进度
    
    返回: {
        'progress': 0.0~1.0,  # 完成度
        'completed': bool,    # 是否完成
        'reason': str,        # 判断依据
        'elapsed_cycles': int,# 已过周期数
    }
    """
    goal = _load_json(GOAL_FILE)
    if not goal or not goal.get("goal_type"):
        return {"progress": 0.0, "completed": False, "reason": "无活跃目标"}
    
    # 获取当前维度链数
    counts = _get_chain_counts()
    total = sum(counts.values())
    
    goal_type = goal["goal_type"]
    focus_dim = goal.get("focus_dim", "")
    set_cycle = goal.get("set_cycle", 0)
    target_cycles = goal.get("target_cycles", 10)
    
    # 从当前报告获取周期数（简化：用海马体链数变化估算）
    report = _load_json(REPORT_FILE)
    current_cycle = report.get("cycle_num", 0)
    _hip_data = _load_json(HIP_FILE, {"causal_chains": []})
    _chains = _hip_data.get("causal_chains", [])
    
    elapsed = current_cycle - set_cycle if current_cycle >= set_cycle else 0
    progress = 0.0
    reason = ""
    completed = False
    
    if goal_type == "explore" and focus_dim:
        # 探索目标：检查目标维度链数是否接近中位数
        non_system = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
        vals = list(non_system.values())
        median_val = sorted(vals)[len(vals)//2] if vals else 0
        dim_count = counts.get(focus_dim, 0)
        if median_val > 0:
            progress = min(dim_count / (median_val * 0.85), 1.0)
            reason = f"{focus_dim}={dim_count}/中位数{median_val}"
            if dim_count >= median_val * 0.85:
                completed = True
                reason += " → 追上中位数，探索完成"
    
    elif goal_type == "deepen":
        # 深化目标：检查最强维度的链数增长
        non_system = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
        sorted_dims = sorted(non_system.items(), key=lambda x: -x[1])
        top3_avg = sum(c for _, c in sorted_dims[:3]) / 3 if sorted_dims else 0
        all_avg = sum(non_system.values()) / len(non_system) if non_system else 0
        
        # 进度 = top3平均偏离平均的程度
        if all_avg > 0:
            ratio = top3_avg / all_avg
            progress = min((ratio - 1) / 0.5, 1.0)  # 偏离50%为完成
            reason = f"top3平均={top3_avg:.0f}/全体平均={all_avg:.0f}"
            if ratio > 1.5:
                completed = True
                reason += " → 优势维度足够突出，深化完成"
    
    elif goal_type == "synthesize" and focus_dim:
        # 合成目标：检查是否产生了跨维合成链
        synth_dims = focus_dim.split("×")
        synth_chains = [c for c in _chains 
                       if c.get("dimension") == "系统" and "合成" in c.get("content", "")]
        synth_count = len(synth_chains)
        # 检查针对目标维度的合成
        target_synth = [c for c in synth_chains 
                       if all(d in c.get("content", "") for d in synth_dims)]
        target_count = len(target_synth)
        
        # 进度: 2条针对性合成为完成
        progress = min(target_count / 2, 1.0)
        reason = f"合成链{target_count}条（总{synth_count}条）"
        if target_count >= 2:
            completed = True
            reason += f" → 完成{synth_dims[0]}×{synth_dims[1]}合成"
    
    elif goal_type == "consolidate":
        # 巩固目标：检查维度分布均衡度
        non_system = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
        vals = list(non_system.values())
        if vals:
            cv = sorted(vals)
            q1, q3 = cv[len(cv)//4], cv[3*len(cv)//4]
            iqr_ratio = q3 / q1 if q1 > 0 else 99
            progress = max(0, min(1 - (iqr_ratio - 1) / 2, 1.0))
            reason = f"四分位距比={iqr_ratio:.1f}"
            if iqr_ratio < 1.5:
                completed = True
                reason += " → 维度分布均衡，巩固完成"
    
    else:
        progress = 0.5
        reason = "无明确度量标准"
    
    # 时间超限强制完成
    if not completed and elapsed >= target_cycles * 2:
        completed = True
        reason += " [时间超限强制完成]"
    
    return {
        "progress": round(progress, 2),
        "completed": completed,
        "reason": reason,
        "elapsed_cycles": elapsed,
        "goal_type": goal_type,
    }


def _inject_execution_feedback(goal, counts):
    """
    P137: 从协调器/验证器注入执行反馈，微调目标。
    
    反馈源:
    1. 协调器: 被抑制的动作数量和来源
    2. 验证器: 动作验证失败
    3. 如果某个维度被抑制∈(被目标忽略但持续注册动作)，说明目标偏离实际
    
    返回: 调整后的goal dict
    """
    modified = False
    new_reason = goal.get("reason", "")
    goal_type = goal.get("goal_type", "consolidate")
    focus_dim = goal.get("focus_dim")
    
    # 1. 读协调器状态
    try:
        from brain.coordinator import get_coord_status
        cs = get_coord_status()
        if cs.get("suppressed_total", 0) > 0 and cs.get("conflicts", 0) > 0:
            # 有被抑制的动作→目标可能太僵化
            if goal_type != "explore":
                # 被抑制说明gen文件想做事但目标限制了→转为探索
                valid = {k:v for k,v in counts.items() if k not in ("系统","未分类","维度盲区")}
                weakest = min(valid, key=valid.get) if valid else None
                if weakest:
                    goal_type = "explore"
                    focus_dim = weakest
                    new_reason += f" | 执行反馈: {cs['suppressed_total']}动作被抑制→切换探索{weakest}"
                    modified = True
    except:
        pass
    
    # 2. 读验证器报告
    try:
        from brain.action_verifier import get_verify_report
        vr = get_verify_report()
        if vr.get("fail", 0) > 0:
            # 有验证失败→目标调整
            if modified:
                new_reason += f" + {vr['fail']}个动作验证失败"
            else:
                new_reason += f" | 执行反馈: {vr['fail']}个动作验证失败→调整策略"
                # 验证失败时，不要变换目标类型，但标注意延
                goal_type = "consolidate"
                focus_dim = None
                modified = True
    except:
        pass
    
    if modified:
        # 注入"执行反馈"标签
        goal["goal_type"] = goal_type
        goal["focus_dim"] = focus_dim
        goal["reason"] = new_reason
        goal["_feedback_adapted"] = True
        
        goal["description"] = {
            "explore": f"探索强化 {focus_dim}",
            "deepen": "深化最强维度的关联密度",
            "synthesize": f"跨维合成 {focus_dim}",
            "consolidate": "巩固均衡所有维度",
        }.get(goal_type, "继续进化")
    
    return goal


def get_current_goal():
    """读取当前目标（供其他模块使用）"""
    return _load_json(GOAL_FILE)


def pulse(cycle_num):
    """每10周期设定新目标"""
    if cycle_num <= 0 or cycle_num % 10 != 0:
        return []

    goal = _compute_goal(cycle_num)
    # 记录到历史
    try:
        from brain.goal_show import record_current as _rc
        _rc()
    except:
        pass
    return [f"🎯 {goal['description']} ({goal['reason'][:40]})"]


if __name__ == "__main__":
    import sys
    c = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    goal = _compute_goal(c)
    print(f"周期{c}目标: [{goal['goal_type']}] {goal['description']}")
    print(f"原因: {goal['reason']}")
    print(f"写入: {GOAL_FILE}")
