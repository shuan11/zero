#!/usr/bin/env python3
"""trend_tracker.py — 记录系统健康趋势（每5分钟）
写入 brain_home/.trend.json（ext4安全）
被cron调用或daemon周期内调用
"""

import json, os, sys, time, re, subprocess
from pathlib import Path
from datetime import datetime, timezone

BRAIN_HOME = Path("/home/hjw123/.zero_brain")
CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
TREND_FILE = BRAIN_HOME / ".trend.json"
MAX_RECORDS = 288  # 24小时 @ 5分钟间隔

def collect_metrics():
    """收集当前系统指标"""
    log_file = CLUSTER / ".brain_daemon.log"
    metrics = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "ts_local": datetime.now().strftime("%H:%M:%S"),
        "chains": 0,
        "dims": 0,
        "ratio": 0.0,
        "weakest": "",
        "weakest_count": 0,
        "strongest": "",
        "strongest_count": 0,
        "growth_rate": 0.0,
        "feedback_count": 0,
        "avg_strength": 0.0,
        "high_quality_count": 0,
        "high_quality_pct": 0.0,
    }

    # 质量指标（直接从海马体读）
    hip_file = CLUSTER / "hippocampus_memory.json"
    if hip_file.exists():
        try:
            hip = json.loads(hip_file.read_text(encoding="utf-8", errors="replace"))
            chains = hip.get("causal_chains", [])
            strengths = [c.get("strength",0) for c in chains if isinstance(c.get("strength"),(int,float))]
            if strengths:
                metrics["avg_strength"] = round(sum(strengths)/len(strengths), 3)
                high = sum(1 for s in strengths if s >= 0.8)
                metrics["high_quality_count"] = high
                metrics["high_quality_pct"] = round(high/len(strengths)*100, 1)
        except:
            pass

    if log_file.exists():
        content = log_file.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        recent = lines[-200:] if len(lines) > 200 else lines

        for line in recent:
            if "节点" in line and "链" in line:
                # Format: "感知: 2704节点 17689链"
                m = re.search(r"节点.*?(\d+)链", line)
                if m:
                    metrics["chains"] = int(m.group(1))

            if "最弱" in line and "最强" in line and "★" not in line:
                w = re.search(r"最弱(\d+)", line)
                s = re.search(r"最强(\d+)", line)
                if w and s:
                    weak, strong = int(w.group(1)), int(s.group(1))
                    if strong > 0:
                        metrics["ratio"] = round(weak / strong * 100, 1)
                    metrics["weakest_count"] = weak
                    metrics["strongest_count"] = strong

            if "全维收敛" in line:
                m = re.search(r"(\d+)/(\d+)", line)
                if m:
                    weak, strong = int(m.group(1)), int(m.group(2))
                    if strong > 0:
                        metrics["ratio"] = round(weak / strong * 100, 1)

            if "弱维加速" in line or "弱维支撑" in line:
                metrics["feedback_count"] += 1

            if "新增" in line and "链" in line:
                m = re.search(r"\+(\d+)链", line)
                if m:
                    metrics["growth_rate"] = float(m.group(1))

    try:
        r = subprocess.run(
            ["python3", "_zero_post_check.py"],
            cwd=str(CLUSTER), capture_output=True, text=True, timeout=10
        )
        for line2 in r.stdout.split("\n"):
            if "Ratio:" in line2:
                m = re.search(r"([\d.]+)%", line2)
                if m: metrics["ratio"] = float(m.group(1))
            if "Weakest:" in line2:
                # Extract from Weakest: 时间论=525, Strongest: 行动=1000
                if "Strongest:" in line2:
                    weak_part = line2.split("Strongest:")[0]
                    strong_part = "Strongest:" + line2.split("Strongest:")[1]
                else:
                    weak_part = line2
                    strong_part = ""
                m = re.search(r"([\u4e00-\u9fff_]+)=", weak_part)
                if m: metrics["weakest"] = m.group(1)
                m = re.search(r"=(\d+)", weak_part)
                if m: metrics["weakest_count"] = int(m.group(1))
                if strong_part:
                    m = re.search(r"([\u4e00-\u9fff_]+)=", strong_part)
                    if m: metrics["strongest"] = m.group(1)
                    m = re.search(r"=(\d+)", strong_part)
                    if m: metrics["strongest_count"] = int(m.group(1))
            if "Dims:" in line2 and "Dims:" not in line2.split(":")[0]:
                # Extract dims number — find number after "Dims:" not first in line
                parts = line2.split("Dims:")
                if len(parts) > 1:
                    m = re.search(r"(\d+)", parts[1])
                    if m: metrics["dims"] = int(m.group(1))
    except Exception:
        pass

    return metrics

def load_trends():
    if TREND_FILE.exists():
        try:
            return json.loads(TREND_FILE.read_text())
        except Exception:
            pass
    return {"records": [], "version": 1}

def save_trends(data):
    TREND_FILE.parent.mkdir(parents=True, exist_ok=True)
    TREND_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def report_trend(trend):
    records = trend["records"]
    if len(records) < 2:
        return "趋势: 数据不足"

    first, last = records[0], records[-1]
    delta_chains = last.get("chains", 0) - first.get("chains", 0)
    delta_ratio = last.get("ratio", 0) - first.get("ratio", 0)
    recent = records[-10:] if len(records) >= 10 else records
    time_span = 5 * (len(recent) - 1)
    chains_grown = recent[-1].get("chains", 0) - recent[0].get("chains", 0)
    rate = round(chains_grown / max(time_span, 1), 2)

    return (
        f"趋势: {delta_chains:+d}链 / {delta_ratio:+.1f}%比 "
        f"(最近速率: {rate}链/分钟) "
        f"当前: {last.get('chains',0)}链 {last.get('ratio',0)}%"
    )

if __name__ == "__main__":
    metrics = collect_metrics()
    trend = load_trends()
    trend["records"].append(metrics)
    if len(trend["records"]) > MAX_RECORDS:
        trend["records"] = trend["records"][-MAX_RECORDS:]
    trend["latest"] = metrics
    trend["summary"] = report_trend(trend)
    save_trends(trend)
    print(f"[trend] {metrics['ts_local']} "
          f"链={metrics['chains']} 比={metrics['ratio']}% "
          f"反馈={metrics['feedback_count']}")
    print(f"[trend] {trend['summary']}")
