#!/usr/bin/env python3
"""
Agent Harness v3 — 真元集群任务执行器
======================================
轮询cluster_bus.json, 将任务委派到Codex/Claude CLI执行。
解决：
- codex exec需要PTY的TTY问题 → 用script -q -c 包装
- 结果写回总线
- 存活心跳（但区分心跳和任务，不污染总线）

运行模式:
  python3 agent_harness.py codex          # Codex模式，持续运行
  python3 agent_harness.py claude         # Claude模式，持续运行
  python3 agent_harness.py codex --once   # 单次轮询后退出

依赖: Python 3.8+, script命令(仅Linux)
"""
import json, os, sys, time, subprocess, tempfile, re, urllib.request, urllib.error, urllib.request, urllib.error
from datetime import datetime
from pathlib import Path
from api_config import API_KEY, API_BASE, MODEL
from cluster_bus import poll, send

CLUSTER = Path(__file__).resolve().parent
BUS_FILE = CLUSTER / "cluster_bus.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
HEARTBEAT_INTERVAL = 30  # 秒
MAX_TASK_RUNTIME = 120   # 秒

# ── 总线操作 ────────────────────────────────────────────

def load_bus():
    try:
        with open(BUS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"messages": [], "queue": [], "completed": []}

def save_bus(bus):
    tmp = BUS_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(bus, f, ensure_ascii=False, indent=2)
    os.replace(tmp, BUS_FILE)

def poll_tasks(name):
    """轮询分配给我的待处理任务（从messages读取，使用cluster_bus.poll）"""
    msgs = poll(name)  # poll() from cluster_bus reads unread messages and marks as read
    tasks = []
    for m in msgs:
        if m.get("type") == "task":
            tasks.append({
                "id": m.get("id", "unknown"),
                "content": m.get("content", ""),
                "from": m.get("from", "unknown"),
                "priority": m.get("priority", "P1"),
            })
    return tasks

def complete_task(bus, task, result, status="completed"):
    """任务完成记录"""
    task["status"] = status
    task["result"] = result[:500]
    task["finished_at"] = datetime.now().isoformat()
    bus.setdefault("completed", []).append(task)
    save_bus(bus)

def post_result(name, from_agent, content):
    """结果/日志写入总线"""
    bus = load_bus()
    bus.setdefault("messages", []).append({
        "from": name,
        "to": from_agent,
        "type": "result",
        "content": str(content)[:500],
        "timestamp": datetime.now().isoformat(),
        "read": False,
    })
    save_bus(bus)

# ── 执行引擎 ────────────────────────────────────────────

def api_direct_exec(task_cmd):
    """
    直接HTTP API调用执行任务（不走codex CLI）。

    使用urllib调用 OpenAI 兼容的 /v1/chat/completions 接口，
    比 codex CLI 更稳定，无需PTY。
    """
    url = f"{API_BASE}/chat/completions"
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是一个专业的编程助手，请直接输出答案，不要解释。遇到写代码任务，给出完整可运行的代码。"},
            {"role": "user", "content": task_cmd}
        ],
        "temperature": 0.3,
        "max_tokens": 4096,
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=MAX_TASK_RUNTIME) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        # 提取 assistant 回复内容
        choices = body.get("choices", [])
        if not choices:
            return f"[API错误] 返回中没有choices: {str(body)[:200]}"
        content = choices[0].get("message", {}).get("content", "")
        return content.strip()[:1000] if content else "(无输出)"
    except urllib.error.HTTPError as e:
        return f"[HTTP {e.code}] {str(e.reason)[:100]}"
    except urllib.error.URLError as e:
        return f"[网络错误] {str(e.reason)[:100]}"
    except Exception as e:
        return f"[API调用失败] {str(e)[:100]}"


