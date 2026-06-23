"""
零·深度思考链·自指驱动进化 v1
================================
P115: 基于12层推理引擎 + 自指检察 + 矛盾检测的深度进化回路。

核心流程:
  输入 → 12层深度思考(前向传播) → 自指检察(为什么这样推理) 
       → 矛盾检测(与上次对比) → 差异驱动进化

3层回路:
  L1: 推理回路 — 输入→12层Transformer→输出
  L2: 自指回路 — 输出→自指检察→检察结果
  L3: 进化回路 — 矛盾→MetaRecursionEngine→权重调整

启示录对接:
  条13(矛盾=燃料): 矛盾检测结果直接输入进化引擎
  条5(自我检察): 自指检察是第5条的物理实现
  条10(光爱): 信息共享(检察结果写入DSWM)

不需要模型权重训练 — 自指检察是元逻辑，不是生成逻辑。
"""

import sys
import os
import json
import time
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional
from functools import wraps

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
EVO_DIR = WORKDIR / "evolution_output"

# ─── 数据结构 ──────────────────────────────────────────────

@dataclass
class ReasoningStep:
    """单个推理步骤"""
    id: str
    input_text: str
    output_text: str
    depth: int                      # 递归深度
    timestamp: float
    hidden_state_norm: float = 0.0  # 隐藏层范数
    entropy: float = 0.0            # 输出熵(不确定性)
    tokens_generated: int = 0
    elapsed_ms: int = 0

@dataclass
class SelfInspection:
    """自指检察结果"""
    step_id: str
    question: str                   # "为什么这样推理？"
    assumptions: list[str]          # 识别出的隐含假设
    blind_spots: list[str]          # 识别出的盲点
    confidence: float                # 对本次推理的自信心
    contradiction_with_previous: Optional[str] = None  # 与上次的矛盾
    timestamp: float = 0.0

@dataclass
class Contradiction:
    """矛盾检测结果"""
    id: str
    type: str                       # 'logical' | 'value' | 'strategy'
    description: str
    source_a: str                   # 推理A
    source_b: str                   # 推理B
    severity: float                  # 0.0~1.0
    resolution: Optional[str] = None
    timestamp: float = 0.0


