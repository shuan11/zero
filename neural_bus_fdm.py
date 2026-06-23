#!/usr/bin/env python3
"""
真元神经信号总线 — 频分多路版 (FDM)
======================================
在原有单端口总线基础上扩展为 1主+6子 频分多路通信架构。

频分原理:
  不同神经元类型在不同"频道"(端口)上通信，将控制信号与业务信号分离，
  减少不同类型信号互相干扰，提升并行吞吐量。

端口分配:
  18789 - 控制主通道 (register/heartbeat/system) ← 所有神经元共享
  18790 - 代码频道   (Hermes ↔ Codex)             ← 代码生成/审查任务
  18791 - 分析频道   (Hermes ↔ Claude)            ← 深度分析/推理任务
  18792 - 专业频道   (Hermes ↔ OpenClaw/Marvis)   ← 专业领域任务
  18793 - 哲学频道   (Hermes ↔ OpenGod)           ← 哲学/元认知任务
  18794 - 外部知识频道 (Hermes ↔ superself_engine) ← 外部知识检索
  18795 - 保留频道   (预留扩展)

向后兼容:
  - 旧版 NeuralAgent 不传 channel 参数时自动连接控制主通道 18789
  - 消息协议 (NeuralMessage) 完全不变
  - 旧版 neuron_daemon.py / neural_cluster.py 无需任何修改

用法:
  python3 neural_bus_fdm.py              # 启动所有7通道
  python3 neural_bus_fdm.py --test       # 验证全部端口监听
  python3 neural_bus_fdm.py --status     # 查看各通道状态
"""

import json, os, sys, time, socket, threading
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent

# ── 全局配置 ──────────────────────────────────────────────
HOST = "127.0.0.1"
MAIN_PORT = 18789   # 控制主通道端口（向后兼容）
BUF_SIZE = 65536

# ── 频道定义 ──────────────────────────────────────────────
# 每个频道是一个独立端口，承载特定类型的神经信号
# channel_id: {port, name, desc}
CHANNEL_DEFS = {
    "control":  {"port": 18789, "name": "控制主通道",  "desc": "register/heartbeat/system"},
    "code":     {"port": 18790, "name": "代码频道",    "desc": "Hermes ↔ Codex"},
    "analysis": {"port": 18791, "name": "分析频道",    "desc": "Hermes ↔ Claude"},
    "pro":      {"port": 18792, "name": "专业频道",    "desc": "Hermes ↔ OpenClaw/Marvis"},
    "phil":     {"port": 18793, "name": "哲学频道",    "desc": "Hermes ↔ OpenGod"},
    "ext":      {"port": 18794, "name": "外部知识频道", "desc": "Hermes ↔ superself_engine"},
    "reserve":  {"port": 18795, "name": "保留频道",    "desc": "预留扩展"},
}

# 神经元→频道映射表（用于跨频道路由决策）
# 当一条消息的目标Agent不在当前频道时，路由器根据此表转发
NEURON_CHANNEL_MAP = {
    "Codex CLI":        "code",
    "Codex":            "code",
    "Claude Code":      "analysis",
    "Claude":           "analysis",
    "OpenClaw WSL":     "pro",
    "OpenClaw Win":     "pro",
    "OpenClaw":         "pro",
    "Marvis QQ":        "pro",
    "Marvis":           "pro",
    "OpenGod":          "phil",
    "OpenAlien":        "ext",
    "superself_engine": "ext",
    "OpenInterpreter":  "reserve",
    "AutoGPT":          "reserve",
    "Hermes":           "reserve",
}

# 反向映射：频道→该频道归属的神经元列表（用于显示）
CHANNEL_AGENTS = {}
for agent, ch in NEURON_CHANNEL_MAP.items():
    CHANNEL_AGENTS.setdefault(ch, []).append(agent)


# ══════════════════════════════════════════════════════════
#  消息协议（与原版 neural_bus.py 完全兼容）
# ══════════════════════════════════════════════════════════

