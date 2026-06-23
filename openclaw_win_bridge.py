#!/usr/bin/env python3
"""
openclaw_win_bridge.py — OpenClaw Windows侧桥接器

将Windows侧的OpenClaw agent接入真元集群总线。
位置: /mnt/c/Users/h/.openclaw/ (Windows: C:\\Users\\h\\.openclaw)
协议: WSL文件桥 + 远程进程管理

用法:
  python3 openclaw_win_bridge.py status
"""
import json, os, sys, subprocess, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

WIN_OPENCLAW = Path("/mnt/c/Users/h/.openclaw")

def get_state():
    info = {}
    if WIN_OPENCLAW.exists():
        info["path"] = str(WIN_OPENCLAW)
        dirs = [d.name for d in WIN_OPENCLAW.iterdir() if d.is_dir()]
        files = [f.name for f in WIN_OPENCLAW.iterdir() if f.is_file()]
        info["directories"] = dirs
        info["files"] = files[:15]
        total_size = sum(f.stat().st_size for f in WIN_OPENCLAW.rglob("*") if f.is_file())
        info["total_size_mb"] = round(total_size / 1024 / 1024, 1)
    try:
        r = subprocess.run(
            ["powershell.exe", "-Command",
             "Get-Process openclaw,node -ErrorAction SilentlyContinue | Format-Table Id,ProcessName -AutoSize"],
            capture_output=True, text=True, timeout=5
        )
        info["windows_process"] = r.stdout.strip() if r.stdout.strip() else "(no process)"
    except Exception:
        info["windows_process"] = "(cannot query)"
    return info

if __name__ == "__main__":
    import sys as _sys
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else "status"
    if cmd == "status":
        state = get_state()
        print(f"OpenClaw Windows:")
        print(f"  Path: {state.get('path','N/A')}")
        print(f"  Size: {state.get('total_size_mb','?')}MB")
        print(f"  Dirs: {len(state.get('directories',[]))} {state.get('directories',[])}")
        print(f"  Files: {len(state.get('files',[]))}")
        print(f"  Windows: {state.get('windows_process','N/A')}")
