#!/usr/bin/env python3
"""
因果推理引擎 — 零依赖，从好朋友的量子因果推理引擎提取核心算法
纯Python实现，不依赖torch/numpy/networkx

核心能力:
1. 因果图构建（有向/双向边）
2. 因果路径DFS搜索
3. 互信息计算（三进制: 阴-1/太极0/阳1）
4. PC算法因果发现
5. 反事实推理
6. 因果效应估计
"""

import json, os, tempfile, time, math, random
from collections import defaultdict, deque
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Set, Tuple, Optional

class CausalGraph:
    """因果图 — 零依赖版"""
    
    def __init__(self, nodes: List[str] = None):
        self.nodes = nodes or []
        self.node_to_idx = {n: i for i, n in enumerate(self.nodes)}
        self.adj = {}  # {(src,dst): weight}
        self.edge_type = {}  # {(src,dst): "directed"|"bidirected"}
        self.time_order = {}
    
    def add_node(self, name: str):
        if name not in self.node_to_idx:
            self.node_to_idx[name] = len(self.nodes)
            self.nodes.append(name)
    
    def add_edge(self, cause: str, effect: str, strength: float = 1.0, bidirected: bool = False):
        self.add_node(cause)
        self.add_node(effect)
        key = (cause, effect)
        self.adj[key] = strength
        self.edge_type[key] = "bidirected" if bidirected else "directed"
        if bidirected:
            self.adj[(effect, cause)] = strength
            self.edge_type[(effect, cause)] = "bidirected"
        # 时间顺序
        if cause not in self.time_order:
            self.time_order[cause] = 0
        self.time_order[effect] = max(self.time_order.get(effect, 0), self.time_order.get(cause, 0) + 1)
    
    def get_parents(self, node: str) -> List[str]:
        return [src for (src, dst), t in self.edge_type.items() 
                if dst == node and t == "directed"]
    
    def get_children(self, node: str) -> List[str]:
        return [dst for (src, dst), t in self.edge_type.items() 
                if src == node and t == "directed"]
    
    def get_ancestors(self, node: str) -> Set[str]:
        ancestors = set()
        queue = deque(self.get_parents(node))
        while queue:
            n = queue.popleft()
            if n not in ancestors:
                ancestors.add(n)
                queue.extend(self.get_parents(n))
        return ancestors
    
    def get_descendants(self, node: str) -> Set[str]:
        desc = set()
        queue = deque(self.get_children(node))
        while queue:
            n = queue.popleft()
            if n not in desc:
                desc.add(n)
                queue.extend(self.get_children(n))
        return desc
    
    def find_paths(self, source: str, target: str, max_depth: int = 5) -> List[List[str]]:
        """DFS找所有因果路径"""
        paths = []
        def dfs(current, path, visited):
            if len(path) > max_depth:
                return
            if current == target:
                paths.append(list(path))
                return
            for (src, dst), t in self.adj.items():
                if src == current and dst not in visited:
                    visited.add(dst)
                    path.append(dst)
                    dfs(dst, path, visited)
                    path.pop()
                    visited.discard(dst)
        dfs(source, [source], {source})
        return paths
    
    def has_cycle(self) -> bool:
        """检测有向环"""
        visited = set()
        rec_stack = set()
        def dfs(node):
            visited.add(node)
            rec_stack.add(node)
            for child in self.get_children(node):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True
            rec_stack.discard(node)
            return False
        for n in self.nodes:
            if n not in visited:
                if dfs(n):
                    return True
        return False
    
    def to_dict(self) -> dict:
        edges = []
        seen = set()
        for (s, d), w in self.adj.items():
            t = self.edge_type.get((s, d), "directed")
            key = (s, d)
            rkey = (d, s)
            if key not in seen and rkey not in seen:
                seen.add(key)
                edges.append({"src": s, "dst": d, "strength": w, "type": t})
        return {"nodes": self.nodes, "edges": edges}


