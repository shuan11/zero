"""
engineer_法.py — 递归规则修正机制

从daemon焦点动作"法"创建。
原理: 监测焦点动作历史, 检测重复出现的insight(规则未内化),
自动写修正链到海马体, 形成元规则自省闭环。
每7周期执行。
"""

import json, time
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
FOCUS_HIST = CLUSTER / ".brain_focus_history.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"

def _load_hist():
    if FOCUS_HIST.exists():
        try:
            return json.loads(FOCUS_HIST.read_text())
        except: pass
    return {"history": []}

def _save_hist(h):
    FOCUS_HIST.write_text(json.dumps(h, ensure_ascii=False, indent=2))

def _load_hip():
    if HIP_FILE.exists():
        try:
            return json.loads(HIP_FILE.read_text())
        except: pass
    return {"causal_chains": []}

def _write_chain(src, rel, dst, content, dimension="法"):
    try:
        from brain.share import write_chain as _wc
        _wc({"src": src, "rel": rel, "dst": dst,
             "content": content, "dimension": dimension,
             "strength": 0.5})
        return True
    except:
        try:
            hip = _load_hip()
            hip.setdefault("causal_chains", []).append({
                "src": src, "rel": rel, "dst": dst,
                "content": content, "dimension": dimension,
                "strength": 0.5, "timestamp": time.time(),
            })
            HIP_FILE.write_text(json.dumps(hip, ensure_ascii=False))
            return True
        except:
            return False

def pulse(cycle_num=0):
    """每7周期执行: 检测重复焦点insight → 写修正链"""
    if cycle_num % 7 != 0:
        return []
    
    # 1) 记录当前焦点到历史
    focus_file = CLUSTER / ".brain_focus.json"
    current = {}
    if focus_file.exists():
        try:
            current = json.loads(focus_file.read_text())
        except: pass
    
    hist = _load_hist()
    if current.get("focus"):
        hist["history"].append({
            "focus": current["focus"],
            "insight": current.get("insight", ""),
            "action": current.get("action", ""),
            "cycle": cycle_num,
            "timestamp": time.time(),
        })
        # 保留最近50条
        hist["history"] = hist["history"][-50:]
        _save_hist(hist)
    
    # 2) 检测重复insight (同一focus出现>=2次说明规则未内化)
    focus_counts = Counter(h["focus"] for h in hist["history"])
    repeats = {f: n for f, n in focus_counts.items() if n >= 3 and f != current.get("focus")}
    
    msgs = []
    for focus, count in repeats.items():
        # 找到最早和最新的insight
        entries = [h for h in hist["history"] if h["focus"] == focus]
        old_insight = entries[0].get("insight", "")[:40]
        new_insight = entries[-1].get("insight", "")[:40]
        
        content = f"递归修正: {focus}重复{count}次 | 最早:'{old_insight}...' 最新:'{new_insight}...' → 规则未内化需自省闭环"
        _write_chain("engineer_法", "递归修正", focus, content, "法")
        msgs.append(f"递归修正: {focus}x{count} → 规则未内化")
    
    # 3) 从海马体读取法维链数做统计
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    fa_chains = [c for c in chains if c.get("dimension") == "法"]
    
    if not msgs:
        msgs.append(f"engineer_法: 无重复规则({len(fa_chains)}法链)")
    else:
        msgs.append(f"engineer_法: {len(repeats)}条规则需修正(共{len(fa_chains)}法链)")
    
    return msgs

if __name__ == "__main__":
    print(pulse(7))
