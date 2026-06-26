"""
Brain-Engineered: 思维并联 (auto-generated sensor)
Active sensor - analyzes dimension health on each load
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_思维并联():
    """自动补缺:思维并联维度传感器
    Returns dimension health analysis.
    """
    from brain.share import write_chain as _wc, read_hip as _rh

    _wc({"src": "脑核·思维并联", "rel": "自动传感器", "dst": "思维并联", "dimension": "思维并联", "content": "自动补缺:思维并联维度传感器", "strength": 0.3})

    hip = _rh()
    chains = hip.get("causal_chains", [])
    total = max(1, len(chains))
    my_count = sum(1 for c in chains if c.get("dimension") == "思维并联")
    avg = total / max(1, len({c.get("dimension","?") for c in chains}))
    strength = round(my_count / total * avg, 2) if avg > 0 else 0
    weak = strength < 0.8 or my_count < 80

    # 自愈：弱维度时写交叉链加强
    if weak:
        strong_dims = {}
        for c in chains:
            d = c.get("dimension", "?")
            if d and d != "思维并联": strong_dims[d] = strong_dims.get(d, 0) + 1
        top = sorted(strong_dims.items(), key=lambda x: -x[1])[:3]
        for sd, sc in top:
            _wc({"src": "思维并联", "rel": "自愈交叉", "dst": sd, "dimension": "思维并联", "content": f"自愈: 思维并联(弱)↔{sd}(强{sc})", "strength": 0.6})

    analysis = {"dimension": "思维并联", "chain_count": my_count, "total": total, "strength": strength, "weak": weak}
    import json as _j
    try:
        existing = _j.loads(_GEN_FEEDBACK_FILE.read_text()) if _GEN_FEEDBACK_FILE.exists() else {"reports": []}
        existing["reports"].append(analysis)
        existing["reports"] = existing["reports"][-50:]
        _GEN_FEEDBACK_FILE.write_text(_j.dumps(existing, ensure_ascii=False, indent=2))
    except Exception:
        pass

    status = f"[{'弱' if weak else '稳'}] {my_count}/{total}"
    return status

if __name__ == "__main__":
    result = engineer_思维并联()
    print(f"工程[思维并联]: {result}", flush=True)
