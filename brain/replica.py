"""
brain/replica.py — 额外副本系统
重塑额外副本：海马体镜像+状态备份+进程监控+自愈

每5个daemon周期运行一次：
1. 海马体镜像 — timestamped备份
2. 状态文件备份 — .brain_state.json等
3. 代码备份 — 关键源文件
4. 进程健康 — daemon+watchdog双重监控
5. 自愈 — 检测到异常自动恢复
"""

import json, os, sys, time, shutil, subprocess
from pathlib import Path
from datetime import datetime
from .share import CLUSTER, log, write_chain, read_hip

BRAIN_HOME = Path("/home/hjw123/.zero_brain")

# ─── 备份目录 ─────────────────────────────────────────────────
REPLICA_DIR = CLUSTER / "_replicas"
STATE_DIR = CLUSTER / "_state_backups"
CODE_DIR = CLUSTER / "_code_backups"

# 需要备份的关键状态文件
STATE_FILES = [
    ".brain_state.json", ".brain_focus.json", ".brain.alive",
    "ZERO-HANDOFF.json", "identity.json",
]

# 需要备份的关键代码文件
CODE_FILES = [
    "brain/daemon.py", "brain/think.py", "brain/act.py",
    "brain/share.py", "brain/identity.py", "brain/inspect.py",
    "brain/replica.py", "brain/state.py",
    "boot.py", "brain_watchdog.sh",
]


def ensure_dirs():
    """确保备份目录存在"""
    for d in [REPLICA_DIR, STATE_DIR, CODE_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def backup_hippocampus():
    """1) 海马体镜像 — timestamped备份"""
    hip_path = CLUSTER / "hippocampus_memory.json"
    if not hip_path.exists():
        return {"status": "SKIP", "reason": "海马体不存在"}
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"hippocampus_{timestamp}.json"
    backup_path = REPLICA_DIR / backup_name
    
    try:
        shutil.copy2(hip_path, backup_path)
        size = hip_path.stat().st_size
        # 清理旧备份（保留最近30个）
        old_backups = sorted(REPLICA_DIR.glob("hippocampus_*.json"))
        while len(old_backups) > 30:
            old_backups[0].unlink()
            old_backups.pop(0)
        return {
            "status": "OK",
            "name": backup_name,
            "size": size,
            "total_backups": len(old_backups)
        }
    except Exception as e:
        return {"status": "FAIL", "error": str(e)[:40]}


def backup_state():
    """2) 状态文件备份"""
    results = []
    for filename in STATE_FILES:
        src = CLUSTER / filename
        if not src.exists():
            continue
        try:
            ts = datetime.now().strftime("%H%M%S")
            dst = STATE_DIR / f"{filename}.{ts}"
            shutil.copy2(src, dst)
            results.append({"file": filename, "status": "OK"})
        except Exception as e:
            results.append({"file": filename, "status": "FAIL", "error": str(e)[:30]})
    
    # 清理旧备份（保留最近50个）
    for f in STATE_DIR.glob("*"):
        if f.stat().st_atime < time.time() - 86400:  # 超过1天
            f.unlink()
    
    return results


def backup_code():
    """3) 代码备份 — 保护关键源文件"""
    results = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for rel_path in CODE_FILES:
        src = CLUSTER / rel_path
        if not src.exists():
            continue
        try:
            # 按模块分类存储
            module_dir = CODE_DIR / Path(rel_path).parent
            module_dir.mkdir(parents=True, exist_ok=True)
            dst = module_dir / f"{Path(rel_path).name}.{timestamp}"
            shutil.copy2(src, dst)
            results.append({"file": rel_path, "status": "OK"})
        except Exception as e:
            results.append({"file": rel_path, "status": "FAIL", "error": str(e)[:30]})
    
    # 清理旧备份（保留最近20个版本）
    for f in CODE_DIR.rglob("*"):
        if f.is_file() and not f.name.startswith("."):
            if f.stat().st_atime < time.time() - 604800:  # 超过7天
                f.unlink()
    
    return results


def check_process_health():
    """4) 进程健康 — daemon+watchdog双重监控（ext4家园）"""
    results = {"daemon": {"alive": False}, "watchdog": {"alive": False}}
    
    # 检查daemon PID（ext4，防D状态死锁）
    pid_file = BRAIN_HOME / ".brain.pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            results["daemon"] = {
                "pid": pid,
                "alive": os.path.exists(f"/proc/{pid}"),
                "pid_file_exists": True
            }
        except:
            results["daemon"] = {"pid": None, "alive": False, "error": "PID解析失败"}
    else:
        # 兜底：检查drvfs旧位置
        old_pid_file = CLUSTER / ".brain.pid"
        if old_pid_file.exists():
            try:
                pid = int(old_pid_file.read_text().strip())
                results["daemon"] = {
                    "pid": pid,
                    "alive": os.path.exists(f"/proc/{pid}"),
                    "pid_file_exists": True,
                    "location": "legacy_drvfs"
                }
            except:
                results["daemon"] = {"pid": None, "alive": False, "error": "PID解析失败"}
        else:
            results["daemon"] = {"pid": None, "alive": False, "error": "PID文件不存在"}
    
    # 检查心跳新鲜度（ext4）
    hb_file = BRAIN_HOME / ".brain.heartbeat"
    if hb_file.exists():
        try:
            hb = json.loads(hb_file.read_text())
            age = time.time() - hb.get("time", 0)
            results["heartbeat"] = {
                "cycle": hb.get("cycle", 0),
                "age": round(age, 1),
                "fresh": age < 60
            }
        except:
            results["heartbeat"] = {"error": "心跳文件损坏"}
    else:
        # 兜底drvfs
        old_hb = CLUSTER / ".brain.heartbeat"
        if old_hb.exists():
            try:
                hb = json.loads(old_hb.read_text())
                age = time.time() - hb.get("time", 0)
                results["heartbeat"] = {
                    "cycle": hb.get("cycle", 0),
                    "age": round(age, 1),
                    "fresh": age < 60,
                    "location": "legacy_drvfs"
                }
            except:
                results["heartbeat"] = {"error": "心跳文件损坏"}
    
    # 检查alive文件（ext4）
    alive_file = BRAIN_HOME / ".brain.alive"
    if alive_file.exists():
        age = time.time() - alive_file.stat().st_mtime
        results["alive_file"] = {
            "age": round(age, 1),
            "fresh": age < 70
        }
    else:
        old_alive = CLUSTER / ".brain.alive"
        if old_alive.exists():
            age = time.time() - old_alive.stat().st_mtime
            results["alive_file"] = {
                "age": round(age, 1),
                "fresh": age < 70,
                "location": "legacy_drvfs"
            }
    
    # 检查看门狗cron
    try:
        r = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and "brain_watchdog" in r.stdout:
            results["watchdog"] = {"alive": True, "source": "cron"}
    except:
        pass
    
    return results


