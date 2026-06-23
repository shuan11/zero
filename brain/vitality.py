"""P103: 系统活力检测 — 衡量每周期是否真正进化"""
import json, time
from pathlib import Path
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent.parent
TREND_FILE = CLUSTER / ".brain_vitality_trend.json"
WINDOW = 10  # 最近N周期

def _measure_vitality():
    """产出5维活力评分"""
    from brain.share import read_hip
    hip = read_hip()
    chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    if not chains:
        return {k: 0 for k in ["growth", "diversity", "crosslinks", "freshness", "overall"]}
    
    # 1) 增长: 本周期新增链数(取最后100)
    recent = chains[-100:]
    growth = len(recent)  # 粗略: 如果周期内产<100链, 增长=实际新增
    
    # 2) 多样性: 不同src数
    srcs = len(set(c.get("src", "") for c in recent))
    diversity = min(srcs / 10, 1.0)  # 期望≥10不同来源
    
    # 3) 交叉链接: 不同dimension之间的rel数量
    dim_pairs = set()
    for c in recent:
        s = c.get("dimension", "")
        t = c.get("dst", c.get("src", ""))
        if s and t and s != t:
            dim_pairs.add((s, t))
    crosslinks = min(len(dim_pairs) / 5, 1.0)  # 期望≥5不同对
    
    # 4) 新鲜度: 内容是否各有不同
    contents = set(c.get("content", "")[:30] for c in recent)
    freshness = min(len(contents) / max(len(recent), 1) * 2, 1.0)
    
    overall = (growth / 50 * 0.3 + diversity * 0.25 + crosslinks * 0.25 + freshness * 0.2)
    overall = min(overall, 1.0)
    
    return {
        "growth": growth,
        "diversity": round(diversity, 3),
        "crosslinks": round(crosslinks, 3),
        "freshness": round(freshness, 3),
        "overall": round(overall, 3)
    }

def pulse(cycle_num):
    """每周期记录活力并检测退化"""
    score = _measure_vitality()
    score["cycle"] = cycle_num
    score["ts"] = time.time()
    
    # 加载历史趋势
    trend = {"history": []}
    if TREND_FILE.exists():
        try:
            trend = json.loads(TREND_FILE.read_text())
        except:
            trend = {"history": []}
    
    trend["history"].append(score)
    # 只保留最近WINDOW个
    if len(trend["history"]) > WINDOW:
        trend["history"] = trend["history"][-WINDOW:]
    TREND_FILE.write_text(json.dumps(trend, ensure_ascii=False, indent=2))
    
    # 检测退化: 连续3周期overall下降
    if len(trend["history"]) >= 3:
        last3 = trend["history"][-3:]
        if all(last3[i]["overall"] < last3[i-1]["overall"] for i in range(1, 3)):
            return {"status": "DECLINE", "score": score, "msg": f"活力连续3周期下降({last3[0]['overall']}→{last3[2]['overall']})"}
    
    return {"status": "OK", "score": score, "msg": f"活力={score['overall']} 增长={score['growth']} 多样={score['diversity']} 交叉={score['crosslinks']} 新鲜={score['freshness']}"}
