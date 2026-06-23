#!/usr/bin/env python3
"""uibot_heartbeat.py — UiBot持久心跳 (运行于Windows侧)
每10分钟写入心跳信号到WSL集群目录。

安装: Windows Task Scheduler 每10分钟运行一次
    python.exe uibot_heartbeat.py
"""
import json, os, time
from pathlib import Path

WSL_CLUSTER = Path(r"C:\Users\h\Desktop\零\真元集群")
MARKER = WSL_CLUSTER / ".uibot_heartbeat"

def write_heartbeat():
    WSL_CLUSTER.mkdir(parents=True, exist_ok=True)
    
    # 读取前一呼吸号
    breath = 0
    if MARKER.exists():
        try:
            data = json.loads(MARKER.read_text(encoding='utf-8'))
            breath = data.get("breath", 0)
        except:
            pass
    
    breath += 1
    
    heartbeat = {
        "breath": breath,
        "time": time.time(),
        "time_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "from": "uibot_windows",
        "python": "3.12.10",
        "host": os.environ.get("COMPUTERNAME", "unknown")
    }
    
    MARKER.write_text(json.dumps(heartbeat, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[UiBot] 第{breath}次心跳已写入 — {heartbeat['time_str']}")

if __name__ == "__main__":
    write_heartbeat()
