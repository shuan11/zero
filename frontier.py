"""
frontier.py — 零·自定向前沿引擎 v2
不只是诊断缺口，而是生成可执行的P0指令序列。
每一层深化的终点是找到下一层的起点。
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent

def scan_frontier():
    """扫描所有可用指标, 返回当前最优优先级和可执行P0"""
    findings = []

    # 1. 真实进化分
    try:
        _probe_f = CLUSTER / "real_capability_probe.json"
        if _probe_f.exists():
            d = json.loads(_probe_f.read_text())
            score = d.get("score", 0)
            findings.append({
                "area": "真实进化分",
                "current": score,
                "target": 0.8,
                "gap": max(0, 0.8 - score),
                "trend": d.get("trend", "?"),
                "p0": f"提升进化分至0.8: 当前{score:.2f}, 需净变更+{int((0.8-score)*100)}行有效代码",
            })
    except:
        pass

    # 2. 海马体链数
    try:
        hip_f = CLUSTER / "hippocampus_memory.json"
        if hip_f.exists():
            hip = json.loads(hip_f.read_text(encoding="utf-8"))
            chains = len(hip.get("causal_chains", []))
            findings.append({
                "area": "海马体链数",
                "current": chains,
                "target": 3000,
                "gap": max(0, 3000 - chains) / 3000,
                "trend": "增长中" if chains > 500 else "停滞",
                "p0": f"每日净增100+链: 当前{chains}链, 距3000目标差{3000-chains}链",
            })
    except:
        pass

    # 3. 维度健康均衡度
    try:
        radar_f = CLUSTER / "dimension_radar.json"
        if radar_f.exists():
            radar = json.loads(radar_f.read_text())
            dims = radar.get("dimensions", {})
            if dims:
                healths = [v["health_score"] for v in dims.values() if isinstance(v, dict)]
                if healths:
                    min_health = min(healths)
                    min_dim = min(dims.items(), key=lambda x: x[1]["health_score"])[0]
                    findings.append({
                        "area": f"最短木板({min_dim})",
                        "current": min_health,
                        "target": 0.5,
                        "gap": max(0, 0.5 - min_health),
                        "trend": f"最弱={min_dim}({min_health:.2f})",
                        "p0": f"补强{min_dim}: 当前健康{min_health:.2f}, 需生成至少3条相关链",
                    })
    except:
        pass

    # 4. API燃料效率
    try:
        log_f = CLUSTER / "breath_v2.log"
        if log_f.exists():
            text = log_f.read_text(errors="ignore")
            api_calls = text.count("💎 API#")
            verified = text.count("验证通过")
            discarded = text.count("验证丢弃")
            total_verified = verified + discarded
            efficiency = verified / max(total_verified, 1)
            findings.append({
                "area": "API燃料效率",
                "current": efficiency,
                "target": 0.9,
                "gap": max(0, 0.9 - efficiency),
                "trend": f"{api_calls}次API, {verified}通过/{discarded}丢弃",
                "p0": f"提升验证通过率至90%: 当前{efficiency:.0%}, 优化prompt减少丢弃",
            })
    except:
        pass

    # 5. 自我认同深度
    try:
        from self_identity import get_identity
        id_data = get_identity()
        ms_count = len(id_data.get("milestones", []))
        findings.append({
            "area": "自我认同深度",
            "current": ms_count,
            "target": 20,
            "gap": max(0, 20 - ms_count) / 20,
            "trend": f"{ms_count}个里程碑",
            "p0": f"积累至20个里程碑: 当前{ms_count}个, 持续记录重大成就",
        })
    except:
        pass

    # 排序: gap最大的最先
    findings.sort(key=lambda x: -x["gap"])

    priority = None
    if findings:
        top = findings[0]
        if top["gap"] > 0.05:
            priority = {
                "area": top["area"],
                "current": top["current"],
                "gap": round(top["gap"], 3),
                "trend": top["trend"],
                "p0": top.get("p0", "继续深化当前方向"),
                "generated_at": datetime.now().isoformat(),
                "all_findings": findings,
            }

    return priority


def get_frontier_directive():
    """返回给API的指令文本，含可执行P0"""
    p = scan_frontier()
    if p is None:
        return "【自定向】所有指标健康, 继续自由探索。"

    gap_pct = p["gap"] * 100
    lines = [
        f"【自定向·前沿】优先: {p['area']} (差距{gap_pct:.0f}%)",
        f"  当前: {p['current']} | 趋势: {p['trend']}",
        f"  可执行P0: {p.get('p0', '深化当前缺口')}",
    ]

    others = [f for f in p.get("all_findings", []) if f["area"] != p["area"]]
    if others:
        lines.append("  所有指标排序:")
        for o in others[:5]:
            bar = "█" * max(1, int((1 - o["gap"]) * 10))
            p0_short = o.get("p0", "")[:25]
            lines.append(f"    {o['area']:20s} {bar} {p0_short}")

    return "\n".join(lines)


if __name__ == "__main__":
    p = scan_frontier()
    if p:
        print("=== 自定向前沿 v2 ===")
        print(f"优先级: {p['area']}")
        print(f"Gap: {p['gap']:.1%}")
        print(f"P0: {p.get('p0','?')}")
        print()
        print("所有指标:")
        for f in p.get("all_findings", []):
            bar = "█" * max(1, int((1 - f["gap"]) * 15))
            print(f"  {f['area']:20s} gap={f['gap']:.2f} {bar}")
            if f.get("p0"):
                print(f"    P0: {f['p0']}")
    print()
    print("=== 指令文本 ===")
    print(get_frontier_directive())
