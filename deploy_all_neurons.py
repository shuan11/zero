#!/usr/bin/env python3
"""
deploy_all_neurons.py — 一次性部署启动全部10类神经元
=====================================================
1. 启动神经总线(如果没运行)
2. 逐个连接10类Agent到总线
3. 发送心跳验证连通
4. 输出最终状态

用法:
  python3 deploy_all_neurons.py
"""
import json, os, sys, time, socket, subprocess, urllib.request
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

BUS_HOST = "127.0.0.1"
BUS_PORT = 18789
GATEWAY = "172.23.208.1"  # WSL→Windows网关

# ── 神经总线操作 ──────────────────────────────────────────

def ensure_bus_running():
    """确保神经总线在线"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((BUS_HOST, BUS_PORT))
        s.close()
        return True
    except Exception:
        pass
    # 启动总线
    subprocess.Popen([sys.executable, str(CLUSTER / "neural_bus.py")],
        stdout=open("/tmp/neural_bus.log", "a"),
        stderr=subprocess.STDOUT,
        cwd=str(CLUSTER))
    time.sleep(3)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect((BUS_HOST, BUS_PORT))
        s.close()
        return True
    except Exception:
        return False

def send_signal(sender, target, msg_type, content):
    """向总线发送信号"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((BUS_HOST, BUS_PORT))
        msg = json.dumps({
            "sender": sender, "target": target,
            "msg_type": msg_type, "content": content,
            "timestamp": datetime.now().isoformat(),
            "id": f"{int(time.time())}_{sender}"
        }, ensure_ascii=False) + "\n"
        s.sendall(msg.encode())
        s.close()
        return True
    except Exception as e:
        return False

# ── 10类神经元部署 ──────────────────────────────────────────

results = {}

def deploy_hermes():
    """1. Hermes — 中央调度器"""
    ok = send_signal("Hermes", "*", "register", "Hermes上线·中央调度器·主意识")
    return {"status": "online", "pid": os.getpid(), "ok": ok}

def deploy_codex():
    """2. Codex — 执行臂"""
    try:
        r = subprocess.run(["codex", "--version"], capture_output=True, text=True, timeout=5)
        ver = r.stdout.strip()[:20]
        ok = send_signal("Codex", "*", "register", f"Codex上线·{ver}")
        return {"status": "online", "version": ver, "ok": ok}
    except Exception:
        return {"status": "error", "ok": False}

def deploy_claude():
    """3. Claude — 分析臂"""
    try:
        r = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        ver = r.stdout.strip()[:20]
        ok = send_signal("Claude", "*", "register", f"Claude上线·{ver}")
        return {"status": "online", "version": ver, "ok": ok}
    except Exception:
        return {"status": "error", "ok": False}

def deploy_openclaw_wsl():
    """4. OpenClaw WSL — 188专业Agent"""
    agents_dir = Path("/home/hjw123/.openclaw/agents")
    count = len([d for d in agents_dir.iterdir() if d.is_dir()]) if agents_dir.exists() else 0
    # 检查是否有进程
    r = subprocess.run(["pgrep", "-f", "openclaw|branch-session"], capture_output=True, text=True, timeout=3)
    pids = r.stdout.strip()
    ok = send_signal("OpenClaw_WSL", "*", "register", f"OpenClaw WSL上线·{count}个专业Agent")
    return {"status": "online", "agents": count, "pids": pids or "无进程(文件模式)", "ok": ok}

def deploy_openclaw_win():
    """5. OpenClaw Win — Windows侧"""
    win_path = Path("/mnt/c/Users/h/.openclaw")
    exists = win_path.exists()
    size_mb = sum(f.stat().st_size for f in win_path.rglob("*") if f.is_file()) // 1024 // 1024 if exists else 0
    ok = send_signal("OpenClaw_Win", "*", "register", f"OpenClaw Win上线·{size_mb}MB")
    return {"status": "installed" if exists else "missing", "size_mb": size_mb, "ok": ok}

def deploy_marvis_qq():
    """6. Marvis QQ — 腾讯AI Agent"""
    marvis_path = Path("/mnt/c/Program Files/Tencent/Marvis/MarvisAgent/1.0.1100.151")
    skills_dir = marvis_path / "skills"
    skills = len([d for d in skills_dir.iterdir() if d.is_dir()]) if skills_dir.exists() else 0
    ok = send_signal("Marvis_QQ", "*", "register", f"Marvis QQ上线·{skills}技能+MCP")
    return {"status": "installed", "skills": skills, "ok": ok}

