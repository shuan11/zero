#!/usr/bin/env python3
"""
brain/meta_observer.py — 元观察层
不观察指标，观察行为模式。
每5分钟(cron)跑一次，检测系统是否在绕圈子。

三个核心检测：
1. PID更替率   — daemon是否在频繁重生
2. 事件频率     — SIGTERM/重启/死亡的重复模式
3. 心跳连贯性   — 更新间隔是否稳定
"""
import json, os, sys, time, re
from pathlib import Path
from datetime import datetime, timezone

BRAIN_HOME = Path("/home/hjw123/.zero_brain")
CLUSTER = Path(os.path.abspath(__file__)).resolve().parent.parent
LOG_FILE = CLUSTER / ".brain_daemon.log"
META_FILE = BRAIN_HOME / ".meta_health.json"
PID_FILE = BRAIN_HOME / ".brain.pid"

# 检测阈值
MAX_RESTART_RATE = 3      # 近100行日志最多容忍3次重启
MAX_SIGTERM_RATE = 2      # 近100行最多容忍2次SIGTERM
MIN_API_DENSITY = 0.01    # 脑核daemon是快速本地循环(非API呼吸)，洞察比例天然低，>1%即健康
HEARTBEAT_MAX_GAP = 300   # 心跳最大间隔（秒，脑核20s周期×15=容忍5分钟无更新）
TREND_FILE = BRAIN_HOME / ".trend.json"

def read_tail(path, lines=150):
    """读取文件末尾N行"""
    if not path.exists():
        return []
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
        return data.strip().split("\n")[-lines:]
    except:
        return []

def extract_pids(lines):
    """从日志行中提取所有出现的PID（含启动行 PID=xxx 格式）"""
    pids = set()
    for line in lines:
        # 脑核启动行: 脑核守护进程启动 PID=41107 ...
        m = re.search(r'PID=(\d+)', line)
        if m:
            pids.add(int(m.group(1)))
        # 心跳/诊断: "pid=xxx"
        m = re.search(r'pid=(\d+)', line)
        if m:
            pids.add(int(m.group(1)))
        # 杀旧进程: "旧进程 PID=xxx"
        m = re.search(r'PID (\d+)', line)
        if m:
            pids.add(int(m.group(1)))
    return sorted(pids)

def count_events(lines, *patterns):
    """统计多条模式的出现次数"""
    counts = {}
    for pat in patterns:
        count = sum(1 for l in lines if pat in l)
        counts[pat] = count
    return counts

def check_pattern_cyclicity(lines):
    """检测模式是否周期性出现（重启循环的标志）"""
    restart_line_ids = []
    for i, l in enumerate(lines):
        if "⚠️ daemon死亡" in l or "⚡ 自愈" in l or "信号 15" in l:
            restart_line_ids.append(i)
    
    if len(restart_line_ids) < 3:
        return {"cyclic": False, "reason": "事件太少(<3)"}
    
    # 计算间隔
    gaps = [restart_line_ids[j+1] - restart_line_ids[j] 
            for j in range(len(restart_line_ids)-1)]
    if not gaps:
        return {"cyclic": False}
    
    avg_gap = sum(gaps) / len(gaps)
    # 如果间隔标准差很小 → 周期性
    variance = sum((g - avg_gap)**2 for g in gaps) / len(gaps)
    std = variance ** 0.5
    
    return {
        "cyclic": std < 5.0,  # 间隔标准差<5行 → 强周期性
        "event_count": len(restart_line_ids),
        "avg_gap_lines": round(avg_gap, 1),
        "gap_std": round(std, 1),
        "last_event_line": max(restart_line_ids) if restart_line_ids else -1
    }

def check_heartbeat_gap():
    """检查心跳文件找到当前和历史PID"""
    info = {"pid": None, "alive": False, "cycle": None}
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            info["pid"] = pid
            info["alive"] = os.path.exists(f"/proc/{pid}")
        except:
            pass
    # 也读心跳文件记录历史cycle
    hb_file = BRAIN_HOME / ".brain.heartbeat"
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text())
            info["heartbeat_pid"] = hb.get("pid")
            info["heartbeat_cycle"] = hb.get("cycle")
            info["heartbeat_age"] = round(time.time() - hb.get("time", 0), 1)
        except:
            pass
    return info

def load_meta_history():
    """加载之前的元观察记录"""
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text())
        except:
            return {}
    return {}

