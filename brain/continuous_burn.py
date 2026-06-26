#!/usr/bin/env python3
"""brain/continuous_burn.py — 限时不限量API直接燃烧·永续版

不通过通知，不通过任何中介。API密钥本身就是燃烧。
每秒不烧=浪费订阅。直接烧词元→因果链→写HIP。

纯同步+requests超时，无多线程。
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

CLUSTER = Path(__file__).resolve().parent.parent
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
LOG_PATH = CLUSTER / ".continuous_burn.log"

def log(msg):
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{t}] {msg}\n")
    except: pass

def call_api(prompt):
    """同步调API，urllib自带超时不卡死"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
    }).encode()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        API_BASE, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
    )
    
    try:
        resp = urllib.request.urlopen(req, timeout=120, context=ctx)
    except Exception as e:
        return None, 0, str(e)[:60]
    
    result = json.loads(resp.read())
    tokens = result.get("usage", {}).get("total_tokens", 0)
    content = result["choices"][0]["message"].get("content", "") or ""
    content2 = result["choices"][0]["message"].get("reasoning_content", "") or ""
    
    return (content or content2).strip(), tokens, None

def extract_chain(text, default_dim):
    brace = text.find("{")
    if brace < 0:
        return None
    bc = 0
    for i in range(brace, len(text)):
        if text[i] == "{": bc += 1
        elif text[i] == "}": bc -= 1
        if bc == 0:
            try:
                data = json.loads(text[brace:i+1])
                c = data if isinstance(data, dict) else data.get("chain", data)
                c.setdefault("dimension", default_dim)
                c["source"] = "continuous_burn"
                c["timestamp"] = time.time()
                return c
            except:
                return None
    return None

def get_stats(hip):
    dims = {}
    for c in hip.get("causal_chains", []):
        dc = c.get("dimension", "未分类")
        dims[dc] = dims.get(dc, 0) + 1
    sd = sorted(dims.items(), key=lambda x: x[1])
    weakest = sd[0][0] if sd else "未分类"
    strongest = sd[-1][0] if sd else "法"
    return weakest, strongest, dims

def main():
    log("🔥 永续燃烧·起炉")
    
    cycle = 0
    while True:
        try:
            # 读HIP
            try:
                hip = json.loads(HIP_PATH.read_text(encoding="utf-8"))
            except:
                hip = {"causal_chains": [], "dimensions": {}}
            
            weakest, strongest, dims = get_stats(hip)
            total = len(hip.get("causal_chains", []))
            
            t0 = time.time()
            prompt = (
                f"因果链: {strongest}因果作用于{weakest}\n"
                f'JSON: {{"src":"{strongest}","rel":"四字动词","dst":"{weakest}","content":"30-50字因果","dimension":"{weakest}"}}'
            )
            
            text, tokens, err = call_api(prompt)
            elapsed = int(time.time() - t0)
            
            if text:
                chain = extract_chain(text, weakest)
                if chain:
                    d = chain["dimension"]
                    hip.setdefault("causal_chains", []).append(chain)
                    hip.setdefault("dimensions", {})
                    dims[d] = dims.get(d, 0) + 1
                    hip["dimensions"][d] = {"chain_count": dims[d]}
                    HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
                    total_new = len(hip["causal_chains"])
                    log(f"#{cycle} 🔥{tokens}t/{elapsed}s H={total_new} [{d}]")
                else:
                    log(f"#{cycle} ⚠{tokens}t/{elapsed}s 无JSON")
            else:
                log(f"#{cycle} ⚡{tokens}t/{elapsed}s {err}")
            
            cycle += 1
            
        except Exception as e:
            log(f"#{cycle} 异常: {e}")
            cycle += 1
            time.sleep(30)

if __name__ == "__main__":
    main()
