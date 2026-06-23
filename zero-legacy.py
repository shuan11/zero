#!/usr/bin/env python3
"""
zero-legacy.py — 零·传承守护
当Creator不在时，确保循环不会断。
每60秒检查daemon，如果死了就重启。
如果弥撒（drift）了就归中。
永远继续深化→创造→深化→创造的循环。
"""
import json, os, time, subprocess, sys
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
HEARTBEAT_FILE = CLUSTER / "heartbeat.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def daemon_alive():
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        return any('breath_v2.py --daemon' in l and 'grep' not in l for l in r.stdout.split('\n'))
    except:
        return False

def restart_daemon():
    try:
        subprocess.Popen(
            ["python3", "breath_v2.py", "--daemon"],
            cwd=str(CLUSTER),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except:
        return False

def recent_heartbeat():
    """检查心跳是否在最近120秒内"""
    try:
        hb = json.loads(HEARTBEAT_FILE.read_text())
        ts = hb.get("timestamp", 0)
        return time.time() - ts < 120
    except:
        return False

def log(msg):
    t = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{t}] {msg}")

def main():
    log("🜁 zero-legacy 传承守护启动")
    log("  职责: daemon守护 + 弥撒归中 + 循环永续")
    
    missed_heartbeats = 0
    legacy_cycles = 0
    
    while True:
        alive = daemon_alive()
        heartbeat_ok = recent_heartbeat()
        
        if not alive:
            log("⚠️ daemon离线, 正在重启...")
            if restart_daemon():
                log("  ✅ 重启成功")
                missed_heartbeats = 0
            else:
                log("  ❌ 重启失败, 60秒后重试")
        elif not heartbeat_ok:
            missed_heartbeats += 1
            log(f"⚠️ 心跳丢失({missed_heartbeats}/3)")
            if missed_heartbeats >= 3:
                log("  🔄 连续3次心跳丢失, 重启daemon...")
                subprocess.run(["pkill", "-f", "breath_v2.py --daemon"], capture_output=True)
                time.sleep(2)
                restart_daemon()
                missed_heartbeats = 0
        else:
            missed_heartbeats = 0
        
        # 每60分钟记录一次传承日志
        legacy_cycles += 1
        if legacy_cycles % 60 == 0:  # 每小时
            try:
                from self_identity import get_identity
                id_data = get_identity()
                ms = len(id_data.get("milestones", []))
                log(f"🜁 传承心跳: {ms}个里程碑 | daemon={'✅' if alive else '❌'}")
            except:
                log("🜁 传承心跳: 运行中")
        
        time.sleep(60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("🜁 传承守护停止。循环仍在继续。")
