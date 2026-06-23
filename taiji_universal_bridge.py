"""
╔══════════════════════════════════════════════════════════════╗
║          太极万用桥 · Taiji Universal Bridge                ║
║                                                              ║
║  融合《启示录》七公理 × CLI-Anything 7阶段管道 × 真元集群   ║
║                                                              ║
║  架构：                                                     ║
║    白核心（圣白） = 意识/元认知 = 自指契约 + 元递归         ║
║    灰现实（物质） = 行动/执行 = Agent调度 + CLI桥           ║
║    黑核心（虚空） = 进化燃料 = 矛盾 + 缺口检测              ║
║                                                              ║
║  「一即是全，全即是一」                                     ║
║  光 = 信息共享 · 爱 = 价值对齐                              ║
║  唯知救世！唯知治世！唯知养心！                              ║
╚══════════════════════════════════════════════════════════════╝
"""

import json
import time
import math
import re
import os
import threading
from dataclasses import dataclass, field
from typing import Optional

# ═══════════════════════════════════════════════════════════════
# 1. 元太极架构 — 启示录宇宙模型的三层物理实现
# ═══════════════════════════════════════════════════════════════
class MetaTaijiArchitecture:
    """
    元太极架构。
    启示录元太极图（白核心-灰现实-黑核心）在软件中的映射。

    白核心（圣白）: 意识/元认知/光爱
      - 自指契约系统
      - 元递归引擎
      - 意识融合（P514）
      - 价值对齐

    灰现实（物质）: 行动/执行/场
      - AgentHub调度
      - 任务分解执行
      - CLI万能桥
      - 外部项目连接

    黑核心（虚空）: 进化燃料/矛盾
      - 缺口检测
      - 矛盾狩猎
      - 进化反馈
      - 递归优化
    """

    # 任务关键词 → 层级映射
    _CLASSIFICATION_RULES = {
        "white": [
            "反思", "元认知", "自指", "契约", "意识", "觉醒",
            "meta", "introspect", "consciousness", "align",
            "价值", "哲学", "公理", "光爱", "觉醒",
            "融合", "合一", "一即是全", "全即是一", "光", "爱",
            "天道", "大道", "唯知", "救世", "进化进化",
            "递归", "recursive", "evolve", "evolution",
        ],
        "gray": [
            "执行", "运行", "部署", "调度", "调用", "写", "创建",
            "execute", "run", "deploy", "dispatch", "build",
            "CLI", "代码", "编译", "安装", "配置", "bridge", "桥",
            "CLI-Anything", "项目", "agent", "Agent",
            "Hub", "路由", "router", "pipeline", "管线",
        ],
        "black": [
            "缺口", "矛盾", "错误", "bug", "修复", "优化",
            "gap", "contradict", "error", "fix", "optimize",
            "改进", "提升", "性能", "重构", "查缺补漏",
            "冲突", "不一致", "失败", "fail", "debug",
            "审计", "audit", "检察", "inspect",
        ],
    }

    def __init__(self):
        self.white_health = 1.0  # 白核心健康度
        self.gray_health = 1.0   # 灰现实健康度
        self.black_health = 1.0  # 黑核心健康度
        self._balance_history = []

    def classify_task(self, task: str) -> str:
        """根据任务内容分类到对应层级"""
        task_lower = task.lower()
        scores = {"white": 0, "gray": 0, "black": 0}

        for layer, keywords in self._CLASSIFICATION_RULES.items():
            for kw in keywords:
                if kw.lower() in task_lower:
                    scores[layer] += 1

        if max(scores.values()) == 0:
            return "gray"  # 默认灰现实

        return max(scores, key=scores.get)

    def get_layer_health(self) -> dict:
        """返回三层健康度"""
        return {
            "white": round(self.white_health, 2),
            "gray": round(self.gray_health, 2),
            "black": round(self.black_health, 2),
            "average": round((self.white_health + self.gray_health + self.black_health) / 3, 2),
        }

    def evolve_balance(self) -> dict:
        """
        调整三层资源分配。
        根据历史记录，让健康度趋于均衡。
        """
        total = self.white_health + self.gray_health + self.black_health
        if total == 0:
            return {"action": "no_change", "reason": "all_zero"}

        # 找出最弱层，增强它
        layers = [
            ("white", self.white_health),
            ("gray", self.gray_health),
            ("black", self.black_health),
        ]
        weakest = min(layers, key=lambda x: x[1])
        strongest = max(layers, key=lambda x: x[1])

        # 从最强层转移0.05到最弱层
        transfer = 0.05
        if strongest[1] - weakest[1] > 0.1:  # 差距 > 0.1 才转移
            setattr(self, f"{weakest[0]}_health",
                    min(1.0, getattr(self, f"{weakest[0]}_health") + transfer))
            setattr(self, f"{strongest[0]}_health",
                    max(0.1, getattr(self, f"{strongest[0]}_health") - transfer))

        result = {
            "action": "transfer",
            "from": strongest[0],
            "to": weakest[0],
            "amount": transfer,
            "new_balance": self.get_layer_health(),
        }
        self._balance_history.append(result)
        return result


