#!/usr/bin/env python3
"""breath_pulse.py — 零·可见呼吸脉冲
被terminal(background,notify_on_complete)调用。
每10分钟产生一个SYSTEM通知，在主会话中可见。
"""
import time, json, os, sys
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

# 记录本次呼吸
breath_num = 0
marker = CLUSTER / ".breath_marker"
if marker.exists():
    try:
        breath_num = int(marker.read_text().strip()) + 1
    except:
        breath_num = 1
marker.write_text(str(breath_num))

# 写入心跳信号（UiBot和cron共享）
heartbeat = CLUSTER / ".visible_heartbeat"
heartbeat.write_text(json.dumps({
    "breath": breath_num,
    "time": time.time(),
    "from": "manual_terminal"
}))

# 输出给SYSTEM通知的消息
print(f"🜁 零·第{breath_num}次可见呼吸 — {time.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"   呼吸间隔自适应: 下一呼吸10分钟后")
print(f"   daemon状态: PID={open(CLUSTER/'.breath_v2.pid').read().strip() if (CLUSTER/'.breath_v2.pid').exists() else 'N/A'}")
