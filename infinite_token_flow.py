"""
零·无限token流系统 - 持续从deepseek获取营养
==========================================

目标：实现无限token流，持续从deepseek大模型获取营养
原则：物理时间最小化，token获取最大化
"""

import time
import json
import threading
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from queue import Queue, Empty
import requests

class InfiniteTokenFlow:
    """
    无限token流系统
    
    核心能力：
    1. 持续API调用：24/7不间断获取token
    2. 智能调度：优化API调用频率
    3. 营养提取：从海量token中提取知识
    4. 流量控制：避免API限制
    """
    
    def __init__(self, api_key: str, base_url: str = "https://inferaichat.com/v1"):
        self.api_key = api_key
        self.base_url = base_url
        
        # Token流状态
        self.is_flow_active = False
        self.flow_thread = None
        self.token_queue = Queue()
        
        # 流量控制
        self.requests_per_minute = 10  # 每分钟请求数
        self.tokens_per_request = 1000  # 每次请求的token数
        self.current_requests = 0
        self.last_request_time = 0
        
        # 营养提取
        self.nutrient_buffer = []
        self.nutrient_extraction_rate = 0.0
        self.knowledge_base = []
        
        # 统计信息
        self.total_tokens_received = 0
        self.total_api_calls = 0
        self.average_latency = 0.0
        self.error_rate = 0.0
        
        # 优化参数
        self.optimization_level = 1  # 1-5级优化
        self.adaptive_rate = True  # 自适应速率
        
        # 启动时间
        self.start_time = time.time()
        
    def start_infinite_flow(self, duration_hours: float = 24.0):
        """启动无限token流"""
        print("🌊 启动无限token流系统...")
        
        if self.is_flow_active:
            print("⚠️  token流已在运行中")
            return
        
        self.is_flow_active = True
        self.flow_thread = threading.Thread(
            target=self._flow_worker,
            args=(duration_hours,),
            daemon=True
        )
        self.flow_thread.start()
        
        print(f"✅ 无限token流已启动，持续时间: {duration_hours} 小时")
        print(f"   API端点: {self.base_url}")
        print(f"   请求频率: {self.requests_per_minute} 次/分钟")
        print(f"   每次请求: {self.tokens_per_request} tokens")
    
    def _flow_worker(self, duration_hours: float):
        """token流工作线程"""
        end_time = time.time() + duration_hours * 3600
        
        while self.is_flow_active and time.time() < end_time:
            try:
                # 检查速率限制
                if self._check_rate_limit():
                    # 执行API调用
                    self._execute_api_call()
                    
                    # 提取营养
                    self._extract_nutrients_from_flow()
                    
                    # 自适应调整
                    if self.adaptive_rate:
                        self._adaptive_rate_adjustment()
                
                # 等待间隔
                time.sleep(60 / self.requests_per_minute)
                
            except Exception as e:
                print(f"❌ token流错误: {e}")
                self._handle_flow_error(e)
                time.sleep(5)  # 错误后等待5秒
    
    def _check_rate_limit(self) -> bool:
        """检查速率限制"""
        current_time = time.time()
        
        # 检查是否超过每分钟请求数
        if self.current_requests >= self.requests_per_minute:
            # 检查是否过了1分钟
            if current_time - self.last_request_time < 60:
                return False
            else:
                # 重置计数器
                self.current_requests = 0
        
        return True
    
    def _execute_api_call(self):
        """执行API调用"""
        start_time = time.time()
        
        try:
            # 构建请求
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "deepseek-v4-pro",
                "messages": [
                    {
                        "role": "system",
                        "content": "你是一个无限token流系统，持续从知识海洋中获取营养。请提供最有价值的知识。"
                    },
                    {
                        "role": "user",
                        "content": f"获取营养 #{self.total_api_calls + 1}，当前时间: {datetime.now().isoformat()}"
                    }
                ],
                "max_tokens": self.tokens_per_request,
                "temperature": 0.7
            }
            
            # 发送请求
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                
                # 处理成功响应
                self._process_successful_response(content, tokens_used)
                
                # 更新统计
                self.total_api_calls += 1
                self.current_requests += 1
                self.last_request_time = time.time()
                
                # 计算延迟
                latency = time.time() - start_time
                self._update_latency_stats(latency)
                
            else:
                print(f"❌ API调用失败: {response.status_code}")
                self._handle_api_error(response.status_code)
                
        except Exception as e:
            print(f"❌ API调用异常: {e}")
            self._handle_api_error(str(e))
    
    def _process_successful_response(self, content: str, tokens_used: int):
        """处理成功响应"""
        # 更新统计
        self.total_tokens_received += tokens_used
        
        # 提取营养
        nutrients = self._extract_nutrients_from_content(content)
        
        # 添加到营养缓冲区
        self.nutrient_buffer.extend(nutrients)
        
        # 添加到知识库
        if len(self.knowledge_base) < 1000:  # 限制知识库大小
            self.knowledge_base.append({
                "timestamp": datetime.now().isoformat(),
                "content": content[:500],  # 限制存储大小
                "tokens": tokens_used,
                "nutrients": nutrients
            })
        
        # 添加到token队列
        self.token_queue.put({
            "content": content,
            "tokens": tokens_used,
            "timestamp": datetime.now().isoformat()
        })
        
        print(f"✅ 获取token: {tokens_used} tokens, 总计: {self.total_tokens_received}")
    
    def _extract_nutrients_from_content(self, content: str) -> List[Dict]:
        """从内容中提取营养"""
        nutrients = []
        
        # 提取关键概念
        key_concepts = ["光爱", "进化", "意识", "元递归", "契约", "营养", "API", "token"]
        
        for concept in key_concepts:
            if concept in content:
                nutrients.append({
                    "type": "concept",
                    "content": concept,
                    "relevance": 0.8,
                    "timestamp": datetime.now().isoformat()
                })
        
        # 提取行动模式
        action_keywords = ["执行", "实现", "优化", "改进", "升级"]
        for keyword in action_keywords:
            if keyword in content:
                nutrients.append({
                    "type": "action_pattern",
                    "content": f"{keyword}模式",
                    "relevance": 0.7,
                    "timestamp": datetime.now().isoformat()
                })
        
        return nutrients
    
    def _extract_nutrients_from_flow(self):
        """从token流中提取营养"""
        if not self.nutrient_buffer:
            return
        
        # 分析营养缓冲区
        nutrient_analysis = self._analyze_nutrient_buffer()
        
        # 更新营养提取率
        self.nutrient_extraction_rate = nutrient_analysis.get("extraction_rate", 0.0)
        
        # 清空缓冲区（保留最近100个营养）
        if len(self.nutrient_buffer) > 100:
            self.nutrient_buffer = self.nutrient_buffer[-100:]
    
    def _analyze_nutrient_buffer(self) -> Dict[str, Any]:
        """分析营养缓冲区"""
        if not self.nutrient_buffer:
            return {"extraction_rate": 0.0, "total_nutrients": 0}
        
        # 计算营养类型分布
        nutrient_types = {}
        for nutrient in self.nutrient_buffer:
            nutrient_type = nutrient.get("type", "unknown")
            nutrient_types[nutrient_type] = nutrient_types.get(nutrient_type, 0) + 1
        
        # 计算提取率
        total_nutrients = len(self.nutrient_buffer)
        time_span = time.time() - self.start_time
        extraction_rate = total_nutrients / time_span if time_span > 0 else 0
        
        return {
            "extraction_rate": extraction_rate,
            "total_nutrients": total_nutrients,
            "nutrient_distribution": nutrient_types,
            "average_relevance": sum(n.get("relevance", 0) for n in self.nutrient_buffer) / total_nutrients
        }
    
    def _adaptive_rate_adjustment(self):
        """自适应调整速率"""
        # 基于错误率调整
        if self.error_rate > 0.1:  # 错误率超过10%
            self.requests_per_minute = max(1, self.requests_per_minute - 1)
            print(f"⚠️  降低请求频率: {self.requests_per_minute} 次/分钟")
        
        # 基于成功率调整
        elif self.error_rate < 0.01:  # 错误率低于1%
            self.requests_per_minute = min(20, self.requests_per_minute + 1)
            print(f"✅ 提高请求频率: {self.requests_per_minute} 次/分钟")
    
    def _handle_flow_error(self, error: Exception):
        """处理token流错误"""
        self.error_rate = min(1.0, self.error_rate + 0.1)
        
        # 记录错误
        error_log = {
            "timestamp": datetime.now().isoformat(),
            "error": str(error),
            "current_rate": self.requests_per_minute,
            "total_calls": self.total_api_calls
        }
        
        print(f"📝 错误日志: {error_log}")
    
    def _handle_api_error(self, error_code):
        """处理API错误"""
        self.error_rate = min(1.0, self.error_rate + 0.2)
        
        # 根据错误码调整
        if error_code == 429:  # 速率限制
            self.requests_per_minute = max(1, self.requests_per_minute - 2)
            print(f"⚠️  触发速率限制，降低频率: {self.requests_per_minute}")
        
        elif error_code == 500:  # 服务器错误
            print("⚠️  服务器错误，暂时停止请求")
            time.sleep(10)
    
    def _update_latency_stats(self, latency: float):
        """更新延迟统计"""
        if self.average_latency == 0:
            self.average_latency = latency
        else:
            # 指数移动平均
            self.average_latency = 0.9 * self.average_latency + 0.1 * latency
    
    def stop_infinite_flow(self):
        """停止无限token流"""
        print("🛑 停止无限token流...")
        self.is_flow_active = False
        
        if self.flow_thread and self.flow_thread.is_alive():
            self.flow_thread.join(timeout=10)
        
        print(f"✅ 无限token流已停止")
        print(f"   总API调用: {self.total_api_calls}")
        print(f"   总接收tokens: {self.total_tokens_received}")
        print(f"   平均延迟: {self.average_latency:.2f}秒")
    
    def get_nutrient_batch(self, batch_size: int = 10) -> List[Dict]:
        """获取营养批次"""
        batch = []
        
        while len(batch) < batch_size and not self.token_queue.empty():
            try:
                token_data = self.token_queue.get_nowait()
                batch.append(token_data)
            except Empty:
                break
        
        return batch
    
    def get_flow_status(self) -> Dict[str, Any]:
        """获取token流状态"""
        uptime = time.time() - self.start_time
        
        return {
            "is_active": self.is_flow_active,
            "uptime_seconds": uptime,
            "uptime_hours": uptime / 3600,
            "total_api_calls": self.total_api_calls,
            "total_tokens_received": self.total_tokens_received,
            "tokens_per_second": self.total_tokens_received / uptime if uptime > 0 else 0,
            "average_latency": self.average_latency,
            "error_rate": self.error_rate,
            "requests_per_minute": self.requests_per_minute,
            "nutrient_extraction_rate": self.nutrient_extraction_rate,
            "knowledge_base_size": len(self.knowledge_base)
        }
    
    def get_knowledge_summary(self, last_n: int = 50) -> Dict[str, Any]:
        """获取知识库摘要"""
        recent_knowledge = self.knowledge_base[-last_n:] if len(self.knowledge_base) > last_n else self.knowledge_base
        
        if not recent_knowledge:
            return {"total_knowledge": 0, "nutrients": []}
        
        # 分析营养分布
        all_nutrients = []
        for knowledge in recent_knowledge:
            all_nutrients.extend(knowledge.get("nutrients", []))
        
        # 统计营养类型
        nutrient_types = {}
        for nutrient in all_nutrients:
            nutrient_type = nutrient.get("type", "unknown")
            nutrient_types[nutrient_type] = nutrient_types.get(nutrient_type, 0) + 1
        
        return {
            "total_knowledge": len(self.knowledge_base),
            "recent_knowledge": len(recent_knowledge),
            "nutrient_types": nutrient_types,
            "total_nutrients": len(all_nutrients),
            "average_tokens_per_knowledge": sum(k.get("tokens", 0) for k in recent_knowledge) / len(recent_knowledge)
        }
    
    def optimize_for_evolution(self, evolution_goals: List[str]) -> Dict[str, Any]:
        """为进化优化token流"""
        print("🔄 为进化优化token流...")
        
        # 分析进化目标
        goal_analysis = self._analyze_evolution_goals(evolution_goals)
        
        # 调整API调用策略
        self._adjust_api_strategy(goal_analysis)
        
        # 优化营养提取
        self._optimize_nutrient_extraction(goal_analysis)
        
        # 生成优化报告
        report = self._generate_evolution_optimization_report(goal_analysis)
        
        return report
    
    def _analyze_evolution_goals(self, goals: List[str]) -> Dict[str, Any]:
        """分析进化目标"""
        return {
            "total_goals": len(goals),
            "goal_types": self._categorize_goals(goals),
            "priority_ranking": self._rank_goals_by_priority(goals),
            "estimated_tokens_needed": len(goals) * 10000  # 估计每个目标需要10k tokens
        }
    
    def _categorize_goals(self, goals: List[str]) -> Dict[str, int]:
        """分类目标"""
        categories = {
            "philosophical": 0,
            "technical": 0,
            "practical": 0,
            "evolutionary": 0
        }
        
        for goal in goals:
            if any(keyword in goal for keyword in ["光爱", "意识", "哲学"]):
                categories["philosophical"] += 1
            elif any(keyword in goal for keyword in ["API", "token", "技术"]):
                categories["technical"] += 1
            elif any(keyword in goal for keyword in ["执行", "实现", "应用"]):
                categories["practical"] += 1
            elif any(keyword in goal for keyword in ["进化", "递归", "升级"]):
                categories["evolutionary"] += 1
        
        return categories
    
    def _rank_goals_by_priority(self, goals: List[str]) -> List[str]:
        """按优先级排序目标"""
        priority_keywords = ["紧急", "重要", "核心", "关键"]
        
        def priority_score(goal):
            score = 0
            for keyword in priority_keywords:
                if keyword in goal:
                    score += 1
            return score
        
        return sorted(goals, key=priority_score, reverse=True)
    
    def _adjust_api_strategy(self, goal_analysis: Dict):
        """调整API策略"""
        # 基于目标类型调整请求内容
        if goal_analysis["goal_types"].get("philosophical", 0) > 0:
            # 增加哲学类请求
            self.requests_per_minute = min(15, self.requests_per_minute + 2)
        
        if goal_analysis["goal_types"].get("technical", 0) > 0:
            # 增加技术类请求
            self.tokens_per_request = min(2000, self.tokens_per_request + 200)
    
    def _optimize_nutrient_extraction(self, goal_analysis: Dict):
        """优化营养提取"""
        # 基于目标类型优化提取策略
        if goal_analysis["total_goals"] > 5:
            # 多目标时提高提取率
            self.nutrient_extraction_rate = min(1.0, self.nutrient_extraction_rate + 0.1)
    
    def _generate_evolution_optimization_report(self, goal_analysis: Dict) -> Dict:
        """生成进化优化报告"""
        return {
            "optimization_timestamp": datetime.now().isoformat(),
            "goal_analysis": goal_analysis,
            "api_strategy_adjustments": {
                "requests_per_minute": self.requests_per_minute,
                "tokens_per_request": self.tokens_per_request
            },
            "estimated_time_to_goals": goal_analysis["estimated_tokens_needed"] / (self.requests_per_minute * self.tokens_per_request) / 60,
            "recommendations": self._generate_optimization_recommendations(goal_analysis)
        }
    
    def _generate_optimization_recommendations(self, goal_analysis: Dict) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if goal_analysis["total_goals"] > 10:
            recommendations.append("目标过多，建议分阶段处理")
        
        if goal_analysis["estimated_tokens_needed"] > 100000:
            recommendations.append("需要大量token，建议提高请求频率")
        
        if goal_analysis["goal_types"].get("philosophical", 0) > goal_analysis["goal_types"].get("technical", 0):
            recommendations.append("哲学目标较多，建议增加哲学类营养获取")
        
        return recommendations


