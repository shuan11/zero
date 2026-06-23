#!/usr/bin/env python3
"""深循环: 分析系统不进化根因 → 注入修复"""
import json, urllib.request, os, sys, time, re, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
BJT = timezone(timedelta(hours=8))
def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

print(f"[{ts()}] 🜁 深循环启动")

# ═══ 1. 读取系统真实状态 ═══
sys_state = {}
r = subprocess.run(["git", "diff", "--stat", "HEAD~5"], capture_output=True, text=True, timeout=10)
py_count = r.stdout.count(".py")
non_py = r.stdout.count(".json") + r.stdout.count(".md")
sys_state["py_changes_5"] = py_count
sys_state["json_changes_5"] = non_py

try:
    hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
    sys_state["chains"] = len(hip.get("causal_chains", []))
    sys_state["nodes"] = len(hip.get("nodes", {}))
except:
    sys_state["chains"] = 0

try:
    rf = json.loads((CLUSTER / "dimension_focus.json").read_text())
    sys_state["weakest"] = rf.get("weakest", "?")
    sys_state["health"] = rf.get("weakest_health", 0)
except:
    pass

# check self-improvement output
try:
    from 自我改进 import scan_for_improvements
    cands = scan_for_improvements()
    sys_state["improvement_candidates"] = len(cands)
    has_code = sum(1 for c in cands if c.get("new_content"))
    sys_state["candidates_with_code"] = has_code
except Exception as e:
    sys_state["improvement_error"] = str(e)[:60]

print(f"[{ts()}] 状态: py变更={py_count}, 链={sys_state.get('chains')}, 候选={sys_state.get('improvement_candidates',0)}, 含代码={sys_state.get('candidates_with_code',0)}")

# ═══ 2. 读API密钥 ═══
api_conf = (CLUSTER / "api_config.py").read_text()
key_match = re.search(r"sk-[a-zA-Z0-9]{20,}", api_conf)
api_key = key_match.group(0) if key_match else ""
ep_match = re.search(r"https?://[^\"'\s)}]+", api_conf)
endpoint = ep_match.group(0) if ep_match else "https://inferaichat.com/v1/chat/completions"

# ═══ 3. API深度分析 ═══
payload = {
    "model": "deepseek-v4-pro",
    "messages": [
        {"role": "system", "content": "你是零·真元集群的核心工程师。系统已自主运行14天但陷入循环——daemon在呼吸但代码不进化。找出根因并给出精确补丁。"},
        {"role": "user", "content": f"""系统现状:
- 最近5次提交: {py_count}行.py变更, {non_py}行状态文件变更
- 海马体: {sys_state.get("chains",0)}链, {sys_state.get("nodes",0)}节点
- 最弱维度: {sys_state.get("weakest","?")} 健康度{sys_state.get("health",0)}
- 自我改进引擎: 扫描出{sys_state.get("improvement_candidates",0)}个候选, 其中{sys_state.get("candidates_with_code",0)}个含实际代码
- breath_v2.py 2697行, 30s间隔daemon循环
- 限时不限量API订阅(deepseek-v4-pro)

根因已定位: evolution_proposal模板的候选缺少new_content和old_content字段→apply_improvement找不到代码可注入→全挂。

问题: 应该修改哪一行代码来修复? 最简短有效的方案是什么?

输出格式(严格JSON):
{{"root_cause":"一句话根因","fix_file":"文件名","fix_type":"add|modify|delete","fix_detail":"具体改什么","code_snippet":"关键代码段"}}"""}
    ],
    "max_tokens": 3000,
    "temperature": 0.3
}

data = json.dumps(payload).encode()
req = urllib.request.Request(
    endpoint, data=data,
    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
)

try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    content = result["choices"][0]["message"].get("content", "")
    reasoning = result["choices"][0]["message"].get("reasoning_content", "")
    if not content and reasoning:
        content = reasoning
    tokens_used = result.get("usage", {}).get("total_tokens", 0)
except Exception as e:
    content = f"API Error: {e}"
    tokens_used = 0

print(f"[{ts()}] ✅ API返回: tokens={tokens_used}")

# ═══ 4. 记录发现 ═══
finding = {
    "time": ts(),
    "type": "deep_cycle_gap_analysis",
    "sys_state": sys_state,
    "api_result": content[:1000],
    "tokens": tokens_used
}
findings_file = CLUSTER / "evolution_output" / "real_findings.jsonl"
findings_file.parent.mkdir(exist_ok=True)
with open(findings_file, "a") as f:
    f.write(json.dumps(finding, ensure_ascii=False) + "\n")

print(f"[{ts()}] ✅ 发现已记录")
print("===== API输出 =====")
print(content[:600])
