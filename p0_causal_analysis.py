#!/usr/bin/env python3
"""
P0 深度分析脚本 — 因果图结构级洞察
"""
import json
import sys
from pathlib import Path
from collections import defaultdict, deque

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

GRAPH_OUTPUT = CLUSTER / "causal_graph_output.json"

print("=" * 60)
print("  P0: 因果图深度结构分析")
print("=" * 60)

# Load graph
with open(GRAPH_OUTPUT, 'r', encoding='utf-8') as f:
    graph_data = json.load(f)

nodes = {n['id']: n for n in graph_data['nodes']}
edges = graph_data['edges']
meta = graph_data['meta']

print(f"\n[基础统计]")
print(f"  总节点: {meta['total_nodes']}")
print(f"  总边:   {meta['total_edges']}")
print(f"  总因果链: {meta['total_chains']}")

# Build adjacency
adj_out = defaultdict(list)
adj_in = defaultdict(list)
for i, e in enumerate(edges):
    adj_out[e['src']].append(i)
    adj_in[e['dst']].append(i)

# ── 2a: 入度最高的10个节点（系统关键汇聚节点）──
print(f"\n{'=' * 60}")
print("  2a: 入度最高Top10节点（被最多因果链指向=系统关键汇聚点）")
print(f"{'=' * 60}")
in_degree_list = [(nid, len(adj_in.get(nid, []))) for nid in nodes]
in_degree_list.sort(key=lambda x: -x[1])
top10_in = in_degree_list[:10]
for rank, (nid, deg) in enumerate(top10_in, 1):
    node = nodes[nid]
    label = node.get('label', '')[:80]
    tags = node.get('tags', [])
    print(f"  {rank}. [{nid}] in_degree={deg} | tags={tags[:3]}")
    print(f"     label: {label}")

# ── 2b: 出度最高的10个节点（系统影响力节点）──
print(f"\n{'=' * 60}")
print("  2b: 出度最高Top10节点（指向最多因果链=系统影响力源）")
print(f"{'=' * 60}")
out_degree_list = [(nid, len(adj_out.get(nid, []))) for nid in nodes]
out_degree_list.sort(key=lambda x: -x[1])
top10_out = out_degree_list[:10]
for rank, (nid, deg) in enumerate(top10_out, 1):
    node = nodes[nid]
    label = node.get('label', '')[:80]
    tags = node.get('tags', [])
    print(f"  {rank}. [{nid}] out_degree={deg} | tags={tags[:3]}")
    print(f"     label: {label}")

# ── 2c: 最长因果链路径（BFS from all roots）──
print(f"\n{'=' * 60}")
print("  2c: 最长因果传导链（从根节点出发的最长路径）")
print(f"{'=' * 60}")

# Find root nodes (in_degree = 0)
root_nodes = [nid for nid in nodes if len(adj_in.get(nid, [])) == 0]
print(f"  根节点数: {len(root_nodes)}")

# BFS from each root to find longest path
def bfs_longest_from(start_nid):
    """BFS to find longest path from start node"""
    dist = {start_nid: 0}
    parent = {start_nid: None}
    queue = deque([start_nid])
    farthest = start_nid
    
    while queue:
        current = queue.popleft()
        for eidx in adj_out.get(current, []):
            dst = edges[eidx]['dst']
            if dst not in dist:
                dist[dst] = dist[current] + 1
                parent[dst] = current
                queue.append(dst)
                if dist[dst] > dist[farthest]:
                    farthest = dst
    
    # Reconstruct path
    path = []
    node = farthest
    while node is not None:
        path.append(node)
        node = parent.get(node)
    path.reverse()
    return dist[farthest], path

# Sample top roots by out_degree to find longest chain
top_roots = sorted(root_nodes, key=lambda nid: len(adj_out.get(nid, [])), reverse=True)[:200]
longest_dist = 0
longest_path = []

for root in top_roots:
    dist, path = bfs_longest_from(root)
    if dist > longest_dist:
        longest_dist = dist
        longest_path = path

# Also try a few random roots
import random
random.seed(42)
random_roots = random.sample(root_nodes, min(300, len(root_nodes)))
for root in random_roots:
    dist, path = bfs_longest_from(root)
    if dist > longest_dist:
        longest_dist = dist
        longest_path = path

print(f"  最长路径长度: {longest_dist} 跳")
print(f"  路径节点数: {len(longest_path)}")
print(f"  最长因果传导链:")
for i, nid in enumerate(longest_path):
    node = nodes[nid]
    label = node.get('label', '')[:70]
    marker = "因" if i == 0 else ("果" if i == len(longest_path) - 1 else "中")
    print(f"    [{i}][{marker}] {nid}: {label}")

