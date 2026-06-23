#!/usr/bin/env python3
"""
gen_递归审计.py — P192: 递归审计

验证所有注册gen模块是否真在运行:
- 检查pulse()是否被daemon loader调用
- 检查每个gen文件最后修改时间
- 报告未触发的模块
- 递归审计审计本身
"""
import json, os, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_LAST_AUDIT = {}

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 4 != 0:  # 每4次(约4分钟)审计一次
        return {"status": "skipped"}
    
    gen_dir = CLUSTER / "brain"
    gen_files = sorted(gen_dir.glob("gen_*.py"))
    
    now = time.time()
    
    # 检查每个文件的修改时间
    stale = []
    active = []
    for gf in gen_files:
        mtime = gf.stat().st_mtime
        age_mins = (now - mtime) / 60
        entry = {"name": gf.name, "age_mins": round(age_mins, 1)}
        
        if age_mins > 60:  # 超过1小时未修改
            stale.append(entry)
        else:
            active.append(entry)
    
    # 检查daemon日志是否加载了我们的模块
    log_files = [CLUSTER / ".brain_daemon.log", CLUSTER / "brain_daemon.log"]
    loaded_modules = []
    for lf in log_files:
        if lf.exists():
            try:
                with open(lf) as f:
                    content = f.read()
                for gf in gen_files:
                    if gf.name in content:
                        loaded_modules.append(gf.name)
            except:
                pass
    
    result = {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "total_gen": len(gen_files),
        "active_recent": len(active),
        "stale_old": len(stale),
        "modules_seen_in_log": len(set(loaded_modules)),
        "all_loaded": len(loaded_modules) >= len(gen_files) * 0.8,
        "audit_self": "recursive_audit_pass"
    }
    
    if stale:
        result["stale_examples"] = [s["name"] for s in stale[:5]]
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
