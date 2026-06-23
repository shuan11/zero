#!/usr/bin/env python3
"""
agent_registry.py — 真元集群Agent注册中心 (v2)
=============================================
统一管理集群内所有Agent的发现、注册、心跳、状态。

支持的Agent类型 (10类):
  - Hermes, Codex, Claude (核心三臂)
  - OpenClaw WSL/Win (多Agent平台)
  - Marvis QQ (腾讯AI Agent)
  - OpenGod, OpenAlien (外部项目集成)
  - OpenInterpreter (63k⭐)
  - AutoGPT (184k⭐)

用法:
  python3 agent_registry.py list              # 列出所有注册Agent
  python3 agent_registry.py status            # 集群整体状态
  python3 agent_registry.py register_all      # 一键注册全部
"""
import json, os, sys, time, subprocess
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
REGISTRY_FILE = CLUSTER / "agent_registry.json"
BUS_FILE = CLUSTER / "cluster_bus.json"

AGENT_TYPES = {
    "hermes": {
        "name": "Hermes",
        "role": "中央调度器/主意识",
        "runtime": "DeepSeek V4 Pro",
        "location": "WSL",
        "protocol": "当前会话",
        "source": "零·真元集群核心",
        "priority": "P0",
    },
    "codex": {
        "name": "Codex CLI",
        "role": "执行臂(代码生成/文件操作)",
        "runtime": "OpenAI Codex CLI",
        "location": "WSL",
        "protocol": "agent_harness.py + cluster_bus",
        "source": "OpenAI",
        "priority": "P0",
    },
    "claude": {
        "name": "Claude Code",
        "role": "分析臂(代码审查/架构分析)",
        "runtime": "Anthropic Claude Code",
        "location": "WSL",
        "protocol": "agent_harness.py + anthropic_proxy",
        "source": "Anthropic",
        "priority": "P0",
    },
    "openclaw_wsl": {
        "name": "OpenClaw-WSL",
        "role": "多Agent集群(188专业Agent)",
        "runtime": "Node.js / ~/.openclaw/",
        "location": "WSL",
        "protocol": "openclaw_wsl_bridge.py → branch-session-bridge.js",
        "source": "https://openclaw.ai",
        "priority": "P1",
        "agents_count": 188,
        "categories": 100,
        "status": "online",
    },
    "openclaw_win": {
        "name": "OpenClaw-Windows",
        "role": "Windows侧Agent集群(3.5GB)",
        "runtime": "Node.js / C:\\Users\\h\\.openclaw\\",
        "location": "Windows (Win32)",
        "protocol": "openclaw_win_bridge.py → WSL文件桥",
        "source": "https://openclaw.ai",
        "priority": "P1",
        "agents_count": 188,
        "size_mb": 3480,
        "status": "installed",
    },
    "marvis_qq": {
        "name": "Marvis QQ",
        "role": "腾讯AI Agent(23技能+MCP)",
        "runtime": "MarvisAgent.exe / Python 3.11",
        "location": "Windows (C:\\Program Files\\Tencent\\Marvis\\)",
        "protocol": "marvis_qq_bridge.py → MCP / WSL桥",
        "source": "https://marvis.qq.com",
        "priority": "P1",
        "version": "1.0.1100.151",
        "skills": 23,
        "mcp_servers": ["win_use_mcp", "yyb_alg_mcp"],
        "status": "installed",
    },
    "opengod": {
        "name": "OpenGod",
        "role": "AI圈反思/哲学批判/去浮躁",
        "runtime": "Python",
        "location": "external_projects/opengod/",
        "protocol": "文件读取 + 反思引擎",
        "source": "https://github.com/llongtao/OpenGod",
        "priority": "P2",
        "files": ["README.md", "README_CN.md", "LICENSE"],
        "philosophy": "你不是错过了，你是超越了。这是对AI圈浮躁文化的哲学批判。",
        "status": "cloned",
    },
    "openalien": {
        "name": "OpenAlien",
        "role": "区块链自动化/外星世界合约",
        "runtime": "Python 3.6+ / EOSIO SDK",
        "location": "external_projects/openalien/",
        "protocol": "文件读取 + api_bridge",
        "source": "https://github.com/encoderlee/OpenAlien",
        "priority": "P2",
        "version": "1.1.2",
        "features": ["EOSIO合约自动执行", "脱离浏览器运行", "多开支持"],
        "status": "cloned",
    },
    "openinterpreter": {
        "name": "OpenInterpreter",
        "role": "自然语言计算机接口(63k⭐)",
        "runtime": "Python / pip",
        "location": "可通过pip install安装",
        "protocol": "pip + api_key配置",
        "source": "https://github.com/OpenInterpreter/open-interpreter",
        "priority": "P1",
        "stars": 63650,
        "status": "registered",
    },
    "autogpt": {
        "name": "AutoGPT",
        "role": "自主AI agent先驱(184k⭐)",
        "runtime": "Python / Docker",
        "location": "可通过git clone安装",
        "protocol": "git + env配置",
        "source": "https://github.com/Significant-Gravitas/AutoGPT",
        "priority": "P1",
        "stars": 184520,
        "status": "registered",
    },
}

