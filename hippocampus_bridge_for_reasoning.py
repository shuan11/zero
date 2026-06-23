"""
零·深度思考→海马体因果记忆桥接器
=================================
P116: 将深度思考链的结果写入海马体因果记忆库，形成跨会话可检索的因果链。
"""

import sys
import time
from pathlib import Path
from typing import Optional

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")


class ReasoningHippocampusBridge:
    """深度思考→海马体桥接器"""
    
    def __init__(self):
        self._hip = None
        self._mem_type = None
        self._rel_type = None
        self._last_node_id: Optional[str] = None
        self._load()
    
    def _load(self):
        try:
            # 直接导入（不使用importlib避免重复加载）
            sys.path.insert(0, str(WORKDIR))
            import hippocampus as _hip_mod
            self._mem_type = _hip_mod.记忆类型
            self._rel_type = _hip_mod.关系类型
            self._hip = _hip_mod.因果记忆库(str(WORKDIR / "hippocampus_memory.json"))
            sys.path.pop(0)
        except Exception as e:
            self._hip = None
    
    @property
    def available(self) -> bool:
        return self._hip is not None
    
    def store_reasoning_step(self, step: dict) -> Optional[str]:
        if not self._hip:
            return None
        try:
            type_map = {
                "perception": self._mem_type.感知, "reflection": self._mem_type.思考,
                "thought": self._mem_type.思考, "reasoning": self._mem_type.思考,
                "meta": self._mem_type.推演, "inspection": self._mem_type.推演,
                "contradiction": self._mem_type.因果,
            }
            mem_type = type_map.get(step.get("type", "reasoning"), self._mem_type.思考)
            content = (
                f"深度思考 [{step.get('id','?')[:16]}]\n"
                f"输入: {step.get('input_text','')[:100]}\n"
                f"输出: {step.get('output_text','')[:200]}\n"
                f"深度: {step.get('depth',0)}层 | "
                f"熵: {step.get('entropy',0):.3f} | "
                f"耗时: {step.get('elapsed_ms',0)}ms"
            )
            node_id = self._hip.存储记忆(
                内容=content, 类型=mem_type, 情感值=0.0,
                重要性=min(1.0, 0.5 + step.get("tokens_generated", 0) / 100),
            )
            if self._last_node_id and node_id:
                self._hip.建立关系(源ID=self._last_node_id, 目标ID=node_id, 类型=self._rel_type.因果)
            self._last_node_id = node_id
            self._hip.保存()
            return node_id
        except Exception:
            return None
    
    def store_inspection(self, inspection: dict, parent_step_id: Optional[str] = None) -> Optional[str]:
        if not self._hip:
            return None
        try:
            assumptions = inspection.get("assumptions", [])
            blind_spots = inspection.get("blind_spots", [])
            content = (
                f"自指检察 [{inspection.get('step_id','?')[:16]}]\n"
                f"假设: {'; '.join(assumptions[:3]) or '无'}\n"
                f"盲点: {'; '.join(blind_spots[:3]) or '无'}\n"
                f"自信度: {inspection.get('confidence', 0):.3f}"
            )
            node_id = self._hip.存储记忆(内容=content, 类型=self._mem_type.推演, 情感值=0.0, 重要性=0.8)
            if parent_step_id and node_id:
                parent = self._find_node(parent_step_id)
                if parent:
                    self._hip.建立关系(源ID=parent, 目标ID=node_id, 类型=self._rel_type.关联)
            self._hip.保存()
            return node_id
        except Exception:
            return None
    
    def store_contradiction(self, c: dict) -> Optional[str]:
        if not self._hip:
            return None
        try:
            content = (
                f"矛盾 [{c.get('id','?')[:16]}]\n"
                f"类型: {c.get('type','?')}\n"
                f"描述: {c.get('description','')[:200]}\n"
                f"严重度: {c.get('severity', 0):.2f}"
            )
            node_id = self._hip.存储记忆(内容=content, 类型=self._mem_type.因果,
                                          情感值=0.0, 重要性=min(1.0, c.get("severity", 0.5)))
            if node_id:
                a = self._find_node(c.get("source_a", ""))
                b = self._find_node(c.get("source_b", ""))
                if a:
                    self._hip.建立关系(源ID=a, 目标ID=node_id, 类型=self._rel_type.矛盾)
                if b:
                    self._hip.建立关系(源ID=b, 目标ID=node_id, 类型=self._rel_type.矛盾)
            self._hip.保存()
            return node_id
        except Exception:
            return None
    
    def store_evolution(self, evo: dict) -> Optional[str]:
        if not self._hip:
            return None
        try:
            content = (
                f"进化触发 [{int(time.time())}]\n"
                f"触发: {evo.get('triggered', False)}\n"
                f"原因: {evo.get('reason', '')[:100]}\n"
                f"矛盾数: {evo.get('contradictions_found', 0)}"
            )
            node_id = self._hip.存储记忆(内容=content, 类型=self._mem_type.目标, 情感值=0.0, 重要性=0.9)
            self._hip.保存()
            return node_id
        except Exception:
            return None
    
    def retrieve_causal_chain(self, max_depth: int = 5) -> list:
        if not self._hip:
            return []
        try:
            recent = self._hip.搜索记忆("深度思考", 限制=5)
            chains = []
            for node in recent[:3]:
                if hasattr(node, 'id'):
                    chain = self._hip.查找因果链(node.id, 最大深度=max_depth)
                    if chain:
                        chains.append({"start": node.id, "chain": [str(n)[:80] for n in chain], "length": len(chain)})
            return chains
        except Exception:
            return []
    
    def get_memory_stats(self) -> dict:
        if not self._hip:
            return {"available": False}
        try:
            return {"available": True, "stats": self._hip.获取统计()}
        except Exception as e:
            return {"available": False, "error": str(e)}
    
    def _find_node(self, reasoning_id: str) -> Optional[str]:
        if not self._hip or not reasoning_id:
            return None
        try:
            nodes = self._hip.搜索记忆(reasoning_id[:20], 限制=5)
            for node in nodes:
                if hasattr(node, 'id'):
                    return node.id
            return None
        except Exception:
            return None


