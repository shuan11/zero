"""
gen_进化日志.py — 人类可读的系统进化日志

每周期产生一条简洁、有信息的日志条目，
写至 .evolution_log，同时在 daemon 日志中输出。
让用户（或未来的自己）可读地了解系统在做什么。

原则：不重复数字，只说有意义的变化。
"""

import json, time, os, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(os.environ.get("CLUSTER", "/mnt/c/Users/h/Desktop/零/真元集群"))
HIPPO = CLUSTER / "hippocampus_memory.json"
LOG = CLUSTER / ".evolution_log"
STATE = CLUSTER / ".brain_state.json"
DAEMON_LOG = CLUSTER / ".brain_daemon.log"
NOTIFY_LOG = CLUSTER / ".brain_notify.log"
GOAL_FILE = CLUSTER / ".brain_goal.json"
NEXT_P0 = CLUSTER / ".next_p0.json"

_prev_total = 0
_prev_api_count = 0
_prev_gen_count = 0

def _read_json(path, default=None):
    try:
        return json.load(open(path))
    except:
        return default or {}

def _timestamp():
    return time.strftime("%H:%M")

def _fmt(n):
    if n >= 10000: return f"{n/1000:.1f}k"
    return str(n)

def _count_api_calls():
    """Count API calls in recent daemon log"""
    try:
        if not DAEMON_LOG.exists(): return 0
        log_text = open(DAEMON_LOG).read()
        # Count unique API call markers
        calls = len(re.findall(r"API调用|API call|P147加速|P147.*API", log_text))
        return calls
    except:
        return 0

def _get_current_goal():
    """Read daemon's current goal"""
    goal = _read_json(GOAL_FILE)
    if goal:
        gtype = goal.get("goal_type", goal.get("type", ""))
        focus = goal.get("focus_dim", goal.get("target", ""))
        if focus:
            return f"[{gtype}] {focus}"
    # Fallback to next_p0
    np0 = _read_json(NEXT_P0)
    if np0:
        return np0.get("p0", "")
    return ""

def _read_dimension_health():
    """Quick health scan from brain_state"""
    state = _read_json(STATE)
    health = {}
    for k, v in state.items():
        if k.startswith("dim_") and isinstance(v, (int, float)):
            health[k.replace("dim_","")] = v
    return health

def pulse():
    """Called every daemon cycle"""
    global _prev_total, _prev_api_count, _prev_gen_count
    
    data = _read_json(HIPPO, {"chains": []})
    chains = data.get("chains", [])
    total = len(chains)
    state = _read_json(STATE)
    cycle = state.get("cycle", "?")
    
    # Calculate deltas
    delta = total - _prev_total if _prev_total > 0 else 0
    _prev_total = total
    
    # API calls delta
    api_now = _count_api_calls()
    api_delta = api_now - _prev_api_count if _prev_api_count > 0 else 0
    _prev_api_count = api_now
    
    # Dimension counts
    srcs = Counter(c.get("src", "") for c in chains)
    dsts = Counter(c.get("dst", "") for c in chains)
    all_dims = srcs + dsts
    
    top = all_dims.most_common(5)
    # Find truly weak dims (lowest counts >0)
    sorted_dims = sorted(all_dims.items(), key=lambda x: x[1])
    weak_list = [(d, n) for d, n in sorted_dims[:10] if d]
    dead = [d for d, n in weak_list if n == 0]
    
    # Build log line
    ts = _timestamp()
    growth = f"+{delta}" if delta > 0 else ""
    
    # Strong dims
    strong_str = " | ".join([f"{d}({n})" for d, n in top[:2]]) if top else ""
    
    # Weak dims
    weak_str = ", ".join([f"{d}={n}" for d, n in weak_list[:3]]) if weak_list else ""
    
    # Goal
    goal = _get_current_goal()
    
    # API
    api_str = f"🔥{api_delta}" if api_delta > 0 else ""
    
    parts = [f"🜁 [{ts}] c{cycle} {_fmt(total)}链{growth}"]
    if api_str:
        parts.append(api_str)
    if strong_str:
        parts.append(f"强:{strong_str}")
    if weak_str:
        parts.append(f"弱:{weak_str}")
    if goal:
        parts.append(f"🎯{goal[:50]}")
    if dead:
        parts.append(f"💀死维:{','.join(dead[:3])}")
    
    log_line = " | ".join(parts) + " ✓"
    
    # Write to evolution log (keep last 30 lines)
    try:
        existing = []
        if LOG.exists():
            existing = open(LOG).readlines()
        existing.append(log_line + "\n")
        if len(existing) > 30:
            existing = existing[-30:]
        open(LOG, "w").writelines(existing)
    except:
        pass
    
    return {"status": "logged", "total": total, "delta": delta, "api_calls": api_delta, "line": log_line}

def _autonomous_run():
    result = pulse()
    print(result.get("line", "?"))

if __name__ == "__main__":
    _autonomous_run()