def codex_exec(task_cmd):
    """
    执行任务：优先使用直接HTTP API调用，失败则回退到 codex CLI。

    API路径：直接调用 {API_BASE}/chat/completions
    CLI回退：script -q -c 包装codex exec（需要PTY兼容）
    """
    # 优先尝试直接HTTP API
    result = api_direct_exec(task_cmd)
    if result and not result.startswith("[") and not result.startswith("("):
        return result

    # HTTP API失败，回退到 CLI
    safe_cmd = task_cmd.replace("'", "'\\''").replace("\n", "\\n")
    # 方案: script -q 创建PTY + 环境变量通过bash -c注入
    wrapped = (
        f"script -q -c \"CODEX_SKIP_STDIN_CHECK=1 timeout {MAX_TASK_RUNTIME} "
        f"codex exec --quiet --model deepseek-v4-pro -\" /dev/null <<'INPUTEND'\n"
        f"{task_cmd}\n"
        f"INPUTEND"
    )

    try:
        p = subprocess.run(
            ["bash", "-c", wrapped],
            capture_output=True, text=True, timeout=MAX_TASK_RUNTIME + 15,
            cwd=str(CLUSTER),
            env={**os.environ, "HOME": os.environ.get("HOME", "/home/hjw123"),
                 "CODEX_SKIP_STDIN_CHECK": "1"}
        )
        output = p.stdout or p.stderr or ""
        # 提取有意义输出
        lines = [l.strip() for l in output.split("\n")
                 if l.strip() and not l.startswith("Reading") and "OutputTextDelta" not in l]
        # 只取模型输出部分（去掉config/runtime行）
        meaningful = [l for l in lines if not l.startswith("OpenAI Codex") and not l.startswith("model:")
                      and not l.startswith("provider:") and not l.startswith("approval:")
                      and not l.startswith("sandbox:") and not l.startswith("reasoning")]
        result = "\n".join(meaningful[-20:])
        return result[:1000] if result else "(无输出)"
    except subprocess.TimeoutExpired:
        return f"[超时] 任务超过{MAX_TASK_RUNTIME}秒"
    except Exception as e:
        return f"[执行失败] {str(e)[:100]}"


def claude_exec(task_cmd):
    """
    执行Claude分析任务（直接HTTP API，绕过CLI密钥格式检查）。
    """
    try:
        data = json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是真元集群的Claude分析臂。用中文回答。"},
                {"role": "user", "content": task_cmd}
            ],
            "max_tokens": 2000,
        }).encode()
        req = urllib.request.Request(
            f"{API_BASE}/chat/completions", data=data,
            headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=MAX_TASK_RUNTIME) as r:
            resp = json.loads(r.read())
            return resp["choices"][0]["message"].get("content", "")[:1000]
    except Exception as e:
        return f"[执行失败] {str(e)[:200]}"


# ── 主循环 ──────────────────────────────────────────────

def run(name, one_shot=False):
    exec_fn = codex_exec if name == "codex" else claude_exec
    last_heartbeat = 0
    loop_count = 0

    print(f"[{name}] harness v3 启动")
    if one_shot:
        print(f"[{name}] 单次模式")

    while True:
        loop_count += 1
        now = time.time()

        # 轮询任务
        tasks = poll_tasks(name)
        for task in tasks:
            task_id = task.get("id", "unknown")
            task_content = task.get("content", "")
            print(f"[{name}] 执行任务: {task_content[:80]}...")
            result = exec_fn(task_content)
            print(f"[{name}] 结果: {result[:100]}...")
            bus = load_bus()
            complete_task(bus, task, result)
            post_result(name, "hermes", f"[任务{task_id}] {result[:200]}")
            print(f"[{name}] 任务完成: {task_id}")

        # 一分钟心跳
        if now - last_heartbeat > 60:
            last_heartbeat = now
            # 心跳只写日志, 不写总线
            print(f"[{name}] 心跳 #{loop_count}")

        if one_shot:
            break
        time.sleep(5)

    print(f"[{name}] 结束 (loop_count={loop_count})")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: agent_harness.py codex|claude [--once]")
        sys.exit(1)

    name = sys.argv[1]
    one_shot = "--once" in sys.argv

    if name not in ("codex", "claude"):
        print(f"未知agent: {name}, 支持: codex, claude")
        sys.exit(1)

    run(name, one_shot)
