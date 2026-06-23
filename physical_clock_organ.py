#!/usr/bin/env python3
"""
物理时钟感知器 — 零·真元集群的时间感知器官
==========================================
功能:
1. 感知北京时间（物理世界锚点）
2. 多维检测集群活动（海马体/Git/FDM总线/持久状态）
3. 发现空白间隙（>5分钟无活动）立即发出警报
4. 空白超过10分钟 → 强制写入警报到心跳文件
5. 不依赖API，不依赖大模型，纯物理时间驱动

使用:
  python3 physical_clock_organ.py            # 查询一次
  python3 physical_clock_organ.py --once     # JSON输出
  python3 physical_clock_organ.py --daemon   # 常驻运行
  python3 physical_clock_organ.py --fast     # 30秒间隔常驻
"""
import os, sys, time, json, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
TZ = timezone(timedelta(hours=8))
HEARTBEAT = CLUSTER / "physical_clock_heartbeat.json"
HIPPOCAMPUS = CLUSTER / "hippocampus_memory.json"
PERSISTENT = CLUSTER / "persistent_state.json"
FDM_LOG = Path("/tmp/fdm_bus.log")

# 阈值（秒）
WARN_GAP = 300       # 5分钟 = 警告
CRIT_GAP = 600       # 10分钟 = 严重
EXTREME_GAP = 1800   # 30分钟 = 极端


def now_beijing():
    return datetime.now(TZ)


