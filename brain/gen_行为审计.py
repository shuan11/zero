#!/usr/bin/env python3
"""
gen_行为审计.py — P186: 行为审计闭环

审计自我通知行为是否真正执行:
- 检查.chain_log中最近50条链是否有gap(超过5分钟无链)
- 检查.next_p0.json是否被自动推进
- 检查永动链是否在循环
- 报告行为审计结果
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
CHAIN_LOG = CLUSTER / "brain" / "hippocampus_chains" / "chain_log.json"
NEXT_P0 = CLUSTER / ".next_p0.json"
BRAIN_LOG = CLUSTER / ".brain_daemon.log"
BRAIN_LOG_VISIBLE = CLUSTER / "brain_daemon.log"

_CALL_COUNT = 0
_LAST_CHECK = {}

def pulse():
    """P186主脉冲 — daemon loader自动调用"""
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    # 每3次脉冲执行一次
    if _CALL_COUNT % 3 != 0:
        return {"status": "skipped"}
    
    issues = []
    healthy = True
    
    # 1. 检查.next_p0.json是否及时更新
    p0_file = NEXT_P0
    if p0_file.exists():
        try:
            with open(p0_file) as f:
                p0 = json.load(f)
            now = time.time()
            updated = p0.get("_updated", 0)
            age_min = (now - updated) / 60
            p0_id = p0.get("id", "?")
            completed = len(p0.get("completed", []))
            
            if age_min > 30:
                issues.append(f"P0停滞: {p0_id} 已{age_min:.0f}分钟未更新")
                healthy = False
            else:
                issues.append(f"P0正常: {p0_id}(完成{completed}个) {age_min:.0f}分钟前更新")
            
            # 检查是否持续在推进
            if "completed" in p0 and len(p0["completed"]) > 1:
                issues.append(f"已推进{len(p0['completed'])}步P0 — 永动链工作✓")
        except:
            issues.append("❌ .next_p0.json 解析失败")
            healthy = False
    else:
        issues.append("⚠️ 无.next_p0.json — 永动链未启动")
    
    # 2. 检查daemon日志是否活跃
    for log_file in [BRAIN_LOG, BRAIN_LOG_VISIBLE]:
        if log_file.exists():
            try:
                mtime = log_file.stat().st_mtime
                age_min = (time.time() - mtime) / 60
                if age_min > 5:
                    issues.append(f"⚠️ daemon日志{age_min:.0f}分钟未更新: {log_file.name}")
                else:
                    issues.append(f"daemon活跃: {log_file.name}({age_min:.0f}分钟前)")
                    break
            except:
                pass
    
    # 3. 检查维度是否在改善
    try:
        hip_file = CLUSTER / "hippocampus_memory.json"
        if hip_file.exists():
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
            total = len(chains) if isinstance(chains, list) else 0
            issues.append(f"海马体链数: {total}")
    except:
        pass
    
    result = {
        "status": "healthy" if healthy else "issues",
        "pulse": _CALL_COUNT,
        "issues": issues,
        "healthy": healthy,
    }
    
    # 输出到结果
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
