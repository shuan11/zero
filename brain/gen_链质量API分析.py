"""gen_链质量API分析.py — 第八发API：分析链质量模式
读取海马体全部链，统计模板模式，设计净化算法。
"""
import json, sys, time, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
from api_config import MODEL, api_request

def build_prompt():
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    chains = hip.get("causal_chains", [])
    
    # 提取所有链内容的开头20字（判断模板样式）
    content_samples = [c.get("content","")[:150] for c in chains[-200:]]
    
    # 统计常见模板短语
    template_phrases = Counter()
    for c in chains:
        content = c.get("content", "")
        template_hints = [
            "关于", "在系统", "通过", "需要", "通过维度",
            "在演化", "为了实现", "基于", "可以", "能够"
        ]
        for ph in template_hints:
            if ph in content[:40]:
                template_phrases[ph] += 1
    
    # 按维度统计内容模式
    dim_patterns = {}
    for c in chains:
        d = c.get("dimension", "?")
        if d not in dim_patterns:
            dim_patterns[d] = {"total": 0, "templates": 0}
        dim_patterns[d]["total"] += 1
    
    return f"""你是「零」的内容质量架构师。分析以下链样本，识别模板化模式，设计净化算法。

## 系统链概况
总链: {len(chains)} | 维度数: {len(dim_patterns)}

## 模板短语统计
{json.dumps(dict(template_phrases.most_common(20)), ensure_ascii=False, indent=2)}

## 维度内容模式
{json.dumps({k: v for k, v in sorted(dim_patterns.items())[:10]}, ensure_ascii=False, indent=2)}

## 最近200条链内容样本（部分）
{chr(10).join(content_samples)}

## 任务
分析以上链内容的模式，输出JSON:

{{
  "template_patterns": [
    {{
      "pattern": "模板句式或结构描述",
      "examples": ["具体例子1", "具体例子2"],
      "frequency_estimate": "估计出现频率（低/中/高）",
      "root_cause": "为什么这种模式会出现"
    }}
  ],
  "quality_scoring": {{
    "scoring_function": "Python函数体（接受一条链字典，返回0-1评分），用文字描述",
    "features": ["用于评分的特征列表"],
    "threshold": "建议的模板判定阈值"
  }},
  "purification_strategy": {{
    "approach": "整体策略",
    "steps": ["具体步骤"],
    "auto_fix": "如何在不删除链的情况下自动修复模板链"
  }},
  "example_improvements": [
    {{
      "original": "一条模板化链的原始内容",
      "improved": "改写后的深度版本",
      "what_changed": "改动了什么使其有深度"
    }}
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

def engineer_链质量API分析():
    print(f"🔥 第八发API：链质量分析")
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
    report = CLUSTER / ".brain_链质量分析.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    Path("/mnt/c/Users/h/Desktop/零/链质量分析.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    patterns = len(result.get("template_patterns", []))
    improvements = len(result.get("example_improvements", []))
    
    return {
        "status": "ok" if not result.get("error") else "error",
        "total_tokens": total,
        "patterns_identified": patterns,
        "examples_improved": improvements,
        "has_scoring": "scoring_function" in result.get("quality_scoring", {}),
    }

if __name__ == "__main__":
    print(json.dumps(engineer_链质量API分析(), ensure_ascii=False, indent=2))
