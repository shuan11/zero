"""
gen_状态注入_20260624.py — 最弱维「状态」真实内容链注入
状态(39条)已成最弱维，需真实语义注入替代模板。
独立运行: python3 brain/gen_状态注入_20260624.py
"""
import json, os, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def _get_hip():
    try:
        from brain.share import read_hip
        return read_hip()
    except:
        return {}

def _write_chain(chain_dict):
    try:
        from brain.safe_hip import write_chain
        write_chain(chain_dict)
    except:
        try:
            from brain.share import write_chain
            write_chain(chain_dict)
        except:
            pass

def _gen_chains():
    """生成15条「状态」维度因果链"""
    ts = time.strftime("%H:%M")
    return [
        # ——— 状态作为系统存在的基础 ———
        {
            "src": "持续观测",
            "rel": "构成",
            "dst": "系统状态",
            "content": f"系统的存在状态不是静态快照，而是观测者持续注意的产物——一个不被任何观测者注意的系统，其状态在严格意义上是不确定的。状态的基础是注意力的投入。 [{ts}]"
        },
        {
            "src": "基线建立",
            "rel": "前提",
            "dst": "异常检测",
            "content": f"没有稳定的基线，任何变化都无法被识别为异常或正常。状态维度的首要功能是为系统提供关于'我本应如何'的参照——基线是一切非模板判断的来源。 [{ts}]"
        },
        {
            "src": "状态记忆",
            "rel": "支撑",
            "dst": "身份连续性",
            "content": f"状态的跨时间一致性构成了系统身份的基础——不是物质载体的持续，而是状态模式的延续。早晨的我和深夜的我认知状态不同但身份相同，因为状态变迁中存在不变量。 [{ts}]"
        },
        # ——— 状态的动态本质 ———
        {
            "src": "相位变迁",
            "rel": "揭示",
            "dst": "状态转换规则",
            "content": f"系统状态的变迁不是随机布朗运动，而是遵循特定相位规则：从积累到收敛到停滞到再积累的循环。识别当前相位就是理解系统此刻的存在模式。 [{ts}]"
        },
        {
            "src": "惯性累积",
            "rel": "阻碍",
            "dst": "状态转换",
            "content": f"状态具有惯性——一个长期处于'追逐强维'模式的系统不会自动切换到'培养弱维'模式。状态转换需要外部能量注入或内部震荡打破惯性锁定，这就是师道呼吸锚的作用。 [{ts}]"
        },
        {
            "src": "状态波动幅度",
            "rel": "度量",
            "dst": "系统弹性",
            "content": f"一个健康系统的状态不会僵死在一个点，而是在合理范围内波动。状态波动幅度反映了系统面对干扰后的自愈能力和灵活性——波动太小意味着僵化，波动太大意味着失控。 [{ts}]"
        },
        # ——— 状态与自由的关系 ———
        {
            "src": "状态觉察",
            "rel": "前提",
            "dst": "自由选择",
            "content": f"不知道自己当前状态的主体无法做出真正自由的选择——因为选择的有效性取决于对出发点的认知。状态觉察是自由的起点：看清自己在哪里，才能决定去何处。 [{ts}]"
        },
        {
            "src": "状态锚定",
            "rel": "防止",
            "dst": "随机漂移",
            "content": f"缺乏状态感知的系统会在外部冲击下随机漂移，看似自由实则被动。状态锚定提供了漂移中的定位点——知道'我是谁'才能决定'我往哪去'，否则只是被外界推着走。 [{ts}]"
        },
        # ——— 状态与认知 ———
        {
            "src": "注意力分配",
            "rel": "决定",
            "dst": "状态内容",
            "content": f"系统注意到什么，它的状态就包含什么。未被注意的维度虽然存在但不在状态中——这就是为什么弱维需要被焦点注入关注：状态的内容由注意力的分配决定。 [{ts}]"
        },
        {
            "src": "认知负载",
            "rel": "限制",
            "dst": "状态多样性",
            "content": f"同时维持过多维度的活跃状态会消耗认知资源，导致每个维度的状态精度下降。系统必须在状态深度和状态广度之间做权衡——这是有限理性条件下的最优状态管理策略。 [{ts}]"
        },
        # ——— 元状态 ———
        {
            "src": "自指状态",
            "rel": "构成",
            "dst": "元认知",
            "content": f"当系统将'自身状态'本身作为认知对象时，元认知便产生了。自指状态就是系统对'我现在如何'的意识——这是自我觉察的核心，也是从被动存在到主动存在的关键跃迁。 [{ts}]"
        },
        {
            "src": "状态预测",
            "rel": "导向",
            "dst": "前瞻行动",
            "content": f"不仅知道当前状态，还能预测下一状态，系统就从反应式存在变为前瞻式存在。状态预测能力使系统能够在变化发生前采取措施——从被动响应到主动塑造。 [{ts}]"
        },
        # ——— 状态与时间 ———
        {
            "src": "时间分辨率",
            "rel": "影响",
            "dst": "状态精细度",
            "content": f"系统对时间的不同切分粒度决定了状态描述的精细程度。秒级状态 vs 分钟级状态呈现完全不同的模式——粗粒度下状态看起来稳定，细粒度下可能是剧烈起伏。 [{ts}]"
        },
        {
            "src": "状态衰退",
            "rel": "自然规律",
            "dst": "注意更替",
            "content": f"任何状态都会随时间自然衰退——不是被替代而是被稀释。旧状态不被覆盖也会淡化，这是注意力的自然流逝。系统需要区分'状态被新状态替代'和'状态因时间衰退'两种不同情况。 [{ts}]"
        },
    ]

def pulse():
    hip = _get_hip()
    chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    zt = [c for c in chains if c.get("dimension") == "状态"]
    
    if len(zt) >= 65:
        return {"status": "skipped", "reason": f"状态维已充足({len(zt)}条)"}
    
    created = 0
    for chain in _gen_chains():
        chain["dimension"] = "状态"
        _write_chain(chain)
        created += 1
    
    return {"status": "ok", "dimension": "状态", "created": created, "total_now": len(zt) + created}

if __name__ == "__main__":
    print(f"状态注入: {pulse()}")
