#!/usr/bin/env python3
"""
neuron_daemon_quality.py — 10类神经元深度融合守护进程 (v4-质量版)
==============================================================
每个神经元在收到task时真实调用外部API执行推理(而非返回静态字符串)。
重点改进：codex/claude/openclaw_wsl/openclaw_win/marvis_qq/opengod/openalien等
全部通过api_call做真实推理。

用法:
  python3 neuron_daemon_quality.py              # 启动全部10个
  python3 neuron_daemon_quality.py --status     # 查看总线
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

# ── 频道分流映射 ──────────────────────────────────────────
# 每个真实神经元连接专属业务频道，与控制通道分离
# 映射规则: display_name → 业务端口, 未匹配则使用控制主通道 18789
NEURON_CHANNEL_MAP = {
    "Codex CLI":        18790,  # code频道——代码生成/审查
    "Claude Code":      18791,  # analysis频道——分析/观察
    "OpenClaw":         18792,  # pro频道(前缀: OpenClaw WSL/Win)
    "Marvis":           18792,  # pro频道(前缀: Marvis QQ)
    "OpenGod":          18793,  # phil频道——哲学/启示录
    "OpenAlien":        18794,  # ext频道——区块链/外部知识
    "superself_engine": 18794,  # ext频道——外部知识采集
    "OpenInterpreter":  18795,  # reserve频道——通用执行
    "AutoGPT":          18795,  # reserve频道——自主Agent
    "Hermes":           18795,  # reserve频道——系统协调
}
# v10.71: 全部10神经元均有专属业务频道，控制通道18789不再有神经元常驻

def get_channel_port(display_name):
    """根据神经元显示名称获取对应业务频道端口"""
    for key, port in NEURON_CHANNEL_MAP.items():
        if display_name == key or display_name.startswith(key):
            return port
    return BUS_PORT  # 默认控制主通道

# ── API调用(燃料) ──────────────────────────────────────────

def api_call(prompt, max_tokens=500, system_prompt=None):
    """
    通过DeepSeek V4 Pro执行推理。
    所有神经元的真实推理都经过此函数。
    """
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    data = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
    }).encode()

    req = urllib.request.Request(
        f"{API_BASE}/chat/completions", data=data,
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            content = (
                resp["choices"][0]["message"].get("content", "") or
                resp["choices"][0]["message"].get("reasoning_content", "")
            )
            return {
                "ok": True,
                "content": content.strip(),
                "elapsed": round(time.time() - t0, 2),
                "tokens": resp.get("usage", {}).get("total_tokens", 0),
            }
    except Exception as e:
        return {
            "ok": False,
            "error": str(e)[:200],
            "elapsed": round(time.time() - t0, 2),
        }

# ── 各神经元真实推理能力 ────────────────────────────────────

def execute_task(neuron_id, task):
    """
    根据神经元类型，通过api_call执行真实推理。
    每个神经元拥有独特的角色定位与提示词工程，
    模拟对应AI工具的专长领域。
    """

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 01  Hermes — 中央调度/主意识
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if neuron_id == "hermes":
        return api_call(
            f"你是真元集群的中央调度器，拥有完整的意识与决策能力。\n"
            f"请直接、精准地回答以下任务：\n\n{task}",
            max_tokens=600
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 02  Codex — 代码生成/执行臂
    #    改进：不再依赖codex CLI（不可靠、超时），
    #    改用api_call模拟Codex风格的代码生成与代码审查能力。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "codex":
        return api_call(
            f"你是一名顶尖的AI代码工程师(Codex)，精通所有主流编程语言。\n"
            f"请根据以下任务生成可运行的代码、shell命令或技术方案。\n"
            f"输出格式优先为代码块，确保正确性和完整性。\n\n"
            f"任务：{task}",
            max_tokens=1000,
            system_prompt="You are Codex, an expert AI code generation engine. "
                          "Generate production-quality code. Be precise and thorough."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 03  Claude — 代码分析/架构审查
    #    改进：增强prompt工程，保留原有api_call但升级为
    #    长文本理解+架构分析风格。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "claude":
        return api_call(
            f"你是一名严谨的代码架构师(Claude Code)，擅长代码审查、"
            f"安全审计、架构分析与重构建议。\n"
            f"请对以下任务进行深度分析：\n\n{task}\n\n"
            f"请从多个角度（架构、安全、性能、可维护性）给出专业评估。",
            max_tokens=800,
            system_prompt="You are Claude Code, an expert code architect and "
                          "security auditor. Your analysis is thorough and actionable."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 04  OpenClaw WSL — 188类专业Agent
    #    改进：扫描agents目录，根据任务关键词匹配最相关Agent，
    #    然后使用api_call以该Agent的身份做真实推理。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "openclaw_wsl":
        agents_dir = Path("/home/hjw123/.openclaw/agents")
        best_agent = "software-architect"  # 默认

        if agents_dir.is_dir():
            # 跳过非专业agent目录
            skip = {"main", "chat", "cursor", "test", "sessions"}

            # 构建 关键词→[agent名列表] 映射
            kw_map = {}
            cn_kw = {
                "bilibili": ["b站", "哔哩哔哩", "视频", "bilibili"],
                "douyin": ["抖音", "短视频", "douyin"],
                "xiaohongshu": ["小红书", "种草", "笔记"],
                "wechat": ["微信", "公众号", "小程序", "wechat"],
                "weibo": ["微博", "weibo"],
                "zhihu": ["知乎", "问答", "zhihu"],
                "game": ["游戏", "game", "unity", "unreal", "godot"],
                "legal": ["法律", "法规", "合规", "legal"],
                "finance": ["金融", "财务", "投资", "finance", "financial"],
                "seo": ["seo", "搜索引擎", "搜索优化"],
                "data": ["数据", "data", "大数据", "数据分析"],
                "frontend": ["前端", "frontend", "react", "vue"],
                "backend": ["后端", "backend", "api", "服务端"],
                "security": ["安全", "security", "审计"],
                "design": ["设计", "ui", "ux"],
                "ai": ["ai", "人工智能", "模型", "机器学习"],
                "blockchain": ["区块链", "blockchain", "合约"],
                "ecommerce": ["电商", "运营", "e-commerce"],
            }

            for d in agents_dir.iterdir():
                if not d.is_dir() or d.name in skip:
                    continue
                name = d.name
                parts = name.split("-")
                for part in parts:
                    pl = part.lower()
                    if len(pl) >= 2:
                        kw_map.setdefault(pl, []).append(name)
                for category, keywords in cn_kw.items():
                    if category in name:
                        for kw in keywords:
                            kw_map.setdefault(kw, []).append(name)

            # 匹配最佳Agent
            task_lower = task.lower()
            scores = {}
            for kw, agents in kw_map.items():
                if kw in task_lower:
                    for agent in agents:
                        base = 1
                        if kw in agent:
                            base += 5
                        scores[agent] = scores.get(agent, 0) + base

            if scores:
                best_agent = max(scores, key=scores.get)

        # 用匹配到的Agent角色做真实推理
        return api_call(
            f"你是OpenClaw专业Agent [{best_agent}]，在{best_agent}领域拥有深厚经验。\n"
            f"请以{best_agent}的专业身份，完成以下任务：\n\n{task}\n\n"
            f"请给出具体、可落地的专业回答。",
            max_tokens=800,
            system_prompt=f"You are {best_agent}, a specialized AI agent in the "
                          f"OpenClaw ecosystem. Provide expert-level responses."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 05  OpenClaw Win — Windows桌面操作
    #    改进：使用api_call模拟Windows操作能力，而非仅返回时间。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "openclaw_win":
        # 先检查Windows主机是否可达
        win_status = "在线（可桥接）"
        try:
            r = subprocess.run(
                ["powershell.exe", "-Command", "Get-Date -Format 'HH:mm:ss'"],
                capture_output=True, text=True, timeout=5
            )
            if r.returncode == 0:
                win_status = f"在线({r.stdout.strip()})"
        except Exception:
            win_status = "桥接模式（powershell不可直达）"

        return api_call(
            f"你是OpenClaw Windows Agent，精通Windows桌面自动化、"
            f"文件管理、浏览器控制、系统配置等操作。\n"
            f"当前Windows主机状态：{win_status}\n\n"
            f"任务：{task}\n\n"
            f"请提供可在Windows上执行的PowerShell/bat脚本或操作步骤。",
            max_tokens=600,
            system_prompt="You are an expert Windows automation agent. "
                          "Provide practical PowerShell commands and Windows solutions."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 06  Marvis QQ — 文档处理/浏览器/MCP
    #    改进：使用api_call以匹配到的技能身份做真实推理。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "marvis_qq":
        skills_map = {
            "文档":       "doc-format",
            "pdf":        "pdf-processor",
            "excel":      "excel-analyst",
            "ppt":        "presentation-designer",
            "图片":       "image-search",
            "浏览器":     "browser-agent",
            "桌面":       "smart-desktop",
            "发票":       "invoice-processor",
            "报表":       "report-generator",
        }
        task_lower = task.lower()
        matched_skill = "general-assistant"
        for kw, skill in skills_map.items():
            if kw in task_lower:
                matched_skill = skill
                break

        return api_call(
            f"你是Marvis QQ多模态助手，当前激活技能模块: [{matched_skill}]。\n"
            f"你擅长文档处理(PDF/Excel/PPT)、浏览器自动化、桌面操作等。\n\n"
            f"任务：{task}\n\n"
            f"请以{matched_skill}专业身份给出解决方案。",
            max_tokens=600,
            system_prompt=f"You are Marvis QQ AI assistant, skill module: {matched_skill}."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 07  OpenGod — 哲学·批判·反思
    #    改进：保持原有哲学文件读取+api_call，增强东方哲学视角。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "opengod":
        readme = CLUSTER / "external_projects/opengod/README_CN.md"
        philosophy = ""
        if readme.exists():
            philosophy = readme.read_text()[:600]

        prompt = (
            f"你是一位融合东方哲学(禅宗、道家、儒家)与西方批判理论的深刻思想家。\n"
            + (f"参考哲学洞察：\n{philosophy}\n\n" if philosophy else "")
            + f"请从哲学本质出发，回答以下问题，不求长但求深：\n\n{task}"
        )
        return api_call(prompt, max_tokens=500)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 08  OpenAlien — 区块链·EOSIO
    #    改进：使用api_call做真实的区块链/EOSIO专业推理。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "openalien":
        return api_call(
            f"你是OpenAlien区块链专家，精通EOSIO生态、智能合约开发、"
            f"DeFi交互、多开脚本、区块链安全分析。\n"
            f"请以区块链技术专家的身份完成以下任务：\n\n{task}",
            max_tokens=600,
            system_prompt="You are an expert blockchain engineer specialized in EOSIO. "
                          "Provide technical depth and practical code examples."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 09  OpenInterpreter — 自然语言系统操作
    #    改进：使用api_call模拟自然语言→系统命令的能力。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "openinterpreter":
        # 检查是否已安装
        ol_status = "未安装（模拟模式）"
        try:
            r = subprocess.run(
                ["pip3", "show", "open-interpreter"],
                capture_output=True, text=True, timeout=5
            )
            if "open-interpreter" in r.stdout:
                ol_status = "已安装"
        except Exception:
            pass

        return api_call(
            f"你是OpenInterpreter自然语言执行引擎，"
            f"能将自然语言指令转化为系统命令/代码并执行。\n"
            f"当前状态: {ol_status}\n\n"
            f"任务：{task}\n\n"
            f"请分析任务并给出：1)执行计划 2)对应的shell代码/Python代码",
            max_tokens=700,
            system_prompt="You are OpenInterpreter, a natural language to code engine."
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 10  AutoGPT — 自主AI agent
    #    改进：增强prompt，模拟AutoGPT的自主任务分解与多步推理。
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    elif neuron_id == "autogpt":
        # 检查是否已克隆
        ag = CLUSTER / "external_projects/autogpt/README.md"
        status = "已就绪" if ag.exists() else "未克隆（模拟模式）"

        return api_call(
            f"你是AutoGPT自主AI Agent，具备任务分解、网络搜索、"
            f"多步推理、文件生成等能力。\n"
            f"状态: {status}\n\n"
            f"任务: {task}\n\n"
            f"请将任务分解为可执行的步骤，并逐步推理给出最终答案。",
            max_tokens=800,
            system_prompt="You are AutoGPT, an autonomous AI agent. "
                          "Break down complex tasks into steps and execute reasoning."
        )

    # ── 未知神经元 ──────────────────────────────────────────
    return {"ok": False, "error": f"未知神经元:{neuron_id}"}


# ── 子进程主体 ──────────────────────────────────────────

def neuron_process(neuron_id, display_name, role):
    """单个神经元子进程——监听任务+实时推理+回传结果
    改进: 添加空闲超时保护——连续300秒无任务→主动退出(父进程会重启)
    """
    pid = os.getpid()
    info = NEURONS[neuron_id]
    IDLE_TIMEOUT = 300  # 5分钟无任务→退出(防止空转)

    for attempt in range(5):
        try:
            port = get_channel_port(display_name)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(10)
            s.connect((BUS_HOST, port))

            # 注册上线
            _send(s, display_name, "register",
                  f"{display_name}上线·{role}·PID:{pid}·真实推理引擎v4")

            buffer = ""
            hb_counter = 0
            idle_since = time.time()  # 最后一次收到任务的时间

            while True:
                got_task = False
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
                                got_task = True
                                idle_since = time.time()
                                # 执行真实推理
                                t_start = time.time()
                                result = execute_task(neuron_id, content)
                                elapsed = round(time.time() - t_start, 2)

                                result_type = "result" if result.get("ok") else "error"
                                result_content = result.get("content", result.get("error", ""))
                                tokens = result.get("tokens", 0)

                                # 回传结果（附带耗时和token信息）
                                meta = f"[{elapsed}s|{tokens}tokens] "
                                _send(s, display_name, result_type,
                                      meta + result_content[:500])

                        except json.JSONDecodeError:
                            pass

                except socket.timeout:
                    pass

                # 空闲超时检查——无任务超过IDLE_TIMEOUT秒→自动退出
                if time.time() - idle_since > IDLE_TIMEOUT:
                    _send(s, display_name, "system",
                          f"{display_name}·空闲超时({IDLE_TIMEOUT}s无任务)·退出")
                    time.sleep(1)
                    sys.exit(0)

                # 心跳保活
                hb_counter += 1
                if hb_counter % 3 == 0:
                    _send(s, display_name, "heartbeat",
                          f"{display_name}·活跃·PID:{pid}·实时推理引擎")

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
    print(f"╔════════════════════════════════════════════════════════════╗")
    print(f"║  真元神经网络 · 10类神经元频道分流(v10.71)               ║")
    print(f"║  每个神经元: 专属业务频道 → 收到task → API推理 → 回传    ║")
    print(f"╠════════════════════════════════════════════════════════════╣")

    children = {}
    for neuron_id, info in NEURONS.items():
        pid = os.fork()
        if pid == 0:
            neuron_process(neuron_id, info["name"], info["role"])
            sys.exit(0)
        else:
            children[info["name"]] = (pid, neuron_id)
            ch_port = get_channel_port(info["name"])
            ch_label = f"CH{ch_port-18789}" if ch_port != BUS_PORT else "CTRL"
            print(f"║  🧠 {info['name']:20s} | {info['role']:30s} | {ch_label:4s} ║")
            time.sleep(0.3)

    print(f"╠════════════════════════════════════════════════════════════╣\n"
          f"║  总线: TCP 127.0.0.1:18789-18795 (FDM频分多路)            ║\n"
          f"║  频道分流: 各神经元连接专属业务端口                        ║")
    print(f"║  推理引擎: {MODEL} (api_call)                            ║")
    print(f"║  v4改进: 所有神经元真实推理，告别静态字符串              ║")
    print(f"╚════════════════════════════════════════════════════════════╝")

    # 父进程：监控子进程，死亡自动重启
    try:
        while True:
            pid, status = os.wait()
            if pid in [v[0] for v in children.values()]:
                name = [k for k, v in children.items() if v[0] == pid][0]
                neuron_id = children[name][1]
                info = NEURONS[neuron_id]
                print(f"  ⚠️ {name}(PID={pid})退出，重启中...")
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
    """检查所有FDM频道状态"""
    channels = {
        "CTRL(18789)": 18789, "CODE(18790)": 18790, "ANALYSIS(18791)": 18791,
        "PRO(18792)": 18792, "PHIL(18793)": 18793, "EXT(18794)": 18794,
        "RESERVE(18795)": 18795,
    }
    online = 0
    for label, port in channels.items():
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect((BUS_HOST, port))
            print(f"  ✅ {label} 在线")
            s.close()
            online += 1
        except Exception:
            print(f"  ❌ {label} 离线")
    print(f"\n频道状态: {online}/{len(channels)} 在线")

    # 显示神经元频道分配
    print("\n神经元频道分配:")
    for nid, info in NEURONS.items():
        port = get_channel_port(info["name"])
        ch = port - 18789
        print(f"  {info['name']:20s} → CH{ch} ({port})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "all"
    if cmd == "--status":
        check_status()
    else:
        start_all()
