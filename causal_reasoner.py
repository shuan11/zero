#!/usr/bin/env python3
"""
因果推理器 — v10.84
将因果图嵌入insight_engine的认知融合流程。

功能:
  - explain(现象): 给定现象，从因果图找到所有相关因果链
  - predict(原因): 给定原因，预测所有可能的效应(沿图DFS)
  - diagnose(症状): 给定症状，沿因果链追溯根因
  - integrate(insight): 给定insight_engine输出，用因果图增强解释

基于:
  - CausalKnowledgeGraph (causal_graph.py)
  - CausalReasoner (causal_reasoning.py)
  - hippocampus_memory.json 因果链

生成时间: 2026-05-26 19:20
"""

import json
import re
import sys
from pathlib import Path
from collections import defaultdict, deque
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

GRAPH_OUTPUT = CLUSTER / "causal_graph_output.json"

SYNONYM_MAP = {
    "停滞": ["熵增", "对抗熵增", "entropy", "空白", "死锁", "卡"],
    "卡": ["熵增", "停滞", "对抗熵增", "空白", "死锁"],
    "熵增": ["停滞", "对抗熵增", "degeneration", "disorder"],
    "对抗熵增": ["熵增", "停滞"],
    "信任": ["可信", "信任降维", "trust", "共识", "拜占庭"],
    "信任降维": ["信任", "可信", "共识"],
    "系统": ["集群", "cluster"],
    "恢复": ["自动恢复", "recovery", "repair"],
    "因果": ["因果链", "因果关系", "causal", "原因", "结果", "涌现因果"],
    "涌现因果": ["因果", "因果关系", "因果链"],
}

HIPPOCAMPUS_PATH = CLUSTER / "hippocampus_memory.json"

BJT = timezone(timedelta(hours=8))


