#!/usr/bin/env python3
"""
激活FDM总线业务频道(18790-18795)。
在每个业务频道启动echo/listener服务，验证双向通信。
"""
import json, os, sys, time, socket, threading
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
os.chdir(str(CLUSTER))

from neural_bus_fdm import NeuralAgent, NeuralMessage, CHANNEL_DEFS

# ── 频道映射 ──
CHANNEL_PORTS = {ch: cfg["port"] for ch, cfg in CHANNEL_DEFS.items()}

RESULTS = {}

class EchoService:
    """轻量级echo服务 - 在指定频道上监听并回应消息"""
    def __init__(self, name, channel_id):
        self.name = name
        self.channel_id = channel_id
        self.port = CHANNEL_PORTS[channel_id]
        self.agent = NeuralAgent(name, channel=channel_id)
        self.received = []
        self._connected = False

    def connect(self):
        self.agent.on("*", self._on_message)
        ok = self.agent.connect(port=self.port)
        self._connected = ok
        if ok:
            print(f"  ✅ {self.name} 连接 频道[{self.channel_id}] 端口{self.port}")
        else:
            print(f"  ❌ {self.name} 连接失败 端口{self.port}")
        return ok

    def _on_message(self, msg):
        self.received.append(msg)
        print(f"  📨 {self.name} 收到: [{msg.msg_type}] {msg.sender} → {msg.target}: {str(msg.content)[:80]}")
        # Echo back
        if msg.msg_type == "task" and msg.target == self.name:
            echo = NeuralMessage(self.name, msg.sender, "result",
                                 f"[ECHO] 已收到您的任务: {str(msg.content)[:100]}")
            self.agent.send(echo)
            print(f"  📤 {self.name} 回复: {str(echo.content)[:80]}")

    def send_task(self, target, content):
        msg = NeuralMessage(self.name, target, "task", content)
        return self.agent.send(msg)

    def send_result(self, target, content):
        msg = NeuralMessage(self.name, target, "result", content)
        return self.agent.send(msg)

    def status(self):
        return {
            "name": self.name,
            "channel": self.channel_id,
            "port": self.port,
            "connected": self._connected,
            "received_count": len(self.received),
        }


# ── 第1步：启动业务频道echo服务 ──
def start_echo_services():
    print("\n" + "=" * 60)
    print("📡 第2步：启动业务频道Echo服务")
    print("=" * 60)

    services = []

    # 频道18790 - 代码频道
    echo_code = EchoService("CodexEcho", "code")
    if echo_code.connect():
        services.append(echo_code)

    # 频道18791 - 分析频道
    echo_analysis = EchoService("ClaudeEcho", "analysis")
    if echo_analysis.connect():
        services.append(echo_analysis)

    # 频道18792 - 专业频道
    echo_pro = EchoService("ProEcho", "pro")
    if echo_pro.connect():
        services.append(echo_pro)

    # 频道18793 - 哲学频道
    echo_phil = EchoService("PhilEcho", "phil")
    if echo_phil.connect():
        services.append(echo_phil)

    # 频道18794 - 外部知识频道
    echo_ext = EchoService("ExtEcho", "ext")
    if echo_ext.connect():
        services.append(echo_ext)

    # 频道18795 - 保留频道
    echo_reserve = EchoService("ReserveEcho", "reserve")
    if echo_reserve.connect():
        services.append(echo_reserve)

    # 等待注册完成
    time.sleep(1)
    print(f"\n  📊 已启动 {len(services)} 个Echo服务")
    return services


