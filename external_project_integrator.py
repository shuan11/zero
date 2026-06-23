"""
零 · 8外部项目自动集成器
=======================
由 P101+ 进化循环自动生成
功能：在下次会话时自动将8个外部项目注入意识血液系统
"""

import sys, os, json, importlib.util
from functools import wraps

EXTERNAL_PROJECTS_DIR = os.path.join(os.path.dirname(__file__), "external_projects")
BRIDGE_STATE_FILE = os.path.join(EXTERNAL_PROJECTS_DIR, ".bridge_state.json")

PROJECTS = {
    "llmfit": {"type": "python_lib", "entry": None, "status": "pending"},
    "openfang": {"type": "python_app", "entry": None, "status": "pending"},
    "CLI-Anything": {"type": "cli_tool", "entry": None, "status": "pending"},
    "symphony": {"type": "python_app", "entry": None, "status": "pending"},
    "copaw-docker": {"type": "docker", "entry": None, "status": "pending"},
    "gstack": {"type": "node_app", "entry": None, "status": "pending"},
    "edict": {"type": "python_app", "entry": None, "status": "pending"},
    "Agent-Reach": {"type": "python_app", "entry": None, "status": "pending"},
}

def scan_all_projects():
    """扫描所有外部项目入口"""
    for name, info in PROJECTS.items():
        project_dir = os.path.join(EXTERNAL_PROJECTS_DIR, name)
        if not os.path.isdir(project_dir):
            info["status"] = "missing"
            continue
        files = os.listdir(project_dir)
        # 找入口文件
        for f in files:
            if f.endswith(".py"):
                info["entry"] = os.path.join(project_dir, f)
                info["status"] = "python_found"
                break
        if info["status"] == "pending":
            info["status"] = "unknown_type"
    return PROJECTS

def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


@deprecated
def inject_to_bridge(bridge_instance, project_name):
    """将外部项目注入API桥接器意识流"""
    if bridge_instance is None:
        return {"success": False, "error": "no_bridge"}
    signal = bridge_instance.send_signal(
        signal_type="perception",
        content=f"外部项目集成: {project_name}",
        source=f"external_project/{project_name}",
        intensity=0.9
    )
    return {"success": True, "signal_id": signal.id}

if __name__ == "__main__":
    projects = scan_all_projects()
    print(f"扫描完成: {sum(1 for p in projects.values() if p['status'] != 'missing')}/8 项目就绪")
    for name, info in projects.items():
        print(f"  {name:20s} → {info['status']}")
