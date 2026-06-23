#!/usr/bin/env python3
"""
真元神经网络核心 — 信号总线
============================
不是文件轮询。是实时TCP信号总线。
每个Agent通过socket直连总线，消息实时推送。

架构:
  Agent → 发消息到总线 → 总线路由到目标Agent → Agent实时接收

使用:
  python3 neural_bus.py              # 启动总线守护进程
  python3 neural_bus.py --send       # 发送消息
  python3 neural_bus.py --status     # 查看总线状态
"""
import json, os, sys, time, socket, threading, select
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent

# ── 配置 ───────────────────────────────────────────────
HOST = "127.0.0.1"
PORT = 18789  # 真元集群专用端口
BUF_SIZE = 65536

# ── 消息协议 ───────────────────────────────────────────

class NeuralMessage:
    """真元神经信号"""
    def __init__(self, sender, target, msg_type, content):
        self.sender = sender
        self.target = target  # "*" = broadcast
        self.msg_type = msg_type  # "signal", "task", "result", "heartbeat"
        self.content = content
        self.timestamp = datetime.now().isoformat()
        self.id = f"{int(time.time())}_{sender}"

    def encode(self):
        return json.dumps(self.__dict__, ensure_ascii=False).encode() + b"\n"

    @classmethod
    def decode(cls, data):
        d = json.loads(data.decode().strip())
        return cls(d["sender"], d["target"], d["msg_type"], d["content"])

    def __repr__(self):
        return f"[{self.msg_type}] {self.sender} → {self.target}: {self.content[:60]}"

# ── 总线服务器 ─────────────────────────────────────────

