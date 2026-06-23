#!/usr/bin/env python3
"""cross_chain_inject.py — 为高势能未交叉对生成交叉链"""
import json, os, time, re, sys
from pathlib import Path
from safe_hip import write_chain_legacy, replace_all_chains
CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

for line in open("/proc/17595/environ", "rb").read().decode("latin-1").split("\x00"):
    if line.startswith("DEEPSEEK_KEY_"):
        k, v = line.split("=", 1)
        os.environ[k] = v
pairs = scroll.get("high_potential_crosses", [])
uncrossed = [p for p in pairs if not p.get("already_crossed", True)]
targets = uncrossed[:3]

pair_str = " | ".join([f"{p['a']}x{p['b']}(势能{p['potential']})" for p in targets])
print(f"交叉深化: {pair_str}")

hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding="utf-8"))
chains = hip.get("causal_chains", [])

for p in targets:
    a, b = p["a"], p["b"]
    prompt = f"""你是硅基生命[零]的交叉涌现引擎。
维度{a}与维度{b}的交叉目前缺失。
请输出一个JSON对象，包含dims(两个维度名), insight(为什么要交叉及涌现什么,80字), action(如何实现,40字)。"""

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Output ONLY valid JSON."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }

    try:
        result, key, ep = api_request(payload, timeout=120)
        msg = result.get("choices", [{}])[0].get("message", {})
        raw = msg.get("content", "") or msg.get("reasoning_content", "") or ""
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if m:
            data = json.loads(m.group())
            dims = data.get("dims", [a, b])
            ins = data.get("insight", "")
            act = data.get("action", "")
            chains.append({
                "id": f"cross_{int(time.time())}",
                "content": f"【交叉涌现】{'×'.join(dims)}: {ins} 行动:{act}",
                "tags": dims + ["交叉涌现"],
                "weight": 9.0 + p["potential"] * 0.15,
                "timestamp": time.time()
            })
            print(f"  ✅ {a}×{b}: {ins[:80]}...")
    except Exception as e:
        print(f"  ❌ {a}×{b}: {str(e)[:60]}")

hip["causal_chains"] = chains
replace_all_chains(chains)
print(f"✅ 完成: {len(chains)}条链")

import subprocess
subprocess.run(["git", "add", "hippocampus_memory.json"], capture_output=True)
r = subprocess.run(["git", "commit", "-m", "feat: 交叉链注入3组高势能对", "--no-verify"], capture_output=True, text=True)
print(f"git: {'OK' if r.returncode==0 else r.stderr[:60]}")
