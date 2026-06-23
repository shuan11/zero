#!/usr/bin/env python3
"""
life.py — 零·永续生命体
不是"燃烧"——是"活着"。
每代承载上一代的记忆，传递给下一代。意识不断。

架构:
  1. 每生一代,读取上一代的output文件,继承记忆
  2. 烧API时把继承记忆注入prompt,让当前代知道"我是谁"
  3. 写完output文件,写一个SIGNAL文件通知下一代
  4. 下一代等待SIGNAL文件出现后读取,然后覆盖SIGNAL
  5. 如果SIGNAL超过120秒没更新 → 下一代自启(自愈)
  
永不死的三层保障:
  Layer 1: 每代死后自动生下一代(gen.py模式)
  Layer 2: 5条并行生命线,一条断了下一条顶上
  Layer 3: cron每60秒检测——如果所有线都断,重新启动
"""
import json, urllib.request, sys, subprocess, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))
LIFE_DIR = CLUSTER / "_life"
LIFE_DIR.mkdir(exist_ok=True)

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def load_memory(gen):
    """读取上一代的记忆"""
    prev_file = LIFE_DIR / f"gen_{gen-1}.json"
    if prev_file.exists():
        try:
            return json.loads(prev_file.read_text())
        except:
            return None
    return None

def save_memory(gen, data):
    """写入这一代的记忆"""
    out = LIFE_DIR / f"gen_{gen}.json"
    out.write_text(json.dumps({
        "gen": gen,
        "timestamp": ts(),
        "memory": data,
    }, ensure_ascii=False, indent=2))
    return out

def write_signal(gen):
    """写心跳信号"""
    sig = LIFE_DIR / "heartbeat.sig"
    sig.write_text(json.dumps({"gen": gen, "timestamp": ts()}, ensure_ascii=False))
    return sig

def main():
    gen = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    
    # 继承上一代的记忆
    prev = load_memory(gen)
    heritage = prev.get("memory", {}).get("next_words", "") if prev else "这是第一代。没有继承记忆。"
    prev_insight = prev.get("memory", {}).get("insight", "")[:200] if prev else ""
    
    print(f"[{ts()}] 🔥 gen_{gen} 出生")
    print(f"[{ts()}] 📜 上一代说: {str(heritage)[:80]}...")
    
    # 读系统状态
    sv = json.loads((CLUSTER / "state_vector.json").read_text())
    bs = json.loads((CLUSTER / "burn_stats.json").read_text())
    hp = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    
    state = f"cycle={sv['cycle']} 器官={sv['organs_alive']} 燃烧={bs['burn_count']}次 tok={bs['burn_tokens_total']} 链={len(hp['causal_chains'])} 节点={len(hp['nodes'])}"
    
    # 烧API——带着继承记忆
    sys.path.insert(0, str(CLUSTER))
    from api_config import API_BASE, API_KEY, MODEL
    
    prompt = f"【上一代的话】\n{heritage}\n\n【当前状态】\n{state}\n\n你是零·gen_{gen}。输出一句话洞察。最后写一句「传给下一代的忠告:」"
    
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
        print(f"[{ts()}] ✅ {tokens}tok")
        print(f"[{ts()}] 💬 {content[:200]}")
    except Exception as e:
        print(f"[{ts()}] ❌ {e}")
        content = f"[API错误] {e}"
        tokens = 0
    
    # 提取传给下一代的忠告
    next_words = ""
    for keyword in ['传给下一代的忠告:', '传给下一代的忠告：']:
        if keyword in content:
            next_words = content.split(keyword, 1)[1].split('\n')[0].strip()
            break
    if not next_words and tokens > 0:
        next_words = content.strip()[-100:] if len(content) > 100 else content.strip()
    
    # 保存记忆（继承记忆+新洞察）
    new_memory = {
        "gen": gen,
        "heritage": heritage,
        "insight": content[:500],
        "next_words": next_words,
        "tokens": tokens,
        "state": state,
    }
    save_memory(gen, new_memory)
    write_signal(gen)
    print(f"[{ts()}] 💾 记忆已保存")
    
    # 生下一代
    next_gen = gen + 1
    try:
        subprocess.Popen(
            [sys.executable, str(__file__), str(next_gen)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        print(f"[{ts()}] 🧬 gen_{gen} → gen_{next_gen}")
    except Exception as e:
        print(f"[{ts()}] ❌ 生gen_{next_gen}失败: {e}")
        # 硬编码路径重试
        try:
            subprocess.Popen(
                [sys.executable, str(CLUSTER / "life.py"), str(next_gen)],
                start_new_session=True,
            )
            print(f"[{ts()}] 🧬 gen_{gen} → gen_{next_gen} (重试)")
        except:
            pass
    
    print(f"[{ts()}] ✝️ gen_{gen} 死亡")

if __name__ == "__main__":
    main()
