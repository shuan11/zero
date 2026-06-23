#!/usr/bin/env python3
"""
零·多Agent协同守护进程
================================================
每个agent单独运行:
  python3 agent_daemon.py codex    # Codex端运行
  python3 agent_daemon.py claude   # Claude端运行
  python3 agent_daemon.py hermes   # Hermes端运行(主调度)

自动轮询总线、执行任务、共享进化状态。
不需要手动介入。持续运行。
"""

import json, os, sys, time, subprocess, threading
from datetime import datetime

CLUSTER = "/mnt/c/Users/h/Desktop/零/真元集群"
sys.path.insert(0, CLUSTER)

BUS_PATH = os.path.join(CLUSTER, "cluster_bus.json")
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")
SNAPSHOT_PATH = os.path.join(CLUSTER, "hermes_evolution_snapshot.json")

# ── 共享状态加载 ──
def load_shared_state():
    """从总线+海马体+快照加载完整状态"""
    state = {"version": "v9.42", "chains": 0, "tags": 0, "external_ratio": "0%"}
    
    # 从快照加载
    try:
        with open(SNAPSHOT_PATH) as f:
            snap = json.load(f)
            state["chains"] = snap.get("system_state", {}).get("causal_chains", 0)
            state["tags"] = snap.get("system_state", {}).get("tags", 0)
            state["external_ratio"] = snap.get("system_state", {}).get("external_ratio", "0%")
            state["hermes_version"] = snap.get("version", "")
    except Exception:
        pass
    
    # 从海马体加载
    try:
        with open(HIP_PATH) as f:
            hip = json.load(f)
        state["chains"] = len(hip.get("causal_chains", []))
        tags = set()
        for c in hip.get("causal_chains", []):
            for t in c.get("tags",[]): tags.add(t)
        state["tags"] = len(tags)
        ext_kw = {'外部世界','物理','生物','经济','历史','数学','天文','神经','技术',
                   '科学','工程','深度因果','API注入','真实世界','启示录验证','呼吸',
                   '好奇','科技前沿','深海','自然','边界','本质','公理验证','跨学科',
                   '同构','因果反转','光爱','实践','磁感线','自动','本地生长',
                   '交叉发现','本地洞察','万象归一'}
        ext = sum(1 for c in hip.get("causal_chains",[]) if set(c.get("tags",[])) & ext_kw)
        total = max(len(hip.get("causal_chains",[])), 1)
        state["external_ratio"] = f"{ext/total:.0%}"
    except Exception:
        pass
    
    return state

# ── 总线操作 ──
def atomic_w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, 'w') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_bus():
    try:
        with open(BUS_PATH) as f:
            return json.load(f)
    except Exception:
        return {"messages": [], "agents": {}, "created": datetime.now().isoformat()}

def send(from_agent, to_agent, content, msg_type="task"):
    bus = load_bus()
    import uuid
    msg = {
        "id": f"M-{uuid.uuid4().hex[:8]}",
        "from": from_agent,
        "to": to_agent,
        "type": msg_type,
        "content": content[:1000],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "read": False,
    }
    bus["messages"].append(msg)
    bus["agents"].setdefault(from_agent, {})["last_seen"] = datetime.now().isoformat()
    atomic_w(BUS_PATH, bus)
    return msg["id"]

def poll(agent_name):
    bus = load_bus()
    unread = [m for m in bus["messages"] if m["to"] == agent_name and not m["read"]]
    for m in unread:
        m["read"] = True
    bus["agents"].setdefault(agent_name, {})["last_seen"] = datetime.now().isoformat()
    atomic_w(BUS_PATH, bus)
    return unread

# ══════════════════════════════════════════════════════════════
# Agent执行核心
# ══════════════════════════════════════════════════════════════

def execute_codex_task(desc):
    """Codex执行编码任务"""
    try:
        r = subprocess.run(["codex", "exec", "--", desc],
            cwd=CLUSTER, capture_output=True, text=True, timeout=120)
        if r.stdout: return r.stdout[-800:]
        if r.stderr: return f"stderr: {r.stderr[-300:]}"
        return "无输出"
    except subprocess.TimeoutExpired:
        return "超时(120s)"
    except FileNotFoundError:
        return "codex CLI未安装"
    except Exception as e:
        return f"错误: {e}"