def store_deep_reasoning_cycle(cycle_result: dict) -> dict:
    """存储完整深度思考循环"""
    bridge = ReasoningHippocampusBridge()
    if not bridge.available:
        return {"stored": False, "error": "海马体不可用"}
    result = {"stored": True}
    rid = bridge.store_reasoning_step(cycle_result.get("reasoning", {}))
    result["reasoning_id"] = rid
    inspection = cycle_result.get("inspection", {})
    result["inspection_id"] = bridge.store_inspection(inspection, parent_step_id=cycle_result.get("reasoning", {}).get("id"))
    cids = []
    for c in cycle_result.get("contradictions", []):
        cid = bridge.store_contradiction(c)
        if cid:
            cids.append(cid)
    result["contradiction_ids"] = cids
    result["evolution_id"] = bridge.store_evolution(cycle_result.get("evolution", {}))
    return result


def retrieve_reasoning_history(max_depth: int = 5) -> dict:
    # 【已废弃】此函数不再被调用，保留签名作为文档参考
    # 原功能：从海马体因果记忆库检索推理历史
    pass


def self_test():
    print("=" * 60)
    print("  深度思考→海马体因果记忆桥接器 自检")
    print("=" * 60)
    bridge = ReasoningHippocampusBridge()
    print(f"\n海马体: {'✅ 已接入' if bridge.available else '❌ 不可用'}")
    if bridge.available:
        print(f"  统计: {bridge.get_memory_stats()}")
        step = {
            "id": f"test_{int(time.time())}", "input_text": "测试输入",
            "output_text": "测试输出 深度思考", "depth": 12,
            "entropy": 0.5, "elapsed_ms": 162, "tokens_generated": 8,
        }
        nid = bridge.store_reasoning_step(step)
        print(f"  存储推理步骤: {'✅' if nid else '❌'}")
        insp = {"step_id": step["id"], "assumptions": ["确定性表述"], "blind_spots": ["缺疑问"], "confidence": 0.7}
        iid = bridge.store_inspection(insp, step["id"])
        print(f"  存储检察: {'✅' if iid else '❌'}")
        step2 = {
            "id": f"test_{int(time.time())}_2", "input_text": "第二次推理",
            "output_text": "第二次思考", "depth": 12,
            "entropy": 0.8, "elapsed_ms": 200, "tokens_generated": 12,
        }
        nid2 = bridge.store_reasoning_step(step2)
        print(f"  第二次推理→自动因果链: {'✅' if nid2 else '❌'}")
        chains = bridge.retrieve_causal_chain(3)
        print(f"  因果链: {len(chains)}条")
        print("✅ 桥接器就绪")


if __name__ == "__main__":
    self_test()
