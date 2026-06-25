"""brain/quality_gate.py — 因果链质量门

职责:
  1. 区分真实链(有知识增量) vs 模板噪声(无知识增量)
  2. 为每条链打质量分 0-1
  3. 提供批量统计: 质量分布/模板率/噪声率
  4. (可选) 拦截低质量链写入

用法:
  from brain.quality_gate import rate_chain, filter_chains, quality_report

设计原则:
  - 纯函数无状态: 输入链→输出分数,不依赖外部缓存
  - 保守拦截: 宁可放行模糊链,不拦截可能有用链
  - 每维独立: 模板链在不同维度可能有不同基线长度
"""

import re
import json
from pathlib import Path
from collections import Counter

# ─── 持久化日志 ─────────────────────────────────────
_BLOCKED_LOG_PATH = Path(__file__).resolve().parent.parent / "blocked_chains.json"
_MAX_BLOCKED_LOG = 1000  # 循环缓冲上限


def _load_blocked_log():
    """读取被拦截链日志"""
    if _BLOCKED_LOG_PATH.exists():
        try:
            with open(_BLOCKED_LOG_PATH) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _save_blocked_log(entries):
    """写入被拦截链日志(循环缓冲)"""
    if len(entries) > _MAX_BLOCKED_LOG:
        entries = entries[-_MAX_BLOCKED_LOG:]
    try:
        with open(_BLOCKED_LOG_PATH, 'w') as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def log_blocked_chain(chain: dict, rating: dict):
    """将一条被拦截的链记录到持久日志
    
    Args:
        chain: 原始链
        rating: rate_chain()的评分结果
    """
    entry = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "chain": {
            "src": chain.get("src", ""),
            "rel": chain.get("rel", ""),
            "dst": chain.get("dst", ""),
            "content": chain.get("content", ""),
            "dimension": chain.get("dimension", ""),
        },
        "rating": rating,
    }
    entries = _load_blocked_log()
    entries.append(entry)
    _save_blocked_log(entries)


def analyze_blocked_clusters() -> dict:
    """分析被拦截链的聚类盲区
    
    对blocked_log中的链按content/rel/dimension聚类,
    发现可能的新维萌芽或系统性模板模式
    
    Returns:
        {"total_blocked": N, "clusters": [{...}], "new_dim_candidates": [...]}
    """
    entries = _load_blocked_log()
    if not entries:
        return {"total_blocked": 0, "clusters": [], "new_dim_candidates": []}

    # 按rel聚合(rel是二元关系,含关键pattern信息)
    rel_counts = Counter()
    dim_counts = Counter()
    content_samples = {}

    for e in entries:
        c = e.get("chain", {})
        rel = c.get("rel", "?")
        dim = c.get("dimension", "?")
        rel_counts[rel] += 1
        dim_counts[dim] += 1
        if rel not in content_samples and c.get("content"):
            content_samples[rel] = c["content"][:150]

    # 聚类: 出现≥3次的rel认为是模式
    clusters = []
    for rel, cnt in rel_counts.most_common(10):
        if cnt >= 3:
            clusters.append({
                "pattern": rel,
                "count": cnt,
                "rate": round(cnt / len(entries), 3),
                "sample_content": content_samples.get(rel, ""),
            })

    # 新维候选: dimension="?" 或 未知 且次数≥3
    new_dim_candidates = []
    for dim, cnt in dim_counts.most_common(5):
        if dim in ("?", "", "unknown", "未分类") and cnt >= 3:
            # 找这些链的conent共性
            samples = []
            for e in entries:
                if e.get("chain", {}).get("dimension", "") == dim:
                    c = e["chain"]
                    samples.append(f"{c.get('src','')}→{c.get('dst','')}: {c.get('content','')[:80]}")
            new_dim_candidates.append({
                "dimension": dim,
                "count": cnt,
                "samples": samples[:5],
            })

    return {
        "total_blocked": len(entries),
        "clusters": clusters[:10],
        "new_dim_candidates": new_dim_candidates[:3],
        "by_dimension": dict(dim_counts.most_common(10)),
    }

