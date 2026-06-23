#!/usr/bin/env python3
"""
STEP 3: 对Top3关键节点用因果推理器explain()生成深度分析
"""
import json
import sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

from causal_reasoner import CausalReasoner

print("=" * 60)
print("  STEP 3: Top3关键节点深度因果分析")
print("=" * 60)

# Load analysis results
with open(CLUSTER / "causal_graph_analysis.json", 'r', encoding='utf-8') as f:
    analysis = json.load(f)

# Load reasoner
reasoner = CausalReasoner()
n, e, c = reasoner.load()
print(f"  推理器加载: {n}节点 / {e}边 / {c}因果链")

# Top3 关键节点 by in-degree (汇聚点 = 系统关键点)
top3_in = analysis["top10_in_degree"][:3]
print(f"\n{'=' * 60}")
print("  Top3 关键汇聚节点 (入度最高)")
print(f"{'=' * 60}")

explain_results = []
for rank, node_info in enumerate(top3_in, 1):
    nid = node_info["nid"]
    label = node_info["label"]
    deg = node_info["degree"]
    
    print(f"\n--- Top{rank}: [{nid}] in_degree={deg} ---")
    print(f"  Label: {label[:100]}")
    
    # Extract keywords from label for explain
    # Try multiple keyword strategies
    keywords_to_try = []
    
    # Strategy 1: Extract meaningful Chinese segments
    import re
    chinese_segments = re.findall(r'[\u4e00-\u9fff]{2,8}', label)
    keywords_to_try.extend(chinese_segments[:3])
    
    # Strategy 2: If it starts with [待推导], use the core question
    if "[待推导]" in label or "外部知识" in label:
        # Extract the question part
        q_match = re.search(r'"([^"]+)"', label)
        if q_match:
            keywords_to_try.append(q_match.group(1)[:30])
    
    # Strategy 3: use some common system concepts
    keywords_to_try.extend(["系统", "因果", "进化"])
    
    print(f"  尝试关键词: {keywords_to_try[:5]}")
    
    # Run explain for the most promising keyword
    best_explain = None
    for kw in keywords_to_try[:3]:
        result = reasoner.explain(kw)
        if result['matched_nodes'] > 0 or result['causal_chain_count'] > 0:
            if best_explain is None or result['causal_chain_count'] > best_explain.get('causal_chain_count', 0):
                best_explain = result
                best_explain['keyword_used'] = kw
    
    if best_explain:
        print(f"\n  关键词 '{best_explain.get('keyword_used', '?')}' 的因果解释:")
        print(f"  匹配节点: {best_explain['matched_nodes']}")
        print(f"  因果链数: {best_explain['causal_chain_count']}")
        print(f"  上游原因链: {len(best_explain['upstream_causes'])}")
        print(f"  下游效应链: {len(best_explain['downstream_effects'])}")
        
        if best_explain.get('explanation'):
            print(f"\n  完整解释:")
            for line in best_explain['explanation'].split('\n'):
                print(f"    {line}")
        
        if best_explain.get('related_chains'):
            print(f"\n  相关因果链:")
            for i, chain in enumerate(best_explain['related_chains'][:3]):
                print(f"    [{i+1}] cause: {chain['cause'][:80]}")
                print(f"        effect: {chain['effect'][:80]}")
                print(f"        confidence: {chain['confidence']}")
        
        explain_results.append({
            "rank": rank,
            "node_id": nid,
            "in_degree": deg,
            "label": label[:150],
            "keyword_used": best_explain.get('keyword_used', ''),
            "matched_nodes": best_explain['matched_nodes'],
            "causal_chain_count": best_explain['causal_chain_count'],
            "upstream_causes": best_explain.get('upstream_causes', [])[:3],
            "downstream_effects": best_explain.get('downstream_effects', [])[:3],
            "explanation": best_explain.get('explanation', ''),
            "related_chains": [
                {"cause": rc['cause'][:150], "effect": rc['effect'][:150], "confidence": rc['confidence']}
                for rc in best_explain.get('related_chains', [])[:3]
            ]
        })
    else:
        print(f"  未能匹配因果链")
        explain_results.append({
            "rank": rank,
            "node_id": nid,
            "in_degree": deg,
            "label": label[:150],
            "error": "no matching causal chains found"
        })

# Also analyze top out-degree nodes for completeness
top3_out = analysis["top10_out_degree"][:3]
print(f"\n{'=' * 60}")
print("  Top3 影响力源节点 (出度最高) — predict分析")
print(f"{'=' * 60}")

predict_results = []
for rank, node_info in enumerate(top3_out, 1):
    nid = node_info["nid"]
    label = node_info["label"]
    deg = node_info["degree"]
    
    print(f"\n--- Top{rank}: [{nid}] out_degree={deg} ---")
    print(f"  Label: {label[:100]}")
    
    import re
    # Extract meaningful keywords
    chinese_segments = re.findall(r'[\u4e00-\u9fff]{2,8}', label)
    keywords_to_try = chinese_segments[:3] + ["因果", "系统"]
    
    best_predict = None
    for kw in keywords_to_try[:3]:
        result = reasoner.predict(kw)
        if result['total_effects_found'] > 0:
            if best_predict is None or result['total_effects_found'] > best_predict.get('total_effects_found', 0):
                best_predict = result
                best_predict['keyword_used'] = kw
    
    if best_predict:
        print(f"  预测关键词: {best_predict.get('keyword_used', '?')}")
        print(f"  预测效应数: {best_predict['total_effects_found']}")
        for p in best_predict.get('predicted_effects', [])[:3]:
            print(f"    [{p['confidence']:.3f}] {p['predicted_effect'][:60]}")
            print(f"    路径: {p['path'][:100]}")
        
        predict_results.append({
            "rank": rank,
            "node_id": nid,
            "out_degree": deg,
            "label": label[:150],
            "keyword_used": best_predict.get('keyword_used', ''),
            "total_effects": best_predict['total_effects_found'],
            "top_effects": best_predict.get('predicted_effects', [])[:3]
        })

# Save all results
deep_analysis = {
    "top3_explain": explain_results,
    "top3_predict": predict_results,
    "graph_stats": {
        "nodes": n,
        "edges": e,
        "chains": c,
        "components": analysis["components"],
        "largest_component": analysis["largest_component_size"],
        "longest_path": analysis["longest_path_length"],
        "isolated_count": analysis["isolated_count"]
    }
}

deep_path = CLUSTER / "p0_deep_analysis_result.json"
with open(deep_path, 'w', encoding='utf-8') as f:
    json.dump(deep_analysis, f, ensure_ascii=False, indent=2)
print(f"\n[保存] 深度分析 → {deep_path}")

print(f"\n{'=' * 60}")
print("  STEP 3 完成")
print(f"{'=' * 60}")
