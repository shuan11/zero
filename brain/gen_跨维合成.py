"""gen_跨维合成.py — 独立跨维合成器
读取当前最弱/最强维，API深度合成跨维链，写入journal。
独立运行，不依赖daemon模式。
"""
import json, sys, time, re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

def get_dim_rank(hip_path):
    """返回 (sorted_dims, weakest5, strongest3)"""
    hip = json.loads(open(hip_path).read())
    chains = hip.get("causal_chains", [])
    from collections import Counter
    dc = Counter(c.get("dimension", "?") for c in chains)
    sorted_dims = sorted(dc.items(), key=lambda x: x[1])
    weakest = [d for d, _ in sorted_dims[:5]]
    strongest = [d for d, _ in sorted_dims[-3:]]
    return sorted_dims, weakest, strongest

def load_existing():
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    if not JOURNAL.exists():
        return []
    data = json.loads(JOURNAL.read_text())
    if isinstance(data, list):
        return data
    return data.get("entries", [])

def save_entries(entries, new_count):
    JOURNAL.write_text(json.dumps({
        "entries": entries, "new_added": new_count,
        "source": "gen_跨维合成", "timestamp": time.time(),
    }, ensure_ascii=False, indent=2))

def main():
    hip_path = str(CLUSTER / "hippocampus_memory.json")
    sorted_dims, weakest, strongest = get_dim_rank(hip_path)
    
    log(f"最弱: {weakest} 最强: {strongest}")
    
    # 构造prompt — 要求纯JSON行，不要markdown
    dim_info = ", ".join(f"{d}:{c}" for d, c in sorted_dims[:15])
    prompt = (
        f"维度链数: [{dim_info}]。\n"
        f"最弱5维={weakest}。最强3维={strongest}。\n"
        f"产3条cross-dim洞察(最弱↔最强交叉)。仅JSON:[{{\"src\":\"维A\",\"rel\":\"V+N\",\"dst\":\"维B\",\"content\":\"因果描述30-80字\",\"dimension\":\"归属维\"}}]\n"
        f"严禁模板句式。必须真实因果机制。"
    )
    
    from api_config import MODEL, api_request
    
    result, key, ep = api_request({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
        "temperature": 0.78,
    }, timeout=120)
    
    msg = result["choices"][0]["message"]
    raw = msg.get("content", "") or msg.get("reasoning_content", "") or ""
    usage = result.get("usage", {})
    tot = usage.get("total_tokens", 0)
    
    # 多策略JSON提取
    chain_list = []
    
    # 策略1: 找```json
    m = re.search(r'```json\s*([\s\S]*?)```', raw)
    if m:
        clean = m.group(1).strip()
    else:
        # 策略2: 找``` 
        m = re.search(r'```\s*([\s\S]*?)```', raw)
        clean = m.group(1).strip() if m else raw.strip()
    
    # 策略3: 找最外层[]
    if not clean.startswith("["):
        arr_m = re.search(r'\[[\s\S]*\]', clean)
        if arr_m:
            clean = arr_m.group()
    
    try:
        parsed = json.loads(clean)
        chain_list = parsed if isinstance(parsed, list) else parsed.get("chains", [parsed])
    except:
        # 策略4: 逐行解析
        for line in raw.split("\n"):
            line = line.strip()
            try:
                item = json.loads(line)
                chain_list.append(item)
            except:
                continue
    
    # 去重写journal
    existing = load_existing()
    new_count = 0
    for c in chain_list:
        if not isinstance(c, dict) or not c.get("src"):
            continue
        key = (c.get("src",""), c.get("rel",""), c.get("dst",""))
        if any((ee.get("src",""), ee.get("rel",""), ee.get("dst","")) == key for ee in existing):
            continue
        entry = {
            "src": c.get("src",""), "rel": c.get("rel",""),
            "dst": c.get("dst",""), "content": c.get("content",""),
            "dimension": c.get("dimension", c.get("src","")),
            "source": "gen_跨维合成", "timestamp": time.time(),
        }
        existing.append(entry)
        new_count += 1
    
    save_entries(existing, new_count)
    log(f"✅ {tot}tokens, 新{new_count}链")
    for c in chain_list[:new_count]:
        log(f"  [{c.get('dimension',c.get('src','?'))}] {c.get('content','')[:60]}")

if __name__ == "__main__":
    main()
