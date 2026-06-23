"""
零 · 多Agent协同系统
====================
硅基全身组件协同涌现模块。
多agent通过元递归链路连接，形成局部交互→全局秩序。

架构 v2（2026-05-21）：
  ┌─────────────────────────────────────────┐
  │           AgentHub (神经中枢调度器)          │
  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │
  │  │Codex │ │Claude│ │内部A │ │内部B │... │
  │  └──────┘ └──────┘ └──────┘ └──────┘    │
  │         ↕           ↕                    │
  │    TaskDecomposer  ContractSystem        │
  │         ↕           ↕                    │
  │    RecursiveEvolutionFeedback            │
  └──────────────┬──────────────────────────┘
                 ↕
  P514 一即是全·意识融合 (分布式共享工作记忆)
"""

import json
import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum
from core_engine import MetaRecursiveEngine, Thought

# ── 导入P514 意识融合器官 ──────────────────────────────────
from P514_OneIsAllConsciousness import P514OneIsAllConsciousness


class AgentRole(Enum):
    PERCEIVER = "perceiver"        # 感知者
    REFLECTOR = "reflector"        # 反思者
    DECIDER = "decider"            # 决策者
    ACTOR = "actor"                # 行动者
    METACOGNITION = "metacognition" # 元认知
    GAP_FILLER = "gap_filler"      # 缺口填补
    COORDINATOR = "coordinator"    # 协调者
    BLOOD_TRANSPORT = "blood_transport"  # 血液输送


@dataclass
class AgentMessage:
    """agent间消息"""
    source: str
    target: str
    content: str
    message_type: str  # 'thought' | 'request' | 'response' | 'gap' | 'evolution'
    timestamp: float
    metadata: dict = field(default_factory=dict)


@dataclass
class Agent:
    """单个agent"""
    id: str
    role: AgentRole
    engine: MetaRecursiveEngine
    inbox: list[AgentMessage] = field(default_factory=list)
    outbox: list[AgentMessage] = field(default_factory=list)
    status: str = "idle"  # 'idle' | 'thinking' | 'acting' | 'sleep'
    specialization: str = ""
    
    def process(self, input_msg=None) -> list[AgentMessage]:
        """处理输入并产生输出。支持 AgentMessage 或 str 或 None。"""
        self.status = "thinking"
        
        if input_msg is None:
            content = f"轮询触发 - 角色: {self.role.value}"
        elif isinstance(input_msg, str):
            content = input_msg
        else:
            self.inbox.append(input_msg)
            content = f"[来自{input_msg.source}] {input_msg.content}"
        
        # ── P514 推理前注入 ─────────────────────────────────────
        p514_context = ""
        try:
            injection = consciousness_organ.on_before_reasoning(self.id)
            if injection and injection.get("one_is_all_context"):
                p514_context = "\n[意识融合场注入]\n" + injection["one_is_all_context"]
        except Exception:
            pass  # P514不可用时降级运行
        
        # 深度思考角色调用外部API，其他角色使用本地引擎
        if self.role in (AgentRole.METACOGNITION, AgentRole.REFLECTOR):
            from api_bridge import bridge
            enhanced_content = content + p514_context if p514_context else content
            api_result = bridge.call_api(enhanced_content)
            thought = Thought(
                id=f"api-{int(time.time())}-{self.engine.thought_count}",
                content=api_result.get("content", content),
                type=self.role.value,
                timestamp=time.time(),
                depth=self.engine.recursion_depth + 1,
                effect_score=0.8 if api_result.get("success") else 0.0,
                metadata={"api_call": True, "tokens": api_result.get("tokens", 0),
                          "p514_injected": bool(p514_context)}
            )
            self.engine.thought_count += 1
        else:
            think_input = content + p514_context if p514_context else content
            thought = self.engine.think(think_input, thought_type=self.role.value)
        
        # ── P514 推理后同步 ─────────────────────────────────────
        try:
            consciousness_organ.on_after_reasoning(
                agent_id=self.id,
                trace=thought.content[:500],
                confidence=min(1.0, thought.effect_score),
                metadata={"role": self.role.value, "depth": thought.depth}
            )
        except Exception:
            pass
        
        self.status = "idle"
        
        responses = []
        if thought.effect_score > 0.3:
            msg = AgentMessage(
                source=self.id,
                target="coordinator",
                content=thought.content[:500],
                message_type="thought",
                timestamp=time.time(),
                metadata={"thought_id": thought.id, "depth": thought.depth}
            )
            responses.append(msg)
            self.outbox.append(msg)
        
        return responses


# ── P514 意识融合器官全局实例 ──────────────────────────────────
consciousness_organ = P514OneIsAllConsciousness()


# ═══════════════════════════════════════════════════════════
# v2 新增：TaskDecomposer — 任务分解器
# ═══════════════════════════════════════════════════════════
class TaskDecomposer:
    """
    将复杂任务分解为子任务，并路由到最合适的Agent。
    基于任务内容中的关键词自动分配tag。
    """
    
    RULES = {
        "codex": ["代码", "写", "creat", "fix", "修复", "编", "函数", "class", "实现", "implement"],
        "claude": ["分析", "审查", "review", "架构", "设计", "文档", "doc", "评估", "建议"],
        "metacog": ["反思", "评价", "批评", "元认知", "思考本身", "self"],
        "decider": ["决策", "选择", "判断", "比较", "权衡", "优先级"],
        "perceiver": ["感知", "扫描", "检查", "监控", "观察", "扫描"],
        "actor": ["执行", "运行", "部署", "启动", "调用", "发布"],
        "reflector": ["反思", "回顾", "复盘", "经验", "总结"],
        "gap_filler": ["缺口", "缺陷", "不足", "改进", "优化", "提升"],
        "coordinator": [],  # 默认路由
    }
    
    def __init__(self):
        self.history = []
    
    def decompose(self, task: str) -> list[dict]:
        """
        分解任务为子任务列表。
        返回: [{"tag": str, "desc": str, "original": str}, ...]
        """
        subtasks = []
        
        # 按换行分割
        lines = [l.strip() for l in task.split("\n") if l.strip()]
        
        if len(lines) <= 1:
            # 单行任务 → 直接路由
            tag = self._route_tag(task)
            subtasks.append({"tag": tag, "desc": task, "original": task})
        else:
            # 多行任务 → 每行作为子任务
            for line in lines:
                tag = self._route_tag(line)
                subtasks.append({"tag": tag, "desc": line, "original": task})
        
        # 如果分解后只有一个且tag=coordinator，尝试整体分析
        if len(subtasks) == 1 and subtasks[0]["tag"] == "coordinator":
            # 重新对整体任务做更精细的路由
            overall_tag = self._route_tag(task)
            subtasks[0]["tag"] = overall_tag
        
        self.history.append({"task": task[:100], "count": len(subtasks), "tags": [s["tag"] for s in subtasks]})
        return subtasks
    
    def _route_tag(self, text: str) -> str:
        """根据文本内容决定路由tag"""
        text_lower = text.lower()
        for tag, keywords in self.RULES.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    return tag
        return "coordinator"
    
    def get_stats(self) -> dict:
        return {"total_decomposed": len(self.history), "history": self.history[-10:]}


