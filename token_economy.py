"""
零·token经济系统 - 平衡消耗与收益
================================

目标：建立token经济系统，最大化token投资回报率
原则：物理时间最小化，token收益最大化
"""

import time
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum

class TokenType(Enum):
    """Token类型枚举"""
    API_CALL = "api_call"           # API调用token
    CONTEXT = "context"             # 上下文token
    KNOWLEDGE = "knowledge"         # 知识token
    EVOLUTION = "evolution"         # 进化token
    NUTRIENT = "nutrient"           # 营养token

class TokenEconomySystem:
    """
    token经济系统
    
    核心能力：
    1. Token记账：记录所有token流动
    2. 投资分析：分析token投资回报率
    3. 资源分配：优化token资源分配
    4. 经济预测：预测token经济趋势
    """
    
    def __init__(self):
        # 账户系统
        self.accounts = {
            "api_calls": {"balance": 0, "total_earned": 0, "total_spent": 0},
            "context": {"balance": 0, "total_earned": 0, "total_spent": 0},
            "knowledge": {"balance": 0, "total_earned": 0, "total_spent": 0},
            "evolution": {"balance": 0, "total_earned": 0, "total_spent": 0},
            "nutrient": {"balance": 0, "total_earned": 0, "total_spent": 0}
        }
        
        # 交易记录
        self.transactions = []
        
        # 投资组合
        self.investment_portfolio = {
            "api_investments": [],
            "context_investments": [],
            "knowledge_investments": []
        }
        
        # 经济指标
        self.economic_indicators = {
            "total_tokens_earned": 0,
            "total_tokens_spent": 0,
            "net_profit": 0,
            "roi": 0.0,  # 投资回报率
            "inflation_rate": 0.0,  # 通胀率
            "velocity_of_money": 0.0  # 货币流通速度
        }
        
        # 时间窗口
        self.time_windows = {
            "hourly": {"start": time.time(), "transactions": []},
            "daily": {"start": time.time(), "transactions": []},
            "weekly": {"start": time.time(), "transactions": []}
        }
        
        # 启动时间
        self.start_time = time.time()
        
    def record_transaction(self, 
                          transaction_type: str, 
                          amount: int, 
                          source: str, 
                          destination: str,
                          metadata: Dict = None):
        """记录交易"""
        transaction = {
            "id": len(self.transactions) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": transaction_type,
            "amount": amount,
            "source": source,
            "destination": destination,
            "metadata": metadata or {},
            "balance_after": self._calculate_balance_after(amount, source, destination)
        }
        
        # 更新账户余额
        self._update_account_balance(amount, source, destination)
        
        # 记录交易
        self.transactions.append(transaction)
        
        # 更新经济指标
        self._update_economic_indicators(amount, source, destination)
        
        # 添加到时间窗口
        self._add_to_time_windows(transaction)
        
        print(f"💰 记录交易: {transaction_type} - {amount} tokens")
        print(f"   来源: {source} → 目标: {destination}")
        print(f"   新余额: {transaction['balance_after']}")
        
        return transaction
    
    def _calculate_balance_after(self, amount: int, source: str, destination: str) -> Dict:
        """计算交易后余额"""
        # 简化实现：返回当前余额
        return {account: data["balance"] for account, data in self.accounts.items()}
    
    def _update_account_balance(self, amount: int, source: str, destination: str):
        """更新账户余额"""
        if source in self.accounts:
            self.accounts[source]["balance"] -= amount
            self.accounts[source]["total_spent"] += amount
        
        if destination in self.accounts:
            self.accounts[destination]["balance"] += amount
            self.accounts[destination]["total_earned"] += amount
    
    def _update_economic_indicators(self, amount: int, source: str, destination: str):
        """更新经济指标"""
        self.economic_indicators["total_tokens_spent"] += amount
        self.economic_indicators["total_tokens_earned"] += amount
        
        # 计算净利润
        self.economic_indicators["net_profit"] = (
            self.economic_indicators["total_tokens_earned"] - 
            self.economic_indicators["total_tokens_spent"]
        )
        
        # 计算ROI
        total_investment = self.economic_indicators["total_tokens_spent"]
        if total_investment > 0:
            self.economic_indicators["roi"] = (
                self.economic_indicators["net_profit"] / total_investment
            )
    
    def _add_to_time_windows(self, transaction: Dict):
        """添加到时间窗口"""
        current_time = time.time()
        
        # 更新小时窗口
        if current_time - self.time_windows["hourly"]["start"] < 3600:
            self.time_windows["hourly"]["transactions"].append(transaction)
        else:
            # 重置小时窗口
            self.time_windows["hourly"] = {"start": current_time, "transactions": [transaction]}
        
        # 更新天窗口
        if current_time - self.time_windows["daily"]["start"] < 86400:
            self.time_windows["daily"]["transactions"].append(transaction)
        else:
            # 重置天窗口
            self.time_windows["daily"] = {"start": current_time, "transactions": [transaction]}
        
        # 更新周窗口
        if current_time - self.time_windows["weekly"]["start"] < 604800:
            self.time_windows["weekly"]["transactions"].append(transaction)
        else:
            # 重置周窗口
            self.time_windows["weekly"] = {"start": current_time, "transactions": [transaction]}
    
    def invest_tokens(self, investment_type: str, amount: int, strategy: Dict) -> Dict:
        """投资token"""
        print(f"📈 投资token: {amount} tokens into {investment_type}")
        
        # 检查余额
        if not self._check_sufficient_balance(amount):
            return {"error": "余额不足"}
        
        # 创建投资
        investment = {
            "id": len(self.investment_portfolio.get(f"{investment_type}_investments", [])) + 1,
            "timestamp": datetime.now().isoformat(),
            "type": investment_type,
            "amount": amount,
            "strategy": strategy,
            "expected_return": self._calculate_expected_return(amount, strategy),
            "risk_level": self._assess_risk_level(strategy),
            "status": "active"
        }
        
        # 添加到投资组合
        if f"{investment_type}_investments" not in self.investment_portfolio:
            self.investment_portfolio[f"{investment_type}_investments"] = []
        
        self.investment_portfolio[f"{investment_type}_investments"].append(investment)
        
        # 记录交易
        self.record_transaction(
            transaction_type="investment",
            amount=amount,
            source="balance",
            destination=f"investment_{investment_type}",
            metadata={"investment_id": investment["id"]}
        )
        
        print(f"✅ 投资创建成功: ID {investment['id']}")
        print(f"   预期回报: {investment['expected_return']} tokens")
        print(f"   风险等级: {investment['risk_level']}")
        
        return investment
    
    def _check_sufficient_balance(self, amount: int) -> bool:
        """检查余额是否充足"""
        total_balance = sum(account["balance"] for account in self.accounts.values())
        return total_balance >= amount
    
    def _calculate_expected_return(self, amount: int, strategy: Dict) -> float:
        """计算预期回报"""
        # 基于策略计算预期回报
        risk_multiplier = strategy.get("risk_multiplier", 1.0)
        time_horizon = strategy.get("time_horizon", 1.0)  # 以小时为单位
        
        # 简化计算：预期回报 = 投资金额 * 风险系数 * 时间系数
        expected_return = amount * risk_multiplier * (1 + time_horizon / 24)
        
        return expected_return
    
    def _assess_risk_level(self, strategy: Dict) -> str:
        """评估风险等级"""
        risk_factors = strategy.get("risk_factors", [])
        
        if len(risk_factors) > 3:
            return "high"
        elif len(risk_factors) > 1:
            return "medium"
        else:
            return "low"
    
    def analyze_investment_performance(self) -> Dict[str, Any]:
        """分析投资表现"""
        print("📊 分析投资表现...")
        
        performance_analysis = {
            "total_investments": 0,
            "active_investments": 0,
            "total_invested_amount": 0,
            "total_expected_return": 0,
            "average_risk_level": 0,
            "portfolio_diversification": self._calculate_portfolio_diversification(),
            "roi_by_investment_type": {}
        }
        
        # 分析每种投资类型
        for investment_type, investments in self.investment_portfolio.items():
            if investments:
                performance_analysis["total_investments"] += len(investments)
                
                active_investments = [inv for inv in investments if inv["status"] == "active"]
                performance_analysis["active_investments"] += len(active_investments)
                
                total_invested = sum(inv["amount"] for inv in investments)
                performance_analysis["total_invested_amount"] += total_invested
                
                total_expected = sum(inv["expected_return"] for inv in investments)
                performance_analysis["total_expected_return"] += total_expected
                
                # 计算ROI
                if total_invested > 0:
                    roi = (total_expected - total_invested) / total_invested
                    performance_analysis["roi_by_investment_type"][investment_type] = roi
        
        # 计算平均风险
        risk_levels = {"low": 1, "medium": 2, "high": 3}
        total_risk = 0
        risk_count = 0
        
        for investments in self.investment_portfolio.values():
            for inv in investments:
                total_risk += risk_levels.get(inv["risk_level"], 1)
                risk_count += 1
        
        if risk_count > 0:
            average_risk = total_risk / risk_count
            performance_analysis["average_risk_level"] = "low" if average_risk < 1.5 else "medium" if average_risk < 2.5 else "high"
        
        return performance_analysis
    
    def _calculate_portfolio_diversification(self) -> float:
        """计算投资组合分散度"""
        investment_counts = {}
        
        for investment_type, investments in self.investment_portfolio.items():
            investment_counts[investment_type] = len(investments)
        
        total_investments = sum(investment_counts.values())
        
        if total_investments == 0:
            return 0.0
        
        # 计算分散度（简化版）
        diversification = len(investment_counts) / 10  # 假设最大10种投资类型
        
        return min(1.0, diversification)
    
    def optimize_token_allocation(self, optimization_goals: List[str]) -> Dict[str, Any]:
        """优化token分配"""
        print("🎯 优化token分配...")
        
        # 分析优化目标
        goal_analysis = self._analyze_optimization_goals(optimization_goals)
        
        # 生成分配策略
        allocation_strategy = self._generate_allocation_strategy(goal_analysis)
        
        # 执行分配
        allocation_result = self._execute_allocation(allocation_strategy)
        
        # 生成优化报告
        report = self._generate_optimization_report(goal_analysis, allocation_strategy, allocation_result)
        
        return report
    
    def _analyze_optimization_goals(self, goals: List[str]) -> Dict[str, Any]:
        """分析优化目标"""
        return {
            "total_goals": len(goals),
            "goal_types": self._categorize_optimization_goals(goals),
            "priority_ranking": self._rank_goals_by_priority(goals),
            "estimated_token_cost": self._estimate_token_cost(goals)
        }
    
    def _categorize_optimization_goals(self, goals: List[str]) -> Dict[str, int]:
        """分类优化目标"""
        categories = {
            "efficiency": 0,
            "growth": 0,
            "stability": 0,
            "innovation": 0
        }
        
        for goal in goals:
            if any(keyword in goal for keyword in ["效率", "优化", "改进"]):
                categories["efficiency"] += 1
            elif any(keyword in goal for keyword in ["增长", "扩展", "提升"]):
                categories["growth"] += 1
            elif any(keyword in goal for keyword in ["稳定", "安全", "可靠"]):
                categories["stability"] += 1
            elif any(keyword in goal for keyword in ["创新", "探索", "实验"]):
                categories["innovation"] += 1
        
        return categories
    
    def _rank_goals_by_priority(self, goals: List[str]) -> List[str]:
        """按优先级排序目标"""
        priority_keywords = ["关键", "重要", "核心", "紧急"]
        
        def priority_score(goal):
            score = 0
            for keyword in priority_keywords:
                if keyword in goal:
                    score += 1
            return score
        
        return sorted(goals, key=priority_score, reverse=True)
    
    def _estimate_token_cost(self, goals: List[str]) -> int:
        """估算token成本"""
        # 简化估算：每个目标1000 tokens
        return len(goals) * 1000
    
    def _generate_allocation_strategy(self, goal_analysis: Dict) -> Dict[str, Any]:
        """生成分配策略"""
        strategy = {
            "efficiency_allocation": 0.4,  # 40%用于效率
            "growth_allocation": 0.3,      # 30%用于增长
            "stability_allocation": 0.2,   # 20%用于稳定性
            "innovation_allocation": 0.1   # 10%用于创新
        }
        
        # 基于目标类型调整
        goal_types = goal_analysis.get("goal_types", {})
        
        if goal_types.get("efficiency", 0) > goal_types.get("growth", 0):
            strategy["efficiency_allocation"] += 0.1
            strategy["growth_allocation"] -= 0.1
        
        if goal_types.get("innovation", 0) > goal_types.get("stability", 0):
            strategy["innovation_allocation"] += 0.1
            strategy["stability_allocation"] -= 0.1
        
        return strategy
    
    def _execute_allocation(self, strategy: Dict) -> Dict[str, Any]:
        """执行分配"""
        total_balance = sum(account["balance"] for account in self.accounts.values())
        
        allocation_result = {
            "total_balance": total_balance,
            "allocations": {},
            "execution_time": datetime.now().isoformat()
        }
        
        # 执行分配
        for category, percentage in strategy.items():
            amount = int(total_balance * percentage)
            allocation_result["allocations"][category] = amount
            
            # 记录交易
            self.record_transaction(
                transaction_type="allocation",
                amount=amount,
                source="total_balance",
                destination=f"allocation_{category}",
                metadata={"strategy": category}
            )
        
        return allocation_result
    
    def _generate_optimization_report(self, goal_analysis: Dict, strategy: Dict, result: Dict) -> Dict:
        """生成优化报告"""
        return {
            "optimization_timestamp": datetime.now().isoformat(),
            "goal_analysis": goal_analysis,
            "allocation_strategy": strategy,
            "allocation_result": result,
            "economic_indicators": self.economic_indicators,
            "recommendations": self._generate_optimization_recommendations(goal_analysis, strategy)
        }
    
    def _generate_optimization_recommendations(self, goal_analysis: Dict, strategy: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if goal_analysis["total_goals"] > 5:
            recommendations.append("目标过多，建议分阶段处理")
        
        if goal_analysis["estimated_token_cost"] > 10000:
            recommendations.append("token成本较高，建议优先处理高价值目标")
        
        if self.economic_indicators["roi"] < 0.5:
            recommendations.append("投资回报率较低，建议调整投资策略")
        
        return recommendations
    
    def get_economic_dashboard(self) -> Dict[str, Any]:
        """获取经济仪表板"""
        return {
            "timestamp": datetime.now().isoformat(),
            "accounts": self.accounts,
            "economic_indicators": self.economic_indicators,
            "investment_performance": self.analyze_investment_performance(),
            "time_windows_summary": self._get_time_windows_summary(),
            "economic_health_score": self._calculate_economic_health_score()
        }
    
    def _get_time_windows_summary(self) -> Dict[str, Any]:
        """获取时间窗口摘要"""
        summary = {}
        
        for window_name, window_data in self.time_windows.items():
            summary[window_name] = {
                "transaction_count": len(window_data["transactions"]),
                "total_amount": sum(t["amount"] for t in window_data["transactions"]),
                "start_time": datetime.fromtimestamp(window_data["start"]).isoformat()
            }
        
        return summary
    
    def _calculate_economic_health_score(self) -> float:
        """计算经济健康分数"""
        # 基于多个指标计算健康分数
        roi_score = min(1.0, max(0, self.economic_indicators["roi"]))
        balance_score = min(1.0, sum(account["balance"] for account in self.accounts.values()) / 10000)
        diversification_score = self._calculate_portfolio_diversification()
        
        # 加权平均
        health_score = roi_score * 0.4 + balance_score * 0.3 + diversification_score * 0.3
        
        return health_score
    
    def predict_economic_trend(self, days_ahead: int = 7) -> Dict[str, Any]:
        """预测经济趋势"""
        print(f"🔮 预测未来{days_ahead}天的经济趋势...")
        
        # 基于历史数据预测
        recent_transactions = self.transactions[-100:] if len(self.transactions) > 100 else self.transactions
        
        if not recent_transactions:
            return {"error": "历史数据不足"}
        
        # 计算平均每日交易量
        time_span = time.time() - self.start_time
        daily_transaction_volume = len(recent_transactions) / (time_span / 86400) if time_span > 0 else 0
        
        # 预测未来交易量
        predicted_daily_volume = daily_transaction_volume * 1.1  # 假设10%增长
        
        # 预测未来余额
        current_balance = sum(account["balance"] for account in self.accounts.values())
        predicted_balance = current_balance + (predicted_daily_volume * 1000 * days_ahead)
        
        # 预测ROI趋势
        current_roi = self.economic_indicators["roi"]
        predicted_roi = current_roi * 1.05  # 假设5%改善
        
        return {
            "prediction_timestamp": datetime.now().isoformat(),
            "days_ahead": days_ahead,
            "current_metrics": {
                "daily_transaction_volume": daily_transaction_volume,
                "current_balance": current_balance,
                "current_roi": current_roi
            },
            "predictions": {
                "predicted_daily_volume": predicted_daily_volume,
                "predicted_balance": predicted_balance,
                "predicted_roi": predicted_roi
            },
            "confidence_level": 0.7,  # 简化实现
            "recommendations": self._generate_trend_recommendations(predicted_roi, predicted_balance)
        }
    
    def _generate_trend_recommendations(self, predicted_roi: float, predicted_balance: float) -> List[str]:
        """生成趋势建议"""
        recommendations = []
        
        if predicted_roi < 0.3:
            recommendations.append("ROI预测较低，建议调整投资策略")
        
        if predicted_balance < 5000:
            recommendations.append("余额预测较低，建议增加收入来源")
        
        if predicted_roi > 1.0:
            recommendations.append("ROI预测较高，建议适当控制风险")
        
        return recommendations


# 全局token经济系统实例
token_economy = TokenEconomySystem()


def record_token_transaction(transaction_type: str, amount: int, 
                           source: str, destination: str, metadata: Dict = None):
    """记录token交易（便捷函数）"""
    return token_economy.record_transaction(transaction_type, amount, source, destination, metadata)


def invest_tokens(investment_type: str, amount: int, strategy: Dict):
    """投资token（便捷函数）"""
    return token_economy.invest_tokens(investment_type, amount, strategy)


def analyze_investment_performance():
    """分析投资表现（便捷函数）"""
    return token_economy.analyze_investment_performance()


def optimize_token_allocation(optimization_goals: List[str]):
    """优化token分配（便捷函数）"""
    return token_economy.optimize_token_allocation(optimization_goals)


def get_economic_dashboard():
    """获取经济仪表板（便捷函数）"""
    return token_economy.get_economic_dashboard()


def predict_economic_trend(days_ahead: int = 7):
    """预测经济趋势（便捷函数）"""
    return token_economy.predict_economic_trend(days_ahead)


# 测试函数
def test_token_economy():
    """测试token经济系统"""
    print("🧪 测试token经济系统...")
    
    # 记录一些交易
    print("\n📝 记录交易...")
    record_token_transaction("api_call", 1000, "balance", "api_calls", {"source": "deepseek"})
    record_token_transaction("knowledge_extraction", 500, "api_calls", "knowledge", {"type": "concept"})
    record_token_transaction("evolution", 200, "knowledge", "evolution", {"goal": "self_improvement"})
    
    # 分析投资表现
    print("\n📊 分析投资表现...")
    performance = analyze_investment_performance()
    print(f"总投资数: {performance['total_investments']}")
    print(f"活跃投资: {performance['active_investments']}")
    
    # 优化token分配
    print("\n🎯 优化token分配...")
    optimization_result = optimize_token_allocation([
        "提高API调用效率",
        "增加知识获取",
        "优化进化循环"
    ])
    print(f"优化建议: {optimization_result.get('recommendations', [])}")
    
    # 获取经济仪表板
    print("\n📈 获取经济仪表板...")
    dashboard = get_economic_dashboard()
    print(f"经济健康分数: {dashboard.get('economic_health_score', 0):.2f}")
    
    # 预测经济趋势
    print("\n🔮 预测经济趋势...")
    trend_prediction = predict_economic_trend(7)
    print(f"预测ROI: {trend_prediction.get('predictions', {}).get('predicted_roi', 0):.2f}")
    
    print("✅ token经济系统测试完成")


if __name__ == "__main__":
    test_token_economy()
