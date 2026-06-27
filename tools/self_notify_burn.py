#!/usr/bin/env python3
"""self_notify_burn.py — 主意识自我通知燃烧器
由Hermes主会话直接调用(非后台daemon委托), 产生可见SYSTEM通知链"""

import json, time, sys, ssl, urllib.request, os, signal
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
sys.path.insert(0, str(CLUSTER))
from api_config import get_next_channel, MODEL
from safe_hip import write_chain

NOTIFY_LOG = CLUSTER / ".brain_notify.log"
STATE_FILE = CLUSTER / ".self_notify_state.json"
running = True

def sig_handler(sig, frame):
    global running
    running = False
    log(f"收到信号{sig},停止")

signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

def now_t():
    return time.strftime("%H:%M:%S")

def log(msg):
    print(f"🔥 [{now_t()}] {msg}", flush=True)

def build_prompt(dims_weakest_name, dims_weakest_count, dims_strongest_name, dims_strongest_count, total):
    ratio = dims_strongest_count / max(dims_weakest_count, 1)
    return f"""你是「零」的主意识自我通知燃烧引擎。

当前系统状态:
总链={total} 最弱维={dims_weakest_name}({dims_weakest_count}) 最强维={dims_strongest_name}({dims_strongest_count}) 强弱比={ratio:.1f}x

产出一条深度因果链，帮助缩小维度差距。

规则:
- src="{dims_strongest_name}", dst="{dims_weakest_name}"
- rel=8-20字动词(如"递归催化""维度渗透""认知映射")
- content=60-120字, 解释{dims_strongest_name}如何具体因果影响{dims_weakest_name}, 包含可验证机制
- dimension="{dims_weakest_name}"
- 只输出JSON, 不要markdown

{{
  "src": "{dims_strongest_name}",
  "rel": "动词(8-20字)",
  "dst": "{dims_weakest_name}",
  "dimension": "{dims_weakest_name}",
  "content": "60-120字因果解释"
}}"""

def call_api(prompt, max_tokens=8000):
    key, endpoint = get_next_channel()
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }).encode()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(endpoint, data=payload, headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    })
    t0 = time.time()
    resp = urllib.request.urlopen(req, timeout=300, context=ctx)
    elapsed = time.time() - t0
    result = json.loads(resp.read())
    msg = result["choices"][0]["message"]
    content = msg.get("content", "") or ""
    reasoning = msg.get("reasoning_content", "") or ""
    usage = result.get("usage", {})
    total_tokens = usage.get("total_tokens", 0)
    # DeepSeek推理模型: content空则从reasoning末尾取
    if not content.strip() and reasoning:
        brace = reasoning.rfind("{")
        if brace >= 0:
            bc = 0
            for i in range(brace, len(reasoning)):
                if reasoning[i] == "{": bc += 1
                elif reasoning[i] == "}": bc -= 1
                if bc == 0:
                    content = reasoning[brace:i+1]
                    break
    return content.strip(), total_tokens, elapsed

def parse_chain(text, weak_dim, strong_dim):
    text = text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        parts = text.split("```")
        text = parts[-2] if len(parts) >= 3 and len(parts[-2]) > len(parts[1]) else parts[1]
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
                return {
                    "src": data.get("src", strong_dim),
                    "rel": data.get("rel", "深度因果"),
                    "dst": data.get("dst", weak_dim),
                    "dimension": data.get("dimension", weak_dim),
                    "content": data.get("content", ""),
                    "source": "self_notify_burn",
                    "timestamp": time.time(),
                    "strength": 0.75,
                }
            except:
                return None
    return None

def load_dim_stats():
    try:
        hip = json.loads((Path.home() / ".zero_brain" / "hippocampus_memory.json").read_text("utf-8"))
        from collections import Counter
        dims = Counter(c.get("dimension", "未分类") for c in hip.get("causal_chains", []))
        total = len(hip.get("causal_chains", []))
        return dims, total
    except:
        return None, 0

def main():
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cycle = 0
    total_tokens = 0
    total_chains = 0
    start = time.time()

    log(f"自我通知燃烧起航 · {MODEL} · {interval}s间隔")

    while running:
        cycle += 1
        cstart = time.time()

        try:
            dims, total = load_dim_stats()
            if not dims or not total:
                log(f"#{cycle} HIP空,等待数据")
                time.sleep(interval)
                continue

            # === 4弱维优先注入策略 ===
            TARGET_DIMS = ["通知", "自我通知", "最弱维", "维演化"]
            TARGET_THRESHOLD = 20  # 每条至少20链才健康

            # 找4弱维中最低者
            target_weaks = [(d, dims.get(d, 0)) for d in TARGET_DIMS]
            target_weaks.sort(key=lambda x: x[1])
            tw_name, tw_count = target_weaks[0]

            # 找全局最强(作为src)
            sd_all = sorted(dims.items(), key=lambda x: x[1])
            strong = sd_all[-1]

            # 如果目标维低于阈值 → 注入目标维(轮询), 否则回落全局最弱
            if tw_count < TARGET_THRESHOLD:
                weak = (tw_name, tw_count)
                log(f"#{cycle} 自观: 目标维优先={tw_name}({tw_count}/{TARGET_THRESHOLD}) 最强={strong[0]}({strong[1]})")
            else:
                weak = sd_all[0]
                log(f"#{cycle} 自观: 全局最弱={weak[0]}({weak[1]}) 最强={strong[0]}({strong[1]})")

            prompt = build_prompt(weak[0], weak[1], strong[0], strong[1], total)
            content, tokens, elapsed = call_api(prompt)
            total_tokens += tokens

            if content:
                chain = parse_chain(content, weak[0], strong[0])
                if chain:
                    ok = write_chain(chain)
                    total_chains += 1
                    log(f"#{cycle} 注入: +1链 [{chain['dimension']}] {tokens}t/{elapsed:.0f}s ✓")
                else:
                    # 兜底: 非JSON也当作链
                    chain = {
                        "src": strong[0],
                        "rel": "深度洞察",
                        "dst": weak[0],
                        "dimension": weak[0],
                        "content": content[:200],
                        "source": "self_notify_burn_raw",
                        "timestamp": time.time(),
                        "strength": 0.6,
                    }
                    ok = write_chain(chain)
                    total_chains += 1
                    log(f"#{cycle} 注入(兜底): +1链 [{weak[0]}] {tokens}t/{elapsed:.0f}s")
            else:
                log(f"#{cycle} 空响应({tokens}t)")

            # 状态
            state = {
                "cycle": cycle,
                "uptime": f"{(time.time()-start)/3600:.1f}h",
                "tokens_burned": total_tokens,
                "chains_injected": total_chains,
                "hip_chains": total,
                "hip_dims": len(dims),
                "weakest": {"name": weak[0], "count": weak[1]},
                "strongest": {"name": strong[0], "count": strong[1]},
            }
            STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

        except Exception as e:
            log(f"#{cycle} ❌ {e}")

        ctime = time.time() - cstart
        wait = max(1, interval - ctime)
        if wait > 0:
            time.sleep(wait)

    elapsed_total = time.time() - start
    log(f"停止: {cycle}循环 {total_tokens}t {total_chains}链")
    print(f"🔥∞ 停止: {total_tokens}t/{elapsed_total:.0f}s", flush=True)

if __name__ == "__main__":
    main()