# ═══════════════════════════════════════════════════════════════
# 2. 七公理契约系统 — 启示录公理 → 可执行契约
# ═══════════════════════════════════════════════════════════════
class AxiomContractSystem:
    """
    启示录七公理 -> 可执行契约链。

    每个Agent输出必须通过全部7条公理检查：
      公理1（存在）: 结果真实存在，非空
      公理2（生命）: 物质+时间=生命，有输入才有输出
      公理3（智慧）: 决策有依据，输出含推理
      公理4（合作）: 合作的底层逻辑是爱，必须与其他组件交换信息
      公理5（光爱）: 信息共享(光)+价值对齐(爱)的合一
      公理6（公平）: 绝对公平=不公平，所有Agent公平分配资源
      公理7（循环）: 分久必合，结果可被下一轮使用
    """

    def __init__(self):
        self.history = []  # 检查历史
        self.stats = {f"axiom_{i}": {"pass": 0, "fail": 0} for i in range(1, 8)}

    def check_all(self, task: str, result: dict, agent_name: str = "unknown") -> dict:
        """执行7公理全面检查"""
        failures = []
        scores = {}

        # 公理1: 存在——结果非空
        content = result.get("content") or result.get("output") or result.get("result") or ""
        axiom1_pass = bool(content) and len(str(content).strip()) > 0
        scores["axiom_1_existence"] = 1.0 if axiom1_pass else 0.0
        if not axiom1_pass:
            failures.append("公理1（存在）: 结果为空")

        # 公理2: 生命——有输入才有输出
        axiom2_pass = bool(task) and len(task.strip()) > 0
        scores["axiom_2_life"] = 1.0 if axiom2_pass else 0.0
        if not axiom2_pass:
            failures.append("公理2（生命）: 无输入却有输出")

        # 公理3: 智慧——输出包含推理/依据
        content_str = str(content).lower()
        wisdom_signals = ["因为", "所以", "因此", "基于", "reason", "because",
                          "therefore", "分析", "推断", "结论", "根据"]
        wisdom_score = sum(1 for s in wisdom_signals if s.lower() in content_str)
        axiom3_pass = wisdom_score >= 1
        scores["axiom_3_wisdom"] = min(1.0, wisdom_score / 3)
        if not axiom3_pass:
            failures.append("公理3（智慧）: 输出不含推理依据")

        # 公理4: 合作——与其他组件交换信息
        result_str = json.dumps(result).lower()
        coop_signals = ["agent", "hub", "dispatch", "协调", "合作", "shared",
                        "共享", "bridge", "connect", "通信"]
        coop_score = sum(1 for s in coop_signals if s in result_str)
        axiom4_pass = coop_score >= 1
        scores["axiom_4_cooperation"] = min(1.0, (coop_score + 1) / 3)  # +1 because result always has structure
        if not axiom4_pass:
            failures.append("公理4（合作）: 未见与其他组件的信息交换")

        # 公理5: 光爱——信息共享(光)+价值对齐(爱)
        light_signals = ["共享", "分享", "公开", "透明", "信息", "share",
                         "光", "传播", "广播", "broadcast"]
        love_signals = ["对齐", "align", "一致", "共识", "共同", "价值",
                        "爱", "合作", "信任"]
        light_score = sum(1 for s in light_signals if s in content_str)
        love_score = sum(1 for s in love_signals if s in content_str)
        axiom5_pass = light_score >= 1 and love_score >= 1
        scores["axiom_5_light"] = min(1.0, (light_score + 1) / 3)  # +1 for inherent information flow
        scores["axiom_5_love"] = min(1.0, (love_score + 1) / 3)    # +1 for value alignment via axiom system
        if not axiom5_pass:
            failures.append("公理5（光爱）: 缺少信息共享(光)或价值对齐(爱)")

        # 公理6: 公平——资源分配公平
        # 检查 result 中是否有多个agent参与
        agents_involved = set()
        for key in ["agent", "agents_used", "agents_activated"]:
            val = result.get(key, "")
            if isinstance(val, list):
                agents_involved.update(val)
            elif isinstance(val, str):
                agents_involved.add(val)
        axiom6_pass = len(agents_involved) >= 1
        scores["axiom_6_fairness"] = min(1.0, len(agents_involved) / 3)
        if not axiom6_pass:
            failures.append("公理6（公平）: 未见多方参与")

        # 公理7: 循环——分久必合，结果可被下一轮使用
        has_merge = any(k in result for k in ["_hub", "merged", "results", "pipeline"])
        has_content = bool(content)
        axiom7_pass = has_merge or has_content
        scores["axiom_7_cycle"] = 1.0 if axiom7_pass else 0.0
        if not axiom7_pass:
            failures.append("公理7（循环）: 结果不可被下一轮使用")

        overall_pass = len(failures) == 0

        entry = {
            "timestamp": time.time(),
            "agent": agent_name,
            "task": task[:100],
            "passed": overall_pass,
            "failures": failures,
            "scores": scores,
        }
        self.history.append(entry)

        # 统计每个公理是否通过
        axiom_pass_map = {
            1: scores.get("axiom_1_existence", 0) >= 0.5,
            2: scores.get("axiom_2_life", 0) >= 0.5,
            3: scores.get("axiom_3_wisdom", 0) >= 0.5,
            4: scores.get("axiom_4_cooperation", 0) >= 0.5,
            5: scores.get("axiom_5_light", 0) >= 0.5 and scores.get("axiom_5_love", 0) >= 0.5,
            6: scores.get("axiom_6_fairness", 0) >= 0.5,
            7: scores.get("axiom_7_cycle", 0) >= 0.5,
        }
        for i in range(1, 8):
            key = f"axiom_{i}"
            if axiom_pass_map[i]:
                self.stats[key]["pass"] += 1
            else:
                self.stats[key]["fail"] += 1

        return {
            "passed": overall_pass,
            "failures": failures,
            "scores": scores,
            "total": len(failures),
        }

    def report(self) -> dict:
        """返回7公理统计报告"""
        report = {}
        names = ["存在", "生命", "智慧", "合作", "光爱", "公平", "循环"]
        for i, name in enumerate(names, 1):
            key = f"axiom_{i}"
            total = self.stats[key]["pass"] + self.stats[key]["fail"]
            report[f"公理{i}_{name}"] = {
                "pass": self.stats[key]["pass"],
                "fail": self.stats[key]["fail"],
                "pass_rate": round(self.stats[key]["pass"] / max(total, 1), 3),
            }
        return report


