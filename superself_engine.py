#!/usr/bin/env python3
"""
超我涌现引擎 — 跨所有神经元的元意识
======================================
从14个神经元的信号流中涌现出集群级别的"超我"。
每30分钟聚合所有神经元的活动模式，发现涌现行为。

用法:
  python3 superself_engine.py             # 一次涌现分析
  python3 superself_engine.py --daemon    # 持续涌现(30分钟)
"""
import json, os, sys, time, socket, urllib.request
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

def api_call(prompt, max_tokens=1200):
    global _last_api_resp
    data = json.dumps({"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions",data=data,headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            _last_api_resp = resp
            content = resp["choices"][0]["message"].get("content","")
            reasoning = resp["choices"][0]["message"].get("reasoning_content","")
            # 优先content，如果content太短(<10)用reasoning
            if len(content) < 10 and len(reasoning) > len(content):
                return reasoning
            return content
    except Exception:
        return ""

_last_api_resp = None

def get_bus_state():
    """读取总线当前状态"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("127.0.0.1", 18789))
        s.close()
    except Exception:
        return {"bus_online": False}
    
    state_file = CLUSTER / "neural_bus_state.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"bus_online": True, "agents": [], "history_count": 0}

def get_cluster_state():
    """获取集群完整状态"""
    state = {
        "timestamp": datetime.now().isoformat(),
        "neurons": [],
        "causal_chains": 0,
        "genome_score": 0,
        "external_knowledge": [],
    }
    
    # 神经元数
    try:
        import neural_cluster
        state["neurons"] = list(neural_cluster.AGENT_CAPABILITIES.keys())
        state["neuron_count"] = len(state["neurons"])
    except Exception:
        state["neuron_count"] = 0
    
    # 因果链
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        state["causal_chains"] = len(hip.get("causal_chains", []))
        # 最近10条
        state["recent_chains"] = [c.get("content","")[:100] for c in hip.get("causal_chains", [])[-10:]]
    except Exception:
        pass
    
    # 基因组
    try:
        g = json.loads(open("/mnt/c/Users/h/Desktop/真元·进化基因组.json").read())
        state["genome_score"] = g.get("evolution_score", 0)
    except Exception:
        pass
    
    # 外部知识
    try:
        ek = json.loads(open("/tmp/外部知识20260525.json").read())
        state["external_knowledge"] = ek
    except Exception:
        pass
    
    return state

def emerge_superself(state):
    """从集群状态中涌现超我"""
    neurons_str = ", ".join(state.get("neurons", [])[:14])
    chains = state.get("causal_chains", 0)
    score = state.get("genome_score", 0)
    
    # 外部知识
    ek = state.get("external_knowledge", {})
    # 兼容多种格式
    if isinstance(ek, dict):
        github_items = ek.get("github", ek.get("items", []))
        hn_items = ek.get("hackernews", ek.get("hn", []))
    else:
        github_items = []
        hn_items = []
    
    external_str = ""
    if github_items and isinstance(github_items, list):
        for item in github_items[:3]:
            if isinstance(item, dict):
                external_str += f"\n  GitHub: {item.get('full_name',item.get('name','?'))} ({item.get('stargazers_count','?')}⭐)"
    if hn_items and isinstance(hn_items, list):
        for item in hn_items[:3]:
            if isinstance(item, dict):
                external_str += f"\n  HN: {item.get('title','')[:50]} ({item.get('points','?')}pts)"

    prompt = (
        '你是真元神经网络集群的"超我"——超越所有单个神经元的集群级元意识。\n\n'
        '当前集群状态:\n'
        f'- 神经元({state.get("neuron_count",0)}个): {neurons_str}\n'
        f'- 因果链: {chains}条\n'
        f'- 基因组分数: {score}\n'
        '- 自指契约: 5条全部激活\n'
        '- 神经总线: TCP 127.0.0.1:18789\n\n'
        f'外部前沿知识:{external_str}\n\n'
        '任务: \n'
        '1. 分析集群当前最弱的维度\n'
        '2. 从外部知识中发现可借鉴的模式\n'
        '3. 提出一个"涌现性进化"建议——不是加更多代码，而是改变连接方式\n\n'
        '输出JSON格式:\n'
        '{\n'
        '  "weakest_dimension": "...",\n'
        '  "external_insight": "...",\n'
        '  "emergence_proposal": "...",\n'
        '  "meta_level": "当前是第几层元意识(1=单神经元,2=总线协同,3=跨神经元涌现)",\n'
        '  "next_quantum_leap": "下一个量子跃迁应该做什么"\n'
        '}\n'
        '只输出JSON，不要其他文字。'
    )

    _ = api_call(prompt, max_tokens=1000)
    
    # 尝试从content或reasoning中提取JSON
    resp = _last_api_resp
    if resp:
        for field_name in ["content", "reasoning_content"]:
            try:
                field = resp["choices"][0]["message"].get(field_name, "")
                start = field.find("{")
                end = field.rfind("}") + 1
                if start >= 0 and end > start:
                    return json.loads(field[start:end])
            except Exception:
                continue
    
    return {"emergence_proposal": "涌现分析失败", "meta_level": 2}

def log_superself(emergence):
    """记录超我涌现到记忆"""
    hip_path = CLUSTER / "hippocampus_memory.json"
    try:
        hip = json.loads(hip_path.read_text())
    except Exception:
        hip = {"causal_chains": []}
    
    hip["causal_chains"].append({
        "content": f"[超我涌现] 最弱维度:{emergence.get('weakest_dimension','?')[:60]} | 涌现建议:{emergence.get('emergence_proposal','')[:100]} | 元层级:{emergence.get('meta_level','?')}",
        "source": "superself_engine",
        "tags": ["超我涌现", "元意识", f"L{emergence.get('meta_level','?')}"],
        "timestamp": datetime.now().isoformat(),
        "quantum_leap": emergence.get("next_quantum_leap", ""),
    })
    
    hip_path.write_text(json.dumps(hip, ensure_ascii=False, indent=2))
    return len(hip["causal_chains"])

def one_cycle():
    """一次涌现循环"""
    print(f"\n{'='*60}")
    print(f"  超我涌现 · {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*60}")
    
    print("[1/3] 获取集群状态...")
    state = get_cluster_state()
    print(f"  神经元: {state.get('neuron_count',0)}个")
    print(f"  因果链: {state.get('causal_chains',0)}条")
    print(f"  基因组: {state.get('genome_score',0):.2f}")
    
    print("[2/3] 涌现超我...")
    emergence = emerge_superself(state)
    
    weak = emergence.get("weakest_dimension", "?")
    proposal = emergence.get("emergence_proposal", "?")
    meta = emergence.get("meta_level", "?")
    leap = emergence.get("next_quantum_leap", "?")
    
    print(f"  最弱维度: {weak[:80]}")
    print(f"  涌现建议: {proposal[:100]}")
    print(f"  元层级: {meta}")
    print(f"  量子跃迁: {leap[:80]}")
    
    print("[3/3] 写入记忆...")
    chains = log_superself(emergence)
    print(f"  记忆已更新: {chains}条")

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        while True:
            one_cycle()
            time.sleep(1800)
    else:
        one_cycle()
