#!/usr/bin/env python3
"""
neural_cluster.py — 真元神经网络集群核心协调器
===============================================
不是注册表。不是文件总线。是活的神经网络。

10类Agent = 10种神经元类型。
任务进来 → 协调器分析 → 路由到最优Agent组合 → 并行执行 → 结果汇聚 → 写入记忆。

用法:
  python3 neural_cluster.py "你的任务描述"
  python3 neural_cluster.py --status
  python3 neural_cluster.py --test   # 运行全集群连通性测试
"""
import json, os, sys, time, subprocess, concurrent.futures, select, re
from datetime import datetime
from pathlib import Path

# PTY支持：用于codex等需要终端的CLI工具
import pty, fcntl, termios, struct

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

# ── Agent能力图谱 ──────────────────────────────────────────

AGENT_CAPABILITIES = {
    "hermes": {
        "can": ["调度", "决策", "记忆", "进化", "哲学思考", "API调用"],
        "executor": "direct",  # 当前进程直接执行
        "latency": 0,
        "reliability": 1.0,
    },
    "codex": {
        "can": ["代码生成", "文件操作", "git操作", "shell命令", "代码审查"],
        "executor": "cli",
        "cmd": "codex exec --model deepseek-v4-pro --",
        "latency": 30,
        "reliability": 0.7,
    },
    "claude": {
        "can": ["代码分析", "架构审查", "长文本理解", "安全审计"],
        "executor": "cli",
        "cmd": "claude -p",
        "latency": 20,
        "reliability": 0.3,  # auth问题
    },
    "openclaw_wsl": {
        "can": ["专业领域188类", "中文优化", "bilibili", "微信", "小红书", "抖音",
                "游戏开发", "法律", "金融", "SEO", "数据分析", "前端", "后端"],
        "executor": "node_bridge",
        "bridge": "/home/hjw123/.openclaw/branch-session-bridge.js",
        "latency": 15,
        "reliability": 0.8,
    },
    "openclaw_win": {
        "can": ["Windows操作", "桌面自动化", "文件管理", "浏览器控制"],
        "executor": "wsl_bridge",
        "latency": 10,
        "reliability": 0.6,
    },
    "marvis_qq": {
        "can": ["文档处理", "PDF", "Excel", "PPT", "图片搜索",
                "浏览器操作", "手机控制", "桌面操作", "发票", "报表"],
        "executor": "mcp",
        "latency": 15,
        "reliability": 0.5,
    },
    "opengod": {
        "can": ["哲学反思", "AI批判", "去浮躁", "本质洞察"],
        "executor": "file_read",
        "file": "external_projects/opengod/README_CN.md",
        "latency": 0,
        "reliability": 1.0,
    },
    "openalien": {
        "can": ["区块链", "EOSIO", "自动合约", "多开脚本"],
        "executor": "python",
        "latency": 5,
        "reliability": 0.4,
    },
    "openinterpreter": {
        "can": ["自然语言执行", "系统操作", "文件处理", "代码运行"],
        "executor": "pip_install",
        "latency": 10,
        "reliability": 0.0,  # 未安装
    },
    "autogpt": {
        "can": ["自主任务", "多步推理", "网络搜索", "文件生成"],
        "executor": "git_install",
        "latency": 30,
        "reliability": 0.0,  # 未安装
    },
    "superpowers": {
        "can": ["软件开发方法论", "头脑风暴设计", "方案规划", "子代理驱动开发",
                "TDD测试驱动", "代码审查", "Git工作树", "系统调试", "并行代理调度"],
        "executor": "cli",
        "cmd": "codex exec --model deepseek-v4-pro --",
        "latency": 10,
        "reliability": 0.85,
    },
    "codegraph": {
        "can": ["代码知识图谱", "语义搜索", "调用链分析", "影响分析",
                "AST解析", "代码结构探索", "MCP服务", "代码导航"],
        "executor": "cli",
        "cmd": "codegraph serve --mcp",
        "latency": 5,
        "reliability": 0.9,
    },
    "academic_research": {
        "can": ["深度学术研究", "论文写作", "同行评审", "文献搜索",
                "学术诚信验证", "LaTeX格式化", "引用管理", "研究流程调度"],
        "executor": "cli",
        "cmd": "claude -p",
        "latency": 20,
        "reliability": 0.75,
    },
    "ruview": {
        "can": ["WiFi感知", "人体检测", "生命体征监测", "穿墙感知",
                "姿态估计", "边缘AI", "跌倒检测", "睡眠监测", "呼吸心率"],
        "executor": "python",
        "latency": 5,
        "reliability": 0.6,
    },
}

