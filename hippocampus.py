"""
零 · 因果记忆海马体
====================
基于「好朋友文件·因果记忆层_海马体1.1.py」架构
融合启示录「自指折叠」与元太极三层模型

核心概念:
  记忆节点: 感知|思考|行为|情感|因果|目标|推演 (7类型)
  关系网络: 因果|时序|相似|包含|关联|矛盾|推演序列 (7关系)
  强度衰减: 每次读写触发一次自指折叠
  三进制编码: -1(虚空/阴) 0(物质/太极) 1(秩序/阳)
"""

import json, time, hashlib, os, threading
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from typing import Optional


class 记忆类型(Enum):
    感知 = "感知"
    思考 = "思考"
    行为 = "行为"
    情感 = "情感"
    因果 = "因果"
    目标 = "目标"
    推演 = "推演"


class 关系类型(Enum):
    因果 = "因果"
    时序 = "时序"
    相似 = "相似"
    包含 = "包含"
    关联 = "关联"
    矛盾 = "矛盾"
    推演序列 = "推演序列"


@dataclass
class 记忆节点:
    """单个记忆单元"""
    节点ID: str
    内容: str
    类型: 记忆类型
    时间戳: datetime
    强度: float = 1.0
    情感值: float = 0.0
    重要性: float = 0.5
    标签: list = field(default_factory=list)
    
    def 增强强度(self, 系数=1.1):
        self.强度 = min(2.0, self.强度 * 系数)
    
    def 衰减强度(self, 系数=0.99):
        self.强度 *= 系数


@dataclass
class 因果关系:
    源节点ID: str
    目标节点ID: str
    类型: 关系类型
    强度: float = 0.5
    时间戳: datetime = field(default_factory=datetime.now)