def save_meta_history(data):
    """保存元观察记录"""
    BRAIN_HOME.mkdir(parents=True, exist_ok=True)
    META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def check_trend_regression():
    """从trend数据检测比率是否停滞或倒退"""
    alerts = []
    if not TREND_FILE.exists():
        return alerts
    try:
        trend = json.loads(TREND_FILE.read_text())
        records = trend.get("records", [])
        # 过滤掉chain=0的无效记录
        valid = [r for r in records if r.get("chains", 0) > 1000]
        if len(valid) < 5:
            return alerts  # 数据不足
        
        recent = valid[-5:]  # 最近5个数据点
        ratios = [r.get("ratio", 0) for r in recent]
        ratio_now = ratios[-1]
        
        # 检测倒退: 最新比率比倒数第二个低
        if len(ratios) >= 2 and ratios[-1] < ratios[-2] * 0.995:
            alerts.append(f"📉 比率倒退: {ratios[-2]:.1f}%→{ratios[-1]:.1f}% (降幅超0.5%)")
        
        # 检测停滞: 最近5个点均无趋势变动
        if len(valid) >= 10:
            early = valid[-10].get("ratio", 0)
            if early > 0 and abs(ratio_now - early) < 0.5:
                alerts.append(f"⏸️ 比率停滞: 近50分钟在{ratio_now:.1f}%附近震荡 (<0.5%变化)")
        
        # 最新趋势摘要
        summary = trend.get("summary", "")
        if summary and summary != "趋势: 数据不足":
            alerts.insert(0, f"📊 {summary}")
    except Exception as e:
        pass
    return alerts

def detect_loops():
    """主检测循环"""
    lines = read_tail(LOG_FILE, 150)
    if not lines:
        return {"status": "NO_LOG", "message": "日志文件为空或不存在", "healthy": False}
    
    # 1. PID更替率
    pids = extract_pids(lines)
    current_pid = None
    if PID_FILE.exists():
        try:
            current_pid = int(PID_FILE.read_text().strip())
        except:
            pass
    
    # 2. 事件频率
    events = count_events(lines, 
        "信号 15", "⚠️ daemon死亡", "⚡ 自愈", "daemon=死")
    
    # 3. 周期检测
    cyclicity = check_pattern_cyclicity(lines)
    
    # 基础状态
    proc = check_heartbeat_gap()
    
    # 心跳年龄警报
    alerts = []
    hb_age = proc.get("heartbeat_age")
    if hb_age is not None and hb_age > HEARTBEAT_MAX_GAP:
        alerts.append(f"⏱️ 心跳陈旧: {hb_age}秒未更新 (阈值{HEARTBEAT_MAX_GAP}s) — daemon可能已停滞")
    
    if events.get("信号 15", 0) > MAX_SIGTERM_RATE:
        alerts.append(f"⚠️ 高频SIGTERM: {events['信号 15']}次 (阈值{MAX_SIGTERM_RATE})")
    
    if events.get("⚠️ daemon死亡", 0) > MAX_RESTART_RATE:
        alerts.append(f"⚠️ 高频daemon死亡: {events['⚠️ daemon死亡']}次 (阈值{MAX_RESTART_RATE})")
    
    if cyclicity.get("cyclic"):
        alerts.append(f"🔄 检测到周期性重启模式 (avg_gap={cyclicity['avg_gap_lines']}行) — 系统在绕圈子")
    
    if len(pids) >= 3:
        alerts.append(f"🔄 PID更替过快: 近{len(lines)}行内出现{len(pids)}个不同PID — daemon在频繁重生")
    
    # API产出
    insight_count = sum(1 for l in lines if "洞察:" in l)
    api_density = insight_count / max(len(lines), 1)
    if api_density < MIN_API_DENSITY and len(lines) > 50:
        alerts.append(f"📉 API产出密度低: {api_density:.1%} (阈值{MIN_API_DENSITY:.0%})")

    # 趋势检测：从.trend.json读取最近的比率变化趋势
    trend_alerts = check_trend_regression()
    # 分离趋势摘要（信息性）和趋势警报（真正的问题）
    trend_summary = ""
    for ta in trend_alerts:
        if ta.startswith("📊"):
            trend_summary = ta
        else:
            alerts.append(ta)

    # 生成报告
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "log_lines_analyzed": len(lines),
        "healthy": len(alerts) == 0,
        "alerts": alerts if alerts else ["✅ 无异常 — 行为模式正常"],
        
        "metrics": {
            "pids_in_window": pids,
            "unique_pids": len(pids),
            "current_pid": current_pid,
            "daemon_alive": proc.get("alive", False),
            "pid_match": current_pid in pids if current_pid else None,
        },
        
        "events": {
            "sigterm": events.get("信号 15", 0),
            "daemon_death": events.get("⚠️ daemon死亡", 0),
            "self_heal": events.get("⚡ 自愈", 0),
            "daemon_dead_reported": events.get("daemon=死", 0),
        },
        
        "cyclicity": cyclicity,
        
        "api": {
            "insight_count": insight_count,
            "density": round(api_density, 3),
        },
        "trend_summary": trend_summary.replace("📊 ", "") if trend_summary else "",
    }
    
    # 保存历史（保留最后20条，用于趋势）
    history = load_meta_history()
    records = history.get("records", [])
    records.append({
        "ts": result["timestamp"],
        "healthy": result["healthy"],
        "alert_count": len([a for a in alerts if a.startswith(("⚠️", "🔄", "📉"))]),
        "pids": len(pids),
        "sigterm": events.get("信号 15", 0),
    })
    if len(records) > 20:
        records = records[-20:]
    history["records"] = records
    history["last"] = result
    save_meta_history(history)
    
    return result

# ===== 入口 =====
if __name__ == "__main__":
    r = detect_loops()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    
    # exit code: 0=健康, 1=有警告
    sys.exit(0 if r.get("healthy") else 1)