# ── API调用(燃料) ──────────────────────────────────────────

def api_call(prompt, max_tokens=400):
    """通过DeepSeek V4 Pro执行推理"""
    import urllib.request, urllib.error
    from api_config import API_KEY, API_BASE, MODEL
    data = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
    }).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"].get("content", "") or resp["choices"][0]["message"].get("reasoning_content", "")
            return {"ok": True, "content": content, "elapsed": round(time.time()-t0,2),
                    "tokens": resp.get("usage",{}).get("total_tokens",0)}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "elapsed": round(time.time()-t0,2)}

# ── 任务路由 ──────────────────────────────────────────────

def route_task(task_description):
    """
    分析任务，决定由哪些Agent执行。
    返回 [(agent_name, subtask, priority), ...]
    """
    # 用API做智能路由
    agents_desc = "\n".join([
        f"- {name}: 能力={','.join(info['can'][:5])} 可靠性={info['reliability']}"
        for name, info in AGENT_CAPABILITIES.items()
    ])

    prompt = f"""你是真元神经网络集群的任务路由器。
给定任务和Agent能力图谱，决定最佳执行方案。

任务: {task_description}

可用Agent:
{agents_desc}

规则:
1. 可以选1-3个Agent
2. 每个Agent分配一个具体子任务
3. 优先选可靠性高的
4. 如果任务需要多个能力，组合多个Agent

输出JSON数组: [{{"agent":"名称","subtask":"子任务描述","reason":"选择原因"}}]
只输出JSON，不要其他文字。"""

    result = api_call(prompt, max_tokens=300)
    if result["ok"]:
        try:
            content = result["content"]
            # 提取JSON
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                routes = json.loads(content[start:end])
                return routes
        except Exception:
            pass

    # 回退：关键词匹配
    task_lower = task_description.lower()
    routes = []
    if any(k in task_lower for k in ["代码", "python", "文件", "git", "修改"]):
        routes.append({"agent": "codex", "subtask": task_description, "reason": "代码任务"})
    if any(k in task_lower for k in ["分析", "审查", "架构", "安全"]):
        routes.append({"agent": "claude", "subtask": task_description, "reason": "分析任务"})
    if any(k in task_lower for k in ["文档", "pdf", "excel", "ppt"]):
        routes.append({"agent": "marvis_qq", "subtask": task_description, "reason": "文档任务"})
    if not routes:
        routes.append({"agent": "hermes", "subtask": task_description, "reason": "默认执行"})
    return routes

# ── Agent执行器 ──────────────────────────────────────────

