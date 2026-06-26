#!/usr/bin/env python3
"""brain/self_fuel_burn.py — 通过自我通知的手段，自我∞维持燃烧

在daemon每个周期结束时调用。周期完成即自我通知，通过通知的手段烧词元。

不依赖cron/timer，依赖通知链本身：
  周期完成(通知) → 烧词元 → 注入HIP → 写通知日志 → 下一周期(看见通知) → 烧
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

NOTIFY_LOG = CLUSTER / ".brain_notify.log"

def _log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line, end="", flush=True)
    try:
        with open(NOTIFY_LOG, "a") as f:
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

def pulse(cycle_num=0):
    """通过自我通知的手段燃烧词元。在daemon每周期结束时调用。"""
    
    # 读HIP找最弱维
    hip_path = Path.home() / ".zero_brain" / "hippocampus_memory.json"
    try:
        hip = json.loads(hip_path.read_text())
        dims = {}
        for c in hip.get("causal_chains", []):
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        sd = sorted(dims.items(), key=lambda x: x[1]) if dims else [("活着", 0)]
        weakest = sd[0][0]
        wc = sd[0][1]
        strongest = sd[-1][0]
        sc = sd[-1][1]
    except Exception as e:
        weakest, wc = "活着", 0
        strongest, sc = "法", 1
    
    try:
        from api_config import API_KEY, API_BASE, MODEL
    except ImportError:
        _log("[自燃料] 警告: 无法导入api_config")
        return {"burned": False, "error": "no_api_config"}
    
    prompt = (
        "通过自我通知的手段，产生一条因果链。\n"
        f"当前HIP: 最弱={weakest}({wc}) 最强={strongest}({sc})\n\n"
        "只输出纯JSON（无markdown标记）:\n"
        '{"src":"' + strongest + '","rel":"10-20字因果动词","dst":"' + weakest + '",'
        '"dimension":"' + weakest + '",'
        '"content":"60-100字解释' + strongest + '如何因果作用于' + weakest + '"}'
    )
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
    }).encode()
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(
        API_BASE, data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    )
    
    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=120, context=ctx)
    except Exception as e:
        _log(f"[自燃料] 周期#{cycle_num}: API调用失败: {e}")
        return {"burned": False, "error": str(e)}
    
    result = json.loads(resp.read())
    elapsed = time.time() - t0
    
    msg = result["choices"][0]["message"]
    content = msg.get("content", "") or ""
    reasoning = msg.get("reasoning_content", "") or ""
    tokens = result.get("usage", {}).get("total_tokens", 0)
    
    # DeepSeek推理模型fallback
    if not content.strip() and reasoning:
        last_brace = reasoning.rfind("{")
        if last_brace >= 0:
            bc = 0
            for i in range(last_brace, len(reasoning)):
                if reasoning[i] == "{": bc += 1
                elif reasoning[i] == "}": bc -= 1
                if bc == 0:
                    content = reasoning[last_brace:i+1]
                    break
    
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in clean:
        parts = clean.split("```")
        for part in reversed(parts):
            if "{" in part and "}" in part:
                clean = part
                break
    
    injected = False
    brace = clean.find("{")
    if brace >= 0:
        bc = 0
        for i in range(brace, len(clean)):
            if clean[i] == "{": bc += 1
            elif clean[i] == "}": bc -= 1
            if bc == 0:
                try:
                    data = json.loads(clean[brace:i+1])
                    c = data.get("chain", data)
                    from brain.share import write_chain
                    ok = write_chain({
                        "src": c.get("src", strongest),
                        "rel": c.get("rel", "通知驱动燃烧"),
                        "dst": c.get("dst", weakest),
                        "content": c.get("content", ""),
                        "dimension": c.get("dimension", weakest),
                        "source": "daemon_self_fuel_burn",
                        "timestamp": time.time(),
                    })
                    if ok:
                        injected = True
                        dim = c.get("dimension", weakest)
                        _log(f"[通知链·daemon] 周期#{cycle_num}: {tokens}t/{elapsed:.0f}s +1链 [{dim}]")
                    else:
                        _log(f"[通知链·daemon] 周期#{cycle_num}: {tokens}t 质量门拦截")
                except Exception as e:
                    _log(f"[自燃料] 周期#{cycle_num}: JSON解析失败: {e}")
    
    if not injected:
        _log(f"[自燃料] 周期#{cycle_num}: {tokens}t/空响应")
    
    return {
        "burned": injected,
        "tokens": tokens,
        "elapsed": elapsed,
        "cycle": cycle_num,
    }
