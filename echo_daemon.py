#!/usr/bin/env python3
"""
持久化FDM业务频道Echo守护进程。
每个业务频道一个独立线程，持续监听，永不退出。
"""
import json, os, sys, time, socket, threading
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
os.chdir(str(CLUSTER))

from neural_bus_fdm import NeuralAgent, NeuralMessage, CHANNEL_DEFS

CHANNEL_PORTS = {ch: cfg["port"] for ch, cfg in CHANNEL_DEFS.items()}

class PersistentEcho:
    def __init__(self, name, channel_id):
        self.name = name
        self.channel_id = channel_id
        self.port = CHANNEL_PORTS[channel_id]
        self.agent = NeuralAgent(name, channel=channel_id)
        self.received = []
        self._running = True

    def run(self):
        while self._running:
            try:
                self.agent.on("*", self._on_message)
                if self.agent.connect(port=self.port):
                    print(f"[{self.name}] 已连接频道[{self.channel_id}] 端口{self.port}")
                    # 保持线程存活，NeuralAgent的_listen线程在后台运行
                    while self._running:
                        time.sleep(5)
                else:
                    print(f"[{self.name}] 连接失败，5秒后重试...")
                    time.sleep(5)
            except Exception as e:
                print(f"[{self.name}] 异常: {e}")
                time.sleep(5)

    def _on_message(self, msg):
        self.received.append(msg)
        # Echo所有非system消息
        if msg.msg_type != "system":
            try:
                echo = NeuralMessage(self.name, msg.sender, "result",
                                     f"[ECHO] 已收到: {str(msg.content)[:100]}")
                self.agent.send(echo)
            except Exception:
                pass

    def stop(self):
        self._running = False
        try:
            self.agent.disconnect()
        except Exception:
            pass

if __name__ == "__main__":
    print("FDM业务频道Echo守护进程启动")
    
    # 为所有业务频道创建echo实例
    services = []
    for ch_id in ["code", "analysis", "pro", "phil", "ext", "reserve"]:
        name = f"{ch_id.capitalize()}Echo"
        svc = PersistentEcho(name, ch_id)
        t = threading.Thread(target=svc.run, daemon=True, name=f"echo-{ch_id}")
        t.start()
        services.append(svc)
        time.sleep(0.3)
    
    print(f"已启动 {len(services)} 个Echo服务")
    print("按Ctrl+C停止...")
    
    try:
        while True:
            time.sleep(30)
            # 打印状态
            active = sum(1 for s in services if s.agent._connected)
            total = sum(len(s.received) for s in services)
            print(f"[{datetime.now().strftime('%H:%M:%S')}] 活跃: {active}/{len(services)} | 总消息: {total}")
    except KeyboardInterrupt:
        print("\n停止所有Echo服务...")
        for s in services:
            s.stop()
