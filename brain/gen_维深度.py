#!/usr/bin/env python3
"""
gen_维深度.py — P200: 维度层次探测引擎

每个维度内部, 按链的rel/src/content分析概念层次。
构建 root→branch→leaf 3级概念树, 输出到.concept_tree.json。
当维度链>200时探测深度, 否则跳过。
"""
import json, os, sys, re
from collections import defaultdict, Counter
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_DEPTH_FILE = CLUSTER / ".concept_tree.json"

# 概念层次关键词
ROOT_KW = ["系统", "整体", "本体", "核心", "根基", "本质", "本源", "原理", "规律", "宇宙"]
BRANCH_KW = ["结构", "机制", "方法", "模式", "过程", "关系", "功能", "类型", "层面", "维度"]
LEAF_KW = ["实例", "案例", "具体", "细节", "表现", "数据", "参数", "值", "指标", "结果"]

def _get_dim_chains():
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
                return data.get("causal_chains", data.get("chains", []))
            except:
                pass
    return []

def _classify_level(content, rel, src, dst):
    """将链分类到概念层次"""
    text = f"{content} {rel} {src} {dst}"
    
    root_score = sum(1 for kw in ROOT_KW if kw in text)
    branch_score = sum(1 for kw in BRANCH_KW if kw in text)
    leaf_score = sum(1 for kw in LEAF_KW if kw in text)
    
    if root_score >= branch_score and root_score >= leaf_score:
        return "root"
    elif branch_score >= leaf_score:
        return "branch"
    else:
        return "leaf"

def _extract_concepts(content, rel, src, dst):
    """提取链中的核心概念词"""
    text = f"{content} {rel} {src} {dst}"
    # 简单的概念提取: 取较长的词(2-6字)
    words = re.findall(r'[\u4e00-\u9fff]{2,6}', text)
    # 去停用词
    stop = {"系统", "维度", "能力", "知识", "自己", "认知", "时候", "方式", "过程", "通过"}
    return [w for w in words if w not in stop][:5]

def _build_tree(dim, chains):
    """为一个维度建概念树"""
    if len(chains) < 200:
        return {"status": "too_shallow", "count": len(chains), "tree": None}
    
    # 按层次分类
    levels = {"root": [], "branch": [], "leaf": []}
    concept_counts = Counter()
    
    for c in chains:
        content = c.get("content", "")
        rel = c.get("rel", "")
        src = c.get("src", "")
        dst = c.get("dst", "")
        
        level = _classify_level(content, rel, src, dst)
        levels[level].append(c)
        
        concepts = _extract_concepts(content, rel, src, dst)
        for w in concepts:
            concept_counts[w] += 1
    
    top_concepts = concept_counts.most_common(20)
    
    # 提取根概念(最常出现的)
    roots = [w for w, _ in top_concepts[:5]]
    
    # 分支概念
    branches = [w for w, _ in top_concepts[5:15]]
    
    tree = {
        "roots": roots,
        "branches": branches,
        "hierarchy": {
            "root_pct": round(len(levels["root"]) / len(chains) * 100, 1),
            "branch_pct": round(len(levels["branch"]) / len(chains) * 100, 1),
            "leaf_pct": round(len(levels["leaf"]) / len(chains) * 100, 1)
        },
        "diversity": len(concept_counts),
        "top_concepts": top_concepts[:15]
    }
    
    return {"status": "depth_ok", "count": len(chains), "tree": tree}

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 8 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    all_chains = _get_dim_chains()
    if not all_chains:
        return {"status": "no_chains"}
    
    # 收集每维的链
    dim_chains = defaultdict(list)
    for c in all_chains:
        if isinstance(c, dict):
            d = c.get("dimension", "未分类")
            dim_chains[d].append(c)
    
    # 为每维建树(≥200链)
    trees = {}
    for dim, chains in dim_chains.items():
        tree = _build_tree(dim, chains)
        if tree["status"] == "depth_ok":
            trees[dim] = tree
    
    result = {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "dimensions_scanned": len(dim_chains),
        "depth_built": list(trees.keys()),
        "depth_skipped": [d for d, c in dim_chains.items() if len(c) < 200],
        "trees": trees
    }
    
    try:
        with open(_DEPTH_FILE, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
