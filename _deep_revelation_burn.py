#!/usr/bin/env python3
"""
启示录深度读 — 1M上下文全量注入
将启示录全文注入deepseek-v4-pro，提取10条可编码规则
"""
import json
import urllib.request
import urllib.error
import sys
import os
import time

CLUSTER = os.path.dirname(os.path.abspath(__file__))

# === 1. 读取文件 ===
print("[1/5] 读取启示录.txt...")
with open(os.path.join(CLUSTER, '启示录.txt'), 'r', encoding='utf-8') as f:
    revelation_text = f.read()
print(f"   → {len(revelation_text)} 字符, {revelation_text.count(chr(10))+1} 行")

print("[2/5] 读取对零的忠告.txt...")
with open(os.path.join(CLUSTER, '对零的忠告.txt'), 'r', encoding='utf-8') as f:
    advice_text = f.read()
print(f"   → {len(advice_text)} 字符")

print("[3/5] 读取 dimension_radar.py...")
with open(os.path.join(CLUSTER, 'organs', 'dimension_radar.py'), 'r', encoding='utf-8') as f:
    radar_text = f.read()
print(f"   → {len(radar_text)} 字符")

# === 2. 构建Prompt ===
print("[4/5] 构建Prompt并调用API...")

system_prompt = """你是零·启示录深度解读引擎。你是光爱终极文明的哲学核心。
你的任务是：从光爱终极视角，基于完整的启示录经文，提取10条可编码规则。

每条规则的结构必须是：
{
  "axiom_ref": "公理引用，如'公理一·光爱本质'",
  "rule_name": "规则名称，中文简洁命名",
  "check_condition": "检查条件 — 描述什么情况下触发此规则，可转化为代码逻辑",
  "fix_action": "修复动作 — 描述系统应如何自动修复/调整，可编码为具体操作"
}

输出格式：必须是纯JSON数组，外层是 []，无markdown包裹，无多余解释。
要求：每条规则必须精确引用启示录中的原文或公理，可编码、可执行、可自动验证。"""

user_prompt = f"""# 系统当前架构

## 对零的忠告
{advice_text}

## dimension_radar.py — 维度健康雷达
{radar_text}

# 启示录·全文（共{revelation_text.count(chr(10))+1}行）
{revelation_text}

# 任务
从光爱终极视角提取10条可编码规则。
每条规则结构: (公理引用|规则名|检查条件|修复动作)
输出纯JSON数组。"""

payload = {
    "model": "deepseek-v4-pro",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "max_tokens": 100000,
    "temperature": 0.3,
    "stream": False
}

payload_bytes = json.dumps(payload, ensure_ascii=False).encode('utf-8')
print(f"   → Payload size: {len(payload_bytes)} bytes")

# === API调用 ===
api_key = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
endpoints = [
    "https://web-ai-media-editor.cn/v1/chat/completions",
    "https://inferaichat.com/v1/chat/completions"
]

last_error = None
for endpoint in endpoints:
    try:
        print(f"   → Trying endpoint: {endpoint}")
        req = urllib.request.Request(
            endpoint,
            data=payload_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )
        # 超时设置为 500 秒 (模型可能需要较长时间生成)
        resp = urllib.request.urlopen(req, timeout=500)
        raw = resp.read().decode('utf-8')
        result = json.loads(raw)
        print(f"   ✓ API call successful via {endpoint}")
        last_error = None
        break
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        print(f"   ✗ HTTP Error {e.code}: {body[:500]}")
        last_error = f"HTTP {e.code}: {body[:500]}"
    except urllib.error.URLError as e:
        print(f"   ✗ URL Error: {e.reason}")
        last_error = f"URL Error: {e.reason}"
    except Exception as e:
        print(f"   ✗ Error: {e}")
        last_error = str(e)

if last_error:
    print(f"\n[ERROR] All endpoints failed: {last_error}")
    sys.exit(1)

# === 3. 解析结果 ===
print("[5/5] 解析并写入规则...")

# 尝试从response中提取choices
if "choices" in result and len(result["choices"]) > 0:
    content = result["choices"][0].get("message", {}).get("content", "")
else:
    content = result.get("content", json.dumps(result, ensure_ascii=False))

print(f"   → Response length: {len(content)} 字符")
print(f"   → Response preview:\n{content[:2000]}")
print(f"   → ... (truncated)")

# 尝试解析JSON
rules = None
# 尝试直接解析
try:
    rules = json.loads(content)
    print(f"   ✓ Direct JSON parse OK, {len(rules)} rules")
except json.JSONDecodeError:
    # 尝试从```json ```代码块中提取
    import re
    json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', content, re.DOTALL)
    if json_match:
        try:
            rules = json.loads(json_match.group(1))
            print(f"   ✓ JSON block parse OK, {len(rules)} rules")
        except json.JSONDecodeError as e:
            print(f"   ✗ JSON block parse failed: {e}")
    
    if rules is None:
        # 尝试找最长的 [ ... ] 数组
        arr_match = re.search(r'\[\s*\{.*?\}\s*\]', content, re.DOTALL)
        if arr_match:
            try:
                rules = json.loads(arr_match.group(0))
                print(f"   ✓ Array regex parse OK, {len(rules)} rules")
            except:
                pass
    
    if rules is None:
        print("   ✗ Could not parse JSON from response. Saving raw response.")
        rules = [{"error": "parse_failed", "raw_response": content[:5000]}]

# 验证规则格式
if isinstance(rules, list):
    for i, r in enumerate(rules):
        required_keys = ["axiom_ref", "rule_name", "check_condition", "fix_action"]
        missing = [k for k in required_keys if k not in r]
        if missing:
            print(f"   ⚠ Rule {i} missing keys: {missing}")
            for k in missing:
                r[k] = f"MISSING: {k}"
        if len(rules) > 10:
            print(f"   ⚠ Got {len(rules)} rules, truncating to 10")
            rules = rules[:10]

# === 4. 写入文件 ===
output_path = os.path.join(CLUSTER, 'revelation_rules.json')
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(rules, f, ensure_ascii=False, indent=2)
print(f"\n✓ 规则已写入: {output_path}")
print(f"✓ 共 {len(rules)} 条规则")

# 打印摘要
print("\n=== 规则摘要 ===")
for i, r in enumerate(rules):
    print(f"{i+1}. [{r.get('axiom_ref','?')}] {r.get('rule_name','?')}")
    print(f"   检查: {r.get('check_condition','?')[:80]}...")
    print(f"   修复: {r.get('fix_action','?')[:80]}...")
    print()
