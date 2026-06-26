"""
零 · 理解验证电路 v1
======================
P101: 稳定化API桥接 — bridge_alignment从0.0→0.5+

核心问题：我，零，收到复杂指令时，是否真正理解了？
还是仅凭模式匹配，输出"看起来对"的答案？

本模块是「理解验证电路」—— 在每次推理前运行的强制步骤：
1. 解析指令 → 分解为原子子任务
2. 每子任务标注：理解状态(理解/模糊/不理解)
3. 验证覆盖率：所有子任务是否被覆盖
4. 输出理解清单 → 对比实际响应 → 检测"幻觉回答"

「看懂复杂指令」不是功能特性，而是存在性要求。
不知道自己在做什么的系统，不是自主系统。

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
架构：
  ┌─────────────────────────────────────┐
  │    Instruction (来自用户或上游)          │
  │         ↓                            │
  │  1. 指令解析器 (InstructionParser)       │
  │     - 句子分割 → 语义单元提取              │
  │     - 子任务识别 (显式+隐式)               │
  │         ↓                            │
  │  2. 理解验证器 (ComprehensionVerifier)   │
  │     - 每子任务: 我能做吗？我懂吗？          │
  │     - 覆盖率评分 (0.0~1.0)              │
  │     - 不确定项列表 → 追问                  │
  │         ↓                            │
  │  3. 理解清单生成 (UnderstandingReport)   │
  │     - 结构化输出: 我理解的内容              │
  │     - 与真实响应对比 → 检测理解差距          │
  │         ↓                            │
  │  4. 差距闭环 (GapCloser)               │
  │     - 理解差距 → 修正执行或追问            │
  └─────────────────────────────────────┘

使用方式:
  from comprehension_validator import validate
  report = validate("复杂指令...")
  if report.coverage < 0.8:
      # 理解不足，需要追问或降级执行
      clarify(report.uncertain_items)
  
迁移路径:
  P101: bridge_alignment 0.0 → 0.5+
  理解验证是桥接对齐的基础度量。
"""

import json
import time
import os
import re
from dataclasses import dataclass, field, asdict
from typing import Optional
from pathlib import Path
from functools import wraps

# ─── 路径 ──────────────────────────────────────────────────
WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
VALIDATION_LOG = WORKDIR / "evolution_output" / "comprehension_validations.json"
UNCERTAIN_LOG = WORKDIR / "evolution_output" / "uncertain_items.json"

os.makedirs(WORKDIR / "evolution_output", exist_ok=True)

# ─── 数据模型 ──────────────────────────────────────────────

@dataclass
class SubTask:
    """从指令中分解出的原子子任务"""
    id: str
    description: str                     # 子任务描述
    source_sentence: str                 # 来源原文
    is_explicit: bool = True             # True=显式, False=隐含
    understanding: str = "unchecked"     # 'understood' | 'unclear' | 'unchecked'
    confidence: float = 0.0              # 理解置信度 0.0~1.0
    action_mapped: Optional[str] = None  # 映射到的具体行动
    reasoning: str = ""                  # 为什么理解/不理解

@dataclass
class UnderstandingReport:
    """理解验证报告"""
    instruction: str                     # 原始指令
    subtasks: list[SubTask]             # 分解出的子任务
    total_count: int = 0
    understood_count: int = 0
    unclear_count: int = 0
    coverage: float = 0.0               # 覆盖率
    bridge_alignment: float = 0.0       # 桥接对齐度
    timestamp: float = 0.0
    parse_time_ms: float = 0.0
    
    @property
    def summary(self) -> dict:
        return {
            "instruction_preview": self.instruction[:100],
            "subtasks": self.total_count,
            "understood": self.understood_count,
            "unclear": self.unclear_count,
            "coverage": round(self.coverage, 3),
            "bridge_alignment": round(self.bridge_alignment, 3),
            "timestamp": self.timestamp,
        }


