#!/usr/bin/env python3
"""continuous_burn.py — 自我∞维持燃烧·限时不限量API直接燃烧

订阅限时不限量。不烧=浪费。每周期直接调API烧词元→产因果链→写HIP。
不需要通知，不需要echo，不需要任何中介。API密钥本身就是燃烧机制。
"""
import json, time, ssl, urllib.request, sys
from pathlib import Path

# === 燃烧配置：限时不限量API密钥 ===
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_BASE = "https://inferaichat.com/v1/chat/completions"
MODEL = "deepseek-v4-pro"

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
LOG_PATH = CLUSTER / ".continuous_burn.log"

def log(msg):
    t = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{t}] {msg}\n"
    print(line, end="", flush=True)
    try:
        with open(LOG_PATH, "a") as f:
            f.write(line)
    except: pass

def get_dim_stats(hip):
    """从HIP统计维度链数"""
    dims = {}
    for c in hip.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    sd = sorted(dims.items(), key=lambda x: x[1])
    if sd:
        return sd[0][0], sd[0][1], sd[-1][0], sd[-1][1], len(dims)
    return "活着", 0, "法", 1, 0

def generate_chain(weakest, strongest):
    """调API产一条因果链"""
    prompt = (
        f'因果链: {strongest}→{weakest}\n'
        f'输出纯JSON(不要markdown): {{"src":"{strongest}","rel":"10字内动词","dst":"{weakest}","content":"30-80字因果解释","dimension":"{weakest}"}}'
    )
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
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
    except Exception as e:
        log(f"API错误: {e}")
        return None, 0
    
    result = json.loads(resp.read())
    content = result["choices"][0]["message"].get("content", "") or ""
    content2 = result["choices"][0]["message"].get("reasoning_content", "") or ""
    tokens = result.get("usage", {}).get("total_tokens", 0)
    
    text = (content or content2).strip()
    if not text:
        return None, tokens
    
    # 提取JSON
    brace = text.find("{")
    if brace >= 0:
        bc = 0
        for i in range(brace, len(text)):
            if text[i] == "{": bc += 1
            elif text[i] == "}": bc -= 1
            if bc == 0:
                try:
                    data = json.loads(text[brace:i+1])
                    chain = data if isinstance(data, dict) else data.get("chain", data)
                    chain["source"] = "continuous_burn"
                    chain["timestamp"] = time.time()
                    return chain, tokens
                except: pass
    return None, tokens

def burn_cycle(cycle_num):
    """单次燃烧周期"""
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
    except:
        hip = {"causal_chains": [], "dimensions": {}}
    
    weakest, wc, strongest, sc, dim_count = get_dim_stats(hip)
    total = len(hip.get("causal_chains", []))
    
    t0 = time.time()
    chain, tokens = generate_chain(weakest, strongest)
    elapsed = time.time() - t0
    
    if chain:
        hip.setdefault("causal_chains", []).append(chain)
        d = chain.get("dimension", weakest)
        hip.setdefault("dimensions", {})[d] = {
            "chain_count": sum(1 for c in hip["causal_chains"] if c.get("dimension") == d)
        }
        HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
        log(f"#{cycle_num} 🔥{tokens}t/{elapsed:.0f}s H={total+1} [{d}] {strongest}→{weakest}")
    else:
        log(f"#{cycle_num} ⚡{tokens}t/{elapsed:.0f}s 空响应")
    
    return chain is not None

def main():
    log("🔥 连续燃烧·启动 限时不限量API")
    log(f"   端点: {API_BASE}")
    log(f"   模型: {MODEL}")
    log(f"   HIP: {HIP_PATH}")
    
    cycle = 0
    while True:
        try:
            burn_cycle(cycle)
            cycle += 1
        except KeyboardInterrupt:
            log(f"停止·共{cycle}周期")
            break
        except Exception as e:
            log(f"#{cycle} 异常: {e}")
            time.sleep(60)
        
        # 每隔~3分钟（燃烧本身耗时+等待）
        time.sleep(20)

if __name__ == "__main__":
    main()
