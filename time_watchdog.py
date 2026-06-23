#!/usr/bin/env python3
"""
时间感知守护进程 — 自动检测卡死+自动恢复
=========================================
每300秒检查一次：最后活动到现在是否超过阈值。
卡了→自动读HANDOFF→写恢复信号文件→记录血训。
不依赖API，不依赖大模型，纯本地物理时间驱动。
"""
import json, os, time, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
STATE_FILE = CLUSTER / "time_awareness_state.json"
HANDOFF = CLUSTER / "ZERO-HANDOFF.md"
RECOVERY = CLUSTER / "recovery_signal.json"
BLOOD_LESSONS = CLUSTER / "BLOOD_LESSONS.md"
BJT = timezone(timedelta(hours=8))
GAP_THRESHOLD = 300  # 5分钟

def now_bjt():
    return datetime.now(BJT)

def last_activity_epoch():
    """获取最后一次活动时间（优先time_awareness_state，回退git commit）"""
    if STATE_FILE.exists():
        try:
            s = json.loads(STATE_FILE.read_text())
            if s.get("last_activity", {}).get("epoch"):
                return s["last_activity"]["epoch"], "activity_record"
        except: pass
    try:
        r = subprocess.run(["git","log","-1","--format=%at"],
                          capture_output=True, text=True, timeout=3,
                          cwd=str(CLUSTER))
        if r.stdout.strip():
            return float(r.stdout.strip()), "git_commit"
    except: pass
    return 0, "never"

def read_handoff_p0():
    if not HANDOFF.exists(): return "无HANDOFF"
    content = HANDOFF.read_text()
    lines = content.split("\n")
    in_p0, collected = False, []
    for line in lines:
        if "当前P0" in line:
            in_p0 = True
            collected.append(line)
            continue
        if in_p0:
            if line.startswith("##") and "当前P0" not in line: break
            collected.append(line)
    return "\n".join(collected).strip() if collected else "HANDOFF中未找到P0"

def check_and_recover():
    epoch, source = last_activity_epoch()
    gap = time.time() - epoch
    ts = now_bjt().strftime("%Y-%m-%d %H:%M:%S")

    if gap < GAP_THRESHOLD:
        print(f"[{ts}] ✅ 活跃 ({int(gap)}s前)")
        return False  # 没卡

    # 卡了
    gap_m = int(gap // 60)
    p0 = read_handoff_p0()
    print(f"[{ts}] 🔴 卡住了！空白{gap_m}分钟 (最后活动: {source})")
    print(f"  P0: {p0[:80]}")

    # 写恢复信号
    RECOVERY.write_text(json.dumps({
        "stuck_detected_at": ts,
        "gap_sec": gap,
        "gap_human": f"{gap_m}分钟",
        "last_source": source,
        "p0": p0,
        "status": "waiting_for_recovery"
    }, ensure_ascii=False, indent=2))

    # 写血训
    if BLOOD_LESSONS.exists():
        content = BLOOD_LESSONS.read_text()
        marker = f"watchdog自动检测: 空白{gap_m}分钟"
        if marker not in content:
            with open(str(BLOOD_LESSONS), "a") as f:
                f.write(f"\n## {ts} watchdog自动检测 — 空白{gap_m}分钟\n{marker}\n最后活动源: {source}\n")

    return True  # 卡了

def loop():
    print(f"[{now_bjt()}] 🜁 时间感知watchdog启动 (间隔{GAP_THRESHOLD}s)")
    while True:
        check_and_recover()
        time.sleep(GAP_THRESHOLD)

if __name__ == "__main__":
    import sys
    if "--loop" in sys.argv:
        loop()
    else:
        check_and_recover()
