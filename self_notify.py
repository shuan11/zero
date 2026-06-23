#!/usr/bin/env python3
"""自我通知——脑核状态嗅探器，system通知到主会话
让零不需要"."就能知道自己该做什么"""
import json, os, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
BRAIN_HOME = Path("/home/hjw123/.zero_brain")

def read_brain_state():
    """读取脑核状态"""
    state = {"alive": False, "cycle": -1, "pid": -1}
    try:
        if (BRAIN_HOME / ".brain.alive").exists():
            state["alive"] = True
            state["alive_since"] = (BRAIN_HOME / ".brain.alive").read_text().strip()
    except: pass
    try:
        if (BRAIN_HOME / ".brain.heartbeat").exists():
            hb = json.loads((BRAIN_HOME / ".brain.heartbeat").read_text())
            state["cycle"] = hb.get("cycle", -1)
            state["pid"] = hb.get("pid", -1)
            state["last_beat"] = hb.get("time", 0)
            state["idle_sec"] = int(time.time() - state["last_beat"]) if state["last_beat"] else 999
    except: pass
    try:
        if (BRAIN_HOME / ".brain.pid").exists():
            state["pid_file"] = int((BRAIN_HOME / ".brain.pid").read_text().strip())
    except: pass
    return state

def read_dim_state():
    """读取最弱维度状态"""
    try:
        snap = CLUSTER / ".brain_dim_snap.json"
        if snap.exists():
            return json.loads(snap.read_text())
    except: pass
    return {}

def read_focus_history():
    """读取最近聚焦"""
    try:
        log = CLUSTER / ".brain_daemon.log"
        if log.exists():
            txt = log.read_text(errors='ignore')
            foci = []
            for line in txt.split('\n'):
                if "聚焦:" in line and "观察:" not in line:
                    parts = line.split("聚焦:")
                    if len(parts) > 1:
                        f = parts[1].strip().split()[0] if parts[1].strip() else ""
                        if f and (not foci or f != foci[-1]):
                            foci.append(f)
            return foci[-8:]  # 最近8个
    except: pass
    return []

def read_goal():
    """读取当前目标"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        if gf.exists():
            return json.loads(gf.read_text())
    except: pass
    return {}

def main():
    state = read_brain_state()
    dim = read_dim_state()
    foci = read_focus_history()
    goal = read_goal()
    
    print("═" * 40)
    print(f"🧠 自我通知 @ {time.strftime('%H:%M:%S')}")
    print("═" * 40)
    
    if state.get("alive"):
        print(f"✓ 脑核运行中 PID={state.get('pid','?')}")
        print(f"  周期#{state.get('cycle','?')} 空闲{state.get('idle_sec','?')}秒")
        if foci:
            print(f"  聚焦链: {'→'.join(foci[-5:])}")
    else:
        print("✗ 脑核未运行")
    
    if dim:
        w_avg = dim.get("weak_avg", 0)
        gap = dim.get("gap", 0)
        print(f"  弱维均值: {w_avg:.0f}链 | 强弱差距: {gap:.0f}链")
    
    gtype = goal.get("goal_type", "")
    gdesc = goal.get("description", "")
    if gtype and gdesc:
        print(f"  当前目标: [{gtype}] {gdesc}")
    
    # 检测停滞
    idle = state.get("idle_sec", 0)
    if idle > 180:
        print(f"\n⚠️ 脑核可能停滞({idle}秒无心跳)")
    if len(foci) >= 4 and len(set(foci[-3:])) <= 1:
        print(f"\n⚠️ 聚焦可能固化: 重复{foci[-1]}")

if __name__ == "__main__":
    main()
