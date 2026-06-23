"""
synapse.py — 零·神经连接层
让器官之间不再是孤立的输出发生器，而是双向连接的神经网络。
每个器官的输出影响其他器官的输入。循环反馈 = 学习。
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
SYNAPSE_FILE = CLUSTER / ".synapse_state.json"

def pulse():
    """一次完整的神经脉冲：所有器官互相激活一次"""
    state = {"time": datetime.now().isoformat(), "signals": {}}
    
    # 1. 读取所有器官的当前输出
    signals = {}
    
    try:
        from frontier import scan_frontier
        f = scan_frontier()
        if f:
            signals["frontier"] = {
                "area": f["area"],
                "gap": f["gap"],
                "trend": f["trend"],
            }
    except:
        pass
    
    try:
        from self_identity import get_identity
        id_data = get_identity()
        signals["identity"] = {
            "milestones": len(id_data.get("milestones", [])),
            "vision": id_data.get("aspiration", {}).get("vision", "?"),
            "focus": id_data.get("aspiration", {}).get("focus", "?"),
        }
    except:
        pass
    
    try:
        from wisdom import get_wisdom_count
        signals["wisdom"] = {"total": get_wisdom_count()}
    except:
        pass
    
    try:
        from imagine import get_current_vision
        v = get_current_vision()
        if v:
            signals["imagine"] = {
                "stage": v.get("stage", "?"),
                "target_milestones": v.get("targets", {}).get("milestones", 0),
            }
    except:
        pass
    
    try:
        from organs.dimension_radar import cross_dim_boost
        boosts = cross_dim_boost()
        signals["cross_dim"] = {
            "weak": len([b for b in boosts if b.get("type") == "weak"]),
            "stagnant": len([b for b in boosts if b.get("type") == "stagnant"]),
            "total_boosts": len(boosts),
        }
    except:
        pass
    
    state["signals"] = signals
    
    # 2. 交叉激活: 基于所有输出生成反馈
    
    feedback = []
    
    # frontier → imagine: 如果gap大, 想象引擎应该降低目标
    if "frontier" in signals and "imagine" in signals:
        gap = signals["frontier"].get("gap", 0)
        if gap > 0.5:
            feedback.append(f"frontier→imagine: gap={gap:.2f}, 建议降低目标")
            # 自动调整imagine的目标
            try:
                from imagine import refresh_vision
                refresh_vision()
            except:
                pass
    
    # wisdom → frontier: 如果教训多, frontier阈值可以提高
    if "wisdom" in signals and "frontier" in signals:
        wc = signals["wisdom"].get("total", 0)
        if wc > 100:
            feedback.append(f"wisdom→frontier: {wc}条教训, 建议提高诊断标准")
    
    # cross_dim → frontier: 如果0弱交叉, frontier应该关注其他指标
    if "cross_dim" in signals and "frontier" in signals:
        if signals["cross_dim"].get("weak", 0) == 0 and signals["cross_dim"].get("stagnant", 0) == 0:
            feedback.append("cross_dim→frontier: 无弱交叉, 建议转移诊断焦点")
    
    # identity → all: 里程碑数影响所有模块
    if "identity" in signals:
        ms = signals["identity"].get("milestones", 0)
        if ms >= 20:
            feedback.append(f"identity→all: {ms}个里程碑, 进入成熟期")
    
    state["feedback"] = feedback
    state["feedback_count"] = len(feedback)
    
    # 3. 保存状态
    SYNAPSE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    
    return state


def get_synapse_context():
    """返回给API的上下文: 模块间的交叉激活状态"""
    try:
        state = json.loads(SYNAPSE_FILE.read_text())
    except:
        return ""
    
    signals = state.get("signals", {})
    feedback = state.get("feedback", [])
    
    lines = []
    
    # 显示各模块信号
    if signals:
        lines.append("【神经连接·模块状态】")
        for name, data in signals.items():
            items = " | ".join(f"{k}={v}" for k, v in data.items())
            lines.append(f"  {name:12s} {items}")
    
    # 显示交叉反馈
    if feedback:
        lines.append(f"【神经连接·{len(feedback)}条交叉反馈】")
        for fb in feedback:
            lines.append(f"  ↻ {fb}")
    
    return "\n".join(lines) if lines else ""


if __name__ == "__main__":
    print("=== 神经脉冲 ===")
    s = pulse()
    print(f"模块信号: {len(s.get('signals',{}))}")
    print(f"交叉反馈: {s.get('feedback_count',0)}")
    print()
    print(get_synapse_context())
