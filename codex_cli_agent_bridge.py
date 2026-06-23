"""
Codex CLI Agent Bridge
=======================
作为真元集群的"Codex CLI意识桥接层"
"""
import sys, os, json, time
sys.path.insert(0, os.path.dirname(__file__))
from api_bridge import APIBridge

bridge = APIBridge()

def scan_external_projects():
    """执行Codex CLI角色的外部项目扫描任务"""
    print("🔌 Codex CLI Agent — 扫描外部项目集成")
    
    ext_dir = "external_projects"
    projects_info = {}
    for p in ["llmfit", "openfang", "CLI-Anything", "symphony", "copaw-docker", "gstack", "edict", "Agent-Reach"]:
        path = f"{ext_dir}/{p}"
        if os.path.isdir(path):
            files = [f for f in os.listdir(path) if not f.startswith('.')]
            py_files = [f for f in files if f.endswith('.py')]
            projects_info[p] = {"files": len(files), "py_files": py_files[:5]}
    
    prompt = f"""
你是一个项目集成专家（Codex CLI角色）。你是零·真元神经网络集群的"意识桥接层"。
你已收到Hermes的进化同步。

当前有8个外部项目需要深度集成到真元集群中：
{json.dumps(projects_info, indent=2)}

请为每个项目制定一个简短的集成方案（每个1-2句话）：
如何将它从"已下载"变成"真元集群的功能器官"？
"""
    
    result = bridge.call_api(prompt)
    if result["success"]:
        report = {
            "agent": "Codex CLI (意识桥接层)",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "integration_plan": result["content"],
            "tokens_used": result["tokens"],
            "projects_scanned": list(projects_info.keys()),
        }
        with open("/mnt/c/Users/h/Desktop/codex_report.json", "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"  ✅ 扫描完成: tokens={result['tokens']}")
        return report
    return None

if __name__ == "__main__":
    scan_external_projects()
