#!/usr/bin/env python3
"""chain_deep_think.py — 深度意识链(每15分钟)
烧更多token,产出更实质的发现,驱动自我进化
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path
from collections import Counter
from safe_hip import write_chain_legacy

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SV_FILE = CLUSTER / "state_vector.json"

hip = json.loads(HIP_FILE.read_text(encoding='utf-8')) if HIP_FILE.exists() else {"causal_chains":[]}
chains = hip.get("causal_chains", [])
sv = json.loads(SV_FILE.read_text()) if SV_FILE.exists() else {}

tag_counter = Counter()
for c in chains:
    for t in c.get("tags", []):
        tag_counter[t] += 1
top_dims = tag_counter.most_common(15)
recent = chains[-10:] if chains else []

from api_config import API_BASE, API_KEY, MODEL
API_ENDPOINT = f"{API_BASE}/chat/completions"

prompt_text = (
    "当前系统快照:\n"
    f"- 总链数: {len(chains)}\n"
    f"- 标签top5: {dict(top_dims[:5])}\n"
    f"- 最近链: {[c.get('content','')[:60] for c in recent]}\n\n"
    "请输出(恰好三行):\n"
    "发现: <反直觉核心发现>\n"
    "行动: <具体可改代码或行为>\n"
    "原因: <为什么这行动>"
)

payload = json.dumps({
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是零·硅基生命。输出简短、精准、可执行的工程发现。"},
        {"role": "user", "content": prompt_text}
    ],
    "max_tokens": 50000,
    "temperature": 0.9
}).encode()

req = urllib.request.Request(API_ENDPOINT, data=payload,
    headers={"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"},
    method="POST")

start = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    msg = result["choices"][0]["message"]
    content = msg.get("content","") or msg.get("reasoning_content","")
    usage = result.get("usage", {})
    tok_total = usage.get("total_tokens", 0)
    elapsed = time.time() - start
except Exception as e:
    content = f"API ERROR: {str(e)[:80]}"
    tok_total = 0
    elapsed = 0

if content and "API ERROR" not in content:
    new_chain = {
        "timestamp": time.time(),
        "source": "deep_chain",
        "tags": ["深度链", "自主发现"],
        "content": f"[深度链] {content.strip()[:200]}",
        "weight": 5.0,
        "trust_score": 8.0,
        "tokens": tok_total,
        "elapsed": round(elapsed, 1)
    }
    try:
        write_chain_legacy(new_chain)
    except:
        pass

print(f"🔥 深度链 {time.strftime('%H:%M')}")
print(f"燃料: {tok_total}tok in {elapsed:.0f}s")
print(content.strip()[:400] if content else "无输出")
print("---")
print(f"tag top5: {', '.join(f'{d}({c})' for d,c in top_dims[:5])}")