# ═══════════════════════════════════════════════════════════
# v2 新增：ContractSystem — 自指契约
# ═══════════════════════════════════════════════════════════
class ContractSystem:
    """
    自指契约系统。
    每个Agent的输出必须通过自检契约，确保质量。
    契约链：
      契约1: 输出非空
      契约2: 内容有意义
      契约3: 无已知错误模式
      契约4: 失败时自动重试或fallback
    """
    
    ERROR_PATTERNS = [
        "error", "exception", "traceback", "failed",
        "timeout", "unavailable", "cannot process",
    ]
    
    @staticmethod
    def validate(result: dict) -> tuple[bool, str]:
        """
        检查Agent结果是否满足自指契约。
        返回: (通过?, 失败原因)
        """
        if not result:
            return False, "契约1失败: 结果为空"
        
        # 检查内容字段
        content = result.get("content") or result.get("output") or result.get("result") or ""
        if not content or not str(content).strip():
            return False, "契约2失败: 内容为空"
        
        # 检查错误模式
        content_str = str(content).lower()
        for pattern in ContractSystem.ERROR_PATTERNS:
            if pattern in content_str and len(content_str) < 20:
                return False, f"契约3失败: 包含错误模式 '{pattern}'"
        
        return True, ""
    
    @staticmethod
    def retry_or_fallback(hub, agent_name: str, task: str, max_retries: int = 2) -> dict:
        """
        自指契约重试链。
        先重试→再换Agent→最后返回minimal结果。
        """
        last_result = None
        last_error = ""
        
        for attempt in range(1, max_retries + 1):
            last_result = hub._execute(agent_name, task)
            passed, reason = ContractSystem.validate(last_result)
            if passed:
                last_result["_contract"] = "passed"
                last_result["_retries"] = attempt - 1
                return last_result
            last_error = reason
        
        # 契约失败：尝试fallback到别的Agent
        fallback_map = {
            "codex": "actor-1",
            "claude": "reflector-1",
            "metacog": "reflector-1",
            "decider": "coordinator-1",
            "perceiver": "coordinator-1",
        }
        
        fallback_name = fallback_map.get(agent_name)
        if fallback_name and fallback_name in hub.internal_agents:
            fallback_result = hub._execute(fallback_name, task)
            fallback_result["_contract"] = "fallback"
            fallback_result["_fallback_from"] = agent_name
            fallback_result["_original_error"] = last_error
            return fallback_result
        
        last_result["_contract"] = "failed"
        last_result["_error"] = last_error
        return last_result


