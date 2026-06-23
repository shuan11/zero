#!/usr/bin/env python3
"""
neural_collaboration_orchestrator.py — FDM神经总线编排10神经元协作
==============================================================
通过频分多路(FDM)神经总线控制通道(18789)，向10个神经元发送任务并收集结果。
替代旧版 collaboration_loop.py 的 subprocess 调用模式。

架构:
  NeuralCollaborationOrchestrator
    ├── 连接控制通道 18789 (所有10神经元在此注册)
    ├── 通过路由转发到各业务频道:
    │   18790=Codex | 18791=Claude | 18792=OpenClaw/Marvis | 18793=OpenGod
    ├── 单任务模式: 定向一个神经元 → 等待结果
    ├── 协作模式: 多神经元并行 → 汇总到海马体
    └── 回退模式: 总线离线时直接API调用

用法:
  from neural_collaboration_orchestrator import NeuralCollaborationOrchestrator
  nco = NeuralCollaborationOrchestrator()
  # 单任务
  result = nco.single_task('codex', '分析这个项目的依赖结构')
  # 协作
  results = nco.collaborate('当前系统有什么架构缺口?')
  nco.disconnect()
"""

import json, os, sys, time, queue, threading, urllib.request, socket
from datetime import datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
#  常量
# ═══════════════════════════════════════════════════════════════

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_PATH = CLUSTER / "hippocampus_memory.json"
SYS_PATH = str(CLUSTER)

BUS_HOST = "127.0.0.1"
CONTROL_PORT = 18789
BUF_SIZE = 65536

# 频道端口定义（与 neural_bus_fdm.py 一致）
CHANNEL_PORTS = {
    "control":  18789,
    "code":     18790,
    "analysis": 18791,
    "pro":      18792,
    "phil":     18793,
    "ext":      18794,
}

# 神经元→频道映射（用于路由日志）
NEURON_CHANNEL_MAP = {
    "codex":          "code",
    "claude":         "analysis",
    "openclaw_wsl":   "pro",
    "openclaw_win":   "pro",
    "marvis_qq":      "pro",
    "opengod":        "phil",
    "openalien":      "control",
    "openinterpreter": "control",
    "autogpt":        "control",
    "hermes":         "control",
}

# 神经元ID → 总线显示名（必须与 neuron_daemon.py 的 NEURONS 字典一致）
DISPLAY_NAMES = {
    "hermes":          "Hermes",
    "codex":           "Codex CLI",
    "claude":          "Claude Code",
    "openclaw_wsl":    "OpenClaw WSL",
    "openclaw_win":    "OpenClaw Win",
    "marvis_qq":       "Marvis QQ",
    "opengod":         "OpenGod",
    "openalien":       "OpenAlien",
    "openinterpreter": "OpenInterpreter",
    "autogpt":         "AutoGPT",
}

# 显示名 → 神经元ID 反向映射
NAME_TO_ID = {v: k for k, v in DISPLAY_NAMES.items()}

# API配置
try:
    sys.path.insert(0, SYS_PATH)
    from api_config import API_KEY, API_BASE, MODEL
except Exception:
    API_KEY = os.environ.get("API_KEY", "")
    API_BASE = "https://inferaichat.com/v1"
    MODEL = "deepseek-v4-pro"


# ═══════════════════════════════════════════════════════════════
#  神经协作编排器
# ═══════════════════════════════════════════════════════════════

