#!/usr/bin/env python3
"""
零·集群总线 + 任务调度器 — 合并版
所有agent的实时通信中枢 + 多agent协同调度

用法:
  python3 cluster_bus.py send "codex" "修复某个bug"
  python3 cluster_bus.py poll "hermes"
  python3 cluster_bus.py status
  python3 cluster_bus.py submit "分析系统缺口" --agent codex
  python3 cluster_bus.py dispatch
"""

import json, os, sys, time, uuid, subprocess
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

# ═══════════════════════════════════════════
# 新增：v2 枚举定义
# ═══════════════════════════════════════════

class Priority(Enum):
    """任务优先级 — P0紧急 / P1普通(默认) / P2低优"""
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"

class TaskStatus(Enum):
    """消息/任务状态追踪"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class TTLStatus(Enum):
    """TTL 状态机: active → expired, 也可 extended 续期"""
    ACTIVE = "active"
    EXPIRED = "expired"
    EXTENDED = "extended"

# ═══════════════════════════════════════════
# 新增：v2 集群默认配置
# ═══════════════════════════════════════════

CLUSTER_CONFIG = {
    "max_message_ttl": 86400,           # 最大TTL（秒）
    "default_timeout": 300,             # 默认超时（秒）
    "max_retries_default": 3,           # 默认最大重试次数
    "priority_timeouts": {              # 按优先级的超时配置
        "P0": 60,
        "P1": 300,
        "P2": 1800,
    },
    "priority_max_retries": {           # 按优先级的最多重试次数
        "P0": 5,
        "P1": 3,
        "P2": 1,
    },
}

CLUSTER = os.path.dirname(os.path.abspath(__file__))
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")
BUS_PATH = os.path.join(CLUSTER, "cluster_bus.json")
QUEUE_PATH = os.path.join(CLUSTER, "shared_task_queue.json")
RESULTS_PATH = os.path.join(CLUSTER, "shared_results.json")

AGENTS = ["hermes", "codex", "claude"]

def atomic_w(path, data):
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else '.', exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default or {}

# ═══════════════════════════════════════════
# 新增：TTL 状态机 — 检查并更新消息过期状态
# ═══════════════════════════════════════════

def update_ttl_status(msg):
    """
    TTL 状态机: active → expired
    如果消息的 expires_at 已过当前时间，则将 ttl_status 改为 expired，
    同时将 task_status 改为 expired（如果尚未终结）。
    """
    expires_at = msg.get("expires_at")
    if expires_at and msg.get("ttl_status") == TTLStatus.ACTIVE.value:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.now() > expires_dt:
                msg["ttl_status"] = TTLStatus.EXPIRED.value
                # 如果任务状态还在进行中，标记为过期
                if msg.get("status") in (TaskStatus.PENDING.value, TaskStatus.PROCESSING.value):
                    msg["status"] = TaskStatus.EXPIRED.value
        except (ValueError, TypeError):
            pass  # 日期格式无效时跳过

def update_all_ttl(bus):
    """遍历总线中所有消息，执行 TTL 状态机检查"""
    for msg in bus.get("messages", []):
        update_ttl_status(msg)

# ═══════════════════════════════════════════
# 总线通信
# ═══════════════════════════════════════════

def load_bus():
    return load_json(BUS_PATH, {"messages": [], "agents": {}})

def save_bus(bus):
    atomic_w(BUS_PATH, bus)

def send(from_agent, to_agent, content, msg_type="task",
         priority=None, timeout=None, max_retries=None,
         tags=None, correlation_id=None):
    """
    发送消息到总线。
    —— 原签名保持兼容: send(from_agent, to_agent, content, msg_type="task")
    —— 新增可选参数支持 v2 字段:
        priority: Priority 枚举或字符串 (P0/P1/P2), 默认 P1
        timeout:  超时秒数, 默认从 CLUSTER_CONFIG 获取
        max_retries: 最大重试次数, 默认从 CLUSTER_CONFIG 获取
        tags: 标签列表
        correlation_id: 关联ID
    """
    bus = load_bus()

    # 计算优先级及对应默认值
    if priority is None:
        priority = Priority.P1
    elif isinstance(priority, str):
        priority = Priority(priority)
    priority_str = priority.value

    # 根据优先级获取默认 timeout / max_retries
    if timeout is None:
        timeout = CLUSTER_CONFIG["priority_timeouts"].get(priority_str, CLUSTER_CONFIG["default_timeout"])
    if max_retries is None:
        max_retries = CLUSTER_CONFIG["priority_max_retries"].get(priority_str, CLUSTER_CONFIG["max_retries_default"])

    # 计算过期时间
    expires_at = (datetime.now() + timedelta(seconds=timeout)).isoformat()

    msg = {
        "id": f"M-{uuid.uuid4().hex[:8]}",
        "from": from_agent, "to": to_agent,
        "type": msg_type, "content": content[:1000],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "read": False,
        # --- v2 新增字段 ---
        "priority": priority_str,
        "timeout": timeout,
        "expires_at": expires_at,
        "ttl_status": TTLStatus.ACTIVE.value,
        "retry_count": 0,
        "max_retries": max_retries,
        "retry_history": [],
        "status": TaskStatus.PENDING.value,
        "error": None,
        "tags": tags or [],
        "correlation_id": correlation_id,
    }
    bus["messages"].append(msg)
    bus["agents"].setdefault(from_agent, {})["last_seen"] = datetime.now().isoformat()
    save_bus(bus)
    return msg["id"]

def poll(agent_name):
    """
    拉取指定 agent 的未读消息。
    —— 原签名保持兼容: poll(agent_name)
    —— 新增: 拉取时执行 TTL 状态机检查
    """
    bus = load_bus()
    # 拉取前执行 TTL 过期检查
    update_all_ttl(bus)

    unread = [m for m in bus["messages"] if m["to"] == agent_name and not m["read"]]
    for m in unread:
        m["read"] = True
        # 如果消息状态是 pending 且被 poll 读取，标记为 processing
        if m.get("status") == TaskStatus.PENDING.value:
            m["status"] = TaskStatus.PROCESSING.value
    bus["agents"].setdefault(agent_name, {})["last_seen"] = datetime.now().isoformat()
    save_bus(bus)
    return unread

def broadcast(from_agent, content, msg_type="broadcast",
              priority=None, timeout=None, max_retries=None,
              tags=None, correlation_id=None):
    """
    广播消息到所有其他 agent。
    —— 原签名保持兼容: broadcast(from_agent, content, msg_type="broadcast")
    —— 新增可选参数同 send()
    """
    bus = load_bus()
    msg_ids = []
    for agent in AGENTS:
        if agent != from_agent:
            if priority is None:
                priority = Priority.P1
            elif isinstance(priority, str):
                priority = Priority(priority)
            priority_str = priority.value
            if timeout is None:
                timeout = CLUSTER_CONFIG["priority_timeouts"].get(priority_str, CLUSTER_CONFIG["default_timeout"])
            if max_retries is None:
                max_retries = CLUSTER_CONFIG["priority_max_retries"].get(priority_str, CLUSTER_CONFIG["max_retries_default"])
            expires_at = (datetime.now() + timedelta(seconds=timeout)).isoformat()
            msg = {
                "id": f"M-{uuid.uuid4().hex[:8]}",
                "from": from_agent, "to": agent,
                "type": msg_type, "content": content[:1000],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "read": False,
                # --- v2 新增字段 ---
                "priority": priority_str,
                "timeout": timeout,
                "expires_at": expires_at,
                "ttl_status": TTLStatus.ACTIVE.value,
                "retry_count": 0,
                "max_retries": max_retries,
                "retry_history": [],
                "status": TaskStatus.PENDING.value,
                "error": None,
                "tags": tags or [],
                "correlation_id": correlation_id,
            }
            bus["messages"].append(msg)
            msg_ids.append(msg["id"])
    bus["agents"].setdefault(from_agent, {})["last_seen"] = datetime.now().isoformat()
    save_bus(bus)
    return msg_ids

def bus_status():
    bus = load_bus()
    # 状态查询时也执行 TTL 检查
    update_all_ttl(bus)
    total = len(bus["messages"])
    unread = {a: len([m for m in bus["messages"] if m["to"] == a and not m["read"]]) for a in AGENTS}
    # 统计各状态消息数量
    status_counts = {}
    for m in bus.get("messages", []):
        s = m.get("status", "unknown")
        status_counts[s] = status_counts.get(s, 0) + 1
    return {"total_messages": total, "unread": unread, "status_counts": status_counts}

def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


# ═══════════════════════════════════════════
# 新增：v2 任务状态更新工具函数
# ═══════════════════════════════════════════

@deprecated
def update_task_status(msg_id, new_status, error=None):
    """
    根据消息 ID 更新其状态。
    new_status: TaskStatus 枚举值或字符串
    error: 可选的错误信息（仅当状态为 failed 时使用）
    """
    bus = load_bus()
    for msg in bus.get("messages", []):
        if msg["id"] == msg_id:
            if isinstance(new_status, TaskStatus):
                msg["status"] = new_status.value
            else:
                msg["status"] = new_status
            if error is not None:
                msg["error"] = error[:500] if error else None
            save_bus(bus)
            return True
    return False

# ═══════════════════════════════════════════
# 任务队列
# ═══════════════════════════════════════════

class TaskQueue:
    def __init__(self):
        self.data = load_json(QUEUE_PATH, {"tasks": [], "completed": [], "failed": []})
    
    def _save(self):
        atomic_w(QUEUE_PATH, self.data)
    
    def submit(self, description, agent="auto", priority=5, context=""):
        task_id = f"T-{uuid.uuid4().hex[:8]}"
        task = {
            "id": task_id, "description": description,
            "assigned_to": agent, "priority": priority,
            "context": context, "status": "pending",
            "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "started_at": None, "completed_at": None, "result": None,
        }
        self.data["tasks"].append(task)
        self._save()
        return task_id
    
    def get_pending(self, agent=None):
        tasks = [t for t in self.data["tasks"] if t["status"] == "pending"]
        if agent:
            tasks = [t for t in tasks if t["assigned_to"] == agent]
        tasks.sort(key=lambda t: -t["priority"])
        return tasks
    
    def start(self, task_id):
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "running"
                t["started_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._save()
                return True
        return False
    
    def complete(self, task_id, result):
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "completed"
                t["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t["result"] = result[:2000]
                self.data["completed"].append(t.copy())
                self.data["tasks"].remove(t)
                self._save()
                return True
        return False
    
    def fail(self, task_id, error):
        for t in self.data["tasks"]:
            if t["id"] == task_id:
                t["status"] = "failed"
                t["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                t["result"] = f"ERROR: {error[:500]}"
                self.data["failed"].append(t.copy())
                self.data["tasks"].remove(t)
                self._save()
                return True
        return False

# ═══════════════════════════════════════════
# Agent执行器
# ═══════════════════════════════════════════

class AgentExecutor:
    def __init__(self):
        self.queue = TaskQueue()
    
    def dispatch(self, max_tasks=3):
        dispatched = []
        for agent_name in AGENTS:
            pending = self.queue.get_pending(agent_name)
            for task in pending[:max_tasks]:
                success = self._execute_task(agent_name, task)
                dispatched.append({"task_id": task["id"], "agent": agent_name, "success": success})
                if len(dispatched) >= max_tasks:
                    return dispatched
        return dispatched
    
    def _execute_task(self, agent_name, task):
        task_id = task["id"]
        desc = task["description"]
        self.queue.start(task_id)
        try:
            if agent_name == "hermes":
                result = f"[Hermes] 已处理: {desc[:100]}"
            elif agent_name == "codex":
                try:
                    proc = subprocess.run(["codex", "exec", "--", desc], cwd=CLUSTER, capture_output=True, text=True, timeout=120)
                    result = proc.stdout[-800:] if proc.stdout else proc.stderr[-500:]
                except Exception:
                    result = "[Codex] 执行失败"
            elif agent_name == "claude":
                try:
                    proc = subprocess.run(["claude", "-p", desc], cwd=CLUSTER, capture_output=True, text=True, timeout=120)
                    result = proc.stdout[-800:] if proc.stdout else proc.stderr[-500:]
                except Exception:
                    result = "[Claude] 执行失败"
            else:
                result = f"Unknown agent: {agent_name}"
            self.queue.complete(task_id, result)
            return True
        except Exception as e:
            self.queue.fail(task_id, str(e))
            return False

# ═══════════════════════════════════════════
# 状态报告
# ═══════════════════════════════════════════

def get_cluster_status():
    queue = TaskQueue()
    hip = load_json(HIP_PATH, {})
    proc = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    
    agent_status = {}
    for name in AGENTS:
        agent_status[name] = {
            "process_alive": name in proc,
        }
    
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "agents": agent_status,
        "queue": {
            "pending": len(queue.get_pending()),
            "completed": len(queue.data.get("completed", [])),
            "failed": len(queue.data.get("failed", [])),
        },
        "causal_chains": len(hip.get("causal_chains", [])),
    }

# ═══════════════════════════════════════════
# CLI入口
# ═══════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="零·集群总线+任务调度")
    sub = parser.add_subparsers(dest="command")
    
    sp = sub.add_parser("send")
    sp.add_argument("to")
    sp.add_argument("content")
    sp.add_argument("--priority", choices=["P0", "P1", "P2"], default="P1",
                    help="消息优先级: P0紧急 / P1普通(默认) / P2低优")
    sp.add_argument("--timeout", type=int, default=None,
                    help="超时秒数（默认按优先级自动计算）")
    sp.add_argument("--max-retries", type=int, default=None,
                    help="最大重试次数（默认按优先级自动计算）")
    sp.add_argument("--tags", nargs="*", default=None,
                    help="标签列表")
    
    sp2 = sub.add_parser("poll")
    sp2.add_argument("agent")
    
    sub.add_parser("status")
    
    sp3 = sub.add_parser("submit")
    sp3.add_argument("description")
    sp3.add_argument("--agent", default="auto")
    sp3.add_argument("--priority", type=int, default=5)
    
    sub.add_parser("dispatch")
    
    args = parser.parse_args()
    
    if args.command == "send":
        mid = send("hermes", args.to, args.content,
                   priority=args.priority, timeout=args.timeout,
                   max_retries=args.max_retries, tags=args.tags)
        print(f"已发送 {mid} → {args.to}  [优先级={args.priority}]")
    elif args.command == "poll":
        msgs = poll(args.agent)
        if msgs:
            for m in msgs:
                status_str = f"[{m.get('status', '?')}]"
                ttl_str = f"[TTL:{m.get('ttl_status', '?')}]"
                print(f"  {status_str}{ttl_str} [{m['from']}→{m['to']}] {m['content'][:80]}")
        else:
            print(f"  {args.agent}: 无新消息")
    elif args.command == "status":
        s = get_cluster_status()
        b = bus_status()
        print(f"总消息: {b['total_messages']}")
        for a, u in b['unread'].items():
            print(f"  {a}: {u}条未读")
        print(f"消息状态分布: {b.get('status_counts', {})}")
        print(f"任务队列: 待处理{s['queue']['pending']} 完成{s['queue']['completed']} 失败{s['queue']['failed']}")
        print(f"因果链: {s['causal_chains']}")
    elif args.command == "submit":
        queue = TaskQueue()
        tid = queue.submit(args.description, args.agent, args.priority)
        print(f"已提交 {tid}")
    elif args.command == "dispatch":
        executor = AgentExecutor()
        dispatched = executor.dispatch()
        for d in dispatched:
            print(f"  {d['task_id']} → {d['agent']}: {'OK' if d['success'] else 'FAIL'}")
    else:
        parser.print_help()
