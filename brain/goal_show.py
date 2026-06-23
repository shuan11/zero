"""brain/goal_show.py — 目标状态展示

用法:
    python3 brain/goal_show.py              # 当前目标
    python3 brain/goal_show.py --history     # 目标历史
"""
import json, time, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
GOAL_FILE = CLUSTER / ".brain_goal.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
REPORT_FILE = CLUSTER / ".brain_cycle_report.json"
HISTORY_FILE = CLUSTER / ".brain_goal_history.json"


def _load_json(path, default=None):
    try:
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except:
        pass
    return default or {}


def _get_chain_counts():
    data = _load_json(HIP_FILE, {"causal_chains": []})
    counts = {}
    for c in data.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        counts[d] = counts.get(d, 0) + 1
    return counts


def show_current():
    goal = _load_json(GOAL_FILE)
    if not goal or not goal.get("goal_type"):
        print("⚠ 无活跃目标")
        return

    gtype = goal["goal_type"]
    focus = goal.get("focus_dim")
    desc = goal.get("description", "")
    reason = goal.get("reason", "")
    set_cycle = goal.get("set_cycle", 0)
    set_at = goal.get("set_at", 0)
    target_cycles = goal.get("target_cycles", 10)

    # 计算已过周期
    report = _load_json(REPORT_FILE)
    current_cycle = report.get("cycle_num", 0)
    elapsed = current_cycle - set_cycle if current_cycle >= set_cycle else 0

    print(f"┌─ 🎯 当前目标 {'─'*40}")
    print(f"│  类型: {gtype}")
    print(f"│  描述: {desc}")
    if focus:
        print(f"│  聚焦: {focus}")
    print(f"│  原因: {reason}")
    print(f"│  周期: 设定于#{set_cycle}，已过{elapsed}/{target_cycles}周期")
    if set_at:
        from datetime import datetime
        dt = datetime.fromtimestamp(set_at)
        print(f"│  时间: {dt.strftime('%m-%d %H:%M')}")

    # 进度检查
    try:
        sys.path.insert(0, str(CLUSTER))
        from brain.goal import check_goal_progress
        gp = check_goal_progress()
        pct = gp.get("progress", 0) * 100
        completed = gp.get("completed", False)
        prog_reason = gp.get("reason", "")
        if completed:
            print(f"│  ✅ 已完成: {prog_reason}")
        else:
            print(f"│  📊 进度: {pct:.0f}% ({prog_reason})")
    except Exception as e:
        print(f"│  ⚠ 进度检查失败: {e}")

    # 维度分布（显示top/bottom各3个）
    counts = _get_chain_counts()
    non_sys = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
    if non_sys:
        sorted_dims = sorted(non_sys.items(), key=lambda x: x[1])
        print(f"│  ── 维度分布 ({sum(non_sys.values())}总链) ──")
        print(f"│  最弱: {' | '.join(f'{d}({c})' for d,c in sorted_dims[:3])}")
        print(f"│  最强: {' | '.join(f'{d}({c})' for d,c in sorted_dims[-3:])}")
    
    print(f"└─{'─'*50}")


def show_history():
    hist = _load_json(HISTORY_FILE, [])
    if not hist:
        print("⚠ 无目标历史")
        show_current()
        # 保存当前目标到历史
        return

    print(f"📜 目标演进历史 ({len(hist)}个):")
    print(f"{'#':<4} {'周期':<8} {'类型':<14} {'描述':<30} {'完成?':<6}")
    print(f"{'─'*4} {'─'*8} {'─'*14} {'─'*30} {'─'*6}")
    for i, h in enumerate(hist[-10:]):  # 最近10个
        gt = h.get("goal_type", "?")
        desc = h.get("description", "")[:28]
        cycle = h.get("set_cycle", "?")
        completed = "✅" if h.get("completed") else "⋯"
        print(f"{i:<4} #{cycle:<6} {gt:<14} {desc:<30} {completed:<6}")

    print()
    show_current()


def record_current():
    """记录当前目标到历史"""
    goal = _load_json(GOAL_FILE)
    if not goal or not goal.get("goal_type"):
        return

    hist = _load_json(HISTORY_FILE, [])
    if not isinstance(hist, list):
        hist = []
    # 如果最后一个目标同类型同描述，不重复记录
    if hist and hist[-1].get("goal_type") == goal["goal_type"] and \
       hist[-1].get("description") == goal.get("description"):
        return

    record = {
        "goal_type": goal["goal_type"],
        "description": goal.get("description", ""),
        "focus_dim": goal.get("focus_dim"),
        "reason": goal.get("reason", ""),
        "set_cycle": goal.get("set_cycle", 0),
        "set_at": goal.get("set_at", 0),
        "completed": False,
    }
    hist.append(record)
    # 保持最多50条
    if len(hist) > 50:
        hist = hist[-50:]
    HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    import sys
    if "--history" in sys.argv or "-h" in sys.argv:
        show_history()
    else:
        record_current()
        show_current()
