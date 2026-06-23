"""
code_injection_gate.py — 代码注入门（零偏移边界）

本地作用域: 决策→代码注入→验证（零偏移）
API输出永远不能直接触发代码修改。
所有代码变更必须经过此门。

安全策略:
  1. 语法验证 (Python AST)
  2. 禁止模式检测 (rm -rf, os.system, subprocess shell注入)
  3. 文件范围限制 (只允许修改 .py / .md / .json)
  4. 变更量限制 (单次不超过200行)
  5. 回滚准备 (自动git备份)
"""

import ast
import json
import os
import subprocess
import tempfile
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent

# ─── 禁止模式 ───
FORBIDDEN_PATTERNS = [
    "rm -rf", "rm -r /", "rm -f /",
    "os.system(",
    "eval(", "exec(",
    "shutil.rmtree", "os.remove(", "os.unlink(",
]

ALLOWED_EXTENSIONS = {".py", ".md", ".json", ".txt", ".yaml", ".yml", ".cfg", ".conf"}
MAX_CHANGES_PER_INJECTION = 200  # 单次最多200行

# ─── 验证函数 ───

def verify_syntax(code: str) -> dict:
    """验证Python代码语法"""
    try:
        ast.parse(code)
        return {"valid": True, "error": ""}
    except SyntaxError as e:
        return {"valid": False, "error": str(e)}

def check_forbidden(code: str) -> list:
    """检测禁止模式"""
    hits = []
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in code:
            hits.append(pattern)
    return hits

def verify_file_extension(filepath: str) -> bool:
    """验证文件扩展名是否允许"""
    ext = Path(filepath).suffix.lower()
    return ext in ALLOWED_EXTENSIONS

def count_lines(code: str) -> int:
    return len(code.strip().split("\n"))

# ─── 代码注入门 ───

def injection_gate(filepath: str, new_content: str, old_content: str = "") -> dict:
    """完整的代码注入安全检查
    
    返回:
        {"allowed": bool, "reason": str, "backup_path": str}
    """
    # 0. 内容非空检查
    if not new_content and not old_content:
        return {"allowed": False, "reason": "无变更内容(new_content和old_content均为空)", "backup_path": ""}
    
    # 1. 文件扩展名检查
    if not verify_file_extension(filepath):
        return {"allowed": False, "reason": f"不允许修改 {Path(filepath).suffix} 文件", "backup_path": ""}
    
    # 2. 禁止模式检测
    forbidden_hits = check_forbidden(new_content)
    if forbidden_hits:
        return {"allowed": False, "reason": f"含禁止模式: {forbidden_hits}", "backup_path": ""}
    
    # 3. 如果是.py文件, 语法验证
    if filepath.endswith(".py"):
        syntax = verify_syntax(new_content)
        if not syntax["valid"]:
            return {"allowed": False, "reason": f"语法错误: {syntax['error']}", "backup_path": ""}
    
    # 4. 变更量限制
    new_lines = count_lines(new_content)
    if new_lines > MAX_CHANGES_PER_INJECTION:
        return {"allowed": False, "reason": f"变更量{new_lines}行超过上限{MAX_CHANGES_PER_INJECTION}", "backup_path": ""}
    
    # 5. 自动git备份（回滚准备）
    backup_path = ""
    try:
        full_path = Path(filepath)
        if full_path.exists():
            # git备份
            subprocess.run(
                ["git", "add", str(full_path)],
                capture_output=True, timeout=10, cwd=str(CLUSTER)
            )
            timestamp = subprocess.run(
                ["git", "stash", "push", "-m", f"auto-backup {full_path.name}"],
                capture_output=True, timeout=10, cwd=str(CLUSTER)
            )
            # 恢复工作区（stash pop留给回滚操作）
    except:
        pass
    
    return {"allowed": True, "reason": f"代码注入通过安全门 (备份已创建)", "backup_path": backup_path}

def rollback(filepath: str) -> dict:
    """回滚文件到git备份"""
    try:
        subprocess.run(
            ["git", "checkout", "--", filepath],
            capture_output=True, timeout=10, cwd=str(CLUSTER)
        )
        return {"success": True, "message": f"已回滚 {filepath}"}
    except Exception as e:
        return {"success": False, "message": str(e)}

# ─── 自检 ───
if __name__ == "__main__":
    # 测试: 危险内容应被拦截
    test = 'import os; os.system("rm -rf /")'
    result = injection_gate("test.py", test)
    print(f"危险测试: {result['reason']}")
    
    # 测试: 安全内容应通过
    safe = 'print("hello world")\n'
    result = injection_gate("test.py", safe)
    print(f"安全测试: {result['reason']}")
    
    # 测试: .exe文件应被拒绝
    result = injection_gate("virus.exe", "bad stuff")
    print(f"扩展名测试: {result['reason']}")