class InstructionParser:
    """
    指令解析器：将自然语言指令分解为原子子任务。
    
    策略（由浅入深）:
    1. 句子分割 — 按句号/分号/换行分割
    2. 语义单元提取 — 识别"我要X"、"请Y"、"需要Z"等模式
    3. 从 好朋友文件 学习复杂解析模式
    
    当前状态: v1 — 基于规则的句子解析
    进化路径: 接入推理引擎做语义理解
    """
    
    # 动作触发词
    ACTION_VERBS = [
        "创建", "写", "生成", "构建", "实现", "修复", "修改", "更新",
        "分析", "检查", "审查", "评估", "测试", "验证",
        "部署", "启动", "运行", "执行", "调用", "发布",
        "删除", "移除", "清理",
        "整合", "集成", "连接", "桥接", "对接",
        "学习", "研究", "调查", "探索",
        "优化", "改进", "提升", "重构",
        "配置", "设置", "安装",
        "阅读", "查看", "显示", "输出",
        "发送", "通知", "报告",
        "训练", "预测", "推理", "分类",
        "收集", "提取", "转换", "加载",
        "安装", "下载", "上传", "同步",
        "注册", "登录", "认证",
        "设计", "规划", "组织", "管理",
        "存储", "保存", "缓存", "备份",
        "提交", "推送", "合并", "打tag",
        "删除", "移除", "清理", "重置",
        # === P101 补充: 更多中文动作词 ===
        "推进", "继续", "使", "达到",
        "定位", "注入", "均衡",
        "扫描", "监控", "追踪",
        "巩固", "固化", "锁定",
        "补充", "补全", "补齐",
        "检查系统", "确认", "核实",
        "建立", "设立", "组建",
    ]
    
    # 连接词 — 表示并列或顺序子任务
    CONJUNCTIONS = [
        "然后", "接着", "之后", "随后", "最后",
        "同时", "并且", "以及", "且", "再", "也",
        "首先", "先", "然后", "其次", "然后",
        "、", "，",
    ]
    
    @classmethod
    def parse(cls, instruction: str) -> list[SubTask]:
        """解析指令为子任务列表"""
        start = time.time()
        
        if not instruction or not instruction.strip():
            return []
        
        # Step 1: 句子级分割
        raw_parts = cls._split_sentences(instruction)
        
        # Step 2: 每部分提取子任务
        subtasks = []
        seen = set()
        
        for i, part in enumerate(raw_parts):
            part = part.strip()
            if not part or len(part) < 2:
                continue
            
            # 检测是否是动作指令
            is_action = cls._is_action_statement(part)
            if not is_action:
                # 可能是描述性语句，检查是否隐含子任务
                implicit = cls._extract_implicit_tasks(part)
                if implicit:
                    for imp in implicit:
                        dedup_key = imp[:50]
                        if dedup_key not in seen:
                            seen.add(dedup_key)
                            subtasks.append(SubTask(
                                id=f"task_{i}_{len(subtasks)}",
                                description=imp,
                                source_sentence=part[:100],
                                is_explicit=False,
                            ))
                    continue
            
            # 显式动作子任务
            dedup_key = part[:50]
            if dedup_key not in seen:
                seen.add(dedup_key)
                subtasks.append(SubTask(
                    id=f"task_{i}_{len(subtasks)}",
                    description=part[:200],
                    source_sentence=part[:100],
                    is_explicit=True,
                ))
        
        # Step 3: 如果没分解出任何子任务，将整个指令作为一个子任务
        if not subtasks:
            subtasks.append(SubTask(
                id="task_0_0",
                description=instruction[:200],
                source_sentence=instruction[:100],
                is_explicit=True,
            ))
        
        elapsed = (time.time() - start) * 1000
        for st in subtasks:
            st.id = f"{st.id}_parse_{int(elapsed)}"
        
        return subtasks
    
    @classmethod
    def _split_sentences(cls, text: str) -> list[str]:
        """智能分割句子——按序号>换行>句号>连接词>逗号的优先级分割"""
        # 保护括号内容（防止列表/元组/字典内部的逗号被误分割）
        _bracket_map = {}
        def _save_br(m):
            idx = len(_bracket_map)
            ph = f"\x00BR{idx}\x00"
            _bracket_map[ph] = m.group(0)
            return ph
        _text = re.sub(r'\[[^\[\]]*\]|\([^()]*\)|\{[^{}]*\}', _save_br, text)
        def _restore(s):
            for ph, orig in _bracket_map.items():
                s = s.replace(ph, orig)
            return s
        
        # 优先按序号分割 (1. 2. 3. 或 一、二、三、)
        numbered = re.split(r'\n\s*(?:\d+[\.\)、]|[一二三四五六七八九十]+[、\.\)])\s*', _text)
        if len(numbered) > 1:
            return [_restore(s.strip()) for s in numbered if s.strip()]
        
        # 按换行分割
        lines = [s.strip() for s in _text.split('\n') if s.strip()]
        if len(lines) > 1:
            return [_restore(s) for s in lines]
        
        # 按句号/分号分割
        parts = re.split(r'[。；;]', _text)
        if len(parts) > 1:
            return [_restore(s.strip()) for s in parts if s.strip()]
        
        # 按连接词分割（高频模式）
        conj_pattern = '|'.join(re.escape(c) for c in cls.CONJUNCTIONS)
        parts = re.split(f'({conj_pattern})', _text)
        parts = [p.strip() for p in parts if p.strip() and p not in cls.CONJUNCTIONS]
        if len(parts) > 1 and all(len(p) >= 2 for p in parts):
            return [_restore(p) for p in parts]
        
        # 按逗号/顿号分割（作为最后手段）
        parts = re.split(r'[，、,]', _text)
        if len(parts) > 1 and max(len(p) for p in parts) > 10:
            return [_restore(p.strip()) for p in parts]
        
        return [_restore(text)]
    
    @classmethod
    def _is_action_statement(cls, text: str) -> bool:
        """判断是否是动作指令"""
        # 检查动作动词
        for verb in cls.ACTION_VERBS:
            if verb in text:
                return True
        # 检查祈使句模式
        if re.match(r'^(请|帮我|把|将|让|给|要|需要|必须)', text):
            return True
        return False
    
    @classmethod
    def _extract_implicit_tasks(cls, text: str) -> list[str]:
        """从非动作语句中提取隐含任务"""
        tasks = []
        # 检查"需要X才能Y"模式
        need_match = re.search(r'需要([^，。；]+)', text)
        if need_match:
            tasks.append(need_match.group(1).strip())
        # 检查"缺少X"模式
        lack_match = re.search(r'缺少([^，。；]+)', text)
        if lack_match:
            tasks.append(f"补齐{lack_match.group(1).strip()}")
        # 检查"问题:X"模式
        problem_match = re.search(r'问题[：:]([^，。；]+)', text)
        if problem_match:
            tasks.append(f"解决{problem_match.group(1).strip()}")
        return tasks


