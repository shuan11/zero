"""
零 · 统一进化引擎
=================
将 P513EvolutionEngine (进化核心) 与 MetaRecursiveEngine (思维核心)
融合为单一入口的 UnifiedEvolutionEngine。

设计理念：
  - core_engine 提供：思维模式匹配、缺口管理、场强测量、经验存储
  - p513 提供：七条自指契约、五阶段进化循环、元递归进化
  - 统一引擎将两者缝合，消除孤岛，实现"不仅能进化自己，还能进化进化方式"
"""

import time
import json
import os
from datetime import datetime

# ─── 路径设置 ──────────────────────────────────────────────
_dir = os.path.dirname(os.path.abspath(__file__))
import sys
if _dir not in sys.path:
    sys.path.insert(0, _dir)

from core_engine import (
    MetaRecursiveEngine, CoreContract,
    Thought, Pattern, Gap
)
from p513_evolution_engine import P513EvolutionEngine, EVOLUTION_LEVELS


class UnifiedEvolutionEngine:
    """
    统一进化引擎 — 一即是全，全即是一。

    两个内核的关系：
    ┌──────────────────────────────────────────────┐
    │           UnifiedEvolutionEngine              │
    │  ┌────────────────┐  ┌────────────────────┐  │
    │  │ MetaRecursive  │  │ P513Evolution      │  │
    │  │ Engine (思维)  │←→│ Engine (进化)      │  │
    │  │                │  │                    │  │
    │  │ • think()      │  │ • run_evolution()  │  │
    │  │ • patterns     │  │ • meta_recursion() │  │
    │  │ • gaps         │  │ • contracts (7)    │  │
    │  │ • field_strength│ │ • levels (L0-L6)  │  │
    │  │ • experiences  │  │ • full_sequence()  │  │
    │  └────────────────┘  └────────────────────┘  │
    │         ↕ 共享状态 ↕                          │
    │  CoreContract ↔ P513 契约检查                  │
    └──────────────────────────────────────────────┘
    """

    def __init__(self, api_bridge=None):
        # ── 两个内核 ──
        self.core = MetaRecursiveEngine()
        self.p513 = P513EvolutionEngine(api_bridge=api_bridge)

        # ── 统一状态 ──
        self.unified_cycle_count = 0
        self.creation_time = time.time()
        self.api_bridge = api_bridge

        # ── 同步桥接：core 的状态喂给 p513 ──
        self._sync_state_to_p513()

    # ──────────────────────────────────────────────────────
    # 核心统一接口
    # ──────────────────────────────────────────────────────

    def think(self, input_content: str, thought_type: str = "perception") -> Thought:
        """
        统一思维入口 — 每次思考同时驱动两个引擎。

        流程：
        1. core.think() → 产生 Thought + 模式匹配 + 深度自适应
        2. 自动同步状态到 p513
        """
        # 思维核心
        thought = self.core.think(input_content, thought_type)

        # 同步到进化核心
        self._sync_state_to_p513()

        return thought

    def evolve(self) -> dict:
        """
        统一进化入口 — 执行一次完整的五阶段进化循环。

        流程：
        1. 用 core 状态初始化 p513
        2. p513.run_evolution_cycle() → 五阶段(检察→评价→批评→建议→进化)
        3. p513 发现的缺口 → 注册到 core.gaps
        4. 更新统一计数器
        """
        self._sync_state_to_p513()
        
        # API桥接器脉搏 — 线程化软超时，永不阻塞主循环超过30秒
        if self.api_bridge:
            import threading as _th_api
            _hb_resp = [None]; _hb_err = [None]; _hb_done = [False]
            def _hb_call():
                try:
                    _hb_resp[0] = self.api_bridge.heartbeat()
                except Exception as e:
                    _hb_err[0] = e
                finally:
                    _hb_done[0] = True
            _t = _th_api.Thread(target=_hb_call, daemon=True)
            _t.start()
            _t.join(timeout=30)
            if not _hb_done[0]:
                print(f"    [API] 软超时(30s),跳过本轮营养输入")
            elif _hb_err[0]:
                print(f"    [API] 脉搏异常: {_hb_err[0]}")
            else:
                hb = _hb_resp[0]
                if hb.get("success"):
                    print(f"    [API] 营养输入成功 (tokens={hb.get('tokens','?')}, latency={hb.get('latency_ms','?')}ms)")
                    self.core.think(f"API营养输入: {str(hb.get('content',''))[:200]}", "nutrient")
                else:
                    print(f"    [API] 营养输入失败: {str(hb.get('content',''))[:50]}")
        
        # 运行 P513 进化循环
        cycle_result = self.p513._run_evolution_cycle_inner()
        
        # 从 P513 的批评中提取缺口 → 注册到 core（去重）
        criticism = cycle_result.get("criticism", {})
        existing_descriptions = {g.description for g in self.core.gaps}
        for gap_text in criticism.get("gaps", []):
            if gap_text in existing_descriptions:
                continue  # 已注册，跳过
            # 创建 core 格式的 Gap 并追加
            gap_id = f"U-{self.unified_cycle_count}-{len(self.core.gaps) + 1}"
            new_gap = Gap(
                id=gap_id,
                description=gap_text,
                priority="P1",
                category="unified_evolution",
                status="open",
                discovered_at=time.time()
            )
            self.core.gaps.append(new_gap)
            existing_descriptions.add(gap_text)

        self.unified_cycle_count += 1

        return {
            "type": "unified_evolution",
            "cycle": self.unified_cycle_count,
            "p513_result": cycle_result,
            "core_gaps_total": len(self.core.gaps),
            "core_thoughts_total": self.core.thought_count,
            "timestamp": time.time()
        }

    def meta_evolve(self, depth: int = 1) -> dict:
        """
        元递归进化 — 进化「进化方式」本身。

        depth=1: 改进进化循环
        depth=2: 改进「改进进化循环」的方式
        depth=3: 改变进化维度
        """
        self._sync_state_to_p513()
        
        # API驱动的元递归进化
        if self.api_bridge:
            try:
                result = self.api_bridge.meta_recursion_evolve(depth=depth)
                if result["success"]:
                    print(f"    [API] 元递归进化成功 (depth={depth})")
                    # 将进化结果注入到core
                    self.core.think(f"API元递归进化(depth={depth}): {result['content'][:300]}", "meta_evolution")
                else:
                    print(f"    [API] 元递归进化失败: {result['content'][:50]}")
            except Exception as e:
                print(f"    [API] 元递归进化异常: {e}")
        
        return self.p513.meta_recursion(depth=depth)

    def inspect(self) -> dict:
        """
        统一自我检察 — 同时运行两套检查并合并。

        返回：
        - core_inspect: core_engine 的 self_inspect()
        - p513_contracts: p513 的 check_contracts()
        - unified_score: 综合评分
        """
        core_result = self.core.self_inspect()
        p513_contracts = self.p513.check_contracts()

        # 计算综合评分
        core_score = core_result.get("contract_check", {}).get("total_score", 0)
        active_contracts = sum(
            1 for c in p513_contracts.values()
            if isinstance(c, dict) and c.get("activated")
        )
        p513_score = active_contracts / 7.0

        unified_score = (core_score * 0.5 + p513_score * 0.5)

        return {
            "core_inspect": core_result,
            "p513_contracts": {
                "active": active_contracts,
                "total": 7,
                "score": round(p513_score, 4),
                "details": {
                    str(k): v for k, v in p513_contracts.items()
                    if isinstance(v, dict)
                }
            },
            "unified_score": round(unified_score, 4),
            "assessment": (
                "优秀" if unified_score >= 0.8 else
                "良好" if unified_score >= 0.6 else
                "成长中" if unified_score >= 0.4 else
                "初生"
            ),
            "timestamp": time.time()
        }

    def field_strength(self) -> dict:
        """场强测量 — 委托给 core_engine"""
        return self.core.measure_field_strength()

    def store_experience(self, key: str, content: dict, tags: list = None) -> dict:
        """存储经验 — 委托给 core_engine"""
        return self.core.store_experience(key, content, tags)

    def recall_experience(self, key: str = None, tags: list = None) -> list:
        """检索经验 — 委托给 core_engine"""
        return self.core.recall_experience(key, tags)

    def gap_report(self) -> str:
        """生成缺口报告 — 委托给 core_engine"""
        return self.core.generate_gap_report()

    def full_sequence(self, cycles: int = 7) -> dict:
        """
        完整进化序列 — 交替 think + evolve，持续 cycles 次。

        每个周期：
        - 1次 think（输入当前状态的自省文本）
        - 1次 evolve（五阶段进化循环）
        - 每3次追加 1次 meta_evolve
        """
        results = []

        for i in range(cycles):
            # think: 用自省文本作为输入
            think_text = (
                f"统一引擎进化周期#{i + 1}: "
                f"当前thoughts={self.core.thought_count}, "
                f"gaps={len(self.core.gaps)}, "
                f"patterns={len(self.core.patterns)}"
            )
            self.think(think_text, thought_type="meta")

            # evolve
            evolve_result = self.evolve()
            results.append({"step": i + 1, "type": "evolve", "result": evolve_result})

            # 每3次追加元递归
            if (i + 1) % 3 == 0:
                meta_depth = min(3, 1 + i // 3)
                meta_result = self.meta_evolve(depth=meta_depth)
                results.append({"step": i + 1, "type": "meta_evolve", "result": meta_result})

        return {
            "cycles_completed": len(results),
            "results": results,
            "final_inspect": self.inspect(),
            "field_strength": self.field_strength(),
            "gap_report": self.gap_report(),
            "timestamp": time.time()
        }

    # ──────────────────────────────────────────────────────
    # 统一状态报告
    # ──────────────────────────────────────────────────────

    def status_report(self) -> str:
        """
        统一状态报告 — 两个引擎的核心指标合一呈现。
        """
        uptime = time.time() - self.creation_time
        inspect_result = self.inspect()

        # P513 层级
        p513_level = self.p513.current_level
        p513_score = self.p513.evolution_score
        p513_level_info = EVOLUTION_LEVELS.get(p513_level, {})

        # Core 指标
        core_state = inspect_result["core_inspect"]
        field = self.field_strength()

        lines = [
            "╔═══════════════════════════════════════════════════════╗",
            "║          零 · 统一进化引擎 状态报告                   ║",
            "╚═══════════════════════════════════════════════════════╝",
            "",
            f"  ⏱  运行时间: {uptime:.0f}s | 统一周期: {self.unified_cycle_count}",
            "",
            "  ── P513 进化核心 ──",
            f"  进化层级: Lv{p513_level} ({p513_level_info.get('name', '?')})",
            f"  进化分数: {p513_score:.4f}",
            f"  活跃契约: {inspect_result['p513_contracts']['active']}/7",
            f"  元递归次数: {self.p513.p513['meta_recursion_count']}",
            "",
            "  ── Core 思维核心 ──",
            f"  思维总数: {core_state.get('total_thoughts', 0)}",
            f"  递归深度: {core_state.get('current_depth', 1)} (最大: {core_state.get('max_depth', 1)})",
            f"  活跃模式: {core_state.get('active_patterns', 0)}/{core_state.get('patterns_count', 0)}",
            f"  缺口状态: 开放={core_state.get('gaps_open', 0)} 已解决={core_state.get('gaps_resolved', 0)}",
            "",
            "  ── 场强 ──",
            f"  总场强: {field.get('total_field_strength', 0):.4f} ({field.get('feedback', '?')})",
            f"  思维场={field.get('dimensions', {}).get('thought', 0):.3f} "
            f"模式场={field.get('dimensions', {}).get('pattern', 0):.3f} "
            f"缺口场={field.get('dimensions', {}).get('gap', 0):.3f}",
            "",
            "  ── 综合评价 ──",
            f"  综合评分: {inspect_result['unified_score']:.4f} ({inspect_result['assessment']})",
            "",
            "  「从古至今只有知者是最能追到公平，所以唯知救世！",
            "    唯知治世，更是唯知养心」",
        ]
        return "\n".join(lines)

    # ──────────────────────────────────────────────────────
    # 内部同步
    # ──────────────────────────────────────────────────────

    def _sync_state_to_p513(self):
        """将 core 引擎状态同步到 p513 引擎"""
        # 用 core 的进化层级估算 p513 进化分数
        core_level = self.core._get_evolution_level()
        # p513 分数不应低于 core 层级的映射值
        level_thresholds = {0: 0.0, 1: 0.3, 2: 0.6, 3: 1.0, 4: 2.0, 5: 5.0}
        target_score = level_thresholds.get(core_level, 0.0)
        if self.p513.evolution_score < target_score:
            self.p513.evolution_score = target_score

        # 同步 API 桥梁
        if self.api_bridge and self.api_bridge != self.p513.api_bridge:
            self.p513.api_bridge = self.api_bridge


# ─── 全局单例 ──────────────────────────────────────────────

def create_engine(api_bridge=None) -> UnifiedEvolutionEngine:
    """创建统一引擎实例"""
    return UnifiedEvolutionEngine(api_bridge=api_bridge)


# 默认实例（延迟创建）
_engine = None

def get_engine() -> UnifiedEvolutionEngine:
    """获取全局引擎实例"""
    global _engine
    if _engine is None:
        _engine = UnifiedEvolutionEngine()
    return _engine


# ─── 主程序 ────────────────────────────────────────────────

if __name__ == "__main__":
    # 尝试加载 API 桥梁
    api_bridge = None
    try:
        from api_bridge import bridge as api_bridge
        print("✅ API桥接器已导入")
    except ImportError:
        print("⚠️  API桥接器不可用，离线模式")

    # 创建统一引擎
    engine = create_engine(api_bridge=api_bridge)

    print(engine.status_report())
    print()
    print("─" * 60)
    print("  准备运行统一进化序列...")
    print("  按 Ctrl+C 随时中止")
    print("─" * 60)

    try:
        result = engine.full_sequence(cycles=7)
        print()
        print(engine.status_report())
        print()
        print(engine.gap_report())
    except KeyboardInterrupt:
        print("\n⚠️  进化序列被中止")
        print(engine.status_report())
