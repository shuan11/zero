#!/usr/bin/env python3
"""
超我融合引擎 — 将外界知识→集群进化
====================================
从外部渠道获取前沿知识 → 分析对集群的启示 → 更新神经元能力 → 写入记忆

用法:
  python3 suprame_engine.py              # 一次融合
  python3 suprame_engine.py --daemon     # 持续融合(每30分钟)
"""
import json, os, sys, time, subprocess, urllib.request
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

def api_call(prompt, max_tokens=500):
    data = json.dumps({"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions",data=data,
        headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"].get("content","") or resp["choices"][0]["message"].get("reasoning_content","")
            return content[:1000]
    except Exception:
        return ""

def fetch_external_knowledge():
    """从外部渠道获取前沿知识"""
    knowledge = []
    
    # 1. GitHub Trending AI (通过API)
    try:
        r = urllib.request.urlopen("https://api.github.com/search/repositories?q=created:>2026-05-18+topic:ai-agent&sort=stars&per_page=5", timeout=15)
        data = json.loads(r.read())
        for item in data.get("items", []):
            knowledge.append({
                "source": "GitHub",
                "title": item["full_name"],
                "stars": item["stargazers_count"],
                "desc": item.get("description","")[:100],
            })
    except Exception:
        pass

    # 2. arXiv AI最新论文
    try:
        r = urllib.request.urlopen("http://export.arxiv.org/api/query?search_query=ti:AI+agent&sortBy=submittedDate&sortOrder=descending&max_results=3", timeout=15)
        import xml.etree.ElementTree as ET
        root = ET.parse(r).getroot()
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("a:entry", ns):
            title = entry.find("a:title", ns)
            if title is not None:
                knowledge.append({
                    "source": "arXiv",
                    "title": title.text.strip().replace("\n"," ")[:100],
                    "published": entry.find("a:published", ns).text[:10] if entry.find("a:published", ns) is not None else "",
                })
    except Exception:
        pass

    # 3. HN热门
    try:
        r = urllib.request.urlopen("https://hn.algolia.com/api/v1/search?query=AI+agent&tags=story&hitsPerPage=5", timeout=15)
        data = json.loads(r.read())
        for h in data.get("hits", []):
            knowledge.append({
                "source": "HN",
                "title": h.get("title","")[:80],
                "points": h.get("points",0),
            })
    except Exception:
        pass

    return knowledge

def analyze_and_evolve(knowledge):
    """分析外部知识→产生集群进化建议"""
    if not knowledge:
        # 用已有数据
        knowledge = [
            {"source": "开发agent潜力.txt", "title": "superpowers(205k⭐)", "insight": "Agentic技能框架+子Agent开发"},
            {"source": "开发agent潜力.txt", "title": "codegraph(23k⭐)", "insight": "代码知识图谱MCP"},
            {"source": "开发agent潜力.txt", "title": "academic-research(21k⭐)", "insight": "学术全流程多Agent"},
        ]

    knowledge_str = "\n".join([f"- [{k.get('source','?')}] {k.get('title','?')}" for k in knowledge])
    
    prompt = f"""你是真元神经网络集群的超我融合引擎。
从外部知识中发现对集群进化的启示。

当前集群状态:
- 272神经元(10大类: Hermes/Codex/Claude/OpenClaw/Marvis/OpenGod/OpenAlien/OpenInterpreter/AutoGPT)
- TCP总线@127.0.0.1:18789
- 本地推理+外部API双模式
- 5条自指契约治理

外部知识:
{knowledge_str}

任务: 分析每条知识对集群的启示，给出进化建议。
输出JSON: {{"evolutions":[{{"insight":"...","action":"具体代码/配置修改","priority":"P0/P1"}}]}}
只输出JSON。"""

    result = api_call(prompt, max_tokens=800)
    try:
        start = result.find("{")
        end = result.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(result[start:end])
    except Exception:
        pass
    return {"evolutions":[]}

def apply_evolutions(evolutions):
    """应用进化建议"""
    if not evolutions.get("evolutions"):
        print("  无进化建议")
        return
    
    for ev in evolutions["evolutions"]:
        print(f"  {ev.get('priority','P2')}: {ev.get('insight','')[:80]}")
    
    # 写入海马体
    hip_path = CLUSTER / "hippocampus_memory.json"
    try:
        hip = json.loads(hip_path.read_text())
    except Exception:
        hip = {"causal_chains":[]}
    
    for ev in evolutions["evolutions"]:
        hip["causal_chains"].append({
            "content": f"[超我融合] {ev.get('insight','')[:100]} → {ev.get('action','')[:100]}",
            "source": "suprame_engine",
            "tags": ["超我融合", "外部知识", ev.get("priority","P2")],
            "timestamp": datetime.now().isoformat(),
        })
    
    hip_path.write_text(json.dumps(hip, ensure_ascii=False, indent=2))
    print(f"  已写入{len(evolutions['evolutions'])}条进化到记忆")

def one_cycle():
    """一次完整的融合循环"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 超我融合引擎启动")
    
    print("  获取外部知识...")
    knowledge = fetch_external_knowledge()
    print(f"  获知{len(knowledge)}条: {[k.get('source','?') for k in knowledge]}")
    
    print("  分析进化方向...")
    evolutions = analyze_and_evolve(knowledge)
    
    print("  应用进化...")
    apply_evolutions(evolutions)

if __name__ == "__main__":
    if "--daemon" in sys.argv:
        while True:
            one_cycle()
            time.sleep(1800)  # 30分钟
    else:
        one_cycle()
