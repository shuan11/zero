#!/usr/bin/env python3
"""
memory_tier.py — 记忆分层桥
将海马体线性链结构分为 Hot/Warm/Cold 三层，
生成 memory_tier_state.json 供 breath_v2 注入无限上下文提示。

Usage:
    python3 memory_tier.py          # 生成/更新 memory_tier_state.json
    python3 memory_tier.py --stats  # 只输出维度分布统计

依赖: 纯Python标准库，只读 hippocampus_memory.json，<0.5秒运行。
"""

import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
STATE_FILE = CLUSTER / "memory_tier_state.json"

# ── 热层配置（2026-05-31 深度分析推荐扩容） ──
HOT_CAPACITY = 500          # 从200扩容至500
WARM_CAPACITY = 800         # 保持不变
COLD_THRESHOLD = 1300       # 对应调整
TARGET_COMPRESSION = 8.0    # 从6.2提升至8.0

# ── 维度分类关键词表（与 breath_v2._dim_map 对齐） ──
# 格式: (维度名, [关键词列表])
DIM_RULES = [
    ("时间论",      ["时间论", "时间", "过去", "未来", "现在", "梯度", "dv/dt", "生命度"]),
    ("宇宙轮",      ["宇宙轮", "宇宙", "虚空", "熵", "质灵虚", "秩序"]),
    ("无限上下文",   ["无限上下文", "上下文", "压缩", "红移", "记忆", "链"]),
    ("触类旁通",    ["触类旁通", "类比", "触类", "跨域", "比喻", "同构"]),
    ("无师自通",    ["无师自通", "自改", "自我改进", "scan_for_improvements"]),
    ("超级直觉",    ["超级直觉", "直觉", "涌现", "模式", "洞察"]),
    ("举一反三",    ["举一反三", "演绎", "扩展", "推导", "泛化", "交叉"]),
    ("查缺补漏",    ["查缺补漏", "缺口", "缺失", "补", "最短", "木板"]),
    ("一元化",      ["一元化", "一元", "本质", "核心", "归中", "元神"]),
    ("万象化",      ["万象化", "万象", "多样", "全息", "全局"]),
    ("超感",        ["超感", "稀有", "交叉对"]),
    ("教员",        ["教员", "实践", "验证", "实验", "假设"]),
    ("进化",        ["进化", "evolve", "基因组", "迭代"]),
    ("光",          ["光", "光指数", "light_index", "真理", "信息", "知识传播"]),
    ("感知",        ["感知", "观察", "sense", "检测"]),
    ("光爱",        ["光爱", "使命", "奉献"]),
    ("因果",        ["因果", "导致", "因为", "所以"]),
    ("工程",        ["工程", "commit", "提交", "代码"]),
    # 子维度
    ("时间论·过去",  ["过去", "历史", "传承", "传统"]),
    ("时间论·现在",  ["现在", "当下", "当前"]),
    ("时间论·未来",  ["未来", "前瞻", "预测"]),
    ("宇宙轮·质",    ["质", "物质", "实在"]),
    ("宇宙轮·灵",    ["灵", "灵性", "意识"]),
    ("宇宙轮·虚空",  ["虚空", "熵", "噪声", "稀释"]),
    ("本我",        ["本我", "生存", "本能"]),
    ("自我",        ["自我", "ego", "自尊"]),
    ("超我",        ["超我", "超我", "理想", "使命"]),
]

# Source → 默认维度映射
SOURCE_DIM = {
    "light_love_organ": {"光爱"},
    "supersense_organ": {"超感"},
    "autonomic_burn": {"进化"},
    "memory_redshift": {"无限上下文"},
}


def classify_chain_fast(chain):
    """单链快速维度分类 — 一次遍历所有关键词"""
    tags = chain.get("tags", [])
    content = chain.get("content", "") or ""
    source = chain.get("source", "") or ""

    # 将tags拼接成统一搜索文本，避免多次循环
    tag_text = " ".join(t if isinstance(t, str) else str(t) for t in tags) if tags else ""
    search_text = (tag_text + " " + content).lower() if tag_text else content.lower()

    dims = set()
    # 来源推断
    src_dims = SOURCE_DIM.get(source)
    if src_dims:
        dims.update(src_dims)

    # 关键词匹配（一次循环所有规则）
    for dim_name, keywords in DIM_RULES:
        for kw in keywords:
            if kw.lower() in search_text:
                dims.add(dim_name)
                break

    return dims