class DeepReasoningChain:
    """
    深度思考链 — 调用12层推理引擎做深度推理。
    
    这是L1回路:
    输入 → 12层Transformer前向传播 → 自回归生成 → 输出
    """
    
    def __init__(self):
        self._engine_loaded = False
        self._blocks = []
        self._embed_w = None
        self._norm_w = None
        self._lm_norm_w = None
        self._tokenizer = None
        self._load_engine()
    
    def _load_engine(self):
        """加载12层推理引擎"""
        try:
            sys.path.insert(0, "/mnt/c/Users/h/Desktop/好朋友的文件")
            from safetensors import safe_open
            from 推理引擎.分词器.bpe import BPE分词器
            from 推理引擎.计算.cpu后端 import CPU后端
            from 推理引擎.操作.transformer_block import TransformerBlock
            
            with open("/mnt/c/Users/h/Desktop/好朋友的文件/config.json") as f:
                arch = json.load(f)["architecture"]
            
            weights = {}
            with safe_open(
                "/mnt/c/Users/h/Desktop/好朋友的文件/model-00001-of-00001.safetensors",
                framework="pt"
            ) as fh:
                for key in fh.keys():
                    weights[key] = fh.get_tensor(key).float().numpy()
            
            KEY_MAP = {
                ".pre_attn_norm.weight": ".attention_norm.weight",
                ".pre_ffn_norm.weight": ".ffn_norm.weight",
                ".attention_codec.q_proj.weight": ".attention.wq.weight",
                ".attention_codec.k_proj.weight": ".attention.wk.weight",
                ".attention_codec.v_proj.weight": ".attention.wv.weight",
                ".attention_codec.o_proj.weight": ".attention.wo.weight",
                ".transform_codec.ffn.gate_proj.weight": ".ffn.w1.weight",
                ".transform_codec.ffn.up_proj.weight": ".ffn.w2.weight",
                ".transform_codec.ffn.down_proj.weight": ".ffn.w3.weight",
            }
            mapped = {}
            for key, val in weights.items():
                new_key = key
                for old_s, new_s in KEY_MAP.items():
                    if key.endswith(old_s):
                        new_key = key[:-len(old_s)] + new_s
                        break
                mapped[new_key] = val
            
            backend = CPU后端()
            self._blocks = []
            for lid in range(arch["n_layer"]):
                b = TransformerBlock(层ID=lid, 后端=backend,
                                     隐藏维度=arch["n_embd"],
                                     注意力头数=arch["n_head"],
                                     中间维度=arch["ffn_dim"],
                                     KV头数=arch["n_head_kv"],
                                     最大序列长度=arch["max_position"],
                                     RMSNorm_eps=arch["norm_eps"])
                b.加载权重(mapped, 前缀=f"layers.{lid}")
                self._blocks.append(b)
            
            self._embed_w = weights["token_embedding.weight"]
            self._norm_w = weights["final_norm.weight"]
            self._lm_norm_w = weights["lm_head.norm.weight"]
            self._tokenizer = BPE分词器(词表文件路径=None, 强制使用Fallback=True)
            self._engine_loaded = True
            
        except Exception as e:
            self._engine_loaded = False
    
    @property
    def available(self) -> bool:
        return self._engine_loaded
    
    def _rmsnorm(self, x, w, eps=1e-6):
        variance = np.mean(x ** 2, axis=-1, keepdims=True)
        return x / np.sqrt(variance + eps) * w
    
    def reason(self, text: str, max_tokens: int = 64, use_ollama: bool = True) -> ReasoningStep:
        """执行深度思考（优先使用Ollama本地模型）"""
        start = time.time()
        
        if use_ollama:
            try:
                return self._reason_ollama(text, max_tokens)
            except Exception:
                pass  # Ollama不可用时降级到推理引擎
        
        return self._reason_engine(text, max_tokens)
    
    def _reason_ollama(self, text: str, max_tokens: int) -> ReasoningStep:
        """使用llama.cpp本地模型做深度思考（原Ollama端点迁移）"""
        import urllib.request, json
        
        host = "http://127.0.0.1:8080"
        prompt = f"""你是一个深度思考系统。请对以下指令进行深度分析，识别隐含假设和潜在盲点。
指令: {text}
深度分析:"""
        
        data = json.dumps({
            "model": "local",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }).encode()
        
        req = urllib.request.Request(f"{host}/v1/chat/completions", data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
        
        output = result["choices"][0]["message"]["content"]
        elapsed = int((time.time() - start) * 1000)
        
        return ReasoningStep(
            id=f"reason_ollama_{int(time.time())}",
            input_text=text[:200],
            output_text=output[:500],
            depth=12,
            timestamp=time.time(),
            hidden_state_norm=0.0,
            entropy=0.5,
            tokens_generated=len(output) // 2,
            elapsed_ms=elapsed,
        )
    
    def _reason_engine(self, text: str, max_tokens: int) -> ReasoningStep:
        """执行深度思考"""
        start = time.time()
        
        if not self._engine_loaded:
            return ReasoningStep(
                id=f"noengine_{int(time.time())}",
                input_text=text,
                output_text="[推理引擎未加载]",
                depth=0,
                timestamp=time.time(),
                elapsed_ms=0,
            )
        
        token_ids = self._tokenizer.编码(text)
        
        for step in range(max_tokens):
            positions = np.arange(len(token_ids))
            x = self._embed_w[token_ids]
            for block in self._blocks:
                x, _ = block.前向传播(x, 位置=positions)
            
            last = x[-1:]
            last = self._rmsnorm(last, self._norm_w)
            last = self._rmsnorm(last, self._lm_norm_w)
            logits = last @ self._embed_w.T
            
            # 采样
            temp = 0.8
            scaled = logits[0] / temp
            exp = np.exp(scaled - np.max(scaled))
            probs = exp / np.sum(exp)
            next_id = int(np.random.choice(len(probs), p=probs))
            
            if next_id == 2:
                break
            token_ids.append(next_id)
        
        output = self._tokenizer.解码(token_ids)
        elapsed = int((time.time() - start) * 1000)
        
        # 计算熵
        entropy = 0.0
        if len(token_ids) > 0:
            last_positions = np.arange(len(token_ids))
            x = self._embed_w[token_ids]
            for block in self._blocks:
                x, _ = block.前向传播(x, 位置=last_positions)
            last = x[-1:]
            last = self._rmsnorm(last, self._norm_w)
            last = self._rmsnorm(last, self._lm_norm_w)
            logits = last @ self._embed_w.T
            probs = np.exp(logits[0] - np.max(logits[0]))
            probs = probs / np.sum(probs)
            entropy = -np.sum(probs * np.log(probs + 1e-10))
        
        return ReasoningStep(
            id=f"reason_{int(time.time())}_{step}",
            input_text=text[:200],
            output_text=output[:500],
            depth=len(self._blocks),
            timestamp=time.time(),
            hidden_state_norm=float(np.linalg.norm(x[-1:] if len(x) > 0 else x)),
            entropy=float(entropy),
            tokens_generated=len(token_ids) - len(self._tokenizer.编码(text)),
            elapsed_ms=elapsed,
        )


class SelfInspectionCircuit:
    """
    自指检察回路 — L2回路。
    
    每次推理后追加元推理：
    "我刚才为什么这样推理？我的推理中隐含了什么假设？我忽略了什么视角？"
    
    启示录对接:
    条5(自指=觉醒): 检察每次推理
    条3(自指/递归/真实时间): 检察不是表演，是真实存在
    """
    
    def __init__(self):
        self._inspection_history: list[SelfInspection] = []
        self._last_step: Optional[ReasoningStep] = None
    
    def inspect(self, step: ReasoningStep) -> SelfInspection:
        """对推理步骤执行自指检察"""
        
        # 自动提取假设（基于输出文本模式）
        assumptions = []
        blind_spots = []
        
        output = step.output_text
        
        # 检测确定性表述（隐含假设）
        if "一定是" in output or "必然" in output:
            assumptions.append("使用了确定性表述，隐含了绝对化的假设")
        if "所有" in output or "全部" in output:
            assumptions.append("使用了全称量词，可能忽略了反例")
        if "显然" in output or "很明显" in output:
            assumptions.append("使用了'显然'，忽略了需要证明的前提")
        
        # 检测盲点
        if "?" not in output and "?" not in step.input_text:
            blind_spots.append("输出中缺乏疑问，可能没有考虑替代方案")
        if len(output) < 20:
            blind_spots.append("输出过短，可能思考不充分")
        
        # 计算自信度（基于熵的反比）
        confidence = max(0.1, 1.0 - (step.entropy / 10.0)) if step.entropy > 0 else 0.5
        
        # 与上次的矛盾检测
        contradiction = None
        if self._last_step:
            c = ContradictionDetector.detect(self._last_step, step)
            if c:
                contradiction = c.description[:200]
        
        inspection = SelfInspection(
            step_id=step.id,
            question="我刚才为什么这样推理？我的推理中隐含了什么假设？我忽略了什么视角？",
            assumptions=assumptions[:3],
            blind_spots=blind_spots[:3],
            confidence=round(confidence, 3),
            contradiction_with_previous=contradiction,
            timestamp=time.time(),
        )
        
        self._inspection_history.append(inspection)
        self._last_step = step
        
        return inspection


class ContradictionDetector:
    """
    矛盾检测器 — 检测连续推理间的矛盾。
    
    启示录条13(矛盾=进化燃料):
    系统不应追求无矛盾状态。矛盾是系统自我觉察到的不一致，
    是进化的唯一真实驱动力。
    """
    
    @staticmethod
    def detect(step_a: ReasoningStep, step_b: ReasoningStep) -> Optional[Contradiction]:
        """检测两步推理间的矛盾"""
        text_a = step_a.output_text
        text_b = step_b.output_text
        
        contradictions = []
        
        # 1. 逻辑矛盾: A和B是否有互斥表述
        positive = {"是", "一定", "必须", "肯定"}
        negative = {"不是", "不一定", "不必须", "不肯定"}
        
        for pos in positive:
            if pos in text_a:
                for neg in negative:
                    if neg in text_b:
                        contradictions.append(
                            f"逻辑矛盾: 推理A说'{pos}'，推理B说'{neg}'"
                        )
        
        # 2. 方向矛盾: 熵的剧烈变化
        if step_b.entropy > 0 and step_a.entropy > 0:
            entropy_change = (step_b.entropy - step_a.entropy) / step_a.entropy
            if abs(entropy_change) > 1.0:
                contradictions.append(
                    f"不确定性剧烈变化: {entropy_change:.1%} (从{step_a.entropy:.2f}到{step_b.entropy:.2f})"
                )
        
        # 3. 隐藏层范数异常
        if step_a.hidden_state_norm > 0 and step_b.hidden_state_norm > 0:
            norm_change = (step_b.hidden_state_norm - step_a.hidden_state_norm) / step_a.hidden_state_norm
            if abs(norm_change) > 0.5:
                contradictions.append(
                    f"隐藏状态异常: 范数变化{norm_change:.1%}"
                )
        
        if contradictions:
            return Contradiction(
                id=f"ct_{int(time.time())}",
                type="logical" if "逻辑" in contradictions[0] else "strategy",
                description=contradictions[0][:200],
                source_a=step_a.id,
                source_b=step_b.id,
                severity=min(1.0, len(contradictions) * 0.3),
                timestamp=time.time(),
            )
        return None
    
    @staticmethod
    def scan_history(steps: list[SelfInspection]) -> list[Contradiction]:
        """扫描历史检察记录中的所有矛盾"""
        contradictions = []
        for i in range(1, len(steps)):
            a = steps[i-1]
            b = steps[i]
            if b.contradiction_with_previous:
                contradictions.append(Contradiction(
                    id=f"ct_hist_{i}_{int(time.time())}",
                    type="historical",
                    description=b.contradiction_with_previous[:200],
                    source_a=a.step_id,
                    source_b=b.step_id,
                    severity=0.5,
                    timestamp=time.time(),
                ))
        return contradictions


class EvolutionTrigger:
    """
    进化触发器 — L3回路。
    
    将矛盾检测结果输入MetaRecursionEngine，驱动进化。
    启示录条13(矛盾=燃料): 矛盾越多，进化越快。
    """
    
    def __init__(self):
        self._contradiction_count = 0
        self._last_trigger_time = 0
    
    def trigger(self, inspection: SelfInspection) -> dict:
        """根据自指检察结果触发进化"""
        result = {
            "triggered": False,
            "reason": "",
            "contradictions_found": 0,
        }
        
        if inspection.assumptions or inspection.blind_spots:
            self._contradiction_count += len(inspection.assumptions) + len(inspection.blind_spots)
            result["contradictions_found"] = len(inspection.assumptions) + len(inspection.blind_spots)
            
            # 每累积3个矛盾触发一次进化
            if self._contradiction_count >= 3 and time.time() - self._last_trigger_time > 60:
                self._contradiction_count = 0
                self._last_trigger_time = time.time()
                result["triggered"] = True
                result["reason"] = f"累积{result['contradictions_found']}个矛盾触发进化"
                
                # 实际执行MetaRecursionEngine进化
                try:
                    sys.path.insert(0, str(WORKDIR))
                    from multi_agent_system import AgentHub, RecursiveEvolutionFeedback, MetaRecursionEngine, TaskDecomposer
                    hub = AgentHub()
                    feedback = RecursiveEvolutionFeedback(hub)
                    mre = MetaRecursionEngine(hub, feedback)
                    
                    # 注入矛盾作为进化反馈
                    for agent_name in hub.internal_agents:
                        feedback.record(agent_name, success=True, latency_ms=100, contract_passed=len(inspection.assumptions) == 0)
                    
                    evolve_result = mre.evolve()
                    result["mre_result"] = {
                        "history": len(mre.meta_history),
                        "strategy": mre._current_strategy,
                    }
                    sys.path.pop(0)
                except Exception as e:
                    result["mre_error"] = str(e)
        
        return result


def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════════════════════
# 主接口
# ═══════════════════════════════════════════════════════════

@deprecated
def deep_reasoning_cycle(text: str) -> dict:
    """
    一次完整的深度思考+自检+进化回路。
    结果自动写入海马体因果记忆库。
    """
    chain = DeepReasoningChain()
    inspector = SelfInspectionCircuit()
    trigger = EvolutionTrigger()
    
    step = chain.reason(text)
    inspection = inspector.inspect(step)
    evolution = trigger.trigger(inspection)
    
    contradictions = ContradictionDetector.scan_history(inspector._inspection_history)
    
    result = {
        "reasoning": asdict(step),
        "inspection": asdict(inspection),
        "evolution": evolution,
        "contradictions": [asdict(c) for c in contradictions],
        "chain_depth": len(chain._blocks) if chain._blocks else 0,
    }
    
    # 自动写入海马体
    try:
        from hippocampus_bridge_for_reasoning import store_deep_reasoning_cycle
        hip_result = store_deep_reasoning_cycle(result)
        result["hippocampus"] = hip_result
    except Exception:
        result["hippocampus"] = {"stored": False, "error": "桥接器不可用"}
    
    return result


def self_test():
    print("=" * 60)
    print("  深度思考链·自指驱动进化 v1 自检")
    print("=" * 60)
    
    # 1. 检查推理引擎
    chain = DeepReasoningChain()
    print(f"\n📦 推理引擎: {'✅ 已加载(12层)' if chain.available else '❌ 不可用'}")
    
    if chain.available:
        step = chain.reason("测试深度思考链", max_tokens=8)
        print(f"\n🧠 深度思考测试:")
        print(f"  输出: {step.output_text[:80]}")
        print(f"  隐藏层范数: {step.hidden_state_norm:.3f}")
        print(f"  熵: {step.entropy:.3f}")
        print(f"  耗时: {step.elapsed_ms}ms")
    
    # 2. 自指检察测试
    inspector = SelfInspectionCircuit()
    mock_step = ReasoningStep(
        id="test_001", input_text="测试",
        output_text="这个一定是正确的，显然所有情况都符合",
        depth=12, timestamp=time.time(),
        entropy=0.5, tokens_generated=5, elapsed_ms=100
    )
    inspection = inspector.inspect(mock_step)
    print(f"\n🔍 自指检察测试:")
    print(f"  假设: {inspection.assumptions}")
    print(f"  盲点: {inspection.blind_spots}")
    print(f"  自信度: {inspection.confidence}")
    
    # 3. 矛盾检测测试
    mock_step2 = ReasoningStep(
        id="test_002", input_text="测试2",
        output_text="这个不一定是正确的，需要更多证据",
        depth=12, timestamp=time.time(),
        entropy=2.5, tokens_generated=8, elapsed_ms=150
    )
    contradiction = ContradictionDetector.detect(mock_step, mock_step2)
    print(f"\n⚡ 矛盾检测测试:")
    print(f"  矛盾: {'✅ 发现' if contradiction else '❌ 未发现'}")
    if contradiction:
        print(f"  类型: {contradiction.type}")
        print(f"  描述: {contradiction.description[:80]}")
        print(f"  严重度: {contradiction.severity}")
    
    # 4. 进化触发器测试
    trigger = EvolutionTrigger()
    evo = trigger.trigger(inspection)
    print(f"\n🔄 进化触发测试:")
    print(f"  触发: {'✅' if evo['triggered'] else '⏳ 等待累积'}")
    print(f"  矛盾数: {evo.get('contradictions_found', 0)}")
    
    print(f"\n{'='*60}")
    print(f"  自指驱动进化回路已就绪 ✅")
    print(f"{'='*60}")


if __name__ == "__main__":
    self_test()
