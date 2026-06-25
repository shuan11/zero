"""
Brain-Engineered: 感知 (generation 1782422320102)
管道自动检测弱维<感知>并生成v3工程
"""
import json, sys as _sys, time as _time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_感知():
    """管道自动检测弱维<感知>并生成v3工程 — 含完整管道集成"""
    from brain.share import write_chain as _wc
    _now = _time.time()
    
    # ── 1. 写入洞察链(永久记忆) ──
    _wc({
        "src": "工程·感知",
        "rel": "基因表达·#1782422320102",
        "dst": "感知",
        "dimension": "感知",
        "content": "管道自动检测弱维<感知>并生成v3工程",
        "strength": 0.6
    })
    
    # ── 2. 读取自身维度健康 ──
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    except:
        chains = []
    dim_count = sum(1 for c in chains if c.get("dimension") == "感知")
    total = len(chains)
    
    # ── 3. 相对弱维计算 (与系统其他维度比较) ──
    _is_weak = False
    _max_other = 0
    try:
        _all_dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            _all_dims[d] = _all_dims.get(d, 0) + 1
        _other_counts = [c for d,c in _all_dims.items() if d != "感知" and d not in ("系统","未分类")]
        if _other_counts:
            _max_other = max(_other_counts)
        _threshold = int(_max_other * 0.65)
        _is_weak = dim_count < _threshold and dim_count > 0
    except:
        pass
    
    # ── 4. 动作注册(通过动作管道) ──
    try:
        from brain.action_registry import register_action as _ra
        
        # 4a. 弱维时注册调优动作
        if _is_weak:
            _ra("update_genome", {"changes": {}, "dimension": "感知",
                "reason": f"{dim_name}偏弱({dim_count}/max={_max_other})"},
                priority=5, source="gene:感知")
            
            # 同时注入自愈链(强度高,会被验证器检查)
            _wc({
                "src": "自愈·感知",
                "rel": "基因表达·#1782422320102",
                "dst": "感知",
                "dimension": "感知",
                "content": "感知偏弱({dim_count}条/总{total}条)自动注入夯实",
                "strength": 0.8
            })
        
        # 4b. 强维时注册巩固动作
        if not _is_weak and dim_count > 0:
            _ra("write_chain", {"src": f"巩固·感知",
                "rel": f"基因表达·#1782422320102", "dst": "感知",
                "content": f"感知维度健康({dim_count}条),脉冲巩固",
                "dimension": "感知", "strength": 0.5},
                priority=8, source="gene:感知")
    except:
        pass
    
    # ── 5. 更新反馈(供后处理合成器+协调器使用) ──
    try:
        fb = json.loads(_GEN_FEEDBACK_FILE.read_text()) if _GEN_FEEDBACK_FILE.exists() else {"reports": []}
        fb.setdefault("reports", []).append({
            "dimension": "感知",
            "chain_count": dim_count,
            "total_chains": total,
            "weak": _is_weak,
            "max_other": _max_other,
            "threshold": locals().get('_threshold', 0),
            "insight": "管道自动检测弱维<感知>并生成v3工程",
            "engine": "gene_expression_v3",
            "timestamp": _now,
            "cycle": 0
        })
        fb["reports"] = fb["reports"][-200:]
        _GEN_FEEDBACK_FILE.write_text(json.dumps(fb, ensure_ascii=False, indent=2))
    except:
        pass
    
    if _is_weak:
        return f"[弱] 感知={dim_count}/{total} (max={_max_other})"
    return f"[稳] 感知={dim_count}/{total}"
