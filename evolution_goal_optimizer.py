#!/usr/bin/env python3
"""
evolution_goal_optimizer.py — 进化目标优化器
============================================
分析当前进化状态，设定更高级的进化目标，优化进化路径，生成进化策略。

优化维度：
1. 知识质量优化
2. 推理能力优化
3. 预测准确性优化
4. 自进化效率优化
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

class EvolutionGoalOptimizer:
    def __init__(self):
        self.current_state = {}
        self.optimization_goals = []
        
    def analyze_current_state(self):
        """分析当前进化状态"""
        try:
            hip = json.load(open(HIP_FILE))
            chains = hip.get("causal_chains", [])
            
            total_chains = len(chains)
            external_chains = len([c for c in chains if '外部世界' in c.get('tags', [])])
            external_ratio = external_chains / total_chains if total_chains > 0 else 0
            
            # 计算因果链
            causal_chains = len([c for c in chains if '因果' in c.get('tags', [])])
            
            # 计算熵增链
            entropy_chains = len([c for c in chains if '熵增' in c.get('tags', [])])
            
            # 计算可信度链
            trust_chains = len([c for c in chains if '可信度' in c.get('tags', [])])
            
            self.current_state = {
                "total_chains": total_chains,
                "external_chains": external_chains,
                "external_ratio": round(external_ratio, 3),
                "causal_chains": causal_chains,
                "entropy_chains": entropy_chains,
                "trust_chains": trust_chains,
                "timestamp": datetime.now(BJT).isoformat()
            }
            
            return self.current_state
            
        except Exception as e:
            print(f"分析系统状态失败: {e}")
            return {}
    
    def set_optimization_goals(self):
        """设定优化目标"""
        self.optimization_goals = [
            {
                "id": "goal_1",
                "name": "知识质量优化",
                "description": "提升外部知识比例到95%以上",
                "target": 0.95,
                "current": self.current_state.get("external_ratio", 0),
                "priority": "high"
            },
            {
                "id": "goal_2",
                "name": "因果推理优化",
                "description": "增加因果链数量到500条以上",
                "target": 500,
                "current": self.current_state.get("causal_chains", 0),
                "priority": "medium"
            },
            {
                "id": "goal_3",
                "name": "系统稳定性优化",
                "description": "减少熵增链到1000条以下",
                "target": 1000,
                "current": self.current_state.get("entropy_chains", 0),
                "priority": "medium"
            },
            {
                "id": "goal_4",
                "name": "预测准确性优化",
                "description": "提升预测准确率到90%以上",
                "target": 0.9,
                "current": 0.8,  # 假设当前80%
                "priority": "high"
            }
        ]
        
        return self.optimization_goals
    
    def generate_optimization_strategy(self):
        """生成优化策略"""
        strategies = []
        
        for goal in self.optimization_goals:
            if goal["current"] < goal["target"]:
                if goal["id"] == "goal_1":
                    strategies.append({
                        "goal": goal["name"],
                        "action": "增加外部知识采集",
                        "method": "调用insight_engine.py --once",
                        "expected_improvement": "外部知识比例提升5%"
                    })
                
                elif goal["id"] == "goal_2":
                    strategies.append({
                        "goal": goal["name"],
                        "action": "提取更多因果关系",
                        "method": "调用causal_reasoning_enhancer.py --extract",
                        "expected_improvement": "因果链数量增加100条"
                    })
                
                elif goal["id"] == "goal_3":
                    strategies.append({
                        "goal": goal["name"],
                        "action": "清理熵增链",
                        "method": "调用rule_entropy_decay.py",
                        "expected_improvement": "熵增链减少200条"
                    })
                
                elif goal["id"] == "goal_4":
                    strategies.append({
                        "goal": goal["name"],
                        "action": "优化预测模型",
                        "method": "调用causal_predictor.py --optimize",
                        "expected_improvement": "预测准确率提升10%"
                    })
        
        return strategies
    
    def execute_optimization(self):
        """执行优化"""
        import subprocess
        
        results = []
        
        for strategy in self.generate_optimization_strategy():
            print(f"执行优化: {strategy['goal']}")
            print(f"  行动: {strategy['action']}")
            print(f"  方法: {strategy['method']}")
            
            try:
                # 解析方法
                method_parts = strategy['method'].split()
                cmd = [sys.executable] + method_parts
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=str(CLUSTER)
                )
                
                if result.returncode == 0:
                    print(f"  结果: ✓")
                    results.append({
                        "goal": strategy['goal'],
                        "success": True,
                        "output": result.stdout[-200:] if result.stdout else ""
                    })
                else:
                    print(f"  结果: ✗ {result.stderr[-100:]}")
                    results.append({
                        "goal": strategy['goal'],
                        "success": False,
                        "error": result.stderr[-100:] if result.stderr else ""
                    })
                    
            except subprocess.TimeoutExpired:
                print(f"  结果: ✗ 超时")
                results.append({
                    "goal": strategy['goal'],
                    "success": False,
                    "error": "timeout"
                })
            except Exception as e:
                print(f"  结果: ✗ {e}")
                results.append({
                    "goal": strategy['goal'],
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def generate_report(self):
        """生成优化报告"""
        self.analyze_current_state()
        self.set_optimization_goals()
        strategies = self.generate_optimization_strategy()
        
        report = {
            "timestamp": datetime.now(BJT).isoformat(),
            "current_state": self.current_state,
            "optimization_goals": self.optimization_goals,
            "strategies": strategies,
            "overall_progress": sum(
                min(1, goal["current"] / goal["target"]) 
                for goal in self.optimization_goals
            ) / len(self.optimization_goals)
        }
        
        # 保存报告
        report_file = CLUSTER / "evolution_output" / "goal_optimization_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report

if __name__ == "__main__":
    optimizer = EvolutionGoalOptimizer()
    
    if "--analyze" in sys.argv:
        state = optimizer.analyze_current_state()
        print("当前系统状态:")
        print(f"  总链: {state.get('total_chains', 0)}")
        print(f"  外部知识: {state.get('external_chains', 0)} ({state.get('external_ratio', 0)*100:.1f}%)")
        print(f"  因果链: {state.get('causal_chains', 0)}")
        print(f"  熵增链: {state.get('entropy_chains', 0)}")
    elif "--goals" in sys.argv:
        optimizer.analyze_current_state()
        goals = optimizer.set_optimization_goals()
        print("优化目标:")
        for goal in goals:
            print(f"  {goal['name']}: {goal['current']}/{goal['target']} ({goal['priority']})")
    elif "--execute" in sys.argv:
        results = optimizer.execute_optimization()
        print(f"\n执行结果: {len(results)}项优化")
        for r in results:
            status = "✓" if r["success"] else "✗"
            print(f"  {status} {r['goal']}")
    else:
        # 默认：生成报告
        report = optimizer.generate_report()
        print(f"进化目标优化报告已生成")
        print(f"整体进度: {report['overall_progress']*100:.1f}%")
        print(f"优化策略: {len(report['strategies'])}条")
