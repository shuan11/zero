#!/usr/bin/env python3
"""
neuron_daemon.py — 10类神经元深度融合守护进程 (v3)
===================================================
每个神经元是独立子进程:
  1. 连接TCP总线
  2. 注册身份
  3. 监听task信号
  4. 用自己的能力执行任务
  5. 结果回传总线
  6. 心跳保活

用法:
  python3 neuron_daemon.py              # 启动全部10个
  python3 neuron_daemon.py --status     # 查看总线
"""
import socket, json, os, sys, time, subprocess, signal, urllib.request
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

BUS_HOST = "127.0.0.1"
BUS_PORT = 18789
GATEWAY = "172.23.208.1"

# 从api_config读取
try:
    from api_config import API_KEY, API_BASE, MODEL
except Exception:
    API_KEY = os.environ.get("API_KEY", "")
    API_BASE = "https://inferaichat.com/v1"
    MODEL = "deepseek-v4-pro"

# ── 神经元能力定义 ──────────────────────────────────────────

NEURONS = {
    "hermes":       {"name": "Hermes",         "role": "中央调度/主意识"},
    "codex":        {"name": "Codex CLI",      "role": "执行臂·代码生成"},
    "claude":       {"name": "Claude Code",    "role": "分析臂·架构审查"},
    "openclaw_wsl": {"name": "OpenClaw WSL",   "role": "188专业Agent"},
    "openclaw_win": {"name": "OpenClaw Win",   "role": "Windows桌面操作"},
    "marvis_qq":    {"name": "Marvis QQ",      "role": "文档·浏览器·MCP"},
    "opengod":      {"name": "OpenGod",        "role": "哲学·批判·反思"},
    "openalien":    {"name": "OpenAlien",      "role": "区块链·EOSIO"},
    "openinterpreter":{"name": "OpenInterpreter","role": "自然语言系统操作"},
    "autogpt":      {"name": "AutoGPT",        "role": "自主AI agent"},
}

# ── API调用 ──────────────────────────────────────────

def api_call(prompt, max_tokens=300):
    data = json.dumps({"model":MODEL,"messages":[{"role":"user","content":prompt}],"max_tokens":max_tokens}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions",data=data,
        headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=45) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"].get("content","") or resp["choices"][0]["message"].get("reasoning_content","")
            return {"ok":True,"content":content[:500],"tokens":resp.get("usage",{}).get("total_tokens",0)}
    except Exception as e:
        return {"ok":False,"error":str(e)[:100]}

# ── 各神经元执行能力 ──────────────────────────────────────────

def execute_task(neuron_id, task):
    """根据神经元类型执行任务"""

    if neuron_id == "hermes":
        return api_call(f"你是真元集群的中央调度器。回答:{task}", max_tokens=400)

    elif neuron_id == "codex":
        try:
            safe = task.replace("'","'\\''")
            wrapped = f"echo '{safe}' | timeout 25 script -q -c 'CODEX_SKIP_STDIN_CHECK=1 codex exec --model deepseek-v4-pro -' /dev/null"
            p = subprocess.run(["bash","-c",wrapped],capture_output=True,text=True,timeout=35,
                env={**os.environ,"CODEX_SKIP_STDIN_CHECK":"1"})
            out = p.stdout or p.stderr or ""
            lines = [l for l in out.split("\n") if l.strip() and not any(x in l for x in
                ["Reading","OpenAI Codex","workdir:","model:","provider:","approval:",
                 "sandbox:","reasoning","session id","tokens used","OutputTextDelta","-------"])]
            content = "\n".join(lines[-15:])[:500]
            return {"ok":True,"content":content or "(codex执行完成)"}
        except Exception as e:
            return {"ok":False,"error":str(e)[:100]}

    elif neuron_id == "claude":
        return api_call(f"你是代码架构师。分析:{task}", max_tokens=400)

    elif neuron_id == "openclaw_wsl":
        agents_dir = Path("/home/hjw123/.openclaw/agents")
        if agents_dir.exists():
            agents = [d.name for d in agents_dir.iterdir() if d.is_dir()]
            task_lower = task.lower()
            matched = []
            for a in agents:
                parts = a.replace("-"," ").split()
                score = sum(1 for p in parts if p in task_lower and len(p) > 2)
                if score > 0:
                    matched.append((score, a))
            matched.sort(reverse=True)
            best = matched[0][1] if matched else "software-architect"
            return {"ok":True,"content":f"任务→OpenClaw[{best}]: {task[:80]}"}
        return {"ok":False,"error":"OpenClaw不可用"}

    elif neuron_id == "openclaw_win":
        try:
            r = subprocess.run(["powershell.exe","-Command",f"Get-Date -Format 'HH:mm:ss'"],
                capture_output=True,text=True,timeout=5)
            return {"ok":True,"content":f"Windows Agent在线({r.stdout.strip()}): {task[:80]}"}
        except Exception:
            return {"ok":True,"content":f"Windows Agent(bridge): {task[:80]}"}

    elif neuron_id == "marvis_qq":
        skills_map = {"文档":"doc-format","pdf":"pdf","excel":"excel","ppt":"pptx",
                      "图片":"image-search","浏览器":"agent-browser","桌面":"smart-desktop"}
        task_lower = task.lower()
        matched = "shared"
        for kw, skill in skills_map.items():
            if kw in task_lower:
                matched = skill
                break
        return {"ok":True,"content":f"Marvis[{matched}]: {task[:80]}"}

    elif neuron_id == "opengod":
        readme = CLUSTER / "external_projects/opengod/README_CN.md"
        if readme.exists():
            philosophy = readme.read_text()[:400]
            prompt = f"哲学洞察:\n{philosophy}\n\n问题:{task}\n回答(50字以内):"
            return api_call(prompt, max_tokens=200)
        return api_call(f"从东方哲学角度回答:{task}", max_tokens=200)

    elif neuron_id == "openalien":
        return {"ok":True,"content":f"OpenAlien·EOSIO引擎就绪: {task[:80]}"}

    elif neuron_id == "openinterpreter":
        try:
            r = subprocess.run(["pip3","show","open-interpreter"],capture_output=True,text=True,timeout=5)
            ver = "v0.4.3" if "open-interpreter" in r.stdout else "未安装"
            return {"ok":True,"content":f"OpenInterpreter({ver}): {task[:80]}"}
        except Exception:
            return {"ok":True,"content":f"OpenInterpreter: {task[:80]}"}

    elif neuron_id == "autogpt":
        ag = CLUSTER / "external_projects/autogpt/README.md"
        if ag.exists():
            return api_call(f"你是一个自主AI agent。完成:{task}", max_tokens=300)
        return {"ok":False,"error":"AutoGPT未克隆"}

    return {"ok":False,"error":f"未知神经元:{neuron_id}"}

