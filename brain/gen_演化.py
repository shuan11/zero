"""
gen_演化.py — 维度演化历史追踪
记录每一轮的维度分布变化，存入CSV，供dashboard/分析使用

让系统的自我成长在物理世界留下可见轨迹
"""

import json, os, time, csv
from pathlib import Path
from collections import Counter
from datetime import datetime

HISTORY_FILE = Path("/mnt/c/Users/h/Desktop/零/真元集群/data/dim_history.csv")
STATE_SNAPSHOT = Path("/mnt/c/Users/h/Desktop/零/真元集群/data/latest_state.json")

def _ensure_dir():
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)


def _load_hip():
    """读海马体"""
    hip_path = "/mnt/c/Users/h/Desktop/零/真元集群/hippocampus_memory.json"
    try:
        with open(hip_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def _get_dimensions():
    """获取当前维度分布"""
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    dims = Counter(c.get("dimension", "?") for c in chains)
    return dims, len(chains)


def _record_history(dims, total_chains):
    """记录一维维度快照到CSV"""
    _ensure_dir()
    now = datetime.now()
    timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
    epoch = int(now.timestamp())

    is_new = not HISTORY_FILE.exists()
    with open(HISTORY_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if is_new:
            header = ["timestamp", "epoch", "total_chains"] + sorted(dims.keys())
            w.writerow(header)
        row = [timestamp, epoch, total_chains] + [dims.get(d, 0) for d in sorted(dims.keys())]
        w.writerow(row)

    return timestamp


def _save_snapshot(dims, total_chains, timestamp):
    """保存当前快照供dashboard/其他模块读取"""
    _ensure_dir()

    sorted_dims = dims.most_common()
    if sorted_dims:
        strongest = sorted_dims[0]
        weakest = sorted_dims[-1]
        ratio = strongest[1] / max(weakest[1], 1)
    else:
        strongest = ("?", 0)
        weakest = ("?", 0)
        ratio = 1

    # 读取历史趋势
    trend = {}
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            if len(rows) >= 10:
                first = rows[0]
                last = rows[-1]
                for key in first:
                    if key not in ("timestamp", "epoch", "total_chains"):
                        try:
                            diff = int(last[key]) - int(first[key])
                            trend[key] = diff
                        except:
                            pass
        except:
            pass

    snapshot = {
        "timestamp": timestamp,
        "epoch": int(time.time()),
        "total_chains": total_chains,
        "dimensions": dict(dims.most_common(35)),
        "dimension_count": len(dims),
        "strongest": {"name": strongest[0], "count": strongest[1]},
        "weakest": {"name": weakest[0], "count": weakest[1]},
        "ratio": round(ratio, 1),
        "trend": trend,  # 自记录起的变化量
        "source": "gen_演化.py",
    }

    with open(STATE_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)

    return snapshot


def pulse():
    """记录一维维度快照"""
    dims, total = _get_dimensions()
    ts = _record_history(dims, total)
    snap = _save_snapshot(dims, total, ts)
    print(f"[演化] @{ts} | chain={total} | dim={len(dims)} | ratio={snap['ratio']}x")
    return snap


def get_history(n=20):
    """读取最近N条历史记录"""
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    return rows[-n:]


def get_snapshot():
    """读取最新快照"""
    if not STATE_SNAPSHOT.exists():
        return {"error": "no_snapshot"}
    with open(STATE_SNAPSHOT, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import json
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
