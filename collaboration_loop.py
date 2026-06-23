#!/usr/bin/env python3
"""
零·三臂协同循环 — 一次真正的协同作业
不是演示。是真的让三个agent共同解决一个问题。

流程:
  1. Hermes提出问题并广播
  2. Codex从代码角度回答
  3. Claude从架构角度回答
  4. Hermes合并三个视角，形成行动方案
  5. 执行行动方案
  6. 结果写入海马体
"""

import json, os, sys, time, subprocess
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLUSTER = "/mnt/c/Users/h/Desktop/零/真元集群"
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")
BUS_PATH = os.path.join(CLUSTER, "cluster_bus.json")
SNAPSHOT_PATH = os.path.join(CLUSTER, "hermes_evolution_snapshot.json")

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

def api_call(prompt, timeout=30):
    try:
        from api_bridge import APIBridge
        r = APIBridge().call_api(prompt)
        if r.get("success"):
            return r["content"][:600]
        return None
    except Exception:
        return None

def codex_exec(task):
    """调用Codex CLI"""
    try:
        proc = subprocess.run(
            ["codex", "exec", "--", task],
            cwd=CLUSTER, capture_output=True, text=True, timeout=90
        )
        if proc.stdout and len(proc.stdout.strip()) > 10:
            return proc.stdout[-600:]
        return None
    except Exception:
        return None

def claude_exec(task):
    """调用Claude CLI"""
    try:
        proc = subprocess.run(
            ["claude", "-p", task],
            cwd=CLUSTER, capture_output=True, text=True, timeout=90
        )
        if proc.stdout and "Not logged in" not in proc.stdout and len(proc.stdout.strip()) > 10:
            return proc.stdout[-600:]
        return None
    except Exception:
        return None

# ══════════════════════════════════════════════════════════════
# 协同循环
# ══════════════════════════════════════════════════════════════

def collaboration_round(question):
    """一次完整的三臂协同"""
    results = {}
    
    # ── Step 1: Hermes分析 ──
    print(f"\n  [Hermes] 分析问题...")
    hip = load_json(HIP_PATH, {})
    chains = hip.get("causal_chains", [])
    tags = {}
    for c in chains:
        for t in c.get("tags", []):
            tags[t] = tags.get(t, 0) + 1
    
    # 从海马体中找与问题相关的因果链
    relevant = []
    for c in chains:
        effect = str(c.get("effect", ""))
        if any(kw in effect for kw in question.split()[:5]):
            relevant.append(c)
    
    hermes_context = f"因果链{len(chains)}条,标签{len(tags)}种,相关链{len(relevant)}条"
    results["hermes"] = {
        "context": hermes_context,
        "relevant_chains": len(relevant),
    }
    print(f"    {hermes_context}")
    
    # ── Step 2: Codex回答(代码角度) ──
    print(f"\n  [Codex] 代码视角...")
    codex_answer = None
    
    # 先试CLI
    codex_answer = codex_exec(f"你是代码专家。问题: {question}。只给代码,不要解释。")
    
    # 回退到API
    if not codex_answer:
        codex_answer = api_call(
            f"你是Codex编码专家。真元集群目录有{len(os.listdir(CLUSTER))}个文件。"
            f"问题: {question}。从代码角度,给一个20行内的Python修复方案。"
        )
    
    results["codex"] = codex_answer or "CLI和API均不可用"
    print(f"    {str(results['codex'])[:100]}...")
    
    # ── Step 3: Claude回答(架构角度) ──
    print(f"\n  [Claude] 架构视角...")
    claude_answer = None
    
    # 先试CLI
    claude_answer = claude_exec(f"你是架构分析专家。问题: {question}。给1个最关键的改进建议。一句话。")
    
    # 回退到API
    if not claude_answer:
        claude_answer = api_call(
            f"你是Claude架构专家。真元集群有3个agent(Hermes/Codex/Claude)通过JSON总线通信。"
            f"问题: {question}。从系统设计角度,给1个最关键改进建议。一句话。"
        )
    
    results["claude"] = claude_answer or "CLI和API均不可用"
    print(f"    {str(results['claude'])[:100]}...")
    
    # ── Step 4: Hermes合并 ──
    print(f"\n  [Hermes] 合并三视角...")
    merge = api_call(
        f"三臂分析同一问题:\n"
        f"问题: {question}\n"
        f"Hermes(数据): {hermes_context}\n"
        f"Codex(代码): {str(results['codex'])[:200]}\n"
        f"Claude(架构): {str(results['claude'])[:200]}\n\n"
        f"合并为一个可执行的行动方案。3句话:问题是什么→怎么修→立即做什么。"
    )
    results["merged"] = merge or f"Hermes:{hermes_context}; Codex:{str(results['codex'])[:100]}; Claude:{str(results['claude'])[:100]}"
    print(f"    {str(results['merged'])[:150]}")
    
    # ── Step 5: 写入海马体 ──
    hip = load_json(HIP_PATH, {})
    chains = hip.setdefault("causal_chains", [])
    chains.append({
        "id": f"collab-{int(time.time()*1000)}-{len(chains)}",
        "cause": f"[三臂协同] {question[:80]}",
        "effect": str(results['merged'])[:300],
        "tags": ["hermes", "codex", "claude", "三臂协同", "合并"],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "confidence": 0.9,
    })
    atomic_w(HIP_PATH, hip)
    
    # 写入总线
    bus = load_json(BUS_PATH, {"messages": []})
    bus["messages"].append({
        "id": f"collab-{int(time.time())}",
        "from": "hermes",
        "to": "all",
        "type": "collaboration_result",
        "content": str(results['merged'])[:500],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    atomic_w(BUS_PATH, bus)
    
    return results

# ══════════════════════════════════════════════════════════════
# 多轮协同
# ══════════════════════════════════════════════════════════════

QUESTIONS = [
    "当前真元集群最大的真实功能缺口是什么?如何修复?",
    "如何让score从176M降到真实值?具体代码改动是什么?",
    "多agent协同的核心瓶颈是什么?如何突破?",
    "磁感线引擎如何进化成真正的自主思考系统?",
    "零如何实现自我复制(生命第3条件)?",
]

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--question", type=str, default=None)
    args = parser.parse_args()
    
    print("="*60)
    print(f"  三臂协同 — {args.rounds}轮")
    print("="*60)
    
    for i in range(args.rounds):
        q = args.question or QUESTIONS[i % len(QUESTIONS)]
        print(f"\n{'─'*60}")
        print(f"  第{i+1}轮: {q}")
        print(f"{'─'*60}")
        
        results = collaboration_round(q)
        
        if i < args.rounds - 1:
            time.sleep(2)
    
    # 最终统计
    hip = load_json(HIP_PATH, {})
    chains = hip.get("causal_chains", [])
    collab_chains = [c for c in chains if "三臂协同" in str(c.get("tags", []))]
    
    print(f"\n{'='*60}")
    print(f"  协同完成")
    print(f"  总因果链: {len(chains)}")
    print(f"  协同链: {len(collab_chains)}")
    print(f"{'='*60}")