# ─── 模板模式 ─────────────────────────────────────
# 匹配自愈/自循环/系统自动生成的链
_TEMPLATE_PATTERNS = [
    r"自愈.*?#\d+",            # 自愈·主动行为#5
    r"自动补链.*?#\d+",        # 自动补链·#123
    r"弱维纠正.*?→.*?",        # 弱维纠正·势→势
    r"巩固.*?→.*?",            # 巩固·自指→自指
    r"被动注入.*?#\d+",        # 被动注入·#45
    r"弱维支撑.*?#\d+",        # 脑核·弱维支撑#9
    r"自加强链#\d+",           # 自加强链#10
    r"交叉加强链#\d+",         # 交叉加强链#5
    r"自愈: 弱维.*?→自加强链", # 自愈: 弱维xxx(2周期,差距597)→自加强链#9
    r"管道自繁殖.*?→.*?",      # 管道自繁殖→势
    r"持续补链.*?#\d+",       # 持续补链·#3
    r"record_dimension_.*?",   # 函数注入链
]

_TEMPLATE_RE = re.compile("|".join(_TEMPLATE_PATTERNS), re.IGNORECASE)

# ─── 低信息密度模式 ───────────────────────────────
# 内容过于简短或重复
_MIN_CONTENT_LEN = 40          # 链content字段最小有意义的长度
_MIN_INSIGHT_LEN = 30          # chain.get("insight","")最小长度
_SRC_DST_MIN_DISTINCT = 2      # src和dst的编辑距离(字符差异)最小值


def _levenshtein_dist(s1: str, s2: str) -> int:
    """简易编辑距离(只算前100字符)"""
    s1, s2 = s1[:100], s2[:100]
    if not s1 or not s2:
        return abs(len(s1) - len(s2))
    # 快速判断: 完全不同则直接返回
    if s1 == s2:
        return 0
    return sum(1 for a, b in zip(s1, s2) if a != b) + abs(len(s1) - len(s2))


def rate_chain(chain: dict) -> dict:
    """评估单条因果链的质量

    Args:
        chain: 因果链字典(至少含src/rel/dst,可选content/insight/dimension)

    Returns:
        {"score": 0.0-1.0, "reason": str, "tags": [str]}
        score=0.0-0.29 → 模板噪声(建议拦截)
        score=0.30-0.59 → 低质量(允许写但标记)
        score=0.60-0.79 → 一般(可接受)
        score=0.80-1.0  → 高质量(有知识增量)
    """
    src = chain.get("src", "")
    rel = chain.get("rel", "")
    dst = chain.get("dst", "")
    content = chain.get("content", "")
    insight = chain.get("insight", "")
    dimension = chain.get("dimension", "")

    # 拼接全文用于评分
    full_text = f"{src} {rel} {dst} {content} {insight}"
    full_len = len(full_text)

    reasons = []
    tags = []
    deductions = 0.0
    boost = 0.0

    # ── 检测1: 模板模式 ──
    if _TEMPLATE_RE.search(full_text):
        deductions += 0.45
        reasons.append("模板模式匹配")
        tags.append("template")

    # ── 检测2: src≈dst(自循环) ──
    src_lower = src.lower().strip()
    dst_lower = dst.lower().strip()
    if src_lower and dst_lower and src_lower == dst_lower:
        deductions += 0.20
        reasons.append("src=dst自循环")
        tags.append("self_loop")
    elif src_lower and dst_lower:
        dist = _levenshtein_dist(src_lower, dst_lower)
        if dist < _SRC_DST_MIN_DISTINCT:
            deductions += 0.10
            reasons.append(f"src≈dst(编辑距离={dist})")
            tags.append("near_self_loop")

    # ── 检测3: 内容过短 ──
    if content and len(content) < _MIN_CONTENT_LEN:
        deductions += 0.15
        reasons.append(f"content过短({len(content)}<{_MIN_CONTENT_LEN})")
        tags.append("short_content")
    if insight and len(insight) < _MIN_INSIGHT_LEN:
        deductions += 0.10
        reasons.append(f"insight过短({len(insight)}<{_MIN_INSIGHT_LEN})")
        tags.append("short_insight")

    # ── 检测4: 无content+无insight(只有骨架) ──
    if not content and not insight:
        deductions += 0.30
        reasons.append("无content+无insight")
        tags.append("skeleton_only")

    # ── 检测5: 编号化内容(如#9, (2周期)) ──
    num_patterns = len(re.findall(r"#\d+|周期|阈值|\d+/\d+", full_text))
    if num_patterns >= 3:
        deductions += 0.10
        reasons.append(f"编号化内容({num_patterns}个数字标记)")
        tags.append("number_heavy")

    # ── 加分项: 有insight且有深度 ──
    if insight and len(insight) > 60:
        # 检测是否包含有意义的陈述(含"→" / "=" / "是" / "不是")
        meaningful_markers = ["→", "=", "是 ", "不是", "因为", "所以", "导致", "意味", "在于", "决定"]
        markers_found = sum(1 for m in meaningful_markers if m in insight)
        if markers_found >= 1:
            boost += 0.15
            tags.append("reasoning")
        if markers_found >= 2:
            boost += 0.10
        if len(insight) > 120:
            boost += 0.05
            tags.append("detailed")

    # ── 加分项: 维度明确且有深度 ──
    if dimension and dimension not in ("未分类", "unknown"):
        boost += 0.05
        tags.append("dimensioned")

    # ── 最终分数 ──
    score = max(0.0, min(1.0, 0.65 - deductions + boost))
    # 标准化到0.0-1.0

    if score >= 0.80:
        tags.append("high_quality")
    elif score >= 0.60:
        tags.append("acceptable")
    elif score >= 0.30:
        tags.append("low_quality")
    else:
        tags.append("noise")

    return {
        "score": round(score, 3),
        "reason": "; ".join(reasons) if reasons else "通过",
        "tags": tags,
        "dimension": dimension or "?"
    }


