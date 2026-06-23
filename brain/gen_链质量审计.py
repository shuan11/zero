#!/usr/bin/env python3
"""
gen_链质量审计.py — P195: 链质量审计引擎

当链数/比值达标后, 质量>数量。
审计: 来源分布(gen_* vs 其他), 内容长度分布, 重复率, 维度分散度。
输出审计报告供其他模块参考。
"""
import json, os, sys, re
from collections import Counter
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_REPORT_FILE = CLUSTER / ".chain_quality_report.json"

def _get_chains():
    """从海马体获取全部链"""
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        return chains if isinstance(chains, list) else []
    except:
        hip_file = CLUSTER / "hippocampus_memory.json"
        if hip_file.exists():
            try:
                with open(hip_file) as f:
                    data = json.load(f)
                chains = data.get("causal_chains", data.get("chains", []))
                return chains if isinstance(chains, list) else []
            except:
                pass
    return []

def _audit(chains):
    """执行链质量审计"""
    total = len(chains)
    if total == 0:
        return {"status": "no_chains"}
    
    # 1.来源分布
    sources = Counter()
    for c in chains:
        src = c.get("source", c.get("src", "unknown"))
        if isinstance(src, str):
            sources[src] += 1
    
    gen_sources = {k: v for k, v in sources.items() if k.startswith("gen_")}
    other_sources = {k: v for k, v in sources.items() if not k.startswith("gen_")}
    
    # 2.维度分布
    dim_counter = Counter()
    dim_content_lens = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counter[d] += 1
        if d not in dim_content_lens:
            dim_content_lens[d] = []
        content = c.get("content", "")
        if content:
            dim_content_lens[d].append(len(content))
    
    # 3.内容长度分布(抽样)
    contents = [c.get("content", "") for c in chains if c.get("content")]
    avg_len = sum(len(s) for s in contents) / max(len(contents), 1)
    short = sum(1 for s in contents if len(s) < 20)
    
    # 4.重复率(前50字符)
    prefixes = {}
    dups = 0
    for c in chains:
        content = c.get("content", "")
        pref = content[:50] if content else ""
        if pref in prefixes:
            dups += 1
        else:
            prefixes[pref] = True
    
    # 5.平均strength
    strengths = [c.get("strength", 0.5) for c in chains if isinstance(c.get("strength"), (int, float))]
    avg_str = sum(strengths) / max(len(strengths), 1)
    
    # 6.有src/rel/dst的链比例
    with_src = sum(1 for c in chains if c.get("src"))
    with_rel = sum(1 for c in chains if c.get("rel"))
    with_dst = sum(1 for c in chains if c.get("dst"))
    
    report = {
        "total": total,
        "dimension_count": len(dim_counter),
        "sources": {
            "gen_total": sum(gen_sources.values()),
            "gen_pct": round(sum(gen_sources.values()) / total * 100, 1),
            "gen_detail": dict(gen_sources.most_common(20)),
            "other_pct": round(sum(other_sources.values()) / total * 100, 1),
            "other_detail": dict(other_sources.most_common(10))
        },
        "content_quality": {
            "avg_length": round(avg_len, 1),
            "short_chain_pct": round(short / total * 100, 1),
            "dup_prefix_pct": round(dups / total * 100, 1),
            "avg_strength": round(avg_str, 3),
            "has_src": f"{round(with_src/total*100,1)}%",
            "has_rel": f"{round(with_rel/total*100,1)}%",
            "has_dst": f"{round(with_dst/total*100,1)}%"
        },
        "dimension_stats": {
            "most": dim_counter.most_common(5),
            "least": dim_counter.most_common()[-5:] if len(dim_counter) >= 5 else list(dim_counter.most_common()),
            "balance_ratio": round(max(dim_counter.values()) / max(min(dim_counter.values()), 1), 1) if dim_counter else 0
        }
    }
    return report

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 3 != 0:  # 每3次才审计(降低IO)
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    chains = _get_chains()
    report = _audit(chains)
    
    # 保存到文件供仪表盘/其他模块使用
    report["pulse"] = _CALL_COUNT
    report["source_sort"] = sorted(
        report.get("sources", {}).get("gen_detail", {}).items(),
        key=lambda x: -x[1]
    )[:5]
    
    try:
        with open(_REPORT_FILE, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return report

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
