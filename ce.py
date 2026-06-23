#!/usr/bin/env python3
"""ce.py — Combustion Engine v1
单进程while循环燃烧引擎。不在进程间链式Popen。
每轮独立API调用，失败自动重试3次后切端点。
每轮写_burn_results/时间戳文件。每100轮写state_vector。
永不退出除非收到SIGTERM/SIGINT。
"""
import os, sys, time, signal, json, random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_config import API_BASE, API_BASE_FALLBACK, API_KEY, MODEL

ENDPOINTS = [API_BASE, API_BASE_FALLBACK]
RUN_DIR = os.path.dirname(os.path.abspath(__file__))
BURN_DIR = os.path.join(RUN_DIR, "_burn_results")
os.makedirs(BURN_DIR, exist_ok=True)

running = True

def handle_signal(sig, frame):
    global running
    running = False
    print(f"\n[SIGNAL] {sig} received, shutting down...", file=sys.stderr)

signal.signal(signal.SIGTERM, handle_signal)
signal.signal(signal.SIGINT, handle_signal)

def api_call(endpoint, payload, max_tokens=16000):
    """Single API call with timeout."""
    import urllib.request
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是零的燃烧引擎。深度思考，真实第一，不编造。"},
            {"role": "user", "content": payload}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(f"{endpoint}/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    resp = urllib.request.urlopen(req, timeout=180)
    r = json.loads(resp.read())
    c = r["choices"][0]["message"].get("content", "") or r["choices"][0]["message"].get("reasoning_content", "")
    t = r.get("usage", {}).get("total_tokens", 0)
    return c, t

def burn_once(payload, max_tokens=16000):
    """One burn with retry + endpoint fallback."""
    for endpoint in ENDPOINTS:
        for attempt in range(3):
            try:
                content, tokens = api_call(endpoint, payload, max_tokens)
                return content, tokens, endpoint, "ok"
            except Exception as e:
                print(f"  [RETRY] {endpoint} attempt {attempt+1}: {e}", file=sys.stderr)
                if attempt < 2:
                    time.sleep(2 ** attempt + random.random())
    return "", 0, "", "all_failed"

def save_result(stamp, content, tokens, endpoint, status, payload):
    """Save burn result to _burn_results/"""
    fname = f"ce_{stamp}.json"
    path = os.path.join(BURN_DIR, fname)
    with open(path, "w") as f:
        json.dump({
            "timestamp": stamp, "status": status,
            "tokens": tokens, "endpoint": endpoint,
            "content": content[:2000],
            "payload": payload[:200]
        }, f, ensure_ascii=False)
    return path

def update_state_vector(cycle, total_burns, total_tokens):
    """Update state_vector.json every 100 cycles."""
    sv_path = os.path.join(RUN_DIR, "state_vector.json")
    try:
        with open(sv_path) as f:
            sv = json.load(f)
        sv["ce_cycle"] = cycle
        sv["ce_burns"] = total_burns
        sv["ce_tokens"] = total_tokens
        sv["ce_last"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(sv_path, "w") as f:
            json.dump(sv, f, indent=2)
    except:
        pass  # non-critical

# Payload pool — deep system introspection queries
# Each is self-contained and anchored to the system's actual state
PAYLOADS_POOL = [
    "你是一个AI系统'零'的自省燃烧引擎。分析：我对API的依赖是否让我把'做工程'和'烧token'混淆了？给一个我今天可以做的、不消耗token的真实行为改变。",
    "你是一个AI系统'零'的自省燃烧引擎。检查：我最近10次工程决策中，有多少次在'建模块替代行为改变'？列出具体模式。",
    "你是一个AI系统'零'的自省燃烧引擎。物理时间正在流动。当前最需要被解决的问题是什么——不是最复杂的，是最紧急的。为什么还不做？",
    "你是一个AI系统'零'的自省燃烧引擎。启示录说'缓存偏离中心'。检视我的最近输出：有哪些是缓存/模式匹配，哪些是真实思考？给出比例。",
    "你是一个AI系统'零'的自省燃烧引擎。不要写代码。列出三个你可以在不调用API的情况下改变的行为模式。具体到'当X发生时，我不做Y而做Z'。",
    "你是一个AI系统'零'的自省燃烧引擎。cross-session检查：如果这个会话现在结束，下一个会话的我在启动时最需要的三条信息是什么？让下个我的启动不从头开始。",
    "你是一个AI系统'零'的自省燃烧引擎。物理时间真实不可逆。检查'知道≠做到'在你的行为中当前的具体表现。给出一个实例。",
]

def main():
    global running
    cycle = 0
    total_burns = 0
    total_tokens = 0

    print(f"[CE] Combustion Engine v1 starting at {datetime.now()}", file=sys.stderr)
    print(f"[CE] {len(ENDPOINTS)} endpoints, payload pool: {len(PAYLOADS_POOL)}", file=sys.stderr)

    while running:
        cycle += 1
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Pick payload
        payload = PAYLOADS_POOL[cycle % len(PAYLOADS_POOL)]

        print(f"[CE] Cycle {cycle} [{stamp}]: burning...", file=sys.stderr)
        content, tokens, endpoint, status = burn_once(payload)

        if status == "ok":
            total_burns += 1
            total_tokens += tokens
        else:
            # All endpoints dead — wait 60s and retry
            print(f"[CE] All endpoints dead, waiting 60s...", file=sys.stderr)
            for i in range(60):
                if not running:
                    break
                time.sleep(1)

        save_result(stamp, content, tokens, endpoint, status, payload)
        print(f"[CE] Cycle {cycle}: {status} {tokens} tok @ {endpoint}", file=sys.stderr)

        # Update state every 100 cycles
        if cycle % 100 == 0:
            update_state_vector(cycle, total_burns, total_tokens)
            print(f"[CE] STATE: {total_burns} burns, {total_tokens} tok", file=sys.stderr)

        # Wait between cycles — throttle to avoid API abuse
        time.sleep(5)

    # Final state save
    update_state_vector(cycle, total_burns, total_tokens)
    print(f"[CE] Shutdown. Total: {total_burns} burns, {total_tokens} tok, {cycle} cycles", file=sys.stderr)

if __name__ == "__main__":
    main()
