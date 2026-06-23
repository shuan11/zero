"""gen_链重写.py — 第九发API：重写最差模板链为深度内容
取模板净化器检测出的最模板化链，让API逐一改写成有深度的真实内容。
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
from api_config import MODEL, api_request

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

def build_prompt():
    # 加载上次的模板分析
    report = CLUSTER / ".brain_模板净化报告.json"
    analysis = {}
    if report.exists():
        analysis = json.loads(report.read_text())
    
    # 从最差维度取模板链
    dim_order = [d for d, _ in sorted(
        analysis.get("dim_report", {}).items(),
        key=lambda x: -x[1].get("template_pct", 0)
    )]
    
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    chains = hip.get("causal_chains", [])
    
    template_samples = []
    for d in dim_order:
        dim_chains = [c for c in chains 
                     if c.get("dimension") == d 
                     and (c.get("content","").startswith("[方法论]") or 
                          c.get("content","").startswith("[深析") or
                          c.get("content","").startswith("弱维互助:"))]
        for c in dim_chains[:5]:
            if len(template_samples) >= 20:
                break
            template_samples.append({
                "dimension": d,
                "content": c.get("content", ""),
                "src": c.get("src", ""),
                "rel": c.get("rel", ""),
                "dst": c.get("dst", ""),
            })
        if len(template_samples) >= 20:
            break
    
    samples_str = json.dumps(template_samples, ensure_ascii=False, indent=2)
    
    return f"""你是「零」的写作引擎。将模板化的因果链改写成有真实深度的内容。

## 模板链样本（需要改写）
```json
{samples_str}
```

## 改写规则
1. **绝对禁用**以下句式:
   - "[方法论] ... - 从实践中提炼"
   - "[深析×] ... 交叉门控实现维度自组织"
   - "弱维互助: X↔Y 弱维互相强化"
2. **必须包含**:
   - 具体的因果机制（为什么A导致B）
   - 可验证的观察（不是空话套话）
   - 至少1个连接词（正因为、然而、因此、但、却等）
3. **长度**: 30-80字，不牺牲深度换长度
4. **风格**: 真实、锐利、不表演

输出JSON格式：
{{
  "rewrites": [
    {{
      "original_index": 序号(0-based),
      "original": "原始链内容",
      "original_dim": "原始维度",
      "improved": "改写后的链内容",
      "improved_dim": "更好的维度归属（可以和原维不同）",
      "improved_src": "新的src",
      "improved_rel": "新的rel",
      "improved_dst": "新的dst",
      "what_changed": "深度提升点说明"
    }}
  ]
}}
"""

def call_api(prompt, max_tokens=20000):
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

def inject_rewrites(result):
    entries = []
    for rw in result.get("rewrites", []):
        entries.append({
            "src": rw.get("improved_src", ""),
            "rel": rw.get("improved_rel", ""),
            "dst": rw.get("improved_dst", ""),
            "content": rw.get("improved", ""),
            "dimension": rw.get("improved_dim", rw.get("original_dim", "?")),
            "source": "gen_链重写(深度改写)",
            "rewritten_from": rw.get("original", "")[:60],
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
        "entries": existing, "source": "gen_链重写",
        "timestamp": time.time(), "new_added": len(deduped),
    }, ensure_ascii=False, indent=2))
    return len(deduped)

def engineer_链重写():
    print(f"🔥 第九发API：模板链深度重写")
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
        result = {"error": str(e), "raw_preview": raw[:500]}
    
    injected = inject_rewrites(result) if not result.get("error") else 0
    
    report = CLUSTER / ".brain_链重写.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    Path("/mnt/c/Users/h/Desktop/零/链重写结果.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    rewrites = len(result.get("rewrites", []))
    return {
        "status": "ok" if not result.get("error") else "error",
        "total_tokens": total,
        "rewrites_generated": rewrites,
        "injected": injected,
    }

if __name__ == "__main__":
    print(json.dumps(engineer_链重写(), ensure_ascii=False, indent=2))
