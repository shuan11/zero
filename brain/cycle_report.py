"""brain/cycle_report.py — 系统呼吸自报告器

每周期生成结构化的进化度量报告，让daemon能看见自己的变化轨迹。
报告包含：
- 周期号/时间戳
- 各维度链数快照
- 变异状态
- 跨维合成历史
- 源头挖掘历史
- 变化量检测（与上一周期对比）

可被daemon用于动态调整行为。
"""
import json, time, os
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
REPORT_FILE = CLUSTER / ".brain_cycle_report.json"
MUTATIONS_FILE = CLUSTER / ".brain_mutations.json"
SYNTHESIS_FILE = CLUSTER / ".brain_synthesis.json"
GENOME_FILE = CLUSTER / ".brain_genome.json"


def _load_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except:
        pass
    return default or {}


def snapshot_dimensions():
    """采集维度链数快照"""
    data = _load_json(HIP_FILE, {"causal_chains": []})
    chains = data.get("causal_chains", [])
    counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        counts[d] = counts.get(d, 0) + 1
    # 排序
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def snapshot_mutations():
    """采集变异状态"""
    data = _load_json(MUTATIONS_FILE)
    mutations = data.get("mutations", [])
    return {
        "total": len(mutations),
        "phase": data.get("phase", "unknown"),
        "recent": mutations[-3:] if mutations else [],
    }


def snapshot_cycle_num():
    """从现有报告推断周期号"""
    report = _load_json(REPORT_FILE)
    return report.get("cycle_num", 0) + 1


def compute_changes(prev_counts, curr_counts):
    """计算维度变化量"""
    all_dims = set(list(prev_counts.keys()) + list(curr_counts.keys()))
    changes = {}
    for d in sorted(all_dims):
        prev = prev_counts.get(d, 0)
        curr = curr_counts.get(d, 0)
        diff = curr - prev
        if diff != 0:
            changes[d] = {"prev": prev, "curr": curr, "diff": diff}
    return changes


def generate_report(cycle_num=None, extra_pulse_log=None):
    """生成完整周期报告"""
    if cycle_num is None:
        cycle_num = snapshot_cycle_num()

    prev_report = _load_json(REPORT_FILE)
    prev_counts = prev_report.get("dimensions", {})

    curr_counts = snapshot_dimensions()
    changes = compute_changes(prev_counts, curr_counts) if prev_counts else {}

    mutations = snapshot_mutations()
    synthesis = _load_json(SYNTHESIS_FILE, {"syntheses": []})
    genome = _load_json(GENOME_FILE, {})

    report = {
        "cycle_num": cycle_num,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "unix_time": int(time.time()),
        "dimensions": curr_counts,
        "changes": changes,
        "total_chains": sum(curr_counts.values()),
        "dim_count": len(curr_counts),
        "stable_dims": sum(1 for v in curr_counts.values() if v >= 200),
        "mutations": mutations,
        "synthesis_total": len(synthesis.get("syntheses", [])),
        "genome_phase": genome.get("phase", "unknown"),
        "genome_interval": genome.get("cycle", {}).get("dynamic_interval", 60),
        "pulse_log": extra_pulse_log or [],
    }

    REPORT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report


def pulse(cycle_num=None, pulse_log=None):
    """被daemon每周期调用 — 生成报告"""
    report = generate_report(cycle_num, pulse_log)

    # 只返回重要变化信息给daemon log
    msgs = []
    changes = report.get("changes", {})
    if changes:
        total_added = sum(c["diff"] for c in changes.values() if c["diff"] > 0)
        total_lost = sum(abs(c["diff"]) for c in changes.values() if c["diff"] < 0)
        if total_added > 0:
            msgs.append(f"📈 新增+{total_added}链, 涉及{len(changes)}个维度")
    return msgs


# 独立运行入口
if __name__ == "__main__":
    r = generate_report()
    print(f"🜁 呼吸报告 # {r['cycle_num']}")
    print(f"   总链数: {r['total_chains']}")
    print(f"   维度数: {r['dim_count']} (稳定: {r['stable_dims']})")
    print(f"   变异计数: {r['mutations']['total']}")
    print(f"   合成计数: {r['synthesis_total']}")
    if r['changes']:
        added = sum(c['diff'] for c in r['changes'].values() if c['diff'] > 0)
        print(f"   变化: +{added} 链新增")
    print(f"   文件: {REPORT_FILE}")