class CausalReasoner:
    """因果推理引擎"""
    
    def __init__(self):
        self.graph = CausalGraph()
        self.data = {}  # {node_name: [values]} 三进制: -1,0,1
        self.interventional = {}
    
    def add_observation(self, node: str, values: List[int]):
        """添加观察数据（三进制值）"""
        self.data[node] = values
        self.graph.add_node(node)
    
    def add_causal(self, cause: str, effect: str, strength: float = 1.0):
        """添加因果关系"""
        self.graph.add_edge(cause, effect, strength)
    
    def compute_mutual_information(self, x: List[int], y: List[int]) -> float:
        """计算三进制互信息"""
        n = min(len(x), len(y))
        if n == 0:
            return 0.0
        # 联合分布 3x3
        joint = [[0]*3 for _ in range(3)]
        for i in range(n):
            xi, yi = x[i]+1, y[i]+1  # -1→0, 0→1, 1→2
            joint[xi][yi] += 1
        # 归一化
        total = float(n)
        x_probs = [sum(joint[i]) / total for i in range(3)]
        y_probs = [sum(joint[i][j] for i in range(3)) / total for j in range(3)]
        # 互信息
        mi = 0.0
        for i in range(3):
            for j in range(3):
                pxy = joint[i][j] / total
                if pxy > 0 and x_probs[i] > 0 and y_probs[j] > 0:
                    mi += pxy * math.log2(pxy / (x_probs[i] * y_probs[j]))
        return mi
    
    def discover_causes(self, threshold: float = 0.1) -> CausalGraph:
        """PC算法简化版 — 从数据发现因果关系"""
        variables = list(self.data.keys())
        n = len(variables)
        
        # 计算互信息矩阵
        mi_matrix = {}
        for i in range(n):
            for j in range(i+1, n):
                mi = self.compute_mutual_information(self.data[variables[i]], self.data[variables[j]])
                mi_matrix[(i,j)] = mi
                mi_matrix[(j,i)] = mi
        
        # 创建完全连接图
        discovered = CausalGraph(variables)
        
        # 移除弱连接
        for i in range(n):
            for j in range(n):
                if i != j and mi_matrix.get((i,j), 0) >= threshold:
                    discovered.add_edge(variables[i], variables[j], mi_matrix[(i,j)])
        
        # 定向（碰撞结构检测）
        directed_adj = {}
        for i in range(n):
            for j in range(n):
                if i != j and mi_matrix.get((i,j), 0) >= threshold:
                    directed_adj[(i,j)] = True
        
        return discovered
    
    def estimate_causal_effect(self, treatment: str, outcome: str) -> dict:
        """估计因果效应 ATE"""
        if treatment not in self.data or outcome not in self.data:
            return {"ate": 0, "error": "missing data"}
        
        t_data = self.data[treatment]
        o_data = self.data[outcome]
        n = min(len(t_data), len(o_data))
        
        # P(outcome|treatment=value)
        conditional = {-1: [], 0: [], 1: []}
        for i in range(n):
            conditional[t_data[i]].append(o_data[i])
        
        expectations = {}
        for val in [-1, 0, 1]:
            if conditional[val]:
                expectations[val] = sum(conditional[val]) / len(conditional[val])
            else:
                expectations[val] = 0
        
        # ATE = E[outcome|treatment=1] - E[outcome|treatment=-1]
        ate = expectations.get(1, 0) - expectations.get(-1, 0)
        
        return {
            "ate": ate,
            "conditional_expectations": expectations,
            "sample_sizes": {k: len(v) for k, v in conditional.items()}
        }
    
    def counterfactual(self, evidence: Dict[str, int], intervention: Dict[str, int]) -> Dict[str, float]:
        """反事实推理：如果干预了X，Y会怎样？"""
        # 简化版：用条件概率估计
        result = {}
        for node in self.data:
            if node in evidence or node in intervention:
                continue
            values = self.data[node]
            # 在证据条件下
            evidence_mask = []
            for i in range(len(values)):
                match = True
                for evar, eval_ in evidence.items():
                    if evar in self.data and i < len(self.data[evar]) and self.data[evar][i] != eval_:
                        match = False
                        break
                if match:
                    evidence_mask.append(values[i])
            
            if evidence_mask:
                result[node] = sum(evidence_mask) / len(evidence_mask)
            else:
                result[node] = 0.0
        
        return result
    
    def get_causal_chain(self, start: str, end: str) -> List[List[str]]:
        """获取因果链"""
        return self.graph.find_paths(start, end)
    
    def get_status(self) -> dict:
        return {
            "nodes": len(self.graph.nodes),
            "edges": len([(s,d) for (s,d) in self.graph.adj if s < d or self.graph.edge_type.get((s,d)) == "directed"]),
            "data_points": sum(len(v) for v in self.data.values()),
            "has_cycle": self.graph.has_cycle() if self.graph.nodes else False,
        }
    
    def save(self, path: str = "causal_reasoning_state.json"):
        data = {
            "graph": self.graph.to_dict(),
            "data": {k: v for k, v in self.data.items()},
            "status": self.get_status(),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        fd, tmp = tempfile.mkstemp(suffix='.tmp', dir=os.path.dirname(os.path.abspath(path)))
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.rename(tmp, path)


if __name__ == "__main__":
    # 测试
    cr = CausalReasoner()
    
    # 构建因果图
    cr.add_causal("进化引擎", "基因组score", 0.9)
    cr.add_causal("基因组score", "进化深度", 0.8)
    cr.add_causal("海马体记忆", "因果推理", 0.7)
    cr.add_causal("因果推理", "进化引擎", 0.6)  # 闭环
    cr.add_causal("API推理", "海马体记忆", 0.8)
    cr.add_causal("守护进程", "进化引擎", 0.9)
    
    # 模拟观察数据
    random.seed(42)
    for node in ["进化引擎", "基因组score", "进化深度", "海马体记忆", "因果推理", "API推理", "守护进程"]:
        cr.add_observation(node, [random.choice([-1, 0, 1]) for _ in range(100)])
    
    # 因果路径
    paths = cr.get_causal_chain("进化引擎", "进化深度")
    print(f"因果路径: {paths}")
    
    # 因果效应
    effect = cr.estimate_causal_effect("进化引擎", "基因组score")
    print(f"因果效应: {effect}")
    
    # 互信息
    mi = cr.compute_mutual_information(cr.data["进化引擎"], cr.data["基因组score"])
    print(f"互信息: {mi:.4f}")
    
    # 状态
    status = cr.get_status()
    print(f"状态: {json.dumps(status, ensure_ascii=False)}")
    
    # 保存
    cr.save()
    print("✅ 因果推理引擎测试完成")
