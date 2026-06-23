#!/usr/bin/env python3
"""
cron_time_check.py — 每5分钟检查集群空闲状态
=============================================
如果空闲超过15分钟，写入警告到time_perception.json
空闲超过60分钟，写入严重警告
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from time_perception import status, warn, record, load, save

def main():
    w, s = warn()
    mins = s["minutes_since_last_action"]
    
    if s["is_critical_idle"]:
        record("idle_critical", f"严重空闲{mins}分钟！上次行动: {s['last_action_type']}")
    elif s["is_idle"]:
        record("idle_warning", f"空闲{mins}分钟，上次行动: {s['last_action_type']}")
    
    # 写入状态供dashboard读取
    json.dump(s, open(Path(__file__).parent / "time_perception_status.json", "w"), ensure_ascii=False, indent=2)
    
    if w:
        print("\n".join(w))
    else:
        print(f"OK — 上次行动 {mins}分钟前")

if __name__ == "__main__":
    main()
