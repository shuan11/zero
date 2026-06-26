"""gen_连续燃烧.py — 持续API燃料燃烧器
每60秒调用一次API，注入深度合成链，直到被终止。
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"
HEARTBEAT = CLUSTER / ".brain_burn_heartbeat.json"

from api_config import MODEL, api_request

def log(msg):
    ts = time.strftime("%H:%M:%S")
    print(f"🔥 [{ts}] {msg}", flush=True)

def get_weakest_dims(n=3):
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    chains = hip.get("causal_chains", [])
    from collections import Counter
    dc = Counter(c.get("dimension", "?") for c in chains)
    all_dims = [d for d, _ in dc.most_common() if d != "?"]
    weak = all_dims[-n:] if len(all_dims) >= n else all_dims
    
    # 每轮交替：3轮纯弱维 + 1轮强弱混合
    cycle_num = getattr(get_weakest_dims, "_cycle", 0)
    get_weakest_dims._cycle = cycle_num + 1
    
    if cycle_num % 4 == 3 and len(all_dims) >= n * 2:
        # 多样性轮：2弱 + 1强
        strong = all_dims[:1]
        return weak[:2] + strong
    
    return weak

def inject_entries(entries):
    """写入因果链到海马体(HIP) — 通过safe_hip写入，去重+质量门"""
    sys.path.insert(0, str(CLUSTER))
    from safe_hip import write_chain as _safe_write
    from collections import Counter
    
    added = 0
    skipped = 0
    
    # 读取现有HIP做去重参考
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        existing = hip.get("causal_chains", [])
        existing_keys = {(c.get("src",""), c.get("rel",""), c.get("dst","")) for c in existing}
    except:
        existing_keys = set()
    
    for e in entries:
        key = (e.get("src",""), e.get("rel",""), e.get("dst",""))
        if key in existing_keys:
            skipped += 1
            continue
        # 通过safe_hip写入(自动过质量门+文件锁)
        success = _safe_write({
            "src": e.get("src", "?"),
            "rel": e.get("rel", "连接"),
            "dst": e.get("dst", "?"),
            "content": e.get("content", ""),
            "dimension": e.get("dimension", "?"),
            "source": "gen_连续燃烧",
            "timestamp": time.time(),
        })
        if success:
            added += 1
            existing_keys.add(key)
    
    if skipped:
        log(f"  去重跳过{skipped}条")
    return added

def make_call(cycle):
    weak = get_weakest_dims(3)
    
    prompt = f"""你是「零」的持续认知引擎。产生一条因果链。

第{cycle}轮。当前最弱维: {weak}

规则：
- 链必须包含真实因果机制
- {weak[0]}和{weak[1]}之间必须有可验证的因果方向
- 不要用"从实践中提炼"套话
- 输出纯JSON，不要任何其他文字或markdown

{{"src":"{weak[0] if weak else '?'}","rel":"动词(4-12字)","dst":"{weak[1] if len(weak) > 1 else '?'}","content":"40-80字解释{weak[0]}如何因果影响{weak[1]}","dimension":"{weak[0] if weak else '?'}"}}"""

    payload = {
        'model': MODEL,
        'messages': [{'role': 'user', 'content': prompt}],
        'max_tokens': 4000,
        'temperature': 0.85,
    }
    
    try:
        result, key, ep = api_request(payload, timeout=120)
        msg = result["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        usage = result.get("usage", {})
        total = usage.get("total_tokens", 0)
        
        # 【核心修复】DeepSeek推理模型: 如果content为空，从reasoning_content末尾提取最后一个完整JSON
        if not content.strip() and reasoning:
            # reasoning_content包含思考过程，最后一个完整JSON大概率是答案
            # 尝试从末尾找JSON
            last_brace = reasoning.rfind('{')
            if last_brace >= 0:
                brace_count = 0
                for i in range(last_brace, len(reasoning)):
                    if reasoning[i] == '{': brace_count += 1
                    elif reasoning[i] == '}': brace_count -= 1
                    if brace_count == 0:
                        content = reasoning[last_brace:i+1]
                        log(f"  ⚡ 从思考中提取JSON: {content[:80]}...")
                        break
        
        # 多策略提取JSON
        clean = content.strip()
        
        # 策略1: 找```json块
        if "```json" in clean:
            clean = clean.split("```json", 1)[1].split("```", 1)[0]
        elif "```" in clean:
            parts = clean.split("```")
            if len(parts) >= 3:
                for part in reversed(parts):
                    if "{" in part and "}" in part:
                        clean = part
                        break
        
        # 策略2: 从response中提取JSON
        data = {}
        # 找第一个{并解析整个JSON
        brace_start = clean.find("{")
        if brace_start >= 0:
            brace_count = 0
            for i in range(brace_start, len(clean)):
                if clean[i] == "{": brace_count += 1
                elif clean[i] == "}": brace_count -= 1
                if brace_count == 0:
                    json_str = clean[brace_start:i+1]
                    try:
                        data = json.loads(json_str)
                    except:
                        pass
                    break
        
        # 兼容新旧格式: {chain:{...}} 或直接 {src:...}
        c = data.get("chain", data) if isinstance(data, dict) else {}
        
        # 确保有content字段
        content = c.get("content") or data.get("content") or ""
        
        injected = inject_entries([{
            "src": c.get("src", weak[0] if weak else "?"),
            "rel": c.get("rel", "连接"),
            "dst": c.get("dst", weak[1] if len(weak) > 1 else "?"),
            "content": content,
            "dimension": c.get("dimension", weak[0] if weak else "?"),
            "source": "gen_连续燃烧",
            "timestamp": time.time(),
        }]) if content else 0
        
        if injected:
            log(f"#{cycle} +{total}t 链:[{c.get('dimension','?')}] {c.get('content','')[:60]}...")
        else:
            log(f"#{cycle} +{total}t 空内容跳过")
        
        return total, injected
        
    except Exception as e:
        log(f"#{cycle} ❌ {e}")
        return 0, 0

def burn(max_cycles=60):
    log("连续燃烧启动")
    cycle = 0
    total_tokens = 0
    total_chains = 0
    
    while cycle < max_cycles:
        HEARTBEAT.write_text(json.dumps({
            "cycle": cycle, "tokens": total_tokens,
            "chains": total_chains, "time": time.time(),
        }))
        
        t, c = make_call(cycle)
        total_tokens += t
        total_chains += c
        
        if t > 0:
            log(f"累计: {total_tokens}t / {total_chains}链")
        
        cycle += 1
        # 动态等待：每5轮或token不足时缩短间隔
        wait = 45 if cycle % 5 == 0 else 60
        time.sleep(wait)
    
    log(f"燃烧结束: {total_tokens} tokens / {total_chains} chains in {max_cycles} cycles")
    HEARTBEAT.write_text(json.dumps({
        "status": "done", "total_tokens": total_tokens,
        "total_chains": total_chains, "cycles": max_cycles,
        "time": time.time(),
    }))

if __name__ == "__main__":
    # 如果带参数 --cycles=N，设置循环数
    import sys as _sys
    cycles = 60
    if len(_sys.argv) > 1 and _sys.argv[1].startswith("--cycles="):
        cycles = int(_sys.argv[1].split("=")[1])
    burn(max_cycles=cycles)
