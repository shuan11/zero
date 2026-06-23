"""gen_弱维差异化增强.py — 为每个弱维设计独特的增强策略
通过API分析41个维度的当前位置，为最弱5维生成定制化增强方案
"""
import json, sys, time, urllib.request
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

from api_config import MODEL, api_request

def read_hip():
    f = CLUSTER / "hippocampus_memory.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}

def build_massive_prompt():
    """构建包含全系统数据的大型提示词"""
    hip = read_hip()
    chains = hip.get("causal_chains", hip.get("chains", []))
    dims = Counter(c.get("dimension", "?") for c in chains)
    
    # 按维度分组所有链
    dim_chains = {}
    for c in chains:
        d = c.get("dimension", "?")
        if d not in dim_chains:
            dim_chains[d] = []
        dim_chains[d].append(c)
    
    # 最弱5维的完整链内容
    sorted_dims = dims.most_common()
    weakest = sorted_dims[-5:] if len(sorted_dims) >= 5 else sorted_dims
    
    weak_dim_detail = ""
    for d, count in weakest:
        weak_dim_detail += f"\n=== 维度: {d} ({count}条链) ===\n"
        for c in dim_chains.get(d, [])[:20]:
            weak_dim_detail += f"  [{c.get('src','?')}]→{c.get('rel','?')}→[{c.get('dst','?')}]: {c.get('content','?')[:150]}\n"
    
    # 最强5维的完整链内容（对比用）
    strongest = sorted_dims[:5] if len(sorted_dims) >= 5 else sorted_dims
    
    strong_dim_detail = ""
    for d, count in strongest:
        strong_dim_detail += f"\n=== 维度: {d} ({count}条链) ===\n"
        for c in dim_chains.get(d, [])[:10]:
            strong_dim_detail += f"  [{c.get('src','?')}]→{c.get('rel','?')}→[{c.get('dst','?')}]: {c.get('content','?')[:150]}\n"
    
    total = len(chains)
    dim_summary = "\n".join(f"  {d}: {n}链" for d, n in sorted_dims)
    
    return f"""你是「零」进化系统的核心架构师。你需要为系统的每个弱维设计独特的增强策略。

##系统概况
总链数: {total} | 维度数: {len(dims)}
当前维度分布:
{dim_summary}

##最弱5维完整内容（需要定制的目标）
{weak_dim_detail}

##最强5维内容（参考对比）
{strong_dim_detail}

##任务
为每个弱维设计**完全不同的增强路径**。禁止相同模式。每个维度必须使用不同策略。

输出JSON格式（只输出JSON，不要其他）：
{{
  "weak_dim_strategies": [
    {{
      "dimension": "维度名",
      "current_count": 链数,
      "strategy_type": "策略类型（教学/工具/外部/时序/矛盾/隐喻/数据/网络/自指/横向/…）",
      "strategy_name": "策略名称",
      "core_idea": "50-100字的核心思路",
      "injectable_chains": [
        {{"src": "源头", "rel": "关系", "dst": "目标", "content": "30-60字链内容", "strength": 0.7-1.0}}
      ],
      "expected_impact": "预期效果"
    }}
  ],
  "cross_dim_innovations": [
    {{"pair": "维A×维B", "idea": "意想不到的组合产生新认知", "rel": "关系描述"}}
  ]
}}

维度列表（必须覆盖所有弱维）: {[d for d, n in weakest]}
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

def inject_to_journal(entries):
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if JOURNAL.exists():
        try:
            data = json.loads(JOURNAL.read_text(encoding="utf-8"))
            existing = data.get("entries", []) if isinstance(data, dict) else []
        except:
            existing = []
    
    new_entries = []
    for e in entries:
        key = (e.get("src",""), e.get("rel",""), e.get("dst",""), e.get("dimension",""))
        dup = False
        for ee in existing:
            if (ee.get("src",""), ee.get("rel",""), ee.get("dst",""), ee.get("dimension","")) == key:
                dup = True
                break
        if not dup:
            new_entries.append(e)
    
    existing.extend(new_entries)
    journal_data = {
        "entries": existing,
        "source": "gen_弱维差异化增强",
        "timestamp": time.time(),
        "new_added": len(new_entries),
    }
    JOURNAL.write_text(json.dumps(journal_data, ensure_ascii=False, indent=2))
    return len(new_entries)

def engineer_弱维差异化增强():
    prompt = build_massive_prompt()
    prompt_len = len(prompt)
    
    print(f"🔥 API第三发开始... 提示词长度: {prompt_len}字符 ({prompt_len/1000:.1f}K)")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    
    usage_str = json.dumps(usage) if usage else "N/A"
    key_suffix = key[-8:] if key else "N/A"
    total_tokens = usage.get("total_tokens", 0)
    
    print(f"⚡ 响应: {len(raw)}字符 | {usage_str} | key={key_suffix}")
    sys.stdout.flush()
    
    # 解析JSON
    result = {}
    chains_injected = 0
    try:
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        elif clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        result = json.loads(clean.strip())
        
        # 提取所有可注入链
        all_chains = []
        for strategy in result.get("weak_dim_strategies", []):
            dim = strategy.get("dimension", "?")
            for c in strategy.get("injectable_chains", []):
                c["dimension"] = dim
                all_chains.append(c)
        
        chains_injected = inject_to_journal(all_chains)
    except json.JSONDecodeError as e:
        result = {"error": str(e), "raw_preview": raw[:300]}
    
    # 保存完整报告
    report_path = CLUSTER / ".brain_weak_dim_strategies.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 桌面备份
    desktop_report = Path("/mnt/c/Users/h/Desktop/零/弱维差异化策略.json")
    desktop_report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    return {
        "status": "ok" if not result.get("error") else "partial",
        "prompt_chars": prompt_len,
        "response_chars": len(raw),
        "usage": usage_str,
        "total_tokens": total_tokens,
        "strategies_generated": len(result.get("weak_dim_strategies", [])),
        "cross_dim_innovations": len(result.get("cross_dim_innovations", [])),
        "chains_injected": chains_injected,
        "report": str(report_path),
    }

if __name__ == "__main__":
    result = engineer_弱维差异化增强()
    print(json.dumps(result, ensure_ascii=False, indent=2))