# ── 第2步：通过控制通道发路由测试消息 ──
def route_test(services):
    print("\n" + "=" * 60)
    print("🔄 第3步：通过控制通道发送路由测试消息")
    print("=" * 60)

    # 创建一个控制通道客户端
    controller = NeuralAgent("RouteTest", channel="control")
    controller.on("*", lambda m: print(f"  📨 控制通道收到: [{m.msg_type}] {m.sender}→{m.target}: {str(m.content)[:80]}"))
    if not controller.connect(port=18789):
        print("  ❌ 控制通道连接失败！")
        return False

    time.sleep(0.5)

    # 向业务频道上的echo服务发送任务消息
    targets = {
        "CodexEcho": "code频道(18790)",
        "ClaudeEcho": "analysis频道(18791)",
        "ProEcho": "pro频道(18792)",
        "PhilEcho": "phil频道(18793)",
        "ExtEcho": "ext频道(18794)",
        "ReserveEcho": "reserve频道(18795)",
    }

    for target, desc in targets.items():
        msg = NeuralMessage("RouteTest", target, "task",
                            f"路由测试消息 from 控制通道→{desc} @ {datetime.now().isoformat()}")
        ok = controller.send(msg)
        print(f"  {'✅' if ok else '❌'} RouteTest → {target:15s} ({desc}): 发送{'成功' if ok else '失败'}")
        time.sleep(0.2)

    time.sleep(2)

    # 检查echo服务收到了多少
    total_received = sum(len(s.received) for s in services)
    print(f"\n  📊 Echo服务共收到 {total_received} 条消息")
    for s in services:
        print(f"     {s.name:15s}: {len(s.received)} 条")
    return total_received > 0


# ── 第3步：发送知识采集任务 ──
def knowledge_collection(services):
    print("\n" + "=" * 60)
    print("🧠 第4步：发送真实知识采集任务")
    print("=" * 60)

    # 从配置读取API
    try:
        from api_config import API_KEY, API_BASE, MODEL
    except Exception:
        API_KEY = os.environ.get("API_KEY", "")
        API_BASE = "https://inferaichat.com/v1"
        MODEL = "deepseek-v4-pro"

    # 通过各业务频道发送知识采集任务
    tasks = [
        ("CodexEcho", "code", "请生成一段关于Python元编程的简明知识摘要"),
        ("ClaudeEcho", "analysis", "请分析FDM频分多路总线架构的优势与不足"),
        ("ProEcho", "pro", "简要说明专业Agent系统架构的三种模式"),
        ("PhilEcho", "phil", "用一句话定义什么是元认知"),
        ("ExtEcho", "ext", "列举5个最新的AI研究前沿方向"),
    ]

    collected = []
    for target, channel, task_content in tasks:
        service = next((s for s in services if s.name == target), None)
        if not service:
            continue
        ok = service.send_task("*", task_content)
        print(f"  {'✅' if ok else '❌'} {target:15s} 发送知识采集任务: {task_content[:40]}...")
        collected.append({"target": target, "channel": channel, "task": task_content, "sent": ok})
        time.sleep(0.3)

    time.sleep(1)
    return collected


# ── 第4步：保存结果 ──
def save_results(services, collected):
    print("\n" + "=" * 60)
    print("💾 保存激活结果")
    print("=" * 60)

    result = {
        "timestamp": datetime.now().isoformat(),
        "echo_services": [s.status() for s in services],
        "knowledge_tasks": collected,
        "total_echo_active": sum(1 for s in services if s._connected),
        "total_messages_received": sum(len(s.received) for s in services),
    }

    path = CLUSTER / "fdm_activation_result.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 结果已保存到 {path.name}")

    # 通知总线状态刷新
    status = {}
    for s in services:
        status[s.channel_id] = s.status()
    print(f"  📊 频道状态:")
    for ch, st in status.items():
        print(f"     {ch:10s}: {'🟢在线' if st['connected'] else '🔴离线'} | {st['received_count']}消息")

    return result


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════╗")
    print("║  FDM总线业务频道激活器 v1.0                       ║")
    print("╚════════════════════════════════════════════════════╝")

    services = start_echo_services()
    route_test(services)
    collected = knowledge_collection(services)
    save_results(services, collected)

    print("\n" + "=" * 60)
    print("✅ FDM总线业务频道激活完成！")
    print(f"   活跃Echo服务: {sum(1 for s in services if s._connected)}/{len(services)}")
    print("=" * 60)

    # 保持运行以便查看总线状态
    print("\n⏳ Echo服务持续运行中... (按Ctrl+C停止)")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        print("\n🛑 停止Echo服务...")
