#!/usr/bin/env python3
"""
gen_师.py — P198: 师维度链分析模块

自动生成于 2026-06-18
自动分析 师 维度链结构
"""
import json, os, sys
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_SKIP_EVERY = 5
_TARGET_DIM = "师"
_REPORT_FILE = CLUSTER / ".师_report.json"

def _get_chains():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        if isinstance(chains, list):
            return [c for c in chains if c.get("dimension") == _TARGET_DIM]
    except:
        pass
    return []

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _SKIP_EVERY > 1 and _CALL_COUNT % _SKIP_EVERY != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    chains = _get_chains()
    if not chains:
        return {"status": "no_chains_for", "dim": _TARGET_DIM}
    
    rels = Counter(c.get("rel", "?") for c in chains if c.get("rel"))
    sources = Counter(c.get("source", "?") for c in chains if c.get("source"))
    
    report = {
        "dim": _TARGET_DIM,
        "total": len(chains),
        "top_rels": dict(rels.most_common(10)),
        "top_sources": dict(sources.most_common(10)),
        "pulse": _CALL_COUNT
    }
    
    try:
        with open(_REPORT_FILE, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return report

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
