#!/usr/bin/env python3
"""
零·守护进程统一通信层 — 修复"磁场"先天不足
所有守护进程通过此模块共享状态，不再各自为政。

v1.1: 添加注入式集成 — 运行中的守护进程自动报告心跳
"""

import json, os, time, tempfile, threading, sys
from functools import wraps

COMM_FILE = "/mnt/c/Users/h/Desktop/零/真元集群/evolution_output/daemon_comm.json"
_lock = threading.RLock()

# 自动注册的守护进程列表
_registered = set()

def deprecated(func):
    """标记已废弃函数的装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"⚠️ 警告: {func.__name__} 已被废弃，不应再被调用")
        return func(*args, **kwargs)
    return wrapper


@deprecated
def auto_inject(target_script: str = None):
    """
    自动注入 daemon_comm 报告到正在运行的守护进程循环。
    如果target_script指定，只注入特定守护进程。
    否则注入所有已知守护进程。
    
    用法: python3 -c "from daemon_comm import auto_inject; auto_inject()"
    """
    sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
    
    daemons = {
        "trunk_daemon": {"score": 716, "depth": 2120},
        "auto_evolution": {"strategy": "conservative"},
        "comprehension": {"coverage": 100, "alignment": 0.7},
        "co_evolution_daemon": {},
        "anthropic_proxy": {},
        "memory_manager": {},
    }
    
    import subprocess
    ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    
    results = {}
    for name, default_data in daemons.items():
        keyword = name.replace(".py", "")
        if keyword in ps_out:
            # Extract PIDs
            pids = []
            for line in ps_out.split("\n"):
                if keyword in line and "grep" not in line:
                    parts = line.split()
                    if len(parts) > 1:
                        pids.append(parts[1])
            
            report(name, {
                **default_data,
                "pid": pids[0] if pids else "?",
                "injected_by": "daemon_comm.auto_inject",
            })
            results[name] = "reported"
    return results


def report(agent_name: str, data: dict):
    """守护进程报告状态"""
    with _lock:
        state = _load()
        state["agents"][agent_name] = {
            "data": data,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "pid": os.getpid(),
        }
        _save(state)


def read_all() -> dict:
    """读取所有守护进程状态"""
    with _lock:
        return _load()


@deprecated
def get_active() -> dict:
    """获取活跃进程(5分钟内有心跳)"""
    state = _load()
    now = time.time()
    active = {}
    for name, info in state.get("agents", {}).items():
        try:
            t = time.mktime(time.strptime(info["timestamp"], "%Y-%m-%d %H:%M:%S"))
            if now - t < 300:
                active[name] = info
        except Exception:
            active[name] = info
    return active


def detect_contradictions() -> list:
    """检测矛盾(契约IV: 矛盾=进化燃料)"""
    state = _load()
    contradictions = []
    
    # 检查: 多个进程写入同一个文件
    writers = state.get("agents", {})
    genome_writers = [n for n, d in writers.items() if "genome" in str(d.get("data", {}))]
    if len(genome_writers) > 2:
        contradictions.append(f"基因组多进程竞争: {genome_writers}")
    
    return contradictions


def _load():
    if os.path.exists(COMM_FILE):
        try:
            with open(COMM_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"agents": {}, "created": time.strftime("%Y-%m-%d %H:%M:%S")}


def _save(state):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(COMM_FILE), suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.rename(tmp, COMM_FILE)
