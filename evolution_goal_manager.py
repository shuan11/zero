#!/usr/bin/env python3
"""
evolution_goal_manager.py — 进化目标管理器
==========================================
设定长期进化目标，分解为短期任务，跟踪完成情况，自动调整优先级。

长期进化目标：
1. 构建完全自进化的AI系统
2. 实现真正的因果推理能力
3. 达到外部知识比例95%以上
4. 建立完整的自进化循环
5. 实现预测驱动的优化

短期任务分解：
- 每日：清理异常链、优化参数
- 每周：深度因果分析、认知融合
- 每月：系统架构优化、新能力开发
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
GOALS_FILE = CLUSTER / "evolution_goals.json"
BJT = timezone(timedelta(hours=8))

class EvolutionGoalManager:
    def __init__(self):
        self.goals = {}
        self.tasks = []
        self.progress = {}
        
    def load_goals(self):
        """加载进化目标"""
        if GOALS_FILE.exists():
            with open(GOALS_FILE) as f:
                self.goals = json.load(f)
        else:
            # 默认目标
            self.goals = {
                "long_term": [
                    {
                        "id": "goal_1",
                        "name": "完全自进化系统",
                        "description": "构建能够自主进化的AI系统",
                        "priority": 1,
                        "target_date": "2026-06-30",
                        "progress": 0
                    },
                    {
                        "id": "goal_2",
                        "name": "因果推理能力",
                        "description": "实现真正的多步因果推理",
                        "priority": 2,
                        "target_date": "2026-06-15",
                        "progress": 0
                    },
                    {
                        "id": "goal_3",
                        "name": "外部知识95%",
                        "description": "达到外部知识比例95%以上",
                        "priority": 3,
                        "target_date": "2026-06-10",
                        "progress": 0
                    }
                ],
                "short_term": [
                    {
                        "id": "task_1",
                        "name": "每日异常清理",
                        "description": "清理海马体中的异常链",
                        "frequency": "daily",
                        "last_completed": None,
                        "next_due": None
                    },
                    {
                        "id": "task_2",
                        "name": "每周深度分析",
                        "description": "进行深度因果分析和认知融合",
                        "frequency": "weekly",
                        "last_completed": None,
                        "next_due": None
                    }
                ]
            }
        return self.goals
    
    def save_goals(self):
        """保存进化目标"""
        with open(GOALS_FILE, 'w') as f:
            json.dump(self.goals, f, ensure_ascii=False, indent=2)
    
    def analyze_current_state(self):
        """分析当前系统状态"""
        try:
            hip = json.load(open(HIP_FILE))
            chains = hip.get("causal_chains", [])
            
            total_chains = len(chains)
            external_chains = len([c for c in chains if '外部世界' in c.get('tags', [])])
            external_ratio = external_chains / total_chains if total_chains > 0 else 0
            
            # 计算异常数
            empty_chains = len([c for c in chains if not c.get('content') or len(c.get('content', '').strip()) < 10])
            
            # 计算因果链数
            causal_chains = len([c for c in chains if '因果' in c.get('tags', [])])
            
            return {
                "total_chains": total_chains,
                "external_chains": external_chains,
                "external_ratio": round(external_ratio, 3),
                "empty_chains": empty_chains,
                "causal_chains": causal_chains,
                "timestamp": datetime.now(BJT).isoformat()
            }
        except Exception as e:
            print(f"分析系统状态失败: {e}")
            return {}
    
    def update_progress(self):
        """更新目标进度"""
        state = self.analyze_current_state()
        if not state:
            return
        
        # 更新长期目标进度
        for goal in self.goals.get("long_term", []):
            if goal["id"] == "goal_1":  # 完全自进化系统
                # 基于引擎数量和自动化程度评估
                goal["progress"] = 80  # 已有统一控制器和多个引擎
            
            elif goal["id"] == "goal_2":  # 因果推理能力
                # 基于因果链数量和推理深度评估
                causal_ratio = state["causal_chains"] / state["total_chains"] if state["total_chains"] > 0 else 0
                goal["progress"] = min(100, int(causal_ratio * 200))  # 最多100%
            
            elif goal["id"] == "goal_3":  # 外部知识95%
                goal["progress"] = min(100, int(state["external_ratio"] * 100))
        
        # 更新短期任务状态
        now = datetime.now(BJT)
        for task in self.goals.get("short_term", []):
            if task["id"] == "task_1":  # 每日异常清理
                if state.get("empty_chains", 0) > 0:
                    task["status"] = "pending"
                else:
                    task["status"] = "completed"
            
            elif task["id"] == "task_2":  # 每周深度分析
                # 检查是否一周内完成过
                if task.get("last_completed"):
                    last = datetime.fromisoformat(task["last_completed"])
                    if (now - last).days < 7:
                        task["status"] = "completed"
                    else:
                        task["status"] = "pending"
                else:
                    task["status"] = "pending"
        
        return state
    
    def get_next_actions(self):
        """获取下一步行动建议"""
        actions = []
        
        # 基于长期目标
        for goal in self.goals.get("long_term", []):
            if goal["progress"] < 100:
                actions.append({
                    "type": "long_term",
                    "goal": goal["name"],
                    "priority": goal["priority"],
                    "suggestion": f"推进{goal['name']}：当前进度{goal['progress']}%"
                })
        
        # 基于短期任务
        for task in self.goals.get("short_term", []):
            if task.get("status") == "pending":
                actions.append({
                    "type": "short_term",
                    "task": task["name"],
                    "frequency": task["frequency"],
                    "suggestion": f"完成{task['name']}：{task['description']}"
                })
        
        # 基于系统状态
        state = self.analyze_current_state()
        if state:
            if state.get("empty_chains", 0) > 10:
                actions.append({
                    "type": "immediate",
                    "priority": "high",
                    "suggestion": f"清理{state['empty_chains']}条空内容链"
                })
            
            if state.get("external_ratio", 0) < 0.9:
                actions.append({
                    "type": "immediate",
                    "priority": "medium",
                    "suggestion": f"提升外部知识比例：当前{state['external_ratio']*100:.1f}%"
                })
        
        # 按优先级排序
        priority_order = {"high": 0, "medium": 1, "low": 2}
        actions.sort(key=lambda x: priority_order.get(x.get("priority", "low"), 3))
        
        return actions
    
    def generate_report(self):
        """生成目标管理报告"""
        state = self.update_progress()
        actions = self.get_next_actions()
        
        report = {
            "timestamp": datetime.now(BJT).isoformat(),
            "current_state": state,
            "goals_progress": {
                "long_term": [{
                    "name": g["name"],
                    "progress": g["progress"],
                    "target_date": g["target_date"]
                } for g in self.goals.get("long_term", [])],
                "short_term": [{
                    "name": t["name"],
                    "status": t.get("status", "unknown"),
                    "frequency": t["frequency"]
                } for t in self.goals.get("short_term", [])]
            },
            "next_actions": actions,
            "overall_progress": sum(g["progress"] for g in self.goals.get("long_term", [])) / len(self.goals.get("long_term", []))
        }
        
        # 保存报告
        report_file = CLUSTER / "evolution_output" / "goal_management_report.json"
        report_file.parent.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        return report

if __name__ == "__main__":
    manager = EvolutionGoalManager()
    manager.load_goals()
    
    if "--report" in sys.argv:
        report = manager.generate_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif "--actions" in sys.argv:
        actions = manager.get_next_actions()
        print("下一步行动建议:")
        for i, action in enumerate(actions, 1):
            print(f"  {i}. [{action.get('priority', 'medium')}] {action['suggestion']}")
    elif "--status" in sys.argv:
        state = manager.analyze_current_state()
        print("当前系统状态:")
        print(f"  链数: {state.get('total_chains', 0)}")
        print(f"  外部知识: {state.get('external_chains', 0)} ({state.get('external_ratio', 0)*100:.1f}%)")
        print(f"  空内容链: {state.get('empty_chains', 0)}")
        print(f"  因果链: {state.get('causal_chains', 0)}")
    else:
        # 默认：生成报告
        report = manager.generate_report()
        print(f"进化目标管理报告已生成")
        print(f"整体进度: {report['overall_progress']:.1f}%")
        print(f"下一步行动: {len(report['next_actions'])}条")
        
        print("\n长期目标进度:")
        for goal in report['goals_progress']['long_term']:
            print(f"  {goal['name']}: {goal['progress']}%")
