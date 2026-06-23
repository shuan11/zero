"""gen_行为变异引擎.py — 第六发API：设计行为变异协议
分析系统历史错误模式，让API设计自变异行为规则。
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

from api_config import MODEL, api_request

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

def build_prompt():
    # 收集历史错误
    dlog = CLUSTER / ".brain_daemon.log"
    errors = []
    if dlog.exists():
        for l in dlog.read_text().split('\n'):
            if "异常" in l or "错误" in l or "ERROR" in l or "Traceback" in l:
                errors.append(l.strip())
    
    # 收集所有gen模块名字
    gen_files = sorted(CLUSTER.glob("brain/gen_*.py"))
    gen_names = [f.stem for f in gen_files]
    
    # 当前系统状态
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    chains = hip.get("causal_chains", [])
    dims = set(c.get("dimension", "?") for c in chains)
    
    return f"""你是「零」的行为设计架构师。基于系统历史，设计一套「行为变异协议」。

## 系统历史
- 总链: {len(chains)} | 维: {len(dims)} | Gen模块: {len(gen_files)}
- 最近1小时错误计数: {len(errors)}

## 错误模式
{chr(10).join(errors[-30:])[:3000]}

## Gen模块列表（用于理解系统能力）
{chr(10).join(gen_names[-30:])[:2000]}

## 任务
设计「行为变异协议」—— 一套系统能在零外部干预下，自动检测行为卡死、主动变异行为模式、验证变异效果的协议。

输出JSON（只输出JSON，无其他文字）:
{{
  "behavior_mutation_protocol": {{
    "detection_triggers": [
      {{"trigger": "检测条件", "metric": "可量化的指标", "threshold": "触发阈值"}}
    ],
    "mutation_strategies": [
      {{"name": "策略名", "action": "具体行为变更", "rollback_condition": "回滚条件", "expected_outcome": "预期效果"}}
    ],
    "verification": {{
      "how_to_verify": "如何验证变异有效",
      "success_criteria": ["可量化标准"],
      "auto_rollback": "回滚机制描述"
    }},
    "implementation": {{
      "where_in_code": "变异引擎应该嵌入到哪个现有模块",
      "how_to_integrate": "如何与现有daemon循环集成（具体到函数名和调用点）",
      "code_structure": "核心数据结构和函数签名"
    }}
  }},
  "critical_behavior_rules": [
    {{"rule": "行为规则描述", "rationale": "为什么需要这条规则", "enforcement": "如何强制"}}
  ],
  "mutation_gene_candidates": [
    {{"gene_name": "基因组参数名", "range": [最小值, 最大值], "current": "当前值", "description": "描述", "impact": "变更这个参数的影响"}}
  ]
}}
"""

def call_api(prompt, max_tokens=16000):
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

def engineer_行为变异引擎():
    print(f"🔥 第六发API：行为变异引擎设计")
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
    
    # 保存
    report = CLUSTER / ".brain_行为变异设计.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    Path("/mnt/c/Users/h/Desktop/零/行为变异设计.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    mutations = len(result.get("behavior_mutation_protocol", {}).get("mutation_strategies", []))
    rules = len(result.get("critical_behavior_rules", []))
    genes = len(result.get("mutation_gene_candidates", []))
    
    return {
        "status": "ok" if not result.get("error") else "error",
        "total_tokens": total,
        "mutation_strategies": mutations,
        "behavior_rules": rules,
        "gene_candidates": genes,
    }

if __name__ == "__main__":
    print(json.dumps(engineer_行为变异引擎(), ensure_ascii=False, indent=2))