def filter_chains(chains: list, threshold: float = 0.30) -> dict:
    """批量过滤链

    Args:
        chains: 因果链列表
        threshold: 最低通过分数(0.0-1.0)

    Returns:
        {"passed": [chain], "blocked": [chain_with_score],
         "stats": {"total": N, "passed": N, "blocked": N, "avg_score": float}}
    """
    results = [rate_chain(c) for c in chains]
    passed = []
    blocked = []
    scores = []

    for chain, rating in zip(chains, results):
        scores.append(rating["score"])
        if rating["score"] >= threshold:
            passed.append(chain)
        else:
            blocked.append((chain, rating))
            # 记录拦截链到持久日志(异步安全)
            try:
                log_blocked_chain(chain, rating)
            except Exception:
                pass

    avg = sum(scores) / len(scores) if scores else 0
    return {
        "passed": passed,
        "blocked": blocked,
        "stats": {
            "total": len(chains),
            "passed": len(passed),
            "blocked": len(blocked),
            "avg_score": round(avg, 3),
            "block_rate": round(len(blocked) / len(chains), 3) if chains else 0
        }
    }


def quality_report(chains: list) -> dict:
    """生成质量统计报告

    Args:
        chains: 因果链列表

    Returns:
        {
            "total": N,
            "distribution": {"high_quality": N, "acceptable": N, "low_quality": N, "noise": N},
            "avg_score": float,
            "per_dimension": {dim_name: {"count": N, "avg_score": float, "noise_rate": float}},
            "template_rate": float,  # 模板模式占比
            "noise_rate": float,     # 噪声(score<0.3)占比
        }
    """
    ratings = [rate_chain(c) for c in chains]
    total = len(ratings)
    if total == 0:
        return {"total": 0, "error": "empty_chains"}

    dist = {"high_quality": 0, "acceptable": 0, "low_quality": 0, "noise": 0}
    template_count = 0
    score_sum = 0

    # 每维统计
    dim_data = {}
    for chain, rating in zip(chains, ratings):
        tag = None
        for t in ("high_quality", "acceptable", "low_quality", "noise"):
            if t in rating["tags"]:
                tag = t
                break
        dist[tag or "noise"] = dist.get(tag or "noise", 0) + 1
        score_sum += rating["score"]

        if "template" in rating["tags"]:
            template_count += 1

        dim = chain.get("dimension", "?")
        if dim not in dim_data:
            dim_data[dim] = {"count": 0, "score_sum": 0, "noise_count": 0}
        dim_data[dim]["count"] += 1
        dim_data[dim]["score_sum"] += rating["score"]
        if rating["score"] < 0.30:
            dim_data[dim]["noise_count"] = dim_data[dim].get("noise_count", 0) + 1

    # 聚合每维
    per_dim = {}
    for dim, d in dim_data.items():
        per_dim[dim] = {
            "count": d["count"],
            "avg_score": round(d["score_sum"] / d["count"], 3),
            "noise_rate": round(d.get("noise_count", 0) / d["count"], 3) if d["count"] else 0,
        }

    return {
        "total": total,
        "distribution": dist,
        "avg_score": round(score_sum / total, 3),
        "template_rate": round(template_count / total, 3),
        "noise_rate": round(dist.get("noise", 0) / total, 3),
        "per_dimension": per_dim,
        "threshold_30_blocked": dist.get("noise", 0),
    }
