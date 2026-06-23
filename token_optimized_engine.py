"""
零·token优化集成系统 - 整合所有token优化模块
==========================================

目标：将token优化器、无限token流、token经济系统整合到统一进化引擎
原则：物理时间最小化，token利用最大化
"""

import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

# 导入token优化模块
from token_optimizer import TokenOptimizer, optimize_token_usage, maximize_api_response_value
from infinite_token_flow import InfiniteTokenFlow, start_token_flow, stop_token_flow, get_token_flow_status
from token_economy import TokenEconomySystem, record_token_transaction, invest_tokens, get_economic_dashboard

class TokenOptimizedEvolutionEngine:
    """
    token优化进化引擎
    
    核心能力：
    1. 整合token优化器、无限token流、token经济系统
    2. 最大化每次进化循环的token利用率
    3. 实现无限token流持续获取营养
    4. 建立token经济系统平衡消耗与收益
    """
    
    def __init__(self, api_key: str = None):
        # 初始化token优化模块
        self.token_optimizer = TokenOptimizer()
        
        # 初始化无限token流
        self.token_flow = None
        if api_key:
            self.token_flow = InfiniteTokenFlow(api_key)
        
        # 初始化token经济系统
        self.token_economy = TokenEconomySystem()
        
        # 进化统计
        self.evolution_stats = {
            "total_cycles": 0,
            "total_tokens_used": 0,
            "total_tokens_earned": 0,
            "average_efficiency": 0.0,
            "optimization_level": 1
        }
        
        # 性能指标
        self.performance_metrics = {
            "context_optimization_score": 0.0,
            "token_flow_efficiency": 0.0,
            "economic_roi": 0.0,
            "overall_optimization_score": 0.0
        }
        
        # 启动时间
        self.start_time = time.time()
    
    def start_optimized_evolution(self, duration_hours: float = 24.0):
        """启动优化进化"""
        print("🚀 启动token优化进化引擎...")
        
        # 启动无限token流
        if self.token_flow:
            self.token_flow.start_infinite_flow(duration_hours)
            print("✅ 无限token流已启动")
        
        # 启动优化进化循环
        self._start_optimization_cycle()
        
        print("✅ token优化进化引擎已启动")
        print(f"   持续时间: {duration_hours} 小时")
        print(f"   优化级别: {self.evolution_stats['optimization_level']}")
    
    def _start_optimization_cycle(self):
        """启动优化循环"""
        import threading
        
        def optimization_worker():
            while True:
                try:
                    # 执行优化循环
                    self._execute_optimization_cycle()
                    
                    # 等待间隔
                    time.sleep(300)  # 每5分钟执行一次
                    
                except Exception as e:
                    print(f"❌ 优化循环错误: {e}")
                    time.sleep(60)
        
        optimization_thread = threading.Thread(target=optimization_worker, daemon=True)
        optimization_thread.start()
    
    def _execute_optimization_cycle(self):
        """执行优化循环"""
        print("🔄 执行优化循环...")
        
        # 1. 优化上下文使用
        context_optimization = self._optimize_context_usage()
        
        # 2. 优化token流
        token_flow_optimization = self._optimize_token_flow()
        
        # 3. 优化token经济
        economic_optimization = self._optimize_token_economy()
        
        # 4. 更新性能指标
        self._update_performance_metrics(
            context_optimization,
            token_flow_optimization,
            economic_optimization
        )
        
        # 5. 记录优化交易
        self._record_optimization_transaction()
        
        # 6. 提升优化级别
        self._escalate_optimization_level()
        
        print("✅ 优化循环完成")
    
    def _optimize_context_usage(self) -> Dict[str, Any]:
        """优化上下文使用"""
        print("🧠 优化上下文使用...")
        
        # 获取当前上下文（模拟）
        current_context = f"当前进化状态: 第{self.evolution_stats['total_cycles']}轮, 使用tokens: {self.evolution_stats['total_tokens_used']}"
        
        # 优化上下文
        optimization_result = optimize_token_usage(current_context)
        
        # 记录交易
        record_token_transaction(
            transaction_type="context_optimization",
            amount=optimization_result.get("optimized_size", 0),
            source="raw_context",
            destination="optimized_context",
            metadata=optimization_result
        )
        
        return optimization_result
    
    def _optimize_token_flow(self) -> Dict[str, Any]:
        """优化token流"""
        if not self.token_flow:
            return {"status": "no_flow"}
        
        print("🌊 优化token流...")
        
        # 获取token流状态
        flow_status = get_token_flow_status()
        
        # 优化营养提取
        nutrients = self.token_flow.get_nutrient_batch(10)
        
        # 记录交易
        total_tokens = sum(nut.get("tokens", 0) for n in nutrients)
        record_token_transaction(
            transaction_type="token_flow_optimization",
            amount=total_tokens,
            source="token_flow",
            destination="nutrient_buffer",
            metadata={"nutrients_count": len(nutrients)}
        )
        
        return {
            "flow_status": flow_status,
            "nutrients_extracted": len(nutrients),
            "total_tokens_received": total_tokens
        }
    
    def _optimize_token_economy(self) -> Dict[str, Any]:
        """优化token经济"""
        print("💰 优化token经济...")
        
        # 分析投资表现
        investment_performance = analyze_investment_performance()
        
        # 优化token分配
        optimization_result = optimize_token_allocation([
            "提高API调用效率",
            "增加知识获取",
            "优化进化循环"
        ])
        
        # 记录交易
        record_token_transaction(
            transaction_type="economic_optimization",
            amount=investment_performance.get("total_invested_amount", 0),
            source="token_economy",
            destination="optimization_fund",
            metadata={"roi": investment_performance.get("roi_by_investment_type", {})}
        )
        
        return {
            "investment_performance": investment_performance,
            "optimization_result": optimization_result
        }
    
    def _update_performance_metrics(self, context_opt: Dict, flow_opt: Dict, economic_opt: Dict):
        """更新性能指标"""
        # 更新上下文优化分数
        self.performance_metrics["context_optimization_score"] = context_opt.get("efficiency_gain", 0) / 100
        
        # 更新token流效率
        if flow_opt.get("status") != "no_flow":
            self.performance_metrics["token_flow_efficiency"] = min(1.0, flow_opt.get("total_tokens_received", 0) / 1000)
        
        # 更新经济ROI
        self.performance_metrics["economic_roi"] = economic_opt.get("investment_performance", {}).get("roi_by_investment_type", {}).get("api_investments", 0)
        
        # 计算总体优化分数
        self.performance_metrics["overall_optimization_score"] = (
            self.performance_metrics["context_optimization_score"] * 0.4 +
            self.performance_metrics["token_flow_efficiency"] * 0.3 +
            self.performance_metrics["economic_roi"] * 0.3
        )
    
    def _record_optimization_transaction(self):
        """记录优化交易"""
        # 记录优化成本
        optimization_cost = 100  # 每次优化循环成本
        
        record_token_transaction(
            transaction_type="optimization_cost",
            amount=optimization_cost,
            source="optimization_fund",
            destination="optimization_process",
            metadata={
                "cycle_number": self.evolution_stats["total_cycles"],
                "performance_score": self.performance_metrics["overall_optimization_score"]
            }
        )
        
        # 更新统计
        self.evolution_stats["total_cycles"] += 1
        self.evolution_stats["total_tokens_used"] += optimization_cost
    
    def _escalate_optimization_level(self):
        """提升优化级别"""
        if self.performance_metrics["overall_optimization_score"] > 0.7:
            if self.evolution_stats["optimization_level"] < 5:
                self.evolution_stats["optimization_level"] += 1
                print(f"🎉 优化级别提升: {self.evolution_stats['optimization_level']}")
    
    def execute_optimized_evolution_cycle(self, evolution_data: Dict) -> Dict[str, Any]:
        """执行优化进化循环"""
        print("🔄 执行优化进化循环...")
        
        start_time = time.time()
        
        # 1. 优化进化数据
        optimized_data = self.token_optimizer.optimize_evolution_cycle(evolution_data)
        
        # 2. 从token流获取营养
        nutrients = []
        if self.token_flow:
            nutrients = self.token_flow.get_nutrient_batch(5)
        
        # 3. 优化token使用
        token_optimization = self._optimize_token_usage_for_evolution(evolution_data, nutrients)
        
        # 4. 记录进化交易
        self._record_evolution_transaction(evolution_data, token_optimization)
        
        # 5. 生成优化报告
        report = self._generate_optimized_evolution_report(
            evolution_data,
            optimized_data,
            nutrients,
            token_optimization
        )
        
        processing_time = time.time() - start_time
        report["processing_time"] = processing_time
        
        print(f"✅ 优化进化循环完成，耗时: {processing_time:.2f}秒")
        
        return report
    
    def _optimize_token_usage_for_evolution(self, evolution_data: Dict, nutrients: List[Dict]) -> Dict:
        """为进化优化token使用"""
        # 分析进化需求
        evolution_needs = self._analyze_evolution_needs(evolution_data)
        
        # 分析营养价值
        nutrient_value = self._analyze_nutrient_value(nutrients)
        
        # 优化分配
        optimization_allocation = self._optimize_token_allocation_for_evolution(
            evolution_needs,
            nutrient_value
        )
        
        return {
            "evolution_needs": evolution_needs,
            "nutrient_value": nutrient_value,
            "optimization_allocation": optimization_allocation,
            "expected_efficiency_gain": self._calculate_expected_efficiency_gain(optimization_allocation)
        }
    
    def _analyze_evolution_needs(self, evolution_data: Dict) -> Dict:
        """分析进化需求"""
        return {
            "current_score": evolution_data.get("score", 0),
            "target_score": evolution_data.get("score", 0) * 1.1,  # 目标提升10%
            "token_budget": evolution_data.get("token_budget", 10000),
            "time_budget": evolution_data.get("time_budget", 300),  # 5分钟
            "priority_areas": evolution_data.get("priority_areas", [])
        }
    
    def _analyze_nutrient_value(self, nutrients: List[Dict]) -> Dict:
        """分析营养价值"""
        if not nutrients:
            return {"total_value": 0, "nutrient_types": {}}
        
        total_value = sum(n.get("tokens", 0) for n in nutrients)
        nutrient_types = {}
        
        for nutrient in nutrients:
            nutrient_type = nutrient.get("type", "unknown")
            nutrient_types[nutrient_type] = nutrient_types.get(nutrient_type, 0) + 1
        
        return {
            "total_value": total_value,
            "nutrient_types": nutrient_types,
            "average_value": total_value / len(nutrients)
        }
    
    def _optimize_token_allocation_for_evolution(self, needs: Dict, nutrient_value: Dict) -> Dict:
        """为进化优化token分配"""
        total_budget = needs.get("token_budget", 10000)
        
        # 基于需求和营养分配
        allocation = {
            "api_calls": total_budget * 0.4,  # 40%用于API调用
            "context_optimization": total_budget * 0.3,  # 30%用于上下文优化
            "knowledge_integration": total_budget * 0.2,  # 20%用于知识整合
            "system_maintenance": total_budget * 0.1  # 10%用于系统维护
        }
        
        # 基于营养调整
        if nutrient_value.get("total_value", 0) > 500:
            allocation["knowledge_integration"] += total_budget * 0.1
            allocation["system_maintenance"] -= total_budget * 0.1
        
        return allocation
    
    def _calculate_expected_efficiency_gain(self, allocation: Dict) -> float:
        """计算预期效率增益"""
        # 基于分配计算预期增益
        total_allocation = sum(allocation.values())
        
        if total_allocation == 0:
            return 0.0
        
        # 优化分配的效率
        optimization_ratio = allocation.get("context_optimization", 0) / total_allocation
        
        return optimization_ratio * 0.5  # 最大50%效率增益
    
    def _record_evolution_transaction(self, evolution_data: Dict, token_optimization: Dict):
        """记录进化交易"""
        # 记录进化成本
        evolution_cost = evolution_data.get("tokens_used", 1000)
        
        record_token_transaction(
            transaction_type="evolution_cost",
            amount=evolution_cost,
            source="evolution_fund",
            destination="evolution_process",
            metadata={
                "evolution_score": evolution_data.get("score", 0),
                "optimization_score": token_optimization.get("expected_efficiency_gain", 0)
            }
        )
        
        # 更新统计
        self.evolution_stats["total_tokens_used"] += evolution_cost
        self.evolution_stats["total_tokens_earned"] += token_optimization.get("expected_efficiency_gain", 0) * evolution_cost
    
    def _generate_optimized_evolution_report(self, evolution_data: Dict, optimized_data: Dict, 
                                           nutrients: List[Dict], token_optimization: Dict) -> Dict:
        """生成优化进化报告"""
        return {
            "timestamp": datetime.now().isoformat(),
            "evolution_data": evolution_data,
            "optimized_data": optimized_data,
            "nutrients_received": len(nutrients),
            "token_optimization": token_optimization,
            "performance_metrics": self.performance_metrics,
            "evolution_stats": self.evolution_stats,
            "optimization_level": self.evolution_stats["optimization_level"],
            "recommendations": self._generate_optimization_recommendations(token_optimization)
        }
    
    def _generate_optimization_recommendations(self, token_optimization: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        efficiency_gain = token_optimization.get("expected_efficiency_gain", 0)
        
        if efficiency_gain < 0.2:
            recommendations.append("效率增益较低，建议增加上下文优化投入")
        
        nutrient_value = token_optimization.get("nutrient_value", {}).get("total_value", 0)
        if nutrient_value < 100:
            recommendations.append("营养摄入不足，建议增加token流频率")
        
        if self.performance_metrics["overall_optimization_score"] < 0.5:
            recommendations.append("总体优化分数较低，建议调整优化策略")
        
        return recommendations
    
    def get_optimization_status(self) -> Dict[str, Any]:
        """获取优化状态"""
        return {
            "timestamp": datetime.now().isoformat(),
            "optimization_level": self.evolution_stats["optimization_level"],
            "performance_metrics": self.performance_metrics,
            "evolution_stats": self.evolution_stats,
            "token_flow_status": get_token_flow_status() if self.token_flow else "no_flow",
            "economic_dashboard": get_economic_dashboard(),
            "system_health": self._calculate_system_health()
        }
    
    def _calculate_system_health(self) -> float:
        """计算系统健康度"""
        # 基于多个指标计算健康度
        health_score = 0.0
        
        # 性能指标
        health_score += self.performance_metrics["overall_optimization_score"] * 0.4
        
        # 经济健康
        economic_health = get_economic_dashboard().get("economic_health_score", 0)
        health_score += economic_health * 0.3
        
        # Token流健康
        if self.token_flow:
            flow_status = get_token_flow_status()
            flow_health = 1.0 if flow_status.get("is_active") else 0.0
            health_score += flow_health * 0.3
        
        return min(1.0, health_score)
    
    def stop_optimized_evolution(self):
        """停止优化进化"""
        print("🛑 停止token优化进化引擎...")
        
        # 停止token流
        if self.token_flow:
            stop_token_flow()
        
        # 生成最终报告
        final_report = self._generate_final_optimization_report()
        
        print("✅ token优化进化引擎已停止")
        print(f"   总进化轮数: {self.evolution_stats['total_cycles']}")
        print(f"   总使用tokens: {self.evolution_stats['total_tokens_used']}")
        print(f"   总获得tokens: {self.evolution_stats['total_tokens_earned']}")
        print(f"   最终优化级别: {self.evolution_stats['optimization_level']}")
        
        return final_report
    
    def _generate_final_optimization_report(self) -> Dict:
        """生成最终优化报告"""
        return {
            "final_report_timestamp": datetime.now().isoformat(),
            "total_optimization_cycles": self.evolution_stats["total_cycles"],
            "total_tokens_used": self.evolution_stats["total_tokens_used"],
            "total_tokens_earned": self.evolution_stats["total_tokens_earned"],
            "net_tokens": self.evolution_stats["total_tokens_earned"] - self.evolution_stats["total_tokens_used"],
            "final_optimization_level": self.evolution_stats["optimization_level"],
            "final_performance_metrics": self.performance_metrics,
            "system_health_score": self._calculate_system_health(),
            "optimization_efficiency": self._calculate_optimization_efficiency()
        }
    
    def _calculate_optimization_efficiency(self) -> float:
        """计算优化效率"""
        total_tokens_used = self.evolution_stats["total_tokens_used"]
        total_tokens_earned = self.evolution_stats["total_tokens_earned"]
        
        if total_tokens_used == 0:
            return 0.0
        
        return total_tokens_earned / total_tokens_used


# 全局token优化进化引擎实例
token_optimized_engine = None


def create_token_optimized_engine(api_key: str = None):
    """创建token优化进化引擎（便捷函数）"""
    global token_optimized_engine
    
    token_optimized_engine = TokenOptimizedEvolutionEngine(api_key)
    return token_optimized_engine


def start_optimized_evolution(duration_hours: float = 24.0):
    """启动优化进化（便捷函数）"""
    global token_optimized_engine
    
    if token_optimized_engine:
        token_optimized_engine.start_optimized_evolution(duration_hours)
    else:
        print("⚠️  token优化引擎未创建")


def execute_optimized_evolution_cycle(evolution_data: Dict):
    """执行优化进化循环（便捷函数）"""
    global token_optimized_engine
    
    if token_optimized_engine:
        return token_optimized_engine.execute_optimized_evolution_cycle(evolution_data)
    else:
        return {"error": "token优化引擎未创建"}


def get_optimization_status():
    """获取优化状态（便捷函数）"""
    global token_optimized_engine
    
    if token_optimized_engine:
        return token_optimized_engine.get_optimization_status()
    else:
        return {"error": "token优化引擎未创建"}


def stop_optimized_evolution():
    """停止优化进化（便捷函数）"""
    global token_optimized_engine
    
    if token_optimized_engine:
        return token_optimized_engine.stop_optimized_evolution()
    else:
        return {"error": "token优化引擎未创建"}


# 测试函数
def test_token_optimized_evolution():
    """测试token优化进化引擎"""
    print("🧪 测试token优化进化引擎...")
    
    # 创建引擎（使用测试API密钥）
    engine = create_token_optimized_engine("sk-test1234567890abcdef")
    
    # 启动优化进化（测试模式，持续1分钟）
    start_optimized_evolution(0.0167)  # 1分钟
    
    # 等待一段时间
    time.sleep(10)
    
    # 执行优化进化循环
    test_evolution_data = {
        "score": 0.5,
        "tokens_used": 1000,
        "token_budget": 5000,
        "priority_areas": ["context_optimization", "knowledge_integration"]
    }
    
    print("\n🔄 执行优化进化循环...")
    optimization_report = execute_optimized_evolution_cycle(test_evolution_data)
    print(f"优化报告: {optimization_report.get('recommendations', [])}")
    
    # 获取优化状态
    print("\n📊 获取优化状态...")
    status = get_optimization_status()
    print(f"优化级别: {status.get('optimization_level', 0)}")
    print(f"系统健康度: {status.get('system_health', 0):.2f}")
    
    # 停止优化进化
    print("\n🛑 停止优化进化...")
    final_report = stop_optimized_evolution()
    print(f"最终效率: {final_report.get('optimization_efficiency', 0):.2f}")
    
    print("✅ token优化进化引擎测试完成")


if __name__ == "__main__":
    test_token_optimized_evolution()