class NeuralCollaborationOrchestrator:
    """通过FDM神经总线编排10神经元协作的主编排器

    使用方式:
        nco = NeuralCollaborationOrchestrator()
        # 单任务
        r = nco.single_task('codex', '写一个冒泡排序')
        # 协作
        rs = nco.collaborate('系统架构如何优化?')
        nco.disconnect()
    """

    def __init__(self, host=BUS_HOST, port=CONTROL_PORT, default_timeout=90):
        self.host = host
        self.port = port
        self.default_timeout = default_timeout
        self._agent_name = "NeuralOrchestrator"

        # socket 和线程状态
        self.sock = None
        self._running = False
        self._connected = False
        self._lock = threading.Lock()

        # 消息队列: 后台监听线程把所有收到的消息放入此队列
        self._msg_queue = queue.Queue()
        self._listener_thread = None

        # 连接尝试计数
        self._connect_attempts = 0

    # ── 总线可用性检测 ─────────────────────────────────

    def check_bus(self):
        """检测FDM神经总线是否在线

        返回:
            True  = 18789端口可连接
            False = 总线离线
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect((self.host, self.port))
            s.close()
            return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def get_bus_status(self):
        """获取总线详细状态（各频道在线Agent数）

        返回:
            dict: 频道状态信息，失败时返回 {"error": "..."}
        """
        nbs = CLUSTER / "neural_bus_state.json"
        if nbs.exists():
            try:
                return json.loads(nbs.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"error": "bus state file not available"}

    # ── 连接管理 ───────────────────────────────────────

    def connect(self):
        """连接到FDM神经总线控制通道(18789)

        返回:
            True  = 连接成功
            False = 连接失败
        """
        if self._connected and self.sock:
            return True

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((self.host, self.port))
            self.sock.settimeout(None)  # 改为阻塞模式，由监听线程控制

            self._running = True
            self._connected = True
            self._connect_attempts = 0

            # 发送注册消息
            self._raw_send({
                "sender": self._agent_name,
                "target": "bus",
                "msg_type": "register",
                "content": f"{self._agent_name} 上线·协作编排器",
                "timestamp": datetime.now().isoformat(),
                "id": f"{int(time.time())}_{self._agent_name}",
            })

            # 启动后台监听线程
            self._listener_thread = threading.Thread(
                target=self._listener_loop, daemon=True,
                name="orchestrator-listener"
            )
            self._listener_thread.start()

            return True

        except Exception as e:
            self._connected = False
            self._connect_attempts += 1
            return False

    def disconnect(self):
        """断开与FDM总线的连接"""
        self._running = False
        self._connected = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def reconnect(self):
        """断线重连"""
        self.disconnect()
        time.sleep(1)
        return self.connect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    # ── 消息收发 ───────────────────────────────────────

    def _raw_send(self, msg_dict):
        """发送JSON消息到总线（低层方法）"""
        if not self.sock:
            return False
        try:
            data = json.dumps(msg_dict, ensure_ascii=False).encode() + b"\n"
            with self._lock:
                self.sock.sendall(data)
            return True
        except Exception:
            self._connected = False
            return False

    def send_task(self, target_name, content):
        """发送任务消息到指定神经元

        参数:
            target_name: 目标神经元显示名（如 "Codex CLI"）
            content:     任务内容字符串

        返回:
            True = 发送成功
        """
        return self._raw_send({
            "sender": self._agent_name,
            "target": target_name,
            "msg_type": "task",
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "id": f"{int(time.time()*1000)}_{self._agent_name}",
        })

    def _listener_loop(self):
        """后台线程：持续接收总线消息，放入队列"""
        buffer = ""
        while self._running and self._connected:
            try:
                data = self.sock.recv(BUF_SIZE)
                if not data:
                    break
                buffer += data.decode(errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        # 所有收到的消息入队列
                        self._msg_queue.put(msg)
                    except json.JSONDecodeError:
                        continue

            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
            except Exception:
                break

        self._connected = False
        # 如果仍在运行，尝试重连
        if self._running:
            time.sleep(3)
            if self.reconnect():
                print(f"  [编排器] 总线重连成功")

    def _wait_for_response(self, sender_names, timeout=None, collect_all=False):
        """等待来自指定发送者的响应

        参数:
            sender_names: 发送者名称列表或单个名称
            timeout:      超时秒数（默认 self.default_timeout）
            collect_all:  是否收集所有匹配响应（否则只收第一个）

        返回:
            单个响应dict或响应dict列表
        """
        if isinstance(sender_names, str):
            sender_names = [sender_names]

        timeout = timeout or self.default_timeout
        deadline = time.time() + timeout
        results = []
        seen_ids = set()

        while time.time() < deadline:
            try:
                # 非阻塞获取队列中的消息
                remaining = deadline - time.time()
                if remaining <= 0:
                    break
                msg = self._msg_queue.get(timeout=min(remaining, 1.0))

                msg_id = msg.get("id", "")
                msg_type = msg.get("msg_type", "")
                sender = msg.get("sender", "")

                # 去重
                if msg_id in seen_ids:
                    continue
                seen_ids.add(msg_id)

                # 只处理 result / error 类型
                if msg_type not in ("result", "error"):
                    continue

                # 检查发送者是否匹配
                if sender in sender_names:
                    result = {
                        "sender": sender,
                        "neuron_id": NAME_TO_ID.get(sender, sender),
                        "success": msg_type == "result",
                        "content": msg.get("content", ""),
                        "timestamp": msg.get("timestamp", ""),
                        "raw": msg,
                    }
                    if collect_all:
                        results.append(result)
                    else:
                        return result

            except queue.Empty:
                continue

        if collect_all:
            return results
        return {
            "sender": sender_names[0] if sender_names else "unknown",
            "neuron_id": NAME_TO_ID.get(sender_names[0], sender_names[0]) if sender_names else "unknown",
            "success": False,
            "content": f"[超时 {timeout}s] 未收到来自 {sender_names} 的响应",
            "error": "timeout",
        }

    # ── 频道感知路由 ───────────────────────────────────

    def _get_channel_for(self, neuron_id):
        """获取指定神经元对应的业务频道名称

        返回:
            str: 频道名（"code", "analysis", "pro", "phil"...）
        """
        return NEURON_CHANNEL_MAP.get(neuron_id, "control")

    def _get_display_name(self, neuron_id):
        """获取神经元在总线上的显示名"""
        return DISPLAY_NAMES.get(neuron_id, neuron_id)

    # ── 核心API ────────────────────────────────────────

    def single_task(self, neuron_id, task, timeout=None):
        """向一个神经元发送任务并等待结果

        这是最基础的通信原语。

        参数:
            neuron_id: 神经元标识符
                       (hermes/codex/claude/openclaw_wsl/openclaw_win/
                        marvis_qq/opengod/openalien/openinterpreter/autogpt)
            task:      任务内容字符串
            timeout:   超时秒数（默认 90s）

        返回:
            dict: {
                "success": bool,
                "neuron_id": str,
                "content": str,
                "elapsed": float,
                ...
            }

        频道路由:
            codex          → 代码频道(18790)
            claude         → 分析频道(18791)
            openclaw_*     → 专业频道(18792)
            marvis_qq      → 专业频道(18792)
            opengod        → 哲学频道(18793)
            hermes/其他    → 控制频道(18789)
        """
        display_name = self._get_display_name(neuron_id)
        channel = self._get_channel_for(neuron_id)

        t0 = time.time()

        # ── 方案A: 通过FDM总线 ──
        if not self._connected:
            if not self.connect():
                # 总线不可用，回退到API
                return self._fallback_api(neuron_id, task, timeout)

        # 发送任务
        if not self.send_task(display_name, task):
            # 发送失败，尝试重连后重试
            if not self.reconnect() or not self.send_task(display_name, task):
                return self._fallback_api(neuron_id, task, timeout)

        # 等待响应
        result = self._wait_for_response(display_name, timeout)
        elapsed = round(time.time() - t0, 2)
        result["elapsed"] = elapsed
        result["channel"] = channel
        result["channel_port"] = CHANNEL_PORTS.get(channel, self.port)

        return result

    def collaborate(self, question, neuron_ids=None, timeout=None):
        """向多个神经元发送同一问题，汇总结果

        这是真元集群的第一次真实生产协作。
        每个神经元以自身专业视角回答同一问题。

        参数:
            question:   问题/任务内容
            neuron_ids: 要询问的神经元ID列表
                        (默认: [codex, claude, openclaw_wsl, marvis_qq, opengod])
            timeout:    总超时（默认 120s，自动分配给每个神经元）

        返回:
            dict: {
                "question": str,
                "results": { neuron_id: {...}, ... },
                "summary": str (合并摘要),
                "total_time": float,
                "success_count": int,
                "total_count": int,
            }

        数据持久化:
            每次协作结果自动写入 hippocampus_memory.json 的 causal_chains。
        """
        if neuron_ids is None:
            # 默认神经元集：覆盖多频道
            neuron_ids = [
                "hermes",      # 中央调度
                "codex",       # 代码频道
                "claude",      # 分析频道
                "openclaw_wsl", # 专业频道
                "marvis_qq",   # 专业频道
                "opengod",     # 哲学频道
            ]

        timeout = timeout or 120
        per_timeout = max(timeout / len(neuron_ids), 20)

        print(f"\n{'='*60}")
        print(f"  🧬 神经协作 | {len(neuron_ids)}神经元 | {question[:60]}")
        print(f"  📡 频道: ", end="")
        channels_used = set()
        for nid in neuron_ids:
            ch = self._get_channel_for(nid)
            channels_used.add(f"{ch}({CHANNEL_PORTS.get(ch, '?')})")
        print(", ".join(sorted(channels_used)))
        print(f"{'='*60}")

        results = {}
        success_count = 0
        t_start = time.time()

        for i, nid in enumerate(neuron_ids):
            display = self._get_display_name(nid)
            channel = self._get_channel_for(nid)
            port = CHANNEL_PORTS.get(channel, self.port)

            print(f"\n  [{i+1}/{len(neuron_ids)}] 🧠 {display:15s} → {channel}频道({port})")

            result = self.single_task(nid, question, timeout=per_timeout)

            elapsed = result.get("elapsed", 0)
            if result.get("success"):
                success_count += 1
                content_preview = result.get("content", "")[:120].replace("\n", " ")
                print(f"    ✅ ({elapsed:.1f}s) {content_preview}...")
            else:
                err = result.get("content", result.get("error", "未知错误"))[:80]
                print(f"    ❌ ({elapsed:.1f}s) {err}")

            results[nid] = result

            # 协作间隔（避免总线拥塞）
            if i < len(neuron_ids) - 1:
                time.sleep(0.3)

        total_time = round(time.time() - t_start, 2)

        # ── 合并摘要 ──
        summary = self._generate_summary(question, results)

        # ── 写入海马体 ──
        self._write_causal_chain(question, results, summary)

        print(f"\n{'─'*60}")
        print(f"  协作完成: {success_count}/{len(neuron_ids)} 成功 | {total_time:.1f}s")
        print(f"  已写入海马体 causal_chains")
        print(f"{'─'*60}")

        return {
            "question": question,
            "results": results,
            "summary": summary,
            "total_time": total_time,
            "success_count": success_count,
            "total_count": len(neuron_ids),
        }

    def _generate_summary(self, question, results):
        """生成多神经元协作的合并摘要"""
        lines = [f"【神经协作】问题: {question[:100]}"]
        for nid, r in results.items():
            display = self._get_display_name(nid)
            if r.get("success"):
                content = r.get("content", "")[:200].replace("\n", " | ")
                lines.append(f"  [{display}] {content}")
            else:
                lines.append(f"  [{display}] ❌ {r.get('error', '无响应')}")
        return "\n".join(lines)

    # ── 海马体持久化 ───────────────────────────────────

    def _write_causal_chain(self, question, results, summary):
        """将协作结果写入 hippocampus_memory.json 的 causal_chains

        每条因果链记录:
            - cause: 协作问题
            - effect: 合并摘要
            - tags: 参与的神经元
            - confidence: 成功比例
            - timestamp: 完成时间
        """
        hip = self._load_hippocampus()
        chains = hip.setdefault("causal_chains", [])

        success_count = sum(1 for r in results.values() if r.get("success"))
        total = len(results)
        confidence = round(success_count / max(total, 1), 2)

        tags = ["神经协作", "neural_collaboration"]
        for nid in results:
            tags.append(nid)
            tags.append(self._get_display_name(nid))

        chains.append({
            "id": f"neural-collab-{int(time.time()*1000)}-{len(chains)}",
            "cause": f"[神经协作] {question[:200]}",
            "effect": summary[:500],
            "tags": list(set(tags)),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "confidence": confidence,
            "neurons_involved": list(results.keys()),
            "success_rate": f"{success_count}/{total}",
        })

        self._atomic_write(HIP_PATH, hip)

    def _load_hippocampus(self):
        """加载海马体记忆文件"""
        try:
            if HIP_PATH.exists():
                return json.loads(HIP_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
        return {"causal_chains": [], "nodes": {}}

    @staticmethod
    def _atomic_write(path, data):
        """原子写入JSON文件（防损坏）"""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            tmp.replace(path)
        except Exception:
            # 如果atomic写入失败，直接写
            try:
                path.write_text(
                    json.dumps(data, ensure_ascii=False, indent=2),
                    encoding="utf-8"
                )
            except Exception:
                pass

    # ── API回退（总线离线时的直接调用） ────────────────

    def _fallback_api(self, neuron_id, task, timeout=None):
        """总线不可用时，直接通过API调用执行推理

        复制 neuron_daemon.py 中 execute_task 的逻辑，
        确保回退模式下仍能获得高质量响应。
        """
        t0 = time.time()
        timeout = timeout or self.default_timeout
        display = self._get_display_name(neuron_id)

        # 为不同神经元构造角色提示
        system_prompts = {
            "hermes":   "You are the central orchestrator of the ZhenYuan cluster.",
            "codex":    "You are Codex, an expert AI code generation engine.",
            "claude":   "You are Claude Code, an expert code architect.",
            "openclaw_wsl": "You are OpenClaw, a specialized AI agent.",
            "openclaw_win": "You are OpenClaw Windows agent.",
            "marvis_qq":    "You are Marvis QQ multi-modal assistant.",
            "opengod":  "You are a philosophical thinker fusing Eastern and Western wisdom.",
            "openalien": "You are OpenAlien blockchain expert.",
            "openinterpreter": "You are OpenInterpreter, natural language to code.",
            "autogpt":  "You are AutoGPT, an autonomous AI agent.",
        }

        system_prompt = system_prompts.get(neuron_id, "You are a helpful AI assistant.")
        role_prompt = f"你以{display}的身份思考。{system_prompt}\n\n任务: {task}"

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": task},
            ]

            data = json.dumps({
                "model": MODEL,
                "messages": messages,
                "max_tokens": 600,
            }).encode()

            req = urllib.request.Request(
                f"{API_BASE}/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json",
                },
            )

            with urllib.request.urlopen(req, timeout=timeout) as resp:
                result = json.loads(resp.read())
                content = (
                    result["choices"][0]["message"].get("content", "")
                    or result["choices"][0]["message"].get("reasoning_content", "")
                )

            elapsed = round(time.time() - t0, 2)
            return {
                "neuron_id": neuron_id,
                "sender": display,
                "display_name": display,
                "success": True,
                "content": content.strip(),
                "elapsed": elapsed,
                "channel": "fallback_api",
                "channel_port": 0,
            }

        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            return {
                "neuron_id": neuron_id,
                "sender": display,
                "display_name": display,
                "success": False,
                "content": f"[API回退失败] {str(e)[:200]}",
                "error": str(e)[:200],
                "elapsed": elapsed,
                "channel": "fallback_api",
                "channel_port": 0,
            }


# ═══════════════════════════════════════════════════════════════
#  便捷函数（无需实例化即可调用）
# ═══════════════════════════════════════════════════════════════

def quick_task(neuron_id, task, timeout=90):
    """快捷：向一个神经元发送任务"""
    with NeuralCollaborationOrchestrator() as nco:
        return nco.single_task(neuron_id, task, timeout=timeout)


def quick_collaborate(question, neuron_ids=None, timeout=120):
    """快捷：多神经元协作"""
    with NeuralCollaborationOrchestrator() as nco:
        return nco.collaborate(question, neuron_ids=neuron_ids, timeout=timeout)


def check_bus():
    """快捷：检查总线状态"""
    nco = NeuralCollaborationOrchestrator()
    online = nco.check_bus()
    if online:
        status = nco.get_bus_status()
        channels = status.get("channels", {})
        total = status.get("total_agents", 0)
        print(f"✅ FDM神经总线在线 | {total}神经元在线")
        for ch_id, ch in channels.items():
            agents = ch.get("agents", [])
            if agents:
                print(f"   📡 {ch.get('name','?'):12s} ({ch.get('port','?')}): {', '.join(agents)}")
        return True
    else:
        print("❌ FDM神经总线离线")
        return False


# ═══════════════════════════════════════════════════════════════
#  命令行入口
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="🧬 真元·神经协作编排器 — FDM总线驱动多神经元协作",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 检查总线状态
  python3 neural_collaboration_orchestrator.py --status

  # 向Codex发送单任务
  python3 neural_collaboration_orchestrator.py --neuron codex --task "写一个快速排序"

  # 多神经元协作
  python3 neural_collaboration_orchestrator.py --collaborate "系统架构缺口?"

  # 指定协作神经元子集
  python3 neural_collaboration_orchestrator.py --collaborate "如何进化?" \\
    --neurons hermes,codex,claude,opengod
        """
    )

    parser.add_argument("--status", action="store_true", help="检查总线状态")
    parser.add_argument("--neuron", type=str, default=None,
                        help="目标神经元ID (hermes/codex/claude/...)")
    parser.add_argument("--task", type=str, default=None,
                        help="单任务内容")
    parser.add_argument("--collaborate", type=str, default=None,
                        help="协作问题")
    parser.add_argument("--neurons", type=str, default=None,
                        help="协作神经元列表 (逗号分隔)")
    parser.add_argument("--timeout", type=int, default=90,
                        help="超时秒数 (默认90)")
    parser.add_argument("--file", type=str, default=None,
                        help="从文件读取任务内容")

    args = parser.parse_args()

    # ── 检查总线 ──
    if args.status:
        check_bus()
        sys.exit(0)

    # ── 从文件读取 ──
    task_content = args.task
    if args.file:
        try:
            fp = Path(args.file)
            task_content = fp.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            sys.exit(1)

    # ── 单任务模式 ──
    if args.neuron and task_content:
        if args.neuron not in DISPLAY_NAMES:
            print(f"⚠️  未知神经元: {args.neuron}")
            print(f"   可用: {', '.join(DISPLAY_NAMES.keys())}")
            sys.exit(1)

        print(f"🧠 单任务 → {args.neuron} ({DISPLAY_NAMES[args.neuron]})")
        print(f"📝 内容: {task_content[:100]}...")
        result = quick_task(args.neuron, task_content, timeout=args.timeout)

        print(f"\n{'─'*40}")
        if result.get("success"):
            print(f"✅ 成功 ({result.get('elapsed',0):.1f}s)")
            print(f"内容: {result.get('content','')[:500]}")
        else:
            print(f"❌ 失败: {result.get('error', result.get('content',''))[:200]}")

    # ── 协作模式 ──
    elif args.collaborate:
        neuron_ids = None
        if args.neurons:
            neuron_ids = [n.strip() for n in args.neurons.split(",")]
            unknown = [n for n in neuron_ids if n not in DISPLAY_NAMES]
            if unknown:
                print(f"⚠️  未知神经元: {unknown}")
                print(f"   可用: {', '.join(DISPLAY_NAMES.keys())}")
                sys.exit(1)

        print(f"🧬 神经协作模式")
        print(f"📝 问题: {args.collaborate[:100]}")
        results = quick_collaborate(args.collaborate, neuron_ids=neuron_ids,
                                    timeout=args.timeout * 2)

        print(f"\n{'='*60}")
        print(f"📊 协作报告")
        print(f"{'='*60}")
        print(f"问题: {results['question']}")
        print(f"结果: {results['success_count']}/{results['total_count']} 成功")
        print(f"耗时: {results['total_time']:.1f}s")
        print(f"\n摘要:")
        print(results.get("summary", "")[:500])

    else:
        parser.print_help()
