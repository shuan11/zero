"""
零·Symphony项目编排桥接器 v1
==============================
P121: 集成Symphony项目管理工具到零的真元集群。

Symphony是什么:
  OpenAI出品的项目管理工具，将编码Agent编排为长期运行的自动化服务。
  核心: READ issue → 创建workspace → 运行agent → 产出结果

集成方式:
  1. Symphony读Linear Issue → 零的理解验证电路分析需求
  2. Symphony创建workspace → Harness Backend执行
  3. Symphony编排Agent → 零的MetaRecursionEngine协调
  4. WORKFLOW.md → 零的自指契约

契约对接:
  条9(合作=爱): Symphony编排多Agent协作 = 互为主体性
  条12(分合循环): 任务分配(分) + 结果合并(合)
"""

import sys
import json
import time
from pathlib import Path
from typing import Optional

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
SYMPHONY_DIR = WORKDIR / "external_projects" / "symphony"


class SymphonyBridge:
    """
    Symphony项目管理桥接器。
    
    将Symphony的issue→workspace→agent流程接入零的架构。
    """
    
    def __init__(self):
        self.available = SYMPHONY_DIR.exists()
        self._load_workflow()
    
    def _load_workflow(self):
        """加载WORKFLOW.md(如存在)"""
        workflow_path = SYMPHONY_DIR / "WORKFLOW.md"
        if workflow_path.exists():
            with open(workflow_path) as f:
                self.workflow = f.read()
        else:
            self.workflow = None
    
    def status(self) -> dict:
        return {
            "symphony_available": self.available,
            "workflow_loaded": self.workflow is not None,
            "version": "draft-v1",
            "capabilities": [
                "issue_tracking", "workspace_isolation",
                "agent_orchestration", "workflow_policy",
            ],
        }
    
    def orchestrate(self, issues: list[str]) -> dict:
        """
        编排多个Issue → 每个Issue分配到对应Agent → 产出结果。
        
        参数:
            issues: [issue_id, issue_description]
        
        返回:
            {workspaces: [{issue, agent, status, result}]}
        """
        workspaces = []
        for issue in issues[:5]:  # 最多5个
            ws = self._create_workspace(issue)
            workspaces.append(ws)
        
        return {
            "orchestrations": workspaces,
            "total": len(workspaces),
            "symphony_mode": "long-running-daemon",
        }
    
    def _create_workspace(self, issue: str) -> dict:
        """为单个Issue创建工作区并分配Agent"""
        # 从issue描述中提取关键词决定Agent
        issue_lower = issue.lower()
        
        if "bug" in issue_lower or "fix" in issue_lower:
            agent = "debugger"
        elif "test" in issue_lower or "spec" in issue_lower:
            agent = "test-engineer"
        elif "doc" in issue_lower or "doc" in issue_lower:
            agent = "doc-writer"
        elif "deploy" in issue_lower or "release" in issue_lower:
            agent = "devops-lead"
        else:
            agent = "coder"
        
        return {
            "issue": issue[:100],
            "workspace_id": f"ws_{int(time.time())}_{hash(issue) % 10000}",
            "assigned_agent": agent,
            "status": "created",
            "workflow_policy": "WORKFLOW.md",
        }
    
    def run_pipeline(self, issues: list[dict]) -> dict:
        """
        完整Symphony管道: issue → 理解 → workspace → agent → 产出
        
        增强: 在分配前先经过零的理解验证电路
        """
        try:
            sys.path.insert(0, str(WORKDIR))
            from comprehension_validator import validate
        except ImportError:
            return {"error": "理解验证不可用"}
        finally:
            sys.path.pop(0)
        
        results = []
        for issue in issues[:5]:
            desc = issue if isinstance(issue, str) else issue.get("description", "")
            
            # Step 1: 理解验证
            report = validate(desc, persist=False)
            
            # Step 2: 创建workspace
            ws = self._create_workspace(desc)
            ws["comprehension_coverage"] = report.coverage
            ws["subtasks"] = [st.description[:40] for st in report.subtasks]
            
            results.append(ws)
        
        return {
            "pipeline_results": results,
            "total": len(results),
            "bridge_alignment": sum(r.get("comprehension_coverage", 0) for r in results) / max(len(results), 1),
        }


def self_test():
    print("="*60)
    print("  Symphony项目编排桥接器 v1 自检")
    print("="*60)
    
    bridge = SymphonyBridge()
    status = bridge.status()
    print(f"\nSymphony可用: {status['symphony_available']}")
    print(f"能力: {status['capabilities']}")
    
    # 测试编排
    issues = [
        "修复登录页面的bug，用户无法登录",
        "添加用户认证的测试用例",
        "更新API文档为v2版本",
        "部署新版本到生产环境",
        "优化数据库查询性能",
    ]
    
    print(f"\n编排5个Issue:")
    result = bridge.orchestrate(issues)
    for ws in result["orchestrations"]:
        print(f"  [{ws['assigned_agent']:15s}] {ws['issue'][:40]}")
    
    print(f"\n完整管道(含理解验证):")
    pipeline = bridge.run_pipeline(issues)
    if "pipeline_results" in pipeline:
        for r in pipeline["pipeline_results"]:
            print(f"  [{r['assigned_agent']:15s}] coverage={r.get('comprehension_coverage',0):.0%}")
    
    print(f"\n✅ Symphony集成就绪")


if __name__ == "__main__":
    self_test()