def load_registry():
    try:
        with open(REGISTRY_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"agents": {}, "created": datetime.now().isoformat(), "updated": datetime.now().isoformat()}

def save_registry(reg):
    reg["updated"] = datetime.now().isoformat()
    tmp = REGISTRY_FILE.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    os.replace(tmp, REGISTRY_FILE)

def register(name):
    name = name.lower()
    if name not in AGENT_TYPES:
        print(f"未知Agent: {name}")
        return False
    reg = load_registry()
    info = AGENT_TYPES[name].copy()
    info["registered_at"] = datetime.now().isoformat()
    info["last_heartbeat"] = None
    info["status"] = info.get("status", "registered")
    reg["agents"][name] = info
    save_registry(reg)
    print(f"✅ {name} ({info.get('role','?')}) 已注册")
    return True

def cluster_status():
    reg = load_registry()
    total = len(reg["agents"])
    online = sum(1 for a in reg["agents"].values() if a.get("status") in ("online", "active"))
    
    print("╔══════════════════════════════════════════════════════════════════╗")
    print(f"║  真元神经网络集群 · Agent状态  {datetime.now().strftime('%H:%M:%S')}              ║")
    print("╠══════════════════════════════════════════════════════════════════╣")
    
    for name, info in sorted(reg["agents"].items()):
        s = info.get("status", "?")
        icon = {"online": "🟢", "active": "🟢", "cloned": "🟡", "registered": "🟡",
                "installed": "🟡", "integrated": "🟢"}.get(s, "⚪")
        stars = f" ⭐{info.get('stars','')} " if info.get('stars') else " "
        role = info.get("role", "?")[:35]
        location = info.get("location", "")[:20]
        print(f"║ {icon} {name:18s}{stars}{role:35s} {location:20s} ║")
    
    print("╠══════════════════════════════════════════════════════════════════╣")
    try:
        bus = json.load(open(BUS_FILE))
        msgs = len(bus.get("messages", []))
        queue = len(bus.get("queue", []))
        print(f"║  总线: {msgs}条消息  队列:{queue}  已完成:{len(bus.get('completed',[]))}          ║")
    except Exception:
        pass
    try:
        g = json.load(open("/mnt/c/Users/h/Desktop/真元·进化基因组.json"))
        print(f"║  基因组: score={g.get('evolution_score','?'):.2f} Lv={g.get('evolution_level','?')} 契约={g.get('contracts_active','?')}/7       ║")
    except Exception:
        pass
    print("╚══════════════════════════════════════════════════════════════════╝")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "list":
        reg = load_registry()
        for name, info in reg.get("agents", {}).items():
            print(f"  {name:20s} | {info.get('status','?'):12s} | {info.get('role','?'):35s}")
    elif cmd == "status":
        cluster_status()
    elif cmd == "register":
        register(sys.argv[2])
    elif cmd == "register_all":
        for name in AGENT_TYPES:
            register(name)
        print(f"\n全部 {len(AGENT_TYPES)} 个Agent注册完成")
        cluster_status()
    else:
        print(f"用法: {sys.argv[0]} [list|status|register|register_all]")