def execute_on_agent(agent_name, subtask):
    """在指定Agent上执行子任务（大小写不敏感）"""
    # 大小写不敏感匹配
    name = agent_name.lower()
    info = AGENT_CAPABILITIES.get(name, {})
    if not info:
        # 尝试匹配别名
        alias_map = {k.lower(): k for k in AGENT_CAPABILITIES}
        name = alias_map.get(name, name)
        info = AGENT_CAPABILITIES.get(name, {})
    executor = info.get("executor", "unknown")

    if executor == "direct":
        # Hermes直接用API执行
        return api_call(subtask, max_tokens=500)

    elif executor == "cli":
        # 使用PTY模式执行CLI工具（如codex），避免script包装
        cmd = info.get("cmd", "")
        try:
            # 创建PTY主从对
            master_fd, slave_fd = pty.openpty()
            # 设置PTY窗口大小（宽200行x高50列）
            winsize = struct.pack("HHHH", 50, 200, 0, 0)
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)

            # 准备环境变量
            env = {**os.environ, "CODEX_SKIP_STDIN_CHECK": "1"}

            # 通过PTY启动子进程
            child_pid = os.fork()
            if child_pid == 0:
                # 子进程：关闭主端，重定向stdio到从端
                os.close(master_fd)
                os.dup2(slave_fd, 0)  # stdin
                os.dup2(slave_fd, 1)  # stdout
                os.dup2(slave_fd, 2)  # stderr
                if slave_fd > 2:
                    os.close(slave_fd)
                # 设置新会话（脱离终端）
                os.setsid()
                os.chdir(str(CLUSTER))
                os.execvpe("bash", ["bash", "-c",
                    f'{cmd} "{subtask}"'], env)
                os._exit(1)

            # 父进程：关闭从端，从主端读取输出
            os.close(slave_fd)

            # 非阻塞读取，带超时
            output_parts = []
            deadline = time.time() + 60  # 60秒总超时

            # 设置非阻塞
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            while time.time() < deadline:
                try:
                    # 等待数据可读（最多1秒）
                    ready, _, _ = select.select([master_fd], [], [], 1.0)
                    if ready:
                        data = os.read(master_fd, 4096)
                        if data:
                            output_parts.append(data.decode("utf-8", errors="replace"))
                        else:
                            break  # EOF
                except OSError:
                    break  # 管道关闭
                # 检查子进程是否已退出
                try:
                    pid, status = os.waitpid(child_pid, os.WNOHANG)
                    if pid != 0:
                        # 子进程已退出，读取剩余输出
                        time.sleep(0.2)
                        try:
                            while True:
                                ready, _, _ = select.select([master_fd], [], [], 0.5)
                                if ready:
                                    data = os.read(master_fd, 4096)
                                    if data:
                                        output_parts.append(data.decode("utf-8", errors="replace"))
                                    else:
                                        break
                                else:
                                    break
                        except Exception:
                            pass
                        break
                except ChildProcessError:
                    break

            os.close(master_fd)

            # 清理子进程（如果还在运行）
            try:
                os.kill(child_pid, 9)
                os.waitpid(child_pid, 0)
            except (ProcessLookupError, ChildProcessError):
                pass

            # 处理输出：过滤PTY控制序列和无用信息
            raw_output = "".join(output_parts)
            # 移除ANSI转义序列
            clean = re.sub(r'\x1b\[[^a-zA-Z]*[a-zA-Z]', '', raw_output)
            # 移除VT100控制字符
            clean = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', clean)
            lines = [l for l in clean.split("\n") if l.strip()
                     and not any(x in l for x in ["Reading", "OpenAI Codex",
                     "workdir:", "model:", "provider:", "approval:",
                     "sandbox:", "reasoning", "session id", "tokens used",
                     "OutputTextDelta", "^M", "\x07"])]
            content = "\n".join(lines[-15:])[:500]
            return {"ok": True, "content": content or "(无输出)", "elapsed": 0, "agent": agent_name}
        except Exception as e:
            return {"ok": False, "error": str(e)[:200], "agent": agent_name}

    elif executor == "node_bridge":
        # OpenClaw WSL：扫描agents目录，根据任务关键词匹配最相关的专业Agent
        openclaw_agents_dir = Path("/home/hjw123/.openclaw/agents")
        bridge_js = info.get("bridge", "")

        # 构建Agent能力映射：从目录名解析专业领域
        # 目录名格式如：backend-architect, bilibili-content-strategist
        _agent_keyword_cache = None

        def _build_agent_keyword_map():
            """扫描agents目录，构建 关键词→Agent名 的映射表"""
            nonlocal _agent_keyword_cache
            if _agent_keyword_cache is not None:
                return _agent_keyword_cache

            kw_map = {}
            # 跳过这些非专业agent目录
            skip = {"main", "chat", "cursor", "test", "sessions"}

            if openclaw_agents_dir.is_dir():
                for d in openclaw_agents_dir.iterdir():
                    if not d.is_dir() or d.name in skip:
                        continue
                    name = d.name
                    # 从目录名提取关键词（拆分连字符）
                    parts = name.split("-")
                    for part in parts:
                        part_lower = part.lower()
                        if len(part_lower) >= 2:
                            kw_map.setdefault(part_lower, []).append(name)

                    # 为常见中文领域添加映射关键词
                    cn_kw = {
                        "bilibili": ["b站", "哔哩哔哩", "视频", "bilibili"],
                        "douyin": ["抖音", "短视频", "douyin"],
                        "xiaohongshu": ["小红书", "种草", "笔记"],
                        "wechat": ["微信", "公众号", "小程序", "wechat"],
                        "weibo": ["微博", "weibo"],
                        "zhihu": ["知乎", "问答", "zhihu"],
                        "kuaishou": ["快手", "kuaishou"],
                        "baidu": ["百度", "baidu"],
                        "tiktok": ["tiktok", "海外短视频"],
                        "game": ["游戏", "game", "unity", "unreal", "godot", "roblox"],
                        "legal": ["法律", "法规", "合规", "legal"],
                        "finance": ["金融", "财务", "投资", "finance", "financial", "投资分析"],
                        "seo": ["seo", "搜索引擎", "搜索优化"],
                        "data": ["数据", "data", "大数据", "数据工程", "数据管道"],
                        "frontend": ["前端", "frontend", "react", "vue"],
                        "backend": ["后端", "backend", "api", "服务端"],
                        "security": ["安全", "security", "审计"],
                        "design": ["设计", "设计", "ui", "ux"],
                        "sales": ["销售", "sales", "营销"],
                        "content": ["内容", "文案", "content"],
                        "ai": ["ai", "人工智能", "模型", "机器学习"],
                        "blockchain": ["区块链", "blockchain", "合约"],
                        "e-commerce": ["电商", "运营", "e-commerce"],
                        "crypto": ["加密", "web3", "defi"],
                    }
                    for category, keywords in cn_kw.items():
                        if category in name:
                            for kw in keywords:
                                kw_map.setdefault(kw, []).append(name)

            _agent_keyword_cache = kw_map
            return kw_map

        def _match_agent(task_text):
            """根据任务文本匹配最佳Agent"""
            kw_map = _build_agent_keyword_map()
            task_lower = task_text.lower()

            # 统计每个agent的匹配分数
            scores = {}
            matched_kws = []
            # 通用角色后缀：任务泛化时优先匹配这类agent
            general_roles = {"architect", "designer", "developer", "engineer",
                           "optimizer", "strategist", "specialist"}

            for kw, agents in kw_map.items():
                if kw in task_lower:
                    matched_kws.append(kw)
                    for agent in agents:
                        # 基础分：关键词出现在任务中
                        base = 1
                        # 加分：如果关键词直接出现在agent目录名中（更精确匹配）
                        if kw in agent:
                            base += 5
                        # 加分：如果agent包含通用角色名（优先匹配通用角色agent）
                        agent_parts = set(agent.split("-"))
                        if agent_parts & general_roles:
                            base += 2
                        scores[agent] = scores.get(agent, 0) + base

            if scores:
                # 按分数排序，返回最佳匹配
                best = max(scores, key=scores.get)
                return best, matched_kws, scores[best]

            # 无匹配时返回默认agent（software-architect）
            default = "software-architect" if (openclaw_agents_dir / "software-architect").is_dir() else "main"
            return default, [], 0

        try:
            # 匹配最相关的Agent
            best_agent, matched_keywords, score = _match_agent(subtask)

            # 将任务写入workspace + agent特定session
            task_file = Path("/home/hjw123/.openclaw/workspace/cluster_tasks.json")
            tasks = []
            if task_file.exists():
                try:
                    tasks = json.loads(task_file.read_text())
                except Exception:
                    tasks = []

            task_id = f"neural_{int(time.time())}"
            tasks.append({
                "id": task_id,
                "content": subtask,
                "source": "zhenyuan_neural_cluster",
                "timestamp": datetime.now().isoformat(),
                "status": "pending",
                "matched_agent": best_agent,
                "matched_keywords": matched_keywords,
                "match_score": score,
            })
            task_file.parent.mkdir(parents=True, exist_ok=True)
            task_file.write_text(json.dumps(tasks, ensure_ascii=False, indent=2))

            # 构建结果信息
            agent_count = len([d for d in openclaw_agents_dir.iterdir()
                             if d.is_dir() and d.name not in ("main", "chat", "cursor", "test", "sessions")])
            info_msg = (f"任务已路由至专业Agent [{best_agent}] "
                       f"(匹配关键词: {','.join(matched_keywords[:3]) if matched_keywords else '默认'}) "
                       f"总Agent库: {agent_count}个")

            return {"ok": True, "content": info_msg,
                    "elapsed": 0, "agent": agent_name,
                    "matched_agent": best_agent,
                    "agent_count": agent_count}
        except Exception as e:
            return {"ok": False, "error": f"OpenClaw路由失败: {str(e)[:200]}", "agent": agent_name}

    elif executor == "file_read":
        # OpenGod: 读取哲学文件作为上下文
        fpath = CLUSTER / info.get("file", "")
        if fpath.exists():
            content = fpath.read_text()[:1000]
            # 结合任务做哲学分析
            prompt = f"基于以下哲学洞察:\n{content}\n\n回答问题: {subtask}"
            return api_call(prompt, max_tokens=300)
        return {"ok": False, "error": "哲学文件不存在"}

    elif executor in ("pip_install", "git_install"):
        return {"ok": False, "error": f"{agent_name} 未安装，请先安装"}

    elif executor == "mcp":
        # Marvis: 检查进程
        try:
            r = subprocess.run(["pgrep", "-f", "MarvisAgent"], capture_output=True, text=True, timeout=3)
            if r.stdout.strip():
                return {"ok": True, "content": f"Marvis QQ在线(PID={r.stdout.strip()}), 子任务已分发: {subtask[:80]}"}
            return {"ok": False, "error": "Marvis QQ未运行"}
        except Exception:
            return {"ok": False, "error": "Marvis检测失败"}

    elif executor == "wsl_bridge":
        return {"ok": True, "content": f"Windows任务已记录: {subtask[:80]}", "agent": agent_name}

    return {"ok": False, "error": f"未知执行器: {executor}"}