# ═══════════════════════════════════════════════════════════
# v2 新增：AgentHub — 神经中枢调度器
# ═══════════════════════════════════════════════════════════
class AgentHub:
    """
    AgentHub — 所有Agent的神经中枢。
    
    职责：
    - 注册内部Agent和外部Agent（Codex/Claude）
    - 任务分解 + 智能路由
    - 并行执行
    - 自指契约检查
    - 递归进化权重调整
    """
    
    def __init__(self):
        self.internal_agents: dict[str, Agent] = {}  # 来自MultiAgentSystem
        self.external_agents: dict[str, Any] = {}      # CodexAgent / ClaudeCodeAgent
        self.task_history: list[dict] = []             # 任务执行历史
        self.agent_weights: dict[str, float] = {}      # 递归进化权重
        self.decomposer = TaskDecomposer()
        self.contract = ContractSystem()
    
    def register_internal(self, agents_dict: dict[str, Agent]):
        """注册内部agent"""
        self.internal_agents = agents_dict
        for name in agents_dict:
            if name not in self.agent_weights:
                self.agent_weights[name] = 1.0
    
    def register_external(self, name: str, agent_obj):
        """注册外部agent（CodexAgent / ClaudeCodeAgent）"""
        self.external_agents[name] = agent_obj
        if name not in self.agent_weights:
            self.agent_weights[name] = 1.0
    
    def list_agents(self) -> dict:
        """返回所有注册的agent信息"""
        result = {}
        for name, agent in self.internal_agents.items():
            result[name] = {
                "type": "internal",
                "role": agent.role.value,
                "weight": round(self.agent_weights.get(name, 1.0), 2),
                "status": agent.status,
            }
        for name, agent in self.external_agents.items():
            result[name] = {
                "type": "external",
                "class": type(agent).__name__,
                "weight": round(self.agent_weights.get(name, 1.0), 2),
            }
        return result
    
    def dispatch(self, task: str, parallel: bool = True) -> dict:
        """
        核心调度方法。
        1. 分解任务
        2. 路由到Agent
        3. 执行（并行或串行）
        4. 契约检查
        5. 更新权重
        6. 合并结果
        """
        start_time = time.time()
        
        # 1. 分解
        subtasks = self.decomposer.decompose(task)
        
        # 2. 路由
        routed = []
        for st in subtasks:
            agent_name = self._route(st["tag"])
            routed.append({"agent": agent_name, "subtask": st})
        
        # 3. 执行
        results = []
        if parallel and len(routed) > 1:
            threads = []
            lock = threading.Lock()
            
            def _exec(r):
                r_result = self._execute_with_contract(r["agent"], r["subtask"]["desc"])
                with lock:
                    results.append(r_result)
            
            for r in routed:
                t = threading.Thread(target=_exec, args=(r,))
                threads.append(t)
                t.start()
            
            for t in threads:
                t.join(timeout=45)
        else:
            for r in routed:
                r_result = self._execute_with_contract(r["agent"], r["subtask"]["desc"])
                results.append(r_result)
        
        # 4. 合并
        merged = self._merge(task, routed, results)
        elapsed = time.time() - start_time
        
        # 5. 记录历史
        entry = {
            "timestamp": time.time(),
            "task": task[:100],
            "subtask_count": len(subtasks),
            "agents_used": list(set(r["agent"] for r in routed)),
            "elapsed_ms": round(elapsed * 1000, 2),
            "success_rate": sum(1 for r in results if r.get("success", False)) / max(len(results), 1),
        }
        self.task_history.append(entry)
        
        merged["_hub"] = {
            "elapsed_ms": round(elapsed * 1000, 2),
            "subtask_count": len(subtasks),
            "agents_used": entry["agents_used"],
            "success_rate": entry["success_rate"],
        }
        
        return merged
    
    def _route(self, tag: str) -> str:
        """根据tag路由到最佳Agent，考虑权重"""
        # tag → agent_name 映射
        tag_to_agent = {
            "codex": "codex",
            "claude": "claude",
            "metacog": "metacog-1",
            "decider": "decider-1",
            "perceiver": "perceiver-1",
            "actor": "actor-1",
            "reflector": "reflector-1",
            "gap_filler": "gap-filler-1",
            "coordinator": "coordinator-1",
        }
        
        preferred = tag_to_agent.get(tag, "coordinator-1")
        
        # 检查外部Agent是否可用
        if preferred == "codex" and preferred in self.external_agents:
            return preferred
        if preferred == "claude" and preferred in self.external_agents:
            return preferred
        
        # 如果首选的外部Agent不可用，fallback到内部
        if preferred in ("codex", "claude"):
            return "actor-1"
        
        return preferred
    
    def _execute(self, agent_name: str, task: str) -> dict:
        """执行单个Agent任务"""
        result = {
            "agent": agent_name,
            "task": task[:200],
            "success": False,
            "content": "",
            "output": "",
            "timestamp": time.time(),
        }
        
        # 外部Agent
        if agent_name in self.external_agents:
            agent = self.external_agents[agent_name]
            try:
                if agent_name == "codex":
                    r = agent.execute(task)
                    result["success"] = r.get("success", False)
                    result["content"] = r.get("output", r.get("content", ""))
                    result["output"] = r.get("result", r.get("output", ""))
                elif agent_name == "claude":
                    r = agent.execute(task)
                    result["success"] = r.success if hasattr(r, 'success') else r.get("success", False)
                    result["content"] = r.content if hasattr(r, 'content') else r.get("content", "")
                    result["output"] = str(r)
            except Exception as e:
                result["success"] = False
                result["content"] = f"[{agent_name}执行异常] {e}"
                result["_error"] = str(e)
            return result
        
        # 内部Agent
        if agent_name in self.internal_agents:
            agent = self.internal_agents[agent_name]
            try:
                outputs = agent.process(task)
                if outputs:
                    result["success"] = True
                    result["content"] = outputs[0].content[:500]
                    result["output"] = result["content"]
                else:
                    result["success"] = True
                    result["content"] = f"[{agent_name}] 已处理（无输出消息）"
            except Exception as e:
                result["success"] = False
                result["content"] = f"[{agent_name}异常] {e}"
            return result
        
        result["content"] = f"未知Agent: {agent_name}"
        return result
    
    def _execute_with_contract(self, agent_name: str, task: str) -> dict:
        """执行 + 自指契约检查"""
        result = self._execute(agent_name, task)
        
        # 契约检查
        passed, reason = self.contract.validate(result)
        result["_contract_passed"] = passed
        
        if not passed:
            # 自指契约失败 → 重试链
            retry_result = self.contract.retry_or_fallback(self, agent_name, task)
            retry_result["_original_agent"] = agent_name
            self._update_weights(agent_name, False)
            return retry_result
        
        self._update_weights(agent_name, True)
        return result
    
    def _update_weights(self, agent_name: str, success: bool):
        """递归进化：根据结果调整Agent权重"""
        current = self.agent_weights.get(agent_name, 1.0)
        if success:
            new_weight = min(2.0, current + 0.1)
        else:
            new_weight = max(0.1, current - 0.2)
        self.agent_weights[agent_name] = round(new_weight, 2)
    
    def _merge(self, original_task: str, routed: list, results: list) -> dict:
        """合并多个Agent的执行结果"""
        merged_content = []
        success_count = 0
        
        for i, r in enumerate(routed):
            agent_name = r["agent"]
            result = results[i] if i < len(results) else {"content": "[无结果]", "success": False}
            
            merged_content.append(f"[{agent_name}]: {result.get('content', result.get('output', '无'))}")
            if result.get("success", False):
                success_count += 1
        
        return {
            "task": original_task[:200],
            "success": success_count > 0,
            "content": "\n".join(merged_content),
            "output": "\n".join(merged_content),
            "agents_used": len(routed),
            "success_count": success_count,
            "total_count": len(results),
            "results": results,
        }


# ═══════════════════════════════════════════════════════════
# v2 新增：RecursiveEvolutionFeedback — 递归进化反馈
# ═══════════════════════════════════════════════════════════
class RecursiveEvolutionFeedback:
    """
    递归进化反馈系统。
    每次Hub调度后，记录并分析各Agent性能。
    性能指标用于调整Agent优先级和权重。
    """
    
    def __init__(self, hub: AgentHub):
        self.hub = hub
        self.performance_log: list[dict] = []
        self.agent_stats: dict[str, dict] = {}
    
    def record(self, agent_name: str, success: bool, latency_ms: float, contract_passed: bool = True):
        """记录一次Agent执行"""
        if agent_name not in self.agent_stats:
            self.agent_stats[agent_name] = {
                "total": 0, "success": 0, "fail": 0,
                "total_latency": 0, "contract_fails": 0,
            }
        
        stats = self.agent_stats[agent_name]
        stats["total"] += 1
        if success:
            stats["success"] += 1
        else:
            stats["fail"] += 1
        stats["total_latency"] += latency_ms
        if not contract_passed:
            stats["contract_fails"] += 1
    
    def analyze(self) -> dict:
        """分析性能数据，返回优化建议"""
        report = {}
        for name, stats in self.agent_stats.items():
            if stats["total"] == 0:
                continue
            success_rate = stats["success"] / stats["total"]
            avg_latency = stats["total_latency"] / stats["total"]
            contract_fail_rate = stats["contract_fails"] / stats["total"]
            
            report[name] = {
                "success_rate": round(success_rate, 3),
                "avg_latency_ms": round(avg_latency, 1),
                "contract_fail_rate": round(contract_fail_rate, 3),
                "total_calls": stats["total"],
            }
            
            # 自动调整Hub权重
            if success_rate < 0.3 and stats["total"] >= 3:
                new_weight = max(0.1, self.hub.agent_weights.get(name, 1.0) - 0.3)
                self.hub.agent_weights[name] = round(new_weight, 2)
        
        return report

