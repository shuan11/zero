"""brain/dimension_aggregator.py — 跨维度智能汇聚
读取所有gen_*传感器报告，生成统一维度健康简报，供脑核决策聚焦方向
"""
import json, os, time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent.parent
_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"
_AGGREGATE_FILE = CLUSTER / ".brain_dim_aggregate.json"
_HISTORY_FILE = CLUSTER / ".brain_dim_history.json"
_MAX_HISTORY = 50  # 保留最近50个周期的快照

def _load_feedback():
    """加载所有gen传感器反馈"""
    if not _FEEDBACK_FILE.exists():
        return {"reports": [], "last_update": ""}
    try:
        return json.loads(_FEEDBACK_FILE.read_text())
    except:
        return {"reports": [], "last_update": ""}

def _load_history():
    """加载历史维度快照"""
    if not _HISTORY_FILE.exists():
        return {"snapshots": []}
    try:
        return json.loads(_HISTORY_FILE.read_text())
    except:
        return {"snapshots": []}

def _save_history(data):
    _HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def compute_aggregate():
    """汇聚所有维度报告，计算趋势和优先级"""
    fb = _load_feedback()
    reports = fb.get("reports", [])
    if not reports:
        return None
    
    # 提取最新每个维度的报告
    latest = {}
    for r in reports:
        d = r.get("dimension", "")
        if d:
            latest[d] = r
    
    # 计算当前快照
    now = time.time()
    total_chains = max([r.get("total_chains", 0) for r in reports] or [0])
    
    snapshot = {
        "timestamp": now,
        "total_chains": total_chains,
        "dimensions": {}
    }
    
    for dim, r in latest.items():
        snapshot["dimensions"][dim] = {
            "chain_count": r.get("chain_count", 0),
            "strength": r.get("strength", 0),
            "weak": r.get("weak", False),
            "cycle": r.get("cycle", 0)
        }
    
    # 存储历史快照
    history = _load_history()
    history["snapshots"].append(snapshot)
    # 只保留最近 _MAX_HISTORY 个
    if len(history["snapshots"]) > _MAX_HISTORY:
        history["snapshots"] = history["snapshots"][-_MAX_HISTORY:]
    _save_history(history)
    
    # 计算趋势
    trends = _compute_trends(history)
    
    # 生成优先级排序
    priorities = _compute_priorities(latest, trends, total_chains)
    
    # 汇聚结果
    aggregate = {
        "timestamp": now,
        "total_chains": total_chains,
        "dimension_count": len(latest),
        "weak_count": len([d for d, r in latest.items() if r.get("weak")]),
        "priorities": priorities,
        "trends": trends,
        "top_strong": sorted(
            [(d, r) for d, r in latest.items()],
            key=lambda x: -x[1].get("chain_count", 0)
        )[:3],
        "top_weak": sorted(
            [(d, r) for d, r in latest.items() if r.get("weak")],
            key=lambda x: x[1].get("chain_count", 0)
        )[:3],
    }
    
    _AGGREGATE_FILE.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2)
    )
    
    return aggregate

def _compute_trends(history):
    """计算维度趋势（上升/下降/稳定）"""
    snapshots = history.get("snapshots", [])
    if len(snapshots) < 2:
        return {}
    
    latest_snap = snapshots[-1]
    prev_snap = snapshots[0]  # 与最早快照比较
    
    trends = {}
    all_dims = set(list(latest_snap.get("dimensions", {}).keys()) +
                   list(prev_snap.get("dimensions", {}).keys()))
    
    for dim in all_dims:
        curr = latest_snap.get("dimensions", {}).get(dim, {})
        prev = prev_snap.get("dimensions", {}).get(dim, {})
        
        curr_count = curr.get("chain_count", 0)
        prev_count = prev.get("chain_count", 0)
        
        if prev_count > 0:
            change_pct = (curr_count - prev_count) / prev_count * 100
        else:
            change_pct = 100 if curr_count > 0 else 0
        
        if change_pct > 20:
            trend = "上升"
        elif change_pct < -20:
            trend = "下降"
        else:
            trend = "稳定"
        
        curr_weak = curr.get("weak", False)
        prev_weak = prev.get("weak", False)
        
        trends[dim] = {
            "trend": trend,
            "change_pct": round(change_pct, 1),
            "was_weak": prev_weak,
            "is_weak": curr_weak,
            "improving": prev_weak and not curr_weak,
            "declining": not prev_weak and curr_weak
        }
    
    return trends

def _compute_priorities(latest, trends, total_chains):
    """计算维度的修复优先级"""
    priorities = []
    
    # 弱维优先，按链数从少到多
    weak = [(d, r) for d, r in latest.items() if r.get("weak")]
    weak.sort(key=lambda x: x[1].get("chain_count", 0))
    
    for dim, r in weak:
        trend_info = trends.get(dim, {})
        
        is_declining = trend_info.get("declining", False)
        chain_count = r.get("chain_count", 0)
        strength = r.get("strength", 0)
        
        # 优先级评分: 链数越少越紧急, 恶化趋势加分
        priority_score = 10 - min(chain_count / max(total_chains, 1) * 100, 8)
        if is_declining:
            priority_score += 3
        
        priorities.append({
            "dimension": dim,
            "chain_count": chain_count,
            "strength": strength,
            "priority": round(priority_score, 1),
            "trend": trend_info.get("trend", "未知"),
            "declining": is_declining,
            "urgent": is_declining or chain_count < total_chains * 0.02
        })
    
    # 按优先级排序
    priorities.sort(key=lambda x: -x["priority"])
    
    return priorities

def generate_brief():
    """生成维度健康简报文本（供API context注入）"""
    agg = compute_aggregate()
    if not agg:
        return "维度汇聚: 无数据"
    
    lines = []
    lines.append(f"维度汇聚: {agg['dimension_count']}维活跃, {agg['weak_count']}维弱, 总{agg['total_chains']}链")
    
    if agg.get("priorities"):
        top_p = agg["priorities"][:3]
        lines.append("优先级→" + " > ".join(
            [f"{p['dimension']}({p['priority']})" for p in top_p]
        ))
    
    if agg.get("trends"):
        improving = [d for d, t in agg["trends"].items() if t.get("improving")]
        declining = [d for d, t in agg["trends"].items() if t.get("declining")]
        if improving:
            lines.append("好转: " + ", ".join(improving[:3]))
        if declining:
            lines.append("恶化: ⚠️" + ", ".join(declining[:3]))
    
    return " | ".join(lines)

def get_focus_recommendation():
    """返回建议聚焦的维度（供daemon决策）"""
    agg = compute_aggregate()
    if not agg or not agg.get("priorities"):
        return None
    
    # 取最高优先级且urgent的维度
    urgent = [p for p in agg["priorities"] if p.get("urgent")]
    if urgent:
        return urgent[0]
    
    # 否则取优先级最高的
    return agg["priorities"][0] if agg["priorities"] else None

if __name__ == "__main__":
    print("=== 维度汇聚简报 ===")
    print(generate_brief())
    print()
    rec = get_focus_recommendation()
    if rec:
        print(f"建议聚焦: {rec['dimension']} (优先级{rec['priority']})")
