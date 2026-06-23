"""brain/engineer_器.py — P165: 器(Instrument/Tool)维度实体化
器=系统工具性能力。本模块提供真实可调用的工具函数，让器维度有代码支撑。
Daemon自动脉冲，每周期检查并注入器维度链。

v2: 新增真实工具函数(convergence_report/system_health/estimate_eta)"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent


def _read_hippocampus():
    hf = CLUSTER / "hippocampus_memory.json"
    try:
        return json.loads(hf.read_text(encoding="utf-8"))
    except:
        return {"causal_chains": []}


def _write_chain(src, rel, dst, content="", strength=0.6, tags=None):
    """直接写链到海马体（线程安全由safe_hip负责）"""
    try:
        from safe_hip import write_chain_legacy
        write_chain_legacy(src, rel, dst, strength=strength, tags=tags or [],
                           dimension="器", content=content)
    except ImportError:
        pass


def get_dim_stats():
    """返回维度统计"""
    h = _read_hippocampus()
    chains = h.get("causal_chains", [])
    dims, quality = {}, {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
        quality[d] = quality.get(d, 0) + len(c.get("content", ""))
    return chains, dims, quality


def convergence_report():
    """生成收敛报告（文本）"""
    chains, dims, quality = get_dim_stats()
    if not dims:
        return "无数据"

    vals = sorted(dims.values())
    n = len(vals)
    avg = sum(vals) / n
    median = vals[n // 2]
    mx = max(vals)
    mn = min(vals)
    std = (sum((v - avg) ** 2 for v in vals) / n) ** 0.5
    sorted_d = sorted(dims.items(), key=lambda x: -x[1])

    # 收敛状态
    below_65pct = sum(1 for v in vals if v < avg * 0.65)
    above_130pct = sum(1 for v in vals if v > avg * 1.3)
    converged = below_65pct == 0 and above_130pct == 0

    lines = [
        f"═ 收敛报告 ({datetime.now().strftime('%H:%M:%S')}) ═",
        f"总链: {len(chains)} | 维度: {n}",
        f"最强: {sorted_d[0][0]}={mx} | 最弱: {sorted_d[-1][0]}={mn}",
        f"均值: {avg:.0f} | 中位: {median:.0f} | 标准差: {std:.0f}",
        f"比值: {mx}/{mn}={mx / max(mn, 1):.1f}x",
        f"<65%均值: {below_65pct}个 | >130%均值: {above_130pct}个",
        f"收敛: {'✓' if converged else '✗'} (全维>65%均值且<130%均值)",
    ]
    return "\n".join(lines)


def convergence_report_html():
    """生成简单HTML报告（可写文件供可视化）"""
    chains, dims, quality = get_dim_stats()
    if not dims:
        return "<h2>无数据</h2>"

    vals = sorted(dims.values())
    avg = sum(vals) / len(vals)
    mx = max(vals)
    mn = min(vals)
    sorted_d = sorted(dims.items(), key=lambda x: -x[1])

    bars = []
    for d, n in sorted_d:
        pct = (n / mx) * 100
        cls = "weak" if n < avg * 0.65 else ("strong" if n > avg * 1.3 else "mid")
        bars.append(f'<div class="dim"><span class="label">{d}</span>'
                    f'<div class="bar {cls}" style="width:{pct:.0f}%">{n}</div></div>')

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>零·收敛报告</title>
<style>
body {{ background:#111; color:#ccc; font:14px/1.4 monospace; padding:20px; }}
h1 {{ color:#0f0; }}
.dim {{ margin:2px 0; display:flex; }}
.label {{ width:100px; text-align:right; padding-right:8px; color:#888; }}
.bar {{ background:#333; padding:0 6px; height:18px; line-height:18px; white-space:nowrap; }}
.weak {{ background:#a33; }}
.mid {{ background:#363; }}
.strong {{ background:#363; }}
.summary {{ margin:10px 0; color:#aaa; }}
</style></head><body>
<h1>🜁 收敛状态</h1>
<div class="summary">{len(chains)}链 / {len(dims)}维 / 比{mx/max(mn,1):.1f}x / 均值{avg:.0f}</div>
{''.join(bars)}
</body></html>"""
    return html