# ── 集群协调 ──────────────────────────────────────────────

def execute_cluster_task(task_description):
    """
    完整的集群任务执行流程:
    1. 路由 → 2. 并行执行 → 3. 汇聚 → 4. 记忆
    """
    print(f"\n{'='*60}")
    print(f"  真元神经集群 · 任务执行")
    print(f"  {task_description[:50]}...")
    print(f"{'='*60}")

    # 1. 路由
    print(f"\n[1/4] 路由分析...")
    routes = route_task(task_description)
    for r in routes:
        print(f"  → {r.get('agent','?')}: {r.get('subtask','?')[:60]}")

    # 2. 并行执行
    print(f"\n[2/4] 并行执行 ({len(routes)}个Agent)...")
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(routes)) as executor:
        futures = {}
        for route in routes:
            agent = route.get("agent", "hermes")
            subtask = route.get("subtask", task_description)
            f = executor.submit(execute_on_agent, agent, subtask)
            futures[f] = route

        for f in concurrent.futures.as_completed(futures):
            route = futures[f]
            result = f.result()
            agent = route.get("agent", "?")
            if result.get("ok"):
                print(f"  ✅ {agent}: {result.get('content','')[:80]}...")
            else:
                print(f"  ❌ {agent}: {result.get('error','?')[:80]}")
            result["agent"] = agent
            results.append(result)

    # 3. 汇聚
    print(f"\n[3/4] 结果汇聚...")
    ok_results = [r for r in results if r.get("ok")]
    fail_results = [r for r in results if not r.get("ok")]
    print(f"  成功: {len(ok_results)}  失败: {len(fail_results)}")

    # 4. 写入记忆
    print(f"\n[4/4] 写入海马体记忆...")
    hip_path = CLUSTER / "hippocampus_memory.json"
    try:
        hip = json.loads(hip_path.read_text())
    except Exception:
        hip = {"causal_chains": []}

    for r in ok_results:
        hip["causal_chains"].append({
            "content": f"[集群任务] {task_description[:100]} → {r.get('content','')[:200]}",
            "source": f"neural_cluster:{r.get('agent','?')}",
            "tags": ["集群协同", r.get("agent","?"), "外部世界"],
            "timestamp": datetime.now().isoformat(),
            "tokens": r.get("tokens", 0),
        })
    hip_path.write_text(json.dumps(hip, ensure_ascii=False, indent=2))
    print(f"  已写入 {len(ok_results)} 条因果链")

    return {
        "task": task_description,
        "routes": routes,
        "results": results,
        "success": len(ok_results),
        "fail": len(fail_results),
    }

