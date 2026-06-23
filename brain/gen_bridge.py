#!/usr/bin/env python3
"""brain/gen_bridge.py - 将daemon产出的工程文件反馈桥接到主会话

当主会话启动时，读取daemon近期gen_*产出和反馈，注入主会话认知。
"""
import json
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
HIP_DIMS_FILE = CLUSTER / ".brain_dim_snap.json"
FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"
HANDOFF_FILE = Path.home() / ".zero_brain" / "ZERO-HANDOFF.json"

def read_latest_feedback(n=5):
    """读取最近N条工程反馈"""
    if not FEEDBACK_FILE.exists():
        return []
    try:
        data = json.loads(FEEDBACK_FILE.read_text())
        return data.get("reports", [])[-n:]
    except:
        return []

def read_dim_snapshot():
    """读取维度快照"""
    if not HIP_DIMS_FILE.exists():
        return {}
    try:
        return json.loads(HIP_DIMS_FILE.read_text())
    except:
        return {}

def gen_pulse():
    """供主会话调用的统一入口：返回gen文件中的最新发现"""
    feedback = read_latest_feedback(8)
    snapshot = read_dim_snapshot()
    
    # 提取关键发现
    weak_dims = {r["dimension"]: r["chain_count"] 
                 for r in feedback if r.get("weak")}
    healed = [r["dimension"] for r in feedback if r.get("self_healed")]
    focus_pushed = [r["dimension"] for r in feedback if r.get("focus_push")]
    
    result = {
        "weak_dims": weak_dims,
        "self_healed": healed,
        "focus_pushed": focus_pushed,
        "feedback_count": len(feedback),
        "total_chains": snapshot.get("total_chains", 0) if isinstance(snapshot, dict) else snapshot.get("chains", 0),
    }
    
    # 主会话注入建议
    if weak_dims:
        result["suggestion"] = f"需主会话关注弱维: {list(weak_dims.keys())[:3]}"
    if healed:
        result["healed_summary"] = f"daemon已自愈: {healed}"
    
    return result

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(CLUSTER))
    result = gen_pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