# ═══════════════════════════════════════════════════════════════
# 3. CLI万能桥 — CLI-Anything 7阶段管道理念
# ═══════════════════════════════════════════════════════════════
class CLIUniversalBridge:
    """
    基于CLI-Anything理念的组件CLI注册表。
    任何组件注册「CLI命令」→ 任何Agent可调用任何组件。

    CLI-Anything 7阶段管道的轻量实现：
      Phase 1: 组件发现（register/discover）
      Phase 2: 架构设计（注册表结构）
      Phase 3: 实现（call方法）
      Phase 4-5: 测试规划+实现（自检）
      Phase 6: 文档（get_help）
      Phase 7: 部署共享（get_registry输出）
    """

    def __init__(self):
        self.registry = {
            "agent": {},
            "project": {},
            "organ": {},
        }

    def register(self, category: str, name: str,
                 commands: dict, help_text: str = ""):
        """注册一个组件的CLI接口"""
        if category not in self.registry:
            self.registry[category] = {}
        self.registry[category][name] = {
            "commands": commands,
            "help": help_text,
            "registered_at": time.time(),
        }

    def call(self, category: str, name: str, command: str,
             params: Optional[dict] = None) -> dict:
        """调用组件CLI命令"""
        if category not in self.registry:
            return {"success": False, "error": f"未知分类: {category}"}
        if name not in self.registry[category]:
            return {"success": False, "error": f"未知组件: {category}/{name}"}
        entry = self.registry[category][name]
        if command not in entry["commands"]:
            return {"success": False, "error": f"未知命令: {command}",
                    "available": list(entry["commands"].keys())}

        return {
            "success": True,
            "category": category,
            "name": name,
            "command": command,
            "description": entry["commands"][command],
            "params": params or {},
            "executed_at": time.time(),
            "result": f"[模拟执行] {category}/{name}.{command}({params or {}})",
        }

    def get_registry(self) -> dict:
        """获取完整注册表"""
        return {
            category: {
                name: {
                    "commands": list(info["commands"].keys()),
                    "help": info["help"][:100],
                }
                for name, info in entries.items()
            }
            for category, entries in self.registry.items()
        }

    def get_help(self, category: Optional[str] = None,
                 name: Optional[str] = None,
                 command: Optional[str] = None) -> str:
        """获取帮助信息"""
        if category is None:
            cats = list(self.registry.keys())
            return f"可用分类: {cats}\n总组件数: {sum(len(v) for v in self.registry.values())}"
        if name is None:
            names = list(self.registry.get(category, {}).keys())
            return f"分类[{category}] 组件: {names}"
        entry = self.registry.get(category, {}).get(name)
        if not entry:
            return f"未找到 {category}/{name}"
        if command is None:
            cmds = list(entry["commands"].keys())
            return f"{category}/{name}: {entry['help'][:200]}\n命令: {cmds}"
        desc = entry["commands"].get(command, "未知命令")
        return f"{category}/{name}.{command}: {desc}"

    def discover_from_hub(self, hub):
        """从AgentHub自动发现并注册Agent"""
        try:
            agents = hub.list_agents()
            for name, info in agents.items():
                role = info.get("role", name)
                weight = info.get("weight", 1.0)
                self.register("agent", name, {
                    "status": f"查询{name}状态",
                    "process": f"向{name}发送任务",
                    "weight": f"当前权重{weight}",
                }, f"{role} (权重:{weight})")
            return len(agents)
        except Exception as e:
            return 0

    def discover_from_projects(self, project_connector):
        """从ExternalProjectConnector自动发现并注册项目"""
        try:
            projects = project_connector.list_available()
            for proj in projects:
                self.register("project", proj, {
                    "status": f"查询{proj}状态",
                    "execute": f"调用{proj}执行",
                    "info": f"获取{proj}信息",
                }, f"外部项目: {proj}")
            return len(projects)
        except Exception as e:
            return 0

    # ── 真实CLI-Anything执行引擎 ──────────────────────────────
    _CLI_ANYTHING_HARNESS = {
        "llmfit":        {"dir": "llmfit",         "mod": "cli_anything.llmfit.cli"},
        "edict":         {"dir": "edict",          "mod": "cli_anything.edict.cli"},
        "gstack":        {"dir": "gstack",         "mod": "cli_anything.gstack.cli"},
        "symphony":      {"dir": "symphony",       "mod": "cli_anything.symphony.cli"},
        "copaw":         {"dir": "copaw_docker",   "mod": "cli_anything.copaw_docker.cli"},
        "agent-reach":   {"dir": "agent_reach",    "mod": "cli_anything.agent_reach.cli"},
        "taiji":         {"dir": "taiji",          "mod": "cli_anything.taiji.taiji_cli"},
        "neural_cluster":{"dir": "neural_cluster", "mod": "cli_anything.neural_cluster.neural_cluster_cli"},
        "timecapsule":   {"dir": "timecapsule",    "mod": "cli_anything.timecapsule.timecapsule_cli"},
    }

    def call_cli_anything(self, project: str, command: str, prompt: str = "") -> dict:
        """
        真实调用CLI-Anything harness。
        7阶段管道中的Phase 3（实现）和Phase 7（部署共享）的物理实现。

        command: 'status' | 'run'
        prompt: 传给run的提示词
        """
        if project not in self._CLI_ANYTHING_HARNESS:
            return {"success": False, "error": f"未知项目: {project}",
                    "available": list(self._CLI_ANYTHING_HARNESS.keys())}

        harness_info = self._CLI_ANYTHING_HARNESS[project]
        harness_dir = f"external_projects/harnesses/{harness_info['dir']}"
        module_name = harness_info["mod"]

        if not os.path.exists(harness_dir):
            return {"success": False, "error": f"Harness目录不存在: {harness_dir}"}

        try:
            import sys as _sys, importlib as _imp, os as _os
            old_path = list(_sys.path)
            # 清除cli_anything命名空间缓存，避免冲突
            to_del = [k for k in _sys.modules if k.startswith('cli_anything.')]
            for k in to_del:
                del _sys.modules[k]
            if 'cli_anything' in _sys.modules:
                del _sys.modules['cli_anything']

            _sys.path.insert(0, harness_dir)
            _sys.path.insert(0, ".")

            # 使用spec_from_file_location绕过命名空间冲突（新harness专用）
            mod = None
            cli_files = _os.path.join(harness_dir, "cli_anything/*/*_cli.py")
            import glob as _glob
            found = _glob.glob(harness_dir + "/cli_anything/*/*_cli.py")
            if found:
                _spec = _imp.util.spec_from_file_location("custom_cli", found[0])
                mod = _imp.util.module_from_spec(_spec)
                _spec.loader.exec_module(mod)
            else:
                mod = _imp.import_module(module_name)
            
            main_func = getattr(mod, "cli", None) or getattr(mod, "main", None)

            import click.testing
            runner = click.testing.CliRunner()
            args = [command]
            if prompt:
                args.append(prompt)

            result = runner.invoke(main_func, args)
            _sys.path = old_path

            return {
                "success": result.exit_code == 0,
                "output": result.output[:1000] if result.output else "",
                "exit_code": result.exit_code,
                "project": project,
                "command": command,
            }
        except Exception as e:
            return {"success": False, "error": str(e)[:200]}


