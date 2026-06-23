"""gen_系统深度审计.py — 第四发API：全系统深度审计
读取完整系统状态（海马体+daemon日志+gen模块索引），
调用API进行深度分析，识别最高优先级进化方向。
"""
import json, sys, time, urllib.request
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

from api_config import MODEL, api_request

def build_audit_prompt():
    """构建包含全系统数据的超大型提示词"""
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding="utf-8"))
    chains = hip.get("causal_chains", [])
    
    # 维度分布
    from collections import Counter
    dim_counts = Counter(c.get("dimension", "?") for c in chains)
    sorted_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
    
    # 链质量抽样（每个维度抽最新2条）
    dim_snapshot = {}
    for c in reversed(chains):
        d = c.get("dimension", "?")
        if d not in dim_snapshot:
            dim_snapshot[d] = []
        if len(dim_snapshot[d]) < 2:
            dim_snapshot[d].append(c)
    
    dim_detail = ""
    for d, cnt in sorted_dims:
        samples = dim_snapshot.get(d, [])
        for s in samples:
            dim_detail += f"  [/{d}/]↦{s.get('content','')[:120]}\n"
    
    # gen模块索引
    gen_files = sorted(CLUSTER.glob("brain/gen_*.py"))
    gen_index = ""
    for f in gen_files:
        name = f.stem
        # 提取简短描述（第一行文档或第一行注释）
        content = f.read_text(encoding="utf-8")
        first_line = content.strip().split('\n')[0] if content else ""
        gen_index += f"  {name}: {first_line.strip('\"\\' )[:80]}\n"
    
    # daemon日志统计
    dlog = CLUSTER / ".brain_daemon.log"
    log_errors = []
    if dlog.exists():
        lines = dlog.read_text(encoding="utf-8").split('\n')
        for l in lines[-200:]:
            if "异常" in l or "错误" in l or "ERROR" in l:
                log_errors.append(l.strip())
    
    total_tokens_in = len(chains) * 30  # 估计
    
    return f"""你是「零」的元架构师。对以下完整快照进行深度诊断并输出演进路线图。

## 系统快照（{time.strftime('%Y-%m-%d %H:%M')}）
- 总链数: {len(chains)} | 总维度: {len(dim_counts)}
- Gen模块数: {len(gen_files)} | 已注入journal链
- 最近daemon错误: {len(log_errors)}个

## 维度分布（{len(sorted_dims)}个维度）
{dim_detail[:3000]}

## Gen模块索引（截取）
{gen_index[:2000]}

## Daemon日志错误（最近）
{chr(10).join(log_errors[-15:])[:2000]}

## 分析任务
请对以上数据深度分析，输出JSON格式：

{{
  "system_diagnosis": {{
    "health_overall": "良好|一般|危险",
    "primary_bottleneck": "当前系统最大的单一瓶颈是什么（精准定位到代码模块或函数）",
    "chain_quality_assessment": "链的质量评估（模板化/真正有价值/噪音比例）",
    "dimension_balance": "维度均衡度评估"
  }},
  "evolution_roadmap": [
    {{
      "priority": 1,
      "title": "最高优先级动作",
      "rationale": "为什么这个是最重要的",
      "approach": "具体怎么实现",
      "expected_impact": "预期效果",
      "tokens_estimate": "预计需要多少API token"
    }}
  ],
  "blind_spots": [
    {{
      "spot": "盲点描述",
      "severity": "严重|中等|轻微",
      "how_to_fix": "如何在10行代码内修复"
    }}
  ],
  "cross_dimension_synthesis": [
    {{
      "from_dim": "源维度",
      "to_dim": "目标维度",
      "synthesis": "深度合成内容",
      "rel": "关系类型"
    }}
  ],
  "next_gen_module_recommendation": {{
    "name": "推荐创建的下一个gen模块",
    "purpose": "用途",
    "api_tokens_needed": "估计消耗"
  }}
}}

约束：
1. 诊断必须精准——基于真实数据，不泛泛而谈
2. 合成链必须有真实内容
3. 优先级必须有数据支撑
4. 每条合成链不超过100字
5. 推荐gen模块必须可直接实现
"""

def call_api(prompt, max_tokens=32000):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        result, key, ep = api_request(payload, timeout=300)
        content = result["choices"][0]["message"].get("content", "")
        usage = result.get("usage", {})
        return content, usage, key, ep
    except Exception as e:
        return f"ERROR: {e}", {}, "", ""

def inject_syntheses(result, source="系统深度审计"):
    """从API输出中提取合成链注入journal"""
    entries = []
    for s in result.get("cross_dimension_synthesis", []):
        entries.append({
            "src": s.get("from_dim", ""),
            "rel": s.get("rel", ""),
            "dst": s.get("to_dim", ""),
            "content": s.get("synthesis", ""),
            "dimension": s.get("from_dim", "?"),
            "source": source,
            "timestamp": time.time(),
        })
        entries.append({
            "src": s.get("to_dim", ""),
            "rel": s.get("rel", ""),
            "dst": s.get("from_dim", ""),
            "content": s.get("synthesis", ""),
            "dimension": s.get("to_dim", "?"),
            "source": source,
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
        "entries": existing, "source": source,
        "timestamp": time.time(), "new_added": len(deduped),
    }, ensure_ascii=False, indent=2))
    return len(deduped)

def engineer_系统深度审计():
    print(f"🔥 第四发API：系统深度审计")
    sys.stdout.flush()
    
    prompt = build_audit_prompt()
    prompt_len = len(prompt)
    print(f"   提示词: {prompt_len}字 ({prompt_len/1000:.1f}K)")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    total_tokens = usage.get("total_tokens", 0)
    
    print(f"⚡ 响应: {len(raw)}字 | tokens={json.dumps(usage)} | key={key[-8:] if key else 'N/A'}")
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
        chains_injected = inject_syntheses(result)
    except json.JSONDecodeError as e:
        result = {"error": str(e), "raw_preview": raw[:500]}
    
    # 保存完整报告
    report_path = CLUSTER / ".brain_系统深度审计.json"
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    desktop_path = Path("/mnt/c/Users/h/Desktop/零/系统深度审计.json")
    desktop_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    return {
        "status": "ok" if not result.get("error") else "partial",
        "prompt_chars": prompt_len,
        "response_chars": len(raw),
        "usage_summary": usage,
        "total_tokens": total_tokens,
        "syntheses_injected": chains_injected,
        "blind_spots_found": len(result.get("blind_spots", [])),
        "roadmap_items": len(result.get("evolution_roadmap", [])),
        "report": str(report_path),
    }

if __name__ == "__main__":
    result = engineer_系统深度审计()
    print(json.dumps(result, ensure_ascii=False, indent=2))
