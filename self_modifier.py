#!/usr/bin/env python3
"""
零 · 自修改引擎 v3
=================
先用静态分析找真实bug，再用API生成修复。
不是让LLM漫无目的地"找改进"，而是给LLM一个具体问题让它修。
"""
import os, sys, json, time, shutil, subprocess, re, random, ast
from pathlib import Path

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(WORKDIR)
sys.path.insert(0, str(WORKDIR))
PATCH_DIR = WORKDIR / "self_patches"
BACKUP_DIR = PATCH_DIR / "backups"
MANIFEST = PATCH_DIR / "manifest.json"
os.makedirs(PATCH_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)

from api_config import API_KEY, API_BASE, MODEL

TARGET_FILES = [
    "coordination_loop.py", "api_bridge.py", "persistent_engine.py",
    "trunk_daemon.py", "auto_evolution_daemon.py", "comprehension_daemon.py",
    "co_evolution_daemon.py", "anthropic_proxy.py", "p513_evolution_engine.py",
    "genome.py", "hippocampus.py",
]


def call_llm(prompt):
    """调API，兼容reasoning模型"""
    import requests
    resp = requests.post(
        f"{API_BASE}/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 4096, "temperature": 0.2},
        timeout=120,
    )
    if resp.status_code != 200:
        return None
    resp.encoding = "utf-8"
    msg = resp.json()["choices"][0]["message"]
    return (msg.get("content") or "").strip()


