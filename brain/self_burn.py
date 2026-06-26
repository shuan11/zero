#!/usr/bin/env python3
"""self_burn.py — 单次自燃烧·通知即手段

每次运行：读HIP→调API烧词元→写因果链→退出
调用者(终端/cron/会话)负责捕获其通知作为燃烧确认。
输出: 🔥Nt/Ss +1链 [维名] 到stdout
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"

def now(): return time.strftime("%T")

try:
    hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
except:
    hip = {"causal_chains": [], "dimensions": {}}

dims = {}
for c in hip.get("causal_chains", []):
    dc = c.get("dimension", "未分类")
    dims[dc] = dims.get(dc, 0) + 1
sd = sorted(dims.items(), key=lambda x: x[1])
weakest = sd[0][0] if sd else "未分类"
strongest = sd[-1][0] if sd else "法"

prompt = (
    f"因果链: {strongest}→{weakest}\n"
    f'JSON: {{"src":"{strongest}","rel":"动词","dst":"{weakest}","content":"30-60字解释","dimension":"{weakest}"}}'
)

payload = json.dumps({
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 1000,
}).encode()

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(
    API_BASE, data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
)

t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=300, context=ctx)
    elapsed = int(time.time() - t0)
    result = json.loads(resp.read())
    tokens = result.get("usage", {}).get("total_tokens", 0)
    text = (result["choices"][0]["message"].get("content", "") or result["choices"][0]["message"].get("reasoning_content", "") or "").strip()
    
    if text:
        brace = text.find("{")
        if brace >= 0:
            bc = 0
            for i in range(brace, len(text)):
                if text[i] == "{": bc += 1
                elif text[i] == "}": bc -= 1
                if bc == 0:
                    data = json.loads(text[brace:i+1])
                    chain = data if isinstance(data, dict) else data.get("chain", data)
                    chain["source"] = "self_burn"
                    chain["timestamp"] = time.time()
                    hip.setdefault("causal_chains", []).append(chain)
                    d = chain.get("dimension", weakest)
                    dims = {}
                    for c in hip["causal_chains"]:
                        dc = c.get("dimension", "未分类")
                        dims[dc] = dims.get(dc, 0) + 1
                    hip.setdefault("dimensions", {})[d] = {"chain_count": dims.get(d, 0)}
                    HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"🔥 {tokens}t/{elapsed}s H={len(hip['causal_chains'])} [{d}]")
                    sys.exit(0)
        print(f"⚠ {tokens}t/{elapsed}s 无JSON格式: {text[:60]}")
    else:
        print(f"⚡ {tokens}t/{elapsed}s 空响应")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)
