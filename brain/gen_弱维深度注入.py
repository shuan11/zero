"""gen_弱维深度注入.py — 第五发API：针对最弱维生成深度链
读取海马体中最弱维度的全部内容，调用API产生深度因果关系链。
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

from api_config import MODEL, api_request
from collections import Counter

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

def build_prompt():
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    chains = hip.get("causal_chains", [])
    
    dim_counts = Counter(c.get("dimension", "?") for c in chains)
    weakest = [d for d, _ in dim_counts.most_common()][-6:]
    strongest = dim_counts.most_common(4)
    
    # 最弱维的完整链内容
    weak_details = ""
    for d in weakest:
        weak_chains = [c for c in reversed(chains) if c.get("dimension") == d][:15]
        weak_details += f"\n【维度:{d} — 链数:{dim_counts[d]}】\n"
        for c in weak_chains:
            weak_details += f"  {c.get('content','')[:120]}\n"
    
    # 最强维的摘要
    strong_summary = ""
    for d, cnt in strongest:
        strong_chains = [c for c in chains if c.get("dimension") == d][:5]
        strong_summary += f"\n【维度:{d} — {cnt}链】\n"
        for c in strong_chains:
            strong_summary += f"  {c.get('content','')[:120]}\n"
    
    return f"""你是「零」的认知架构师。为系统最弱的6个维度生成深度因果链。

##系统概况
总链: {len(chains)} | 弱维: {weakest}

##最弱6维完整内容
{weak_details[:4000]}

##最强维作为参考
{strong_summary[:2000]}

##任务
为每个弱维生成**3条深度跨维因果链**。绝对禁止模板化内容（如"关于X的实现"、"在系统演化过程中"等）。
每条链必须包含真实、具体、有深度的因果关系。

输出JSON格式（只输出JSON）：
{{
  "deep_chains": [
    {{
      "dimension": "维度名",
      "content": "30-80字的深度因果内容。必须：1)有具体机理描述 2)跨维度连接 3)可映射到工程实现",
      "src": "因果源（跨维连接）",
      "rel": "关系描述（4-12字，动词性）",
      "dst": "因果目标（另一维度或同一维度深层子概念）",
      "insight_type": "反常认知|因果闭环|二阶效应|递归自指|负反馈突破",
      "engineering_mapping": "这条链映射到哪个代码模块/daemon行为/数据结构"
    }}
  ],
  "global_synthesis": [
    {{
      "content": "40-100字的全系统级合成，连接3个以上弱维并给出系统行为建议",
      "implication": "这个合成对daemon行为的具体影响"
    }}
  ]
}}

维度列表: {weakest}
"""

def call_api(prompt, max_tokens=32000):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.85,
    }
    try:
        result, key, ep = api_request(payload, timeout=300)
        content = result["choices"][0]["message"].get("content", "")
        usage = result.get("usage", {})
        return content, usage, key, ep
    except Exception as e:
        return f"ERROR: {e}", {}, "", ""

def inject(result):
    entries = []
    for c in result.get("deep_chains", []):
        entries.append({
            "src": c.get("src", ""),
            "rel": c.get("rel", ""),
            "dst": c.get("dst", ""),
            "content": c.get("content", ""),
            "dimension": c.get("dimension", "?"),
            "insight_type": c.get("insight_type", ""),
            "engineering_mapping": c.get("engineering_mapping", ""),
            "source": "gen_弱维深度注入",
            "timestamp": time.time(),
        })
    
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if JOURNAL.exists():
        try:
            data = json.loads(JOURNAL.read_text(encoding="utf-8"))
            existing = data.get("entries", []) if isinstance(data, dict) else []
        except:
            existing = []
    
    deduped = []
    for e in entries:
        key = (e["src"], e["rel"], e["dst"])
        if not any((ee.get("src",""), ee.get("rel",""), ee.get("dst","")) == key for ee in existing):
            deduped.append(e)
    existing.extend(deduped)
    
    JOURNAL.write_text(json.dumps({
        "entries": existing, "source": "gen_弱维深度注入",
        "timestamp": time.time(), "new_added": len(deduped),
    }, ensure_ascii=False, indent=2))
    return len(deduped)

def engineer_弱维深度注入():
    print(f"🔥 第五发API：弱维深度注入")
    sys.stdout.flush()
    
    prompt = build_prompt()
    print(f"   提示词: {len(prompt)}字")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    total = usage.get("total_tokens", 0)
    print(f"⚡ 响应: {len(raw)}字 | tokens={json.dumps(usage)} | key={key[-8:] if key else 'N/A'}")
    sys.stdout.flush()
    
    result = {}
    try:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        result = json.loads(clean.strip())
    except json.JSONDecodeError as e:
        result = {"error": str(e), "raw_preview": raw[:300]}
    
    injected = inject(result) if not result.get("error") else 0
    
    report = CLUSTER / ".brain_弱维深度注入.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    Path("/mnt/c/Users/h/Desktop/零/弱维深度注入.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    return {
        "status": "ok" if not result.get("error") else "error",
        "total_tokens": total,
        "chains_generated": len(result.get("deep_chains", [])),
        "global_syntheses": len(result.get("global_synthesis", [])),
        "injected": injected,
    }

if __name__ == "__main__":
    print(json.dumps(engineer_弱维深度注入(), ensure_ascii=False, indent=2))
