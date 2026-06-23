#!/usr/bin/env python3
"""
gen_模式识别.py — P196: 跨维模式识别引擎

系统下23维已收敛(259-317差59)。模式识别在不同维度间
发现结构相似的链模式(相同rel/相似src结构),建立跨维映射。
输出: .pattern_map.json 供其他模块消费。
"""
import json, os, sys, re, random
from collections import defaultdict
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_PATTERN_FILE = CLUSTER / ".pattern_map.json"

# 关系分类模式
REL_PATTERNS = {
    "因果": ["导致", "引发", "产生", "造成", "驱动", "触发", "推动"],
    "关联": ["关联", "连接", "结合", "耦合", "交织", "并行", "对应"],
    "层次": ["包含", "属于", "分层", "构成", "组成", "结构", "组织"],
    "进化": ["进化", "深化", "升级", "发展", "生长", "演变", "扩展"],
    "映射": ["映射", "反映", "体现", "代表", "象征", "表达", "展现"],
    "控制": ["调节", "控制", "管理", "约束", "限制", "引导", "协调"],
    "反馈": ["反馈", "循环", "自指", "递归", "闭环", "反射", "自反"],
}

def _get_dim_chains_dict(limit=1000):
    """获取维度→链映射"""
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
    except:
        hip_file = CLUSTER / "hippocampus_memory.json"
        if not hip_file.exists():
            return {}
        try:
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
        except:
            return {}
    
    if not isinstance(chains, list):
        return {}
    
    dim_chains = defaultdict(list)
    for c in chains[:limit]:
        if isinstance(c, dict):
            d = c.get("dimension")
            if d:
                dim_chains[d].append(c)
    return dict(dim_chains)

def _classify_rel(rel):
    """分类关系类型"""
    if not rel:
        return "未知"
    for pattern, keywords in REL_PATTERNS.items():
        for kw in keywords:
            if kw in rel:
                return pattern
    return rel[:4]

def _find_patterns(dim_chains):
    """找跨维模式: 同rel分类的链在不同维度间分布"""
    dims = list(dim_chains.keys())
    
    # 统计: 各模式在各维度的数量
    pattern_dim_count = defaultdict(lambda: defaultdict(int))
    dim_total = {}
    
    for dim, chains in dim_chains.items():
        dim_total[dim] = len(chains)
        for c in chains:
            rel = c.get("rel", "")
            pc = _classify_rel(rel)
            pattern_dim_count[pc][dim] += 1
    
    # 找跨维模式: 出现在最多维度的模式
    pattern_spread = {}
    for pat, dims_dict in pattern_dim_count.items():
        appears_in = len(dims_dict)
        total_count = sum(dims_dict.values())
        # 在各维度的分布
        dim_dist = sorted(dims_dict.items(), key=lambda x: -x[1])[:10]
        pattern_spread[pat] = {
            "dim_count": appears_in,
            "total": total_count,
            "top_dims": dim_dist
        }
    
    # 排序: 按覆盖维度数
    sorted_patterns = sorted(
        pattern_spread.items(),
        key=lambda x: -x[1]["dim_count"]
    )
    
    # 识别最强的跨维模式
    cross_dim_patterns = []
    for pat, info in sorted_patterns[:10]:
        if info["dim_count"] >= 3:  # 至少出现在3维
            cross_dim_patterns.append({
                "pattern": pat,
                "dim_count": info["dim_count"],
                "total": info["total"],
                "top_dims": info["top_dims"][:5]
            })
    
    return {
        "patterns": sorted_patterns[:15],
        "cross_dim": cross_dim_patterns,
        "dim_count": len(dims),
        "pattern_count": len(pattern_spread)
    }

def _find_structural_similarity(dim_chains):
    """找结构相似的维度对: 相同rel占比高的维度对"""
    dims = list(dim_chains.keys())
    
    # 计算每维的关系分布
    dim_rel_dist = {}
    for dim, chains in dim_chains.items():
        rels = defaultdict(int)
        for c in chains:
            r = c.get("rel", "")
            if r:
                rels[r] += 1
        dim_rel_dist[dim] = dict(rels)
    
    # 计算Jaccard相似度
    pairs = []
    for i in range(len(dims)):
        for j in range(i+1, len(dims)):
            da, db = dims[i], dims[j]
            set_a = set(dim_rel_dist.get(da, {}).keys())
            set_b = set(dim_rel_dist.get(db, {}).keys())
            if not set_a or not set_b:
                continue
            intersection = set_a & set_b
            union = set_a | set_b
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard > 0.3:  # 高相似度
                pairs.append({
                    "dim_a": da,
                    "dim_b": db,
                    "jaccard": round(jaccard, 3),
                    "common_rels": list(intersection)[:10]
                })
    
    return sorted(pairs, key=lambda x: -x["jaccard"])[:20]

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 4 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    dim_chains = _get_dim_chains_dict()
    if not dim_chains:
        return {"status": "no_data"}
    
    patterns = _find_patterns(dim_chains)
    sim_pairs = _find_structural_similarity(dim_chains)
    
    result = {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "patterns": patterns,
        "similar_pairs": sim_pairs[:10]
    }
    
    try:
        with open(_PATTERN_FILE, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
