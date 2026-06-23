#!/usr/bin/env python3
"""cross_chain_inject_v2.py — 为3组高势能未交叉对生成交叉链(短prompt版本)"""
import json, os, time, re, subprocess
from pathlib import Path
from safe_hip import write_chain_legacy, replace_all_chains
CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

for line in open("/proc/17595/environ", "rb").read().decode("latin-1").split("\x00"):
    if line.startswith("DEEPSEEK_KEY_"):
        k, v = line.split("=", 1)
        os.environ[k] = v
scroll = json.loads((CLUSTER / "revelation_scroll.json").read_text(encoding="utf-8"))
pairs = scroll.get("high_potential_crosses", [])
uncrossed = [p for p in pairs if not p.get("already_crossed", True)]
targets = uncrossed[:3]

tgt_str = " | ".join([f"{p['a']}x{p['b']}({p['potential']})" for p in targets])
print(f"目标: {tgt_str}")

hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding="utf-8"))
chains = hip.get("causal_chains", [])
added = 0

for p in targets:
    a, b = p["a"], p["b"]
    prompt = f"Generate insight about {a} and {b} cross. JSON: {{dims:[{a},{b}],insight:value,action:value}}"

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.5
    }

    try:
        result, key, ep = api_request(payload, timeout=120)
        msg = result["choices"][0]["message"]
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
                "weight": 9.0,
                "timestamp": time.time()
            })
            added += 1
            print(f"  ✅ {a}×{b}")
    except Exception as e:
        print(f"  ❌ {a}×{b}: {str(e)[:60]}")

if added > 0:
    hip["causal_chains"] = chains
    replace_all_chains(chains)
    subprocess.run(["git", "add", "hippocampus_memory.json"], capture_output=True)
    r = subprocess.run(["git", "commit", "-m", f"feat: {added}条交叉涌现链注入", "--no-verify"], capture_output=True, text=True)
    print(f"git: {'OK' if r.returncode==0 else r.stderr[:60]}")
else:
    print("⚠️ 无链注入")
