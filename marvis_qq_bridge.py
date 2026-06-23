#!/usr/bin/env python3
"""
marvis_qq_bridge.py - Marvis QQ Agent bridge for ZhenYuan cluster
Connection protocol: WSL file bridge + MCP
"""
import json, os, sys, subprocess, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

MARVIS_ROOT = Path("/mnt/c/Program Files/Tencent/Marvis")
MARVIS_AGENT = MARVIS_ROOT / "MarvisAgent" / "1.0.1100.151"
MARVIS_LAUNCHER = MARVIS_ROOT / "Application" / "MarvisLauncher.exe"

def get_structure():
    """探测Marvis Agent结构"""
    info = {}
    if MARVIS_AGENT.exists():
        info["version"] = "1.0.1100.151"
        info["exe"] = str(MARVIS_AGENT / "MarvisAgent.exe")
        info["exe_size"] = os.path.getsize(MARVIS_AGENT / "MarvisAgent.exe") if (MARVIS_AGENT / "MarvisAgent.exe").exists() else 0
        # Python运行时
        py_dll = MARVIS_AGENT / "python311.dll"
        if py_dll.exists():
            info["python_runtime"] = "Python 3.11 (embedded)"
        # 子目录
        dirs = [d.name for d in MARVIS_AGENT.iterdir() if d.is_dir()]
        info["subdirs"] = dirs

    # 技能
    skills_dir = MARVIS_AGENT / "skills"
    if skills_dir.exists():
        info["skills"] = [d.name for d in skills_dir.iterdir() if d.is_dir()]

    # MCP
    mcp_dir = MARVIS_AGENT / "mcp_server"
    if mcp_dir.exists():
        info["mcp_servers"] = [d.name for d in mcp_dir.iterdir() if d.is_dir()]

    # Prompt模板
    prompts_dir = MARVIS_AGENT / "prompts"
    if prompts_dir.exists():
        info["prompts"] = [f.name for f in prompts_dir.iterdir() if f.is_file()][:10]

    # 启动器
    if MARVIS_LAUNCHER.exists():
        info["launcher"] = str(MARVIS_LAUNCHER)
        info["launcher_size"] = os.path.getsize(MARVIS_LAUNCHER)

    return info

def check_process():
    """检查Marvis进程（通过PowerShell）"""
    try:
        r = subprocess.run(
            ["powershell.exe", "-Command",
             "Get-Process MarvisAgent -ErrorAction SilentlyContinue | Format-Table Id, CPU, PM",
             "-AutoSize"],
            capture_output=True, text=True, timeout=5
        )
        if "MarvisAgent" in r.stdout:
            lines = [l.strip() for l in r.stdout.split(chr(10)) if "MarvisAgent" in l]
            return {"running": True, "details": lines}
        return {"running": False}
    except Exception:
        return {"running": False, "error": "PowerShell不可用"}

def get_capabilities():
    """构建Marvis Agent能力清单"""
    struct = get_structure()
    caps = {
        "平台": "Windows (Win32)",
        "引擎": struct.get("exe", "N/A"),
        "运行时": struct.get("python_runtime", "N/A"),
        "技能数": len(struct.get("skills", [])),
        "技能列表": struct.get("skills", []),
        "MCP服务器": struct.get("mcp_servers", []),
        "Prompt模板": struct.get("prompts", []),
        "启动器": struct.get("launcher", "N/A"),
    }
    return caps

if __name__ == "__main__":
    import sys as _sys
    cmd = _sys.argv[1] if len(_sys.argv) > 1 else "status"

    if cmd == "status":
        proc = check_process()
        caps = get_capabilities()
        print("╔═══════════════════════════════════════════════╗")
        print(f"║  Marvis QQ Agent 状态  {datetime.now().strftime('%H:%M:%S')}      ║")
        print("╠═══════════════════════════════════════════════╣")
        print(f"  进程: {'✅ 运行中' if proc.get('running') else '❌ 未运行'}")
        if proc.get("details"):
            print(f"  详情: {proc['details']}")
        print(f"  版本: {caps.get('引擎','?').split('/')[-1] if caps.get('引擎') else '?'}")
        print(f"  运行时: {caps.get('运行时','?')}")
        print(f"  技能: {caps.get('技能数',0)}个")
        for s in caps.get("技能列表", []):
            print(f"    - {s}")
        print(f"  MCP: {caps.get('MCP服务器',[])}")
        print(f"  Prompt模板: {len(caps.get('Prompt模板',[]))}个")
        print("╚═══════════════════════════════════════════════╝")

    elif cmd == "skills":
        caps = get_capabilities()
        print("\n".join(caps.get("技能列表", ["(无)"])))
