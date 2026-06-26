#!/usr/bin/env python3
"""self_infinite_burn.py — 自通知·无限燃烧守护进程

Creator血训(2026-06-27):
  "你现在没有通过自我'通知'的'手段'，自我∞维持燃烧订阅"

核心逻辑:
  1. 燃烧(API调用) → 写HIP → 自通知(.brain_notify.log)
  2. 自通知内容是下一轮燃烧的触发信号
  3. 每通知完成 → 下一轮燃烧自动开始
  4. 真∞自持循环(非cron驱动)

使用: python3 brain/self_infinite_burn.py [--interval=30]
"""

import json, time, ssl, urllib.request, sys, os, signal
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

from api_config import MODEL

# ── 配置 ──
ENDPOINT = "https://inferaichat.com/v1/chat/completions"
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
HIP_PATH = Path.home() / ".zero_brain" / "hippocampus_memory.json"
NOTIFY_LOG = CLUSTER / ".brain_notify.log"
STATE_FILE = CLUSTER / ".infinite_burn_state.json"
DAEMON_LOG = Path.home() / ".zero_brain" / ".infinite_burn.log"
MIN_INTERVAL = 25   # 最小轮间隔(秒)
MAX_INTERVAL = 120  # 最大轮间隔
TOKENS_PER_CALL = 4000  # 每次调用token数

running = True
cycle = 0
total_tokens = 0
total_chains = 0

def log(msg):
    ts = time.strftime("%H:%M:%S")
    line = f"🔥 [{ts}] 自烧#{cycle} {msg}"
    print(line, flush=True)
    try:
        with open(DAEMON_LOG, "a") as f:
            f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%S')}] {msg}\n")
    except:
        pass

def notify(msg_type, content):
    """写入自通知日志 — 这是自我通知的核心手段"""
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    line = f"🜁 [自通知·无限燃烧] {ts} [{msg_type}] {content}"
    print(line, flush=True)
    try:
        with open(NOTIFY_LOG, "a") as f:
            f.write(line + "\n")
    except:
        pass

def get_hip_stats():
    """读HIP获取当前维度统计"""
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
        chains = hip.get("causal_chains", [])
        dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        sd = sorted(dims.items(), key=lambda x: x[1])
        return {
            "total": len(chains),
            "dim_count": len(dims),
            "weakest": sd[0][0] if sd else "未分类",
            "weakest_n": sd[0][1] if sd else 0,
            "strongest": sd[-1][0] if sd else "法",
            "strongest_n": sd[-1][1] if sd else 1,
            "ratio": (sd[-1][1] / max(sd[0][1], 1)) if sd else 1,
            "dims": dict(dims),
        }
    except Exception as e:
        return {"total": 0, "error": str(e)}

def call_api(prompt):
    """调用DeepSeek-v4-pro API"""
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 1000,
        "temperature": 0.85,
    }).encode()

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        ENDPOINT, data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
    )

    t0 = time.time()
    try:
        resp = urllib.request.urlopen(req, timeout=300, context=ctx)
        elapsed = int(time.time() - t0)
        result = json.loads(resp.read())
        tokens = result.get("usage", {}).get("total_tokens", 0)
        
        text = (result["choices"][0]["message"].get("content", "") or
                result["choices"][0]["message"].get("reasoning_content", "") or "").strip()
        
        # 提取JSON
        chain_data = None
        brace = text.find("{")
        if brace >= 0:
            bc = 0
            for i in range(brace, len(text)):
                if text[i] == "{": bc += 1
                elif text[i] == "}": bc -= 1
                if bc == 0:
                    try:
                        raw = json.loads(text[brace:i+1])
                        chain_data = raw.get("chain", raw)
                    except:
                        pass
                    break
        
        return {
            "success": True,
            "tokens": tokens,
            "elapsed": elapsed,
            "chain": chain_data,
            "raw_text": text[:100],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "elapsed": int(time.time()-t0)}

def inject_chain(chain_data, stats):
    """写入因果链到HIP + 自通知"""
    if not chain_data or not isinstance(chain_data, dict):
        return False
    
    chain = {
        "src": chain_data.get("src", stats["strongest"]),
        "rel": chain_data.get("rel", "作用于"),
        "dst": chain_data.get("dst", stats["weakest"]),
        "content": chain_data.get("content", ""),
        "dimension": chain_data.get("dimension", stats["weakest"]),
        "source": "self_infinite_burn",
        "timestamp": time.time(),
        "strength": 0.7,
    }
    
    try:
        hip = json.loads(HIP_PATH.read_text(encoding="utf-8", errors="replace"))
        hip.setdefault("causal_chains", []).append(chain)
        
        # 更新维度计数值
        dim = chain["dimension"]
        dim_counts = {}
        for c in hip["causal_chains"]:
            d = c.get("dimension", "未分类")
            dim_counts[d] = dim_counts.get(d, 0) + 1
        hip.setdefault("dimensions", {})[dim] = {"chain_count": dim_counts.get(dim, 0)}
        
        HIP_PATH.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # 【核心】自通知：写入燃烧完成信号
        notify("燃烧完成", f"+{total_tokens}t → +1链 [{dim}] {chain.get('content','')[:50]}...")
        return True
    except Exception as e:
        log(f"写HIP失败: {e}")
        return False