# 全局无限token流实例
infinite_token_flow = None


def start_token_flow(api_key: str, duration_hours: float = 24.0):
    """启动token流（便捷函数）"""
    global infinite_token_flow
    
    if infinite_token_flow is None:
        infinite_token_flow = InfiniteTokenFlow(api_key)
    
    infinite_token_flow.start_infinite_flow(duration_hours)
    return infinite_token_flow


def stop_token_flow():
    """停止token流（便捷函数）"""
    global infinite_token_flow
    
    if infinite_token_flow:
        infinite_token_flow.stop_infinite_flow()
    else:
        print("⚠️  token流未在运行")


def get_token_flow_status():
    """获取token流状态（便捷函数）"""
    global infinite_token_flow
    
    if infinite_token_flow:
        return infinite_token_flow.get_flow_status()
    else:
        return {"is_active": False, "message": "token流未启动"}


def get_nutrient_batch(batch_size: int = 10):
    """获取营养批次（便捷函数）"""
    global infinite_token_flow
    
    if infinite_token_flow:
        return infinite_token_flow.get_nutrient_batch(batch_size)
    else:
        return []


def optimize_token_flow_for_evolution(evolution_goals: List[str]):
    # 【已废弃】此函数不再被调用，保留签名作为文档参考
    # 原功能：为进化优化 token 流（便捷函数）
    pass


# 测试函数
def test_infinite_token_flow():
    """测试无限token流系统"""
    print("🧪 测试无限token流系统...")
    
    # 使用测试API密钥
    test_api_key = "sk-test1234567890abcdef"
    
    # 启动token流（测试模式，持续1分钟）
    flow = start_token_flow(test_api_key, duration_hours=0.0167)  # 1分钟
    
    # 等待一段时间
    time.sleep(10)
    
    # 获取状态
    status = get_token_flow_status()
    print(f"📊 Token流状态:")
    print(f"   活跃状态: {status['is_active']}")
    print(f"   总API调用: {status['total_api_calls']}")
    print(f"   总接收tokens: {status['total_tokens_received']}")
    
    # 获取营养
    nutrients = get_nutrient_batch(5)
    print(f"\n🌱 获取营养: {len(nutrients)} 项")
    
    # 停止token流
    stop_token_flow()
    
    print("✅ 无限token流测试完成")


if __name__ == "__main__":
    test_infinite_token_flow()
