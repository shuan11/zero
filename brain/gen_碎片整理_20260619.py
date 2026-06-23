"""
维度碎片整理器 — 分析低频维度(<20链)是否可合并或提升
39维碎片化警告触发，系统维度过多弱维分散
"""
import json, sys, os
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def analyze_fragmentation():
    """分析39维碎片状态"""
    try:
        with open(CLUSTER / "hippocampus_memory.json") as f:
            data = json.load(f)
    except:
        return {"status":"no_data"}
    
    chains = data.get("causal_chains", [])
    dim_counts = {}
    for c in chains:
        d = c.get("dimension","未分类")
        dim_counts[d] = dim_counts.get(d,0) + 1
    
    # 分档
    weak_dims = [(d,c) for d,c in dim_counts.items() if c < 20]
    medium_dims = [(d,c) for d,c in dim_counts.items() if 20 <= c < 60]
    strong_dims = [(d,c) for d,c in dim_counts.items() if c >= 200]
    
    return {
        "total_chains": len(chains),
        "total_dims": len(dim_counts),
        "over_threshold": len(dim_counts) > 35,
        "weak_dims": sorted(weak_dims, key=lambda x:x[1]),
        "medium_dims": sorted(medium_dims, key=lambda x:x[1]),
        "strong_dims": sorted(strong_dims, key=lambda x:x[1], reverse=True),
    }

def suggest_merge(dim_counts=None):
    """建议可合并的同族维度"""
    families = {}
    merge_suggestions = []
    return merge_suggestions

if __name__ == "__main__":
    result = analyze_fragmentation()
    print(json.dumps(result, ensure_ascii=False))
    
    # 如果有弱维<20链, 输出建议
    if result.get("weak_dims"):
        print("\n=== 低链维度(<20链) ===")
        for d,c in result["weak_dims"]:
            print(f"  {d}: {c}链")