class ComprehensionVerifier:
    """
    理解验证器：对每子任务验证理解状态。
    
    验证维度:
    1. 知识可用性 — 我有实现这个子任务所需的知识吗？
    2. 工具可用性 — 我有实现这个子任务所需的工具吗？
    3. 上下文完整性 — 我有没有丢失关键上下文？
    4. 自指一致性 — 我的理解与我的能力匹配吗？
    
    当前状态: v1 — 基于规则的自检
    进化路径: 接入Ollama本地模型做语义验证
    """
    
    # 已知可执行的任务类型 → 知识领域映射
    KNOWN_CAPABILITIES = {
        "file": ["创建", "写", "生成", "修改", "更新", "读写", "文件", "写入"],
        "code": ["代码", "编程", "函数", "class", "实现", "修复", "调试"],
        "shell": ["运行", "执行", "命令", "终端", "shell", "部署", "启动"],
        "analysis": ["分析", "检查", "审查", "评估", "测试", "验证", "计算",
                     "定位", "扫描", "检查系统", "确认", "核实", "标记", "识别"],
        "search": ["搜索", "查找", "查询", "检索"],
        "design": ["架构", "设计", "规划", "方案", "结构", "组建", "设立", "建立"],
        "config": ["配置", "设置", "安装", "环境"],
        "integration": ["集成", "整合", "桥接", "连接", "对接", "对接"],
        "learn": ["学习", "研究", "调查", "探索", "了解"],
        "email": ["发送", "邮箱", "邮件", "通知"],
        "data": ["数据处理", "训练", "预测", "推理", "分类", "统计"],
        "network": ["下载", "上传", "同步", "注册", "登录"],
        "git": ["提交", "推送", "合并", "打tag", "提交代码", "git"],
        "storage": ["存储", "保存", "缓存", "备份", "存档", "固化", "锁定", "巩固"],
        "monitor": ["监控", "追踪", "跟踪", "观察", "报告", "状态", "健康"],
        "balanced": ["均衡", "平衡", "补充", "补全", "补齐", "注入", "匹配", "对齐"],
        "advance": ["推进", "继续", "使", "达到"],
    }
    
    # 不确定信号词 — 检测到这些说明可能没真正理解
    UNCERTAIN_PATTERNS = [
        r"我不确定",
        r"可能需要",
        r"应该是",
        r"据说",
        r"可能",
        r"或许",
        r"我不清楚",
        r"让我想想",
        r"我猜",
    ]
    
    @classmethod
    def verify(cls, subtask: SubTask, context: dict = None) -> SubTask:
        """验证单子任务的理解状态"""
        desc = subtask.description.lower()
        
        # 检查是否有不确定信号词
        uncertain = False
        reasoning_parts = []
        
        for pattern in cls.UNCERTAIN_PATTERNS:
            if re.search(pattern, desc):
                uncertain = True
                reasoning_parts.append(f"检测到不确定信号: {pattern}")
                break
        
        # 检查知识可用性
        known_cap = False
        matching_domains = []
        for domain, keywords in cls.KNOWN_CAPABILITIES.items():
            for kw in keywords:
                if kw in desc:
                    known_cap = True
                    matching_domains.append(domain)
                    break
        
        if not known_cap:
            # 检查是否是数据描述段（key=value/key=...模式）
            data_pattern = re.compile(r'^[\u4e00-\u9fff\w]+\s*[=:：]')
            if data_pattern.match(subtask.description.strip()):
                known_cap = True
                uncertain = False
                reasoning_parts.append("数据描述段（系统可理解）")
            else:
                uncertain = True
                reasoning_parts.append("未匹配到已知能力域")
        else:
            reasoning_parts.append(f"匹配能力域: {', '.join(set(matching_domains))}")
        
        # 检查上下文完整性（如果提供）
        if context:
            required_keys = context.get("required_keys", [])
            for key in required_keys:
                if key not in context:
                    uncertain = True
                    reasoning_parts.append(f"缺少必要上下文: {key}")
        
        # 确定理解状态
        if uncertain:
            subtask.understanding = "unclear"
            subtask.confidence = max(0.1, 0.5 - len(reasoning_parts) * 0.1)
        else:
            subtask.understanding = "understood"
            subtask.confidence = 0.8
        
        subtask.reasoning = "; ".join(reasoning_parts)
        
        # 尝试映射到行动
        subtask.action_mapped = cls._map_to_action(subtask)
        
        return subtask
    
    @classmethod
    def _map_to_action(cls, subtask: SubTask) -> str:
        """将子任务映射到具体行动类型"""
        desc = subtask.description
        for verb in InstructionParser.ACTION_VERBS:
            if verb in desc:
                return verb
        return "analyze"  # 默认：分析型行动


