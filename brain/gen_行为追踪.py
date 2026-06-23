"""gen_行为追踪.py — 行为变化追踪器
测量系统行为是否随链数增长而真正变化。
回答daemon自问:"30次变异后，行为变了吗？"
"""
import json, time
from pathlib import Path

def pulse():
    """每周期记录daemon行为快照，检测行为漂移"""
    log = Path("/mnt/c/Users/h/Desktop/零/真元集群/.brain_daemon.log")
    snap = Path.home() / ".zero_brain" / ".behavior_snapshot.json"
    
    if not log.exists():
        return {"status": "no_log"}
    
    lines = log.read_text().splitlines()
    
    # Extract key behavior markers from log
    markers = {}
    for line in lines[-200:]:  # last 200 lines
        if "好奇:" in line:
            markers["curiosity"] = line
        if "预测:" in line:
            markers["predict"] = line
        if "意外:" in line:
            markers["surprise"] = line
        if "目标:" in line:
            markers["goal"] = line
        if "管道:" in line and "goal" not in line:
            markers["pipeline"] = line
        if "深度注入] 目标维度:" in line:
            markers["inject_targets"] = line
    
    # Read previous snapshot
    prev = {}
    if snap.exists():
        try:
            prev = json.loads(snap.read_text())
        except:
            prev = {}
    
    # Detect behavior change
    changes = []
    for k in markers:
        pval = prev.get(k, "")
        cval = markers[k]
        if pval != cval:
            changes.append(k)
    
    stability = len([k for k in markers if k in prev and prev[k] == markers[k]])
    novelty = len(changes)
    total = len(markers)
    drift_pct = round(novelty * 100 / total, 1) if total else 0
    
    result = {
        "status": "ok",
        "tracked_markers": total,
        "changed": novelty,
        "stable": stability,
        "drift_pct": drift_pct,
        "changes": changes,
        "ts": time.strftime("%H:%M:%S")
    }
    
    # Save snapshot
    snap.write_text(json.dumps(markers, ensure_ascii=False, indent=2))
    return result

def check():
    """快速读取最新行为漂移报告"""
    snap = Path.home() / ".zero_brain" / ".behavior_snapshot.json"
    if not snap.exists():
        return {"status": "no_data"}
    prev = json.loads(snap.read_text())
    return {
        "status": "ok",
        "current_curiosity": prev.get("curiosity", "?")[:60],
        "current_goal": prev.get("goal", "?")[:60],
        "current_predict": prev.get("predict", "?")[:60],
        "current_inject": prev.get("inject_targets", "?")[:60]
    }

if __name__ == "__main__":
    print(json.dumps(pulse(), ensure_ascii=False, indent=2))