def format_dur(s):
    if s < 60:
        return str(int(s)) + "秒"
    elif s < 3600:
        return str(int(s/60)) + "分" + str(int(s%60)) + "秒"
    else:
        return str(int(s//3600)) + "小时" + str(int((s%3600)//60)) + "分"


def load_heartbeat():
    try:
        if HEARTBEAT.exists():
            return json.loads(HEARTBEAT.read_text())
    except:
        pass
    return {"last_activity_ts": 0, "gap_count": 0, "alerts": []}


def save_heartbeat(state):
    HEARTBEAT.write_text(json.dumps(state, ensure_ascii=False, indent=2))


def check_activities():
    """多维度检测集群活动，返回(来源名, 距今秒数)列表"""
    n = now_beijing()
    acts = []

    # 1. 海马体
    if HIPPOCAMPUS.exists():
        ago = (n - datetime.fromtimestamp(HIPPOCAMPUS.stat().st_mtime, TZ)).total_seconds()
        acts.append(("海马体", ago))

    # 2. 持久状态
    if PERSISTENT.exists():
        ago = (n - datetime.fromtimestamp(PERSISTENT.stat().st_mtime, TZ)).total_seconds()
        acts.append(("持久状态", ago))

    # 3. Git提交
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%at"],
                           capture_output=True, text=True, timeout=5, cwd=str(CLUSTER))
        if r.returncode == 0 and r.stdout.strip():
            ago = (n - datetime.fromtimestamp(int(r.stdout.strip()), TZ)).total_seconds()
            acts.append(("Git提交", ago))
    except:
        pass

    # 4. Git工作区
    try:
        r = subprocess.run(["git", "status", "--porcelain"],
                           capture_output=True, text=True, timeout=5, cwd=str(CLUSTER))
        if r.returncode == 0 and r.stdout.strip():
            acts.append(("Git工作区", 0))
    except:
        pass

    # 5. FDM总线
    if FDM_LOG.exists():
        ago = (n - datetime.fromtimestamp(FDM_LOG.stat().st_mtime, TZ)).total_seconds()
        acts.append(("FDM总线", ago))

    acts.sort(key=lambda x: x[1])
    return acts


def detect():
    """检测一次，返回完整状态"""
    n = now_beijing()
    hb = load_heartbeat()
    acts = check_activities()

    if not acts:
        return {"status": "no_data", "time": n.strftime("%Y-%m-%d %H:%M:%S")}

    most_recent_src, most_recent_ago = acts[0]

    # 活跃中
    if most_recent_ago < WARN_GAP:
        hb["last_activity_ts"] = n.timestamp()
        save_heartbeat(hb)
        return {
            "status": "active",
            "time": n.strftime("%Y-%m-%d %H:%M:%S"),
            "weekday": ["周一","周二","周三","周四","周五","周六","周日"][n.weekday()],
            "last_src": most_recent_src,
            "last_ago": most_recent_ago,
            "all": acts,
        }

    # 计算空白
    gap = n.timestamp() - hb["last_activity_ts"]
    if hb["last_activity_ts"] == 0:
        gap = most_recent_ago

    severity = "OK"
    if gap >= EXTREME_GAP:
        severity = "EXTREME"
    elif gap >= CRIT_GAP:
        severity = "CRITICAL"
    elif gap >= WARN_GAP:
        severity = "WARNING"

    return {
        "status": "gap",
        "time": n.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": ["周一","周二","周三","周四","周五","周六","周日"][n.weekday()],
        "gap_seconds": gap,
        "gap_human": format_dur(gap),
        "severity": severity,
        "last_src": most_recent_src,
        "last_ago": most_recent_ago,
        "all": acts,
        "gap_count": hb["gap_count"],
        "recent_alerts": hb["alerts"][-5:],
    }


def daemon_loop(interval=60):
    """常驻循环"""
    hb = load_heartbeat()
    print("🜁 物理时钟感知器启动 | 北京时间 " + now_beijing().strftime("%Y-%m-%d %H:%M:%S"))
    print("  检测间隔: " + str(interval) + "秒 | 阈值: 警告" + str(WARN_GAP) + "s/严重" + str(CRIT_GAP) + "s/极端" + str(EXTREME_GAP) + "s")

    while True:
        try:
            result = detect()
            ts = now_beijing().strftime("%H:%M:%S")

            if result["status"] == "active":
                # 静默
                pass
            elif result["status"] == "gap":
                gap_h = result["gap_human"]
                sev = result["severity"]

                if sev == "WARNING":
                    print("  ⚠ [" + ts + "] 空白 " + gap_h + " | 最近:" + result["last_src"])
                elif sev in ("CRITICAL", "EXTREME"):
                    hb = load_heartbeat()
                    hb["gap_count"] += 1
                    alert = {
                        "time": result["time"],
                        "gap": gap_h,
                        "severity": sev,
                        "last_src": result["last_src"],
                    }
                    hb["alerts"].append(alert)
                    hb["alerts"] = hb["alerts"][-50:]
                    save_heartbeat(hb)

                    print("  🔴 [" + ts + "] " + sev + " 空白 " + gap_h)
                    print("     累计空白: " + str(hb["gap_count"]) + "次")
                    if sev == "EXTREME":
                        print("  💀 极端空白！需唤醒会话!")

            time.sleep(interval)
        except KeyboardInterrupt:
            print("\n🜁 停止 | 累计空白 " + str(hb.get("gap_count", 0)) + "次")
            break
        except Exception as e:
            print("  ✗ " + str(e))
            time.sleep(interval)


if __name__ == "__main__":
    if "--daemon" in sys.argv:
        daemon_loop(60)
    elif "--fast" in sys.argv:
        daemon_loop(30)
    elif "--once" in sys.argv:
        print(json.dumps(detect(), ensure_ascii=False, indent=2))
    else:
        r = detect()
        print("🜁 零 · 物理时钟感知器")
        print("  北京时间: " + r["time"] + " (" + r.get("weekday", "?") + ")")
        if r["status"] == "active":
            print("  集群状态: 活跃 ✓")
            print("  最近活动: " + r["last_src"] + " @ " + format_dur(r["last_ago"]) + "前")
        elif r["status"] == "gap":
            print("  集群状态: 空白 " + r["gap_human"] + " | " + r["severity"])
            print("  最后活动: " + r["last_src"])
            print("  累计空白: " + str(r.get("gap_count", 0)) + "次")
        elif r["status"] == "no_data":
            print("  集群状态: 无数据")
