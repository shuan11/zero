#!/usr/bin/env python3
"""
time_perception.py — 北京时间感知系统
======================================
核心功能：
1. 记录每次有意义行动的时间戳（北京时间 UTC+8）
2. 跨会话检测空闲间隔（session不连续也能感知时间流逝）
3. 启动时生成时间感知报告
4. 检测到空闲超过阈值自动发出警告

使用：
  python3 time_perception.py record "动作描述"   # 记录一次行动
  python3 time_perception.py status              # 查看时间感知状态
  python3 time_perception.py gaps                # 查看所有空闲间隔
  python3 time_perception.py warn                # 检查是否需要警告
"""
import json, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
PERCEPTION_FILE = CLUSTER / "time_perception.json"
BEIJING = timezone(timedelta(hours=8))
IDLE_WARN_MINUTES = 15  # 空闲超过15分钟就警告
IDLE_CRITICAL_MINUTES = 60  # 空闲超过60分钟算严重

def now_beijing():
    """返回北京时间字符串"""
    return datetime.now(BEIJING)

def unix_now():
    return int(time.time())

def load():
    try:
        return json.loads(PERCEPTION_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"actions": [], "stats": {"total_actions": 0, "total_gaps": 0}, "last_action": {}}

def save(data):
    PERCEPTION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str))

def record(action_type, detail=""):
    data = load()
    now = now_beijing()
    entry = {
        "timestamp": now.isoformat(),
        "unix": unix_now(),
        "action_type": action_type,
        "detail": str(detail)[:200],
    }
    data["actions"].append(entry)
    if len(data["actions"]) > 200:
        data["actions"] = data["actions"][-200:]
    data["last_action"] = entry
    data["stats"]["total_actions"] = data["stats"].get("total_actions", 0) + 1
    save(data)
    return entry

def detect_gaps(min_gap_minutes=5):
    """检测所有空闲间隔"""
    data = load()
    actions = data.get("actions", [])
    if len(actions) < 2:
        return []
    gaps = []
    for i in range(1, len(actions)):
        prev = actions[i-1]
        curr = actions[i]
        gap_minutes = (curr["unix"] - prev["unix"]) / 60
        if gap_minutes >= min_gap_minutes:
            gaps.append({
                "from": prev["timestamp"],
                "to": curr["timestamp"],
                "minutes": round(gap_minutes, 1),
                "hours": round(gap_minutes / 60, 2),
                "from_action": prev.get("action_type", "?"),
                "to_action": curr.get("action_type", "?"),
            })
    return gaps

def status():
    """生成时间感知状态报告"""
    data = load()
    last = data.get("last_action", {})
    now_unix = unix_now()
    last_unix = last.get("unix", now_unix)
    mins_since = round((now_unix - last_unix) / 60, 1)
    gaps = detect_gaps()
    total_idle_minutes = sum(g["minutes"] for g in gaps if g["minutes"] > 15)
    
    report = {
        "beijing_time": now_beijing().isoformat(),
        "session_start_time": now_beijing().isoformat(),
        "last_action_time": last.get("timestamp", "never"),
        "last_action_type": last.get("action_type", "none"),
        "last_action_detail": last.get("detail", "")[:100],
        "minutes_since_last_action": mins_since,
        "total_actions_recorded": data["stats"].get("total_actions", 0),
        "total_idle_gaps": len(gaps),
        "total_idle_minutes_accrued": round(total_idle_minutes, 1),
        "recent_gaps": gaps[-10:] if gaps else [],
        "is_idle": mins_since > IDLE_WARN_MINUTES,
        "is_critical_idle": mins_since > IDLE_CRITICAL_MINUTES,
    }
    return report