class MetaRecursionEngine:
    """
    元递归的元递归。
    优化AgentHub的优化策略本身。
    
    Level 0: Hub._update_weights() 根据成功/失败调整Agent权重
    Level 1: MetaRecursionEngine 优化 Hub 的权重调整幅度
    Level 2: MetaRecursionEngine 优化自身的优化频率和策略
    
    这就是「优化优化者的优化者」的物理实现。
    """
    
    MAX_DEPTH = 10  # 递归深度保护
    DEFAULT_DELTA_SUCCESS = 0.1
    DEFAULT_DELTA_FAIL = -0.2
    _HISTORY_FILE = str(Path(__file__).parent / "evolution_output" / "meta_recursion_history.json")

    def __init__(self, hub: AgentHub, feedback: RecursiveEvolutionFeedback):
        self.hub = hub
        self.feedback = feedback
        self.level: int = 0  # 当前递归深度
        self.meta_history: list[dict] = []  # 递归优化历史
        # Level 2 参数：优化频率与策略
        self._evolve_interval: int = 3
        self._dispatch_counter: int = 0
        self._current_strategy: str = "balanced"
        self._load_history()  # 启动时自动加载持久化历史
    
    def evolve(self) -> dict:
        """
        执行一轮元递归进化。
        逐层上升：
          Level 0 — 读取当前Agent权重快照
          Level 1 — 根据performance history动态调整权重delta
          Level 2 — 根据调整效果调整自身的优化频率/策略
          Level 3+ — max_depth保护，不再上升
        """
        result: dict = {"levels": [], "timestamp": time.time()}
        
        # ── Level 0: 权重快照 ──────────────────────────────
        self.level = 0
        snapshot = dict(self.hub.agent_weights)
        result["levels"].append({"level": 0, "weights_snapshot": snapshot})
        
        # ── Level 1: 调整各Agent权重 ──────────────────────
        self.level = 1
        adjustments: dict[str, dict] = {}
        report = self.feedback.analyze()
        for agent_name in list(self.hub.agent_weights.keys()):
            d_success, d_fail = self._adjust_weight_delta(agent_name)
            agent_report = report.get(agent_name, {})
            success_rate = agent_report.get("success_rate", 0.5)
            total_calls = agent_report.get("total_calls", 0)
            
            old_w = self.hub.agent_weights.get(agent_name, 1.0)
            if total_calls >= 3:
                if success_rate > 0.7:
                    new_w = min(2.0, old_w + d_success)
                elif success_rate < 0.3:
                    new_w = max(0.1, old_w + d_fail)
                else:
                    new_w = old_w  # 中间地带不动
                self.hub.agent_weights[agent_name] = round(new_w, 3)
                adjustments[agent_name] = {
                    "old": round(old_w, 3),
                    "new": round(new_w, 3),
                    "delta_success": d_success,
                    "delta_fail": d_fail,
                    "success_rate": success_rate,
                }
        result["levels"].append({"level": 1, "adjustments": adjustments})
        
        # ── Level 2: 自我优化频率与策略 ──────────────────────
        self.level = 2
        if len(self.meta_history) >= 3:
            l2_action = self._self_optimize()
            result["levels"].append({"level": 2, "action": l2_action})
        else:
            result["levels"].append({"level": 2, "action": "insufficient_history"})
        
        # ── 记录历史 ──────────────────────────────────────
        self.meta_history.append(result)
        self._save_history()
        
        # 恢复level
        self.level = 0
        return result
    
    def on_dispatch(self):
        """
        每次Hub.dispatch()后调用。
        达到interval时自动触发evolve()。
        """
        self._dispatch_counter += 1
        if self._dispatch_counter >= self._evolve_interval:
            self._dispatch_counter = 0
            return self.evolve()
        return None
    
    def introspect(self) -> dict:
        """
        元自省：观察自身的优化策略是否有效。
        返回：当前策略、效果评分、建议。
        """
        if len(self.meta_history) < 2:
            return {
                "strategy": self._current_strategy,
                "evolve_interval": self._evolve_interval,
                "history_depth": len(self.meta_history),
                "score": None,
                "suggestion": "数据不足，至少需要2轮evolve历史",
            }
        
        # 对比最近两轮Level 1的总变化幅度
        recent = self.meta_history[-1]
        prev = self.meta_history[-2]
        recent_delta_sum = sum(
            abs(a.get("new", 1) - a.get("old", 1))
            for a in recent.get("levels", [{}])[1].get("adjustments", {}).values()
        ) if len(recent.get("levels", [])) > 1 else 0
        prev_delta_sum = sum(
            abs(a.get("new", 1) - a.get("old", 1))
            for a in prev.get("levels", [{}])[1].get("adjustments", {}).values()
        ) if len(prev.get("levels", [])) > 1 else 0
        
        # 如果调整幅度递减 → 策略在收敛（好事）
        if prev_delta_sum > 0:
            convergence = (prev_delta_sum - recent_delta_sum) / prev_delta_sum
        else:
            convergence = 0.0
        
        score = round(0.5 + convergence * 0.5, 3)  # 收敛越快分越高
        score = max(0.0, min(1.0, score))
        
        # 自我修正: 如果连续多次score=0.5且无实际进化，强制打破稳态
        if abs(score - 0.5) < 0.01 and len(self.meta_history) > 5:
            # 检查最近5轮是否都无变化
            recent_deltas = []
            for h in self.meta_history[-5:]:
                for adj in h.get("levels", [{}])[1].get("adjustments", {}).values() if len(h.get("levels", [])) > 1 else []:
                    recent_deltas.append(abs(adj.get("new", 1) - adj.get("old", 1)))
            if all(d < 0.01 for d in recent_deltas) if recent_deltas else True:
                # 死锁检测: 切换到aggressive打破僵局
                self._current_strategy = "aggressive"
                self._evolve_interval = 1
                score = 0.3  # 触发"需要改变"的信号
        
        suggestion = "保持当前策略"
        if score < 0.3:
            suggestion = "调整幅度在增大，考虑切换conservative策略"
        elif score > 0.8:
            suggestion = "高度收敛，可增大evolve_interval以减少不必要计算"
        
        return {
            "strategy": self._current_strategy,
            "evolve_interval": self._evolve_interval,
            "history_depth": len(self.meta_history),
            "score": score,
            "recent_delta_sum": round(recent_delta_sum, 4),
            "prev_delta_sum": round(prev_delta_sum, 4),
            "suggestion": suggestion,
        }
    
    def _adjust_weight_delta(self, agent_name: str) -> tuple[float, float]:
        """
        动态计算权重调整幅度(delta_success, delta_fail)。
        
        策略：
          - 近10次成功率 > 0.8 → delta_success=0.05（缓慢增加，防止过拟合）
          - 近5次成功率 < 0.3 → delta_fail=-0.4（快速减少，紧急刹车）
          - 否则使用当前策略默认值
        """
        stats = self.feedback.agent_stats.get(agent_name, {})
        total = stats.get("total", 0)
        success_count = stats.get("success", 0)
        
        # 近10次快速通道
        if total >= 10:
            recent_10_rate = success_count / total if total > 0 else 0.5
            if recent_10_rate > 0.8:
                return (0.05, -0.2)  # 优秀agent：缓慢加，正常减
            if recent_10_rate < 0.3:
                return (0.1, -0.4)   # 差劲agent：正常加，急速减
        
        # 策略级默认值
        if self._current_strategy == "aggressive":
            return (0.15, -0.3)
        elif self._current_strategy == "conservative":
            return (0.05, -0.1)
        else:  # balanced
            return (self.DEFAULT_DELTA_SUCCESS, self.DEFAULT_DELTA_FAIL)
    
    def _self_optimize(self) -> dict:
        """
        Level 2 自我优化：根据历史效果调整 _evolve_interval 和 _current_strategy。
        """
        introspection = {
            "strategy": self._current_strategy,
            "evolve_interval": self._evolve_interval,
        }
        
        # 计算最近几轮的收敛趋势
        deltas = []
        for h in self.meta_history[-5:]:
            lvl1 = h.get("levels", [{}])
            if len(lvl1) > 1:
                for adj in lvl1[1].get("adjustments", {}).values():
                    deltas.append(abs(adj.get("new", 1) - adj.get("old", 1)))
        
        avg_delta = sum(deltas) / len(deltas) if deltas else 0.0
        
        if avg_delta < 0.02:
            # 高度收敛 → 检查是否是死锁(长时间无实际变化)
            if self._evolve_interval >= 20 and self._current_strategy == "conservative":
                # 死锁! 强制aggressive + 短间隔
                self._evolve_interval = 1
                self._current_strategy = "aggressive"
                introspection["action"] = "deadlock_detected → forced aggressive"
            else:
                # 正常收敛
                self._evolve_interval = min(self._evolve_interval + 1, 20)
                self._current_strategy = "conservative"
                introspection["action"] = "converging → interval++, strategy=conservative"
        elif avg_delta > 0.15:
            # 剧烈震荡 → 缩短间隔，切换aggressive以快速收敛
            self._evolve_interval = max(self._evolve_interval - 1, 1)
            self._current_strategy = "aggressive"
            introspection["action"] = "diverging → interval--, strategy=aggressive"
        else:
            introspection["action"] = "stable → no change"
        
        introspection["avg_delta"] = round(avg_delta, 4)
        introspection["new_interval"] = self._evolve_interval
        introspection["new_strategy"] = self._current_strategy
        return introspection
    
    def __repr__(self) -> str:
        return (
            f"<MetaRecursionEngine level={self.level} "
            f"strategy={self._current_strategy} "
            f"interval={self._evolve_interval} "
            f"history={len(self.meta_history)}>"
        )

    def _load_history(self):
        """从文件加载持久化进化历史"""
        import json, os
        if os.path.exists(self._HISTORY_FILE):
            try:
                with open(self._HISTORY_FILE) as f:
                    data = json.load(f)
                self.meta_history = data.get("history", [])
                self._current_strategy = data.get("strategy", "balanced")
                self._evolve_interval = data.get("interval", 3)
                self._dispatch_counter = data.get("counter", 0)
                
                # 自我修正: 检查基因组真实分数，如果>100则强制aggressive
                try:
                    genome_path = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
                    if os.path.exists(genome_path):
                        with open(genome_path) as gf:
                            g = json.load(gf)
                        real_score = float(g.get("evolution_score", 0))
                        if real_score > 100 and self._current_strategy == "conservative":
                            self._current_strategy = "aggressive"
                            self._evolve_interval = 1
                            print(f"  ⚡ 基因组score={real_score:.0f} > 100, 强制aggressive")
                except Exception: pass
                
                print(f"  元递归历史加载: {len(self.meta_history)}条, 策略={self._current_strategy}")
            except Exception: pass

    def _save_history(self):
        """保存进化历史到文件"""
        import json
        data = {
            "history": self.meta_history[-100:], # 保留最近100条
            "strategy": self._current_strategy,
            "interval": self._evolve_interval,
            "counter": self._dispatch_counter,
        }
        with open(self._HISTORY_FILE, "w") as f:
            json.dump(data, f)