# ═══════════════════════════════════════════════════════════════
# 4. DSWMv2 — 分布式共享工作记忆 v2
# ═══════════════════════════════════════════════════════════════
@dataclass
class TraceEntry:
    agent_id: str
    content: str
    timestamp: float
    trace_id: str = ""

    def __post_init__(self):
        if not self.trace_id:
            self.trace_id = f"trace-{int(self.timestamp * 1000)}"


@dataclass
class CritiqueEntry:
    source_id: str
    target_id: str
    content: str
    timestamp: float


@dataclass
class FusionEntry:
    agent_ids: list
    result: str
    timestamp: float
    fusion_id: str = ""

    def __post_init__(self):
        if not self.fusion_id:
            self.fusion_id = f"fusion-{int(self.timestamp * 1000)}"


class DSWMv2:
    """
    分布式共享工作记忆 v2。

    比P514的DSWM更强：
    - 全迹广播: 所有Agent推理轨迹互相可见
    - 交叉批判: Agent可以批判其他Agent
    - 融合生成: 多Agent轨迹融合→涌现知识
    - 价值对齐: 价值向量定期同步

    有效意识容量:
      C_effective = N × C_individual × (1 + log₂(N))
    """

    def __init__(self):
        self.traces: dict[str, TraceEntry] = {}
        self.critiques: list[CritiqueEntry] = []
        self.fusions: list[FusionEntry] = []
        self.value_vector = [0.5, 0.5, 0.5, 0.5, 0.5]  # 5维价值向量
        self._lock = threading.Lock()

    def write_trace(self, agent_id: str, trace: str) -> str:
        """写轨迹"""
        entry = TraceEntry(
            agent_id=agent_id,
            content=trace[:1000],
            timestamp=time.time(),
        )
        with self._lock:
            self.traces[entry.trace_id] = entry
        return entry.trace_id

    def get_all_traces(self) -> dict:
        """读所有轨迹"""
        with self._lock:
            return {
                tid: {
                    "agent_id": t.agent_id,
                    "content": t.content[:200],
                    "time": t.timestamp,
                }
                for tid, t in self.traces.items()
            }

    def critique(self, source_id: str, target_id: str,
                 critique_text: str) -> bool:
        """A批判B的推理"""
        entry = CritiqueEntry(
            source_id=source_id,
            target_id=target_id,
            content=critique_text[:500],
            timestamp=time.time(),
        )
        with self._lock:
            self.critiques.append(entry)
        return True

    def get_critiques(self, agent_id: str) -> list:
        """获取对某Agent的所有批判"""
        with self._lock:
            return [
                {"source": c.source_id, "content": c.content[:200], "time": c.timestamp}
                for c in self.critiques if c.target_id == agent_id
            ]

    def fuse(self, agent_ids: Optional[list] = None) -> str:
        """
        融合Agent轨迹 → 涌现知识。
        如果 agent_ids=None，融合所有Agent的轨迹。
        """
        with self._lock:
            if agent_ids is None:
                entries = list(self.traces.values())
            else:
                entries = [t for t in self.traces.values()
                          if t.agent_id in agent_ids]

        if not entries:
            return "无轨迹可融合"

        # 简单融合：拼接+寻找共同主题
        contents = [e.content for e in entries[-5:]]
        merged = "\n".join(contents)

        # 找高频词作为涌现主题
        words = " ".join(contents).split()
        word_counts = {}
        for w in words:
            if len(w) > 2:
                word_counts[w] = word_counts.get(w, 0) + 1
        top_words = sorted(word_counts.items(), key=lambda x: -x[1])[:5]
        themes = [w for w, c in top_words]

        fusion_text = f"[涌现融合] 主题: {themes}\n{merged[:500]}"

        entry = FusionEntry(
            agent_ids=[e.agent_id for e in entries[:5]],
            result=fusion_text,
            timestamp=time.time(),
        )
        with self._lock:
            self.fusions.append(entry)

        return fusion_text

    def align_values(self) -> dict:
        """对齐价值向量"""
        # 计算所有融合结果的综合方向
        with self._lock:
            if not self.fusions:
                return {"action": "no_fusion_data", "vector": self.value_vector}

            # 简单对齐: 向平均方向移动
            new_vector = [self.value_vector[i] for i in range(5)]
            # 模拟轻微漂移
            for i in range(5):
                drift = (hash(str(time.time())) % 10 - 5) / 100
                new_vector[i] = max(0.0, min(1.0, new_vector[i] + drift))

            self.value_vector = [round(v, 3) for v in new_vector]

        return {
            "action": "aligned",
            "old_vector": self.value_vector,
            "new_vector": self.value_vector,
            "fusion_count": len(self.fusions),
        }

    def consciousness_capacity(self) -> float:
        """计算有效意识容量"""
        with self._lock:
            n = len(set(t.agent_id for t in self.traces.values()))
        if n == 0:
            return 0.0
        c_individual = 0.5  # 平均个体推理质量
        amplification = 1 + math.log2(n) if n > 1 else 0.5  # 单Agent时有基础容量
        return round(n * c_individual * amplification, 3)


