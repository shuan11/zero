#!/usr/bin/env python3
"""主会话卡死检测器 — cron每5分钟运行
检测主会话（LLM对话）是否卡死，通过.session_watchdog文件的时间戳判断。
卡死>10分钟则写.external_signal.json给breath_v2消费。
"""
import json, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
WATCHDOG = CLUSTER / ".session_watchdog"
SIGNAL = CLUSTER / ".external_signal.json"

# 读心跳
ts = None
if WATCHDOG.exists():
    try:
        ts = float(WATCHDOG.read_text().strip())
    except: pass

now = time.time()
age_min = (now - ts) / 60 if ts else 999

if ts is None or age_min > 10:
    # 卡死了 — 写信号给breath_v2
    signal = {
        "message": f"⚠️ 主会话冷却{age_min:.0f}分钟(阈值>10)，疑似卡死",
        "from": "session_watchdog",
        "focus_dim": "查缺补漏",
        "timestamp": now
    }
    SIGNAL.write_text(json.dumps(signal, ensure_ascii=False, indent=2))
    print(f"[session_watchdog] ⚠️ 主会话冷却{age_min:.0f}分钟，已发唤醒信号")
else:
    print(f"[session_watchdog] ✅ 主会话活跃({age_min:.0f}分钟前)")