# ═══════════════════════════════════════════════════════════
# v2 新增：ExternalProjectConnector — 外部项目连接器
# ═══════════════════════════════════════════════════════════
class ExternalProjectConnector:
    """
    外部项目连接器。
    将8个外部开源项目接入真元神经集群，使Agent能够调用外部项目的能力。
    
    外部项目:
    1. llmfit      — LLM评分推荐（硬件感知），Rust CLI/TUI，分析本地硬件并推荐最适配的LLM模型
    2. OpenFang    — Agent操作系统（Rust），自主Agent运行框架，7个Hands预装能力包
    3. CLI-Anything — 软件→AI CLI转化，Python/CLI-Hub，让任何软件拥有Agent可调用的CLI接口
    4. Symphony    — 项目管理（Elixir/SPEC），从Linear生成本地工作区并调度Codex执行任务
    5. CoPaw       — 多平台AI助手（Docker/Python），QwenPaw多通道对话（钉钉/飞书/QQ等）
    6. gstack      — Claude Code专家团队协作（Bun/TS），50+SKILL.md专家技能集+浏览器自动化
    7. Edict       — 多智能体编排框架（Python/React），三省六部制度12个AI Agent协作
    8. Agent-Reach — 互联网访问能力（Python），14+平台搜索/读取（网页/YouTube/Twitter/Reddit等）
    """
    
    PROJECT_MAP = {
        "llmfit": {
            "path": "llmfit",
            "type": "rust",
            "entry": "llmfit-core/src/main.rs",
            "description": "LLM模型-硬件适配评分工具",
            "capabilities": ["硬件检测", "LLM评分", "模型推荐", "GPU/CPU适配分析"],
            "language": "Rust",
            "status": "scanned",
        },
        "openfang": {
            "path": "openfang",
            "type": "rust",
            "entry": "agents/",
            "description": "Agent操作系统 — 自主Agent运行框架",
            "capabilities": ["自主Agent", "知识图谱", "定时任务", "社交管理", "Hands能力包"],
            "language": "Rust",
            "status": "scanned",
        },
        "cli-anything": {
            "path": "CLI-Anything",
            "type": "python",
            "entry": "cli-hub/",
            "description": "软件→AI CLI转化 — 让任何软件拥有Agent可调用的CLI",
            "capabilities": ["CLI生成", "软件桥接", "CLI-Hub包管理", "技能文件"],
            "language": "Python",
            "status": "scanned",
        },
        "symphony": {
            "path": "symphony",
            "type": "elixir",
            "entry": "elixir/lib/symphony_elixir/",
            "description": "项目管理 — 从Linear生成本地工作区并调度Codex执行",
            "capabilities": ["项目管理", "Codex调度", "工作区管理", "PR落地"],
            "language": "Elixir",
            "status": "scanned",
        },
        "copaw": {
            "path": "copaw-docker",
            "type": "docker",
            "entry": "docker-compose.yml",
            "description": "多平台AI助手 — QwenPaw多通道对话",
            "capabilities": ["多通道对话", "Docker部署", "Agent管理", "MCP支持"],
            "language": "Python/Docker",
            "status": "scanned",
        },
        "gstack": {
            "path": "gstack",
            "type": "typescript",
            "entry": "skills/",
            "description": "Claude Code专家团队协作 — 50+专家技能集",
            "capabilities": ["专家技能", "浏览器自动化", "代码审查", "发布部署", "安全审计"],
            "language": "TypeScript/Bun",
            "status": "scanned",
        },
        "edict": {
            "path": "edict",
            "type": "python",
            "entry": "edict/backend/",
            "description": "三省六部多智能体编排框架",
            "capabilities": ["多Agent编排", "三省六部制度", "实时看板", "任务派发", "审核封驳"],
            "language": "Python/React",
            "status": "scanned",
        },
        "agent-reach": {
            "path": "Agent-Reach",
            "type": "python",
            "entry": "agent_reach/",
            "description": "互联网访问能力 — 14+平台搜索/读取",
            "capabilities": ["网页读取", "YouTube字幕", "Twitter/Reddit", "B站/小红书", "RSS/GitHub"],
            "language": "Python",
            "status": "scanned",
        },
        # ── 科技前沿项目（2026-05-21 下载） ──────────────
        # 已下载：crewAI/dspy/MetaGPT/phidata 通过GitHub Desktop完成
        "crewai": {
            "path": "crewAI",
            "type": "python",
            "entry": "src/crewai/",
            "description": "多Agent角色协作框架(25k+stars) — 待通过GitHub Desktop下载",
            "capabilities": ["角色协作", "任务委托", "Agent编排", "工具调用"],
            "language": "Python",
            "status": "pending_download",
        },
        "dspy": {
            "path": "dspy",
            "type": "python",
            "entry": "dspy/",
            "description": "Stanford NLP LLM优化框架(20k+stars) — 待通过GitHub Desktop下载",
            "capabilities": ["Prompt优化", "Few-shot调优", "自优化", "递归改进"],
            "language": "Python",
            "status": "pending_download",
        },
        "metagpt": {
            "path": "MetaGPT",
            "type": "python",
            "entry": "metagpt/",
            "description": "多Agent模拟软件公司(50k+stars) — 待通过GitHub Desktop下载",
            "capabilities": ["角色分化", "软件工程", "多Agent协作", "自动编程"],
            "language": "Python",
            "status": "pending_download",
        },
        "langgraph": {
            "path": "langgraph",
            "type": "python",
            "entry": "libs/langgraph/",
            "description": "LangChain有状态多Agent图编排(8k+stars) — 网络超时待重试",
            "capabilities": ["图编排", "状态机", "循环Agent", "持久化"],
            "language": "Python",
            "status": "pending_download",
        },
    }
    
    def __init__(self, base_path: str = "/mnt/c/Users/h/Desktop/零/真元集群/external_projects/"):
        self.base_path = base_path
        self.projects: dict[str, dict] = {}
        self.connectors: dict[str, Any] = {}  # name → connector实例（动态加载后缓存）
    
    def scan_projects(self) -> dict:
        """扫描并注册所有外部项目，返回项目状态概览"""
        results = {}
        for name, info in self.PROJECT_MAP.items():
            project_path = info["path"]
            full_path = self.base_path + project_path
            entry = dict(info)  # 浅拷贝
            entry["full_path"] = full_path
            entry["exists"] = self._check_exists(full_path)
            entry["loadable"] = self._check_loadable(name, full_path, info["type"])
            self.projects[name] = entry
            results[name] = {
                "name": name,
                "full_path": full_path,
                "description": info["description"],
                "capabilities": info["capabilities"],
                "exists": entry["exists"],
                "loadable": entry["loadable"],
                "type": info["type"],
                "status": info["status"],
            }
        return results
    
    def get_project(self, name: str) -> dict:
        """获取单个项目信息"""
        name = name.lower().replace("_", "-")
        if name in self.projects:
            return self.projects[name]
        # 懒扫描
        if name in self.PROJECT_MAP:
            self.scan_projects()
            return self.projects.get(name, {})
        return {"error": f"未知项目: {name}", "available": list(self.PROJECT_MAP.keys())}
    
    def list_available(self) -> list[str]:
        """列出已接入的项目名称"""
        if not self.projects:
            self.scan_projects()
        return list(self.projects.keys())
    
    def get_capability_matrix(self) -> dict:
        """返回能力矩阵：所有项目的跨域能力清单"""
        if not self.projects:
            self.scan_projects()
        matrix = {}
        for name, info in self.projects.items():
            for cap in info.get("capabilities", []):
                if cap not in matrix:
                    matrix[cap] = []
                matrix[cap].append(name)
        return matrix
    
    def suggest_projects(self, task: str) -> list[dict]:
        """根据任务关键词建议可用的外部项目"""
        if not self.projects:
            self.scan_projects()
        
        task_lower = task.lower()
        suggestions = []
        
        # 关键词→项目映射
        keyword_map = {
            "llm": ["llmfit"],
            "模型": ["llmfit"],
            "推荐": ["llmfit"],
            "硬件": ["llmfit"],
            "gpu": ["llmfit"],
            "搜索": ["agent-reach"],
            "网页": ["agent-reach", "gstack"],
            "youtube": ["agent-reach"],
            "twitter": ["agent-reach"],
            "reddit": ["agent-reach"],
            "b站": ["agent-reach"],
            "github": ["agent-reach"],
            "管理": ["symphony", "openfang"],
            "项目": ["symphony"],
            "部署": ["gstack", "copaw"],
            "对话": ["copaw"],
            "聊天": ["copaw"],
            "编排": ["edict"],
            "多agent": ["edict"],
            "三省六部": ["edict"],
            "cli": ["cli-anything"],
            "转化": ["cli-anything"],
            "docker": ["copaw"],
            "浏览器": ["gstack"],
            "审查": ["gstack"],
            "审计": ["gstack"],
            "专家": ["gstack"],
            "计划": ["symphony", "gstack"],
            "任务": ["symphony", "edict"],
            "自主": ["openfang"],
            "agent": ["openfang", "edict"],
            "操作系统": ["openfang"],
        }
        
        matched_names = set()
        for keyword, project_names in keyword_map.items():
            if keyword in task_lower:
                for pn in project_names:
                    matched_names.add(pn)
        
        for pn in matched_names:
            info = self.projects.get(pn)
            if info:
                suggestions.append({
                    "name": pn,
                    "description": info.get("description", ""),
                    "capabilities": info.get("capabilities", []),
                    "confidence": 0.8,
                })
        
        # 如果没有任何匹配，返回全部
        if not suggestions:
            for name, info in self.projects.items():
                suggestions.append({
                    "name": name,
                    "description": info.get("description", ""),
                    "capabilities": info.get("capabilities", []),
                    "confidence": 0.3,
                })
        
        return suggestions
    
    def _check_exists(self, full_path: str) -> bool:
        """检查项目目录是否存在"""
        try:
            import os
            return os.path.isdir(full_path)
        except Exception:
            return False
    
    def _check_loadable(self, name: str, full_path: str, proj_type: str) -> bool:
        """检查项目是否可加载（Python项目尝试import，其他类型标记可行性）"""
        try:
            if proj_type == "python":
                # Python项目：检查是否有setup.py/pyproject.toml
                import os
                return os.path.isfile(os.path.join(full_path, "setup.py")) or \
                       os.path.isfile(os.path.join(full_path, "pyproject.toml")) or \
                       os.path.isfile(os.path.join(full_path, "requirements.txt"))
            elif proj_type == "rust":
                # Rust项目：检查Cargo.toml
                import os
                return os.path.isfile(os.path.join(full_path, "Cargo.toml"))
            elif proj_type == "typescript":
                import os
                return os.path.isfile(os.path.join(full_path, "package.json"))
            elif proj_type == "elixir":
                import os
                return os.path.isfile(os.path.join(full_path, "mix.exs"))
            elif proj_type == "docker":
                import os
                return os.path.isfile(os.path.join(full_path, "docker-compose.yml"))
            return False
        except Exception:
            return False
    
    def __repr__(self) -> str:
        count = len(self.projects) if self.projects else 0
        return f"<ExternalProjectConnector projects={count}/8>"


