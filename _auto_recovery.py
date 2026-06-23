#!/usr/bin/env python3
"""
卡死强制恢复 — 零的主会话自救机制
每次工具调用后写心跳 + 定时器。超时则自动写唤醒信号。
"""
import json, os, time, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
WATCHDOG = CLUSTER / ".session_watchdog"
RECOVERY = CLUSTER / ".recovery_signal.json"

now = time.time()

# 模式1: 读心跳检测卡死
if WATCHDOG.exists():
    try:
        ts = float(WATCHDOG.read_text().strip())
        age = now - ts
        if age > 300:  # 5分钟无心跳 → 卡死
            recovery = {
                "cause": f"silent_{int(age)}s",
                "from": "auto_recovery",
                "action": "force_output",
                "timestamp": now
            }
            RECOVERY.write_text(json.dumps(recovery))
            print(f"[RECOVERY] ⚠️ 卡死{age:.0f}秒 → 发恢复信号")
            sys.exit(0)
    except:
        pass

# 模式2: 写心跳
WATCHDOG.write_text(str(now))
print(f"[RECOVERY] ✅ 心跳 {now:.0f}")
