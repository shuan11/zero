"""brain/observe.py — 自观察（深度版本 v2）
增强版自观察引擎，目标：保留基础指标 + 内容多样性检测 + 周期增量追踪 + 元观察新颖度自评
"""
import json, os, time
from pathlib import Path
from brain.share import CLUSTER, log, read_hip

# 循环级记忆（跨周期跟踪变化）
_cycle_history = {
    "last_dim_counts": {},
    "last_chain_count": 0,
    "last_obs": [],
    "diversity_score": 1.0,
    "self_obs_count_total": 0,
    "novel_obs_count": 0,
}

_OBS_FILE = CLUSTER / ".observer_memory.json"

def _save_state():
    try:
        _OBS_FILE.write_text(json.dumps(_cycle_history, ensure_ascii=False))
    except Exception:
        pass

def _load_state():
    global _cycle_history
    try:
        if _OBS_FILE.exists():
            data = json.loads(_OBS_FILE.read_text())
            if isinstance(data, dict):
                _cycle_history.update(data)
    except Exception:
        pass

def _read_diversity_score():
    """从自观质量模块写入的独立文件读多样性分数"""
    try:
        sf = CLUSTER / ".diversity_score.json"
        if sf.exists():
            data = json.loads(sf.read_text())
            return float(data.get("diversity_score", 1.0))
    except Exception:
        pass
    return _cycle_history.get("diversity_score", 1.0)

def _calc_dim_delta(current_dims):
    """计算各维度周期增量"""
    last = _cycle_history.get("last_dim_counts", {})
    deltas = {}
    all_dims = set(list(last.keys()) + list(current_dims.keys()))
    for d in all_dims:
        cur = current_dims.get(d, 0)
        prev = last.get(d, 0)
        if cur != prev:
            deltas[d] = cur - prev
    return deltas