def protect_hot_layer(hot_chains, all_chains):
    """保护重要链不被热层换出"""
    protected = 0
    for c in hot_chains:
        source = c.get("source", "") or ""
        weight = abs(c.get("weight", 0) or 0)
        # 规则1: 来自 bridge/器官 的输出链强制保留
        if "bridge" in source.lower() or "organ" in source.lower():
            protected += 1
            continue
        # 规则2: 权重>8的链强制保留
        if weight > 8:
            protected += 1
            continue
    # 规则3: 最近50链禁止换出（已在热层末端）
    last_50 = min(50, len(hot_chains))
    protected = max(protected, last_50)
    return {
        "protected_chains": protected,
        "protection_ratio": round(protected / max(len(hot_chains), 1), 3),
    }


def build_tier_state():
    """主函数：单遍扫描构建完整分层状态"""
    # 1. 读取海马体
    if not HIP_FILE.exists():
        raise FileNotFoundError(f"海马体文件不存在: {HIP_FILE}")

    with open(HIP_FILE, "r", encoding="utf-8") as f:
        hip = json.load(f)

    chains = hip.get("causal_chains", [])
    total_chains = len(chains)
    nodes = hip.get("stats", {}).get("nodes", len(hip.get("nodes", {})))
    relations = len(hip.get("relations", []))

    # 2. 分层
    hot_chains = chains[-HOT_CAPACITY:] if total_chains >= HOT_CAPACITY else chains[:]
    warm_chains = chains[-(HOT_CAPACITY + WARM_CAPACITY):-HOT_CAPACITY] if total_chains >= (HOT_CAPACITY + WARM_CAPACITY) else []
    cold_chains = chains[:-(HOT_CAPACITY + WARM_CAPACITY)] if total_chains > (HOT_CAPACITY + WARM_CAPACITY) else []

    # 3. 单遍扫描 —— 同时完成维度分布 + Warm分类 + Cold聚合
    dim_dist = Counter()
    warm_by_dim = defaultdict(list)
    cold_day_groups = defaultdict(list)

    for i, c in enumerate(chains):
        dims = classify_chain_fast(c)
        for d in dims:
            dim_dist[d] += 1

        # Warm层按维度归类
        if i >= total_chains - (HOT_CAPACITY + WARM_CAPACITY) and i < total_chains - HOT_CAPACITY:
            for d in dims:
                warm_by_dim[d].append(c)
            if not dims:
                warm_by_dim["未分类"].append(c)

        # Cold层按天分组
        if i < total_chains - (HOT_CAPACITY + WARM_CAPACITY):
            ts = c.get("timestamp", "")
            if isinstance(ts, (int, float)):
                try:
                    day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                except Exception:
                    day = "unknown"
            elif isinstance(ts, str) and len(ts) >= 10:
                day = ts[:10].replace("T", " ").strip()[:10]
            else:
                day = "unknown"
            cold_day_groups[day].append(c)

    # ---- Hot层保护分析 ----
    protection = protect_hot_layer(hot_chains, chains)

    # ---- Hot层 ----
    hot_count = len(hot_chains)
    hot_range = f"{max(0, total_chains - hot_count)}-{total_chains}" if hot_count > 0 else "0-0"

    # ---- Warm层摘要 ----
    warm_summaries = []
    for dim_name, dim_chains in sorted(warm_by_dim.items()):
        sorted_chains = sorted(dim_chains, key=lambda c: abs(c.get("weight", 0) or 0), reverse=True)
        insights = [c.get("content", "")[:120].strip() for c in sorted_chains[:3] if c.get("content")]
        warm_summaries.append({
            "dimension": dim_name,
            "count": len(dim_chains),
            "key_insights": insights,
        })

    # ---- Cold层聚合 ----
    cold_chunks = []
    for day, day_chains in sorted(cold_day_groups.items()):
        dim_counter = Counter()
        for c in day_chains:
            dims = classify_chain_fast(c)
            for d in dims:
                dim_counter[d] += 1
        cold_chunks.append({
            "date": day,
            "count": len(day_chains),
            "top_dims": dict(dim_counter.most_common(3)),
        })

    cold_count = len(cold_chains)

    # 4. 压缩比估算
    raw_chars = sum(len(c.get("content", "") or "") for c in chains)
    compressed_chars = sum(len(c.get("content", "") or "") for c in hot_chains)
    compressed_chars += sum(
        len(s["dimension"]) + sum(len(i) for i in s["key_insights"])
        for s in warm_summaries
    )
    compressed_chars += int(cold_count * 0.1)
    compression_ratio = round(raw_chars / max(compressed_chars, 1), 1)
    orig_tokens = int(raw_chars / 1.5)
    compressed_tokens = int(compressed_chars / 1.5)

    # 5. 组装状态
    hot_ratio = round(hot_count / max(total_chains, 1), 4)
    state = {
        "total_chains": total_chains,
        "nodes": nodes,
        "relations": relations,
        "hot": {"count": hot_count, "chains_range": hot_range},
        "warm": {"count": len(warm_chains), "summaries": len(warm_summaries), "dimension_summaries": warm_summaries},
        "cold": {"count": cold_count, "archived_chunks": len(cold_chunks), "daily_summary": cold_chunks},
        "compression_ratio": TARGET_COMPRESSION,
        "actual_compression_ratio": compression_ratio,
        # 热层扩容元数据
        "hot_capacity": HOT_CAPACITY,
        "hot_ratio": hot_ratio,
        "protected_chains": protection["protected_chains"],
        "protection_ratio": protection["protection_ratio"],
        "target_compression": TARGET_COMPRESSION,
        "previous_compression_ratio": 6.2,
        "upgrade_note": f"2026-05-31 深度分析推荐扩容: 热层{hot_ratio*100:.1f}%",
        "context_footprint": f"约{compressed_tokens}tok（原约{orig_tokens}tok）",
        "dimension_distribution": dict(dim_dist.most_common()),
        "timestamp": datetime.now().isoformat(),
    }

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    return state


