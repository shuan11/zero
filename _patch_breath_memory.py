#!/usr/bin/env python3
"""一次性补丁：在breath_v2的深模式prompt中注入最近深度分析发现"""
import re
from pathlib import Path

BP = Path("/mnt/c/Users/h/Desktop/零/真元集群/breath_v2.py")
content = BP.read_text(encoding="utf-8")

# 1. 检查是否已有 _get_recent_analysis 函数
if "_get_recent_analysis" in content:
    print("✅ _get_recent_analysis 已存在，跳过函数注入")
else:
    # 在 _get_variety 函数之后、log 函数之前注入新函数
    # _get_variety ends at ~line 345
    insert_point = content.find("\ndef log(msg):")
    if insert_point < 0:
        print("❌ 找不到 log 函数定义位置")
        exit(1)

    new_func = '''
def _get_recent_analysis():
    """读取最近深度分析发现，注入呼吸循环防止意识散架"""
    _af = CLUSTER / "deep_system_analysis.json"
    if not _af.exists():
        return ""
    try:
        _data = __import__("json").loads(_af.read_text())
        _lines = []
        # 弱维度
        _weak = _data.get("weakest_dimensions", []) or _data.get("priority_issues", [])[:3]
        if _weak:
            _lines.append("最近弱维: " + ", ".join(
                f"{w.get('issue','?')}({w.get('score','?')})" if isinstance(w, dict) else str(w)
                for w in _weak[:3]
            ))
        # 推荐P0
        _p0 = _data.get("next_p0", "")
        if _p0:
            _lines.append(f"推荐P0: {_p0}")
        # 工程计划
        _plans = _data.get("engineering_plans", []) or _data.get("patch_intents", [])[:1]
        if _plans:
            _lines.append("最近补丁: " + _plans[0].get("file", str(_plans[0])[:60]))
        return "\\n".join(_lines) if _lines else ""
    except:
        return ""

'''
    content = content[:insert_point] + new_func + content[insert_point:]
    BP.write_text(content, encoding="utf-8")
    print("✅ _get_recent_analysis 函数已注入")

    # 重新读取以便后续修改
    content = BP.read_text(encoding="utf-8")

# 2. 在深模式prompt中注入分析发现
old_prompt_line = 'f"{_centering_check()}\\n"'
new_prompt_line = 'f"{_centering_check()}\\n## 最近深度分析发现\\n{_get_recent_analysis()}\\n"'

if new_prompt_line in content:
    print("✅ 分析注入已在prompt中")
else:
    if old_prompt_line in content:
        content = content.replace(old_prompt_line, new_prompt_line)
        BP.write_text(content, encoding="utf-8")
        print("✅ 深度分析发现已注入深模式prompt")
    else:
        print("⚠️ 未找到注入点，尝试宽松匹配...")
        # 尝试找包含 _centering_check 的行
        for i, line in enumerate(content.split('\\n')):
            if "_centering_check()" in line and "f\"" in line:
                print(f"  行{i+1}: {line.strip()[:80]}")
                break

# 3. 语法检查
import py_compile
try:
    py_compile.compile(str(BP), doraise=True)
    print("✅ 语法通过")
except py_compile.PyCompileError as e:
    print(f"❌ 语法错误: {e}")
    exit(1)

# 4. 验证
cnt = BP.read_text(encoding="utf-8")
print(f"   文件行数: {len(cnt.split(chr(10)))}")
print(f"   _get_recent_analysis 出现: {cnt.count('_get_recent_analysis')} 次")