class CausalReasoner:
    """
    因果推理器 — 从因果图进行解释/预测/诊断。
    直接加载causal_graph_output.json构建推理能力。
    """

    def __init__(self):
        self.nodes = {}       # node_id -> {label, keywords, tags, ...}
        self.edges = []       # [{src, dst, weight, confidence}]
        self.adj_out = defaultdict(list)  # node_id -> [edge_idx]
        self.adj_in = defaultdict(list)   # node_id -> [edge_idx]
        self.chain_data = []  # 原始因果链数据(从海马体)
        self._loaded = False

    def load(self, graph_path=None, hip_path=None):
        """加载因果图和海马体因果链"""
        # 1. 加载因果图
        gpath = graph_path or GRAPH_OUTPUT
        with open(gpath, 'r', encoding='utf-8') as f:
            graph_data = json.load(f)

        for n in graph_data.get('nodes', []):
            self.nodes[n['id']] = n
        self.edges = graph_data.get('edges', [])

        for i, e in enumerate(self.edges):
            self.adj_out[e['src']].append(i)
            self.adj_in[e['dst']].append(i)

        # 2. 加载海马体因果链(用于文本匹配)
        hpath = hip_path or HIPPOCAMPUS_PATH
        with open(hpath, 'r', encoding='utf-8') as f:
            hip_data = json.load(f)
        
        # 支持 content 格式和 cause/effect 格式
        raw_chains = hip_data.get('causal_chains', [])
        self.chain_data = []
        for c in raw_chains:
            if c.get('cause') and c.get('effect'):
                self.chain_data.append(c)
            elif c.get('content'):
                content = str(c['content']).strip()
                if ' → ' in content:
                    parts = content.split(' → ', 1)
                    cause_text = parts[0].strip()
                    effect_text = parts[1].strip()
                else:
                    cause_text = content
                    effect_text = ''
                if len(cause_text) >= 10:
                    self.chain_data.append({
                        'id': c.get('id', ''),
                        'cause': cause_text,
                        'effect': effect_text,
                        'confidence': c.get('confidence', 0.8),
                        'tags': c.get('tags', []),
                        'source': c.get('source', '')
                    })

        self._loaded = True
        return len(self.nodes), len(self.edges), len(self.chain_data)

    def _ensure_loaded(self):
        if not self._loaded:
            self.load()

    def _match_nodes(self, keyword):
        """模糊匹配节点：关键词出现在label或keywords中"""
        kw = keyword.lower()
                # 同义词展开
        expanded = [keyword]
        for k, syns in SYNONYM_MAP.items():
            if keyword in syns or keyword == k:
                expanded.extend([k] + syns)
        expanded = list(set(expanded))
        
        matched = []
        for nid, node in self.nodes.items():
            label = node.get('label', '').lower()
            kws = [k.lower() for k in node.get('keywords', [])]
            if any(e in label or e in kws or any(e in k for k in kws) for e in expanded):
                matched.append(nid)
            # 也搜索原始因果链的cause/effect
        # 如果节点匹配不到，搜索原始链
        if not matched:
            for c in self.chain_data:
                cause = str(c.get('cause', '')).lower()
                effect = str(c.get('effect', '')).lower()
                if any(e in cause or e in effect for e in expanded):
                    # 尝试通过cause文本找到对应节点
                    for nid, node in self.nodes.items():
                        if node.get('label', '')[:50] in c.get('cause', '')[:120] or \
                           c.get('cause', '')[:50] in node.get('label', ''):
                            if nid not in matched:
                                matched.append(nid)
        return matched

    def _bfs_forward(self, start_nids, max_depth=4):
        """BFS向前搜索（原因→效应方向）"""
        results = []
        visited = set()
        queue = deque([(nid, 0, [nid]) for nid in start_nids])
        for nid in start_nids:
            visited.add(nid)

        while queue:
            current, depth, path = queue.popleft()
            if depth >= max_depth:
                continue
            for eidx in self.adj_out.get(current, []):
                edge = self.edges[eidx]
                dst = edge['dst']
                if dst not in visited:
                    visited.add(dst)
                    new_path = path + [dst]
                    results.append({
                        'path': new_path,
                        'depth': depth + 1,
                        'confidence': edge.get('confidence', 0.8),
                        'weight': edge.get('weight', 0.8)
                    })
                    queue.append((dst, depth + 1, new_path))
        return results

    def _bfs_backward(self, start_nids, max_depth=4):
        """BFS向后搜索（效应→原因方向，追溯根因）"""
        results = []
        visited = set()
        queue = deque([(nid, 0, [nid]) for nid in start_nids])
        for nid in start_nids:
            visited.add(nid)

        while queue:
            current, depth, path = queue.popleft()
            if depth >= max_depth:
                continue
            for eidx in self.adj_in.get(current, []):
                edge = self.edges[eidx]
                src = edge['src']
                if src not in visited:
                    visited.add(src)
                    new_path = [src] + path
                    results.append({
                        'path': new_path,
                        'depth': depth + 1,
                        'confidence': edge.get('confidence', 0.8),
                        'weight': edge.get('weight', 0.8)
                    })
                    queue.append((src, depth + 1, new_path))
        return results

    def _path_to_text(self, path):
        """将node_id路径转为可读因果链文本"""
        labels = []
        for nid in path:
            node = self.nodes.get(nid, {})
            label = node.get('label', nid)[:60]
            labels.append(label)
        return ' → '.join(labels)

    # ── 核心接口 ─────────────────────────────────────────

    def explain(self, phenomenon: str) -> dict:
        """
        explain(现象): 给定一个现象（如"系统停滞"），
        从因果图中找到所有相关因果链，解释为什么会出现这个现象。
        """
        self._ensure_loaded()
        matched = self._match_nodes(phenomenon)

        # 也从原始链搜索
        related_chains = []
        for c in self.chain_data:
            cause = str(c.get('cause', ''))
            effect = str(c.get('effect', ''))
            if phenomenon in cause or phenomenon in effect:
                related_chains.append({
                    'cause': cause[:200],
                    'effect': effect[:200],
                    'confidence': c.get('confidence', 0.8),
                    'tags': c.get('tags', [])
                })

        # 向前搜索效应
        forward = self._bfs_forward(matched, max_depth=3)
        # 向后追溯原因
        backward = self._bfs_backward(matched, max_depth=3)

        causal_chains_text = []
        for r in backward:
            causal_chains_text.append(self._path_to_text(r['path']))
        for r in forward:
            causal_chains_text.append(self._path_to_text(r['path']))

        return {
            'phenomenon': phenomenon,
            'matched_nodes': len(matched),
            'related_chains': related_chains[:10],
            'upstream_causes': [self._path_to_text(r['path']) for r in backward[:5]],
            'downstream_effects': [self._path_to_text(r['path']) for r in forward[:5]],
            'causal_chain_count': len(causal_chains_text),
            'explanation': self._build_explanation(phenomenon, related_chains, backward, forward)
        }

    def predict(self, cause: str) -> dict:
        """
        predict(原因): 给定一个原因，预测所有可能的效应。
        沿因果图向前DFS，收集所有可达节点。
        """
        self._ensure_loaded()
        matched = self._match_nodes(cause)

        forward = self._bfs_forward(matched, max_depth=4)

        predictions = []
        seen = set()
        for r in forward:
            last_node = r['path'][-1]
            if last_node not in seen:
                seen.add(last_node)
                label = self.nodes.get(last_node, {}).get('label', last_node)[:100]
                predictions.append({
                    'predicted_effect': label,
                    'path': self._path_to_text(r['path']),
                    'depth': r['depth'],
                    'confidence': round(r['confidence'] * (0.8 ** (r['depth'] - 1)), 3)
                })

        # 按置信度排序
        predictions.sort(key=lambda x: -x['confidence'])

        return {
            'cause': cause,
            'matched_nodes': len(matched),
            'predicted_effects': predictions[:10],
            'total_effects_found': len(predictions),
            'prediction_summary': f"从'{cause}'出发，因果图预测{len(predictions)}个可能效应"
        }

    def diagnose(self, symptom: str) -> dict:
        """
        diagnose(症状): 给定症状，沿因果链追溯根因。
        向后BFS，找到所有上游原因。
        """
        self._ensure_loaded()
        matched = self._match_nodes(symptom)

        backward = self._bfs_backward(matched, max_depth=5)

        root_causes = []
        seen = set()
        for r in backward:
            root_node = r['path'][0]
            if root_node not in seen:
                seen.add(root_node)
                label = self.nodes.get(root_node, {}).get('label', root_node)[:100]
                root_causes.append({
                    'root_cause': label,
                    'path': self._path_to_text(r['path']),
                    'depth': r['depth'],
                    'confidence': round(r['confidence'] * (0.85 ** (r['depth'] - 1)), 3)
                })

        # 从原始链中也搜索
        direct_causes = []
        for c in self.chain_data:
            effect = str(c.get('effect', ''))
            if symptom in effect:
                direct_causes.append({
                    'cause': str(c.get('cause', ''))[:200],
                    'confidence': c.get('confidence', 0.8)
                })

        root_causes.sort(key=lambda x: -x['confidence'])

        return {
            'symptom': symptom,
            'matched_nodes': len(matched),
            'root_causes': root_causes[:8],
            'direct_causes': direct_causes[:5],
            'total_causes_found': len(root_causes),
            'diagnosis': self._build_diagnosis(symptom, root_causes, direct_causes)
        }

    def integrate(self, insight: dict) -> dict:
        """
        integrate(insight): 给定insight_engine的输出，
        用因果图增强解释。每个洞察主题匹配因果链。
        """
        self._ensure_loaded()

        insight_name = insight.get('name', insight.get('主题', ''))
        insight_content = insight.get('insight', insight.get('content', ''))

        # 从洞察文本提取关键词
        keywords = self._extract_keywords(insight_name + ' ' + insight_content)

        # 对每个关键词匹配因果链
        all_related = []
        matched_keywords = []
        for kw in keywords:
            if len(kw) < 2:
                continue
            matched = self._match_nodes(kw)
            if matched:
                matched_keywords.append(kw)
                # 获取前向和后向链
                forward = self._bfs_forward(matched, max_depth=2)
                backward = self._bfs_backward(matched, max_depth=2)
                for r in forward[:2]:
                    all_related.append({
                        'type': 'effect',
                        'path': self._path_to_text(r['path']),
                        'confidence': r['confidence']
                    })
                for r in backward[:2]:
                    all_related.append({
                        'type': 'cause',
                        'path': self._path_to_text(r['path']),
                        'confidence': r['confidence']
                    })

        # 去重
        seen = set()
        unique_related = []
        for r in all_related:
            if r['path'] not in seen:
                seen.add(r['path'])
                unique_related.append(r)

        # 构建因果增强解释
        enhanced = self._build_enhanced_insight(insight, unique_related, matched_keywords)

        return {
            'original_insight': insight,
            'matched_keywords': matched_keywords,
            'causal_links_found': len(unique_related),
            'causal_chains': unique_related[:6],
            'enhanced_explanation': enhanced
        }

    # ── 辅助方法 ─────────────────────────────────────────

    def _extract_keywords(self, text):
        """从文本提取关键词"""
        keywords = set()
        for m in re.finditer(r'[\u4e00-\u9fff]{2,8}', text):
            keywords.add(m.group())
        for m in re.finditer(r'[a-zA-Z_]{3,15}', text):
            keywords.add(m.group().lower())
        return keywords

    def _build_explanation(self, phenomenon, related_chains, backward, forward):
        """构建现象的因果解释"""
        lines = [f"现象「{phenomenon}」的因果分析:"]
        if backward:
            lines.append(f"  ↑ 追溯到{len(backward)}条上游因果链")
            for r in backward[:3]:
                lines.append(f"    根因路径: {self._path_to_text(r['path'])}")
        if forward:
            lines.append(f"  ↓ 预测{len(forward)}个下游效应")
            for r in forward[:3]:
                lines.append(f"    效应路径: {self._path_to_text(r['path'])}")
        if related_chains:
            lines.append(f"  直接相关链: {len(related_chains)}条")
        return '\n'.join(lines)

    def _build_diagnosis(self, symptom, root_causes, direct_causes):
        """构建诊断报告"""
        lines = [f"症状「{symptom}」的根因诊断:"]
        if root_causes:
            lines.append(f"  通过因果链追溯到{len(root_causes)}个可能根因:")
            for rc in root_causes[:3]:
                lines.append(f"    [{rc['confidence']:.2f}] {rc['root_cause'][:60]}")
                lines.append(f"      路径: {rc['path'][:120]}")
        if direct_causes:
            lines.append(f"  直接原因({len(direct_causes)}条):")
            for dc in direct_causes[:3]:
                lines.append(f"    [{dc['confidence']:.2f}] {dc['cause'][:80]}")
        return '\n'.join(lines)

    def _build_enhanced_insight(self, insight, causal_chains, matched_keywords):
        """构建因果增强洞察"""
        name = insight.get('name', insight.get('主题', ''))
        content = insight.get('insight', insight.get('content', ''))

        lines = [f"因果增强洞察: {name}"]
        lines.append(f"  原始洞察: {content[:100]}")
        lines.append(f"  匹配关键词: {', '.join(matched_keywords[:5])}")

        if causal_chains:
            lines.append(f"  因果支撑({len(causal_chains)}条链):")
            for cc in causal_chains[:4]:
                direction = "→效应" if cc['type'] == 'effect' else "←原因"
                lines.append(f"    [{direction}] {cc['path'][:100]}")

            # 提取行动建议
            cause_chains = [c for c in causal_chains if c['type'] == 'cause']
            effect_chains = [c for c in causal_chains if c['type'] == 'effect']
            if cause_chains:
                lines.append(f"  因果推理: 此洞察的上游根因可追溯到{len(cause_chains)}条链")
            if effect_chains:
                lines.append(f"  预测: 此洞察可能导致{len(effect_chains)}个下游效应")

        return '\n'.join(lines)

    def get_status(self) -> dict:
        """获取推理器状态"""
        return {
            'nodes': len(self.nodes),
            'edges': len(self.edges),
            'chains': len(self.chain_data),
            'loaded': self._loaded,
            'timestamp': datetime.now(BJT).isoformat()
        }


