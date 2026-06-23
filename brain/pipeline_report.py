"""
动作管道报告 — Action Pipeline Report
═══════════════════════════════════════════
P138: 全管道可见性——从注册到验证的完整状态报告。

汇聚:
- 当前目标(.brain_goal.json)
- 动作队列状态(action_registry)
- 协调结果(coordinator)
- 验证结果(action_verifier)
- 基因组变化(genome)
- 执行历史

输出: 统一的 .brain_pipeline_report.json + 控制台摘要
"""
import json, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
REPORT_FILE = CLUSTER / ".brain_pipeline_report.json"


def generate_pipeline_report(log=None):
    """
    生成完整的动作管道状态报告。
    
    收集所有模块的状态 → 统一输出
    """
    log_fn = log or (lambda x: None)
    
    report = {
        "timestamp": time.time(),
        "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "goal": _get_goal_status(),
        "coordinator": _get_coordinator_status(),
        "action_queue": _get_action_queue_status(),
        "verifier": _get_verifier_status(),
        "pipeline_health": _calc_pipeline_health(),
    }
    
    # 持久化
    REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    
    # 生成摘要
    health = report["pipeline_health"]
    summary = (
        f"管道: goal={report['goal']['type']} "
        f"focus={report['goal']['focus']} "
        f"actions={report['action_queue']['pending']}/{report['action_queue']['total']} "
        f"coord={report['coordinator']['status']} "
        f"verify={report['verifier']['status']} "
        f"health={health['emoji']} {health['label']}"
    )
    log_fn(f"  管道: {summary}")
    
    return report


def _get_goal_status():
    """读取目标状态"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        if not gf.exists():
            return {"type": "无", "focus": "无", "description": "未设定", "adapted": False}
        g = json.loads(gf.read_text(encoding="utf-8"))
        return {
            "type": g.get("goal_type", "?"),
            "focus": g.get("focus_dim", "无"),
            "description": g.get("description", ""),
            "adapted": g.get("_feedback_adapted", False),
            "reason": g.get("reason", ""),
        }
    except:
        return {"type": "error", "focus": "?", "description": "读取失败"}


def _get_coordinator_status():
    """读取协调器状态"""
    try:
        from brain.coordinator import get_coord_status
        cs = get_coord_status()
        if cs.get("recent_coordination"):
            s = cs.get("suppressed_total", 0)
            c = cs.get("conflicts", 0)
            t = cs.get("actions_total", 0)
            if s > 0 or c > 0:
                status = f"⚠️ 抑制{s}冲突{c}({t}总)"
                return {"status": status, "suppressed": s, "conflicts": c, "total": t, "healthy": False}
            return {"status": "✅ 无冲突", "suppressed": 0, "conflicts": 0, "total": t, "healthy": True}
        return {"status": "待机", "suppressed": 0, "conflicts": 0, "total": 0, "healthy": True}
    except:
        return {"status": "error", "healthy": False}


def _get_action_queue_status():
    """读取动作队列状态"""
    try:
        from brain.action_registry import get_queue_status
        qs = get_queue_status()
        return {
            "total": qs.get("total", 0),
            "pending": qs.get("pending", 0),
            "by_type": qs.get("by_type", {}),
        }
    except:
        return {"total": 0, "pending": 0, "by_type": {}}


def _get_verifier_status():
    """读取验证器状态"""
    try:
        from brain.action_verifier import get_verify_report
        vr = get_verify_report()
        ok = vr.get("ok", 0)
        fail = vr.get("fail", 0)
        total = ok + fail
        if total == 0:
            return {"status": "待机", "ok": 0, "fail": 0, "healthy": True}
        if fail > 0:
            return {"status": f"⚠️ {fail}失败/{total}总", "ok": ok, "fail": fail, "healthy": False}
        return {"status": f"✅ {ok}/{total}通过", "ok": ok, "fail": 0, "healthy": True}
    except:
        return {"status": "error", "ok": 0, "fail": 0, "healthy": False}


def _calc_pipeline_health():
    """
    计算管道综合健康度。
    
    加权:
    - 协调器无冲突=+2, 有冲突=-1
    - 验证器全通过=+2, 有失败=-2
    - 目标已适应=+1
    - 队列阻塞=0
    """
    score = 0
    labels = []
    
    # 协调器
    cs = _get_coordinator_status()
    if cs.get("healthy", True):
        score += 2
        labels.append("协调✅")
    else:
        score -= 1
        labels.append(f"协调⚠️({cs.get('suppressed',0)}抑)")
    
    # 验证器
    vs = _get_verifier_status()
    if vs.get("healthy", True):
        score += 2
        labels.append("验证✅")
    else:
        score -= 2
        labels.append(f"验证❌({vs.get('fail',0)}败)")
    
    # 目标适应
    goal = _get_goal_status()
    if goal.get("adapted"):
        score += 1
        labels.append("目标适应")
    
    # 队列
    qs = _get_action_queue_status()
    if qs.get("pending", 0) > 5:
        labels.append(f"队列⏳({qs['pending']})")
    
    if score >= 3:
        emoji = "🟢"
        label = "健康"
    elif score >= 0:
        emoji = "🟡"
        label = "注意"
    else:
        emoji = "🔴"
        label = "异常"
    
    return {
        "score": score,
        "emoji": emoji,
        "label": label,
        "details": " | ".join(labels),
    }


def get_report_summary():
    """获取最近报告摘要"""
    try:
        data = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        return data
    except:
        return {}


if __name__ == "__main__":
    report = generate_pipeline_report(print)
    print(f"\n管道健康: {report['pipeline_health']['emoji']} {report['pipeline_health']['label']}")
    print(f"详情: {report['pipeline_health']['details']}")
