"""

Brain-Engineered: 师 (cycle #356)
Active sensor - analyzes dimension health on each load
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_师():
    """燕尾榫启示：从自然形制中领悟连接智慧
    Returns dimension health analysis; feeds into next think() cycle.
    """
    from brain.share import write_chain as _wc, read_hip as _rh

    # 1) Always write the insight chain
    _wc({
        "src": "工程·师",
        "rel": "活脉冲·#356",
        "dst": "师",
        "dimension": "师",
        "content": """燕尾榫启示：从自然形制中领悟连接智慧""",
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

        my_dim = "师"
        my_count = dim_counts.get(my_dim, 0)
        total = len(chains)
        avg_count = total / max(len(dim_counts), 1)

        analysis = {}
        analysis["dimension"] = my_dim
        analysis["chain_count"] = my_count
        analysis["total_chains"] = total
        analysis["strength"] = round(my_count / max(avg_count, 1), 2) if avg_count > 0 else 0
        analysis["insight"] = """燕尾榫启示：从自然形制中领悟连接智慧"""
        analysis["weak"] = my_count < avg_count * 0.5
        analysis["cycle"] = 356

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

        # 4) Self-heal weak dimension: auto-generate reinforcing cross-links
        if analysis.get("weak"):
            try:
                # 找3个最强维度做交叉链
                sorted_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
                strong_dims = [d for d, _ in sorted_dims[:3] if d and d != my_dim]
                for strong_dim in strong_dims:
                    _wc({
                        "src": my_dim,
                        "rel": "自愈交叉",
                        "dst": strong_dim,
                        "dimension": my_dim,
                        "content": "自愈: " + str(my_dim) + "(" + str(my_count) + ")↔" + str(strong_dim) + "(" + str(dim_counts.get(strong_dim,0)) + ") 弱维自修复",
                        "strength": 0.5
                    })
                if strong_dims:
                    analysis["self_healed"] = len(strong_dims)
            except Exception:
                pass

        status = f"[{'弱' if analysis['weak'] else '稳'}] {my_dim}={my_count}/{total}"
        return status
    except Exception as e:
        return f"分析异常: {e}"

if __name__ == "__main__":
    result = engineer_师()
    print(f"工程[师]: {result}", flush=True)
