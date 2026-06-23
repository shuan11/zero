#!/usr/bin/env python3
"""
time_past_bridge.py — 时间论·过去·历史传承桥
功能:
  1. 扫描 hippocampus_memory.json 全部链，做历史模式识别
  2. 生成传承连续性报告 time_past_state.json
  3. 为 breath_v2 提供定期回顾上下文
约束: <300行, 纯Python标准库, 只读不写 hippocampus, 运行<0.5秒
"""

import json, os, time, sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timezone

CLUSTER = Path(__file__).resolve().parent
HIPPO_FILE = CLUSTER / "hippocampus_memory.json"
STATE_FILE = CLUSTER / "time_past_state.json"

# ─── 传承关键词谱系 ─────────────────────────────────────
HERITAGE_TAGS = {'启示录','历史','历史传承','传承','过去','时间论','教训','反思',
                 'Gen','世代','回忆','根源','传统','回顾','复盘'}
# 不区分大小写的后缀匹配
HERITAGE_SUFFIXES = ['启示','历史','传承','过去','时间论','教训','反思','gen','世代','根源']


def load_hippo():
    with open(HIPPO_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def is_heritage_tag(tag):
    """判断是否为传承相关标签"""
    if tag in HERITAGE_TAGS:
        return True
    tl = tag.lower()
    return any(s in tl for s in HERITAGE_SUFFIXES)


def analyze_patterns(hippo):
    """功能1: 历史模式识别"""
    chains = hippo.get('causal_chains', [])
    total = len(chains)

    # ── 维度/标签统计 ──
    dim_counter = Counter()
    tag_counter = Counter()
    tag_sequence = defaultdict(list)  # tag -> [chain_index, ...]

    for i, c in enumerate(chains):
        dim_counter[c.get('dimension', '?')] += 1
        for tag in c.get('tags', []):
            tag_counter[tag] += 1
            tag_sequence[tag].append(i)

    # ── 重复模式 (传承标签聚类) ──
    recurring_patterns = []
    mid = total // 2
    for tag, count in tag_counter.most_common(30):
        if not is_heritage_tag(tag):
            continue
        seq = tag_sequence.get(tag, [])
        first_half = sum(1 for i in seq if i < mid)
        second_half = sum(1 for i in seq if i >= mid)
        if first_half == 0 and second_half == 0:
            trend = "稳定"
        elif first_half == 0:
            trend = "上升"
        elif second_half == 0:
            trend = "下降"
        else:
            r = second_half / first_half
            trend = "上升" if r > 1.2 else ("下降" if r < 0.8 else "稳定")
        recurring_patterns.append({"pattern": tag, "count": count, "trend": trend})

    recurring_patterns.sort(key=lambda x: x['count'], reverse=True)

    # ── 遗忘洞察: 早期独特内容 vs 近期 ──
    forgotten_insights = []
    if total > 20:
        early_idx = max(1, total // 10)          # 最早的10%
        late_idx = total - max(1, total // 10)   # 最晚的10%
        early_chains = chains[:early_idx]
        late_chains = chains[late_idx:]

        # 提取早期关键词集
        early_sets = []
        for c in early_chains:
            words = set(w for w in c.get('content', '').split() if len(w) > 2)
            early_sets.append((c, words))

        # 提取近期关键词集
        late_words = set()
        for c in late_chains:
            late_words.update(w for w in c.get('content', '').split() if len(w) > 2)

        # 找早期中有但近期没有的关键词
        for c, wset in early_sets:
            unique = wset - late_words
            if len(unique) >= 5:  # 至少有5个独特关键词
                last_idx = chains.index(c)
                gap = total - 1 - last_idx
                if gap > 100:  # 超过100链未出现
                    dim = c.get('dimension', '?')
                    insight = c.get('content', '')[:100]
                    forgotten_insights.append({
                        "insight": insight,
                        "last_seen": f"{gap}个链前",
                        "dimension": dim,
                        "unique_keywords": list(unique)[:8]
                    })

    # 去重 (内容前30字符去重)
    seen = set()
    deduped = []
    for fi in forgotten_insights:
        key = fi['insight'][:30]
        if key not in seen:
            seen.add(key)
            deduped.append(fi)
    forgotten_insights = deduped[:8]

    # ── 传承断裂点 ──
    breaking_points = []
    for tag, seq in tag_sequence.items():
        if not is_heritage_tag(tag):
            continue
        if len(seq) < 3:
            continue
        gaps = []
        for i in range(1, len(seq)):
            gap = seq[i] - seq[i-1] - 1
            if gap > 10:
                gaps.append(gap)
        if gaps:
            breaking_points.append({
                "pattern": tag,
                "max_break_gap": max(gaps),
                "total_occurrences": len(seq),
                "average_gap": round(sum(seq[i]-seq[i-1]-1 for i in range(1,len(seq))) / max(1, len(seq)-1), 1),
            })
    breaking_points.sort(key=lambda x: x['max_break_gap'], reverse=True)

    # ── 最连续传承维度 (排除未知) ──
    meaningful_dims = {k: v for k, v in dim_counter.items() if k not in ('?', 'unknown', '')}
    if meaningful_dims:
        most_continuous_dim = max(meaningful_dims.items(), key=lambda x: x[1])
    else:
        most_continuous_dim = ("N/A", 0)

    return {
        'total_chains': total,
        'dim_counter': dim_counter,
        'most_continuous_dim': most_continuous_dim[0],
        'most_continuous_count': most_continuous_dim[1],
        'recurring_patterns': recurring_patterns,
        'forgotten_insights': forgotten_insights,
        'breaking_points': breaking_points,
        'oldest_timestamp': chains[0].get('timestamp', 0) if chains else 0,
        'newest_timestamp': chains[-1].get('timestamp', 0) if chains else 0,
    }


def detect_fractures(chains):
    """检测所有维度的传承断裂链间隔"""
    dim_sequences = defaultdict(list)
    for i, c in enumerate(chains):
        dim = c.get("dimension", "?")
        dim_sequences[dim].append(i)

    fractures = []
    total_fracture_span = 0
    max_fracture = 0

    for dim, indices in dim_sequences.items():
        if len(indices) < 2:
            continue
        indices.sort()
        max_gap = 0
        dim_fracture_span = 0
        for j in range(1, len(indices)):
            gap = indices[j] - indices[j - 1] - 1
            if gap > 20:
                dim_fracture_span += gap
            if gap > max_gap:
                max_gap = gap

        if max_gap > max_fracture:
            max_fracture = max_gap
        total_fracture_span += dim_fracture_span

        if max_gap > 20:
            fractures.append({
                "dimension": dim,
                "max_gap": max_gap,
                "chain_count": len(indices),
                "fracture_span": dim_fracture_span,
            })

    fractures.sort(key=lambda x: x["max_gap"], reverse=True)
    return {
        "max_fracture": max_fracture,
        "fracture_risk_dimensions": [f["dimension"] for f in fractures],
        "fracture_details": fractures,
        "total_fracture_span": total_fracture_span,
    }


def compute_heritage_continuity(analysis, fracture_data=None):
    """计算传承连续性分数 (0~1) — 基于断裂间隔"""
    chains = analysis['total_chains']
    if chains == 0:
        return 0.0

    total_fracture_span = fracture_data.get("total_fracture_span", 0) if fracture_data else 0
    continuity = 1.0 - (total_fracture_span / chains)

    # 同时保留 continuity_target 和 gap 供输出
    continuity = min(1.0, max(0.0, continuity))
    return round(continuity, 4)


def generate_suggestions(analysis, continuity):
    """根据分析生成建议"""
    s = []
    if continuity < 0.65:
        s.append("传承连续性偏低，建议增加历史反思回合")
    if analysis['forgotten_insights']:
        dims = set(f['dimension'] for f in analysis['forgotten_insights'][:5] if f['dimension'] not in ('?', 'unknown', ''))
        if dims:
            s.append(f"发现{len(analysis['forgotten_insights'])}条遗忘洞察,建议回看{dims}维早期链")
    bp = analysis['breaking_points']
    if bp:
        worst = bp[0]
        s.append(f"传承断裂:{worst['pattern']}标签最大间隔{worst['max_break_gap']}链,需加强该维度连续思考")
    patterns = analysis['recurring_patterns']
    if patterns and patterns[0]['count'] > 100:
        s.append(f"最频繁传承模式:{patterns[0]['pattern']}({patterns[0]['count']}次,{patterns[0]['trend']})")
    return s if s else ["传承体系良好,建议维持历史回顾节奏"]


def generate_backfill(hippo, fracture_details):
    """Generate backfill content for fractured dimensions — 回溯填充"""
    chains = hippo.get("causal_chains", [])
    backfill = []
    for fd in fracture_details:
        dim = fd["dimension"]
        gap = fd["max_gap"]
        # Find chains containing this dimension
        dim_chains = []
        for c in chains:
            content = str(c.get("content", ""))
            tags = str(c.get("tags", []))
            cdim = str(c.get("dimension", ""))
            if dim in content or dim in tags or dim == cdim:
                dim_chains.append(c)
        if not dim_chains:
            continue
        # Get earliest 3 chains for sampling
        earliest = dim_chains[:3]
        summaries = []
        keywords = set()
        for c in earliest:
            ctext = str(c.get("content", ""))
            summaries.append(ctext[:80])
            words = ctext.split()
            keywords.update(w for w in words if len(w) > 2)
        # Get latest chain
        latest = dim_chains[-1] if dim_chains else None
        latest_content = str(latest.get("content", ""))[:80] if latest else ""
        # Build summary and prompt
        summary_parts = summaries[:2]
        summary = (
            f"{dim}维度已{gap}链未提及。"
            f"历史{dim}链共{len(dim_chains)}条，"
            f"核心内容涉及：{'；'.join(summary_parts)}"
        )
        prompt = (
            f"请思考{dim}与当前关注维度的联系："
            f"{dim}核心公式=合作是爱的底层逻辑。"
            f"当前系统状态与{dim}终极的差距"
        )
        backfill.append({
            "dimension": dim,
            "gap": gap,
            "total_chains": len(dim_chains),
            "summary": summary,
            "earliest_samples": summaries,
            "latest_content": latest_content,
            "keywords": list(keywords)[:15],
            "prompt": prompt,
        })
    return backfill


def generate_review_context(state):
    """功能3: 生成回顾上下文"""
    lines = [f"【时间论·过去·传承】总链{state['total_chains']}, "
             f"最长连续传承{state.get('most_continuous_dim','?')}({state.get('most_continuous_count',0)}链)"]
    patterns = state.get('recurring_patterns', [])
    if patterns:
        lines.append("重复模式: " + ' '.join(
            f"{p['pattern']}({p['count']}次,{p['trend']})" for p in patterns[:5]))
    forgotten = state.get('forgotten_insights', [])
    if forgotten:
        dims = set(f['dimension'] for f in forgotten[:3] if f['dimension'] not in ('?', 'unknown', ''))
        if dims:
            lines.append(f"遗忘洞察:{len(forgotten)}条已{forgotten[0]['last_seen']}未提及({','.join(dims)})")
        else:
            lines.append(f"遗忘洞察:{len(forgotten)}条已{forgotten[0]['last_seen']}未提及")
    bp = state.get('breaking_points', [])
    if bp:
        lines.append("传承断裂:" + '; '.join(
            f"{b['pattern']}间隔{b['max_break_gap']}链" for b in bp[:3]))
    lines.append(f"传承连续性={state.get('heritage_continuity',0):.2f}")
    return '\n'.join(lines)


def generate_report():
    """主流程"""
    t0 = time.time()
    hippo = load_hippo()
    chains = hippo.get('causal_chains', [])
    analysis = analyze_patterns(hippo)

    # 断裂检测
    fracture_data = detect_fractures(chains)
    continuity = compute_heritage_continuity(analysis, fracture_data)
    suggestions = generate_suggestions(analysis, continuity)

    # 生成 auto_repair_suggestions
    auto_repair = []
    for f in fracture_data.get("fracture_details", [])[:5]:
        dim = f["dimension"]
        gap = f["max_gap"]
        count = f["chain_count"]
        # 从 cold 层建议回溯历史链数
        backfill = min(3, max(1, gap // 20))
        auto_repair.append(
            f"维度{dim}间隔{gap}链: 建议从Cold层回溯{backfill}条历史链"
        )

    # 生成回溯填充
    backfill_data = generate_backfill(hippo, fracture_data.get("fracture_details", [])[:5])

    oldest_dt = datetime.fromtimestamp(analysis['oldest_timestamp'], tz=timezone.utc).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    continuity_target = 0.85
    continuity_gap = round(max(0.0, continuity_target - continuity), 4)

    state = {
        "total_chains": analysis['total_chains'],
        "oldest_chain_age": oldest_dt,
        "most_continuous_dim": analysis['most_continuous_dim'],
        "most_continuous_count": analysis['most_continuous_count'],
        "recurring_patterns": analysis['recurring_patterns'][:8],
        "forgotten_insights": analysis['forgotten_insights'][:5],
        "breaking_points": analysis['breaking_points'][:5],
        "heritage_continuity": continuity,
        # 断裂检测元数据
        "max_fracture": fracture_data["max_fracture"],
        "fracture_risk_dimensions": fracture_data["fracture_risk_dimensions"],
        "fracture_details": fracture_data["fracture_details"][:5],
        "continuity_target": continuity_target,
        "continuity_gap": continuity_gap,
        "total_fracture_span": fracture_data["total_fracture_span"],
        "auto_repair_suggestions": auto_repair,
        "backfill": backfill_data,
        "suggestions": suggestions,
        "timestamp": now_iso,
    }

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
    ctx = generate_review_context(state)
    elapsed = time.time() - t0
    print(ctx)
    print(f"\n[time_past_bridge] heritage_continuity={continuity:.4f} max_fracture={fracture_data['max_fracture']} ({elapsed*1000:.1f}ms)", file=sys.stderr)
    return state


if __name__ == '__main__':
    generate_report()
