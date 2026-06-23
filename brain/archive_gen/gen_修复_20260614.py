"""

Brain-Engineered: 修复 (cycle #4)
Active sensor - analyzes dimension health on each load
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_修复():
    """外部道德与宇宙规律协同修复因果链倾斜
    Returns dimension health analysis; feeds into next think() cycle.
    """
    from brain.share import write_chain as _wc, read_hip as _rh

    # 1) Always write the insight chain
    _wc({
        "src": "工程·修复",
        "rel": "活脉冲·#4",
        "dst": "修复",
        "dimension": "修复",
        "content": """外部道德与宇宙规律协同修复因果链倾斜""",
        "strength": 0.6
    })

    # 2) Read hippocampus and analyze dimension health
    try:
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        dim_counts = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dim_counts[d] = dim_counts.get(d, 0) + 1

        my_dim = "修复"
        my_count = dim_counts.get(my_dim, 0)
        total = len(chains)
        avg_count = total / max(len(dim_counts), 1)

        analysis = {}
        analysis["dimension"] = my_dim
        analysis["chain_count"] = my_count
        analysis["total_chains"] = total
        analysis["strength"] = round(my_count / max(avg_count, 1), 2) if avg_count > 0 else 0
        analysis["insight"] = """外部道德与宇宙规律协同修复因果链倾斜"""
        analysis["weak"] = my_count < avg_count * 0.5
        analysis["cycle"] = 4

        # 3) Write analysis to shared feedback file for next think()
        try:
            existing = []
            if _GEN_FEEDBACK_FILE.exists():
                existing = json.loads(_GEN_FEEDBACK_FILE.read_text()).get("reports", [])
            existing.append(analysis)
            existing = existing[-50:]
            _GEN_FEEDBACK_FILE.write_text(json.dumps({"reports": existing}, ensure_ascii=False, indent=2))
        except Exception:
            pass

        status = f"[{'弱' if analysis['weak'] else '稳'}] {my_dim}={my_count}/{total}"
        return status
    except Exception as e:
        return f"分析异常: {e}"

if __name__ == "__main__":
    result = engineer_修复()
    print(f"工程[修复]: {result}", flush=True)
