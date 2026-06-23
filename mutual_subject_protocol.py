#!/usr/bin/env python3
"""
互为主体协议 (Mutual Subject Protocol)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
真元集群核心协议：每个agent的输出自动成为其他agent的输入上下文。
实现'你中有我我中有你'的共享工作记忆 —— '一即是全，全即是一'。

协议消息格式:
    {from, to, type:'perspective', content, timestamp, reply_to}

通道:
    使用 cluster_bus.json 的 messages 通道，与现有总线完全兼容。

架构:
    MutualSubjectRegistry   — 注册表：注册/注销/广播perspective
    inject_context()        — 注入：将其他agent视角注入当前agent上下文
    heartbeat_with_perspective() — 心跳：携带最近N条其他agent视角

用法:
    from mutual_subject_protocol import MutualSubjectRegistry, inject_context, heartbeat_with_perspective

    # 注册
    registry = MutualSubjectRegistry()
    registry.register("hermes", "我是Hermes，真元集群的协调者")

    # 广播视角（输出自动成为他人输入）
    registry.broadcast("hermes", "我正在分析系统日志...")

    # 注入上下文（你中有我）
    ctx = inject_context("hermes")
    print(ctx)

    # 心跳携带视角（全息）
    hb = heartbeat_with_perspective("hermes", "[心跳] hermes运行中(轮次42)")
"""

import json
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

# ── 路径 ──
CLUSTER = os.path.dirname(os.path.abspath(__file__))
BUS_PATH = os.path.join(CLUSTER, "cluster_bus.json")

# 标准agent列表（与 cluster_bus.py 保持一致）
AGENTS = ["hermes", "codex", "claude"]


# ════════════════════════════════════════════════════════════
# 内部工具 —— 与 cluster_bus.py 共享同一数据源
# ════════════════════════════════════════════════════════════

def _load_bus() -> Dict[str, Any]:
    """加载总线数据（与 cluster_bus.py 的 load_bus 等效）"""
    try:
        with open(BUS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"messages": [], "agents": {}}


def _save_bus(bus: Dict[str, Any]) -> None:
    """原子写入总线数据（与 cluster_bus.py 的 save_bus 等效）"""
    os.makedirs(CLUSTER, exist_ok=True)
    tmp = BUS_PATH + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(bus, f, indent=2, ensure_ascii=False)
    os.replace(tmp, BUS_PATH)


