#!/usr/bin/env python3
"""
频分神经总线 — 多通道信号分离
================================
原版总线只有一个通道，所有信号混在一起。
新版按"频率"分通道：不同类型信号走不同端口。

通道分配:
  18789 — 系统总线(register/heartbeat/system)
  18790 — 任务总线(task/result/error)  ← 核心工作通道
  18791 — 感知总线(perception/signal)   ← 前沿知识+外部信号
  18792 — 涌现总线(emergence/superself) ← 超我涌现+元意识

每个通道独立监听，避免不同频率信号互相干扰。

用法:
  python3 freq_bus.py                # 启动全部4通道
  python3 freq_bus.py --status       # 查看全部通道状态
"""
import socket, json, os, sys, time, threading, subprocess, signal
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

# ── 频道定义 ──────────────────────────────────────────

CHANNELS = {
    18789: {"name": "system", "desc": "系统总线", "types": ["register", "heartbeat", "system", "status"]},
    18790: {"name": "task",   "desc": "任务总线", "types": ["task", "result", "error"]},
    18791: {"name": "sense",  "desc": "感知总线", "types": ["perception", "signal", "knowledge"]},
    18792: {"name": "emerge", "desc": "涌现总线", "types": ["emergence", "superself", "evolution"]},
}

class FreqBus:
    """频分复用总线"""
    def __init__(self):
        self.clients = {}  # {port: {name: socket}}
        self.history = {}  # {port: [messages]}
        self._running = False
        self._servers = {}
    
    def start(self):
        self._running = True
        for port, info in CHANNELS.items():
            try:
                server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server.bind(("127.0.0.1", port))
                server.listen(20)
                server.settimeout(1.0)
                self._servers[port] = server
                self.clients[port] = {}
                self.history[port] = []
                threading.Thread(target=self._accept_loop, args=(port, server), daemon=True).start()
                print(f"  📡 {info['name']:8s} @ 127.0.0.1:{port} | {info['desc']}")
            except OSError as e:
                print(f"  ❌ {info['name']:8s} @ 127.0.0.1:{port} | 端口被占用")
        
        # 状态报告
        threading.Thread(target=self._status_loop, daemon=True).start()
        return True
    
    def _accept_loop(self, port, server):
        while self._running:
            try:
                conn, addr = server.accept()
                threading.Thread(target=self._handle_client, args=(port, conn, addr), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                if self._running:
                    break
    
    def _handle_client(self, port, conn, addr):
        buffer = ""
        agent_name = None
        conn.settimeout(60)
        
        try:
            while self._running:
                try:
                    data = conn.recv(65536)
                    if not data:
                        break
                    buffer += data.decode(errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        if not line.strip():
                            continue
                        try:
                            msg = json.loads(line)
                            if agent_name is None:
                                agent_name = msg.get("sender", f"anon_{addr[1]}")
                                self.clients[port][agent_name] = conn
                            
                            # 记录
                            self.history[port].append(msg)
                            if len(self.history[port]) > 500:
                                self.history[port] = self.history[port][-500:]
                            
                            # 路由：同频道广播
                            target = msg.get("target", "*")
                            if target == "*":
                                self._broadcast(port, msg)
                            elif target in self.clients[port]:
                                self._send_to(port, target, msg)
                        except json.JSONDecodeError:
                            pass
                except socket.timeout:
                    continue
        except Exception:
            pass
        finally:
            if agent_name and agent_name in self.clients.get(port, {}):
                self.clients[port].pop(agent_name, None)
            try:
                conn.close()
            except Exception:
                pass
    
    def _broadcast(self, port, msg):
        dead = []
        for name, sock in self.clients.get(port, {}).items():
            try:
                sock.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode())
            except Exception:
                dead.append(name)
        for name in dead:
            self.clients.get(port, {}).pop(name, None)
    
    def _send_to(self, port, target, msg):
        sock = self.clients.get(port, {}).get(target)
        if sock:
            try:
                sock.sendall((json.dumps(msg, ensure_ascii=False) + "\n").encode())
            except Exception:
                self.clients.get(port, {}).pop(target, None)
    
    def _status_loop(self):
        while self._running:
            time.sleep(30)
            if self._running:
                for port, info in CHANNELS.items():
                    agents = list(self.clients.get(port, {}).keys())
                    msgs = len(self.history.get(port, []))
                    if agents:
                        print(f"  ❤️  {info['name']:8s}:{port} | {len(agents)}在线 | {msgs}消息 | {' '.join(agents[:5])}")
    
    def stop(self):
        self._running = False
        for port, server in self._servers.items():
            try:
                server.close()
            except Exception:
                pass
        for port, agents in self.clients.items():
            for sock in agents.values():
                try:
                    sock.close()
                except Exception:
                    pass
    
    def status(self):
        print("╔═══════════════════════════════════════════════╗")
        print("║  频分神经总线 · 多通道状态                   ║")
        print("╠═══════════════════════════════════════════════╣")
        for port, info in CHANNELS.items():
            agents = list(self.clients.get(port, {}).keys())
            msgs = len(self.history.get(port, []))
            icon = "🟢" if agents else "🟡"
            print(f"║  {icon} {info['name']:8s} @ :{port} | {info['desc']:8s} | {len(agents)}Agent {msgs}消息 ║")
            for a in agents[:5]:
                print(f"║     · {a:35s}                    ║")
        print("╚═══════════════════════════════════════════════╝")

def run_freq_bus():
    bus = FreqBus()
    print(f"╔═══════════════════════════════════════════════╗")
    print(f"║  频分神经总线启动                             ║")
    print(f"╠═══════════════════════════════════════════════╣")
    bus.start()
    print(f"╠═══════════════════════════════════════════════╣")
    print(f"║  4通道全部在线                                ║")
    print(f"╚═══════════════════════════════════════════════╝")
    
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n关闭中...")
        bus.stop()

if __name__ == "__main__":
    if "--status" in sys.argv:
        bus = FreqBus()
        bus.status()
    else:
        run_freq_bus()
