#!/usr/bin/env python3
"""
因果图构建 — v10.83
从海马体 causal_chains 中读取所有含因果语义的链，构建可查询的知识图谱。

功能:
  - load_graph(): 从海马体读取所有含 cause+effect 的因果链
  - build_graph(): 解析因果对，构建有向图(cause→effect)
  - query(关键词): 从图中查找与关键词相关的所有因果链
  - export(): 输出JSON格式的因果图
  - visualize(): 输出文本格式的因果图(树形/图)

生成时间: 2026-05-26
"""

import json
import re
import os
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
HIP_PATH = CLUSTER / "hippocampus_memory.json"
GRAPH_OUTPUT = CLUSTER / "causal_graph_output.json"

BJT = timezone(timedelta(hours=8))


class CausalKnowledgeGraph:
    """因果知识图谱 — 从海马体因果链构建的有向图"""

    def __init__(self):
        self.nodes = {}          # node_id -> {label, tags, chain_ids, count}
        self.edges = []          # [{src, dst, weight, chain_ids, confidence}]
        self.node_index = {}     # label -> node_id (用于去重)
        self.chain_data = []     # 原始因果链
        self.adj_out = defaultdict(list)  # node_id -> [edge_indices]
        self.adj_in = defaultdict(list)   # node_id -> [edge_indices]

    def load_graph(self, hip_path=None):
        """从海马体读取所有因果链 — 支持 content 格式和 cause/effect 格式"""
        path = hip_path or HIP_PATH
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        chains = data.get("causal_chains", [])
        self.chain_data = []
        
        for c in chains:
            if c.get("cause") and c.get("effect"):
                # 原生 cause/effect 格式
                self.chain_data.append(c)
            elif c.get("content"):
                # content 格式 — 解析 "cause → effect"
                content = str(c["content"]).strip()
                if " → " in content:
                    parts = content.split(" → ", 1)
                    cause_text = parts[0].strip()
                    effect_text = parts[1].strip()
                else:
                    # 没有分隔符,整条作为cause, effect为空摘要
                    cause_text = content
                    effect_text = f"[待推导] {content[:50]}"
                
                # 只保留有效因果对(cause至少10字)
                if len(cause_text) >= 10:
                    self.chain_data.append({
                        "id": c.get("id", f"chain-{len(self.chain_data)}"),
                        "cause": cause_text,
                        "effect": effect_text,
                        "confidence": c.get("confidence", 0.8),
                        "tags": c.get("tags", []),
                        "timestamp": c.get("timestamp", ""),
                        "source": c.get("source", "")
                    })
        
        print(f"[load_graph] 海马体总链: {len(chains)}, 有效因果链: {len(self.chain_data)}")

        # 按标签分类统计
        tag_stats = defaultdict(int)
        for c in self.chain_data:
            for t in c.get("tags", []):
                tag_stats[t] += 1
        top_tags = sorted(tag_stats.items(), key=lambda x: -x[1])[:10]
        print(f"[load_graph] Top10标签: {top_tags}")

        return self.chain_data

    def _normalize_text(self, text):
        """规范化文本用于去重/索引"""
        text = text.strip()
        # 移除常见前缀标记
        text = re.sub(r'^\[因果提取v2?\]\s*', '', text)
        text = re.sub(r'^\[光\](提问|收获|外部世界).*?:\s*', '', text)
        text = re.sub(r'^\[爱\](提问|收获|外部世界).*?:\s*', '', text)
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _extract_keywords(self, text):
        """从文本中提取关键词（2-8字的中文词组）"""
        keywords = set()
        # 中文词组
        for m in re.finditer(r'[\u4e00-\u9fff]{2,12}', text):
            keywords.add(m.group())
        # 英文词
        for m in re.finditer(r'[a-zA-Z_]{3,20}', text):
            keywords.add(m.group().lower())
        return keywords

    def _find_or_create_node(self, label):
        """查找或创建节点，返回node_id"""
        norm = self._normalize_text(label)
        # 截断长文本作为标签
        short = norm[:120] if len(norm) > 120 else norm

        if short in self.node_index:
            node_id = self.node_index[short]
            self.nodes[node_id]["count"] += 1
            return node_id

        node_id = f"n-{len(self.nodes)}"
        self.node_index[short] = node_id
        self.nodes[node_id] = {
            "id": node_id,
            "label": short,
            "keywords": list(self._extract_keywords(short)),
            "chain_ids": [],
            "count": 1
        }
        return node_id

    def build_graph(self):
        """解析因果对，构建有向图(cause→effect)"""
        for chain in self.chain_data:
            cause_text = chain["cause"]
            effect_text = chain["effect"]
            chain_id = chain.get("id", "")
            confidence = chain.get("confidence", 0.8)
            tags = chain.get("tags", [])

            # 创建/查找节点
            cause_node = self._find_or_create_node(cause_text)
            effect_node = self._find_or_create_node(effect_text)

            # 记录链ID到节点
            self.nodes[cause_node]["chain_ids"].append(chain_id)
            self.nodes[effect_node]["chain_ids"].append(chain_id)
            if tags:
                for t in tags:
                    if t not in self.nodes[cause_node].get("tags", []):
                        self.nodes[cause_node].setdefault("tags", []).append(t)
                    if t not in self.nodes[effect_node].get("tags", []):
                        self.nodes[effect_node].setdefault("tags", []).append(t)

            # 添加边
            edge_idx = len(self.edges)
            self.edges.append({
                "src": cause_node,
                "dst": effect_node,
                "weight": confidence,
                "chain_ids": [chain_id],
                "confidence": confidence
            })
            self.adj_out[cause_node].append(edge_idx)
            self.adj_in[effect_node].append(edge_idx)

        # 合并平行边（相同src→dst的边）
        self._merge_parallel_edges()

        n_nodes = len(self.nodes)
        n_edges = len(self.edges)
        print(f"[build_graph] 节点数: {n_nodes}, 边数: {n_edges}")
        # 统计入度出度
        out_degrees = {nid: len(self.adj_out.get(nid, [])) for nid in self.nodes}
        in_degrees = {nid: len(self.adj_in.get(nid, [])) for nid in self.nodes}
        max_out = max(out_degrees.values()) if out_degrees else 0
        max_in = max(in_degrees.values()) if in_degrees else 0
        print(f"[build_graph] 最大出度: {max_out}, 最大入度: {max_in}")
        return n_nodes, n_edges

    def _merge_parallel_edges(self):
        """合并同一src→dst的平行边"""
        edge_map = {}  # (src,dst) -> edge_idx
        new_edges = []
        for e in self.edges:
            key = (e["src"], e["dst"])
            if key in edge_map:
                # 合并到已有边
                idx = edge_map[key]
                new_edges[idx]["weight"] = max(new_edges[idx]["weight"], e["weight"])
                new_edges[idx]["chain_ids"].extend(e["chain_ids"])
                new_edges[idx]["confidence"] = max(new_edges[idx]["confidence"], e["confidence"])
            else:
                edge_map[key] = len(new_edges)
                new_edges.append(e)

        if len(new_edges) < len(self.edges):
            self.edges = new_edges
            # 重建邻接表
            self.adj_out = defaultdict(list)
            self.adj_in = defaultdict(list)
            for i, e in enumerate(self.edges):
                self.adj_out[e["src"]].append(i)
                self.adj_in[e["dst"]].append(i)
            print(f"[build_graph] 合并平行边: {len(self.edges)} (原{len(new_edges)})")

    def query(self, keyword):
        """
        从图中查找与关键词相关的所有因果链。
        返回: {causes: [...], effects: [...], paths: [...]}
        """
        keyword_lower = keyword.lower()
        results = {
            "keyword": keyword,
            "as_cause": [],   # 该关键词作为原因的节点
            "as_effect": [],  # 该关键词作为结果的节点
            "related_chains": []  # 相关因果链
        }

        # 搜索匹配的节点
        matching_nodes = []
        for nid, node in self.nodes.items():
            label = node["label"].lower()
            kws = [k.lower() for k in node.get("keywords", [])]
            if keyword_lower in label or keyword_lower in kws:
                matching_nodes.append(nid)

        results["matching_node_count"] = len(matching_nodes)

        # 对每个匹配节点，找上下游
        visited_chains = set()
        for nid in matching_nodes:
            # 作为原因: 找出度
            for eidx in self.adj_out.get(nid, []):
                edge = self.edges[eidx]
                dst_node = self.nodes[edge["dst"]]
                for cid in edge["chain_ids"]:
                    if cid not in visited_chains:
                        visited_chains.add(cid)
                        # 找原始链数据
                        for c in self.chain_data:
                            if c["id"] == cid:
                                results["as_cause"].append({
                                    "cause": c["cause"][:200],
                                    "effect": c["effect"][:200],
                                    "confidence": c.get("confidence", 0.8),
                                    "tags": c.get("tags", [])
                                })
                                break

            # 作为结果: 找入度
            for eidx in self.adj_in.get(nid, []):
                edge = self.edges[eidx]
                src_node = self.nodes[edge["src"]]
                for cid in edge["chain_ids"]:
                    if cid not in visited_chains:
                        visited_chains.add(cid)
                        for c in self.chain_data:
                            if c["id"] == cid:
                                results["as_effect"].append({
                                    "cause": c["cause"][:200],
                                    "effect": c["effect"][:200],
                                    "confidence": c.get("confidence", 0.8),
                                    "tags": c.get("tags", [])
                                })
                                break

        # 统计
        results["total_related_chains"] = len(visited_chains)
        return results

    def export(self, output_path=None):
        """输出JSON格式的因果图"""
        graph_data = {
            "meta": {
                "version": "v10.83",
                "created_at": datetime.now(BJT).isoformat(),
                "total_chains": len(self.chain_data),
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges)
            },
            "nodes": [
                {
                    "id": nid,
                    "label": n["label"][:200],
                    "keywords": n.get("keywords", []),
                    "tags": n.get("tags", []),
                    "chain_count": len(n.get("chain_ids", [])),
                    "out_degree": len(self.adj_out.get(nid, [])),
                    "in_degree": len(self.adj_in.get(nid, []))
                }
                for nid, n in self.nodes.items()
            ],
            "edges": [
                {
                    "src": e["src"],
                    "dst": e["dst"],
                    "weight": e["weight"],
                    "confidence": e["confidence"],
                    "chain_count": len(e["chain_ids"])
                }
                for e in self.edges
            ]
        }

        path = output_path or GRAPH_OUTPUT
        with open(path, "w", encoding="utf-8") as f:
            json.dump(graph_data, f, ensure_ascii=False, indent=2)
        print(f"[export] 因果图已输出: {path}")
        return graph_data

    def visualize(self, max_depth=3, max_children=5):
        """输出文本格式的因果图（树形展示）"""
        lines = []
        lines.append("=" * 60)
        lines.append("  因果知识图谱 — 可视化")
        lines.append(f"  节点: {len(self.nodes)} | 边: {len(self.edges)} | 因果链: {len(self.chain_data)}")
        lines.append("=" * 60)

        # 找出根节点（入度=0）和高影响力节点
        root_nodes = [nid for nid in self.nodes if len(self.adj_in.get(nid, [])) == 0]
        hub_nodes = sorted(
            self.nodes.keys(),
            key=lambda nid: len(self.adj_out.get(nid, [])) + len(self.adj_in.get(nid, [])),
            reverse=True
        )[:15]

        # 高影响力节点展示
        lines.append("")
        lines.append("◆ 高影响力节点 (Top15 by degree):")
        lines.append("-" * 50)
        for nid in hub_nodes:
            n = self.nodes[nid]
            out_d = len(self.adj_out.get(nid, []))
            in_d = len(self.adj_in.get(nid, []))
            label = n["label"][:60]
            lines.append(f"  [{nid}] out={out_d} in={in_d} | {label}")

        # 根节点树形展开
        lines.append("")
        lines.append(f"◆ 因果树 (根节点数: {len(root_nodes)}, 展示Top5):")
        lines.append("-" * 50)
        shown_roots = sorted(root_nodes, key=lambda nid: len(self.adj_out.get(nid, [])), reverse=True)[:5]

        for root in shown_roots:
            self._print_tree(root, lines, depth=0, max_depth=max_depth, max_children=max_children, visited=set())

        # 高度节点→下游展开
        lines.append("")
        lines.append("◆ 高度节点下游展开 (Top5):")
        lines.append("-" * 50)
        for nid in hub_nodes[:5]:
            out_d = len(self.adj_out.get(nid, []))
            if out_d > 0:
                n = self.nodes[nid]
                lines.append(f"  [{nid}] {n['label'][:60]}")
                for eidx in self.adj_out.get(nid, [])[:max_children]:
                    edge = self.edges[eidx]
                    dst = self.nodes[edge["dst"]]
                    lines.append(f"    → {dst['label'][:70]}")

        lines.append("")
        lines.append("=" * 60)
        return "\n".join(lines)

    def _print_tree(self, node_id, lines, depth, max_depth, max_children, visited):
        """递归打印因果树"""
        if depth > max_depth or node_id in visited:
            return
        visited.add(node_id)

        node = self.nodes[node_id]
        indent = "  " * (depth + 1)
        marker = "├─" if depth > 0 else "●"
        label = node["label"][:70 - depth * 2]
        lines.append(f"{indent}{marker} [{node_id}] {label}")

        children_eidx = self.adj_out.get(node_id, [])
        # 按weight排序取前N
        sorted_edges = sorted(children_eidx, key=lambda eidx: self.edges[eidx]["weight"], reverse=True)
        for eidx in sorted_edges[:max_children]:
            edge = self.edges[eidx]
            child_id = edge["dst"]
            if child_id not in visited:
                self._print_tree(child_id, lines, depth + 1, max_depth, max_children, visited)