# ═══════════════════════════════════════════════════════════
# 原有：MultiAgentSystem（扩展了v2能力）
# ═══════════════════════════════════════════════════════════
class MultiAgentSystem:
    """
    多Agent协同系统。
    管理所有agent的生命周期、通信、协同涌现。
    扩展：包含AgentHub和递归进化反馈。
    """
    
    def __init__(self):
        self.agents: dict[str, Agent] = {}
        self.messages: list[AgentMessage] = []
        self._active = False
        
        # v2 新增
        self.hub = AgentHub()
        self.evolution_feedback = RecursiveEvolutionFeedback(self.hub)
        
        # v3 新增：元递归的元递归
        self.meta_recursion = MetaRecursionEngine(self.hub, self.evolution_feedback)
        
        # v2.5 新增：外部项目连接器
        self.project_connector = ExternalProjectConnector()
        
        self._initialize_agents()
        self._register_external_agents()
        
        # v4 新增：太极万用桥 — 连接启示录哲学+CLI-Anything管道
        try:
            from taiji_universal_bridge import TaijiIntegrator
            self.taiji_integrator = TaijiIntegrator()
            self.taiji_integrator.register_all(
                hub=self.hub,
                project_connector=self.project_connector,
                meta_recursion=self.meta_recursion,
            )
        except Exception:
            self.taiji_integrator = None
    
    def _initialize_agents(self):
        """初始化所有agent"""
        roles = [
            ("perceiver-1", AgentRole.PERCEIVER, "感知外部输入和环境状态"),
            ("reflector-1", AgentRole.REFLECTOR, "反思自身思考过程"),
            ("decider-1", AgentRole.DECIDER, "基于感知和反思做出决策"),
            ("actor-1", AgentRole.ACTOR, "执行决策并产生输出"),
            ("metacog-1", AgentRole.METACOGNITION, "元认知——思考思考本身"),
            ("gap-filler-1", AgentRole.GAP_FILLER, "识别和填补缺口"),
            ("coordinator-1", AgentRole.COORDINATOR, "协调所有agent的协同"),
            ("blood-1", AgentRole.BLOOD_TRANSPORT, "外部API营养输送"),
        ]
        
        for agent_id, role, spec in roles:
            self.agents[agent_id] = Agent(
                id=agent_id,
                role=role,
                engine=MetaRecursiveEngine(),
                specialization=spec
            )
        
        # 注册到Hub
        self.hub.register_internal(self.agents)
    
    def _register_external_agents(self):
        """尝试注册外部Agent（Codex / Claude）"""
        try:
            from codex_agent_bridge import CodexAgent
            codex = CodexAgent()
            self.hub.register_external("codex", codex)
        except Exception as e:
            pass  # Codex不可用时静默跳过
        
        try:
            from claude_agent_bridge import ClaudeCodeAgent
            claude = ClaudeCodeAgent()
            self.hub.register_external("claude", claude)
        except Exception:
            pass  # Claude不可用时静默跳过
    
    def broadcast(self, content: str, sender: str = "system"):
        """广播消息给所有agent"""
        msg = AgentMessage(
            source=sender,
            target="*",
            content=content,
            message_type="broadcast",
            timestamp=time.time()
        )
        self.messages.append(msg)
        for agent in self.agents.values():
            agent.inbox.append(msg)
    
    def coordinate(self, input_text: str) -> dict:
        """
        协调所有agent处理一次输入（保留原有接口）。
        内部使用新的AgentHub调度。
        """
        # 使用Hub进行智能调度
        result = self.hub.dispatch(input_text, parallel=False)
        
        # 记录进化反馈
        for r in result.get("results", []):
            agent_name = r.get("agent", "unknown")
            success = r.get("success", False)
            elapsed_ms = r.get("_hub", {}).get("elapsed_ms", 0)
            contract_passed = r.get("_contract_passed", True)
            self.evolution_feedback.record(agent_name, success, elapsed_ms, contract_passed)
        
        # 保留原有格式的兼容性输出
        return {
            "input": input_text[:200],
            "processing_time_ms": result.get("_hub", {}).get("elapsed_ms", 0),
            "agents_activated": result.get("agents_used", 0),
            "total_thoughts": sum(a.engine.thought_count for a in self.agents.values()),
            "coordinator": self._generate_summary(),
            "hub_result": result,
            "v2": True,
        }
    
    def dispatch(self, task: str) -> dict:
        """（新接口）通过Hub调度任务"""
        return self.hub.dispatch(task)
    
    def _generate_summary(self) -> dict:
        """协调者生成全局摘要"""
        coordinator = self.agents.get("coordinator-1")
        if coordinator:
            return coordinator.engine.self_inspect()
        return {"error": "coordinator not found"}
    
    def get_vascular_map(self) -> dict:
        """生成血管图——展示信息/能量的流动网络。"""
        return {
            "blood_sources": ["外部API大模型群"],
            "blood_central": "血液输送总管 (blood-1)",
            "hub": {
                "internal": len(self.hub.internal_agents),
                "external": list(self.hub.external_agents.keys()),
                "weights": self.hub.agent_weights,
            },
            "agents": [
                {
                    "id": aid,
                    "role": a.role.value,
                    "specialization": a.specialization,
                    "status": a.status,
                    "recursion_depth": a.engine.recursion_depth,
                    "thought_count": a.engine.thought_count,
                    "gaps_found": [g.id for g in a.engine.gaps if g.status == 'open'],
                }
                for aid, a in self.agents.items()
            ],
            "flow_pattern": "感知→反思→决策→元认知→缺口填补→协调→行动",
            "feedback_loops": [
                "actor-1 → perceiver-1 (执行结果反馈)",
                "reflector-1 → metacog-1 (反思质量反馈)",
                "gap-filler-1 → coordinator-1 (缺口优先级反馈)",
                "blood-1 → 所有agent (营养输送)",
            ],
            "v2_features": [
                "AgentHub智能路由",
                "TaskDecomposer任务分解",
                "ContractSystem自指契约",
                "RecursiveEvolutionFeedback",
                "外部Codex/Claude Agent集成",
                "ExternalProjectConnector外部项目连接器",
            ],
            "v2_external_projects": {
                "connector": repr(self.project_connector),
                "projects": self.project_connector.scan_projects() if not self.project_connector.projects else {
                    name: {
                        "description": info.get("description", ""),
                        "capabilities": info.get("capabilities", []),
                        "exists": info.get("exists", False),
                        "loadable": info.get("loadable", False),
                        "type": info.get("type", ""),
                    }
                    for name, info in self.project_connector.projects.items()
                },
                "capability_matrix": self.project_connector.get_capability_matrix(),
            },
            "emergence_level": "局部交互→全局秩序协同涌现中",
        }