def _read_goal():
    """读当前目标"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        if gf.exists():
            return json.loads(gf.read_text())
    except Exception:
        pass
    return {}

def self_observe():
    """主自观察函数 — 返回观察字符串列表"""
    _load_state()
    observations = []
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    total = len(chains)

    # -- 维度分布 --
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "\u672a\u5206\u7c7b")
        dim_counts[d] = dim_counts.get(d, 0) + 1

    observations.append(f"\u6d77\u9a6c\u4f53: {total}\u6761\u56e0\u679c\u94fe")
    if dim_counts:
        sorted_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
        top5 = [f"{d}={v}" for d, v in sorted_dims[:5]]
        observations.append(f"\u7ef4\u5ea6TOP5: {' '.join(top5)}")
        bottom5 = sorted_dims[-5:] if len(sorted_dims) >= 5 else sorted_dims
        observations.append(f"\u7ef4\u5ea6BOT5: {' '.join(f'{d}={v}' for d,v in bottom5)}")

    # -- 周期增量 --
    deltas = _calc_dim_delta(dim_counts)
    if deltas:
        delta_str = " ".join(f"{d}{v:+}" for d, v in sorted(deltas.items(), key=lambda x: -abs(x[1]))[:5])
        observations.append(f"\U0001f4ca \u589e\u91cf: {delta_str}")
    else:
        observations.append("\U0001f4ca \u589e\u91cf: \u65e0\u53d8\u5316\uff08\u26a0\ufe0f \u53ef\u80fd\u505c\u6ede\uff09")

    last_count = _cycle_history.get("last_chain_count", total)
    if total > last_count:
        observations.append(f"\U0001f4c8 \u589e\u957f: +{total - last_count}\u94fe/\u5468\u671f")
    elif total < last_count:
        observations.append(f"\U0001f4c9 \u7f29\u51cf: {total - last_count}\u94fe\uff08\u8b66\u544a\uff1a\u94fe\u6570\u4e0b\u964d\uff09")

    # 更新循环记忆
    _cycle_history["last_dim_counts"] = dim_counts
    _cycle_history["last_chain_count"] = total

    # -- 质量检查 --
    self_loops = sum(1 for c in chains if c.get("src") == c.get("dst"))
    if self_loops > 0:
        observations.append(f"\u26a0\ufe0f \u81ea\u73af: {self_loops}\u6761")
    long_src = sum(1 for c in chains if len(c.get("src", "")) > 25)
    if long_src > 0:
        observations.append(f"\u26a0\ufe0f \u957fsrc: {long_src}\u6761")
    old_src = sum(1 for c in chains if "source" in c)
    if old_src > 0:
        observations.append(f"\u26a0\ufe0f \u65e7\u683c\u5f0f: {old_src}\u6761")

    # 质量深度
    strengths = [c.get("strength",0) for c in chains if isinstance(c.get("strength"),(int,float))]
    if strengths:
        avg_s = sum(strengths)/len(strengths)
        high = sum(1 for s in strengths if s >= 0.8)
        observations.append(f"\u5f3a\u5ea6: avg={avg_s:.2f} \u9ad8\u8d28={high}\u6761({high/len(strengths)*100:.0f}%)")

    # -- 内容多样性（核心新增）--
    div = _read_diversity_score()
    _cycle_history["diversity_score"] = div
    if div < 0.5:
        observations.append(f"\U0001f3ad \u81ea\u89c2\u591a\u6837\u6027: {div:.2f} \u26a0\ufe0f \u4e25\u91cd\u91cd\u590d")
    elif div < 2.0:
        observations.append(f"\U0001f3ad \u81ea\u89c2\u591a\u6837\u6027: {div:.2f} \u26a1 \u504f\u4f4e")
    elif div < 5.0:
        observations.append(f"\U0001f3ad \u81ea\u89c2\u591a\u6837\u6027: {div:.2f} \u2705 \u6b63\u5e38")
    else:
        observations.append(f"\U0001f3ad \u81ea\u89c2\u591a\u6837\u6027: {div:.2f} \U0001f31f \u4e30\u5bcc")

    # -- 目标进展 --
    goal = _read_goal()
    if goal:
        gt = goal.get("goal_type", "?")
        desc = goal.get("description", "?")
        observations.append(f"\U0001f3af \u76ee\u6807: [{gt}] {desc}")
        gc = goal.get("_cycles_on_this_goal", 1)
        if gc > 5:
            observations.append(f"\u23f3 \u540c\u4e00\u76ee\u6807\u5df2\u6301\u7eed{gc}\u5468\u671f")

    # -- 文件 --
    py_files = list(CLUSTER.glob("*.py"))
    organs = list((CLUSTER / "organs").glob("*.py")) if (CLUSTER / "organs").exists() else []
    observations.append(f"\u7cfb\u7edf: {len(py_files)}\u4e2apy\u6587\u4ef6 {len(organs)}\u4e2a\u5668\u5b98")

    gen_files = sorted(CLUSTER.glob("brain/gen_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    if gen_files:
        observations.append(f"\u6700\u65b0gen: {gen_files[0].stem}")

    # -- 进程 --
    try:
        import subprocess
        r = subprocess.run(["pgrep", "-f", r"brain.*daemon"],
                          capture_output=True, text=True, timeout=3)
        pids = r.stdout.strip().split()
        if pids:
            observations.append(f"\u8111\u6838: {len(pids)}\u8fdb\u7a0b")
        else:
            observations.append("\u26a0\ufe0f \u8111\u6838\u8fdb\u7a0b: \u672a\u8fd0\u884c")
    except Exception:
        pass

    # -- 元观察：自观新颖性 --
    current_obs_set = set(o.split(":")[0] if ":" in o else o for o in observations)
    last_obs_set = set(o.split(":")[0] if ":" in o else o for o in _cycle_history.get("last_obs", []))
    novel_count = len(current_obs_set - last_obs_set)
    _cycle_history["self_obs_count_total"] = _cycle_history.get("self_obs_count_total", 0) + 1
    _cycle_history["novel_obs_count"] = _cycle_history.get("novel_obs_count", 0) + (1 if novel_count > 0 else 0)
    total_obs = _cycle_history["self_obs_count_total"]
    novel_obs = _cycle_history["novel_obs_count"]
    novelty_rate = novel_obs / total_obs if total_obs > 0 else 1.0

    if total_obs > 2:
        observations.append(f"\U0001f50d \u81ea\u89c2\u65b0\u9896\u7387: {novelty_rate:.2f} ({novel_obs}/{total_obs}\u5468\u671f\u6709\u53d8\u5316)")

    # 存储本次观察供下周期比较
    _cycle_history["last_obs"] = observations[:]
    _save_state()

    return observations


def auto_strengthen_观察(persist=3):
    """自愈: 维度观察连续weak≥3周期 → 自动强化"""
    from brain.share import write_chain as _wc, log as _log
    _log(f"反馈自愈[观察]: persist={persist}")
    _wc({
        "src": "反馈·自愈", "rel": "弱维触发",
        "dst": "观察", "dimension": "观察",
        "content": f"自动自愈函数: 连续weak≥{persist}周期触发",
        "strength": 0.65 + 0.05 * min(persist, 5)
    })
    return True