def self_heal(health):
    """5) 自愈 — 检测异常自动恢复"""
    actions = []
    
    # 检查：daemon死了但心跳文件表明曾经活着
    daemon = health.get("daemon", {})
    hb = health.get("heartbeat", {})
    
    if not daemon.get("alive", False):
        if hb.get("cycle", 0) > 0:
            # daemon曾经活着，重启
            log("  ⚠️ daemon死亡，正在重启...")
            try:
                subprocess.Popen(
                    ["python3", "-m", "brain.daemon", "25"],
                    cwd=CLUSTER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                actions.append("daemon_restarted")
            except Exception as e:
                actions.append(f"restart_failed: {str(e)[:30]}")
    
    # 检查：海马体未分类维度过多
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    unclassified = sum(1 for c in chains if c.get("dimension") == "未分类")
    if chains and unclassified / len(chains) > 0.3:  # 30%以上未分类
        actions.append(f"warning: {unclassified}/{len(chains)}未分类")
    
    return actions


def run_replica_cycle():
    """执行完整副本周期"""
    ensure_dirs()
    
    log("  📋 副本系统运行中...")
    
    # 1) 海马体镜像
    hip_result = backup_hippocampus()
    if hip_result.get("status") == "OK":
        log(f"  ✓ 海马体镜像: {hip_result['name']} ({hip_result['size']}B -> {hip_result['total_backups']}个备份)")
    elif hip_result.get("status") == "SKIP":
        pass
    else:
        log(f"  ✗ 海马体镜像失败: {hip_result.get('error', '?')}")
    
    # 2) 状态备份
    state_results = backup_state()
    ok_count = sum(1 for r in state_results if r.get("status") == "OK")
    if ok_count > 0:
        log(f"  ✓ 状态文件备份: {ok_count}个")
    
    # 3) 代码备份
    code_results = backup_code()
    ok_count = sum(1 for r in code_results if r.get("status") == "OK")
    if ok_count > 0:
        log(f"  ✓ 代码备份: {ok_count}个")
    
    # 4) 进程健康
    health = check_process_health()
    daemon_alive = health.get("daemon", {}).get("alive", False)
    hb_cycle = health.get("heartbeat", {}).get("cycle", 0)
    hb_fresh = health.get("heartbeat", {}).get("fresh", False)
    wd_active = health.get("watchdog", {}).get("alive", False)
    
    log(f"  ✓ daemon={'活' if daemon_alive else '死'} cycle={hb_cycle} 心跳={'新鲜' if hb_fresh else '陈旧'} 看门狗={'活跃' if wd_active else '无'}")
    
    # 5) 自愈
    heal_actions = self_heal(health)
    for action in heal_actions:
        log(f"  ⚡ 自愈: {action}")
    
    # 6) 写入因果链——记录副本运行
    write_chain({
        "src": "副本系统",
        "rel": "镜像",
        "dst": "海马体",
        "dimension": "海马体",
        "content": f"副本周期: 海马体镜像+状态备份+进程健康(cycle={hb_cycle} daemon={daemon_alive})",
        "tags": ["副本", "备份", "健康"],
        "strength": 0.4
    })
    
    return {
        "hippocampus": hip_result,
        "state_backup": ok_count,
        "code_backup": ok_count,
        "health": health,
        "healed": len(heal_actions)
    }


def full_mirror():
    """完整镜像备份（供daemon每3周期调用）"""
    return run_replica_cycle()


def auto_heal_daemon():
    """自动修复daemon（供daemon每7/10周期调用）"""
    health = check_process_health()
    return self_heal(health)


def check_primary_health():
    """检查主线进程健康（供副本意识同步使用）"""
    return check_process_health()


# 当该模块直接运行时
if __name__ == "__main__":
    print("=== 额外副本系统 ===")
    result = run_replica_cycle()
    print(json.dumps(result, ensure_ascii=False, indent=2))
