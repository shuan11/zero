#!/usr/bin/env python3
"""gen_质量仪表 — P217: 质量指标可视 + 检测修复闭环

每5cycle生成一次质量快报，显示real_pct趋势、高模板维度、改进速度。
同时触发自动修复：长src清理、旧格式标准化。
"""
import json, time
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
HIP_FILE = ROOT / "hippocampus_memory.json"
DASHBOARD = ROOT / "brain/.质量仪表.json"
_CALL_COUNT = 0
_RUN_EVERY = 5

_TEMPLATE_MARKERS = [
    "全维收敛:", "收敛路径:", "认知势差:", "底部填充:",
    "收敛深化:", "映射桥梁:", "结构匹配:", "交叉深化:",
    "弱维激活:", "受最强", "需建立从", "需从", "牵引，需",
    "优先吸收来自", "对标", "当前覆盖度",
    "底注_", "跨维授粉_", "弱维聚焦", "品质升级_",
    "收敛顶注:", "后处理·", "海马体观测#",
    "的认知密度远低于", "是注入最短路径",
    "弱维纠正·",
]

# 元内容标记 — 检测链是"论述维度本身"还是"具体实现"
_META_PATTERNS = [
    "【维度",           # 【维度盲区定义】
    "维度盲区是",       # 解释维度是什么
    "维度盲区指",
    "的填补方法",       # 方法论叙述
    "的本质是",        # 本质定义
    "的本质——", 
    "作为一种",
    "指的是",          # 指代定义
    "可以理解为",
    "所谓的",
    "看不见的维度",     # 维度盲区常见描述 
    "注意: ",          # 注释性说明
    "举个类比",
    "这就像",
    "打个比方",
    "换句话说",
    "简单来说",
    "从哲学角度",
    "从定义上看",
    "概念上讲",
]

# 消费待办/动作标记 — 需要被消费但不是有意义的内容
_ACTION_MARKERS = [
    "[消费待办]",
    "[深析←]",
    "[深析]",
    "[自观]",
    "[靶向]",
    "弱维<",
    "消费待办",
]


def _is_template(content=""):
    for m in _TEMPLATE_MARKERS:
        if m in content:
            return True
    return False

def _is_meta(content=""):
    """检测链内容是'论述维度本身'的元叙述而非具体实例"""
    for m in _META_PATTERNS:
        if m in content:
            return True
    return False

def _is_action_item(content=""):
    """检测链是待办/动作标记而非实质性内容"""
    for m in _ACTION_MARKERS:
        if m in content:
            return True
    return False


def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _CALL_COUNT % _RUN_EVERY != 1:
        return {"status": "skipped", "pulse": _CALL_COUNT}

    try:
        hip = json.loads(HIP_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"status": "error", "msg": "读海马体失败"}

    chains = hip.get("causal_chains", [])
    if not chains:
        return {"status": "error", "msg": "无链"}

    total = len(chains)
    dim_counts = Counter(c.get("dimension", "?") for c in chains
                         if c.get("dimension") not in ("未分类", "系统", "?"))

    # 质量分析
    dim_quality = {}
    for dim in dim_counts:
        dc = [c for c in chains if c.get("dimension") == dim]
        tmpl = sum(1 for c in dc if _is_template(c.get("content", "")))
        meta = sum(1 for c in dc if _is_meta(c.get("content", "")))
        action = sum(1 for c in dc if _is_action_item(c.get("content", "")))
        real = len(dc) - tmpl - meta - action
        dim_quality[dim] = {
            "total": len(dc),
            "template": tmpl,
            "meta": meta,
            "action_item": action,
            "real": real,
            "tmpl_pct": round(100 * tmpl / max(len(dc), 1), 1),
            "meta_pct": round(100 * meta / max(len(dc), 1), 1),
            "action_pct": round(100 * action / max(len(dc), 1), 1),
        }

    real_total = sum(v["real"] for v in dim_quality.values())
    tmpl_total = sum(v["template"] for v in dim_quality.values())
    real_pct = round(100 * real_total / max(real_total + tmpl_total + sum(v["meta"] for v in dim_quality.values()) + sum(v["action_item"] for v in dim_quality.values()), 1), 1)

    # 长src & 旧格式
    long_src = [c for c in chains if len(c.get("src", "")) > 60]
    old_fmt = [c for c in chains if not c.get("src") or not c.get("rel") or not c.get("dst")]

    # 高模板维(>60%)
    high_tmpl = sorted(
        [(d, v["tmpl_pct"], v["template"], v["real"])
         for d, v in dim_quality.items() if v["tmpl_pct"] > 60],
        key=lambda x: -x[1]
    )

    # 高元叙述维(>50%链是"关于维度本身"的论述)
    high_meta = sorted(
        [(d, v["meta_pct"], v["meta"], v["total"])
         for d, v in dim_quality.items() if v["total"] >= 10 and v["meta_pct"] > 50],
        key=lambda x: -x[1]
    )

    # 高动作待办维(>30%链是未消费动作标记)
    high_action = sorted(
        [(d, v["action_pct"], v["action_item"], v["total"])
         for d, v in dim_quality.items() if v["total"] >= 10 and v["action_pct"] > 30],
        key=lambda x: -x[1]
    )

    # 最强/最弱维
    sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
    weakest = sorted_dims[:3] if len(sorted_dims) >= 3 else sorted_dims
    strongest = sorted_dims[-3:] if len(sorted_dims) >= 3 else sorted_dims

    report = {
        "timestamp": time.strftime("%H:%M:%S"),
        "total_chains": total,
        "dimensions": len(dim_counts),
        "real_pct": real_pct,
        "template_chains": tmpl_total,
        "real_chains": real_total,
        "long_src": len(long_src),
        "old_format": len(old_fmt),
        "high_template_dims": high_tmpl[:5],
        "high_meta_dims": high_meta[:5],
        "high_action_item_dims": high_action[:5],
        "weakest_dims": [(d, c) for d, c in weakest],
        "strongest_dims": [(d, c) for d, c in strongest],
        "trend_direction": "up" if real_pct > 55 else "stagnant" if real_pct > 50 else "needs_boost",
    }

    # 自动修复: 截断长src字段
    if long_src:
        fixed = 0
        for c in chains:
            if len(c.get("src", "")) > 60:
                c["src"] = c["src"][:57] + "..."
                fixed += 1
        if fixed > 0:
            hip["causal_chains"] = chains
            tmp = HIP_FILE.with_suffix(".tmp_dash")
            tmp.write_text(json.dumps(hip, ensure_ascii=False), encoding="utf-8")
            tmp.replace(HIP_FILE)
            report["fixed_long_src"] = fixed

    # 保存仪表盘
    try:
        DASHBOARD.parent.mkdir(parents=True, exist_ok=True)
        DASHBOARD.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {
        "status": "ok",
        "real_pct": real_pct,
        "high_tmpl": len(high_tmpl),
        "pulse": _CALL_COUNT,
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result.get("status") == "ok":
        print(f"\n仪表盘: {DASHBOARD}")
        print(json.loads(DASHBOARD.read_text(encoding="utf-8")))