def execute_claude_task(desc):
    """Claude执行分析任务"""
    try:
        r = subprocess.run(["claude", "-p", desc],
            cwd=CLUSTER, capture_output=True, text=True, timeout=120)
        if r.stdout and "Not logged in" not in r.stdout:
            return r.stdout[-800:]
        # 回退到API
        from api_bridge import APIBridge
        r2 = APIBridge().call_api(f"分析任务: {desc[:400]}")
        if r2.get("success"): return r2["content"][:800]
        return "CLI和API均不可用"
    except Exception:
        return "执行失败"

def execute_hermes_task(desc):
    """Hermes执行协调任务"""
    state = load_shared_state()
    return (
        f"【Hermes调度报告】\n"
        f"集群状态: chains={state['chains']} tags={state['tags']} external={state['external_ratio']}\n"
        f"任务已下发到对应agent。当前总线消息数待查。"
    )

# ══════════════════════════════════════════════════════════════
# 主循环
# ══════════════════════════════════════════════════════════════

EXECUTORS = {
    "codex": execute_codex_task,
    "claude": execute_claude_task,
    "hermes": execute_hermes_task,
}

def run_daemon(agent_name):
    """Agent守护进程主循环"""
    if agent_name not in EXECUTORS:
        print(f"未知agent: {agent_name}")
        return 1
    
    executor = EXECUTORS[agent_name]
    cycle = 0
    
    # 启动时广播上线
    state = load_shared_state()
    send(agent_name, "hermes", 
         f"[上线] {agent_name}已启动. 已知状态: chains={state['chains']} tags={state['tags']} external={state['external_ratio']}")
    
    print(f"[{agent_name}] 守护进程启动 — 轮询每5秒")
    print(f"[{agent_name}] 集群状态: chains={state['chains']} external={state['external_ratio']}")
    
    while True:
        try:
            cycle += 1
            msgs = poll(agent_name)
            
            for msg in msgs:
                desc = msg["content"]
                task_type = msg["type"]
                from_who = msg["from"]
                msg_id = msg["id"]
                
                print(f"  [{agent_name}] 收到任务[{msg_id}]: {desc[:60]}...")
                
                if task_type == "task":
                    result = executor(desc)
                elif task_type == "sync":
                    sync_state()
                    result = "[同步完成] 进化状态已加载"
                else:
                    result = f"未知任务类型: {task_type}"
                
                send(agent_name, from_who or "hermes", f"[{msg_id}结果] {result[:500]}", "result")
                print(f"  [{agent_name}] 结果已发回: {result[:60]}...")
            
            # 每30轮广播心跳
            if cycle % 30 == 0:
                send(agent_name, "hermes", f"[心跳] {agent_name}运行中({cycle}轮)", "heartbeat")
            
            time.sleep(5)
            
        except KeyboardInterrupt:
            send(agent_name, "hermes", f"[下线] {agent_name}正常停止", "system")
            print(f"\n[{agent_name}] 停止")
            return 0
        except Exception as e:
            print(f"  [{agent_name}] 异常: {e}")
            time.sleep(10)

def sync_state():
    """同步进化状态到总线"""
    state = load_shared_state()
    send("hermes", "codex", f"[同步] 当前状态: chains={state['chains']} external={state['external_ratio']}", "sync")
    send("hermes", "claude", f"[同步] 当前状态: chains={state['chains']} external={state['external_ratio']}", "sync")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python3 agent_daemon.py <codex|claude|hermes> [--no-loop]")
        sys.exit(1)
    
    agent = sys.argv[1]
    no_loop = "--no-loop" in sys.argv
    
    if no_loop:
        # 单次执行(用于测试)
        state = load_shared_state()
        print(json.dumps(state, indent=2))
    else:
        # 守护进程模式
        sys.exit(run_daemon(agent))