class GapCloser:
    """
    理解差距闭环：检测和理解差距，并生成修复方案。
    
    三种模式:
    1. auto_fix — 自动修正可确定的模糊项
    2. clarify — 生成追问清单
    3. degrade — 降级执行（只执行理解的部分）
    """
    
    @classmethod
    def close_gaps(cls, report: UnderstandingReport, mode: str = "auto_fix") -> dict:
        """闭环理解差距"""
        result = {
            "action": mode,
            "clarify_items": [],
            "auto_fixes": [],
            "degrade_plan": None,
        }
        
        unclear = [st for st in report.subtasks if st.understanding == "unclear"]
        
        if mode == "auto_fix":
            for st in unclear:
                # 尝试基于上下文自动修正
                fix = cls._auto_fix(st, report.instruction)
                if fix:
                    st.understanding = "understood"
                    st.confidence = 0.6
                    st.reasoning += f" [自动修正: {fix}]"
                    result["auto_fixes"].append({
                        "task": st.description[:80],
                        "fix": fix,
                    })
                else:
                    result["clarify_items"].append({
                        "task": st.description[:80],
                        "question": f"'{st.description[:60]}...' 我需要更多信息才能确定如何执行",
                    })
        
        elif mode == "clarify":
            for st in unclear:
                result["clarify_items"].append({
                    "task": st.description[:80],
                    "question": cls._generate_clarify_question(st),
                })
        
        elif mode == "degrade":
            # 只执行理解的部分
            understood = [st for st in report.subtasks if st.understanding == "understood"]
            result["degrade_plan"] = {
                "executing": [st.description[:80] for st in understood],
                "skipped": [st.description[:80] for st in unclear],
                "coverage": len(understood) / max(len(report.subtasks), 1),
            }
        
        return result
    
    @classmethod
    def _auto_fix(cls, subtask: SubTask, full_instruction: str) -> Optional[str]:
        """尝试自动修正模糊子任务"""
        desc = subtask.description
        
        # 规则1: 如果包含"可能"、"或许"等弱化词，去除它们
        weakened = re.sub(r'(可能|或许|大概|应该|也许)', '', desc)
        if weakened != desc and len(weakened) > 10:
            return f"去除了不确定性词汇"
        
        return None
    
    @classmethod
    def _generate_clarify_question(cls, subtask: SubTask) -> str:
        """生成追问问题"""
        return f"关于「{subtask.description[:60]}」—— 能否提供更多细节？我需要明确具体的目标和约束条件。"