class NeuralBus:
    """
    TCP信号总线。
    Agent连接后保持长连接，实时收发信号。
    """
    def __init__(self):
        self.clients = {}  # {name: socket}
        self.history = []  # 最近1000条消息
        self.lock = threading.Lock()

    def start(self):
        """启动总线"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind((HOST, PORT))
            server.listen(10)
            server.settimeout(1.0)
        except OSError:
            print(f"⚠️ 端口{PORT}被占用，尝试新端口...")
            for alt_port in range(PORT+1, PORT+100):
                try:
                    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    server.bind((HOST, alt_port))
                    server.listen(10)
                    server.settimeout(1.0)
                    self.port = alt_port
                    self._server = server
                    break
                except OSError:
                    continue
            else:
                print("❌ 无法绑定端口")
                return False

        print(f"🧬 真元神经总线启动 @ {HOST}:{PORT}")
        self._server = server
        self._running = True
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._status_loop, daemon=True).start()
        return True

    def _accept_loop(self):
        """接受新Agent连接"""
        while self._running:
            try:
                conn, addr = self._server.accept()
                threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    print(f"  accept错误: {e}")

    def _handle_client(self, conn, addr):
        """处理单个Agent连接"""
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
                        if agent_name is None:
                            agent_name = msg.sender
                            with self.lock:
                                self.clients[agent_name] = conn
                            self._broadcast(NeuralMessage("bus", "*", "system",
                                f"{agent_name} 加入集群 ({addr[0]}:{addr[1]})"))
                            print(f"  ➕ {agent_name} 已连接 ({len(self.clients)}在线)")

                        # 路由消息
                        with self.lock:
                            self.history.append(msg)
                            if len(self.history) > 1000:
                                self.history = self.history[-1000:]

                        if msg.target == "*":
                            self._broadcast(msg)
                        elif msg.target in self.clients:
                            self._send_to(msg.target, msg)
                        else:
                            # Agent离线，缓存
                            self._queue_for(msg.target, msg)
                            self._send_to(msg.sender, NeuralMessage("bus", msg.sender, "error",
                                f"{msg.target} 当前离线，消息已缓存"))

                except socket.timeout:
                    continue
        except Exception as e:
            pass
        finally:
            if agent_name:
                with self.lock:
                    self.clients.pop(agent_name, None)
                self._broadcast(NeuralMessage("bus", "*", "system",
                    f"{agent_name} 断开连接 ({len(self.clients)}在线)"))
                print(f"  ➖ {agent_name} 断开 ({len(self.clients)}在线)")
            try:
                conn.close()
            except Exception:
                pass

    def _broadcast(self, msg):
        """广播消息给所有Agent"""
        with self.lock:
            dead = []
            for name, sock in self.clients.items():
                try:
                    sock.sendall(msg.encode())
                except Exception:
                    dead.append(name)
            for name in dead:
                self.clients.pop(name, None)

    def _send_to(self, target, msg):
        """发送消息给特定Agent"""
        with self.lock:
            sock = self.clients.get(target)
            if sock:
                try:
                    sock.sendall(msg.encode())
                    return True
                except Exception:
                    self.clients.pop(target, None)
            return False

    def _queue_for(self, target, msg):
        """缓存离线消息"""
        qfile = CLUSTER / f"bus_cache_{target}.json"
        try:
            cache = json.loads(qfile.read_text()) if qfile.exists() else []
        except Exception:
            cache = []
        cache.append(msg.__dict__)
        if len(cache) > 100:
            cache = cache[-100:]
        qfile.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

    def _status_loop(self):
        """每30秒报告总线状态"""
        while self._running:
            time.sleep(30)
            with self.lock:
                agents = list(self.clients.keys())
            hb = NeuralMessage("bus", "*", "heartbeat",
                f"在线:{agents} 消息数:{len(self.history)}")
            self._broadcast(hb)
            print(f"  ❤️  {len(agents)}在线 {' '.join(agents[:5])}...")

    def stop(self):
        self._running = False
        if hasattr(self, '_server'):
            self._server.close()
        with self.lock:
            for sock in self.clients.values():
                try:
                    sock.close()
                except Exception:
                    pass
            self.clients.clear()

# ── Agent客户端 ─────────────────────────────────────────

class NeuralAgent:
    """Agent端连接器——替代文件轮询"""
    def __init__(self, name):
        self.name = name
        self.sock = None
        self.buffer = ""
        self._callbacks = {}
        self._running = False
        self._connected = False

    def connect(self, host=HOST, port=PORT):
        """连接到总线"""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(10)
        try:
            self.sock.connect((host, port))
            self._running = True
            self._connected = True
            # 发送身份信号
            self.send(NeuralMessage(self.name, "bus", "register", f"{self.name} 上线"))
            # 启动监听线程
            threading.Thread(target=self._listen, daemon=True).start()
            return True
        except Exception as e:
            print(f"  {self.name} 连接失败: {e}")
            return False

    def on(self, msg_type, callback):
        """注册消息处理器"""
        self._callbacks[msg_type] = callback

    def send(self, msg):
        """发送消息"""
        try:
            self.sock.sendall(msg.encode())
            return True
        except Exception:
            self._connected = False
            return False

    def task(self, target, content):
        """发送任务"""
        msg = NeuralMessage(self.name, target, "task", content)
        return self.send(msg)

    def result(self, target, content):
        """发送结果"""
        msg = NeuralMessage(self.name, target, "result", content)
        return self.send(msg)

    def _listen(self):
        """监听消息"""
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
                    # 调用回调
                    if msg.msg_type in self._callbacks:
                        self._callbacks[msg.msg_type](msg)
            except socket.timeout:
                continue
            except (ConnectionResetError, BrokenPipeError, OSError):
                break
        self._connected = False
        if self._running:
            self._reconnect()

    def _reconnect(self):
        """断线重连"""
        for i in range(3):
            time.sleep(5)
            if self.connect():
                return
        print(f"  {self.name} 断线, 转为文件模式")

    def disconnect(self):
        self._running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

# ── 总线持久化 ──────────────────────────────────────────

def save_bus_state(bus):
    """将总线状态持久化到JSON"""
    with bus.lock:
        state = {
            "timestamp": datetime.now().isoformat(),
            "agents": list(bus.clients.keys()),
            "agent_count": len(bus.clients),
            "history_count": len(bus.history),
            "recent_signals": [(m.sender, m.target, m.msg_type, m.content[:100])
                              for m in bus.history[-20:]],
        }
    path = CLUSTER / "neural_bus_state.json"
    with open(path, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_bus_state():
    """读取持久化的总线状态"""
    path = CLUSTER / "neural_bus_state.json"
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"agents": [], "agent_count": 0, "history_count": 0}

# ── CLI ────────────────────────────────────────────────

if __name__ == "__main__":
    if "--send" in sys.argv:
        # 发送模式
        agent = NeuralAgent("cli")
        if agent.connect():
            target = sys.argv[sys.argv.index("--send") + 1] if "--send" in sys.argv and len(sys.argv) > sys.argv.index("--send") + 1 else "*"
            msg = " ".join(sys.argv[sys.argv.index("--target") + 1:]) if "--target" in sys.argv else "hello"
            agent.task(target, msg)
            print(f"已发送: {msg} → {target}")
            time.sleep(1)
            agent.disconnect()
    elif "--status" in sys.argv:
        state = load_bus_state()
        print(f"🧬 真元神经总线状态")
        print(f"  Agents: {state.get('agent_count',0)}")
        for a in state.get('agents', []):
            print(f"    - {a}")
        print(f"  历史消息: {state.get('history_count',0)}")
        for s in state.get('recent_signals', [])[-5:]:
            print(f"    [{s[2]}] {s[0]} → {s[1]}: {s[3][:50]}")
    else:
        bus = NeuralBus()
        if bus.start():
            try:
                while True:
                    time.sleep(10)
                    save_bus_state(bus)
            except KeyboardInterrupt:
                print("\n总线关闭")
                bus.stop()
                save_bus_state(bus)