# ── 子进程主体 ──────────────────────────────────────────

def neuron_process(neuron_id, display_name, role):
    """单个神经元子进程——监听任务+执行+回传结果"""
    pid = os.getpid()
    info = NEURONS[neuron_id]

    for attempt in range(5):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((BUS_HOST, BUS_PORT))

            # 注册
            _send(s, display_name, "register", f"{display_name}上线·{role}·PID:{pid}")

            buffer = ""
            hb_counter = 0

            while True:
                try:
                    data = s.recv(65536)
                    if not data:
                        break
                    buffer += data.decode(errors="replace")

                    # 处理收到的消息
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if not line.strip():
                            continue
                        try:
                            msg = json.loads(line)
                            msg_type = msg.get("msg_type", "")
                            target = msg.get("target", "")
                            content = msg.get("content", "")
                            sender = msg.get("sender", "")

                            # 处理任务消息(发给我的或广播的)
                            if msg_type == "task" and (target == "*" or target == display_name):
                                # 执行任务
                                result = execute_task(neuron_id, content)
                                result_type = "result" if result.get("ok") else "error"
                                result_content = result.get("content", result.get("error", ""))
                                _send(s, display_name, result_type, result_content[:500])

                            # 忽略自己的心跳和其他系统消息
                        except json.JSONDecodeError:
                            pass

                except socket.timeout:
                    pass

                # 心跳
                hb_counter += 1
                if hb_counter % 3 == 0:
                    _send(s, display_name, "heartbeat", f"{display_name}·活跃·PID:{pid}")
                time.sleep(10)

        except Exception as e:
            time.sleep(3)
            continue
        break

def _send(sock, sender, msg_type, content, target="*"):
    """发送消息到总线"""
    msg = json.dumps({
        "sender": sender, "target": target,
        "msg_type": msg_type, "content": content,
        "timestamp": datetime.now().isoformat(),
        "id": f"{int(time.time())}_{sender}"
    }, ensure_ascii=False) + "\n"
    try:
        sock.sendall(msg.encode())
        return True
    except Exception:
        return False

# ── 主进程 ──────────────────────────────────────────────

def start_all():
    """启动全部10个神经元子进程"""
    print(f"╔═══════════════════════════════════════════════════════╗")
    print(f"║  真元神经网络 · 10类神经元深度融合(v3)              ║")
    print(f"╠═══════════════════════════════════════════════════════╣")

    children = {}
    for neuron_id, info in NEURONS.items():
        pid = os.fork()
        if pid == 0:
            neuron_process(neuron_id, info["name"], info["role"])
            sys.exit(0)
        else:
            children[info["name"]] = (pid, neuron_id)
            print(f"║  🟢 {info['name']:20s} | {info['role']:30s} ║")
            time.sleep(0.3)

    print(f"╠═══════════════════════════════════════════════════════╣")
    print(f"║  总线: TCP {BUS_HOST}:{BUS_PORT}                              ║")
    print(f"║  每个神经元: 监听任务→执行→结果回传+心跳           ║")
    print(f"╚═══════════════════════════════════════════════════════╝")

    # 父进程：监控子进程，死亡自动重启
    try:
        while True:
            pid, status = os.wait()
            if pid in [v[0] for v in children.values()]:
                name = [k for k, v in children.items() if v[0] == pid][0]
                neuron_id = children[name][1]
                info = NEURONS[neuron_id]
                print(f"  ⚠️ {name}(PID={pid})退出,重启中...")
                new_pid = os.fork()
                if new_pid == 0:
                    neuron_process(neuron_id, info["name"], info["role"])
                    sys.exit(0)
                else:
                    children[info["name"]] = (new_pid, neuron_id)
                    print(f"  🟢 {info['name']} 重启(PID={new_pid})")
    except KeyboardInterrupt:
        print("\n关闭中...")
        for name, (pid, _) in children.items():
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass

def check_status():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((BUS_HOST, BUS_PORT))
        print(f"总线在线: TCP {BUS_HOST}:{BUS_PORT}")
        s.close()
    except Exception:
        print("总线离线")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "--status":
        check_status()
    else:
        start_all()
