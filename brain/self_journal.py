"""brain/self_journal.py — 自我日记引擎

每周期记录系统的"主观体验"：
- 什么变化了
- 什么让系统"意外"
- 系统好奇什么
- 对下一周期的预测

日记存储在 .brain_journal.jsonl 中，可追溯。
"""
import json, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
JOURNAL_FILE = CLUSTER / ".brain_journal.jsonl"
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


def _load_prev_journal():
    """读取上一篇日记"""
    if not JOURNAL_FILE.exists():
        return None
    try:
        lines = JOURNAL_FILE.read_text(encoding="utf-8").strip().split("\n")
        if lines:
            return json.loads(lines[-1])
    except:
        pass
    return None


def _detect_surprises(current, prev):
    """检测什么让系统意外"""
    surprises = []
    if not prev:
        return surprises

    # 维度变化检测
    curr_dims = current.get("dimensions", {})
    prev_dims = prev.get("dimensions", {})
    for dim in set(list(curr_dims.keys()) + list(prev_dims.keys())):
        cv = curr_dims.get(dim, 0)
        pv = prev_dims.get(dim, 0)
        if cv - pv >= 5:
            surprises.append(f"{dim}突增+{cv-pv}")

    return surprises


def _load_goal():
    """读取当前目标"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        return json.loads(gf.read_text())
    except:
        return None


def _synthesize_curiosity(report, prev, goal):
    """系统"好奇"什么"""
    curiosities = []

    # 如果链数超过12000，好奇质量
    total = report.get("total_chains", 0)
    if total > 12000:
        curiosities.append("链超1.2万，质量有多深？")

    # 如果有新变异，好奇效果
    mutations = report.get("mutations", {}).get("total", 0)
    if mutations > 0:
        curiosities.append(f"{mutations}次变异后，行为变了吗？")

    # 目标反思
    if goal:
        gt = goal.get("goal_type", "")
        gf = goal.get("focus_dim", "")
        if gf:
            curiosities.append(f"[{gt}]聚焦{gf}还差多少？")
        else:
            curiosities.append(f"[{gt}]均衡能持续多久？")

    return curiosities


def _make_prediction(current, prev):
    """预测下一周期"""
    curr_chains = current.get("total_chains", 0)
    if prev:
        prev_chains = prev.get("total_chains", 0)
        delta = curr_chains - prev_chains
        if delta > 0:
            return f"预计+{delta}~{delta+5}链"
    return "持平或微增"


def write_entry(pulse_log=None, goal=None):
    """生成并写入一条日记"""
    report = _load_json(REPORT_FILE)
    prev_entry = _load_prev_journal()

    curr_dims = report.get("dimensions", {})
    prev_dims = prev_entry.get("dimensions", {}) if prev_entry else {}

    surprises = _detect_surprises({"dimensions": curr_dims}, {"dimensions": prev_dims})
    curiosities = _synthesize_curiosity(report, prev_entry, goal)
    prediction = _make_prediction({"total_chains": report.get("total_chains", 0)},
                                   {"total_chains": prev_entry.get("total_chains", 0)} if prev_entry else None)

    entry = {
        "cycle": report.get("cycle_num", 0),
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_chains": report.get("total_chains", 0),
        "dimensions": curr_dims,  # 保存维度快照用于下期比较
        "stable_dims": report.get("stable_dims", 0),
        "mode": report.get("genome_phase", "unknown"),
        "goal_type": goal.get("goal_type") if goal else None,
        "goal_focus": goal.get("focus_dim") if goal else None,
        "surprises": surprises[:3],
        "curiosities": curiosities[:2],
        "prediction": prediction,
        "pulse_summary": (pulse_log or [])[:5],
    }

    JOURNAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(JOURNAL_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    # 返回可读日记
    lines = []
    lines.append(f"日记#{entry['cycle']}: {entry['total_chains']}链/{entry['stable_dims']}稳")
    if entry.get("goal_type"):
        _gf = entry.get("goal_focus") or "全局均衡"
        lines.append(f"  目标: [{entry['goal_type']}] {_gf}")
    if entry["surprises"]:
        lines.append(f"  意外: {' '.join(entry['surprises'])}")
    if entry["curiosities"]:
        lines.append(f"  好奇: {' '.join(entry['curiosities'])}")
    lines.append(f"  预测: {entry['prediction']}")
    return "\n".join(lines)


def pulse(cycle_num, pulse_log=None):
    """被daemon每周期调用 — 生成日记"""
    if cycle_num <= 0:
        return []
    _goal = _load_goal()
    return [write_entry(pulse_log, goal=_goal)]


if __name__ == "__main__":
    entry = write_entry()
    print(entry)
    print("---")
    print(f"日记文件: {JOURNAL_FILE}")