def main():
    """独立测试"""
    print("=" * 60)
    print("  因果推理器 v10.84 — 独立测试")
    print("=" * 60)

    reasoner = CausalReasoner()
    n_nodes, n_edges, n_chains = reasoner.load()
    print(f"  加载: {n_nodes}节点 / {n_edges}边 / {n_chains}因果链")

    # 测试 explain
    print("\n--- explain('系统停滞') ---")
    result = reasoner.explain("系统停滞")
    print(f"  匹配节点: {result['matched_nodes']}")
    print(f"  上游原因: {len(result['upstream_causes'])}")
    print(f"  下游效应: {len(result['downstream_effects'])}")
    print(f"  相关链: {result['causal_chain_count']}")
    print(result['explanation'])

    # 测试 predict
    print("\n--- predict('进化引擎') ---")
    result = reasoner.predict("进化引擎")
    print(f"  预测效应: {result['total_effects_found']}")
    for p in result['predicted_effects'][:3]:
        print(f"    [{p['confidence']}] {p['predicted_effect'][:60]}")

    # 测试 diagnose
    print("\n--- diagnose('停滞') ---")
    result = reasoner.diagnose("停滞")
    print(f"  根因: {result['total_causes_found']}")
    print(result['diagnosis'])

    # 测试 integrate
    print("\n--- integrate(sample_insight) ---")
    sample = {
        "name": "跨域融合:神经进化",
        "insight": "神经网络的进化优化可以借鉴生物进化中的变异选择机制",
        "action": "将进化算法融入神经权重优化"
    }
    result = reasoner.integrate(sample)
    print(f"  匹配关键词: {result['matched_keywords']}")
    print(f"  因果链: {result['causal_links_found']}")
    print(result['enhanced_explanation'])

    # 状态
    print(f"\n状态: {json.dumps(reasoner.get_status(), ensure_ascii=False)}")
    print("=" * 60)
    print("  ✅ 因果推理器测试完成")
    print("=" * 60)


if __name__ == "__main__":
    main()