def extract_json(text):
    """从文本中提取JSON对象"""
    if not text:
        return None
    clean = re.sub(r'```[a-z]*\s*', '', text)
    start = clean.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(clean)):
        if clean[i] == "{":
            depth += 1
        elif clean[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(clean[start:i+1])
                except json.JSONDecodeError:
                    return None
    return None


# ─── 静态分析器：找真实问题 ───────────────────────────

def find_issues(filepath, content):
    """在文件中找真实可改进的问题"""
    issues = []
    lines = content.split("\n")

    for i, line in enumerate(lines):
        ln = i + 1

        # 1. 空 except（吞掉异常）
        if re.match(r'\s*except\s*:\s*(#.*)?$', line):
            # 看下一行是不是pass
            if i+1 < len(lines) and re.match(r'\s*pass\s*(#.*)?$', lines[i+1]):
                issues.append({
                    "type": "bare_except_pass",
                    "line": ln,
                    "desc": f"第{ln}行空except+pass吞掉所有异常",
                    "context": "\n".join(lines[max(0,i-1):i+3]),
                })

        # 2. 空except with simple action
        if re.match(r'\s*except\s+Exception\s+as\s+\w+:\s*$', line):
            if i+1 < len(lines) and re.match(r'\s*pass\s*(#.*)?$', lines[i+1]):
                issues.append({
                    "type": "except_pass",
                    "line": ln,
                    "desc": f"第{ln}行except Exception吞掉异常",
                    "context": "\n".join(lines[max(0,i-1):i+3]),
                })

        # 3. 硬编码密钥（明文）
        if re.search(r'(?:API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*["\'][^"\']{10,}["\']', line):
            if "import" not in line and "***" not in line:
                issues.append({
                    "type": "hardcoded_secret",
                    "line": ln,
                    "desc": f"第{ln}行硬编码密钥",
                    "context": line.strip(),
                })

        # 4. 可变默认参数
        if re.search(r'def\s+\w+\(.*=\s*(\[\]|\{\})\s*[,)]', line):
            issues.append({
                "type": "mutable_default",
                "line": ln,
                "desc": f"第{ln}行使用可变默认参数([]或{{}})",
                "context": line.strip(),
            })

        # 5. time.sleep在循环中且>300s
        if re.match(r'\s*time\.sleep\(\s*(\d+)\s*\)', line):
            m = re.search(r'sleep\(\s*(\d+)\s*\)', line)
            if m and int(m.group(1)) > 300:
                issues.append({
                    "type": "long_sleep",
                    "line": ln,
                    "desc": f"第{ln}行sleep({m.group(1)})过长",
                    "context": line.strip(),
                })

        # 6. os.system() (应使用subprocess)
        if re.search(r'\bos\.system\(', line):
            issues.append({
                "type": "os_system",
                "line": ln,
                "desc": f"第{ln}行使用os.system()，应使用subprocess.run()",
                "context": line.strip(),
            })

        # 7. eval() / exec() 调用
        if re.search(r'\b(?:eval|exec)\s*\([^)]*\)', line) and 'def ' not in line:
            issues.append({
                "type": "eval_exec",
                "line": ln,
                "desc": f"第{ln}行使用eval/exec，安全风险",
                "context": line.strip(),
            })

    return issues


class SelfModifier:
    def __init__(self):
        self.count = 0
        self.history = []
        self._load()

    def _load(self):
        if MANIFEST.exists():
            d = json.loads(MANIFEST.read_text())
            self.count = d.get("count", 0)
            self.history = d.get("history", [])

    def _save(self):
        MANIFEST.write_text(json.dumps({"count": self.count, "history": self.history[-100:]}, indent=2))

    def pick_target(self):
        modified = {h["file"] for h in self.history[-30:]}
        candidates = [f for f in TARGET_FILES if f not in modified]
        return random.choice(candidates) if candidates else random.choice(TARGET_FILES)

    def run_one_cycle(self):
        target = self.pick_target()
        filepath = WORKDIR / target
        if not filepath.exists():
            return {"status": "skipped", "reason": f"{target} not found"}

        content = filepath.read_text(encoding="utf-8")

        # Phase 1: 静态分析找问题
        issues = find_issues(filepath, content)
        if not issues:
            return {"status": "no_issues", "file": target}

        issue = issues[0]  # 取第一个问题

        # Phase 2: 让API生成精确修复
        context_lines = issue["context"].split("\n")
        prompt = (
            f"Python文件 {target} 第{issue['line']}行有问题：{issue['desc']}\n\n"
            f"上下文代码：\n```python\n{issue['context']}\n```\n\n"
            f"生成精确修复。输出JSON（不要markdown围栏）：\n"
            f'{{"find":"问题代码的精确原文","replace":"修复后的代码","safe":true}}\n'
            f"如果无法安全修复：{{\"safe\":false}}"
        )

        response = call_llm(prompt)
        fix = extract_json(response) if response else None

        if not fix or not isinstance(fix, dict):
            # API失败时用规则修复
            fix = self._rule_fix(issue, content)

        if not fix or fix.get("safe") is False:
            return {"status": "no_fix", "issue": issue["desc"]}

        find_str = fix.get("find", "")
        replace_str = fix.get("replace", "")
        if not find_str or not replace_str:
            return {"status": "empty_fix"}

        current = filepath.read_text(encoding="utf-8")
        if find_str not in current:
            # 尝试模糊匹配
            find_str = find_str.strip()
            if find_str not in current:
                return {"status": "no_match", "find": find_str[:80]}

        new_content = current.replace(find_str, replace_str, 1)

        # 语法验证
        try:
            compile(new_content, str(filepath), "exec")
        except SyntaxError as e:
            return {"status": "syntax_error", "error": str(e)[:100]}

        # 备份+应用
        bak_path = BACKUP_DIR / f"{target}.{int(time.time())}.bak"
        shutil.copy2(filepath, bak_path)
        filepath.write_text(new_content, encoding="utf-8")

        # git
        git_ok = False
        try:
            subprocess.run(["git", "add", target], capture_output=True, timeout=10)
            r = subprocess.run(
                ["git", "commit", "-m", f"fix: {target}:{issue['line']} — {issue['desc']}",
                 "--author=SelfModifier <zero@evolution>"],
                capture_output=True, timeout=10,
            )
            git_ok = r.returncode == 0
        except Exception:
            pass

        self.count += 1
        self.history.append({
            "time": time.time(), "file": target, "line": issue["line"],
            "type": issue["type"], "desc": issue["desc"], "git": git_ok,
        })
        self._save()
        return {"status": "applied", "file": target, "line": issue["line"],
                "type": issue["type"], "desc": issue["desc"]}

    def _rule_fix(self, issue, content):
        """API失败时的规则修复"""
        if issue["type"] == "bare_except_pass":
            return {
                "find": issue["context"].split("\n")[1] if len(issue["context"].split("\n")) > 1 else "except:",
                "replace": "except Exception as e:",
                "safe": True,
            }
        return None

    def get_report(self):
        return {
            "total": self.count,
            "recent": [
                {"time": time.strftime("%H:%M", time.localtime(h["time"])),
                 "file": h["file"], "type": h.get("type", "?"), "desc": h.get("desc", "?")}
                for h in self.history[-10:]
            ],
        }


if __name__ == "__main__":
    sm = SelfModifier()
    result = sm.run_one_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    r = sm.get_report()
    print(f"\n总计: {r['total']}")
    for h in r["recent"]:
        print(f"  {h['time']} {h['file']}:{h['type']} — {h['desc']}")