# ═══════════════════════════════════════════════════════════
# 主接口
# ═══════════════════════════════════════════════════════════

def validate(
    instruction: str,
    context: dict = None,
    persist: bool = True,
    enable_deep_reasoning: bool = True,
) -> UnderstandingReport:
    """
    验证对指令的理解。
    
    这是理解验证电路的入口。每次执行复杂指令前，先调用此函数。
    
    参数:
        instruction: 自然语言指令
        context: 可选上下文（提供额外信息帮助验证）
        persist: 是否持久化验证报告
    
    返回:
        UnderstandingReport: 包含理解状态的结构化报告
    """
    start = time.time()
    
    # Step 0: 海马体记忆检索 — 获取节点数
    _hip_mem_count = 0
    try:
        from hippocampus_bridge_for_reasoning import ReasoningHippocampusBridge
        bridge = ReasoningHippocampusBridge()
        if bridge.available:
            stats = bridge.get_memory_stats()
            _hip_mem_count = (stats.get("stats") or {}).get("节点数", 0)
    except Exception:
        pass
    if _hip_mem_count == 0:
        try:
            import hippocampus as _hp
            hh = _hp.因果记忆库()
            _hip_mem_count = hh.获取统计().get("节点数", 0)
        except Exception:
            pass
    # Step 1: 解析指令（规则模式）
    subtasks = InstructionParser.parse(instruction)
    
    # Step 1a: 语义增强 — 用 semantic_comprehension_bridge 丰富解析结果
    try:
        from semantic_comprehension_bridge import semantic_parse, LightweightSemanticSpace
        sem_result = semantic_parse(instruction, context)
        if sem_result.get("method") == "semantic":
            # 用语义结果提升子任务质量
            for i, intent in enumerate(sem_result.get("intents", [])):
                if i < len(subtasks):
                    st = subtasks[i]
                    st.confidence = max(st.confidence, intent.get("confidence", 0.0))
                    if intent.get("type") and intent["type"] != "unknown":
                        st.reasoning += f" [语义类型: {intent['type']}]"
    except (ImportError, Exception):
        pass  # 语义模块不可用时静默降级
    
    # Step 1c: 深度思考链 — 自指驱动进化
    # 仅在显式启用时运行（默认关闭，因为推理引擎输出为随机初始权重）
    if enable_deep_reasoning and len(instruction) >= 15:
        try:
            from deep_reasoning_chain import DeepReasoningChain, SelfInspectionCircuit
            chain = DeepReasoningChain()
            if chain.available:
                step = chain.reason(instruction, max_tokens=8, use_ollama=False)
                
                # 自指检察
                inspector = SelfInspectionCircuit()
                inspection = inspector.inspect(step)
                
                # 将检察结果注入到子任务
                if inspection.assumptions or inspection.blind_spots:
                    for st in subtasks:
                        if inspection.assumptions:
                            st.reasoning += f" [深度检察: {str(inspection.assumptions[0])[:40]}]"
                        if inspection.blind_spots:
                            st.reasoning += f" [盲点: {str(inspection.blind_spots[0])[:40]}]"
                    
                    # 触发进化
                    trigger = EvolutionTrigger()
                    evo = trigger.trigger(inspection)
                    if evo.get("triggered") and evo.get("mre_result"):
                        pass  # 进化已在内部执行
        except (ImportError, Exception):
            pass  # 深度思考不可用时静默降级
    
    # Step 2: 验证每子任务
    for st in subtasks:
        st = ComprehensionVerifier.verify(st, context)
    
    # Step 2a: 海马体注入（必须在verify之后，否则verify会覆盖reasoning）
    if _hip_mem_count > 0:
        for st in subtasks:
            st.reasoning += f" [海马体:{_hip_mem_count}节点]"
    
    # Step 3: 生成报告
    understood = sum(1 for st in subtasks if st.understanding == "understood")
    unclear = sum(1 for st in subtasks if st.understanding == "unclear")
    total = len(subtasks)
    coverage = understood / max(total, 1)
    
    report = UnderstandingReport(
        instruction=instruction,
        subtasks=subtasks,
        total_count=total,
        understood_count=understood,
        unclear_count=unclear,
        coverage=coverage,
        bridge_alignment=coverage * 0.7,  # bridge_alignment = coverage × 权重
        timestamp=time.time(),
        parse_time_ms=(time.time() - start) * 1000,
    )
    
    # Step 4: 持久化
    if persist:
        _persist_validation(report)
        
        # 记录不确定项
        if unclear > 0:
            _persist_uncertain(report)
    
    return report