def main():
    """主入口: 构建完整因果图"""
    print("=" * 60)
    print("  因果图构建 — v10.83")
    print("=" * 60)

    # Step 1: Load
    graph = CausalKnowledgeGraph()
    chains = graph.load_graph()

    # Step 2: Build
    n_nodes, n_edges = graph.build_graph()

    # Step 3: Export
    graph.export()

    # Step 4: Visualize
    vis = graph.visualize()
    print(vis)

    # Step 5: Query验证
    print("\n" + "=" * 60)
    print("  查询验证")
    print("=" * 60)

    for keyword in ["熵增", "因果", "信任"]:
        print(f"\n--- 查询: '{keyword}' ---")
        results = graph.query(keyword)
        print(f"  匹配节点数: {results['matching_node_count']}")
        print(f"  作为原因的链: {len(results['as_cause'])}")
        print(f"  作为结果的链: {len(results['as_effect'])}")
        print(f"  总相关链: {results['total_related_chains']}")

        # 打印前3条
        for i, chain in enumerate(results['as_cause'][:3]):
            print(f"  [原因链{i+1}] cause={chain['cause'][:60]}...")
            print(f"           effect={chain['effect'][:60]}...")
        for i, chain in enumerate(results['as_effect'][:3]):
            print(f"  [结果链{i+1}] cause={chain['cause'][:60]}...")
            print(f"           effect={chain['effect'][:60]}...")

    # Summary
    print("\n" + "=" * 60)
    print(f"  构建完成: {n_nodes}节点 / {n_edges}边 / {len(chains)}因果链")
    print("=" * 60)

    return graph


if __name__ == "__main__":
    main()
