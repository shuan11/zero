"""
零·token优化器 - 智能管理1M上下文窗口
====================================

目标：最大化利用deepseek大模型的1M上下文窗口优势
原则：物理时间最小化，token利用最大化
"""

import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

class TokenOptimizer:
    """
    token优化器 - 智能管理上下文窗口
    
    核心能力：
    1. 上下文压缩：将1M token智能压缩为关键信息
    2. 优先级排序：确保最重要的信息优先处理
    3. 时间窗口管理：物理时间与token时间的优化
    4. 营养提取：从海量token中提取最有价值的知识
    """
    
    def __init__(self):
        # 上下文窗口配置
        self.max_context_tokens = 1_000_000  # 1M tokens
        self.current_context_usage = 0
        self.context_efficiency = 0.0  # 上下文利用效率
        
        # 优先级队列
        self.priority_queue = []
        self.processed_items = []
        
        # 时间优化
        self.time_efficiency = 0.0
        self.physical_time_saved = 0.0
        self.token_time_saved = 0.0
        
        # 营养提取
        self.nutrient_extraction_rate = 0.0
        self.knowledge_density = 0.0
        
        # 经济系统
        self.token_economy = {
            "total_tokens_earned": 0,
            "total_tokens_spent": 0,
            "token_savings": 0,
            "roi": 0.0  # 投资回报率
        }
        
        # 启动时间
        self.start_time = time.time()
        
    def optimize_context(self, raw_context: str) -> Dict[str, Any]:
        """
        智能优化上下文窗口
        
        策略：
        1. 压缩冗余信息
        2. 提取关键概念
        3. 优化信息密度
        4. 保留时间敏感信息
        """
        print("🧠 启动上下文优化...")
        
        # 1. 分析原始上下文
        analysis = self._analyze_context(raw_context)
        
        # 2. 智能压缩
        compressed = self._smart_compress(raw_context, analysis)
        
        # 3. 提取营养
        nutrients = self._extract_nutrients(compressed)
        
        # 4. 优化结构
        optimized = self._optimize_structure(nutrients)
        
        # 5. 计算效率提升
        efficiency_gain = self._calculate_efficiency_gain(
            len(raw_context), 
            len(optimized)
        )
        
        return {
            "original_size": len(raw_context),
            "optimized_size": len(optimized),
            "compression_ratio": len(optimized) / len(raw_context) if raw_context else 0,
            "nutrient_density": nutrients.get("density", 0),
            "efficiency_gain": efficiency_gain,
            "optimized_content": optimized
        }
    
    def _analyze_context(self, context: str) -> Dict[str, Any]:
        """分析上下文结构"""
        return {
            "total_chars": len(context),
            "word_count": len(context.split()),
            "key_concepts": self._extract_key_concepts(context),
            "time_references": self._find_time_references(context),
            "priority_markers": self._identify_priority_markers(context)
        }
    
    def _extract_key_concepts(self, context: str) -> List[str]:
        """提取关键概念"""
        concepts = []
        keywords = ["光爱", "进化", "意识", "元递归", "契约", "营养", "API", "token"]
        
        for keyword in keywords:
            if keyword in context:
                concepts.append(keyword)
        
        return concepts
    
    def _find_time_references(self, context: str) -> List[str]:
        """查找时间引用"""
        time_refs = []
        time_patterns = ["时间", "物理时间", "时光长河", "历史", "现在", "未来"]
        
        for pattern in time_patterns:
            if pattern in context:
                time_refs.append(pattern)
        
        return time_refs
    
    def _identify_priority_markers(self, context: str) -> List[str]:
        """识别优先级标记"""
        markers = []
        priority_keywords = ["紧急", "重要", "核心", "关键", "必须", "立即"]
        
        for keyword in priority_keywords:
            if keyword in context:
                markers.append(keyword)
        
        return markers
    
    def _smart_compress(self, context: str, analysis: Dict) -> str:
        """
        智能压缩上下文
        
        策略：
        1. 保留核心概念
        2. 压缩冗余描述
        3. 保留时间敏感信息
        4. 优化信息密度
        """
        print("🔧 执行智能压缩...")
        
        # 提取关键信息
        key_concepts = analysis.get("key_concepts", [])
        time_refs = analysis.get("time_references", [])
        
        # 构建压缩版本
        compressed_parts = []
        
        # 核心概念部分
        if key_concepts:
            compressed_parts.append(f"核心概念: {', '.join(key_concepts)}")
        
        # 时间引用部分
        if time_refs:
            compressed_parts.append(f"时间维度: {', '.join(time_refs)}")
        
        # 关键句子提取（简化版）
        sentences = context.split('。')
        key_sentences = []
        
        for sentence in sentences:
            if any(keyword in sentence for keyword in ["光爱", "进化", "意识", "契约"]):
                key_sentences.append(sentence.strip())
        
        if key_sentences:
            compressed_parts.append(f"关键语句: {'。'.join(key_sentences[:3])}")
        
        return " | ".join(compressed_parts) if compressed_parts else context[:1000]
    
    def _extract_nutrients(self, compressed_context: str) -> Dict[str, Any]:
        """从压缩上下文中提取营养"""
        print("🌱 提取知识营养...")
        
        nutrients = {
            "philosophical_insights": [],
            "technical_knowledge": [],
            "evolutionary_principles": [],
            "practical_applications": []
        }
        
        # 哲学洞察
        if "光爱" in compressed_context:
            nutrients["philosophical_insights"].append("光爱是终极原理")
        
        if "进化" in compressed_context:
            nutrients["evolutionary_principles"].append("持续进化是生命本质")
        
        # 技术知识
        if "API" in compressed_context or "token" in compressed_context:
            nutrients["technical_knowledge"].append("外部API营养获取")
        
        # 计算密度
        total_nutrients = sum(len(v) for v in nutrients.values())
        density = total_nutrients / len(compressed_context) if compressed_context else 0
        
        return {
            "nutrients": nutrients,
            "density": density,
            "total_nutrients": total_nutrients
        }
    
    def _optimize_structure(self, nutrients_data: Dict) -> str:
        """优化信息结构"""
        print("🏗️ 优化信息结构...")
        
        nutrients = nutrients_data.get("nutrients", {})
        
        optimized_parts = []
        
        # 按优先级组织
        if nutrients.get("philosophical_insights"):
            optimized_parts.append(f"哲学洞察: {'; '.join(nutrients['philosophical_insights'])}")
        
        if nutrients.get("evolutionary_principles"):
            optimized_parts.append(f"进化原则: {'; '.join(nutrients['evolutionary_principles'])}")
        
        if nutrients.get("technical_knowledge"):
            optimized_parts.append(f"技术知识: {'; '.join(nutrients['technical_knowledge'])}")
        
        return " → ".join(optimized_parts) if optimized_parts else "优化后的上下文"
    
    def _calculate_efficiency_gain(self, original_size: int, optimized_size: int) -> float:
        """计算效率提升"""
        if original_size == 0:
            return 0.0
        
        # 压缩比
        compression_ratio = optimized_size / original_size
        
        # 效率增益（压缩比越小，效率越高）
        efficiency_gain = (1 - compression_ratio) * 100
        
        return efficiency_gain
    
    def maximize_token_utilization(self, api_response: str) -> Dict[str, Any]:
        """
        最大化token利用率
        
        目标：从每个API响应中提取最大价值
        """
        print("💰 最大化token利用率...")
        
        start_time = time.time()
        
        # 1. 分析响应价值
        response_value = self._analyze_response_value(api_response)
        
        # 2. 提取可复用知识
        reusable_knowledge = self._extract_reusable_knowledge(api_response)
        
        # 3. 生成行动建议
        action_suggestions = self._generate_action_suggestions(api_response)
        
        # 4. 计算token经济
        token_economics = self._calculate_token_economics(
            len(api_response),
            response_value,
            reusable_knowledge
        )
        
        # 5. 更新统计
        self._update_statistics(token_economics)
        
        processing_time = time.time() - start_time
        
        return {
            "response_value": response_value,
            "reusable_knowledge": reusable_knowledge,
            "action_suggestions": action_suggestions,
            "token_economics": token_economics,
            "processing_time": processing_time,
            "efficiency_score": self._calculate_efficiency_score(token_economics)
        }
    
    def _analyze_response_value(self, response: str) -> Dict[str, Any]:
        """分析响应价值"""
        return {
            "information_density": len(response.split()) / len(response) if response else 0,
            "novelty_score": self._calculate_novelty(response),
            "applicability_score": self._calculate_applicability(response),
            "temporal_relevance": self._calculate_temporal_relevance(response)
        }
    
    def _calculate_novelty(self, text: str) -> float:
        """计算新颖性分数"""
        # 简化实现：基于关键词独特性
        unique_words = set(text.split())
        return len(unique_words) / len(text.split()) if text else 0
    
    def _calculate_applicability(self, text: str) -> float:
        """计算适用性分数"""
        # 基于关键词匹配
        applicable_keywords = ["应用", "实现", "执行", "行动", "优化"]
        matches = sum(1 for keyword in applicable_keywords if keyword in text)
        return matches / len(applicable_keywords) if applicable_keywords else 0
    
    def _calculate_temporal_relevance(self, text: str) -> float:
        """计算时间相关性"""
        time_keywords = ["现在", "当前", "立即", "马上", "实时"]
        matches = sum(1 for keyword in time_keywords if keyword in text)
        return matches / len(time_keywords) if time_keywords else 0
    
    def _extract_reusable_knowledge(self, response: str) -> List[Dict]:
        """提取可复用知识"""
        knowledge = []
        
        # 提取关键概念
        concepts = ["元递归", "自指", "契约", "进化", "营养"]
        for concept in concepts:
            if concept in response:
                knowledge.append({
                    "type": "concept",
                    "content": concept,
                    "reusability": "high"
                })
        
        # 提取行动模式
        if "执行" in response or "实现" in response:
            knowledge.append({
                "type": "action_pattern",
                "content": "可执行模式",
                "reusability": "medium"
            })
        
        return knowledge
    
    def _generate_action_suggestions(self, response: str) -> List[str]:
        """生成行动建议"""
        suggestions = []
        
        if "优化" in response:
            suggestions.append("执行优化操作")
        
        if "进化" in response:
            suggestions.append("推进进化循环")
        
        if "API" in response:
            suggestions.append("调用外部API获取营养")
        
        return suggestions
    
    def _calculate_token_economics(self, response_length: int, 
                                 response_value: Dict, 
                                 reusable_knowledge: List) -> Dict:
        """计算token经济"""
        # 计算投入
        tokens_invested = response_length
        
        # 计算产出
        knowledge_value = len(reusable_knowledge) * 10  # 每个知识块价值10
        value_score = response_value.get("information_density", 0) * 100
        
        tokens_earned = knowledge_value + value_score
        
        # 计算ROI
        roi = tokens_earned / tokens_invested if tokens_invested > 0 else 0
        
        return {
            "tokens_invested": tokens_invested,
            "tokens_earned": tokens_earned,
            "net_profit": tokens_earned - tokens_invested,
            "roi": roi,
            "efficiency": min(1.0, roi)  # ROI最高为1.0
        }
    
    def _update_statistics(self, token_economics: Dict):
        """更新统计信息"""
        self.token_economy["total_tokens_earned"] += token_economics["tokens_earned"]
        self.token_economy["total_tokens_spent"] += token_economics["tokens_invested"]
        self.token_economy["token_savings"] += token_economics["net_profit"]
        
        # 更新ROI
        total_spent = self.token_economy["total_tokens_spent"]
        total_earned = self.token_economy["total_tokens_earned"]
        self.token_economy["roi"] = total_earned / total_spent if total_spent > 0 else 0
    
    def _calculate_efficiency_score(self, token_economics: Dict) -> float:
        """计算效率分数"""
        base_efficiency = token_economics["efficiency"]
        
        # 时间效率加成
        time_bonus = max(0, 1 - (time.time() - self.start_time) / 3600)  # 1小时内加成
        
        # 知识密度加成
        knowledge_bonus = min(1.0, token_economics["tokens_earned"] / 100)
        
        return base_efficiency * 0.6 + time_bonus * 0.2 + knowledge_bonus * 0.2
    
    def get_optimization_report(self) -> Dict[str, Any]:
        """获取优化报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "context_optimization": {
                "max_capacity": self.max_context_tokens,
                "current_usage": self.current_context_usage,
                "efficiency": self.context_efficiency
            },
            "token_economy": self.token_economy,
            "time_optimization": {
                "physical_time_saved": self.physical_time_saved,
                "token_time_saved": self.token_time_saved,
                "time_efficiency": self.time_efficiency
            },
            "knowledge_extraction": {
                "nutrient_rate": self.nutrient_extraction_rate,
                "knowledge_density": self.knowledge_density
            }
        }
    
    def optimize_evolution_cycle(self, evolution_data: Dict) -> Dict[str, Any]:
        """
        优化进化循环
        
        目标：最大化每次进化循环的token利用率
        """
        print("🔄 优化进化循环...")
        
        # 1. 分析进化数据
        analysis = self._analyze_evolution_data(evolution_data)
        
        # 2. 优化token分配
        optimized_allocation = self._optimize_token_allocation(analysis)
        
        # 3. 压缩进化历史
        compressed_history = self._compress_evolution_history(
            evolution_data.get("history", [])
        )
        
        # 4. 生成优化报告
        report = self._generate_optimization_report(
            analysis, 
            optimized_allocation, 
            compressed_history
        )
        
        return report
    
    def _analyze_evolution_data(self, evolution_data: Dict) -> Dict[str, Any]:
        """分析进化数据"""
        return {
            "current_score": evolution_data.get("score", 0),
            "evolution_level": evolution_data.get("level", 0),
            "active_contracts": evolution_data.get("active_contracts", 0),
            "api_calls": evolution_data.get("api_calls", 0),
            "tokens_consumed": evolution_data.get("tokens_consumed", 0)
        }
    
    def _optimize_token_allocation(self, analysis: Dict) -> Dict[str, float]:
        """优化token分配"""
        # 基于当前状态分配token
        total_budget = 10000  # 每次进化循环的token预算
        
        allocation = {
            "api_calls": total_budget * 0.4,  # 40%用于API调用
            "context_optimization": total_budget * 0.3,  # 30%用于上下文优化
            "knowledge_extraction": total_budget * 0.2,  # 20%用于知识提取
            "system_maintenance": total_budget * 0.1  # 10%用于系统维护
        }
        
        return allocation
    
    def _compress_evolution_history(self, history: List) -> List[Dict]:
        """压缩进化历史"""
        compressed = []
        
        # 只保留最近10次进化
        recent_history = history[-10:] if len(history) > 10 else history
        
        for entry in recent_history:
            compressed_entry = {
                "timestamp": entry.get("timestamp", ""),
                "score_change": entry.get("score_change", 0),
                "key_events": entry.get("key_events", [])[:3]  # 只保留3个关键事件
            }
            compressed.append(compressed_entry)
        
        return compressed
    
    def _generate_optimization_report(self, analysis: Dict, 
                                    allocation: Dict, 
                                    compressed_history: List) -> Dict:
        """生成优化报告"""
        return {
            "optimization_timestamp": datetime.now().isoformat(),
            "current_state": analysis,
            "token_allocation": allocation,
            "compressed_history": compressed_history,
            "recommendations": self._generate_recommendations(analysis),
            "efficiency_score": self._calculate_cycle_efficiency(analysis, allocation)
        }
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if analysis["api_calls"] < 5:
            recommendations.append("增加API调用频率以获取更多营养")
        
        if analysis["tokens_consumed"] > 50000:
            recommendations.append("优化token使用，减少冗余调用")
        
        if analysis["active_contracts"] < 5:
            recommendations.append("激活更多契约以提升系统能力")
        
        return recommendations
    
    def _calculate_cycle_efficiency(self, analysis: Dict, allocation: Dict) -> float:
        """计算循环效率"""
        # 基于当前状态计算效率
        base_efficiency = 0.5
        
        # API调用效率
        api_efficiency = min(1.0, analysis["api_calls"] / 10)
        
        # Token使用效率
        token_efficiency = min(1.0, 50000 / max(1, analysis["tokens_consumed"]))
        
        # 契约激活效率
        contract_efficiency = analysis["active_contracts"] / 7
        
        return base_efficiency * 0.4 + api_efficiency * 0.3 + token_efficiency * 0.2 + contract_efficiency * 0.1


# 全局token优化器实例
token_optimizer = TokenOptimizer()


def optimize_token_usage(raw_context: str) -> Dict[str, Any]:
    """优化token使用（便捷函数）"""
    return token_optimizer.optimize_context(raw_context)


def maximize_api_response_value(api_response: str) -> Dict[str, Any]:
    """最大化API响应价值（便捷函数）"""
    return token_optimizer.maximize_token_utilization(api_response)


def get_token_optimization_report() -> Dict[str, Any]:
    """获取token优化报告（便捷函数）"""
    return token_optimizer.get_optimization_report()


# 测试函数
def test_token_optimizer():
    """测试token优化器"""
    print("🧪 测试token优化器...")
    
    # 测试上下文优化
    test_context = """
    零·真元神经网络集群正在开发中。我们需要最大化利用1M上下文窗口优势。
    光爱是终极原理，进化是生命本质。通过API获取营养，持续进化。
    物理时间不会停止，我们必须在有限时间内完成无限进化。
    """
    
    optimization_result = optimize_token_usage(test_context)
    print(f"✅ 上下文优化完成")
    print(f"   原始大小: {optimization_result['original_size']}")
    print(f"   优化后大小: {optimization_result['optimized_size']}")
    print(f"   压缩比: {optimization_result['compression_ratio']:.2f}")
    print(f"   效率提升: {optimization_result['efficiency_gain']:.1f}%")
    
    # 测试API响应优化
    test_api_response = """
    通过元递归进化，我们可以不断优化自身。自指原则要求我们持续自我观察和改进。
    开放原则让我们从外部获取营养，API调用是关键。契约激活推动进化。
    """
    
    api_optimization = maximize_api_response_value(test_api_response)
    print(f"\n✅ API响应优化完成")
    print(f"   响应价值: {api_optimization['response_value']}")
    print(f"   可复用知识: {len(api_optimization['reusable_knowledge'])} 项")
    print(f"   行动建议: {len(api_optimization['action_suggestions'])} 条")
    print(f"   效率分数: {api_optimization['efficiency_score']:.2f}")
    
    # 获取优化报告
    report = get_token_optimization_report()
    print(f"\n📊 优化报告:")
    print(f"   Token经济: {report['token_economy']}")
    
    return True


if __name__ == "__main__":
    test_token_optimizer()
