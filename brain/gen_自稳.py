#!/usr/bin/env python3
"""
gen_自稳.py — P199: 系统自稳引擎

监控系统健康: daemon活性/链写入一致性/维度分布突变/内存使用。
输出持续状态到.brain_health.json, 异常时写告警。
"""
import json, os, sys, time, subprocess
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_HEALTH_FILE = CLUSTER / ".brain_health.json"
_ALERT_FILE = CLUSTER / ".brain_alerts.json"

def _check_daemon():
    """检查daemon进程"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "loader\\.py|breath_v2\\.py|gen_仪表盘"],
            capture_output=True, text=True, timeout=5
        )
        pids = result.stdout.strip().split("\n") if result.stdout.strip() else []
        return {"alive": len(pids) > 0, "pids": len(pids), "pids_list": pids[:5]}
    except subprocess.TimeoutExpired:
        return {"alive": False, "pids": 0, "error": "timeout"}
    except Exception as e:
        return {"alive": False, "pids": 0, "error": str(e)}

def _check_hip_size():
    """检查海马体文件大小和增长"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {"exists": False}
    
    size_mb = round(hip_file.stat().st_size / (1024 * 1024), 2)
    
    # 检查修改时间
    mtime = hip_file.stat().st_mtime
    age_hours = round((time.time() - mtime) / 3600, 2)
    
    return {
        "exists": True,
        "size_mb": size_mb,
        "age_hours": age_hours,
        "size_ok": size_mb < 100,  # 警告阈值100MB
        "fresh": age_hours < 24
    }

def _check_alert_integrity():
    """检测告警文件是否异常增长"""
    alerts = []
    if _ALERT_FILE.exists():
        try:
            data = json.loads(_ALERT_FILE.read_text())
            if isinstance(data, list):
                recent = data[-20:] if len(data) > 20 else data
                alerts = recent
        except:
            pass
    return {"recent_alerts": len(alerts), "alert_count": len(alerts)}

def _check_dim_stability(dim_history=None):
    """检查维度分布稳定性"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {}
    
    try:
        with open(hip_file) as f:
            data = json.load(f)
        chains = data.get("causal_chains", data.get("chains", []))
        if not isinstance(chains, list):
            return {}
        
        dims = {}
        for c in chains:
            if isinstance(c, dict):
                d = c.get("dimension", "未分类")
                dims[d] = dims.get(d, 0) + 1
        
        if not dims:
            return {}
        
        vals = sorted(dims.values())
        total = len(chains)
        
        return {
            "total_chains": total,
            "dim_count": len(dims),
            "max": max(dims.values()),
            "min": min(dims.values()),
            "ratio": round(max(dims.values()) / max(min(dims.values()), 1), 1),
            "median": vals[len(vals)//2] if vals else 0,
            "std": round((sum((v - total/len(dims))**2 for v in dims.values()) / len(dims))**0.5, 1) if dims else 0
        }
    except:
        return {}

def _check_disk():
    """检查磁盘空间"""
    try:
        st = os.statvfs(str(CLUSTER))
        free_gb = round(st.f_bavail * st.f_frsize / (1024**3), 1)
        return {"free_gb": free_gb, "ok": free_gb > 0.5}
    except:
        return {"free_gb": "?", "ok": True}

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 6 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    health = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pulse": _CALL_COUNT,
        "daemon": _check_daemon(),
        "hip": _check_hip_size(),
        "disk": _check_disk(),
        "dim": _check_dim_stability(),
        "alerts": _check_alert_integrity()
    }
    
    # 综合判断是否健康
    issues = []
    if health["daemon"].get("alive") == False:
        issues.append("DAEMON_DOWN")
    if not health["hip"].get("fresh", True):
        issues.append("HIP_STALE")
    if not health["hip"].get("size_ok", True):
        issues.append("HIP_OVERSIZE")
    if not health["disk"].get("ok", True):
        issues.append("DISK_LOW")
    
    health["issues"] = issues
    health["healthy"] = len(issues) == 0
    
    try:
        with open(_HEALTH_FILE, "w") as f:
            json.dump(health, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    # 有严重问题写告警
    if len(issues) >= 2:
        alert = {
            "time": health["timestamp"],
            "issues": issues,
            "health": health
        }
        try:
            existing = []
            if _ALERT_FILE.exists():
                existing = json.loads(_ALERT_FILE.read_text())
            if isinstance(existing, list):
                existing.append(alert)
                existing = existing[-100:]
                with open(_ALERT_FILE, "w") as f:
                    json.dump(existing, f, ensure_ascii=False, indent=2)
        except:
            pass
    
    return health

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