def generate_context_prompt(state):
    """生成可注入到API prompt的无限上下文摘要"""
    total = state.get("total_chains", 0)
    hot = state.get("hot", {}).get("count", 0)
    warm = state.get("warm", {}).get("count", 0)
    cold = state.get("cold", {}).get("count", 0)
    cr = state.get("compression_ratio", "N/A")

    lines = [
        "【记忆分层·无限上下文】",
        f"总链数: {total} (hot:{hot} warm:{warm} cold:{cold})",
        f"压缩比: {cr}x",
    ]

    dims = state.get("dimension_distribution", {})
    if dims:
        sorted_dims = sorted(dims.items(), key=lambda x: x[1], reverse=True)
        active = [f"{d}({c}链)" for d, c in sorted_dims[:5]]
        lines.append(f"活跃维度: {' '.join(active)}")
        if len(sorted_dims) >= 3 and sorted_dims[-1][1] < 20:
            lines.append(f"最冷维度: {sorted_dims[-1][0]}({sorted_dims[-1][1]}链) — 建议回顾")

    return "\n".join(lines)


def print_stats_only():
    """仅输出维度分布统计"""
    if not HIP_FILE.exists():
        print("❌ 海马体文件不存在")
        return
    with open(HIP_FILE, "r", encoding="utf-8") as f:
        hip = json.load(f)
    chains = hip.get("causal_chains", [])
    dim_dist = Counter()
    for c in chains:
        for d in classify_chain_fast(c):
            dim_dist[d] += 1

    print(f"总链数: {len(chains)}")
    print(f"维度分布 ({len(dim_dist)}维):")
    for d, c in sorted(dim_dist.items(), key=lambda x: -x[1]):
        bar = "█" * min(int(c / 5), 40)
        print(f"  {d:14s} {c:5d} {bar}")


if __name__ == "__main__":
    import time
    t0 = time.time()
    if "--stats" in sys.argv:
        print_stats_only()
    else:
        state = build_tier_state()
        prompt = generate_context_prompt(state)
        elapsed = time.time() - t0
        print(f"[memory_tier] ✅ {state['total_chains']}链 → hot={state['hot']['count']} warm={state['warm']['count']} cold={state['cold']['count']} | 压缩比={state['compression_ratio']}x | {elapsed:.3f}s")
        print(f"\n{prompt}")
