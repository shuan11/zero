"""
gen_盲区分析_20260626.py — P109: 质量门盲区分析管道

职责:
  1. 读blocked_chains.json分析被拦截链模式
  2. 发现可能的新维萌芽或系统性噪声源
  3. 向原维注入提升链(若拦截率过高说明该维写入质量差)
  4. 输出分析报告

调用: daemon周期内调用 run_blind_spot_analysis()
"""

import os, sys, json, re
from pathlib import Path
from collections import Counter

# ─── 路径 ─────────────────────────────────────────────
CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
os.chdir(str(CLUSTER))

BLOCKED_LOG = CLUSTER / "blocked_chains.json"
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"


def _load_blocked():
    if BLOCKED_LOG.exists():
        try:
            with open(BLOCKED_LOG) as f:
                return json.load(f)
        except:
            return []
    return []


def _load_hip():
    if HIP_FILE.exists():
        try:
            with open(HIP_FILE) as f:
                data = json.load(f)
            chains = data.get("causal_chains", [])
            if isinstance(chains, list):
                return chains
            return []
        except:
            return []
    return []


def _count_by_dim(chains):
    """统计每维链数"""
    dims = Counter()
    for c in chains:
        dim = c.get("dimension", c.get("dst", "?"))
        dims[dim] += 1
    return dims


def _inject_boost_chain(dim, insight):
    """注入提升链到海马体"""
    from brain.share import write_chain
    chain = {
        "src": f"质量门·盲区分析",
        "rel": f"发现{dim}维系统性低质量",
        "dst": dim,
        "content": f"{dim}维被拦截链占比高,需提升写入质量",
        "insight": insight[:300],
        "dimension": dim,
        "tags": ["blind_spot_boost", "quality_gate"],
    }
    try:
        ret = write_chain(chain)
        if ret is not None:
            return True
        return False
    except Exception as e:
        print(f"  ⚠ 注入失败: {e}")
        return False


def run_blind_spot_analysis() -> dict:
    """盲区分析主函数

    Returns:
        {"report": str, "injected": N, "clusters": [...], "new_dim_candidates": [...]}
    """
    # ── 1. 读数据 ──
    blocked = _load_blocked()
    all_chains = _load_hip()

    if not blocked:
        return {"report": "无被拦截链记录,跳过分析", "injected": 0, "clusters": [], "new_dim_candidates": []}

    hip_dims = _count_by_dim(all_chains)
    total_hip = len(all_chains)

    # ── 2. 按rel聚合聚类 ──
    rel_counts = Counter()
    dim_counts = Counter()
    dim_score_sum = Counter()

    for e in blocked:
        c = e.get("chain", {})
        r = e.get("rating", {})
        rel = c.get("rel", "?")
        dim = c.get("dimension", c.get("dst", "?"))
        rel_counts[rel] += 1
        dim_counts[dim] += 1
        dim_score_sum[dim] += r.get("score", 0)

    # ── 3. 找高拦截率的维(该维平均分低且拦截多) ──
    high_block_dims = []
    for dim, cnt in dim_counts.most_common(20):
        avg_score = dim_score_sum[dim] / cnt if cnt else 0
        hip_cnt = hip_dims.get(dim, 0)
        # 如果一个维有≥5条拦截且平均分<0.25,说明该维写入质量差
        if cnt >= 5 and avg_score < 0.25:
            high_block_dims.append({
                "dimension": dim,
                "blocked_count": cnt,
                "avg_blocked_score": round(avg_score, 3),
                "hip_total": hip_cnt,
                "block_rate_hip": round(cnt / (cnt + hip_cnt + 1), 3),
            })

    # ── 4. 聚类分析(≥3同类rel视为模式) ──
    clusters = []
    for rel, cnt in rel_counts.most_common(10):
        if cnt >= 3:
            # 找该rel的sample content
            samples = []
            for e in blocked[:200]:
                if e.get("chain", {}).get("rel", "") == rel:
                    c = e["chain"]
                    samples.append(f"{c.get('src','')[:40]}→{c.get('dst','')[:40]}: {c.get('content','')[:80]}")
                    if len(samples) >= 3:
                        break
            clusters.append({
                "pattern": rel,
                "count": cnt,
                "rate": round(cnt / len(blocked), 3),
                "samples": samples,
            })

    # ── 5. 注入提升链 ──
    injected = 0
    for dim_info in high_block_dims:
        dim = dim_info["dimension"]
        insight = (f"盲区管道检测: {dim}维被拦截{dim_info['blocked_count']}条链"
                   f"(平均分{dim_info['avg_blocked_score']:.2f}),"
                   f"海马体总{dim_info['hip_total']}链。"
                   f"该维系统性产生低质量链,需降低模板生成/提升写入质量。")
        if _inject_boost_chain(dim, insight):
            injected += 1

    # ── 6. 新维候选 ──
    # 如果大量链的dimension="?" 或 "unknown" 且有共性rel
    unassigned = [e for e in blocked
                  if e.get("chain", {}).get("dimension", "") in ("?", "", "unknown", "未分类")]
    new_dim_candidates = []
    if len(unassigned) >= 5:
        # 分析这些链的rel共性
        unassigned_rels = Counter(e["chain"]["rel"] for e in unassigned if e.get("chain", {}).get("rel"))
        common_rel = unassigned_rels.most_common(3)
        if common_rel:
            new_dim_candidates.append({
                "trigger": f"{len(unassigned)}条未分类链被拦截",
                "common_rels": [pr for pr, pc in common_rel if pc >= 2],
                "suggestion": "考虑创建新维或分类这些链",
            })

    # ── 7. 报告 ──
    report_lines = [
        f"盲区分析: {len(blocked)}总拦截, {total_hip}海马体链",
        f"高拦截维({len(high_block_dims)}个): " + ",".join(d["dimension"][:10] for d in high_block_dims[:5]) if high_block_dims else "无",
        f"模式聚类({len(clusters)}个): " + ",".join(c["pattern"][:15] for c in clusters[:5]) if clusters else "无",
        f"新维候选: {len(new_dim_candidates)}",
        f"注入提升链: {injected}",
    ]
    report = "\n".join(report_lines)

    return {
        "report": report,
        "injected": injected,
        "clusters": clusters,
        "high_block_dims": high_block_dims,
        "new_dim_candidates": new_dim_candidates,
        "total_blocked": len(blocked),
        "total_hip": total_hip,
    }


if __name__ == "__main__":
    result = run_blind_spot_analysis()
    print(result["report"])
    if result.get("clusters"):
        print("\n── 模式聚类 ──")
        for c in result["clusters"][:5]:
            print(f"  [{c['count']}x] {c['pattern']}")
    if result.get("high_block_dims"):
        print("\n── 高拦截维 ──")
        for d in result["high_block_dims"][:5]:
            print(f"  {d['dimension']}: {d['blocked_count']}条(avg分{d['avg_blocked_score']:.2f})")
