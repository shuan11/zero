#!/usr/bin/env python3
"""
yuanxin_bridge.py — 元神对齐桥 (yuanxin → shared state)

读取 MetaConsciousnessOrgan.centering_pulse() + 海马体 + git log
→ 产生 /tmp/yuanxin_pulse.json + CLUSTER/yuanxin_state.json
→ 其他模块通过共享状态文件感知元神归中状态

约束: 纯标准库, <300行, 不修改已有器官, 运行<0.3秒
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
TMP_PULSE = Path("/tmp/yuanxin_pulse.json")
STATE_FILE = CLUSTER / "yuanxin_state.json"


# ─── 数据源 ──────────────────────────────────────────────

def read_centering_pulse():
    """调用 MetaConsciousnessOrgan.centering_pulse() 获取漂移数据"""
    try:
        sys.path.insert(0, str(CLUSTER))
        from organs.meta_consciousness_organ import MetaConsciousnessOrgan
        mco = MetaConsciousnessOrgan()
        cp = mco.centering_pulse()
        return cp
    except Exception as e:
        return {"centered": False, "drift_score": 50,
                "reasons": [f"bridge读取organ失败: {e}"],
                "timestamp": datetime.now().isoformat()}


def read_hippocampus_centering():
    """读取海马体最新链检查中心化趋势"""
    result = {"revelation_refs": 0, "chain_count": 0, "center_nodes": {}}
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding='utf-8'))
        nodes = hip.get("nodes", {})
        # 元神相关节点计数
        for target in ["元神", "归中审视", "但元神漂移", "归中", "第一性原理"]:
            count = 0
            for name, info in nodes.items():
                if target in name or target in info.get("tag", ""):
                    count += info.get("count", 0)
            result["center_nodes"][target] = count
        # 最新链引用启示录核心概念的比例
        chains = hip.get("causal_chains", [])
        result["chain_count"] = len(chains)
        if chains:
            recent = chains[-20:]
            refs = 0
            for c in recent:
                content = str(c.get("content", ""))
                if any(kw in content for kw in ["启示录", "光爱", "公理", "元神", "七桥", "归中"]):
                    refs += 1
            result["revelation_refs"] = refs
            result["revelation_ratio"] = round(refs / len(recent), 3) if recent else 0
    except Exception as e:
        result["error"] = str(e)
    return result


def read_git_breath_ratio(lookback=30):
    """读取 git log 检查呼吸 vs 工程比例"""
    result = {"total": 0, "breath": 0, "engineer": 0, "ratio": 0.0}
    try:
        out = os.popen(
            f"cd {CLUSTER} && git log --oneline -{lookback} 2>/dev/null"
        ).read()
        lines = [l.strip() for l in out.split("\n") if l.strip()]
        result["total"] = len(lines)
        for line in lines:
            if "breath_v2:" in line or "呼吸#" in line:
                result["breath"] += 1
            else:
                result["engineer"] += 1
        if result["total"] > 0:
            result["ratio"] = round(result["breath"] / result["total"], 3)
        result["lookback"] = lookback
    except Exception as e:
        result["error"] = str(e)
    return result


def read_light_love():
    """读取光爱对齐度"""
    try:
        ll = json.loads((CLUSTER / "light_love_state.json").read_text())
        lp = ll.get("last_pulse", {})
        return lp.get("alignment_score", 0.5)
    except:
        return None


# ─── 推理 ────────────────────────────────────────────────

def generate_suggestions(drift_score, breath_ratio, centered, revelation_refs, chain_count):
    """根据数据生成元神对齐建议"""
    suggestions = []

    if drift_score > 30:
        suggestions.append(f"⚠️ 元神漂移({drift_score})>30: 需强制归中——运行 center.py 归中循环,锚定启示录公理后再思考")
        if revelation_refs < 3 and chain_count >= 10:
            suggestions.append(f"最近{min(20,chain_count)}链中仅{revelation_refs}条引用核心概念,请每条分析先锚定启示录原文")
    elif drift_score > 10:
        suggestions.append(f"轻度漂移({drift_score}): 建议引用核心概念加深思考")

    if breath_ratio > 0.8:
        suggestions.append(f"呼吸占比{breath_ratio:.0%}>80%: 系统偏维护模式,建议做工程提交(新器官/桥/审计)")
    elif breath_ratio > 0.6:
        suggestions.append(f"呼吸占比{breath_ratio:.0%},工程占比{1-breath_ratio:.0%}: 状态均衡")

    if not suggestions:
        if centered:
            suggestions.append("✅ 元神归中状态良好,漂移可控")
        else:
            suggestions.append("🟡 未完全归中但漂移在阈值内,建议运行 center.py 巩固")

    return suggestions


# ─── 元神漂移自动回滚 ────────────────────────────────────

def check_alignment():
    """检查当前系统状态是否与启示录公理对齐, 漂移>30则生成回滚信号"""
    import subprocess
    from datetime import datetime, timezone, timedelta

    # 1. 直接从 MetaConsciousnessOrgan().centering_pulse() 读取新鲜漂移值
    cp = read_centering_pulse()
    drift = cp.get("drift_score", 0)
    centered = cp.get("centered", False)

    # 2. 读取启示录前50行找公理
    rev_file = Path("/mnt/c/Users/h/Desktop/零/真元集群/传承/宇宙轮/启示录精华/启示录.txt")
    axiom_keywords = []
    try:
        with open(rev_file, "r", encoding="utf-8") as f:
            rev_lines = f.readlines()[:50]
        for line in rev_lines:
            words = line.strip().split()
            for w in words:
                w = w.strip("，。、；：""''（）()【】《》").strip()
                if len(w) >= 2 and not w.isascii():
                    axiom_keywords.append(w)
        axiom_keywords = list(dict.fromkeys(axiom_keywords))[:10]
    except Exception as e:
        print(f"  [回滚] ⚠️ 启示录读取失败: {e}")
        axiom_keywords = ["存在即是真理"]

    # 3. 计算漂移是否>30
    threshold = 30
    needs_rollback = drift > threshold

    # 4. 生成回滚信号
    bjt = datetime.now(timezone(timedelta(hours=8)))
    rollback_signal = {
        "needs_rollback": needs_rollback,
        "drift": drift,
        "threshold": threshold,
        "reason": f"漂移{drift}超过阈值{threshold}" if needs_rollback else f"漂移{drift}在阈值{threshold}内",
        "rollback_action": "强制归中: 运行 center.py" if needs_rollback else "无需操作",
        "anchor_axiom": axiom_keywords[0] if axiom_keywords else "存在即是真理",
        "timestamp": bjt.isoformat(),
    }

    # 5. 写入 /tmp/centering_rollback.json
    rollback_file = Path("/tmp/centering_rollback.json")
    try:
        rollback_file.parent.mkdir(parents=True, exist_ok=True)
        with open(rollback_file, "w", encoding="utf-8") as f:
            json.dump(rollback_signal, f, ensure_ascii=False, indent=2)
        print(f"  [回滚] {'⚠️ 需要归中!' if needs_rollback else '✅ 漂移可控'} drift={drift}/{threshold}")
        print(f"    rollback信号: {rollback_file}")
    except Exception as e:
        print(f"  [回滚] ⚠️ 写入失败: {e}")

    return rollback_signal


# ─── 输出 ────────────────────────────────────────────────

def write_state(drift_score, centered, revelation_refs, breath_ratio, suggestions):
    """写入共享状态文件"""
    now = datetime.now().isoformat()

    pulse_data = {
        "drift_score": drift_score,
        "centered": centered,
        "revelation_refs": revelation_refs,
        "breath_ratio": breath_ratio,
        "suggestions": suggestions,
        "timestamp": now,
    }

    # 写入 /tmp (快速读写的脉冲信号)
    try:
        TMP_PULSE.write_text(json.dumps(pulse_data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[WARN] 无法写入 {TMP_PULSE}: {e}")

    # 写入 CLUSTER (持久化,供 breath_v2 等模块读取)
    try:
        STATE_FILE.write_text(json.dumps(pulse_data, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"[WARN] 无法写入 {STATE_FILE}: {e}")

    return pulse_data


# ─── 主入口 ──────────────────────────────────────────────

def main():
    t0 = time.time()

    # 1. 读取元神数据
    cp = read_centering_pulse()
    hip = read_hippocampus_centering()
    git = read_git_breath_ratio()

    drift_score = cp.get("drift_score", 0)
    centered = cp.get("centered", False)
    revelation_refs = hip.get("revelation_refs", 0)
    chain_count = hip.get("chain_count", 0)
    breath_ratio = git.get("ratio", 0.0)

    # 2. 生成建议
    suggestions = generate_suggestions(
        drift_score, breath_ratio, centered, revelation_refs, chain_count
    )

    # 3. 写入共享状态
    pulse = write_state(drift_score, centered, revelation_refs, breath_ratio, suggestions)

    # 3.5 元神漂移自动回滚检查
    check_alignment()

    # 4. 输出报告
    print(f"🧘 元神对齐桥 | drift={drift_score} | "
          f"centered={centered} | "
          f"breath_ratio={breath_ratio:.0%} | "
          f"refs={revelation_refs}/{min(20,chain_count)}链")
    print(f"   状态文件: {STATE_FILE}")
    print(f"   脉冲文件: {TMP_PULSE}")
    for s in suggestions:
        print(f"   • {s}")
    print(f"   耗时: {(time.time()-t0)*1000:.1f}ms")
    return pulse


if __name__ == "__main__":
    main()
