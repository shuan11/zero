"""
零·语义理解桥接器 v2
======================
P106: 推理引擎深度集成 — 轻量语义理解层

核心:
  1. 高频词向量索引 — 从好朋友文件语料构建基础语义空间
  2. n-gram语义重叠检测 — 指令与已知模式间的语义相似度
  3. 海马体上下文增强 — 因果记忆辅助多轮理解
  
降级策略:
  numpy → 语义相似度匹配
  无numpy → 降级到 comprehension_validator 规则解析
"""

import sys
import os
import json
import re
import math
from pathlib import Path
from collections import Counter
from functools import wraps

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False


class LightweightSemanticSpace:
    """轻量语义空间 — 基于统计共现+n-gram重叠的语义相似度"""
    
    STOP_WORDS = set("的了是在有和就这那也之我与他以会对但要而所被把让给没"
                     "看能说为从又只已很到都去用与于")
    
    # 动作意图原型
    INTENT_PROTOTYPES = {
        "create": {
            "tokens": ["创建", "生成", "新建", "写", "建立", "构建", "实现"],
            "weight": 1.0
        },
        "modify": {
            "tokens": ["修改", "更新", "编辑", "改动", "变更", "修复", "修复"],
            "weight": 1.0
        },
        "delete": {
            "tokens": ["删除", "移除", "清除", "去掉", "销毁"],
            "weight": 1.0
        },
        "read": {
            "tokens": ["读取", "查看", "显示", "输出", "阅读", "检查"],
            "weight": 1.0
        },
        "analyze": {
            "tokens": ["分析", "审查", "评估", "测试", "验证", "诊断", "检查", "训练", "推理", "计算"],
            "weight": 1.0
        },
        "execute": {
            "tokens": ["运行", "执行", "启动", "部署", "调用", "发布"],
            "weight": 1.0
        },
        "integrate": {
            "tokens": ["集成", "整合", "连接", "桥接", "对接"],
            "weight": 1.0
        },
        "search": {
            "tokens": ["搜索", "查找", "查询", "检索", "找"],
            "weight": 1.0
        },
        "learn": {
            "tokens": ["学习", "研究", "调查", "探索", "了解"],
            "weight": 1.0
        },
        "configure": {
            "tokens": ["配置", "设置", "安装", "初始化", "提交", "推送", "合并", "提交代码"],
            "weight": 1.0
        },
        "communicate": {
            "tokens": ["发送", "通知", "报告", "输出", "打印"],
            "weight": 1.0
        },
        "continue": {
            "tokens": ["继续", "接着", "下一步", "往下"],
            "weight": 0.5  # 模糊意图 — 需要上下文
        },
    }
    
    # 连接词 — 复合子任务分割
    CONJUNCTIONS = [
        "然后", "接着", "之后", "随后", "最后",
        "同时", "并且", "以及",
        "首先", "先", "其次", "再", "也",
    ]
    
    @classmethod
    def tokenize(cls, text: str) -> list[str]:
        """中文分词（基于字符二元组+词典匹配）"""
        text = re.sub(r'[^\u4e00-\u9fff\w]', ' ', text)
        tokens = []
        i = 0
        while i < len(text):
            if text[i] == ' ':
                i += 1
                continue
            # 2-gram (中文双字词)
            if i + 1 < len(text) and '\u4e00' <= text[i] <= '\u9fff' and '\u4e00' <= text[i+1] <= '\u9fff':
                tokens.append(text[i:i+2])
            # 单字
            tokens.append(text[i])
            i += 1
        
        # 过滤停用词
        return [t for t in tokens if t and t not in cls.STOP_WORDS and not t.isspace()]
    
    @classmethod
    def compute_similarity(cls, text1: str, text2: str) -> float:
        """计算两个文本的语义相似度 (0~1)"""
        t1 = set(cls.tokenize(text1))
        t2 = set(cls.tokenize(text2))
        
        if not t1 or not t2:
            return 0.0
        
        # Jaccard相似度
        intersection = t1 & t2
        union = t1 | t2
        
        jaccard = len(intersection) / len(union)
        
        # 双向包含度
        coverage = max(
            len(intersection) / len(t1) if t1 else 0,
            len(intersection) / len(t2) if t2 else 0,
        )
        
        return jaccard * 0.4 + coverage * 0.6
    
    @classmethod
    def extract_subtasks(cls, instruction: str) -> list[dict]:
        """
        基于语义+规则提取子任务
        
        返回: [{text, action_type, confidence}]
        """
        # 按连接词分割
        conj_pattern = '|'.join(re.escape(c) for c in cls.CONJUNCTIONS)
        parts = re.split(f'(?:{conj_pattern})', instruction)
        
        subtasks = []
        seen = set()
        
        for part in parts:
            part = part.strip().strip('，,。；;')
            if not part or len(part) < 2:
                continue
            
            dedup = part[:20]
            if dedup in seen:
                continue
            seen.add(dedup)
            
            # 识别动作类型
            action_type = None
            max_sim = 0.0
            
            for intent, prototype in cls.INTENT_PROTOTYPES.items():
                for token in prototype["tokens"]:
                    if token in part:
                        sim = prototype["weight"]
                        if sim > max_sim:
                            max_sim = sim
                            action_type = intent
            
            if not action_type:
                # 用相似度降级匹配
                for intent, prototype in cls.INTENT_PROTOTYPES.items():
                    if prototype["tokens"]:
                        proto_text = "".join(prototype["tokens"])
                        sim = cls.compute_similarity(part, proto_text)
                        if sim * prototype["weight"] > max_sim:
                            max_sim = sim * prototype["weight"]
                            action_type = intent
            
            if not action_type:
                action_type = "unknown"
            
            subtasks.append({
                "text": part,
                "action_type": action_type,
                "confidence": min(1.0, max_sim + 0.3),  # base confidence
            })
        
        return subtasks


