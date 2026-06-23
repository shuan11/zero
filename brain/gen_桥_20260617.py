"""
Brain-Engineered: 桥 (generation 1 → P134升级)
职责=监测API桥健康并主动修复
使用动作注册表(不是只写链) — 执行器模式
"""
import json, sys as _sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

REGISTRY_AVAILABLE = True
try:
    from brain.action_registry import register_action as _ra
except Exception:
    REGISTRY_AVAILABLE = False


def engineer_桥():
    """桥维度：监测API桥健康 → 执行动作"""
    from brain.share import write_chain as _wc, read_hip as _rh
    results = []

    # 1. 检查桥状态
    bridge_ok = False
    bridge_info = {}
    try:
        from brain.bridge_manager import BridgeManager
        bm = BridgeManager()
        state = bm.get_state()
        alignment = state.get("alignment", 0)
        failures = state.get("failures", 0)
        calls = state.get("calls", 0)
        bridge_info = {"alignment": alignment, "failures": failures, "calls": calls}
        bridge_ok = calls > 0  # 至少有过调用
    except Exception:
        alignment, failures, calls = 0, 0, 0
        results.append("[弱] 桥 BridgeManager不可用")

    # 2. 写洞察链(常规报告)
    _wc({
        "src": "工程·桥",
        "rel": "基因表达·P134",
        "dst": "桥",
        "dimension": "桥",
        "content": f"桥状态: align={alignment:.3f} calls={calls} fail={failures}",
        "strength": 0.6
    })

    # 3. ═══ 动作注册表：主动执行 ═══
    if REGISTRY_AVAILABLE:
        if failures > 0 and calls > 0 and failures / calls > 0.1:
            # 桥故障率>10% → 发出警报 + 调优 + 强化链
            _ra("signal_alert", {
                "level": "warning",
                "message": f"桥失败率{failures/calls*100:.1f}% > 10%",
                "source": "gen_桥"
            }, priority=2, source="gen_桥")
            results.append("  动作: 桥警报已注册")

            _ra("update_genome", {
                "changes": {"cycle.self_evolve_interval": 5}
            }, priority=4, source="gen_桥")
            results.append("  动作: 调优已注册")

            _ra("write_chain", {
                "chain": {
                    "src": "自愈·桥",
                    "rel": "修复",
                    "dst": "repair",
                    "dimension": "桥",
                    "content": f"桥失败率过高({failures/calls*100:.1f}%), 自动修复中",
                    "strength": 0.85
                }
            }, priority=6, source="gen_桥")
            results.append("  动作: 强化链已注册")

        elif alignment > 0.9 and calls > 50:
            # 桥健康 → 静默
            results.append("  桥健康, 低优先级")
        else:
            # 中等状态 → 调优
            _ra("update_genome", {
                "changes": {"heal.persist_behavioral": 2}
            }, priority=5, source="gen_桥")
            results.append("  动作: 中等桥状态调优已注册")
    else:
        results.append("[弱] 动作注册表不可用")

    # 4. 分析维度健康(向后兼容)
    try:
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        dim_count = sum(1 for c in chains if c.get("dimension") == "桥")
        total = len(chains)

        try:
            fb = json.loads(_GEN_FEEDBACK_FILE.read_text()) if _GEN_FEEDBACK_FILE.exists() else {"reports": []}
            fb.setdefault("reports", []).append({
                "dimension": "桥",
                "chain_count": dim_count,
                "weak": dim_count < 400,
                "bridge_alignment": alignment,
                "bridge_failures": failures
            })
            fb["reports"] = fb["reports"][-100:]
            _GEN_FEEDBACK_FILE.write_text(json.dumps(fb, ensure_ascii=False, indent=2))
        except:
            pass

        results.insert(0, f"[稳] 桥={dim_count}/{total} aln={alignment:.3f}")
        return "\n".join(results)
    except Exception as _e:
        return f"[弱] 桥 read error: {_e}"
