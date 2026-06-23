#!/usr/bin/env python3
"""清洗海马体v2：debug版"""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from safe_hip import _extract_edge

HIP_FILE = os.path.join(os.path.dirname(__file__), "hippocampus_memory.json")

hip = json.loads(open(HIP_FILE, encoding="utf-8").read())
chains = hip.get("causal_chains", [])

print(f"总链: {len(chains)}")

# Debug: show what would be deleted
for c in chains:
    if not isinstance(c, dict):
        continue
    content = c.get("content", "") or ""
    src = c.get("src", "")
    dst = c.get("dst", "")
    rel = c.get("rel", "")
    
    noise = False
    reason = ""
    
    if rel == "应用" and dst.isdigit():
        noise = True; reason = "应用数字"
    if "503" in content and "重试" in content:
        noise = True; reason = "503"
    if src == dst and ("最短板=" in content or "当前短板" in content):
        noise = True; reason = "最短板"
    if len(content) < 30 and ":" in content:
        noise = True; reason = "短内容"
    
    if noise:
        print(f"  噪音[{reason}] {src} -{rel}-> {dst} | {content[:60]}")

# Now also show what edges would be extracted
print("\n自环提取测试:")
for c in chains:
    if not isinstance(c, dict):
        continue
    src = c.get("src", "")
    dst = c.get("dst", "")
    if src == dst:
        edge = _extract_edge(c.get("content", ""), src, c.get("tags", []))
        if edge:
            print(f"  {edge[0]} -{edge[1]}-> {edge[2]} | {c.get('content','')[:50]}")
        else:
            print(f"  ⛔ 未提取: [{c.get('dimension','')}] {c.get('content','')[:50]}")