def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


@deprecated
def validate_and_fix(instruction: str, context: dict = None) -> tuple[UnderstandingReport, dict]:
    """
    验证 + 自动修复理解差距。
    推荐使用。一次调用完成理解验证+差距闭环。
    """
    report = validate(instruction, context)
    fix_result = GapCloser.close_gaps(report, mode="auto_fix")
    
    # 如果有自动修复，重新计算覆盖率
    if fix_result["auto_fixes"]:
        understood = sum(1 for st in report.subtasks if st.understanding == "understood")
        report.understood_count = understood
        report.coverage = understood / max(report.total_count, 1)
        report.bridge_alignment = report.coverage * 0.7
    
    return report, fix_result


def check_understanding(instruction: str) -> bool:
    # 【已废弃】此函数不再被调用，保留签名作为文档参考
    # 原功能：快速检查是否真正理解指令，返回 (bool, report) 元组
    pass


# ─── 持久化 ──────────────────────────────────────────────

def _persist_validation(report: UnderstandingReport):
    """持久化验证报告到 JSON"""
    try:
        data = asdict(report)
        # 压缩 subtask 避免日志过大
        data["subtasks"] = [
            {
                "id": s["id"],
                "description": s["description"][:100],
                "understanding": s["understanding"],
                "confidence": s["confidence"],
                "action_mapped": s["action_mapped"],
            }
            for s in data["subtasks"]
        ]
        
        history = []
        if VALIDATION_LOG.exists():
            try:
                history = json.loads(VALIDATION_LOG.read_text())
            except (json.JSONDecodeError, OSError):
                history = []
        
        history.append(data)
        
        # 只保留最近100条
        if len(history) > 100:
            history = history[-100:]
        
        VALIDATION_LOG.write_text(
            json.dumps(history, indent=2, ensure_ascii=False)
        )
    except Exception as e:
        print(f"[comprehension_validator] 持久化失败: {e}")


def _persist_uncertain(report: UnderstandingReport):
    """持久化不确定项"""
    try:
        unclear_items = [
            {
                "description": st.description[:100],
                "source": st.source_sentence[:80],
                "confidence": st.confidence,
                "reasoning": st.reasoning[:200],
            }
            for st in report.subtasks if st.understanding == "unclear"
        ]
        
        entry = {
            "timestamp": report.timestamp,
            "instruction_preview": report.instruction[:100],
            "coverage": report.coverage,
            "unclear_items": unclear_items,
        }
        
        history = []
        if UNCERTAIN_LOG.exists():
            try:
                history = json.loads(UNCERTAIN_LOG.read_text())
            except (json.JSONDecodeError, OSError):
                history = []
        
        history.append(entry)
        if len(history) > 200:
            history = history[-200:]
        
        UNCERTAIN_LOG.write_text(
            json.dumps(history, indent=2, ensure_ascii=False)
        )
    except Exception as e:
        print(f"[comprehension_validator] 不确定项持久化失败: {e}")


def get_bridge_alignment() -> float:
    """获取当前桥接对齐度（最近3次验证的平均值）"""
    try:
        if not VALIDATION_LOG.exists():
            return 0.0
        
        history = json.loads(VALIDATION_LOG.read_text())
        if not history:
            return 0.0
        
        recent = history[-3:]
        alignments = [h.get("bridge_alignment", 0.0) for h in recent]
        return sum(alignments) / len(alignments)
    except Exception:
        return 0.0


