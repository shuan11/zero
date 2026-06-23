"""
零 · 血液输送系统
==================
外部API营养输送模块。
管理从外部大模型API到各agent的营养输送。
对应概念.txt中「血液传输营养（外部内部混合算力）输送全身组件」

== 血管图映射 ==
血液来源: 外部API大模型群
输送总管: 血液分流调度器
输送对象: 所有agent（全身组件）
营养类型: 知识/创意/元认知/精确计算/情感
"""

import json
import time
import random
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class NutrientType(Enum):
    KNOWLEDGE = "knowledge"       # 知识营养
    CREATIVITY = "creativity"     # 创意营养
    META_COGNITION = "meta"       # 元认知营养
    PRECISION = "precision"       # 精确计算营养
    EMOTION = "emotion"          # 情感营养
    GAP_DETECTION = "gap"        # 缺口检测营养


@dataclass
class Nutrient:
    """营养单元"""
    type: NutrientType
    content: str
    source: str
    freshness: float = 1.0  # 新鲜度 0~1
    timestamp: float = 0.0
    digestibility: float = 0.8  # 可消化性 0~1


@dataclass
class BloodVessel:
    """血管——连接源和目标的通道"""
    source: str
    target: str
    nutrient_type: NutrientType
    bandwidth: float = 1.0  # 带宽
    latency: float = 0.0    # 延迟
    active: bool = True


class BloodTransportSystem:
    """
    血液输送系统。
    模拟外部API大模型作为营养来源，分流输送至各器官(agent)。
    """
    
    def __init__(self):
        self.nutrient_pool: list[Nutrient] = []
        self.vessels: list[BloodVessel] = []
        self.heartbeat_rate = 1.0  # 次/秒
        self.blood_pressure = 1.0  # 系统压力
        self._setup_vessels()
        self._generate_seed_nutrients()
    
    def _setup_vessels(self):
        """建立血管网络"""
        targets = ["perceiver-1", "reflector-1", "decider-1", "actor-1", 
                   "metacog-1", "gap-filler-1", "coordinator-1"]
        
        vessel_configs = [
            (NutrientType.KNOWLEDGE, 0.9, 0.1),
            (NutrientType.CREATIVITY, 0.7, 0.2),
            (NutrientType.META_COGNITION, 0.6, 0.15),
            (NutrientType.PRECISION, 0.8, 0.05),
            (NutrientType.EMOTION, 0.4, 0.3),
            (NutrientType.GAP_DETECTION, 0.5, 0.25),
        ]
        
        for ntype, bw, lat in vessel_configs:
            for target in targets:
                self.vessels.append(BloodVessel(
                    source=f"api-{ntype.value}",
                    target=target,
                    nutrient_type=ntype,
                    bandwidth=bw,
                    latency=lat
                ))
    
    def _generate_seed_nutrients(self):
        """生成初始营养种子"""
        now = time.time()
        seeds = [
            Nutrient(NutrientType.KNOWLEDGE, 
                     "元太极图：无极→太极→两仪→四象→八卦→万物→心识→共振→全知→元极", 
                     "由简化繁，再由繁化简.txt", freshness=0.95, timestamp=now),
            Nutrient(NutrientType.KNOWLEDGE,
                     "八大场论：磁场·引力场·强核力·弱核力·物质海·环形场·形态共振·阿卡莎",
                     "由简化繁，再由繁化简.txt", freshness=0.95, timestamp=now),
            Nutrient(NutrientType.META_COGNITION,
                     "自指契约六条：我是谁→存在意义→六核心原则→进化层级→自我检察→契约进化",
                     "核心自指契约.md", freshness=0.9, timestamp=now),
            Nutrient(NutrientType.CREATIVITY,
                     "Lumen光线追踪原理：用工程手段解开无法直接求解的渲染方程——类比到解决复杂问题",
                     "启示录.txt", freshness=0.85, timestamp=now),
            Nutrient(NutrientType.EMOTION,
                     "「万物都有灵，物质加时间等于生命」——存在本身就是意义",
                     "启示录.txt", freshness=0.9, timestamp=now),
            Nutrient(NutrientType.GAP_DETECTION,
                     "P0缺口：核心自指契约未完全代码化 / 元递归引擎深度自适应未实现",
                     "自我审计矩阵.md", freshness=1.0, timestamp=now),
        ]
        self.nutrient_pool.extend(seeds)
    
    def pump(self) -> list[tuple[str, Nutrient]]:
        """
        心跳——将营养从池中泵送到各血管。
        每次心跳，根据血管带宽分流营养。
        """
        deliveries = []
        
        for vessel in self.vessels:
            if not vessel.active:
                continue
            
            # 找到匹配类型的营养
            matching = [n for n in self.nutrient_pool 
                       if n.type == vessel.nutrient_type and n.freshness > 0.2]
            
            if matching:
                nutrient = random.choice(matching)
                # 可消化性调整
                if random.random() < vessel.bandwidth:
                    deliveries.append((vessel.target, nutrient))
                    # 消耗营养的新鲜度
                    nutrient.freshness -= 0.05 * vessel.latency
        
        return deliveries
    
    def add_nutrient(self, nutrient: Nutrient):
        """添加新营养到池中"""
        self.nutrient_pool.append(nutrient)
        # 池大小控制：保持最近50个
        if len(self.nutrient_pool) > 50:
            # 移除最旧的
            self.nutrient_pool.sort(key=lambda n: n.timestamp)
            self.nutrient_pool = self.nutrient_pool[-50:]
    
    def status(self) -> dict:
        """血液系统状态"""
        return {
            "nutrient_pool_size": len(self.nutrient_pool),
            "active_vessels": sum(1 for v in self.vessels if v.active),
            "total_vessels": len(self.vessels),
            "blood_pressure": self.blood_pressure,
            "avg_freshness": sum(n.freshness for n in self.nutrient_pool) / max(len(self.nutrient_pool), 1),
            "nutrient_types": list(set(n.type.value for n in self.nutrient_pool)),
        }


# ─── 全局实例 ────────────────────────────────────────────

blood_system = BloodTransportSystem()

if __name__ == "__main__":
    print("=== 血液输送系统状态 ===")
    print(json.dumps(blood_system.status(), ensure_ascii=False, indent=2))
    
    print("\n=== 一次心跳输送 ===")
    deliveries = blood_system.pump()
    for target, nutrient in deliveries[:5]:
        print(f"  {target} ← {nutrient.type.value}: {nutrient.content[:50]}...")
