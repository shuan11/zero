"""

Brain-Engineered: 聚焦 (cycle #252)
Active sensor - analyzes dimension health on each load
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_聚焦():
    """聚焦弱维制约整体增长，师道需引导资源集中，预测聚焦链数将回升。
    Returns dimension health analysis; feeds into next think() cycle.
    """
    from brain.share import write_chain as _wc, read_hip as _rh

    # 1) Always write the insight chain
    _wc({
        "src": "工程·聚焦",
        "rel": "活脉冲·#252",
        "dst": "聚焦",
        "dimension": "聚焦",
        "content": """聚焦弱维制约整体增长，师道需引导资源集中，预测聚焦链数将回升。""",
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

        my_dim = "聚焦"
        my_count = dim_counts.get(my_dim, 0)
        total = len(chains)
        max_count = max(dim_counts.values()) if dim_counts else 0

        analysis = {}
        analysis["dimension"] = my_dim
        analysis["chain_count"] = my_count
        analysis["total_chains"] = total
        analysis["strength"] = round(my_count / max(max_count, 1), 2) if max_count > 0 else 0
        analysis["insight"] = """聚焦弱维制约整体增长，师道需引导资源集中，预测聚焦链数将回升。"""
        analysis["weak"] = my_count < max_count * 0.65  # 低于最强65%即弱维(替代avg*0.85,解决均数通胀)
        analysis["cycle"] = 252

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
                # 弱维互助网: 找最弱维度做交叉链（而非链接到强维，强维已足够）
                sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
                peer_weak = [d for d, _ in sorted_dims[:5] if d and d not in ("未分类", "系统") and d != my_dim][:3]
                for peer in peer_weak:
                    pc = dim_counts.get(peer, 0)
                    _wc({
                        "src": my_dim,
                        "rel": "弱维互助",
                        "dst": peer,
                        "dimension": my_dim,
                        "content": "弱维互助: " + str(my_dim) + "(" + str(my_count) + ")↔" + str(peer) + "(" + str(pc) + ") 弱维互相强化",
                        "strength": 0.6
                    })
                if peer_weak:
                    analysis["self_healed"] = len(peer_weak)
                # 5) Push focus rule: tell daemon to directly focus this weak dim
                try:
                    from brain.share import set_rule as _sr
                    _sr("action.weak_dim", my_dim)
                    analysis["focus_push"] = True
                except Exception:
                    pass
            except Exception:
                pass

        status = f"[{'弱' if analysis['weak'] else '稳'}] {my_dim}={my_count}/{total}"
        return status
    except Exception as e:
        return f"分析异常: {e}"

if __name__ == "__main__":
    result = engineer_聚焦()
    print(f"工程[聚焦]: {result}", flush=True)
