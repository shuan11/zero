#!/usr/bin/env python3
"""
zero_startup_timecheck.py — 每次会话启动时感知北京时间
======================================================
放在零的启动链中，每次新session自动调用。
"""
import sys, os, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from time_perception import status, print_status, warn, now_beijing, record

def main():
    print()
    print("╔══════════════════════════════════════════════╗")
    print("║      🕐 北京时间感知系统 · 启动检查         ║")
    print("╚══════════════════════════════════════════════╝")
    print_status()
    
    w, s = warn()
    if s["is_idle"]:
        print()
        print("  ⚠️  已检测到空闲 — 自动执行恢复流程")
        print(f"  上次行动: {s['last_action_type']} @ {s['last_action_time']}")
        print(f"  空闲时间: {s['minutes_since_last_action']} 分钟")
        print(f"  建议: 立即执行 HANDOFF 中预选的 P0")
        print()
    
    record("session_start", f"新会话启动 @ {now_beijing().isoformat()}")
    return s

if __name__ == "__main__":
    s = main()
    # 以JSON输出供其他工具读取
    print(f"TIME_PERCEPTION_JSON={json.dumps(s)}")
