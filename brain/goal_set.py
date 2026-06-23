"""brain/goal_set.py — 手动设定目标

用法:
    python3 brain/goal_set.py                        # 选最弱维探索
    python3 brain/goal_set.py explore 术             # 探索指定维度
    python3 brain/goal_set.py deepen                 # 深化最强维
    python3 brain/goal_set.py synthesize 观察×行动   # 跨维合成
    python3 brain/goal_set.py consolidate            # 巩固均衡
"""
import json, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
GOAL_FILE = CLUSTER / ".brain_goal.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"


def _get_chain_counts():
    try:
        data = json.loads(HIP_FILE.read_text(encoding="utf-8"))
        counts = {}
        for c in data.get("causal_chains", []):
            d = c.get("dimension", "未分类")
            counts[d] = counts.get(d, 0) + 1
        return counts
    except:
        return {}


def _load_goal():
    try:
        return json.loads(GOAL_FILE.read_text())
    except:
        return {}


def set_goal(goal_type, focus_dim=None, reason=""):
    counts = _get_chain_counts()
    non_sys = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
    sorted_dims = sorted(non_sys.items(), key=lambda x: x[1])
    total = sum(counts.values())
    
    if not focus_dim and goal_type == "explore" and sorted_dims:
        focus_dim = sorted_dims[0][0]
    
    desc = {
        "explore": f"探索强化 {focus_dim}" if focus_dim else "探索弱维",
        "deepen": "深化最强维度的关联密度",
        "synthesize": f"跨维合成 {focus_dim}" if focus_dim else "跨维合成",
        "consolidate": "巩固均衡所有维度",
    }.get(goal_type, "手动设定")
    
    if not reason:
        reasons = {
            "explore": f"手动设定: 强化{focus_dim}",
            "deepen": "手动设定: 深化最强维度",
            "synthesize": f"手动设定: 合成{focus_dim}",
            "consolidate": "手动设定: 巩固均衡",
        }
        reason = reasons.get(goal_type, "手动设定")
    
    # 读取当前周期
    import time
    try:
        report = json.loads((CLUSTER / ".brain_cycle_report.json").read_text())
        current_cycle = report.get("cycle_num", 0)
    except:
        current_cycle = 0
    
    goal = {
        "goal_type": goal_type,
        "focus_dim": focus_dim,
        "description": desc,
        "reason": reason,
        "target_cycles": 10,
        "set_at": int(time.time()),
        "set_cycle": current_cycle,
    }
    
    GOAL_FILE.write_text(json.dumps(goal, ensure_ascii=False, indent=2), encoding="utf-8")
    
    # 记录到历史
    try:
        HISTORY_FILE = CLUSTER / ".brain_goal_history.json"
        hist = json.loads(HISTORY_FILE.read_text()) if HISTORY_FILE.exists() else []
        if not isinstance(hist, list):
            hist = []
        record = {**goal, "completed": False}
        if not hist or hist[-1].get("goal_type") != goal_type or hist[-1].get("focus_dim") != focus_dim:
            hist.append(record)
            if len(hist) > 50:
                hist = hist[-50:]
            HISTORY_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2), encoding="utf-8")
    except:
        pass
    
    print(f"✅ 目标已设定: [{goal_type}] {desc}")
    if focus_dim:
        print(f"   聚焦: {focus_dim}")
    print(f"   原因: {reason}")
    print(f"   当前: {total}总链 / 最弱{sorted_dims[0][0]}({sorted_dims[0][1]}) 最强{sorted_dims[-1][0]}({sorted_dims[-1][1]})")
    
    return goal


if __name__ == "__main__":
    args = sys.argv[1:]
    
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        sys.exit(0)
    
    goal_type = args[0]
    focus_dim = args[1] if len(args) > 1 else None
    reason = " ".join(args[2:]) if len(args) > 2 else ""
    
    valid_types = ("explore", "deepen", "synthesize", "consolidate")
    if goal_type not in valid_types:
        print(f"❌ 无效类型: {goal_type}，可选: {', '.join(valid_types)}")
        sys.exit(1)
    
    if goal_type == "explore" and not focus_dim:
        # 自动选最弱维
        counts = _get_chain_counts()
        non_sys = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
        sorted_dims = sorted(non_sys.items(), key=lambda x: x[1])
        if sorted_dims:
            focus_dim = sorted_dims[0][0]
            print(f"🌐 自动选择最弱维度: {focus_dim}")
    
    if goal_type == "synthesize" and not focus_dim:
        counts = _get_chain_counts()
        non_sys = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
        sorted_dims = sorted(non_sys.items(), key=lambda x: x[1])
        if len(sorted_dims) >= 2:
            focus_dim = f"{sorted_dims[-1][0]}×{sorted_dims[-2][0]}"
            print(f"🌐 自动选择最强两维合成: {focus_dim}")
    
    set_goal(goal_type, focus_dim, reason)