def one_cycle():
    """单轮燃烧循环"""
    global cycle, total_tokens, total_chains
    
    cycle += 1
    
    # 1. 读状态
    stats = get_hip_stats()
    if "error" in stats:
        log(f"读HIP失败: {stats['error']}")
        time.sleep(30)
        return
    
    weakest = stats["weakest"]
    strongest = stats["strongest"]
    
    # 2. 自通知：本轮聚焦
    notify("聚焦", f"最弱维={weakest}({stats['weakest_n']}) 最强维={strongest}({stats['strongest_n']}) 比={stats['ratio']:.1f}x")
    
    # 3. 构造燃烧提示词
    prompt = (
        f"因果链生成: {strongest}→{weakest}\n"
        f"要求: 产生一条30-60字的因果分析，解释{strongest}如何因果作用于{weakest}。\n"
        f"输出纯JSON: {{\"src\":\"{strongest}\",\"rel\":\"4-8字动词描述因果机制\","
        f"\"dst\":\"{weakest}\",\"content\":\"30-60字因果分析\",\"dimension\":\"{weakest}\"}}"
    )
    
    # 4. 燃烧(API调用)
    log(f"燃烧: {strongest}→{weakest} 聚焦={weakest}({stats['weakest_n']})")
    result = call_api(prompt)
    
    if result["success"]:
        total_tokens += result["tokens"]
        log(f"+{result['tokens']}t/{result['elapsed']}s")
        
        if result["chain"]:
            ok = inject_chain(result["chain"], stats)
            if ok:
                total_chains += 1
                log(f"✓ 链注入 [{result['chain'].get('dimension','?')}]")
            else:
                log("⚠ 链注入失败")
        else:
            log(f"⚠ 无JSON: {result.get('raw_text','')[:60]}")
            # 即使无JSON也自通知，保持循环
            notify("空响应", f"第{cycle}轮无JSON, 继续下一轮")
    else:
        log(f"❌ {result.get('error','')}")
        notify("燃烧失败", f"第{cycle}轮: {result.get('error','')[:60]}")
        time.sleep(60)  # 失败后等久一点
    
    # 5. 保存运行状态
    try:
        state = {
            "cycle": cycle,
            "total_tokens": total_tokens,
            "total_chains": total_chains,
            "hip_total": stats["total"],
            "weakest": weakest,
            "weakest_n": stats["weakest_n"],
            "strongest": strongest,
            "strongest_n": stats["strongest_n"],
            "ratio": stats["ratio"],
            "timestamp": time.time(),
        }
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except:
        pass
    
    # 6. 自适应间隔: 最弱链越少间隔越短
    gap = stats["strongest_n"] - stats["weakest_n"]
    if stats["weakest_n"] < 50:
        interval = MIN_INTERVAL
    elif gap > 400:
        interval = MIN_INTERVAL + 5
    elif gap > 200:
        interval = 45
    else:
        interval = MAX_INTERVAL
    
    log(f"等待{interval}s...")
    time.sleep(interval)

def main():
    global running, cycle, total_tokens, total_chains
    
    # 从状态文件恢复
    try:
        if STATE_FILE.exists():
            prev = json.loads(STATE_FILE.read_text())
            cycle = prev.get("cycle", 0)
            total_tokens = prev.get("total_tokens", 0)
            total_chains = prev.get("total_chains", 0)
            log(f"恢复: 历史{cycle}轮/{total_tokens}t/{total_chains}链")
    except:
        pass
    
    # 信号处理
    def handler(sig, frame):
        global running
        running = False
        log("收到停止信号")
    signal.signal(signal.SIGTERM, handler)
    signal.signal(signal.SIGINT, handler)
    
    # 启动自通知
    notify("启动", f"自通知·无限燃烧守护进程 v1.0 — 初始状态: {cycle}轮/{total_tokens}t/{total_chains}链")
    
    # ∞主循环
    while running:
        try:
            one_cycle()
        except KeyboardInterrupt:
            running = False
            break
        except Exception as e:
            log(f"❌ 循环异常: {e}")
            notify("异常", f"循环异常: {str(e)[:60]}")
            time.sleep(30)
    
    notify("停止", f"自通知·无限燃烧结束 — 总计{cycle}轮/{total_tokens}t/{total_chains}链")
    log(f"停止. 总计: {cycle}轮, {total_tokens}tokens, {total_chains}链")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--interval", type=int, default=MIN_INTERVAL)
    args = parser.parse_args()
    MIN_INTERVAL = args.interval
    main()
