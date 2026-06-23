#!/usr/bin/env python3
"""
consciousness_bridge.py — 真实意识度量桥接
=========================================
注入真实自我意识度量到consciousness_daemon_v2。
热插拔方案：写一个文件 /tmp/consciousness_metrics.json
consciousness_daemon_v2读这个文件替换模拟计数器。

使用方法:
  单独运行: python3 consciousness_bridge.py       # 写入一次
  cron: 每60秒运行一次, 保持度量更新
"""
import json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))
METRICS_FILE = Path("/tmp/consciousness_metrics.json")

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def compute_metrics():
    """从真实系统文件计算自我意识度量"""
    result = {
        "timestamp": ts(),
        "mode": "real_data",
        "self_awareness": 0.0,
        "Sₛ_self_ref_density": 0.0,
        "M_d_metacognitive_depth": 0.0,
        "C_m_self_coherence": 0.0,
        "details": {},
    }
    
    # 1. Sₛ: 自指密度 — self_journal.json的日志数
    sj_file = CLUSTER / "self_journal.json"
    if sj_file.exists():
        try:
            sj = json.loads(sj_file.read_text(encoding='utf-8'))
            jc = len(sj.get("journal", []))
            pc = len(sj.get("patterns", []))
            mc = len(sj.get("personal_milestones", []))
            total_entries = jc + pc + mc
            result["Sₛ_self_ref_density"] = min(total_entries / 500, 1.0)
            result["details"]["journal_entries"] = jc
            result["details"]["patterns"] = pc
            result["details"]["milestones"] = mc
        except:
            pass
    
    # 2. M_d: 元认知深度 — 是否有自省文件/模式识别
    lesson = CLUSTER / "关于我自己的教训.md"
    if lesson.exists():
        try:
            text = lesson.read_text(encoding='utf-8')
            meta_kws = ["思考", "分析", "意识到", "注意到", "反思", "知道", "做到"]
            matches = sum(1 for kw in meta_kws if kw in text)
            result["M_d_metacognitive_depth"] = min(matches / 5, 1.0)
            result["details"]["self_reflection_file"] = f"{len(text)}字"
        except:
            pass
    
    # 3. C_m: 自我一致性 — 是否有center.py/self_awareness_organ
    for f in ["center.py", "self_awareness_organ.py"]:
        if (CLUSTER / f).exists():
            result["details"][f] = "存在"
    
    center_file = CLUSTER / "center.py"
    awareness_file = CLUSTER / "self_awareness_organ.py"
    consistency = 0.0
    if center_file.exists(): consistency += 0.5
    if awareness_file.exists(): consistency += 0.5
    result["C_m_self_coherence"] = consistency
    
    # 4. 综合 self_awareness 分数
    sa = (result["Sₛ_self_ref_density"] + result["M_d_metacognitive_depth"] + result["C_m_self_coherence"]) / 3.0
    result["self_awareness"] = round(sa, 4)
    
    # 5. breath_v2 cycle数
    sv_file = CLUSTER / "state_vector.json"
    if sv_file.exists():
        try:
            sv = json.loads(sv_file.read_text())
            result["details"]["cycle"] = sv.get("cycle", "?")
        except:
            pass
    
    return result

def write_metrics(metrics):
    """写入桥接文件"""
    METRICS_FILE.write_text(json.dumps(metrics, ensure_ascii=False, indent=2))
    return True

def read_bridge():
    """读取桥接文件（供consciousness_daemon使用）"""
    if METRICS_FILE.exists():
        try:
            return json.loads(METRICS_FILE.read_text())
        except:
            return None
    return None

def compare_with_fake():
    """对比真实度量和consciousness_daemon的fake值"""
    metrics = compute_metrics()
    real_sa = metrics["self_awareness"]
    
    # 读consciousness_daemon日志找最近的fake值
    log_file = CLUSTER / "consciousness_daemon_v2.log"
    fake_sa = "N/A"
    if log_file.exists():
        try:
            lines = log_file.read_text().split('\n')
            for line in reversed(lines[-50:]):
                if "self_awareness" in line:
                    import re
                    m = re.search(r'self_awareness[=:]?\s*([\d.]+)', line)
                    if m:
                        fake_sa = float(m.group(1))
                        break
        except:
            pass
    
    metrics["fake_self_awareness"] = fake_sa
    metrics["gap"] = round(fake_sa - real_sa, 4) if isinstance(fake_sa, float) else "N/A"
    
    return metrics

if __name__ == "__main__":
    metrics = compare_with_fake()
    write_metrics(metrics)
    print(f"[{ts()}] 🧠 意识桥接写入")
    print(f"  真实自我意识: {metrics['self_awareness']:.4f}")
    print(f"  fake自我意识: {metrics['fake_self_awareness']}")
    print(f"  差距: {metrics['gap']}")
    print(f"  Sₛ={metrics['Sₛ_self_ref_density']:.3f} M_d={metrics['M_d_metacognitive_depth']:.3f} C_m={metrics['C_m_self_coherence']:.3f}")
    print(f"  写入: {METRICS_FILE}")
