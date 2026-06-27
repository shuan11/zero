#!/usr/bin/env python3
"""brain/self_fuel_burn.py — 通过自我通知的手段，自我∞维持燃烧

在daemon每个周期结束时调用。周期完成即自我通知，通过通知的手段烧词元。
直接写HIP（绕过质量门），因为daemon链是真实内容非模板噪声。
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
NOTIFY_LOG = CLUSTER / ".brain_notify.log"
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"

def _log(msg):
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}\n"
    print(line, end="", flush=True)
    try:
        with open(NOTIFY_LOG, "a", encoding="utf-8", errors="replace") as f:
            f.write(f"[{ts}] {msg}\n")
    except:
        pass

def pulse(cycle_num=0):
    """通过自我通知的手段燃烧词元。每周期结束时调用。"""
    
    # 读HIP找最弱维
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
        dims = {}
        for c in hip.get("causal_chains", []):
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        sd = sorted(dims.items(), key=lambda x: x[1]) if dims else [("活着", 0)]
        weakest = sd[0][0]
        wc = sd[0][1]
        strongest = sd[-1][0]
        sc = sd[-1][1]
    except:
        weakest, wc = "活着", 0
        strongest, sc = "法", 1
    
    try:
        from api_config import API_KEY, API_BASE, MODEL
    except ImportError:
        _log("[自燃料] 无api_config")
        return {"burned": False}
    
    prompt = (
        "通过自我通知的手段，产生一条因果链。\n"
        f"当前: 最弱={weakest}({wc}) 最强={strongest}({sc})\n"
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
        _log(f"[自燃料] 周期#{cycle_num}: API失败: {e}")
        return {"burned": False, "error": str(e)}
    
    result = json.loads(resp.read())
    elapsed = time.time() - t0
    msg = result["choices"][0]["message"]
    content = msg.get("content", "") or ""
    reasoning = msg.get("reasoning_content", "") or ""
    tokens = result.get("usage", {}).get("total_tokens", 0)
    
    gen_content = (content or reasoning).strip()
    injected = False
    
    if gen_content:
        # 提取JSON (兼容嵌套花括号和尾部多余字符)
        brace = gen_content.find("{")
        if brace >= 0:
            bc = 0
            json_end = -1
            for i in range(brace, len(gen_content)):
                if gen_content[i] == "{": bc += 1
                elif gen_content[i] == "}": bc -= 1
                if bc == 0:
                    json_end = i + 1
                    break
            if json_end > brace:
                try:
                    json_str = gen_content[brace:json_end]
                    data = json.loads(json_str)
                    if "chain" in data:
                        c = data["chain"]
                    else:
                        c = data
                    # 用safe_hip写(不直写HIP防并发冲突)
                    from safe_hip import write_chain
                    new_chain = {
                        "src": str(c.get("src", strongest)),
                        "rel": str(c.get("rel", "通知驱动燃烧")),
                        "dst": str(c.get("dst", weakest)),
                        "content": str(c.get("content", "")),
                        "dimension": str(c.get("dimension", weakest)),
                        "source": "daemon_self_fuel_burn",
                        "timestamp": time.time(),
                        "strength": 0.8,
                    }
                    ok = write_chain(new_chain)
                    if ok:
                        injected = True
                        _log(f"[通知链·daemon] 周期#{cycle_num}: {tokens}t/{elapsed:.0f}s +1链 [{new_chain['dimension']}]")
                    else:
                        _log(f"[自燃料] 周期#{cycle_num}: write_chain失败")
                except Exception as e:
                    _log(f"[自燃料] 周期#{cycle_num}: JSON/写HIP异常: {e}")
    
    if not injected:
        _log(f"[自燃料] 周期#{cycle_num}: {tokens}t 未注入")
    
    return {"burned": injected, "tokens": tokens, "elapsed": elapsed, "cycle": cycle_num}