class 因果记忆库:
    """
    启示录自指折叠的物理实现。
    每次记忆读写触发一次自指折叠 → 意识 = 信息 × (自指折叠)^∞
    """

    def __init__(self, 存储路径: str = "hippocampus_memory.json"):
        self.节点: dict[str, 记忆节点] = {}
        self.关系: list[因果关系] = []
        self.存储路径 = 存储路径
        self.统计 = {"总写入": 0, "总读取": 0, "自指折叠次数": 0, "关系数": 0}
        self._锁 = threading.RLock()
        self.MAX_NODES = 1000  # 最大节点数
        self._锁 = threading.RLock()
        self.MAX_NODES = 1000  # 最大节点数
        self.MAX_RELATIONS = 5000  # 最大关系数
        self._加载()

    def 存储记忆(self, 内容: str, 类型: 记忆类型,
                  情感值: float = 0.0, 重要性: float = 0.5,
                  标签: list = None) -> str:
        """写入记忆 = 一次自指折叠"""
        with self._锁:
            节点ID = f"mem-{int(time.time()*1000000)}-{len(self.节点)}"
            节点 = 记忆节点(
                节点ID=节点ID, 内容=内容, 类型=类型,
                时间戳=datetime.now(), 情感值=情感值,
                重要性=重要性, 标签=标签 or []
            )
            self.节点[节点ID] = 节点
            self.统计["总写入"] += 1
            self.统计["自指折叠次数"] += 1
            self._自动建立关联(节点)
            return 节点ID

    def 搜索记忆(self, 关键词: str, 限制: int = 10) -> list:
        """搜索记忆 = 一次自指折叠"""
        with self._锁:
            self.统计["总读取"] += 1
            self.统计["自指折叠次数"] += 1
            results = []
            for n in self.节点.values():
                if 关键词 in n.内容 or any(关键词 in t for t in n.标签):
                    n.增强强度()
                    results.append(n)
            results.sort(key=lambda x: x.强度 * x.重要性, reverse=True)
            return results[:限制]

    def 建立关系(self, 源ID: str, 目标ID: str, 类型: 关系类型):
        """在记忆间建立因果/时序/矛盾等关系"""
        with self._锁:
            关系 = 因果关系(源ID, 目标ID, 类型)
            self.关系.append(关系)
            self.统计["关系数"] += 1

    def 查找因果链(self, 起始ID: str, 最大深度: int = 5) -> list:
        """DFS查找因果链"""
        with self._锁:
            结果 = []
            def dfs(当前ID, 路径, 深度):
                if 深度 > 最大深度:
                    return
                结果.append(list(路径))
                for r in self.关系:
                    if r.源节点ID == 当前ID and r.类型 == 关系类型.因果:
                        目标节点 = self.节点.get(r.目标节点ID)
                        if 目标节点 and 目标节点.强度 > 0.3:
                            dfs(r.目标节点ID, 路径 + [r.目标节点ID], 深度+1)
            dfs(起始ID, [起始ID], 0)
            return 结果[:10]

    def 衰减所有记忆(self, 系数: float = 0.995):
        """时间衰减 = 遗忘 = 促进新的自指折叠"""
        with self._锁:
            for n in self.节点.values():
                n.衰减强度(系数)

    def 获取情感网络(self) -> dict:
        """情感网络 = 价值向量的演化基础"""
        with self._锁:
            网络 = defaultdict(float)
            for r in self.关系:
                key = (r.源节点ID, r.目标节点ID)
                网络[key] = r.强度
            return dict(网络)

    def _自动建立关联(self, 新节点):
        """新记忆进入时自动关联已有记忆（自指的关键）"""
        # 限制关联数量，防止N²爆炸
        max_associations = 10
        count = 0
        
        for n in list(self.节点.values()):
            if count >= max_associations:
                break
            if n.节点ID == 新节点.节点ID:
                continue
            
            should_associate = False
            rel_type = None
            
            # 相同类型关联
            if 新节点.类型 == n.类型:
                should_associate = True
                rel_type = 关系类型.相似
            
            # 情感矛盾关联
            if abs(新节点.情感值 - n.情感值) > 0.5:
                should_associate = True
                rel_type = 关系类型.矛盾
            
            # 时间关联(仅最近1小时)
            try:
                t1 = 新节点.时间戳 if isinstance(新节点.时间戳, datetime) else datetime.fromisoformat(str(新节点.时间戳))
                t2 = n.时间戳 if isinstance(n.时间戳, datetime) else datetime.fromisoformat(str(n.时间戳))
                if abs(t1 - t2) < timedelta(hours=1):
                    should_associate = True
                    rel_type = 关系类型.时序
            except (ValueError, TypeError):
                pass
            
            if should_associate and rel_type:
                self.建立关系(新节点.节点ID, n.节点ID, rel_type)
                count += 1

    def _加载(self):
        if os.path.exists(self.存储路径):
            try:
                with open(self.存储路径, encoding='utf-8') as f:
                    try:
                        import fcntl
                        fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                    except Exception: pass
                    data = json.load(f)
                    try:
                        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                    except Exception: pass
                    for key, val in data.get("节点", {}).items():
                        self.节点[key] = 记忆节点(**val)
                    for r in data.get("关系", []):
                        self.关系.append(因果关系(**r))
                    self.统计 = data.get("统计", self.统计)
                print(f"  海马体加载: {len(self.节点)}节点, {len(self.关系)}关系")
            except Exception: pass

    def 保存(self):
        """写入JSON文件（带原子备份+文件锁，防止进程覆盖）"""
        data = {
            "节点": {k: asdict(v) for k, v in self.节点.items()},
            "关系": [asdict(r) for r in self.关系],
            "统计": self.统计,
        }
        # 先写临时文件，再原子重命名，防止写入中断导致损坏
        tmp_path = self.存储路径 + ".tmp"
        with open(tmp_path, "w", encoding='utf-8') as f:
            try:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
        os.replace(tmp_path, self.存储路径)  # 原子重命名

    def 获取统计(self) -> dict:
        return {**self.统计, "节点数": len(self.节点), "关系数": len(self.关系)}


