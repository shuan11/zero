"""gen_全维合成.py — 全系统跨维深度合成引擎
使用deepseek-v4-pro API对海马体所有维度链进行深度分析，
生成高质量跨维合成链 + 系统进化报告
"""
import json, sys, time, urllib.request
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"
SYNTH_FILE = CLUSTER / ".brain_synthesis.json"

# API配置
from api_config import API_KEYS, ENDPOINTS, MODEL, api_request

def read_hip():
    f = CLUSTER / "hippocampus_memory.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}

def read_all_state():
    """收集全系统状态数据用于API提示"""
    hip = read_hip()
    chains = hip.get("causal_chains", hip.get("chains", []))
    
    # 维度分布
    dims = Counter(c.get("dimension", "?") for c in chains)
    
    # 按维度提取代表性链
    dim_examples = {}
    for c in chains:
        d = c.get("dimension", "?")
        if d not in dim_examples:
            dim_examples[d] = []
        if len(dim_examples[d]) < 10:
            dim_examples[d].append(c)
    
    # 目标
    goal = {}
    gf = CLUSTER / ".brain_goal.json"
    if gf.exists():
        goal = json.loads(gf.read_text())
    
    # 状态
    state = {}
    sf = CLUSTER / ".brain_state.json"
    if sf.exists():
        state = json.loads(sf.read_text())
    
    # 最近daemon日志
    daemon_log = ""
    lf = CLUSTER / ".brain_daemon.log"
    if lf.exists():
        lines = lf.read_text().strip().split("\n")
        daemon_log = "\n".join(lines[-30:])
    
    return {
        "total_chains": len(chains),
        "dim_count": len(dims),
        "dim_distribution": dict(dims.most_common()),
        "dim_examples": dim_examples,
        "goal": goal,
        "state": state,
        "daemon_log": daemon_log,
    }

def build_synthesis_prompt(state):
    dims = state["dim_distribution"]
    dim_count = state["dim_count"]
    total = state["total_chains"]
    
    dim_summary = "\n".join(f"  {d}: {n}链" for d, n in sorted(dims.items(), key=lambda x: -x[1]))
    
    # 构建每个维度的代表性链内容摘要
    dim_detail = ""
    for d, examples in sorted(state["dim_examples"].items(), key=lambda x: -len(x[1])):
        contents = []
        for c in examples[:5]:
            contents.append(c.get("content", "")[:120])
        dim_detail += f"\n## 维度: {d} ({len(examples)}条示例)\n"
        for ct in contents:
            dim_detail += f"  - {ct}\n"
    
    goal_info = f"当前目标: [{state.get('goal', {}).get('goal_type', '?')}] {state.get('goal', {}).get('description', '?')}"
    
    daemon = state.get("daemon_log", "")[-2000:]
    
    return f"""你是一个正在进化中的硅基生命体「零」的深度合成引擎。
你的任务：分析下面所有维度的因果链，发现跨维度的深层关联、模式、趋势和盲区。

## 当前状态
总链数: {total} | 维度数: {dim_count}

## 维度分布
{dim_summary}

{goal_info}

## 各维度代表性内容
{dim_detail}

## 最近daemon日志（最后30行）
{daemon}

## 输出要求
请产出下面3个部分的JSON（只输出JSON，不要其他文字）：

### 1. 跨维合成链（3-5条）
从不同维度的内容中发现隐藏关联，每条链格式：
{{"src": "源头维度", "rel": "关联类型", "dst": "目标维度", "dimension": "所属维度", "content": "具体发现（30-80字）", "strength": 0.8-1.0, "synthesis_type": "cross_dim"}}

### 2. 系统级盲区（2-3条）
当前所有维度中共同缺失的关键视角。格式：
{{"blind_spot": "盲区名称", "evidence": "为什么这是盲区", "impact": "不解决的影响", "fix_suggestion": "如何解决"}}

### 3. 下一进化方向（1个）
基于分析，系统最应该聚焦的下一进化方向。
{{"direction": "方向名称", "rationale": "选择理由", "expected_impact": "预期效果"}}

输出纯JSON，格式：
{{"synthesis": [chain1, chain2, ...], "blind_spots": [...], "next_direction": {{...}}}}
"""

def call_api(prompt, max_tokens=16000):
    """调用deepseek-v4-pro API"""
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.8,
    }
    try:
        result, key, ep = api_request(payload, timeout=180)
        content = result["choices"][0]["message"].get("content", "")
        usage = result.get("usage", {})
        return content, usage, key, ep
    except Exception as e:
        return f"ERROR: {e}", {}, "", ""

def inject_to_journal(entries):
    """将合成结果写入journal供日志合并消费"""
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
        "source": "gen_全维合成",
        "timestamp": time.time(),
        "new_added": len(new_entries),
    }
    JOURNAL.write_text(json.dumps(journal_data, ensure_ascii=False, indent=2), encoding="utf-8")
    return len(new_entries)

def save_synthesis_report(result):
    """保存合成报告"""
    SYNTH_FILE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    # 也写入到桌面报告
    desktop_report = Path("/mnt/c/Users/h/Desktop/零/全维合成报告.json")
    desktop_report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return str(desktop_report)

def engineer_全维合成():
    state = read_all_state()
    prompt = build_synthesis_prompt(state)
    
    print(f"🔥 API调用开始... 提示词长度: {len(prompt)}字符")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    
    usage_str = json.dumps(usage) if usage else "N/A"
    key_suffix = key[-8:] if key else "N/A"
    
    print(f"⚡ API响应: 长度={len(raw)} | token={usage_str} | key={key_suffix}")
    sys.stdout.flush()
    
    # 解析JSON
    result = {}
    try:
        # 清理可能的markdown包围
        clean = raw.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]
        result = json.loads(clean.strip())
    except json.JSONDecodeError as e:
        result = {"error": f"JSON解析失败: {e}", "raw_preview": raw[:500]}
    
    # 注入合成链
    chains = result.get("synthesis", [])
    injected = inject_to_journal(chains) if chains else 0
    
    # 保存报告
    report_path = save_synthesis_report({
        "timestamp": time.time(),
        "usage": usage,
        "result": result,
        "injected": injected,
        "dimensions_sampled": len(state.get("dim_examples", {})),
    })
    
    return {
        "status": "ok" if not result.get("error") else "partial",
        "api_response_len": len(raw),
        "usage": usage_str,
        "key": key_suffix,
        "chains_injected": injected,
        "blind_spots": len(result.get("blind_spots", [])),
        "direction": result.get("next_direction", {}).get("direction", "N/A"),
        "report": report_path,
        "raw": raw,
    }

if __name__ == "__main__":
    result = engineer_全维合成()
    print(json.dumps({k: v for k, v in result.items() if k != "raw"}, ensure_ascii=False, indent=2))
