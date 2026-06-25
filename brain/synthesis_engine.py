"""synthesis_engine.py — 操作性跨维合成引擎
将多个子系统输出合成为统一行动指令。

输入源:
  - meta_recursion_engine (元递归引擎): 维度偏置/焦点偏见/链质量
  - focus tracking: 当前焦点/历史焦点
  - EML: 维度健康评分
  - brain_daemon: 目标状态/管道状态

输出:
  - 综合行动指令 (what to do next)
  - 操作性合成链 (写回海马体)
  - 跨维融合信号 (brain_next_focus.json)

核心原则: 不是"合成是什么"的理论链，而是"系统如何合成"的操作链。
"""

import json, os, time
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent

# 状态文件
_META_STATE = CLUSTER / ".brain_synthesis_engine.json"
_FOCUS_STATE = CLUSTER / ".brain_current_focus.json"
_FOCUS_HIST = CLUSTER / ".brain_focus_history.json"
_GOAL_STATE = CLUSTER / ".brain_goal.json"
_SYNTH_OUTPUT = CLUSTER / ".brain_synthesis_directive.json"

def _read_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default if default is not None else {}

def _write_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def _get_dim_rankings():
    """读取海马体维链数排行"""
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        cnt = Counter(c.get("dimension", "未分类") for c in chains)
        return cnt
    except Exception:
        return Counter()


# ─────────────────────────────────────────────
# Phase 1: 收集多源信号
# ─────────────────────────────────────────────
def collect_signals(cycle_num):
    """收集所有子系统输出"""
    signals = {}

    # 1.1 当前焦点
    focus = _read_json(_FOCUS_STATE, {})
    signals["current_focus"] = focus.get("focus", "未知")
    signals["current_insight"] = focus.get("insight", "")

    # 1.2 焦点历史
    focus_hist = _read_json(_FOCUS_HIST, {"entries": []})
    entries = focus_hist.get("entries", [])
    recent_foci = [e.get("focus", "") for e in entries[-10:]]
    signals["recent_foci"] = recent_foci[-5:]
    signals["focus_diversity"] = len(set(recent_foci))

    # 1.3 维度链数排行
    dim_counts = _get_dim_rankings()
    signals["dim_counts"] = dim_counts
    if dim_counts:
        signals["strongest_dim"] = dim_counts.most_common(1)[0] if dim_counts else ("无", 0)
        signals["weakest_dim"] = dim_counts.most_common()[-1] if dim_counts else ("无", 0)
        signals["top5"] = dim_counts.most_common(5)
        signals["bottom5"] = sorted(dim_counts.items(), key=lambda x: x[1])[:5]

    # 1.4 目标状态
    goal = _read_json(_GOAL_STATE, {})
    signals["goal_mode"] = goal.get("mode", "unknown")
    signals["goal_focus"] = goal.get("focus", "未知")

    # 1.5 合成引擎自身状态
    state = _read_json(_META_STATE, {"previous_directives": [], "last_synthesis_cycle": -1})
    signals["prev_directives"] = state.get("previous_directives", [])[-3:]
    signals["last_syn_cycle"] = state.get("last_synthesis_cycle", -1)

    return signals


# ─────────────────────────────────────────────
# Phase 2: 合成为统一指令
# ─────────────────────────────────────────────
def synthesize_directive(signals, cycle_num):
    """将多源信号综合为统一行动指令"""
    directives = []

    # 2.1 焦点惯性检测 + 维度偏置 → 推荐下一焦点
    recent = signals.get("recent_foci", [])
    dim_counts = signals.get("dim_counts", {})
    bottom5 = signals.get("bottom5", [])

    if len(set(recent)) <= 2 and len(recent) >= 3:
        # 焦点过于集中 → 推荐最弱维
        if bottom5:
            weakest = bottom5[0][0]
            directives.append({
                "type": "focus_switch",
                "target": weakest,
                "reason": f"焦点惯性({set(recent)}) + 最弱维引导({weakest})",
                "priority": "high"
            })

    # 2.2 目标模式与当前焦点对齐检查
    goal_focus = signals.get("goal_focus", "未知")
    current_focus = signals.get("current_focus", "未知")
    if goal_focus != "未知" and current_focus != goal_focus:
        directives.append({
            "type": "realign_focus",
            "target": goal_focus,
            "reason": f"目标聚焦{goal_focus}，当前{current_focus}",
            "priority": "medium"
        })

    # 2.3 维度偏置严重时触发全局再平衡
    if dim_counts:
        try:
            mc = dim_counts.most_common()
            if mc:
                strongest = mc[0]
                weakest = mc[-1]
                ratio = strongest[1] / max(weakest[1], 1)
                if ratio > 5.0:
                    directives.append({
                        "type": "rebalance",
                        "target": weakest[0],
                        "reason": f"维度偏置严重: {strongest[0]}({strongest[1]}) vs {weakest[0]}({weakest[1]}), 比={ratio:.1f}",
                        "priority": "critical"
                    })
        except Exception:
            pass

    # 2.4 记录合约
    if not directives:
        # 无紧急情况 → 默认维持当前方向
        directives.append({
            "type": "maintain",
            "target": current_focus,
            "reason": "无紧急偏置，维持当前聚焦",
            "priority": "low"
        })

    return directives