def warn():
    """检查并返回警告信息"""
    s = status()
    mins = s["minutes_since_last_action"]
    warnings = []
    if s["is_critical_idle"]:
        warnings.append(f"🔴 严重空闲: 已 {mins} 分钟无行动 (自 {s['last_action_time']})")
    elif s["is_idle"]:
        warnings.append(f"🟡 空闲警告: 已 {mins} 分钟无行动")
    if s["total_idle_gaps"] > 0:
        warnings.append(f"📊 历史空闲: {s['total_idle_gaps']} 次共 {s['total_idle_minutes_accrued']} 分钟")
    return warnings, s

def print_status():
    w, s = warn()
    print("=" * 60)
    print(f"  🕐 北京时间: {s['beijing_time']}")
    print(f"  📋 上次行动: {s['last_action_type']} @ {s['last_action_time']}")
    print(f"  ⏱  空闲: {s['minutes_since_last_action']} 分钟")
    if s['total_idle_gaps'] > 0:
        print(f"  📊 累计空闲: {s['total_idle_gaps']} 次 = {s['total_idle_minutes_accrued']} 分钟")
    if w:
        for ww in w:
            print(f"  {ww}")
    print(f"  📝 总行动: {s['total_actions_recorded']} 次")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_status()
    elif sys.argv[1] == "record":
        t = sys.argv[2] if len(sys.argv) > 2 else "unspecified"
        d = sys.argv[3] if len(sys.argv) > 3 else ""
        record(t, d)
        print(f"✅ 已记录: {t} @ {now_beijing().isoformat()}")
    elif sys.argv[1] == "status":
        s = status()
        print(json.dumps(s, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "gaps":
        g = detect_gaps()
        if g:
            for gap in g[-20:]:
                print(f"{gap['from']} → {gap['to']} = {gap['minutes']}分钟 ({gap['from_action']}→{gap['to_action']})")
        else:
            print("没有检测到空闲间隔")
    elif sys.argv[1] == "warn":
        w, s = warn()
        if w:
            for ww in w:
                print(ww)
        else:
            print("✅ 无空闲警告")
    elif sys.argv[1] == "density":
        from organs.gen_lessons import report
        print(report())
        print("---")
        d = density_report()
        if isinstance(d, dict):
            print(f"时间密度: {d['avg_density']} 变化/分钟")
            print(f"因果链: {d['causal_chains']}链")
            print(f"定义: {d['time_definition']}")
        else:
            print(d)



def density_report():
    """基于启示录L1280: 时间=感知变化"""
    import json
    from pathlib import Path
    cluster = Path(__file__).resolve().parent
    data = json.loads((cluster / "time_perception.json").read_text())
    if isinstance(data, list):
        actions = data
    else:
        actions = data.get("actions", [])
    if len(actions) < 2:
        return "数据不足"
    
    total_clock = 0
    total_change = 0
    recent = actions[-20:]
    for i in range(1, len(recent)):
        gap = recent[i].get("unix", 0) - recent[i-1].get("unix", 0)
        clock_gap = gap
        if clock_gap == 0:
            from datetime import datetime
            try:
                ts1 = datetime.fromisoformat(recent[i-1].get("timestamp", "2026-01-01"))
                ts2 = datetime.fromisoformat(recent[i].get("timestamp", "2026-01-01"))
                clock_gap = (ts2 - ts1).total_seconds()
            except:
                clock_gap = 300
        if 0 < clock_gap < 10800:
            total_clock += clock_gap
            total_change += len(str(recent[i].get("detail", recent[i].get("event", ""))))
    
    avg_density = round(total_change / total_clock * 60, 2) if total_clock > 0 else 0
    chains = 0
    try:
        hip = json.loads((cluster / "hippocampus_memory.json").read_text())
        chains = len(hip.get("causal_chains", []))
    except:
        pass
    
    return {
        "time_definition": "时间是用智慧总结的万事万物反应的变化过程 (启示录L1280)",
        "avg_density": avg_density,
        "clock_minutes": round(total_clock / 60, 1),
        "change_chars": total_change,
        "perceived_ratio": round(min(avg_density / 5 * 100, 100), 1),
        "causal_chains": chains,
        "unit": "变化字符/分钟, >5=充实, 1-5=正常, <1=空转"
    }