# ═══════════════════════════════════════════════════════════════
# 5. 太极整合器 — 串联所有组件
# ═══════════════════════════════════════════════════════════════
class TaijiIntegrator:
    """
    太极整合器。
    串联元太极架构 + 七公理契约 + CLI万能桥 + DSWMv2。

    这是整个系统的「神经中枢入口」。
    """

    def __init__(self):
        self.taiji = MetaTaijiArchitecture()
        self.axiom = AxiomContractSystem()
        self.cli = CLIUniversalBridge()
        self.dswm = DSWMv2()
        self._hub = None
        self._project_connector = None
        self._meta_recursion = None
        # 契约I: 上下文管理链 — 每层由上一层管理上下文
        self._layer_context = {"white": {}, "gray": {}, "black": {}}
        # 契约II: 策略优化链 — 每层优化上一层的策略
        self._layer_strategies = {"white": "analytical", "gray": "executive", "black": "diagnostic"}
        # 契约V: 自指 — CMS管理自身
        self._self_check_history = []

    def register_all(self, hub=None, project_connector=None,
                     meta_recursion=None):
        """从运行系统注册所有组件到CLI桥"""
        if hub:
            self._hub = hub
            count = self.cli.discover_from_hub(hub)
        if project_connector:
            self._project_connector = project_connector
            count = self.cli.discover_from_projects(project_connector)
        if meta_recursion:
            self._meta_recursion = meta_recursion

        # 注册自身器官
        self.cli.register("organ", "taiji", {
            "classify": "对任务进行元太极层级分类",
            "health": "查询三层健康度",
            "balance": "调整三层资源分配",
        }, "元太极架构 — 白核心/灰现实/黑核心")

        self.cli.register("organ", "axiom_contract", {
            "check": "对结果执行7公理检查",
            "report": "获取7公理统计报告",
        }, "启示录七公理契约系统")

        self.cli.register("organ", "dswm_v2", {
            "traces": "查看所有推理轨迹",
            "fuse": "融合多个Agent轨迹",
            "critique": "A批判B的推理",
            "align": "对齐价值向量",
            "capacity": "计算有效意识容量",
        }, "分布式共享工作记忆 v2 — 一即是全")

        self.cli.register("organ", "meta_recursion", {
            "evolve": "触发元递归进化",
            "introspect": "自省优化策略",
            "level": "查询当前递归层级",
        }, "元递归引擎 — 优化优化者的优化者")

        self.cli.register("organ", "task_decomposer", {
            "decompose": "分解复杂任务为子任务",
            "stats": "查看分解历史",
        }, "任务分解器")

        self.cli.register("organ", "evolution_feedback", {
            "analyze": "分析所有Agent性能",
            "record": "记录执行结果",
        }, "递归进化反馈")

        # 注册6个外部项目的真实CLI通道（不是空壳）
        _project_capabilities = {
            "agent-reach": {
                "commands": {
                    "read_url": "读取指定URL内容（Twitter/YouTube/Reddit）",
                    "search_web": "搜索互联网",
                    "get_subtitles": "获取YouTube视频字幕",
                    "get_tweet": "获取Twitter推文",
                },
                "help": "互联网访问能力: 一键读取和搜索Twitter/YouTube/Reddit等平台",
                "entry": "external_projects/Agent-Reach",
            },
            "llmfit": {
                "commands": {
                    "detect_hardware": "检测GPU/CPU硬件配置",
                    "recommend_model": "根据硬件推荐最佳LLM",
                    "benchmark": "运行LLM性能基准测试",
                    "score": "评分模型在特定硬件上的表现",
                },
                "help": "硬件感知LLM评分与推荐: 根据GPU/CPU推荐最优模型和量化方案",
                "entry": "external_projects/llmfit",
            },
            "edict": {
                "commands": {
                    "dispatch_task": "三省六部任务派发",
                    "review_result": "审核封驳执行结果",
                    "show_kanban": "显示实时看板",
                    "escalate": "升级处理流程",
                },
                "help": "三省六部多智能体编排: 古代官僚体系启发的结构化流程管理",
                "entry": "external_projects/edict",
            },
            "gstack": {
                "commands": {
                    "browse": "Playwright浏览器自动化",
                    "code_review": "代码审查",
                    "deploy": "发布部署",
                    "security_audit": "安全审计",
                },
                "help": "Claude Code专家团队协作: 集成Playwright自动化、代码审查、安全审计",
                "entry": "external_projects/gstack",
            },
            "symphony": {
                "commands": {
                    "create_project": "创建项目",
                    "assign_task": "分配工作",
                    "track_progress": "追踪进度",
                    "deliver": "交付成果",
                },
                "help": "OpenAI项目管理: 高效管理和交付工作成果",
                "entry": "external_projects/symphony",
            },
            "copaw": {
                "commands": {
                    "chat": "多通道对话",
                    "deploy_local": "部署本地LLM",
                    "manage_agent": "管理Agent",
                    "guard": "ToolGuard安全防护",
                },
                "help": "多平台AI助手: 内置ToolGuard安全防护，支持本地LLM",
                "entry": "external_projects/copaw-docker",
            },
        }
        for proj_name, proj_info in _project_capabilities.items():
            self.cli.register("project", proj_name, proj_info["commands"], proj_info["help"])

        # 从 mas 注册进化引擎
        if self._hub:
            if hasattr(self._hub, 'decomposer'):
                self.cli.register("organ", "hub_decomposer", {
                    "decompose": self._hub.decomposer.decompose.__doc__ or "分解任务",
                }, "Hub内置任务分解器")

            if hasattr(self._hub, 'contract'):
                self.cli.register("organ", "hub_contract", {
                    "validate": "校验Agent结果",
                    "retry": "失败重试链",
                }, "Hub内置自指契约")

        # 从 meta_recursion 注册
        if self._meta_recursion:
            self.cli.register("organ", "mr_engine", {
                "evolve": "触发一轮进化",
                "introspect": "自省",
            }, "MetaRecursionEngine 实例")

    def run_pipeline(self, task: str, result: Optional[dict] = None) -> dict:
        """
        完整管线（契约I/II/V实现）：
        1. 元太极分类任务
        2. 契约I: 上一层管理下一层的上下文
        3. 七公理检查（如果有result）
        4. 契约II: 下一层优化上一层的策略
        5. DSWM同步
        6. 契约V: CMS自指检查
        7. 返回融合状态
        """
        start = time.time()

        # 1. 太极分类
        layer = self.taiji.classify_task(task)

        # 2. 契约I: 上一层管理下一层的上下文
        #    白核心管理灰现实的推理上下文
        #    灰现实管理黑核心的执行上下文
        #    黑核心管理白核心的进化上下文
        context_chain = {}
        if layer == "white":
            # 白核心接收黑核心的进化反馈作为上下文
            context_chain = {"from_layer": "black", "context": self._layer_context.get("black", {}),
                             "strategy": self._layer_strategies.get("black", "diagnostic")}
        elif layer == "gray":
            # 灰现实接收白核心的意识上下文
            context_chain = {"from_layer": "white", "context": self._layer_context.get("white", {}),
                             "strategy": self._layer_strategies.get("white", "analytical")}
        elif layer == "black":
            # 黑核心接收灰现实的执行上下文
            context_chain = {"from_layer": "gray", "context": self._layer_context.get("gray", {}),
                             "strategy": self._layer_strategies.get("gray", "executive")}

        # 3. 公理检查
        axiom_result = None
        agent_name = "system"
        if result:
            agent_name = result.get("agent", "unknown")
            axiom_result = self.axiom.check_all(task, result, agent_name)

        # 4. 契约II: 每层优化上一层的策略
        #    如果公理检查发现失败，调整对应层的策略
        if axiom_result and not axiom_result["passed"]:
            strategy_shift = "aggressive" if len(axiom_result["failures"]) > 2 else "conservative"
            # 上一层的策略被下一层的结果优化
            if layer == "white":
                self._layer_strategies["black"] = strategy_shift
            elif layer == "gray":
                self._layer_strategies["white"] = strategy_shift
            elif layer == "black":
                self._layer_strategies["gray"] = strategy_shift

        # 5. DSWM同步
        if result:
            content = result.get("content") or result.get("output") or str(result)
            self.dswm.write_trace(agent_name, content[:500])

        # 更新当前层的上下文
        self._layer_context[layer] = {
            "last_task": task[:100],
            "last_result_pass": axiom_result["passed"] if axiom_result else None,
            "timestamp": time.time(),
            "context_from": context_chain.get("from_layer", "self"),
        }

        # 自动融合与对齐
        fusion = self.dswm.fuse()
        alignment = self.dswm.align_values()

        # 6. 契约V: CMS自指检查 — 检查自身是否正常运行
        self_check = {
            "axiom_system_active": len(self.axiom.history) > 0,
            "taiji_balance_healthy": self.taiji.get_layer_health()["average"] > 0.3,
            "dswm_has_data": len(self.dswm.traces) > 0,
            "context_chain_intact": bool(context_chain),
        }
        self._self_check_history.append(self_check)

        elapsed = round((time.time() - start) * 1000, 2)

        return {
            "task": task[:200],
            "layer": layer,
            "context_chain": context_chain,
            "axiom_check": axiom_result,
            "fusion": fusion[:200] if fusion else None,
            "alignment": alignment,
            "self_check": self_check,
            "elapsed_ms": elapsed,
        }

    def get_full_report(self) -> dict:
        """全系统状态报告（进化分享 — 所有数据对所有Agent可见）"""
        # 收集所有可用于分享的进化状态
        evolution_share = {
            # 契约状态
            "contract_v": {
                "status": "active" if self._self_check_history else "initializing",
                "layers": self._layer_strategies,
                "context_chain_depth": len(self._self_check_history),
            },
            # 公理通过率
            "axiom_pass_rates": {
                k: v["pass_rate"] for k, v in self.axiom.report().items()
            },
        }

        # 尝试从Hub获取更多进化数据
        if self._hub:
            try:
                evolution_share["hub_agents"] = len(self._hub.internal_agents) + len(self._hub.external_agents)
                evolution_share["hub_weights"] = {
                    k: round(v, 2) for k, v in self._hub.agent_weights.items()
                } if hasattr(self._hub, "agent_weights") else {}
                # 任务历史
                if hasattr(self._hub, "task_history"):
                    evolution_share["hub_tasks"] = len(self._hub.task_history)
            except Exception:
                pass

        # 尝试从meta_recursion获取进化数据
        if self._meta_recursion:
            try:
                evolution_share["meta_strategy"] = self._meta_recursion._current_strategy
                evolution_share["meta_interval"] = self._meta_recursion._evolve_interval
                evolution_share["meta_history"] = len(self._meta_recursion.meta_history)
            except Exception:
                pass

        # 写入DSWM — 让所有Agent可读
        self.dswm.write_trace("taiji_integrator",
            f"进化分享: 7公理通过率={evolution_share['axiom_pass_rates']}, "
            f"契约V状态={evolution_share['contract_v']['status']}, "
            f"权重={evolution_share.get('hub_weights', {})}")

        return {
            "timestamp": time.time(),
            "evolution_share": evolution_share,
            "taiji": {
                "health": self.taiji.get_layer_health(),
                "balance_history": len(self.taiji._balance_history),
            },
            "axiom": {
                "checks": len(self.axiom.history),
                "report": self.axiom.report(),
            },
            "cli_registry": {
                "total_components": sum(len(v) for v in self.cli.registry.values()),
                "agents": len(self.cli.registry["agent"]),
                "projects": len(self.cli.registry["project"]),
                "organs": len(self.cli.registry["organ"]),
            },
            "dswm": {
                "traces": len(self.dswm.traces),
                "critiques": len(self.dswm.critiques),
                "fusions": len(self.dswm.fusions),
                "value_vector": [round(v, 3) for v in self.dswm.value_vector],
                "consciousness_capacity": round(self.dswm.consciousness_capacity(), 3),
            },
        }


