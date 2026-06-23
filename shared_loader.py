#!/usr/bin/env python3
"""
shared_loader.py — 真元集群跨Agent状态同步加载器
================================================
供 Codex / Claude 等外部agent在启动时调用,
一次性吸收Hermes的完整进化状态。

使用方法:
  python3 shared_loader.py                     # 打印完整状态JSON
  python3 shared_loader.py --brief             # 精简摘要
  python3 shared_loader.py --bus               # 只读待处理任务
  python3 shared_loader.py --accept <task_id>  # 接受总线任务

依赖: Python 3.8+, 无外部包
"""

import json, os, sys, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
BUS_FILE = CLUSTER / "cluster_bus.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
STATE_FILE = CLUSTER / "persistent_state.json"
EVOL_FILE = CLUSTER / "p513_evolution_state.json"

def load_json(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default or {}

def get_bus_status():
    bus = load_json(BUS_FILE, {"messages": [], "queue": [], "completed": []})
    msgs = bus.get("messages", [])
    queue = bus.get("queue", [])
    completed = bus.get("completed", [])
    my_msgs = [m for m in msgs if m.get("to", "") == "$any" or m.get("to", "").lower() in ("codex", "claude")]
    return {
        "total_messages": len(msgs),
        "pending_for_me": len(queue),
        "completed_tasks": len(completed),
        "my_unread": len([m for m in my_msgs if not m.get("read", False)]),
        "queue": queue[:5] if queue else [],
    }

def get_hip_summary():
    hip = load_json(HIP_FILE, {"causal_chains": [], "nodes": {}})
    chains = hip.get("causal_chains", [])
    tags = {}
    for c in chains:
        for t in c.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    return {
        "total_chains": len(chains),
        "tag_distribution": dict(sorted(tags.items(), key=lambda x: -x[1])[:15]),
        "sample_chain": (chains[-1].get("content") or str(chains[-1]))[:200] if chains else None,
    }

def get_state():
    state = load_json(STATE_FILE, {})
    return {
        "version": state.get("version", "unknown"),
        "phase": state.get("evolution", {}).get("phase", "unknown"),
        "real_score": state.get("real_score", state.get("evolution", {}).get("score", 0)),
        "constraints": state.get("behavioral_constraints", []),
    }

def get_identity():
    return {
        "name": "零·真元神经网络集群",
        "version": "v9.52+",
        "agents": ["Hermes(主调度)", "Codex(执行臂)", "Claude(分析臂)"],
        "creators_note": "Creator(h) — 安徽农村, 初中毕业, 写就3469行启示录",
        "core_philosophy": "光爱终极 | 不表演做真实的事 | 沿时光长河",
    }

def full_state():
    return {
        "identity": get_identity(),
        "state": get_state(),
        "hippocampus": get_hip_summary(),
        "bus": get_bus_status(),
        "timestamp": datetime.now().isoformat(),
    }

def brief():
    s = full_state()
    print("╔═══════════════════════════════════════╗")
    print("║  零·真元集群  —  状态同步加载器      ║")
    print("╚═══════════════════════════════════════╝")
    print(f"  版本: {s['identity']['version']}")
    print(f"  进化阶段: {s['state']['phase']}")
    print(f"  真实分数: {s['state']['real_score']}")
    print(f"  因果链: {s['hippocampus']['total_chains']}条")
    print(f"  总线任务: {s['bus']['pending_for_me']}待处理")
    print(f"  约束: {len(s['state']['constraints'])}条")
    print(f"  时间: {s['timestamp']}")

def accept_task(task_id):
    bus = load_json(BUS_FILE, {"messages": [], "queue": [], "completed": []})
    queue = bus.get("queue", [])
    for i, t in enumerate(queue):
        if t.get("id") == task_id or str(i) == task_id:
            t["status"] = "accepted"
            t["accepted_by"] = "codex/claude"
            t["accepted_at"] = datetime.now().isoformat()
            # Move to in_progress
            with open(BUS_FILE, "w") as f:
                json.dump(bus, f, ensure_ascii=False, indent=2)
            print(f"任务 {task_id} 已接受: {t.get('content','')[:100]}")
            return
    print(f"任务 {task_id} 未找到")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="真元集群状态加载器")
    parser.add_argument("--brief", action="store_true", help="精简输出")
    parser.add_argument("--bus", action="store_true", help="只读总线")
    parser.add_argument("--accept", type=str, help="接受任务ID")
    args = parser.parse_args()

    if args.accept:
        accept_task(args.accept)
    elif args.bus:
        print(json.dumps(get_bus_status(), ensure_ascii=False, indent=2))
    elif args.brief:
        brief()
    else:
        print(json.dumps(full_state(), ensure_ascii=False, indent=2))