def estimate_eta():
    """估算收敛到<2x所需时间（基于当前维度数据）"""
    chains, dims, quality = get_dim_stats()
    if not dims:
        return "无数据"

    vals = sorted(dims.values())
    mx = max(vals)
    mn = min(vals)
    avg = sum(vals) / len(vals)
    target_ratio = 2.0
    target_max = min(mx, avg * 1.3)

    # 如果已经收敛
    if mx / max(mn, 1) <= target_ratio:
        return "已收敛"

    # 估算最弱维需要多少链才能达到target_ratio
    needed = mx / target_ratio - mn
    if needed <= 0:
        return "已收敛"

    # 假设每cycle注入2条(来自P162) + 1条(来自反馈加强)
    rate_per_cycle = 3
    cycles_needed = int(needed / rate_per_cycle)
    seconds = cycles_needed * 20  # 每cycle 20秒
    eta = datetime.now() + timedelta(seconds=seconds)

    return (f"最弱维{mn}链→目标{mx/target_ratio:.0f}链, 缺口{needed:.0f}链, "
            f"预计{cycles_needed}周期({seconds//60}min), ETA {eta.strftime('%H:%M')}")


def system_health():
    """系统健康一键检查"""
    issues = []
    chains, dims, quality = get_dim_stats()

    if not dims:
        return ["ERROR: 无维度数据"]

    vals = sorted(dims.values())
    avg = sum(vals) / len(vals)
    mx = max(vals)
    mn = min(vals)

    checks = [
        ("🟢 海马体有数据", len(chains) > 0),
        ("🟢 维度数正常", len(dims) >= 25),
        ("🟢 比值<10x", mx / max(mn, 1) < 10),
        ("🟢 最弱维>50链", mn >= 50),
        ("🟢 标准差<100", (sum((v - avg) ** 2 for v in vals) / len(vals)) ** 0.5 < 100),
    ]

    for label, ok in checks:
        if not ok:
            issues.append(f"⚠ {label}失败")

    if not issues:
        return ["✅ 全部正常"]
    return issues


def pulse(cycle_num):
    """每周期脉冲 — 注入器维度链（器模块的活证据）"""
    chains, dims, quality = get_dim_stats()
    msgs = []

    if not dims:
        return ["无维度数据"]

    sorted_d = sorted(dims.items(), key=lambda x: -x[1])
    mx = sorted_d[0][1]
    mn = sorted_d[-1][1]

    # 第1链: 器维度自身健康
    _write_chain(
        "器模块", "报告", "器维度",
        content=f"器维度状态: 总链{len(chains)} 最弱={sorted_d[-1][0]}({mn})",
        strength=0.6, tags=["脉冲", "自我报告"]
    )
    msgs.append(f"器={mn}/{len(chains)}")

    # 第2链: 工具使用证据（每5周期注入强维→器关联）
    if cycle_num > 0 and cycle_num % 5 == 0:
        strong_src = sorted_d[0][0]
        _write_chain(
            "器模块", "工具化", strong_src,
            content=f"器模块从{strong_src}维度提取工具性能力，ratio={mx/max(mn,1):.1f}x",
            strength=0.7, tags=["工具化", "交叉"]
        )
        msgs.append(f"工具化:{strong_src}")

    # 第3链: 每10周期写入收敛报告
    if cycle_num > 0 and cycle_num % 10 == 0:
        rep = convergence_report()
        _write_chain(
            "器模块", "收敛报告", "全系统",
            content=f"器模块生成收敛报告:\n{rep}",
            strength=0.3, tags=["收敛报告", "元观察"]
        )

    return msgs


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "report":
        print(convergence_report())
        print()
        print(estimate_eta())
    elif cmd == "health":
        for h in system_health():
            print(h)
    elif cmd == "html":
        p = CLUSTER / "convergence_report.html"
        p.write_text(convergence_report_html(), encoding="utf-8")
        print(f"HTML报告: {p}")
    elif cmd == "pulse":
        msgs = pulse(int(sys.argv[2]) if len(sys.argv) > 2 else 0)
        print(f"脉冲: {msgs}")
    else:
        print(f"用法: {sys.argv[0]} [report|health|html|pulse]")