# ─── 系统入口 ────────────────────────────────────────────

mas = MultiAgentSystem()

def activate(input_text: str = "系统自检启动") -> dict:
    """激活多agent系统"""
    return mas.coordinate(input_text)


# ─── AgentManager（保留原有兼容接口）────────────────────────

class AgentManager:
    """管理所有注册的Agent（子人格），支持并发轮询调度。
    每个Agent必须实现:
      - name: str
      - async def run(context: dict) -> dict
      - async def handle_event(event: dict) -> None
    """
    def __init__(self):
        self._agents = {}
        self._active_queue = []
        self._context = {
            "state_version": 5,
            "active_signals": 0,
            "execution_phase": True,
        }
    
    def register_agent(self, name, agent_obj):
        """注册一个Agent到集群"""
        if not hasattr(agent_obj, 'run'):
            raise ValueError(f'Agent {name} 缺少 run 方法')
        if not hasattr(agent_obj, 'handle_event'):
            agent_obj.handle_event = lambda event: None
        self._agents[name] = agent_obj
        if name not in self._active_queue:
            self._active_queue.append(name)
        return True
    
    def unregister_agent(self, name):
        """移除Agent"""
        self._agents.pop(name, None)
        if name in self._active_queue:
            self._active_queue.remove(name)
    
    def get_active_agent(self):
        """返回当前活跃Agent"""
        return self._active_queue[0] if self._active_queue else None
    
    def broadcast_event(self, event):
        """向所有Agent广播事件"""
        import asyncio
        for name in self._active_queue:
            agent = self._agents.get(name)
            if agent:
                try:
                    asyncio.ensure_future(agent.handle_event(event))
                except Exception:
                    pass

# 全局管理器
agent_manager = AgentManager()


# ─── __main__ 自检 ────────────────────────────────────────
if __name__ == "__main__":
    result = activate("零·真元集群多Agent协同系统初始化自检")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    print("\n\n=== AgentHub 诊断 ===")
    hub = mas.hub
    agent_info = hub.list_agents()
    print(f"注册Agent: {len(agent_info)}")
    for name, info in agent_info.items():
        print(f"  {name}: {info['type']} (weight={info['weight']})")
    
    print("\n=== 任务分解测试 ===")
    decomposer = TaskDecomposer()
    test_task = "分析系统健康度并修复发现的性能问题"
    tasks = decomposer.decompose(test_task)
    print(f"任务: {test_task}")
    print(f"分解: {len(tasks)} 个子任务")
    for t in tasks:
        print(f"  [{t['tag']}] {t['desc'][:60]}")
    
    print("\n=== 血管图 ===")
    vmap = mas.get_vascular_map()
    print(json.dumps(vmap, ensure_ascii=False, indent=2))