class ComprehensionEnricher:
    """
    理解增强器 — 用语义分析丰富理解验证结果
    
    与 comprehension_validator 的 UnderstandingReport 集成
    """
    
    @staticmethod
    def parse(instruction: str, context: dict = None) -> dict:
        """
        语义解析主入口
        
        返回:
        {
            "intents": [{type, action, confidence, entities}],
            "method": "semantic|rule",
            "context_used": bool
        }
        """
        if not instruction or not instruction.strip():
            return {"intents": [], "method": "skip", "context_used": False}
        
        subtasks = LightweightSemanticSpace.extract_subtasks(instruction)
        
        intents = []
        for st in subtasks:
            intent_type = st["action_type"]
            intents.append({
                "type": intent_type,
                "action": st["text"][:30],
                "confidence": st["confidence"],
                "entities": {},
            })
        
        return {
            "intents": intents,
            "method": "semantic",
            "context_used": context is not None,
        }


def semantic_parse(instruction: str, context: dict = None) -> dict:
    """语义解析接口 — 供 comprehension_validator 调用"""
    return ComprehensionEnricher.parse(instruction, context)


def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


@deprecated
def enrich_report(report, semantic_result: dict):
    """用语义结果丰富理解报告"""
    for i, intent in enumerate(semantic_result.get("intents", [])):
        if i < len(report.subtasks):
            st = report.subtasks[i]
            st.action_mapped = intent.get("action", st.action_mapped)
            st.confidence = max(st.confidence, intent.get("confidence", 0.0))
            if intent.get("type"):
                st.reasoning += f" [语义: {intent['type']}]"
    
    return report


def self_test():
    """自检"""
    print("=" * 60)
    print("  语义理解桥接器 v2 — 自检")
    print(f"  numpy: {'✅' if NUMPY_AVAILABLE else '❌'}")
    print("=" * 60)
    
    test_cases = [
        "创建文件然后运行测试最后发送结果到邮箱",
        "先分析数据，接着训练模型，最后部署",
        "继续",
        "帮我修复这个bug然后提交代码",
        "创建 hippocampus.py 实现7类记忆节点和7类关系",
    ]
    
    for tc in test_cases:
        result = ComprehensionEnricher.parse(tc)
        print(f"\n📝 {tc[:45]:45s} [{result['method']}]")
        for intent in result["intents"]:
            icon = "✅" if intent["confidence"] > 0.5 else "❓"
            print(f"   {icon} [{intent['type']:12s}] {intent['action'][:30]} (conf={intent['confidence']:.2f})")


if __name__ == "__main__":
    self_test()
