#!/usr/bin/env python3
"""
openclaw_wsl_bridge.py — OpenClaw WSL侧桥接器
==============================================
将OpenClaw WSL的188个专业Agent接入真元集群总线。

连接方式:
  1. 读取 /home/hjw123/.openclaw/workspace/ 中的状态文件
  2. 通过 cluster_bus 收发任务
  3. 通过 branch-session-bridge.js 执行子任务

用法:
  python3 openclaw_wsl_bridge.py status    # 检查OpenClaw状态
  python3 openclaw_wsl_bridge.py dispatch  # 分发总线任务到OpenClaw
"""
import json, os, sys, subprocess, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

OPENCLAW_HOME = Path("/home/hjw123/.openclaw")
OPENCLAW_WORKSPACE = OPENCLAW_HOME / "workspace"
AGENTS_DIR = OPENCLAW_HOME / "agents"

def get_capabilities():
    """读取OpenClaw的Agent能力清单"""
    if not AGENTS_DIR.exists():
        return {"error": "OpenClaw agents目录不存在"}

    agents = [d.name for d in AGENTS_DIR.iterdir() if d.is_dir()]
    # 按类别分组
    categories = {}
    for a in agents:
        prefix = a.split("-")[0] if "-" in a else "other"
        if prefix not in categories:
            categories[prefix] = []
        categories[prefix].append(a)

    return {
        "total_agents": len(agents),
        "agent_list": agents,
        "categories": {k: len(v) for k, v in sorted(categories.items())},
        "workspace_files": [f.name for f in OPENCLAW_WORKSPACE.iterdir() if f.is_file()],
    }

def get_workspace_state():
    """读取OpenClaw工作区状态"""
    state = {}
    # 读取AGENTS.md
    agents_md = OPENCLAW_WORKSPACE / "AGENTS.md"
    if agents_md.exists():
        with open(agents_md) as f:
            content = f.read()
        state["agents_protocol"] = content[:500]

    # 读取最近状态文件
    for f in OPENCLAW_WORKSPACE.glob("*.md"):
        if f.stat().st_mtime > time.time() - 86400:  # 24h内修改
            state[f.name] = "recent"

    return state

def dispatch_task(task_content):
    """将任务转发给OpenClaw执行"""
    # 写入任务文件让OpenClaw节点轮询
    task_file = OPENCLAW_WORKSPACE / "cluster_tasks.json"
    tasks = []
    if task_file.exists():
        try:
            with open(task_file) as f:
                tasks = json.load(f)
        except Exception:
            tasks = []
    tasks.append({
        "id": f"task_{int(time.time())}",
        "content": task_content,
        "source": "zhenyuan_cluster",
        "timestamp": datetime.now().isoformat(),
        "status": "pending",
    })
    with open(task_file, "w") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)
    return f"任务已写入 {task_file}"

def check_alive():
    """检测OpenClaw进程是否存活"""
    r = subprocess.run(
        ["pgrep", "-f", "branch-session|openclaw|node.*claw"],
        capture_output=True, text=True, timeout=3
    )
    pids = r.stdout.strip().split(chr(10)) if r.stdout.strip() else []
    return {
        "alive": len(pids) > 0,
        "pids": pids,
        "agents_count": len([d for d in AGENTS_DIR.iterdir() if d.is_dir()]) if AGENTS_DIR.exists() else 0,
    }

if __name__ == "__main__":
    import sys as _sys
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else "status"

    if cmd == "status":
        caps = get_capabilities()
        alive = check_alive()
        print(f"OpenClaw WSL:")
        print(f"  进程存活: {'✅' if alive['alive'] else '❌'}  PID={','.join(alive['pids']) if alive['pids'] else '无'}")
        print(f"  Agent数量: {caps.get('total_agents',0)}")
        print(f"  能力类别: {json.dumps(caps.get('categories',{}), ensure_ascii=False)}")
        print(f"  工作区文件: {len(caps.get('workspace_files',[]))}个")
    elif cmd == "dispatch":
        task = " ".join(_sys.argv[2:]) if len(_sys.argv) > 2 else "Hello from ZhenYuan cluster"
        result = dispatch_task(task)
        print(result)