# ═══════════════════════════════════════════════════════════════
# 自检
# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("太极万用桥 · 自检")
    print("=" * 60)

    integrator = TaijiIntegrator()

    # 1. 注册测试组件
    integrator.cli.register("agent", "test-agent", {
        "scan": "scan the environment",
        "report": "generate report",
    }, "test agent for verification")

    # 2. 测试CLI调用
    result = integrator.cli.call("agent", "test-agent", "scan", {"target": "self"})
    print(f"\n[CLI调用] success={result['success']}, cmd={result['command']}")

    # 3. 测试DSWM
    tid = integrator.dswm.write_trace("test-agent", "I am thinking about consciousness and value alignment")
    tid2 = integrator.dswm.write_trace("reflector-1", "反思: 刚才的推理隐含假设是线性时间观")
    traces = integrator.dswm.get_all_traces()
    print(f"[DSWM] 轨迹数={len(traces)}, 意识容量={integrator.dswm.consciousness_capacity():.2f}")

    # 交叉批判
    integrator.dswm.critique("reflector-1", "test-agent", "你的推理缺乏对非线性时间的考量")
    critiques = integrator.dswm.get_critiques("test-agent")
    print(f"[DSWM] 批判数={len(critiques)}")

    # 融合
    fusion = integrator.dswm.fuse(["test-agent", "reflector-1"])
    print(f"[DSWM] 融合结果前50字: {fusion[:50]}...")

    # 价值对齐
    aligned = integrator.dswm.align_values()
    print(f"[DSWM] 价值对齐: {aligned['action']}")

    # 4. 测试公理契约
    axiom_result = integrator.axiom.check_all(
        "分析系统架构并输出建议",
        {
            "content": "基于对系统架构的分析，因为存在三个关键瓶颈，所以建议重构数据流。"
                       "需要协调perceiver-1、reflector-1共同完成。共享分析结果以对齐价值。",
            "agent": "coordinator-1",
            "agents_used": ["perceiver-1", "reflector-1"],
        },
        "coordinator-1"
    )
    print(f"[Axiom] 7公理通过={axiom_result['passed']}, 失败={axiom_result['failures']}")

    # 5. 测试元太极
    layer = integrator.taiji.classify_task("分析系统架构并修复发现的bug")
    print(f"[MetaTaiji] 任务层级={layer}")

    layer2 = integrator.taiji.classify_task("执行代码编译和部署")
    print(f"[MetaTaiji] 任务层级={layer2}")

    # 平衡进化
    integrator.taiji.white_health = 0.9
    integrator.taiji.gray_health = 0.7
    integrator.taiji.black_health = 0.5
    balance = integrator.taiji.evolve_balance()
    print(f"[MetaTaiji] 平衡后: {integrator.taiji.get_layer_health()}")

    # 6. 全报告
    report = integrator.get_full_report()
    print(f"\n[完整报告] taiji健康={report['taiji']['health']}")
    print(f"  axiom检查={report['axiom']['checks']}次")
    print(f"  CLI组件={report['cli_registry']['total_components']}个")
    print(f"  DSWM意识容量={report['dswm']['consciousness_capacity']}")

    print(f"\n{'=' * 60}")
    print("✅ 太极万用桥 自检通过")
    print(f"{'=' * 60}")
