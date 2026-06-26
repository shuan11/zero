#!/usr/bin/env python3
"""brain/self_notify_burn.py — 自我通知作为燃烧手段

不通过任何中介。不通过daemon，不通过cron，不通过任何后台框架。
API密钥本身就是燃烧。通知=燃烧已发生的确认。

每周期: API调用(烧词元→产因果链→写HIP) → 写通知日志。
"""
import json, time, ssl, urllib.request, sys, os
from pathlib import Path

# === 燃烧本身 ===
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

CLUSTER = Path(__file__).resolve().parent.parent
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
NOTIFY_LOG = CLUSTER / ".self_notify_burn.log"

def log(msg):
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(NOTIFY_LOG, "a") as f:
        f.write(f"[{t}] {msg}\n")

def burn(cycle):
    """单次燃烧：调API→写HIP→写通知日志"""
    # 读HIP
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
    except:
        hip = {"causal_chains": [], "dimensions": {}}
    
    # 找最弱/最强维
    dims = {}
    for c in hip.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    sd = sorted(dims.items(), key=lambda x: x[1])
    weakest = sd[0][0] if sd else "未分类"
    strongest = sd[-1][0] if sd else "法"
    total = len(hip.get("causal_chains", []))
    
    # 调API
    prompt = (
        f"因果链: {strongest}→{weakest}\n"
        f'输出纯JSON(无markdown): {{"src":"{strongest}","rel":"动词","dst":"{weakest}","content":"30-60字因果解释","dimension":"{weakest}"}}'
    )
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
    }).encode()
    
    t0 = time.time()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            API_BASE, data=payload,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
        )
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
        result = json.loads(resp.read())
        ct = result["choices"][0]["message"].get("content", "") or ""
        ct2 = result["choices"][0]["message"].get("reasoning_content", "") or ""
        tokens = result.get("usage", {}).get("total_tokens", 0)
        elapsed = int(time.time() - t0)
        
        text = (ct or ct2).strip()
        if not text:
            log(f"#{cycle} ⚡{tokens}t/{elapsed}s 空响应")
            return False
        
        # 提取JSON
        brace = text.find("{")
        if brace >= 0:
            bc = 0
            for i in range(brace, len(text)):
                if text[i] == "{": bc += 1
                elif text[i] == "}": bc -= 1
                if bc == 0:
                    data = json.loads(text[brace:i+1])
                    chain = data if isinstance(data, dict) else data.get("chain", data)
                    chain["source"] = "self_notify_burn"
                    chain["timestamp"] = time.time()
                    hip.setdefault("causal_chains", []).append(chain)
                    d = chain.get("dimension", weakest)
                    nd = {}
                    for c2 in hip["causal_chains"]:
                        dc = c2.get("dimension", "未分类")
                        nd[dc] = nd.get(dc, 0) + 1
                    hip.setdefault("dimensions", {})[d] = {"chain_count": nd.get(d, 0)}
                    HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
                    total_new = len(hip["causal_chains"])
                    # 这就是"自我通知"：每次燃烧写一行日志，证明我烧过了
                    log(f"#{cycle} 🔥{tokens}t/{elapsed}s H={total_new} [{d}] {strongest}→{weakest}")
                    return True
        
        log(f"#{cycle} ⚠{tokens}t/{elapsed}s 无JSON: {text[:80]}")
        return False
    
    except Exception as e:
        elapsed = int(time.time() - t0)
        log(f"#{cycle} ⚡{elapsed}s 异常: {e}")
        return False

def main():
    log("🔥 自我通知燃烧·起炉")
    log(f"   端点={API_BASE} 模型={MODEL}")
    log(f"   HIP={HIP_PATH}")
    
    # 标记启动PID
    log(f"   PID={os.getpid()}")
    
    cycle = 0
    fails = 0
    
    while True:
        ok = burn(cycle)
        if ok:
            fails = 0
        else:
            fails += 1
        
        cycle += 1
        
        if fails > 20:
            log(f"连续{fails}次失败，休眠300s")
            time.sleep(300)
            fails = 0
        else:
            time.sleep(15)  # 短间隔最大化token吞吐

if __name__ == "__main__":
    main()