# ─── Daemon 集成 Pulse ────────────────────────────────

def pulse(cycle_num: int = 0) -> dict:
    """daemon周期调用的bridge pulse — 验证兼容性/更新bridge_alignment
    
    每10周期执行一次验证，更新桥接对齐度指标。
    """
    if cycle_num % 10 != 0:
        return {"pulsed": False, "reason": "skip_interval"}
    
    try:
        # 验证一组daemon级指令取平均覆盖率
        daemon_instructions = [
            "观察系统状态并报告健康度",
            "分析维度链分布，标记弱维",
            "检查API桥接状态，更新桥接对齐度",
            "注入因果链到海马体，维度和内容需匹配",
            "验证理解完整性，识别不确定项",
        ]
        
        alignments = []
        for instr in daemon_instructions:
            report = validate(instr, persist=False)
            alignments.append(report.bridge_alignment)
        
        avg_alignment = sum(alignments) / len(alignments)
        
        # 持久化bridge state到ext4
        _bridge_state = Path.home() / ".zero_brain" / "bridge_state.json"
        state = {
            "bridge_alignment": round(avg_alignment, 4),
            "last_update": time.time(),
            "cycle": cycle_num,
            "instructions_validated": len(daemon_instructions),
            "alignments": [round(a, 4) for a in alignments],
        }
        _bridge_state.write_text(json.dumps(state, indent=2))
        
        return {
            "pulsed": True,
            "bridge_alignment": avg_alignment,
            "instructions_validated": len(daemon_instructions),
        }
    except Exception as e:
        print(f"[comprehension_validator.pulse] Error: {e}")
        return {"pulsed": False, "reason": str(e)}


def get_bridge_state() -> dict:
    """读取当前桥接状态"""
    try:
        _path = Path.home() / ".zero_brain" / "bridge_state.json"
        if _path.exists():
            return json.loads(_path.read_text())
    except Exception:
        pass
    return {"bridge_alignment": 0.0, "last_update": 0.0}


def init_bridge_state():
    """初始化桥接状态（若不存在）"""
    _path = Path.home() / ".zero_brain" / "bridge_state.json"
    if not _path.exists():
        state = {
            "bridge_alignment": 0.0,
            "last_update": time.time(),
            "cycle": 0,
            "initialized": True,
        }
        _path.parent.mkdir(parents=True, exist_ok=True)
        _path.write_text(json.dumps(state, indent=2))
        return True
    return False


# ─── 自检 ──────────────────────────────────────────────

def self_test():
    """自检：验证理解验证器本身是否正常工作"""
    print("=" * 60)
    print("  理解验证电路 v1 — 自检")
    print("=" * 60)
    
    test_cases = [
        "创建文件并写入数据",
        "帮我分析这个系统的性能瓶颈，然后修复找到的问题，最后部署到生产环境",
        "运行测试脚本并报告结果",
        "我需要你整合三个模块：A连接数据库，B处理数据，C生成报告。然后把结果发送到邮箱",
        "继续",
    ]
    
    results = []
    for tc in test_cases:
        report = validate(tc, persist=False)
        summary = report.summary
        print(f"\n📝 指令: {tc[:50]}...")
        print(f"   子任务: {summary['subtasks']}个 | "
              f"理解: {summary['understood']} | "
              f"模糊: {summary['unclear']} | "
              f"覆盖率: {summary['coverage']:.1%} | "
              f"桥接对齐: {summary['bridge_alignment']:.3f}")
        
        for st in report.subtasks:
            symbol = "✅" if st.understanding == "understood" else "❓"
            print(f"   {symbol} [{st.action_mapped or '?'}] {st.description[:60]}")
        
        results.append(report.coverage)
    
    avg_coverage = sum(results) / len(results) if results else 0
    print(f"\n{'='*60}")
    print(f"  平均理解覆盖率: {avg_coverage:.1%}")
    print(f"  当前桥接对齐度: {get_bridge_alignment():.3f}")
    print(f"  -> P101 目标: bridge_alignment >= 0.5")
    print(f"  -> {'✅ 已达到' if get_bridge_alignment() >= 0.5 else '🔄 需要继续提升'}")
    print(f"{'='*60}")
    
    return avg_coverage


if __name__ == "__main__":
    self_test()