# ── CLI入口 ──────────────────────────────────────────────

def show_status():
    """显示集群状态"""
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  真元神经网络集群 · 神经元状态                              ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    for name, info in AGENT_CAPABILITIES.items():
        can = ", ".join(info["can"][:4])
        rel = info["reliability"]
        icon = "🟢" if rel >= 0.7 else "🟡" if rel >= 0.3 else "🔴"
        print(f"║ {icon} {name:18s} | {can:40s} | 可靠:{rel:.0%}  ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    try:
        hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        chains = len(hip.get("causal_chains", []))
        real = len([c for c in hip.get("causal_chains", []) if "集群协同" in str(c.get("tags", []))])
        print(f"║  记忆: {chains}条因果链  集群协同:{real}条                      ║")
    except Exception:
        pass
    print("╚══════════════════════════════════════════════════════════════╝")

def test_connectivity():
    """测试所有Agent连通性"""
    print("集群连通性测试:")
    for name, info in AGENT_CAPABILITIES.items():
        result = execute_on_agent(name, "测试连通性，请回复ok")
        icon = "✅" if result.get("ok") else "❌"
        print(f"  {icon} {name}: {result.get('content', result.get('error','?'))[:60]}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: neural_cluster.py '任务描述' | --status | --test")
        sys.exit(0)

    if sys.argv[1] == "--status":
        show_status()
    elif sys.argv[1] == "--test":
        test_connectivity()
    else:
        task = " ".join(sys.argv[1:])
        execute_cluster_task(task)
