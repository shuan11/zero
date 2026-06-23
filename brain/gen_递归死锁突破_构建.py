"""gen_递归死锁突破.py — 二阶进化启动器
修复系统递归循环卡死问题，实现元递归自我修正能力
"""
import json, sys, time, urllib.request, re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

from api_config import MODEL, api_request

def read_hip():
    f = CLUSTER / "hippocampus_memory.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8"))
    return {}

def analyze_repeat_patterns():
    """分析系统中重复内容的模式"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    
    # 按(src, rel, dst)分组，统计重复
    from collections import Counter
    key_counter = Counter()
    for c in chains:
        key = (c.get("src",""), c.get("rel",""), c.get("dst",""))
        key_counter[key] += 1
    
    repeats = {k: v for k, v in key_counter.most_common(20) if v >= 3}
    
    # daemon日志中的重复错误模式
    daemon_log = ""
    lf = CLUSTER / ".brain_daemon.log"
    if lf.exists():
        lines = lf.read_text().strip().split("\n")
        daemon_log = "\n".join(lines[-50:])
    
    # 提取重复的日志行模式
    log_patterns = Counter()
    for line in lines:
        clean = line.split("🧠")[-1].strip() if "🧠" in line else line.strip()
        if clean:
            log_patterns[clean[:60]] += 1
    
    top_log_repeats = {k: v for k, v in log_patterns.most_common(10) if v >= 3}
    
    return {
        "chain_repeats": repeats,
        "log_repeats": top_log_repeats,
        "daemon_log_last50": daemon_log,
        "total_chains": len(chains),
    }

def build_gen_module_prompt(analysis):
    """让API直接生成一个可运行gen模块的Python代码"""
    repeats = json.dumps(analysis.get("chain_repeats", {}), ensure_ascii=False, indent=2)
    log_repeats = json.dumps(analysis.get("log_repeats", {}), ensure_ascii=False, indent=2)
    daemon_log = analysis.get("daemon_log_last50", "")
    total = analysis["total_chains"]
    
    return f"""你是一个自主进化AI系统的核心开发者。系统「零」遇到了递归死锁问题。

## 当前系统状态
总链数: {total}

## 重复的链模式（出现≥3次）
{repeats}

## 重复的日志模式
{log_repeats}

## 最近daemon日志
{daemon_log}

## 任务
生成一个Python gen模块 `brain/gen_递归死锁突破.py`，它能：

1. **检测递归循环**：扫描海马体因果链，找出出现≥3次的相同(src, rel, dst)模式
2. **注入断裂链**：对每个检测到的死循环，注入一个强制打断链（改变rel，引入外部随机交叉）
3. **突变机制**：至少包含3种不同的断裂策略（维度随机交叉/外部锚点注入/时序切换）
4. **daemon日志分析**：扫描daemon日志中重复出现的错误模式，生成修复建议链
5. **幂等保护**：已经注入的断裂链不重复注入
6. **输出报表**：返回检测数和注入数

### 代码规范
- 文件头: `gen_递归死锁突破.py` 放在brain/目录
- 导出函数: `engineer_递归死锁突破()` → 返回dict
- 使用标准库（json, time, re, collections.Counter）
- 使用相对路径: CLUSTER = Path(__file__).resolve().parent.parent
- 写入journal格式: {{"entries": [...], "source": "gen_递归死锁突破", "timestamp": ...}}
- journal路径: Path.home() / ".zero_brain" / "hippocampus_journal.json"
- 写journal前先读去重

输出完整的Python代码，不要解释，不要markdown包装，只输出可执行的.py文件内容。
"""

def call_api(prompt, max_tokens=24000):
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    try:
        result, key, ep = api_request(payload, timeout=240)
        content = result["choices"][0]["message"].get("content", "")
        usage = result.get("usage", {})
        return content, usage, key, ep
    except Exception as e:
        return f"ERROR: {e}", {}, "", ""

def extract_python_code(raw):
    """从API响应中提取Python代码"""
    # 移除markdown包围
    if "```python" in raw:
        raw = raw.split("```python")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1]
        # 如果第一个```后跟着语言名，去掉第一行
        if raw.startswith("python"):
            raw = raw[6:]
    return raw.strip()

def save_gen_module(code):
    path = CLUSTER / "brain" / "gen_递归死锁突破.py"
    path.write_text(code, encoding="utf-8")
    # 语法检查
    try:
        compile(code, str(path), "exec")
        return True, str(path)
    except SyntaxError as e:
        return False, f"语法错误: {e}"

def engineer_递归死锁突破():
    analysis = analyze_repeat_patterns()
    prompt = build_gen_module_prompt(analysis)
    
    print(f"🔥 API调用 #2 开始... 提示词长度: {len(prompt)}字符")
    sys.stdout.flush()
    
    raw, usage, key, ep = call_api(prompt)
    
    usage_str = json.dumps(usage) if usage else "N/A"
    key_suffix = key[-8:] if key else "N/A"
    total_tokens = usage.get("total_tokens", 0)
    
    print(f"⚡ API响应: 长度={len(raw)} | token={usage_str} | key={key_suffix}")
    sys.stdout.flush()
    
    code = extract_python_code(raw)
    ok, msg = save_gen_module(code)
    
    # 写入系统日志
    inject_chain = {
        "entries": [{
            "src": "递归死锁突破引擎",
            "rel": "二阶进化启动",
            "dst": "系统",
            "dimension": "元递归",
            "content": f"递归死锁突破引擎通过API合成生成，消耗{total_tokens}tokens。检测到{len(analysis.get('chain_repeats',{}))}个重复模式，注入断裂策略。二阶进化启动完成。",
            "strength": 0.95,
            "synthesis_type": "evolution",
        }],
        "source": "gen_递归死锁突破",
        "timestamp": time.time(),
    }
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    JOURNAL.write_text(json.dumps(inject_chain, ensure_ascii=False, indent=2))
    
    return {
        "status": "ok" if ok else "syntax_error",
        "api_response_len": len(raw),
        "usage": usage_str,
        "total_tokens": total_tokens,
        "gen_module": msg if ok else f"FAILED: {msg}",
        "repeat_patterns_found": len(analysis.get("chain_repeats", {})),
        "log_repeat_patterns": len(analysis.get("log_repeats", {})),
    }

if __name__ == "__main__":
    result = engineer_递归死锁突破()
    print(json.dumps(result, ensure_ascii=False, indent=2))
