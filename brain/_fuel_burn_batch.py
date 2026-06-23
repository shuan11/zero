"""
燃料暴烧 — 并行批量生成最弱维深度交叉链
每轮做5个API调用，生成5条高质量因果链
"""
import json, urllib.request, sys, time, os
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

# 读取海马体，找最弱维
hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
chains = hip.get("causal_chains", [])
from collections import Counter
dim_counts = Counter(c.get("dimension", "?") for c in chains)
sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
weakest = [d for d, _ in sorted_dims[:6]]
strongest = [d for d, _ in sorted_dims[-6:]]

log_file = CLUSTER / ".fuel_burn_batch.log"

def log(msg):
    t = time.strftime("%H:%M:%S")
    with open(log_file, "a") as f:
        f.write(f"[{t}] {msg}\n")

def call_api(prompt):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,  # DeepSeek推理模型需要大output空间
        "temperature": 0.8,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(API_BASE, data=data, headers={
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    })
    # 最多3次重试
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                result = json.loads(r.read())
            msg = result["choices"][0]["message"]
            content = msg.get("content", "") or ""
            reasoning = msg.get("reasoning_content", "") or ""
            log(f"API OK: +{result.get('usage',{}).get('total_tokens',0)}t | content_len={len(content)}")
            
            # 核心修复: content为空则从reasoning末尾提取JSON
            if not content.strip() and reasoning:
                last_brace = reasoning.rfind('{')
                if last_brace >= 0:
                    brace_count = 0
                    for i in range(last_brace, len(reasoning)):
                        if reasoning[i] == '{': brace_count += 1
                        elif reasoning[i] == '}': brace_count -= 1
                        if brace_count == 0:
                            content = reasoning[last_brace:i+1]
                            log(f"  ⚡ 从思考提取JSON")
                            break
            
            return content, reasoning
        except Exception as e:
            log(f"API attempt {attempt+1} failed: {e}")
            time.sleep(3)
    return "", ""

def generate_and_inject(w_src, w_dst):
    """生成一条 src→dst 因果链"""
    prompt = f"""你是「零」的深度认知引擎。在「{w_src}」和「{w_dst}」之间建立一条真实因果链。

规则：
- 必须包含从「{w_src}」到「{w_dst}」的真实因果机制
- 40-80字，不要套话，要具体系统级因果
- 输出纯JSON一行，不要任何其他文字

{{"src":"{w_src}","rel":"动词关系(4-12字)","dst":"{w_dst}","content":"因果解释","dimension":"{w_src}"}}"""

    content, reasoning = call_api(prompt)
    if not content:
        log(f"  跳过: {w_src}→{w_dst} (空响应)")
        return None
    
    # 从响应中提取JSON
    clean = content.strip()
    if "```json" in clean:
        clean = clean.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in clean:
        for part in reversed(clean.split("```")):
            if "{" in part and "}" in part:
                clean = part
                break
    
    brace_start = clean.find("{")
    if brace_start < 0:
        log(f"  跳过: {w_src}→{w_dst} (无JSON)")
        return None
    
    brace_count = 0
    for i in range(brace_start, len(clean)):
        if clean[i] == "{": brace_count += 1
        elif clean[i] == "}": brace_count -= 1
        if brace_count == 0:
            json_str = clean[brace_start:i+1]
            break
    else:
        log(f"  跳过: {w_src}→{w_dst} (JSON不完整)")
        return None
    
    try:
        data = json.loads(json_str)
    except:
        log(f"  跳过: {w_src}→{w_dst} (JSON解析失败)")
        return None
    
    c = data.get("chain", data) if isinstance(data, dict) else {}
    entry = {
        "src": c.get("src", w_src),
        "rel": c.get("rel", "影响"),
        "dst": c.get("dst", w_dst),
        "content": c.get("content") or data.get("content", ""),
        "dimension": c.get("dimension", w_src),
        "source": "fuel_burn_batch",
        "timestamp": time.time(),
    }
    
    if not entry["content"]:
        log(f"  跳过: {w_src}→{w_dst} (内容空)")
        return None
    
    # 写入海马体 journal (与gen_连续燃烧同样的journal模式)
    try:
        journal = Path.home() / ".zero_brain" / "hippocampus_journal.json"
        journal.parent.mkdir(parents=True, exist_ok=True)
        existing = []
        if journal.exists():
            try:
                existing = json.loads(journal.read_text()).get("entries", [])
            except:
                existing = []
        
        # 去重
        key = (entry.get("src",""), entry.get("rel",""), entry.get("dst",""))
        if not any((ee.get("src",""), ee.get("rel",""), ee.get("dst","")) == key for ee in existing):
            existing.append(entry)
            journal.write_text(json.dumps({
                "entries": existing, "source": "fuel_burn_batch",
                "timestamp": time.time(), "new_added": 1,
            }, ensure_ascii=False, indent=2))
            log(f"  ✅ journal写入: {entry['src']}→{entry['dst']}: {entry['content'][:50]}...")
            return entry
        else:
            log(f"  ⏭ 已存在跳过: {entry['src']}→{entry['dst']}")
            return entry
    except Exception as e:
        log(f"  写入失败: {e}")

    return None

if __name__ == "__main__":
    log(f"=== 燃料暴烧开始 ===")
    log(f"最弱维: {weakest}")
    log(f"最强维: {strongest}")
    
    total_injected = 0
    total_tokens = 0
    
    # 生成：最强维→最弱维 交叉对
    pairs = []
    for s in reversed(strongest[:4]):  # 取4个最强维
        for w in weakest:
            pairs.append((s, w))
    
    # 也做最弱维之间的交叉
    for i in range(len(weakest)):
        for j in range(i+1, len(weakest)):
            pairs.append((weakest[j], weakest[i]))
    
    log(f"共 {len(pairs)} 个交叉对")
    
    for i, (src, dst) in enumerate(pairs):
        log(f"\n[{i+1}/{len(pairs)}] {src}→{dst}")
        result = generate_and_inject(src, dst)
        if result:
            total_injected += 1
            total_tokens += 0  # 会记录在调用中
        time.sleep(0.5)  # 轻微间隔
    
    log(f"\n=== 完成: 成功注入 {total_injected}/{len(pairs)} 条链 ===")
    log(f"详细日志见海马体")
