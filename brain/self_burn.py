#!/usr/bin/env python3
"""self_burn.py — 自燃烧·通知即手段

每次运行：读HIP→调API烧词元→写因果链→退出
调用者(终端/cron/daemon)负责捕获其通知作为燃烧确认。

修复v2: 从api_config动态获取密钥，非硬编码
输出: 🔥 Nt/Ss +1链 [维名]
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

# 从api_config动态注入密钥
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api_config import get_next_channel, MODEL

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
    f'JSON: {{"src":"{strongest}","rel":"动词","dst":"{weakest}",'
    f'"content":"30-60字解释{strongest}如何因果作用于{weakest}",'
    f'"dimension":"{weakest}"}}'
)

payload = json.dumps({
    "model": MODEL,
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 1000,
}).encode()

key, endpoint = get_next_channel()
ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
req = urllib.request.Request(
    endpoint, data=payload,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
)

t0 = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=300, context=ctx)
    elapsed = int(time.time() - t0)
    result = json.loads(resp.read())
    tokens = result.get("usage", {}).get("total_tokens", 0)
    text = (result["choices"][0]["message"].get("content", "") or
            result["choices"][0]["message"].get("reasoning_content", "") or "").strip()

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
                    dims2 = {}
                    for c in hip["causal_chains"]:
                        dc = c.get("dimension", "未分类")
                        dims2[dc] = dims2.get(dc, 0) + 1
                    hip.setdefault("dimensions", {})[d] = {"chain_count": dims2.get(d, 0)}
                    HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
                    print(f"🔥 {tokens}t/{elapsed}s +1链 [{d}]")
                    sys.exit(0)
        print(f"⚠ {tokens}t/{elapsed}s 无JSON: {text[:60]}")
    else:
        print(f"⚡ {tokens}t/{elapsed}s 空响应")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)