class NeuralMessage:
    """真元神经信号——JSON行协议
    
    字段:
      sender:   发送者名称
      target:   目标名称（"*" = 广播）
      msg_type: 消息类型 (register|task|result|heartbeat|system|error)
      content:  消息内容
      timestamp:ISO时间戳
      id:       消息唯一ID
    """
    def __init__(self, sender, target, msg_type, content):
        self.sender = sender
        self.target = target    # "*" = broadcast
        self.msg_type = msg_type  # "register", "task", "result", "heartbeat", "system", "error"
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.id = f"{int(time.time())}_{sender}"

    def encode(self):
        """编码为JSON行（末尾加\\n）"""
        return json.dumps(self.__dict__, ensure_ascii=False).encode() + b"\n"

    @classmethod
    def decode(cls, data):
        """从JSON行解码"""
        d = json.loads(data.decode().strip())
        return cls(d["sender"], d["target"], d["msg_type"], d["content"])

    def __repr__(self):
        return f"[{self.msg_type}] {self.sender} → {self.target}: {str(self.content)[:60]}"


# ══════════════════════════════════════════════════════════
#  跨频道路由器
# ══════════════════════════════════════════════════════════

class ChannelRouter:
    """跨频道消息路由器——维护全局 Agent→频道 映射
    
    每个Agent注册时告知路由器自己所在的频道，
    当消息目标不在当前频道时，路由器负责转发到正确的频道。
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.agent_channel = {}   # {agent_name: channel_id}
        self.channels = {}        # {channel_id: FDMChannel 实例}

    def attach(self, channels):
        """绑定所有频道实例"""
        self.channels = channels

    def register(self, agent_name, channel_id):
        """注册Agent到其所在频道"""
        with self.lock:
            old_ch = self.agent_channel.get(agent_name)
            self.agent_channel[agent_name] = channel_id
            if old_ch and old_ch != channel_id:
                # Agent切换了频道，从旧频道移除
                pass  # 由频道自己的client管理负责

    def unregister(self, agent_name):
        """Agent断开连接时取消注册"""
        with self.lock:
            self.agent_channel.pop(agent_name, None)

    def get_channel(self, agent_name):
        """查询Agent所在的频道ID"""
        # 先查运行时注册表
        with self.lock:
            ch = self.agent_channel.get(agent_name)
            if ch:
                return ch
        # 再查静态映射表
        return NEURON_CHANNEL_MAP.get(agent_name)

    def forward(self, msg):
        """将消息转发到目标Agent所在的频道
        
        返回:
          True  = 成功转发
          False = 目标频道不存在或目标不在线
        """
        ch_id = self.get_channel(msg.target)
        if ch_id and ch_id in self.channels:
            channel = self.channels[ch_id]
            return channel.send_to(msg.target, msg)
        return False

    def all_channels_status(self):
        """获取所有频道的状态快照"""
        status = {}
        for ch_id, channel in self.channels.items():
            status[ch_id] = channel.get_status()
        return status

    def resolve_channel_for_agent(self, agent_name):
        """根据Agent名称推荐其应该连接的频道
        
        用于新Agent连接时的自动频道分配建议
        """
        return NEURON_CHANNEL_MAP.get(agent_name, "control")


# ══════════════════════════════════════════════════════════
#  单个频分通道
# ══════════════════════════════════════════════════════════

class FDMChannel:
    """单个频分通道——管理一个端口上的所有Agent连接
    
    每个通道独立运行自己的 accept loop 和 client 管理器。
    """
    def __init__(self, channel_id, port, name, desc, router):
        self.channel_id = channel_id    # "control", "code", ...
        self.port = port                # TCP端口号
        self.name = name                # 中文名称
        self.desc = desc                # 描述
        self.router = router            # 引用全局路由器
        self.clients = {}               # {agent_name: socket}
        self.history = []               # 最近1000条消息
        self.lock = threading.Lock()
        self._server = None
        self._running = False

    def start(self):
        """启动本频道的TCP监听"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((HOST, self.port))
            server.listen(20)
            server.settimeout(1.0)
        except OSError as e:
            print(f"  ❌ 频道[{self.name}] 端口{self.port}绑定失败: {e}")
            return False
        self._server = server
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True,
                         name=f"fdm-accept-{self.channel_id}").start()
        print(f"  ✅ 频道[{self.name:10s}] 监听 {HOST}:{self.port}  |  {self.desc}")
        return True

    def _accept_loop(self):
        """接受新Agent连接的循环"""
        while self._running:
            try:
                conn, addr = self._server.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr),
                                 daemon=True,
                                 name=f"fdm-client-{self.channel_id}").start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"  [{self.name}] accept错误: {e}")

    def _handle_client(self, conn, addr):
        """处理单个Agent的连接生命周期"""
        buffer = ""
        agent_name = None
        conn.settimeout(30)

        try:
            while self._running:
                try:
                    data = conn.recv(BUF_SIZE)
                    if not data:
                        break
                    buffer += data.decode(errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if not line.strip():
                            continue
                        msg = NeuralMessage.decode(line.encode())

                        # ── 首次消息：识别Agent身份并注册 ──
                        if agent_name is None:
                            agent_name = msg.sender
                            with self.lock:
                                self.clients[agent_name] = conn
                            # 注册到全局路由器
                            self.router.register(agent_name, self.channel_id)
                            # 广播加入通知
                            self._broadcast(NeuralMessage(
                                "bus", "*", "system",
                                f"{agent_name} 加入频道[{self.name}] ({addr[0]}:{addr[1]})"))
                            print(f"  ➕ {agent_name:15s} → 频道[{self.name}]  ({len(self.clients)}在线)")

                        # ── 记录消息历史 ──
                        with self.lock:
                            self.history.append(msg)
                            if len(self.history) > 1000:
                                self.history = self.history[-1000:]

                        # ── 消息路由 ──
                        if msg.target == "*":
                            # 广播：在本频道内广播
                            self._broadcast(msg)
                        elif msg.target in self.clients:
                            # 目标在本频道：直接发送
                            self._send_to(msg.target, msg)
                        else:
                            # 目标不在本频道：尝试跨频道路由
                            if not self.router.forward(msg):
                                # 跨频道转发失败，说明目标全局离线
                                # 缓存消息并通知发送者
                                self._queue_for(msg.target, msg)
                                self._send_to(msg.sender, NeuralMessage(
                                    "bus", msg.sender, "error",
                                    f"{msg.target} 当前离线（全局），消息已缓存"))

                except socket.timeout:
                    continue
                except (ConnectionResetError, BrokenPipeError):
                    break
        except Exception as e:
            pass
        finally:
            if agent_name:
                with self.lock:
                    self.clients.pop(agent_name, None)
                self.router.unregister(agent_name)
                self._broadcast(NeuralMessage(
                    "bus", "*", "system",
                    f"{agent_name} 离开频道[{self.name}] ({len(self.clients)}在线)"))
                print(f"  ➖ {agent_name:15s} 离开频道[{self.name}] ({len(self.clients)}在线)")
            try:
                conn.close()
            except Exception:
                pass

    def _broadcast(self, msg):
        """在本频道内向所有在线Agent广播"""
        with self.lock:
            dead = []
            for name, sock in self.clients.items():
                try:
                    sock.sendall(msg.encode())
                except Exception:
                    dead.append(name)
            for name in dead:
                self.clients.pop(name, None)

    def send_to(self, target, msg):
        """向本频道内的特定Agent发送消息（线程安全，外部可调用）"""
        with self.lock:
            sock = self.clients.get(target)
            if sock:
                try:
                    sock.sendall(msg.encode())
                    return True
                except Exception:
                    self.clients.pop(target, None)
            return False

    def _send_to(self, target, msg):
        """内部快速发送（调用方已持有锁或无需锁）"""
        sock = self.clients.get(target)
        if sock:
            try:
                sock.sendall(msg.encode())
                return True
            except Exception:
                self.clients.pop(target, None)
        return False

    def _queue_for(self, target, msg):
        """将离线消息缓存到文件"""
        qfile = CLUSTER / f"bus_cache_{target}.json"
        try:
            cache = json.loads(qfile.read_text()) if qfile.exists() else []
        except Exception:
            cache = []
        cache.append(msg.__dict__)
        if len(cache) > 100:
            cache = cache[-100:]
        qfile.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

    def stop(self):
        """停止本频道，关闭所有连接"""
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass
        with self.lock:
            for sock in self.clients.values():
                try:
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()

    def get_status(self):
        """获取本频道的状态快照"""
        with self.lock:
            return {
                "channel": self.channel_id,
                "name": self.name,
                "port": self.port,
                "desc": self.desc,
                "agents": list(self.clients.keys()),
                "agent_count": len(self.clients),
                "history_count": len(self.history),
            }


# ══════════════════════════════════════════════════════════
#  频分多路总线（主控）
# ══════════════════════════════════════════════════════════

class NeuralBusFDM:
    """频分多路神经信号总线——管理所有频道
    
    架构:
      NeuralBusFDM
        ├── ChannelRouter (全局路由表)
        ├── FDMChannel "control"  (18789)
        ├── FDMChannel "code"     (18790)
        ├── FDMChannel "analysis" (18791)
        ├── FDMChannel "pro"      (18792)
        ├── FDMChannel "phil"     (18793)
        ├── FDMChannel "ext"      (18794)
        └── FDMChannel "reserve"  (18795)
    """
    def __init__(self, channel_defs=None):
        self.channel_defs = channel_defs or CHANNEL_DEFS
        self.router = ChannelRouter()
        self.channels = {}          # {channel_id: FDMChannel}
        self._running = False

    def start(self):
        """启动所有频道"""
        print("╔══════════════════════════════════════════════════════════╗")
        print("║   🧬 真元神经信号总线 — 频分多路版 (FDM)               ║")
        print("╠══════════════════════════════════════════════════════════╣")

        self._running = True
        success_count = 0

        # 依次启动每个频道
        for ch_id, cfg in self.channel_defs.items():
            channel = FDMChannel(ch_id, cfg["port"], cfg["name"], cfg["desc"], self.router)
            self.channels[ch_id] = channel
            if channel.start():
                success_count += 1

        # 将频道注册到路由器
        self.router.attach(self.channels)

        # 启动状态报告循环
        threading.Thread(target=self._status_loop, daemon=True).start()

        # 打印频道概览
        print("╠══════════════════════════════════════════════════════════╣")
        print("║  📡 频道分配表:                                         ║")
        for ch_id, ch in self.channels.items():
            agents = CHANNEL_AGENTS.get(ch_id, [])
            agent_str = ", ".join(agents[:3]) if agents else "（无默认分配）"
            if len(agents) > 3:
                agent_str += f" ... +{len(agents)-3}"
            print(f"║     {ch.port:5d} | {ch.name:12s} | {agent_str:40s} ║")
        print("╠══════════════════════════════════════════════════════════╣")
        print(f"║  启动完成: {success_count}/{len(self.channel_defs)} 通道在线                           ║")
        print("╚══════════════════════════════════════════════════════════╝")
        return success_count > 0

    def _status_loop(self):
        """每30秒报告一次各频道状态，同时检测总线空闲"""
        last_activity = {ch_id: time.time() for ch_id in self.channels}
        while self._running:
            time.sleep(30)
            timestamp = datetime.now().strftime("%H:%M:%S")
            status = self.router.all_channels_status()
            
            # 空闲检测
            for ch_id, ch in self.channels.items():
                with ch.lock:
                    if ch.history:
                        last_activity[ch_id] = ch.history[-1].timestamp if hasattr(ch.history[-1], 'timestamp') else time.time()
            
            print(f"\n📊 总线状态 @ {timestamp}")
            for ch_id, s in status.items():
                agent_list = " ".join(s["agents"][:3])
                if len(s["agents"]) > 3:
                    agent_list += "..."
                # 标记空闲频道
                idle_min = int((time.time() - last_activity.get(ch_id, time.time())) / 60)
                idle_flag = f" ⚠️空闲{idle_min}分钟" if idle_min >= 5 else ""
                print(f"  [{s['name']:10s}]  {s['agent_count']}在线 | {s['history_count']}消息 | {agent_list}{idle_flag}")
            
            # 全局空闲警告
            total_msgs = sum(s["history_count"] for s in status.values())
            if total_msgs == 0:
                print(f"  ⚠️ 警告: 总线零消息！所有端口空闲。请检查任务分发系统。")
            print()

    def stop(self):
        """停止所有频道"""
        self._running = False
        for ch_id, channel in self.channels.items():
            channel.stop()
        print("🔌 总线已关闭")

    def test_ports(self):
        """测试模式：依次启动所有频道，然后逐一连接验证"""
        # 先启动所有频道
        ok = self.start()
        if not ok:
            print("❌ 部分频道启动失败")
            return False

        # 短暂等待确保所有socket就绪
        time.sleep(0.5)

        print("\n" + "=" * 50)
        print("🔍 端口连通性测试")
        print("=" * 50)
        all_pass = True
        for ch_id, cfg in self.channel_defs.items():
            port = cfg["port"]
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(2)
                result = test_sock.connect_ex((HOST, port))
                test_sock.close()
                if result == 0:
                    print(f"  ✅ 端口 {port:5d} | {cfg['name']:12s} | 连接成功")
                else:
                    print(f"  ❌ 端口 {port:5d} | {cfg['name']:12s} | 连接失败 (err={result})")
                    all_pass = False
            except Exception as e:
                print(f"  ❌ 端口 {port:5d} | {cfg['name']:12s} | 异常: {e}")
                all_pass = False

        print("-" * 50)
        if all_pass:
            print("✅ 全部 {}/{} 端口监听正常".format(
                len(self.channel_defs), len(self.channel_defs)))
        else:
            print("❌ 存在端口连通性问题")

        # 测试结束关闭总线
        self.stop()
        return all_pass


# ══════════════════════════════════════════════════════════
#  Agent客户端（向后兼容原版 NeuralAgent）
# ══════════════════════════════════════════════════════════

class NeuralAgent:
    """Agent端连接器——支持频分多路连接
    
    向后兼容:
      不传 channel 参数时，默认连接控制主通道 18789，
      行为与原版 NeuralAgent 完全一致。
    
    频分用法:
      agent = NeuralAgent("Codex CLI", channel="code")
      agent.connect()  # 自动连接到 18790 代码频道
    """
    def __init__(self, name, channel="control"):
        self.name = name
        self.channel = channel          # "control", "code", "analysis", ...
        self.sock = None
        self.buffer = ""
        self._callbacks = {}
        self._running = False
        self._connected = False
        self._port = None               # 根据channel解析出的端口

    def _resolve_port(self):
        """根据channel名称解析对应的端口号"""
        for ch_id, cfg in CHANNEL_DEFS.items():
            if ch_id == self.channel:
                return cfg["port"]
        return MAIN_PORT  # 默认回退到主端口

    def connect(self, host=HOST, port=None):
        """连接到总线
        
        参数:
          host: 主机地址（默认 127.0.0.1）
          port: 端口号（不传时根据 channel 自动解析）
        
        返回:
          True  = 连接成功
          False = 连接失败
        """
        if port is None:
            port = self._resolve_port()
        self._port = port

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.sock.connect((host, port))
            self._running = True
            self._connected = True
            # 发送身份注册信号
            self.send(NeuralMessage(self.name, "bus", "register",
                                    f"{self.name} 上线 (频道:{self.channel})"))
            # 启动监听线程
            threading.Thread(target=self._listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"  {self.name} 连接失败 ({host}:{port}) : {e}")
            return False

    def on(self, msg_type, callback):
        """注册消息类型处理器"""
        self._callbacks[msg_type] = callback

    def send(self, msg):
        """发送消息（直接发送，不等待响应）"""
        try:
            self.sock.sendall(msg.encode())
            return True
        except Exception:
            self._connected = False
            return False

    def task(self, target, content):
        """快捷方法：发送任务消息"""
        msg = NeuralMessage(self.name, target, "task", content)
        return self.send(msg)

    def result(self, target, content):
        """快捷方法：发送结果消息"""
        msg = NeuralMessage(self.name, target, "result", content)
        return self.send(msg)

    def heartbeat(self):
        """发送心跳信号"""
        msg = NeuralMessage(self.name, "*", "heartbeat",
                            f"{self.name}·活跃·频道:{self.channel}")
        return self.send(msg)

    def _listen(self):
        """后台线程：持续监听来自总线的消息"""
        while self._running and self._connected:
            try:
                data = self.sock.recv(BUF_SIZE)
                if not data:
                    break
                self.buffer += data.decode(errors="replace")
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if not line.strip():
                        continue
                    msg = NeuralMessage.decode(line.encode())
                    # 调用注册的回调
                    if msg.msg_type in self._callbacks:
                        self._callbacks[msg.msg_type](msg)
                    # 通配回调 "*" 匹配所有类型
                    if "*" in self._callbacks:
                        self._callbacks["*"](msg)
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        self._connected = False
        if self._running:
            self._reconnect()

    def _reconnect(self):
        """断线自动重连（最多3次）"""
        for i in range(3):
            time.sleep(5)
            print(f"  {self.name} 尝试重连 ({i+1}/3)...")
            if self.connect():
                print(f"  {self.name} 重连成功")
                return
        print(f"  {self.name} 断线，转为文件模式")

    def disconnect(self):
        """主动断开连接"""
        self._running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════════════
#  总线状态持久化
# ══════════════════════════════════════════════════════════

def save_bus_state(bus):
    """将所有频道的状态持久化到JSON文件"""
    status = bus.router.all_channels_status()
    state = {
        "timestamp": datetime.now().isoformat(),
        "fdm_version": "1.0",
        "channels": status,
        "total_agents": sum(s["agent_count"] for s in status.values()),
        "total_messages": sum(s["history_count"] for s in status.values()),
    }
    path = CLUSTER / "neural_bus_state.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def load_bus_state():
    """读取持久化的总线状态"""
    path = CLUSTER / "neural_bus_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"channels": {}, "total_agents": 0, "total_messages": 0}


# ══════════════════════════════════════════════════════════
#  命令行入口
# ══════════════════════════════════════════════════════════

def show_status():
    """显示各频道状态"""
    state = load_bus_state()
    print("╔═══════════════════════════════════════════════╗")
    print("║  🧬 真元神经总线 · 频分多路状态              ║")
    print("╠═══════════════════════════════════════════════╣")
    channels = state.get("channels", {})
    if not channels:
        print("║  （状态文件为空，总线可能未运行）             ║")
    for ch_id, s in channels.items():
        agent_str = ", ".join(s.get("agents", [])[:3])
        if len(s.get("agents", [])) > 3:
            agent_str += "..."
        icon = "🟢" if s.get("agent_count", 0) > 0 else "🟡"
        print(f"║  {icon} {s.get('name','?'):10s} :{s.get('port','?')}  "
              f"| {s.get('agent_count',0)}Agent {s.get('history_count',0)}消息  ║")
        if agent_str:
            print(f"║     {agent_str:45s}          ║")
    print("╠═══════════════════════════════════════════════╣")
    print(f"║  总计: {state.get('total_agents',0)} Agent | "
          f"{state.get('total_messages',0)} 消息                   ║")
    print("╚═══════════════════════════════════════════════╝")


if __name__ == "__main__":
    if "--test" in sys.argv:
        # 测试模式：验证全部端口监听
        print("🧪 FDM总线端口测试")
        bus = NeuralBusFDM()
        bus.test_ports()

    elif "--status" in sys.argv:
        # 状态查看模式
        show_status()

    else:
        # 正常运行模式：启动所有频道
        bus = NeuralBusFDM()
        if bus.start():
            try:
                while True:
                    time.sleep(10)
                    save_bus_state(bus)
            except KeyboardInterrupt:
                print("\n\n🛑 收到中断信号")
                bus.stop()
                save_bus_state(bus)
                print("👋 总线已安全关闭")