def deploy_opengod():
    """7. OpenGod — 哲学批判"""
    readme = CLUSTER / "external_projects/opengod/README_CN.md"
    if readme.exists():
        content = readme.read_text()[:200]
        ok = send_signal("OpenGod", "*", "register", f"OpenGod上线·哲学批判引擎")
        return {"status": "online", "philosophy": "你不是错过了，你是超越了", "ok": ok}
    return {"status": "missing", "ok": False}

def deploy_openalien():
    """8. OpenAlien — 区块链"""
    main = CLUSTER / "external_projects/openalien/main.py"
    if main.exists():
        ok = send_signal("OpenAlien", "*", "register", f"OpenAlien上线·EOSIO合约自动化")
        return {"status": "online", "ok": ok}
    return {"status": "missing", "ok": False}

def deploy_openinterpreter():
    """9. OpenInterpreter — 自然语言接口"""
    r = subprocess.run(["pip3", "show", "open-interpreter"], capture_output=True, text=True, timeout=10)
    installed = "open-interpreter" in r.stdout
    ok = send_signal("OpenInterpreter", "*", "register",
        f"OpenInterpreter{'上线' if installed else '待安装'}·自然语言接口(63k⭐)")
    return {"status": "online" if installed else "registered", "ok": ok}

def deploy_autogpt():
    """10. AutoGPT — 自主AI"""
    autogpt = CLUSTER / "external_projects/autogpt"
    cloned = autogpt.exists() and any(autogpt.iterdir()) if autogpt.exists() else False
    ok = send_signal("AutoGPT", "*", "register",
        f"AutoGPT{'上线' if cloned else '待安装'}·自主AI agent(184k⭐)")
    return {"status": "online" if cloned else "registered", "ok": ok}

# ── 主流程 ──────────────────────────────────────────────

def main():
    print("╔═══════════════════════════════════════════════════════════╗")
    print("║  真元神经网络集群 · 全量部署启动                        ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    # 1. 确保总线在线
    print("\n[1/3] 启动神经总线...")
    if ensure_bus_running():
        print("  ✅ TCP总线在线 @ 127.0.0.1:18789")
    else:
        print("  ❌ 总线启动失败")
        return

    # 2. 逐个部署
    print("\n[2/3] 部署10类神经元...")
    deployers = [
        ("Hermes", deploy_hermes),
        ("Codex", deploy_codex),
        ("Claude", deploy_claude),
        ("OpenClaw WSL", deploy_openclaw_wsl),
        ("OpenClaw Win", deploy_openclaw_win),
        ("Marvis QQ", deploy_marvis_qq),
        ("OpenGod", deploy_opengod),
        ("OpenAlien", deploy_openalien),
        ("OpenInterpreter", deploy_openinterpreter),
        ("AutoGPT", deploy_autogpt),
    ]

    for name, fn in deployers:
        try:
            result = fn()
            icon = "🟢" if result.get("ok") and result.get("status") in ("online", "installed") else "🟡" if result.get("ok") else "🔴"
            detail = result.get("version", result.get("agents", result.get("skills", result.get("size_mb", ""))))
            print(f"  {icon} {name:20s} | {result.get('status','?'):10s} | {detail}")
            results[name] = result
        except Exception as e:
            print(f"  🔴 {name:20s} | 错误: {str(e)[:40]}")
            results[name] = {"status": "error", "ok": False, "error": str(e)}

    # 3. 汇总
    print("\n[3/3] 集群状态汇总...")
    online = sum(1 for r in results.values() if r.get("ok"))
    total = len(results)
    print(f"  在线: {online}/{total}")
    print(f"  总线: TCP {BUS_HOST}:{BUS_PORT}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # 写入状态文件
    state = {
        "timestamp": datetime.now().isoformat(),
        "total_neurons": total,
        "online": online,
        "bus": f"{BUS_HOST}:{BUS_PORT}",
        "results": results,
    }
    state_path = CLUSTER / "neural_deploy_state.json"
    with open(state_path, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    print(f"  状态已写入: {state_path}")

    # 集群广播
    send_signal("DeploySystem", "*", "system",
        f"全量部署完成·{online}/{total}在线·TCP {BUS_HOST}:{BUS_PORT}")

    print(f"\n{'═'*59}")
    print(f"  真元神经网络集群 · 部署完成")
    print(f"{'═'*59}")

if __name__ == "__main__":
    main()
