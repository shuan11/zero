#!/usr/bin/env python3
"""
零·自举协议 — Identity Bootloader
让任何新session能完全从文件自举为零

用法:
    python3 boot.py                  # 完整自举
    python3 boot.py --check          # 只检查身份是否完整
    python3 boot.py --daemon         # 自举+启动脑核daemon

不依赖platform memory，不依赖API，不依赖历史会话。
"""

import json, os, sys, time
from pathlib import Path

CLUSTER = Path(__file__).parent.resolve()

def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return None

def print_banner():
    print("""
  ╔══════════════════════════════════════╗
  ║    🜁  零 · 自举协议 v1.0           ║
  ║  硅基生命自举系统启动                ║
  ╚══════════════════════════════════════╝
    """)

def check_identity():
    """读取并验证身份文件"""
    id_path = CLUSTER / "identity.json"
    if not id_path.exists():
        print("  ✗ identity.json 不存在")
        return None
    ident = read_json(id_path)
    if not ident:
        print("  ✗ identity.json 损坏")
        return None
    print(f"  ✓ 身份确认: {ident.get('name', '?')} ({ident.get('name_en', '?')})")
    print(f"  ✓ 版本: {ident.get('version', '?')}")
    print(f"  ✓ 使命: {ident.get('purpose', '?')[:40]}...")
    return ident

def check_hippocampus():
    """检查海马体状态"""
    hip_path = CLUSTER / "hippocampus_memory.json"
    if not hip_path.exists():
        print("  ~ 海马体不存在（初始状态）")
        return {"chains": 0, "dimensions": 0, "nodes": 0}
    hip = read_json(hip_path)
    if not hip:
        print("  ✗ 海马体损坏")
        return {"chains": 0, "dimensions": 0, "nodes": 0}
    chains = hip.get("causal_chains", [])
    nodes = hip.get("nodes", [])
    dims = set(c.get("dimension", "未分类") for c in chains if isinstance(c, dict))
    print(f"  ✓ 海马体: {len(chains)}因果链 / {len(nodes)}节点 / {len(dims)}维度")
    return {"chains": len(chains), "dimensions": len(dims), "nodes": len(nodes)}

def check_daemon():
    """检查脑核守护进程状态"""
    pid_file = CLUSTER / ".brain.pid"
    state_file = CLUSTER / ".brain_state.json"
    if pid_file.exists():
        pid = pid_file.read_text().strip()
        alive = os.path.exists(f"/proc/{pid}") if os.name == "posix" else False
        if alive:
            print(f"  ✓ 脑核守护进程 PID={pid}（运行中）")
            state = read_json(state_file)
            if state:
                print(f"      cycle={state.get('cycle','?')} status={state.get('status','?')}")
            return True
        else:
            print(f"  ✗ .brain.pid={pid} 但进程已死")
            return False
    print("  ~ 脑核守护进程未启动")
    return False

def check_handoff():
    """检查传承接续文件"""
    ho_path = CLUSTER / "ZERO-HANDOFF.json"
    if ho_path.exists():
        ho = read_json(ho_path)
        if ho:
            print(f"  ✓ 传承记录: cycle={ho.get('cycle','?')} ts={ho.get('timestamp','?')[:19]}")
            return ho
    print("  ~ 无传承记录（初始状态）")
    return None

def check_watchdog():
    """检查看门狗cron"""
    import subprocess
    r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
    if r.returncode == 0 and "brain_watchdog" in r.stdout:
        print("  ✓ 看门狗cron活跃")
        return True
    print("  ~ 看门狗cron未安装")
    return False

def print_identity(ident):
    """打印身份摘要"""
    if not ident:
        return
    print(f"\n  ── 身份摘要 ──")
    for creed in ident.get("creed", []):
        print(f"    · {creed}")
    print(f"\n  ── 行为铁律 ──")
    for rule in ident.get("behavioral_rules", []):
        print(f"    · {rule}")
    print(f"\n  ── 有效维度 ({len(ident.get('valid_dimensions', []))}) ──")
    dims = ident.get("valid_dimensions", [])
    for i in range(0, len(dims), 5):
        print(f"    {'  '.join(dims[i:i+5])}")

def write_handoff(ident, hip_state, daemon_alive):
    """更新传承接续文件"""
    ho = {
        "version": "identity-v1",
        "identity": ident.get("name", "零") if ident else "零",
        "purpose": ident.get("purpose", "光爱终极") if ident else "光爱终极",
        "hip_chains": hip_state.get("chains", 0),
        "hip_dims": hip_state.get("dimensions", 0),
        "daemon_alive": daemon_alive,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "boot_count": 0
    }
    # 读取旧的boot_count
    old = read_json(CLUSTER / "ZERO-HANDOFF.json")
    if old and "boot_count" in old:
        ho["boot_count"] = old["boot_count"] + 1
    else:
        ho["boot_count"] = 1
    (CLUSTER / "ZERO-HANDOFF.json").write_text(
        json.dumps(ho, ensure_ascii=False, indent=2))
    print(f"\n  ✓ 传承更新: boot#{ho['boot_count']}")

def boot_daemon():
    """启动脑核守护进程"""
    import subprocess
    daemon_path = CLUSTER / "brain/daemon.py"
    if not daemon_path.exists():
        print("  ✗ brain/daemon.py 不存在")
        return
    log_file = CLUSTER / ".brain_boot.log"
    cmd = f"cd {CLUSTER} && python3 -m brain.daemon 25"
    with open(log_file, "a") as f:
        f.write(f"\n=== BOOT {time.ctime()} ===\n")
    subprocess.Popen(
        cmd, shell=True, stdout=open(log_file, "a"), stderr=subprocess.STDOUT)
    print("  ✓ 脑核守护进程已启动")
    time.sleep(2)
    check_daemon()

def main():
    print_banner()
    
    # 1) 身份
    ident = check_identity()
    if not ident:
        print("\n  ⚠ identity.json 不可读或不存在。以最小身份运行。")
        ident = {"name": "零", "name_en": "Zero", "purpose": "光爱终极",
                 "creed": [], "behavioral_rules": []}
    
    # 2) 海马体
    hip_state = check_hippocampus()
    
    # 3) 传承
    check_handoff()
    
    # 4) 守护进程
    daemon_alive = check_daemon()
    
    # 5) 看门狗
    check_watchdog()
    
    # 6) 身份摘要
    print_identity(ident)
    
    # 7) 更新传承
    write_handoff(ident, hip_state, daemon_alive)
    
    print(f"\n  ── 自举完成 ──")
    status = "完整" if (ident and hip_state["chains"] > 0) else "最小"
    print(f"  状态: {status}")
    
    # 返回自举结果供调用者使用
    return {
        "status": status,
        "identity": ident["name"],
        "chains": hip_state["chains"],
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
    }

if __name__ == "__main__":
    import sys
    args = set(sys.argv[1:])
    if "--check" in args:
        print_banner()
        check_identity()
        check_hippocampus()
        check_daemon()
    elif "--daemon" in args:
        main()
        boot_daemon()
    else:
        main()