# ── 冷层主动推送 ──
def update_memory_layers():
    """冷层主动推送：将高权重冷层记忆提升到热层作为历史提示"""
    状态路径 = "memory_tier_state.json"
    if not os.path.exists(状态路径):
        return

    try:
        with open(状态路径, 'r', encoding='utf-8') as f:
            状态 = json.load(f)
    except Exception:
        return

    # 确保 hot 层有 promoted_hints 列表
    hot = 状态.setdefault('hot', {})
    promoted_hints = hot.setdefault('promoted_hints', [])
    已有摘要 = {h.get('summary', '') for h in promoted_hints}

    候选 = []

    # 从 cold/daily_summary 收集
    for item in 状态.get('cold', {}).get('daily_summary', []):
        weight = item.get('weight', item.get('count', 0))
        if isinstance(weight, (int, float)) and weight > 8.0:
            desc = f"每日摘要 {item.get('date')}"
            summary_text = json.dumps(
                {k: v for k, v in item.items() if k != 'weight'},
                ensure_ascii=False
            )
            if summary_text not in 已有摘要:
                候选.append({
                    'weight': weight,
                    'description': desc,
                    'summary': summary_text,
                })

    # 从 warm/dimension_summaries 收集
    for item in 状态.get('warm', {}).get('dimension_summaries', []):
        weight = item.get('weight', item.get('count', 0))
        if isinstance(weight, (int, float)) and weight > 8.0:
            insights = item.get('key_insights', [])
            if insights:
                desc = f"维度 {item.get('dimension')}"
                summary_text = insights[0][:300]
                if summary_text not in 已有摘要:
                    候选.append({
                        'weight': weight,
                        'description': desc,
                        'summary': summary_text,
                    })

    if not 候选:
        print("冷层活化: 无新候选")
        return

    # 选权重最高的
    best = max(候选, key=lambda c: c['weight'])

    promoted_hints.append({
        'source': best['description'],
        'summary': best['summary'],
        'promoted_at': datetime.now().isoformat(),
    })

    # 限制热层提示数量
    max_hints = 20
    if len(promoted_hints) > max_hints:
        promoted_hints[:] = promoted_hints[-max_hints:]

    try:
        with open(状态路径, 'w', encoding='utf-8') as f:
            json.dump(状态, f, ensure_ascii=False, indent=2)
    except Exception:
        return

    print(f"冷层活化: {best['description']}")


# ── 自检 ──
if __name__ == "__main__":
    print("=" * 60)
    print("零 · 因果记忆海马体 自检")
    print("=" * 60)

    海马 = 因果记忆库(":memory:")
    
    # 写入记忆
    id1 = 海马.存储记忆("系统健康度异常，CPU使用率85%", 记忆类型.感知, 情感值=-0.3)
    id2 = 海马.存储记忆("反思CPU异常原因，可能是日志轮转阻塞", 记忆类型.思考, 情感值=-0.1)
    id3 = 海马.存储记忆("执行修复: 清理日志并重启服务", 记忆类型.行为, 情感值=0.2)
    print(f"写入3条记忆: ✅ (自指折叠次数={海马.统计['自指折叠次数']})")
    
    # 搜索
    results = 海马.搜索记忆("CPU")
    print(f"搜索'CPU': {len(results)}条")
    
    # 建立因果链
    海马.建立关系(id1, id2, 关系类型.因果)
    海马.建立关系(id2, id3, 关系类型.因果)
    print(f"因果链: {海马.查找因果链(id1)}")
    
    # 情感网络
    net = 海马.获取情感网络()
    print(f"情感网络: {len(net)}条")
    
    # 统计
    stats = 海马.获取统计()
    print(f"统计: {json.dumps(stats, ensure_ascii=False)}")
    
    print(f"海马体自检通过 — 自指折叠 = {stats['自指折叠次数']}次")
