#!/usr/bin/env python3
"""brain_watchdog.py — 脑核守护者（cron每2分钟调用）
如果brain.daemon死亡，自动重启。
日志: /home/hjw123/.zero_brain/watchdog.log（ext4安全）
"""
import os, sys, subprocess, json, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
BRAIN_HOME = Path("/home/hjw123/.zero_brain")
BRAIN_HOME.mkdir(parents=True, exist_ok=True)
LOG = BRAIN_HOME / "watchdog.log"
PID_FILE = BRAIN_HOME / ".brain.pid"

def log(msg):
    t = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a") as f:
        f.write(f"[{t}] {msg}\n")

def is_alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def find_brain():
    """pgrep找brain.daemon，返回PID列表"""
    r = subprocess.run(
        ["pgrep", "-f", r"^python3.*brain(/|\.)daemon"],
        capture_output=True, text=True, timeout=5
    )
    pids = [int(p) for p in r.stdout.strip().split() if p]
    # 排除bash包装器
    valid = []
    for pid in pids:
        try:
            cmd = Path(f"/proc/{pid}/cmdline").read_text().replace("\0", " ")
            if "python3" in cmd and "brain" in cmd:
                valid.append(pid)
        except OSError:
            continue
    return valid

def restart():
    log("脑核死亡 → 启动重启...")
    # 日志轮换：超过1MB则归档
    log_path = CLUSTER / ".brain_daemon.log"
    if log_path.exists() and log_path.stat().st_size > 1024 * 1024:
        import shutil
        archive = CLUSTER / f".brain_daemon.{int(time.time())}.log"
        shutil.move(str(log_path), str(archive))
        log(f"日志轮换: {archive.name} ({log_path.stat().st_size} bytes)")
    subprocess.run(
        ["nohup", "python3", "-m", "brain.daemon"],
        cwd=str(CLUSTER),
        stdout=open(str(log_path), "w"),
        stderr=subprocess.STDOUT,
        preexec_fn=os.setsid,
    )
    time.sleep(3)
    pids = find_brain()
    if pids:
        log(f"脑核重启成功 PID={pids}")
    else:
        log("脑核重启失败！")
        # 致命: wsl --terminate自愈
        if os.path.exists("/proc/sys/fs/binfmt_misc/WSLInterop"):
            subprocess.run(["wsl.exe", "--terminate", "Ubuntu"],
                         capture_output=True, timeout=10)

if __name__ == "__main__":
    pids = find_brain()
    if not pids:
        log(f"未找到脑核进程 → 重启")
        restart()
    else:
        # 检查PID文件一致性
        pid_from_file = None
        if PID_FILE.exists():
            try:
                pid_from_file = int(PID_FILE.read_text().strip())
            except (ValueError, OSError):
                pass
        if pid_from_file and pid_from_file not in pids:
            log(f"PID文件={pid_from_file}但不在{pids}中 → 脑核异常，杀死全部重启")
            for p in pids:
                try:
                    os.kill(p, 9)
                except OSError:
                    pass
            time.sleep(1)
            restart()
        else:
            log(f"脑核正常 (PIDs={pids})")