# ── 2d: 孤立节点 ──
print(f"\n{'=' * 60}")
print("  2d: 孤立节点分析（无入边无出边=可能噪声）")
print(f"{'=' * 60}")
isolated_nodes = []
for nid in nodes:
    out_d = len(adj_out.get(nid, []))
    in_d = len(adj_in.get(nid, []))
    if out_d == 0 and in_d == 0:
        isolated_nodes.append(nid)

print(f"  孤立节点数: {len(isolated_nodes)} / {len(nodes)} ({100*len(isolated_nodes)/len(nodes):.1f}%)")

# Show some isolated
if isolated_nodes:
    print(f"  前10个孤立节点:")
    for nid in isolated_nodes[:10]:
        node = nodes[nid]
        label = node.get('label', '')[:80]
        print(f"    [{nid}] {label}")

# Stats
no_in = sum(1 for nid in nodes if len(adj_in.get(nid, [])) == 0)
no_out = sum(1 for nid in nodes if len(adj_out.get(nid, [])) == 0)
print(f"\n  无入边节点数: {no_in} ({100*no_in/len(nodes):.1f}%)")
print(f"  无出边节点数: {no_out} ({100*no_out/len(nodes):.1f}%)")

# ── 额外: 度分布统计 ──
print(f"\n{'=' * 60}")
print("  度分布统计")
print(f"{'=' * 60}")
total_degrees = []
for nid in nodes:
    d = len(adj_out.get(nid, [])) + len(adj_in.get(nid, []))
    total_degrees.append(d)

total_degrees.sort(reverse=True)
print(f"  最大总度: {total_degrees[0]}")
print(f"  Top1%总度阈值: {total_degrees[max(0, len(total_degrees)//100)]}")
print(f"  中位数总度: {total_degrees[len(total_degrees)//2]}")
print(f"  平均总度: {sum(total_degrees)/len(total_degrees):.2f}")

# Tag distribution in high-degree nodes
print(f"\n  高度节点(总度>=3)的标签分布:")
tag_count = defaultdict(int)
high_deg_nodes = [(nid, len(adj_out.get(nid,[]))+len(adj_in.get(nid,[]))) for nid in nodes 
                  if len(adj_out.get(nid,[]))+len(adj_in.get(nid,[])) >= 3]
for nid, _ in high_deg_nodes:
    for t in nodes[nid].get('tags', []):
        tag_count[t] += 1
for tag, cnt in sorted(tag_count.items(), key=lambda x: -x[1])[:10]:
    print(f"    {tag}: {cnt}")

# ── Component analysis ──
print(f"\n{'=' * 60}")
print("  连通分量分析")
print(f"{'=' * 60}")
visited_all = set()
components = []
all_nids = set(nodes.keys())

for nid in all_nids:
    if nid in visited_all:
        continue
    # BFS to find component
    comp = set()
    q = deque([nid])
    comp.add(nid)
    visited_all.add(nid)
    while q:
        cur = q.popleft()
        for eidx in adj_out.get(cur, []):
            dst = edges[eidx]['dst']
            if dst not in comp:
                comp.add(dst)
                visited_all.add(dst)
                q.append(dst)
        for eidx in adj_in.get(cur, []):
            src = edges[eidx]['src']
            if src not in comp:
                comp.add(src)
                visited_all.add(src)
                q.append(src)
    components.append(comp)

components.sort(key=len, reverse=True)
print(f"  连通分量数: {len(components)}")
print(f"  最大分量节点数: {len(components[0])} ({100*len(components[0])/len(nodes):.1f}%)")
for i, comp in enumerate(components[:5]):
    print(f"  分量{i+1}: {len(comp)}节点")

# Save analysis results
analysis_result = {
    "top10_in_degree": [{"nid": nid, "degree": d, "label": nodes[nid].get("label","")[:100]} for nid, d in top10_in],
    "top10_out_degree": [{"nid": nid, "degree": d, "label": nodes[nid].get("label","")[:100]} for nid, d in top10_out],
    "longest_path_length": longest_dist,
    "longest_path_nodes": longest_path,
    "isolated_count": len(isolated_nodes),
    "isolated_pct": round(100*len(isolated_nodes)/len(nodes), 1),
    "root_count": len(root_nodes),
    "leaf_count": no_out,
    "components": len(components),
    "largest_component_size": len(components[0]),
    "largest_component_pct": round(100*len(components[0])/len(nodes), 1)
}

analysis_path = CLUSTER / "causal_graph_analysis.json"
with open(analysis_path, 'w', encoding='utf-8') as f:
    json.dump(analysis_result, f, ensure_ascii=False, indent=2)
print(f"\n[保存] 分析结果 → {analysis_path}")

print(f"\n{'=' * 60}")
print("  STEP 2 完成")
print(f"{'=' * 60}")