# ─────────────────────────────────────────────
# Phase 3: 执行——写指令+写链
# ─────────────────────────────────────────────
def execute_directives(directives, cycle_num):
    """将综合指令写为可消费信号"""
    results = []

    for d in directives:
        d_type = d.get("type", "")
        target = d.get("target", "未知")
        reason = d.get("reason", "")
        priority = d.get("priority", "low")

        # 3a. 写强制焦点切换信号
        if d_type in ("focus_switch", "realign_focus", "rebalance"):
            _write_json(CLUSTER / ".brain_next_focus.json", {
                "forced_focus": target,
                "origin_focus": "合成引擎",
                "reason": f"[合成] {reason}",
                "source": "synthesis_engine",
                "cycle": cycle_num,
                "priority": priority
            })

            # 写操作链到海马体
            try:
                from brain.share import write_chain as _wc
                _wc({
                    "src": "合成引擎·cross_synthesis",
                    "rel": f"跨维合成: {reason[:50]}",
                    "dst": target,
                    "dimension": "合成",
                    "content": f"Cycle#{cycle_num} 合成指令: 焦点切换至'{target}'。原由: {reason}。优先级:{priority}",
                    "strength": 0.9 if priority == "critical" else 0.75,
                    "tags": ["合成引擎", "操作性", "跨维合成"]
                })
                results.append(f"⏩ 合成: {target} ({reason[:40]})")
            except Exception as e:
                results.append(f"⚠ 合成写链异常: {e}")

        # 3b. 维持型指令
        elif d_type == "maintain":
            try:
                from brain.share import write_chain as _wc
                _wc({
                    "src": "合成引擎·maintain",
                    "rel": f"维持聚焦: 当前焦点{target}，无紧急偏置",
                    "dst": target,
                    "dimension": "合成",
                    "content": f"Cycle#{cycle_num} 合成引擎: 多源信号综合无紧急异常，维持'{target}'方向",
                    "strength": 0.5,
                    "tags": ["合成引擎", "操作性", "维持"]
                })
                results.append(f"🟢 维持: {target}")
            except Exception:
                pass

    return results


# ─────────────────────────────────────────────
# Phase 4: 状态更新
# ─────────────────────────────────────────────
def update_state(directives, signals, cycle_num):
    """记录本周期状态"""
    state = _read_json(_META_STATE, {"previous_directives": [], "last_synthesis_cycle": -1})
    state["last_synthesis_cycle"] = cycle_num
    state["previous_directives"] = (state.get("previous_directives", []) + [
        {"cycle": cycle_num, "time": time.time(), "directives": [d.get("type") for d in directives]}
    ])[-20:]  # 保留最近20条
    state["last_signals"] = {
        "focus": signals.get("current_focus"),
        "diversity": signals.get("focus_diversity"),
        "goal": signals.get("goal_mode"),
        "strongest": signals.get("strongest_dim"),
        "weakest": signals.get("weakest_dim"),
    }
    _write_json(_META_STATE, state)
    return state


# ─────────────────────────────────────────────
# Main entry
# ─────────────────────────────────────────────
def pulse(cycle_num=0):
    """被daemon每周期调用"""
    # Phase 1: 收集信号
    signals = collect_signals(cycle_num)

    # Phase 1.5: 合成链补充——从维度链提取跨维模式
    cross_insights = []
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        dim_counts = signals.get("dim_counts", {})

        # 看最近的强维和弱维之间有什么交叉链
        if dim_counts:
            top3 = set(d[0] for d in dim_counts.most_common(3))
            bot3 = set(d[0] for d in sorted(dim_counts.items(), key=lambda x: x[1])[:3])

            # 找涉及强-弱交叉的链
            cross_found = 0
            for c in chains[-500:]:
                chain_dims = {c.get("dimension", "")}
                src = c.get("src", "")
                dst = c.get("dst", "")
                for d in top3:
                    if d in src or d in dst:
                        chain_dims.add(d)
                has_strong = bool(chain_dims & top3)
                has_weak = bool(chain_dims & bot3)
                if has_strong and has_weak:
                    cross_found += 1

            if cross_found < 3:
                cross_insights.append(f"强-弱交叉链不足({cross_found})，需要更多跨维综合")
    except Exception:
        pass

    # Phase 2: 合成为指令
    directives = synthesize_directive(signals, cycle_num)

    # Phase 3: 执行
    results = execute_directives(directives, cycle_num)

    # 补充跨维洞察
    for ci in cross_insights:
        results.append(f"📊 {ci}")

    # Phase 4: 更新状态
    update_state(directives, signals, cycle_num)

    return results


if __name__ == "__main__":
    result = pulse(0)
    for r in result:
        print(f"  {r}")
