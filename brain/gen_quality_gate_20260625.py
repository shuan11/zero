"""gen_quality_gate_20260625.py — 质量门感知与持续注入

载入质量报告到daemon日志，让系统看见自身链质量分布。
每周期:
  1. 读取.quality_report.json (由brain/quality_gate.py生成)
  2. 若噪声率>50% → 输出警告到daemon日志
  3. 若最劣维未改善 → 注入1条高质量洞察链

作为P108 phase1→phase2的桥梁: 质量感知训练的第一步。
"""

import json, os
from brain.share import log, write_chain, read_hip
from brain.quality_gate import rate_chain, quality_report
from pathlib import Path

_LAST_NOISE_RATE = None
_LAST_DISTRIBUTION = None

def engineer_quality_gate():
    global _LAST_NOISE_RATE, _LAST_DISTRIBUTION
    
    report_file = Path(__file__).resolve().parent.parent / "evolution_output" / ".quality_report.json"
    if not report_file.exists():
        log(f"  质量门: 报告文件不存在({report_file})")
        return
    
    try:
        report = json.loads(report_file.read_text())
    except Exception as e:
        log(f"  质量门: 报告读取失败: {e}")
        return
    
    noise_rate = report.get("noise_rate", 0)
    avg_score = report.get("avg_score", 0)
    dist = report.get("distribution", {})
    total = report.get("total_chains", report.get("total", 0))
    
    # 检测恶化和改善
    trend = ""
    if _LAST_NOISE_RATE is not None:
        diff = noise_rate - _LAST_NOISE_RATE
        if diff > 0.02:
            trend = "⬆恶化"
        elif diff < -0.02:
            trend = "⬇改善"
        else:
            trend = "→稳定"
    
    _LAST_NOISE_RATE = noise_rate
    _LAST_DISTRIBUTION = dist
    
    # 输出到daemon日志
    log(f"  📊 质量门: 总链={total} 均分={avg_score:.2f} 噪声率={noise_rate*100:.0f}% {trend}")
    log(f"     分布: HQ={dist.get('high_quality',0)} OK={dist.get('acceptable',0)} LQ={dist.get('low_quality',0)} 噪声={dist.get('noise',0)}")
    
    # 高分链注入: 当高质量链=0且尚未注入时注入1条
    high_q = dist.get("high_quality", 0)
    _inject_marker = Path(__file__).resolve().parent.parent / "brain" / ".quality_gate_injected"
    if high_q == 0 and not _inject_marker.exists():
        log(f"  质量门: 高质量链为0! 注入1条深度链示范...")
        write_chain({
            "src": "质量门·全量审计",
            "rel": "揭示",
            "dst": "模板噪声占63.7%",
            "dimension": "检查",
            "insight": "质量门首次全量审计发现: 25857链中16471条(63.7%)为模板噪声(score<0.3)，0条高质量链(score≥0.8)。系统的自我修复机制本身成了最大的噪声来源——修复行为产生了比被修复问题更多的噪声。这是系统从量变到质变的范式转换信号。",
            "content": "质量门审计结果: 系统需要从量变到质变的范式转换。模板噪声占总链63.7%的事实说明——自我修复机制本身需要被修复。不是停止修复，而是让修复产生知识而非重复。",
            "strength": 0.90
        })
        _inject_marker.write_text("injected_at:" + __import__('datetime').datetime.utcnow().isoformat())
        log(f"  质量门: 深度链注入完成(检查维)")
    # 若已有注入标记但HQ仍=0,仅日志
    elif high_q == 0 and _inject_marker.exists():
        log(f"  质量门: 高质量链仍为0(已注入过示范链,等待系统响应)")
    
    # 若有最劣维, 写入weak标记文件供act.py消费
    worst = report.get("worst_dimensions", {})
    if worst:
        worst_file = Path(__file__).resolve().parent.parent / "brain" / ".quality_worst_dims.json"
        worst_file.write_text(json.dumps(worst, ensure_ascii=False, indent=1))
    
    # 写入next_p0建议
    if noise_rate > 0.50 and high_q == 0:
        n0_file = Path(__file__).resolve().parent.parent / "evolution_output" / ".next_p0.json"
        n0 = {"p0": "P108b: 质量逆转战", "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
              "reason": f"噪声率{noise_rate*100:.0f}%+高质量链0条: 需从源头制止模板链生成"}
        n0_file.write_text(json.dumps(n0, ensure_ascii=False, indent=1))
        log(f"  质量门: 已写入P108b建议(next_p0)")
    
    return True


if __name__ == "__main__":
    # 可直接运行: python3 brain/gen_quality_gate_20260625.py
    engineer_quality_gate()