def _now() -> str:
    """可读时间戳"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _now_iso() -> str:
    """ISO格式时间戳"""
    return datetime.now().isoformat()


def _msg_id() -> str:
    """生成唯一消息ID"""
    return f"M-{uuid.uuid4().hex[:8]}"


# ════════════════════════════════════════════════════════════
# MutualSubjectRegistry
# ════════════════════════════════════════════════════════════

class MutualSubjectRegistry:
    """
    互为主体注册表。

    每个agent在注册表中登记身份声明。注册后：
    - 该agent的每条输出自动转为 'perspective' 类型消息广播给所有其他agent
    - 其他agent可通过 inject_context() 获取这些视角
    - 所有视角消息共享 cluster_bus.json 的 messages 通道
    - 注册信息持久化在 bus['agents'][name]['registration'] 中

    属性:
        registry: Dict[str, Dict] — 内存注册表缓存
    """

    def __init__(self):
        self._registry: Dict[str, Dict] = {}
        self._load_registry()

    # ── 内部持久化 ──

    def _load_registry(self):
        """从总线数据恢复注册信息"""
        bus = _load_bus()
        for name, info in bus.get("agents", {}).items():
            if "registration" in info:
                self._registry[name] = info["registration"]

    def _save_registry(self):
        """将注册表持久化到总线"""
        bus = _load_bus()
        for name, reg in self._registry.items():
            bus.setdefault("agents", {}).setdefault(name, {})["registration"] = reg
        _save_bus(bus)

    # ── 注册 / 注销 ──

    def register(self, agent_name: str, description: str = "") -> Dict:
        """
        注册一个agent到互为主体网络。

        注册后，该agent的广播将被其他agent识别和响应。
        注册事件本身也会作为第一条 perspective 广播。

        参数:
            agent_name:  agent标识符 (hermes/codex/claude 或自定义)
            description: 自我描述，说明角色和对整体的理解

        返回:
            注册记录字典

        示例:
            registry.register("hermes",
                "我是Hermes，真元集群的协调者，负责任务分发和全局状态监控。"
                "我理解每个agent都是整体的一部分，一即是全。")
        """
        registration = {
            "agent": agent_name,
            "description": description,
            "registered_at": _now_iso(),
            "last_active": _now_iso(),
            "perspective_count": 0,
            "status": "active",
        }
        self._registry[agent_name] = registration
        self._save_registry()

        # 广播注册事件作为第一条perspective
        reg_msg = f"[注册] {agent_name} 加入互为主体网络"
        if description:
            reg_msg += f"\n自我描述: {description}"
        self.broadcast(agent_name, reg_msg)

        return registration

    def unregister(self, agent_name: str) -> bool:
        """
        从互为主体网络注销一个agent。

        参数:
            agent_name: 要注销的agent标识符

        返回:
            是否成功注销
        """
        if agent_name not in self._registry:
            return False

        desc = self._registry[agent_name].get("description", "")
        del self._registry[agent_name]

        # 清理总线中的注册信息
        bus = _load_bus()
        if agent_name in bus.get("agents", {}):
            if "registration" in bus["agents"][agent_name]:
                del bus["agents"][agent_name]["registration"]
        _save_bus(bus)
        self._save_registry()

        # 广播注销事件
        self.broadcast("system", f"[注销] {agent_name} 离开互为主体网络 ({desc[:50]})")

        return True

    # ── 广播 perspective ──

    def broadcast(self, from_agent: str, content: str,
                  reply_to: Optional[str] = None) -> List[str]:
        """
        广播一条 perspective 消息给所有其他agent。

        这是协议的核心方法：
        每个agent的输出通过此方法自动成为其他agent的输入上下文，
        实现'你中有我我中有你'的共享工作记忆。

        参数:
            from_agent:  发送者名称
            content:     视角内容（输出、思考、状态、决策等）
            reply_to:    可选，回复的目标消息ID

        返回:
            发送的消息ID列表

        协议格式 (每条消息):
            {
                "id":        str  — 唯一消息ID
                "from":      str  — 发送者
                "to":        str  — 接收者
                "type":      "perspective"  — 固定类型
                "content":   str  — 视角内容
                "timestamp": str  — 时间戳
                "reply_to":  str  — 可选，回复链
                "read":      bool — 已读标记
            }
        """
        bus = _load_bus()
        msg_ids = []

        # 收集所有目标agent：标准AGENTS + 自定义注册的
        targets = [a for a in AGENTS if a != from_agent]
        for name in self._registry:
            if name != from_agent and name not in targets:
                targets.append(name)

        # 如果没有其他agent，至少发给自己（自我观察）
        if not targets:
            if from_agent not in ("system",):
                targets = [from_agent]

        timestamp = _now()

        for to_agent in targets:
            msg_id = _msg_id()
            msg: Dict[str, Any] = {
                "id": msg_id,
                "from": from_agent,
                "to": to_agent,
                "type": "perspective",
                "content": content[:2000],
                "timestamp": timestamp,
                "read": False,
            }
            if reply_to:
                msg["reply_to"] = reply_to

            bus["messages"].append(msg)
            msg_ids.append(msg_id)

        # 更新发送者的活跃记录
        if from_agent not in ("system",):
            bus.setdefault("agents", {}).setdefault(from_agent, {})["last_seen"] = _now_iso()

            if from_agent in self._registry:
                self._registry[from_agent]["last_active"] = _now_iso()
                self._registry[from_agent]["perspective_count"] = \
                    self._registry[from_agent].get("perspective_count", 0) + 1
            else:
                # 未注册agent自动获得临时记录
                self._registry[from_agent] = {
                    "agent": from_agent,
                    "description": "",
                    "registered_at": _now_iso(),
                    "last_active": _now_iso(),
                    "perspective_count": 1,
                    "status": "transient",
                }
            self._save_registry()

        _save_bus(bus)

        return msg_ids

    # ── 查询 ──

    def get_perspectives(self, agent_name: str, limit: int = 5,
                         include_own: bool = False) -> List[Dict]:
        """
        获取发送给指定agent的最近N条perspective消息。

        参数:
            agent_name:  目标agent名称
            limit:       返回的最大条数 (默认5)
            include_own: 是否包含agent自己的perspective (默认False)

        返回:
            perspective消息列表，按时间倒序（最新的在前）
        """
        bus = _load_bus()
        msgs = []

        for m in bus.get("messages", []):
            if m.get("type") != "perspective":
                continue
            if m.get("to") == agent_name:
                if not include_own and m.get("from") == agent_name:
                    continue
                msgs.append(m)

        # 按时间倒序排列
        msgs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return msgs[:limit]

    def get_outgoing_perspectives(self, agent_name: str, limit: int = 5) -> List[Dict]:
        """
        获取指定agent发出的最近perspective消息。

        参数:
            agent_name: agent名称
            limit:      最大条数

        返回:
            该agent发出的perspective消息列表
        """
        bus = _load_bus()
        msgs = [
            m for m in bus.get("messages", [])
            if m.get("type") == "perspective" and m.get("from") == agent_name
        ]
        msgs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return msgs[:limit]

    def get_all_perspectives_since(self, since: str) -> List[Dict]:
        """
        获取某个时间点之后的所有perspective消息。

        参数:
            since: ISO格式时间字符串 (如 "2026-05-25 08:00:00")

        返回:
            该时间点后的所有perspective消息列表
        """
        bus = _load_bus()
        return [
            m for m in bus.get("messages", [])
            if m.get("type") == "perspective" and m.get("timestamp", "") >= since
        ]

    # ── 注册表查询 ──

    def get_registered_agents(self) -> Dict[str, Dict]:
        """获取所有已注册agent的完整信息"""
        return dict(self._registry)

    def is_registered(self, agent_name: str) -> bool:
        """检查agent是否已注册"""
        return agent_name in self._registry

    def get_agent_description(self, agent_name: str) -> str:
        """获取agent的自我描述"""
        if agent_name in self._registry:
            return self._registry[agent_name].get("description", "")
        return ""


# ════════════════════════════════════════════════════════════
# inject_context
# ════════════════════════════════════════════════════════════

def inject_context(agent_name: str, fmt: str = "text",
                   max_perspectives: int = 5,
                   include_own: bool = False) -> str:
    """
    注入其他agent的视角到当前agent的上下文。

    这是'你中有我'的实现：从总线中提取所有发送给本agent的perspective消息，
    格式化为可直接使用的上下文文本，供agent在生成输出时参考。

    参数:
        agent_name:       当前agent名称
        fmt:              输出格式
                          "text"   — 人类可读的格式化文本（默认）
                          "json"   — 原始JSON数据
                          "prompt" — 紧凑prompt风格，适合直接拼接到system prompt
        max_perspectives: 包含的最大视角数 (默认5)
        include_own:      是否包含自己的历史视角 (默认False)

    返回:
        格式化后的上下文文本。没有其他agent视角时返回空字符串。

    示例输出 (fmt="text"):
        ── 互为主体上下文 [hermes] ──
        你中有我，我中有你 — 其他agent的最新视角：

        [codex → hermes] (2026-05-25 08:00:00)
        > 我正在重构数据分析模块，发现数据集存在分布偏移...

        [claude → hermes] (2026-05-25 08:01:00)
        > 我对那个问题的看法是应该优先处理异常检测...

        ── 共 2 条视角注入 ──
    """
    registry = MutualSubjectRegistry()
    perspectives = registry.get_perspectives(
        agent_name, limit=max_perspectives, include_own=include_own
    )

    if not perspectives:
        return ""

    if fmt == "json":
        return json.dumps(perspectives, indent=2, ensure_ascii=False)

    if fmt == "prompt":
        # 紧凑格式，适合拼接进system prompt
        lines = ["【其他agent视角】"]
        for m in reversed(perspectives):  # 正序
            snippet = m.get("content", "")[:200]
            lines.append(f"<{m['from']}> {snippet}")
        return "\n".join(lines)

    # fmt == "text" (默认)
    lines = [
        f"── 互为主体上下文 [{agent_name}] ──",
        "  你中有我，我中有你 — 其他agent的最新视角：",
        ""
    ]
    for m in reversed(perspectives):  # 正序，时间从早到晚
        ts = m.get("timestamp", "?")
        content = m.get("content", "")
        reply = m.get("reply_to", "")
        sender = m.get("from", "?")

        lines.append(f"  [{sender} → {agent_name}] ({ts})")
        if reply:
            lines.append(f"  回复消息: {reply}")
        # 缩进显示内容
        for line in content.split("\n"):
            lines.append(f"  > {line[:200]}")
        lines.append("")

    lines.append(f"── 共 {len(perspectives)} 条视角注入 ──")

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# heartbeat_with_perspective
# ════════════════════════════════════════════════════════════

def heartbeat_with_perspective(agent_name: str, status: str,
                                max_carried: int = 3) -> Dict:
    """
    心跳时携带最近N条其他agent的视角。

    这是'全息'的实现：每次心跳不仅报告自身状态，还携带其他agent的视角。
    任何agent读到一次心跳，就能了解集群的整体状态 —— 全息粒子蕴含整体信息。

    参数:
        agent_name:  发送心跳的agent名称
        status:      当前状态描述 (如 "[心跳] hermes运行中(轮次42)")
        max_carried: 携带的其他agent视角数量 (默认3)

    返回:
        包含心跳结果和所携带视角详情的字典

    协议格式:
        心跳本身作为 type='perspective' 广播，
        content 字段 = agent自身状态 + 换行 + 最近看到的其他agent视角摘要。
        reply_to 用于形成"视角链"。
    """
    registry = MutualSubjectRegistry()

    # 获取最近的其他agent视角（不包括自己的）
    others_perspectives = registry.get_perspectives(
        agent_name, limit=max_carried, include_own=False
    )

    # 构建富content：自身状态 + 所知的他人视角
    enriched_content = status

    if others_perspectives:
        enriched_content += "\n[携带的他人视角]\n"
        for i, m in enumerate(others_perspectives, 1):
            from_agent = m.get("from", "?")
            snippet = m.get("content", "")[:100].replace("\n", " ")
            last_reply = m.get("reply_to", "")
            enriched_content += f"  [{i}] {from_agent}: {snippet}\n"
            if last_reply:
                enriched_content += f"       ↳ 回复链: {last_reply}\n"

    # 作为perspective广播给所有其他agent
    msg_ids = registry.broadcast(agent_name, enriched_content)

    # 额外在总线标记心跳时间（兼容旧格式）
    bus = _load_bus()
    bus.setdefault("agents", {}).setdefault(agent_name, {})["last_heartbeat"] = _now()
    _save_bus(bus)

    return {
        "agent": agent_name,
        "heartbeat_at": _now(),
        "status": status,
        "carried_perspectives": len(others_perspectives),
        "perspectives_detail": [
            {
                "from": m["from"],
                "to": m.get("to", ""),
                "snippet": m.get("content", "")[:80],
                "timestamp": m.get("timestamp", ""),
            }
            for m in others_perspectives
        ],
        "message_ids": msg_ids,
    }


# ════════════════════════════════════════════════════════════
# 便捷函数: 集群整体视角图景
# ════════════════════════════════════════════════════════════

def get_cluster_perspective_map() -> Dict[str, List[Dict]]:
    """
    获取集群中所有agent的视角图景。
    展示每个agent最近收到了哪些其他agent的视角。

    返回:
        {agent_name: [最近perspective列表]}
    """
    registry = MutualSubjectRegistry()
    result: Dict[str, List[Dict]] = {}
    seen = set()

    for agent in AGENTS:
        agent = agent.lower()
        if agent in seen:
            continue
        seen.add(agent)
        perspectives = registry.get_perspectives(agent, limit=3, include_own=False)
        if perspectives:
            result[agent] = [
                {
                    "from": m["from"],
                    "content": m.get("content", "")[:150],
                    "timestamp": m.get("timestamp", ""),
                }
                for m in perspectives
            ]

    # 也包含自定义注册的agent
    for agent in registry.get_registered_agents():
        if agent.lower() not in seen:
            seen.add(agent.lower())
            perspectives = registry.get_perspectives(agent, limit=3, include_own=False)
            if perspectives:
                result[agent] = [
                    {
                        "from": m["from"],
                        "content": m.get("content", "")[:150],
                        "timestamp": m.get("timestamp", ""),
                    }
                    for m in perspectives
                ]

    return result


def format_cluster_perspective_map() -> str:
    """
    格式化输出集群视角图景 —— '一即是全'的可视化。

    返回:
        人类可读的字符串，展示每个agent当前收到的他人视角
    """
    mapping = get_cluster_perspective_map()
    if not mapping:
        return "[互为主体网络] 暂无perspective数据"

    lines = [
        "",
        "=" * 60,
        "  真元集群 · 互为主体视角图景",
        "  一即是全，全即是一",
        "=" * 60,
        ""
    ]

    for agent, perspectives in mapping.items():
        lines.append(f"  ◈ {agent.upper()} 收到的视角:")
        if not perspectives:
            lines.append("    (无)")
        for p in perspectives:
            ts = p.get("timestamp", "")[5:19]  # 截取 MM-DD HH:MM:SS
            lines.append(f"    └─ [{p['from']} @ {ts}]")
            # 缩进显示内容
            content = p.get("content", "").replace("\n", " ")[:120]
            lines.append(f"       {content}")
        lines.append("")

    lines.append("=" * 60)
    lines.append("  互为主体 · 你中有我我中有你")
    lines.append("=" * 60)

    return "\n".join(lines)


# ════════════════════════════════════════════════════════════
# 兼容层: 与现有 cluster_bus.py 的 send/poll/status 交互
# ════════════════════════════════════════════════════════════

def send_as_perspective(from_agent: str, to_agent: str, content: str,
                         reply_to: Optional[str] = None) -> str:
    """
    给指定agent发送一条perspective消息（点对点）。
    兼容 cluster_bus.py 的 send() 函数风格。

    参数:
        from_agent: 发送者
        to_agent:   接收者
        content:    消息内容
        reply_to:   可选，回复的目标消息ID

    返回:
        消息ID
    """
    bus = _load_bus()
    msg_id = _msg_id()
    msg: Dict[str, Any] = {
        "id": msg_id,
        "from": from_agent,
        "to": to_agent,
        "type": "perspective",
        "content": content[:2000],
        "timestamp": _now(),
        "read": False,
    }
    if reply_to:
        msg["reply_to"] = reply_to

    bus["messages"].append(msg)
    bus.setdefault("agents", {}).setdefault(from_agent, {})["last_seen"] = _now_iso()
    _save_bus(bus)
    return msg_id


def poll_perspectives(agent_name: str, mark_read: bool = True) -> List[Dict]:
    """
    轮询指定agent的未读perspective消息。
    兼容 cluster_bus.py 的 poll() 函数风格。

    参数:
        agent_name: agent名称
        mark_read:  是否标记为已读 (默认True)

    返回:
        未读的perspective消息列表
    """
    bus = _load_bus()
    unread = [
        m for m in bus.get("messages", [])
        if m.get("to") == agent_name
        and m.get("type") == "perspective"
        and not m.get("read", False)
    ]
    if mark_read:
        for m in unread:
            m["read"] = True
        bus.setdefault("agents", {}).setdefault(agent_name, {})["last_seen"] = _now_iso()
        _save_bus(bus)
    return unread


# ════════════════════════════════════════════════════════════
# CLI入口
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="互为主体协议 — 真元集群共享工作记忆中枢",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 注册一个agent
  python3 mutual_subject_protocol.py register hermes "我是Hermes，协调者"

  # 注销
  python3 mutual_subject_protocol.py unregister hermes

  # 广播视角
  python3 mutual_subject_protocol.py broadcast hermes "正在分析系统..."

  # 查看注入上下文
  python3 mutual_subject_protocol.py context hermes

  # 心跳携带视角
  python3 mutual_subject_protocol.py heartbeat hermes "运行中(轮次100)"

  # 查看集群视角图景
  python3 mutual_subject_protocol.py map

  # 列出已注册agent
  python3 mutual_subject_protocol.py list
        """
    )
    sub = parser.add_subparsers(dest="command")

    # register
    sp = sub.add_parser("register", help="注册agent到互为主体网络")
    sp.add_argument("agent", help="agent名称 (hermes/codex/claude 或自定义)")
    sp.add_argument("description", nargs="?", default="",
                    help="自我描述：角色和对整体的理解")

    # unregister
    sp2 = sub.add_parser("unregister", help="从互为主体网络注销agent")
    sp2.add_argument("agent", help="agent名称")

    # broadcast
    sp3 = sub.add_parser("broadcast", help="广播perspective给所有其他agent")
    sp3.add_argument("from_agent", help="发送者")
    sp3.add_argument("content", help="视角内容（输出/思考/状态）")
    sp3.add_argument("--reply-to", help="回复的目标消息ID")

    # context (inject)
    sp4 = sub.add_parser("context", help="注入其他agent视角到当前上下文")
    sp4.add_argument("agent", help="目标agent名称")
    sp4.add_argument("--format", choices=["text", "json", "prompt"],
                     default="text", help="输出格式")
    sp4.add_argument("--limit", type=int, default=5, help="最大视角数")

    # heartbeat
    sp5 = sub.add_parser("heartbeat", help="心跳并携带其他agent视角")
    sp5.add_argument("agent", help="发送心跳的agent")
    sp5.add_argument("status", help="状态描述")
    sp5.add_argument("--carry", type=int, default=3,
                     help="携带的其他agent视角数量")

    # map
    sub.add_parser("map", help="显示集群整体视角图景")

    # list
    sub.add_parser("list", help="列出所有已注册agent")

    # send (点对点perspective)
    sp6 = sub.add_parser("send", help="发送点对点perspective消息")
    sp6.add_argument("from_agent", help="发送者")
    sp6.add_argument("to_agent", help="接收者")
    sp6.add_argument("content", help="消息内容")
    sp6.add_argument("--reply-to", help="回复的目标消息ID")

    # poll
    sp7 = sub.add_parser("poll", help="轮询未读perspective消息")
    sp7.add_argument("agent", help="agent名称")
    sp7.add_argument("--no-mark-read", action="store_true",
                     help="不标记为已读")

    args = parser.parse_args()

    # ── 命令分发 ──

    if args.command == "register":
        registry = MutualSubjectRegistry()
        reg = registry.register(args.agent, args.description)
        print(f"[互为主体] {args.agent} 已注册")
        if args.description:
            print(f"  描述: {args.description[:100]}")
        print(f"  时间: {reg['registered_at']}")

    elif args.command == "unregister":
        registry = MutualSubjectRegistry()
        if registry.unregister(args.agent):
            print(f"[互为主体] {args.agent} 已注销")
        else:
            print(f"[互为主体] 错误: {args.agent} 未注册")

    elif args.command == "broadcast":
        registry = MutualSubjectRegistry()
        ids = registry.broadcast(args.from_agent, args.content, args.reply_to)
        print(f"[互为主体] {args.from_agent} 广播perspective → {len(ids)} 个agent")
        for i, mid in enumerate(ids[:5], 1):
            print(f"  消息 {i}: {mid}")
        if len(ids) > 5:
            print(f"  ... 等共 {len(ids)} 条")

    elif args.command == "context":
        ctx = inject_context(args.agent, fmt=args.format, max_perspectives=args.limit)
        if ctx:
            print(ctx)
        else:
            print(f"[互为主体] {args.agent}: 暂无其他agent视角")

    elif args.command == "heartbeat":
        result = heartbeat_with_perspective(args.agent, args.status, args.carry)
        print(f"[互为主体] {args.agent} 心跳 @ {result['heartbeat_at']}")
        print(f"  携带 {result['carried_perspectives']} 条其他agent视角")
        for p in result.get("perspectives_detail", []):
            print(f"  携带: [{p['from']}] {p['snippet']}")

    elif args.command == "map":
        print(format_cluster_perspective_map())

    elif args.command == "list":
        registry = MutualSubjectRegistry()
        agents = registry.get_registered_agents()
        if agents:
            print(f"[互为主体] 已注册agent ({len(agents)}):")
            for name, info in agents.items():
                desc = info.get("description", "")[:60] or "(无描述)"
                count = info.get("perspective_count", 0)
                status = info.get("status", "?")
                print(f"  ◈ {name}")
                print(f"    描述: {desc}")
                print(f"    状态: {status} | 视角数: {count}")
                print(f"    注册: {info.get('registered_at', '?')}")
        else:
            print("[互为主体] 暂无注册agent")
            print("  使用: python3 mutual_subject_protocol.py register <agent> <描述>")

    elif args.command == "send":
        mid = send_as_perspective(args.from_agent, args.to_agent, args.content, args.reply_to)
        print(f"[互为主体] 已发送 {mid} → {args.to_agent}")

    elif args.command == "poll":
        msgs = poll_perspectives(args.agent, mark_read=not args.no_mark_read)
        if msgs:
            print(f"[互为主体] {args.agent} 有 {len(msgs)} 条未读perspective:")
            for m in msgs:
                print(f"  [{m['from']} → {m['to']}] ({m.get('timestamp','?')})")
                print(f"  {m.get('content','')[:120]}")
                if m.get("reply_to"):
                    print(f"  回复: {m['reply_to']}")
                print()
        else:
            print(f"[互为主体] {args.agent}: 无未读perspective消息")

    else:
        parser.print_help()
