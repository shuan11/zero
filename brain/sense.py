"""brain/sense.py — 系统感知"""
import json, os, time
from pathlib import Path
from .share import CLUSTER, log, read_hip

def sense():
    hip = read_hip()
    chains = hip.get("causal_chains", [])

    nodes = set()
    for c in chains:
        if c.get("src"): nodes.add(c["src"])
        if c.get("dst"): nodes.add(c["dst"])

    py_count = len(list(CLUSTER.glob("*.py")))

    # 进程 — 核心daemon是brain.daemon（旧breath_v2已弃用）
    daemon_alive = False
    legacy_daemon = False
    try:
        import subprocess
        r = subprocess.run(["pgrep", "-f", r"^python3.*brain\.daemon"],
                          capture_output=True, text=True, timeout=3)
        daemon_alive = bool(r.stdout.strip())
        r2 = subprocess.run(["pgrep", "-f", r"^python3.*breath_v2\.py"],
                           capture_output=True, text=True, timeout=3)
        legacy_daemon = bool(r2.stdout.strip())
    except:
        pass

    # 海马体质量
    hip_ok = True
    for c in chains:
        if c.get("src") == c.get("dst"):
            hip_ok = False
            break

    return {
        "nodes": len(nodes), "chains": len(chains),
        "py_count": py_count,
        "daemon_alive": daemon_alive,
        "legacy_daemon": legacy_daemon,
        "hip_ok": hip_ok,
        "timestamp": time.time()
    }

def sense_proposal(insight):
    """由提案注入的感知观察函数"""
    from .share import write_chain
    write_chain({
        "src": "感知·提案",
        "rel": "观察",
        "dst": "系统",
        "dimension": "感知",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True

def sense_proposal(insight):
    """由提案注入的感知观察函数"""
    from .share import write_chain
    write_chain({
        "src": "感知·提案",
        "rel": "观察",
        "dst": "系统",
        "dimension": "感知",
        "content": str(insight)[:100],
        "strength": 0.5
    })
    return True
