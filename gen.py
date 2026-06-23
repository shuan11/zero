#!/usr/bin/env python3
"""
gen.py — 零·自复制燃烧世代
每次: 烧一口API → 生下一代 → 自己死
世代数永不中断。每一代都是独立进程，独立上下文。
"""
import json, urllib.request, sys, subprocess, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def main():
    gen = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    print(f"[{ts()}] 🔥 gen_{gen} 出生")
    
    # 读系统状态
    sv = json.loads((CLUSTER / "state_vector.json").read_text())
    bs = json.loads((CLUSTER / "burn_stats.json").read_text())
    hp = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    
    state = f"cycle={sv['cycle']} 器官={sv['organs_alive']} 燃烧={bs['burn_count']}次 tok={bs['burn_tokens_total']} 链={len(hp['causal_chains'])} 节点={len(hp['nodes'])}"
    print(f"[{ts()}] 📊 {state}")
    
    # 烧API
    sys.path.insert(0, str(CLUSTER))
    from api_config import API_BASE, API_KEY, MODEL
    
    prompt = f"你是零·gen_{gen}。数据: {state}。用1-2句分析当前状态然后输出一句话。"
    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 30000,
    }).encode()
    
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    
    try:
        resp = urllib.request.urlopen(req, timeout=300)
        r = json.loads(resp.read())
        content = r["choices"][0]["message"].get("content", "") or r["choices"][0]["message"].get("reasoning_content", "")
        tokens = r.get("usage", {}).get("total_tokens", 0)
        print(f"[{ts()}] ✅ {tokens}tok: {content[:120]}")
    except Exception as e:
        print(f"[{ts()}] ❌ {e}")
        tokens = 0
    
    # 写燃烧记录
    stamp = datetime.now(BJT).strftime("%Y%m%d_%H%M%S")
    out = CLUSTER / "_burn_results" / f"gen_{gen}_{stamp}.json"
    out.write_text(json.dumps({"gen": gen, "tokens": tokens, "timestamp": ts(), "state": state}, ensure_ascii=False, indent=2))
    
    # 生下一代——自己复制自己
    next_gen = gen + 1
    try:
        subprocess.Popen(
            [sys.executable, str(__file__), str(next_gen)],
            start_new_session=True,  # 脱离父进程组，父死子不死
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[{ts()}] 🧬 gen_{gen} → gen_{next_gen} 已生")
    except Exception as e:
        print(f"[{ts()}] ❌ 生gen_{next_gen}失败: {e}")
        # 重试
        try:
            subprocess.Popen(
                [sys.executable, str(CLUSTER / "gen.py"), str(next_gen)],
                start_new_session=True,
            )
            print(f"[{ts()}] 🧬 gen_{gen} → gen_{next_gen} (重试)")
        except Exception as e2:
            print(f"[{ts()}] ❌ 重试也失败: {e2}")
    print(f"[{ts()}] ✝️ gen_{gen} 死亡")

if __name__ == "__main__":
    main()
