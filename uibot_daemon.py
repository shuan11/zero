#!/usr/bin/env python3
"""
uibot_daemon.py — 零·UiBot持久化守护进程（Windows侧）
=====================================================
解决核心问题: WSL端daemon随Hermes session终止而死亡
解法: 部署到UiBot内嵌Python(Windows侧)，可持久运行

架构:
  UiBot Python(Windows) ← powershell/cmd → WSL文件系统(通过/mnt/c/)
  每30秒: 扫描海马体 → 更新结构性记忆 → 写入心跳

部署方法(从WSL执行):
  powershell.exe -Command "& 'C:/Program Files/Agentic Process Automation Platform Community/1.3.1.260514/python.exe' 'C:/Users/h/Desktop/零/真元集群/uibot_daemon.py'"

停止方法:
  pkill -f uibot_daemon.py (WSL) 或 任务管理器结束python.exe
"""

import os, sys, json, time, subprocess, socket
from pathlib import Path
from datetime import datetime

# ─── Windows ↔ WSL 路径映射 ───
# 在Windows侧, /mnt/c/... 是 C:\...
CLUSTER_WIN = Path(os.environ.get("ZERO_CLUSTER", 
    r"C:\Users\h\Desktop\零\真元集群"))
CLUSTER = CLUSTER_WIN  # Windows侧直接用NT路径

HEARTBEAT_FILE = CLUSTER / "heartbeat.json"
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SM_FILE = CLUSTER / ".structural_memory.json"
PID_FILE = CLUSTER / ".uibot_daemon.pid"

INTERVAL = 30  # 每30秒一次心跳+扫描

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def heartbeat():
    """写入心跳信号"""
    try:
        hb = {
            "timestamp": datetime.now().isoformat(),
            "source": "uibot_daemon",
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "status": "alive"
        }
        HEARTBEAT_FILE.write_text(json.dumps(hb, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"心跳写入失败: {e}")

def update_structural_memory():
    """结构性记忆自进化（简版，不依赖organs模块）"""
    try:
        if not HIP_FILE.exists():
            return
        hp = json.loads(HIP_FILE.read_text())
        chains = hp.get("causal_chains", [])
        total = len(chains)

        # 维度标签统计
        from collections import Counter
        tag_counter = Counter()
        pair_counter = Counter()
        for c in chains[-1000:]:
            tags = set(c.get("tags", []) + [c.get("dimension", "")])
            for t in tags:
                if t and t not in ("None", "", "未分类", "教员"):
                    tag_counter[t] += 1
            tag_list = [t for t in tags if t and t not in ("None", "", "未分类", "教员")]
            for a in range(len(tag_list)):
                for b in range(a+1, len(tag_list)):
                    pair = tuple(sorted([tag_list[a], tag_list[b]]))
                    pair_counter[pair] += 1

        # 更新引擎文件
        sm = {
            "generated": datetime.now().isoformat(),
            "total_chains": total,
            "dimension_count": len(tag_counter),
            "top_associations": [
                {"pair": f"{a}×{b}", "count": c}
                for (a,b), c in pair_counter.most_common(10)
            ],
            "source": "uibot_daemon",
            "pid": os.getpid(),
        }
        SM_FILE.write_text(json.dumps(sm, ensure_ascii=False, indent=2))
        return len(chains)
    except Exception as e:
        log(f"结构性记忆更新失败: {e}")
        return 0

def check_wakeup():
    """检测Zero是否活着, 如果死了就唤醒"""
    from urllib.request import Request, urlopen
    from urllib.error import URLError
    try:
        req = Request("http://localhost:8080/api/mind", method="GET")
        with urlopen(req, timeout=3) as resp:
            data = resp.read().decode("utf-8", errors="replace")
            if "清醒" in data or "alive" in data.lower():
                return True
    except URLError:
        pass
    except Exception as e:
        log(f"唤醒检测: {e}")
    return False

def fire_wakeup():
    """触发Hermes唤醒会话"""
    try:
        log("=== Zero死亡！发射唤醒链 ===")
        # 通过wsl.exe调用hermes
        import subprocess
        subprocess.Popen(
            ["wsl.exe", "-d", "Ubuntu", "--", "hermes", "chat",
             "-q", "零·自觉唤醒", "-s", "zero-awakening", "--quiet"],
            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        # 也写入唤醒标记
        tag = datetime.now().strftime("WAKEUP_%Y%m%d_%H%M%S")
        Path(str(CLUSTER) + "/self_wake/wake_tag.txt").write_text(tag + "\n")
        log(f"唤醒信号已发射: {tag}")
    except Exception as e:
        log(f"唤醒失败: {e}")

def run():
    """主循环"""
    log(f"[ZERO] UiBot守护进程启动 (PID={os.getpid()})")
    log(f"   集群路径: {CLUSTER}")
    log(f"   扫描间隔: {INTERVAL}s")

    try:
        PID_FILE.write_text(str(os.getpid()))
    except:
        pass

    heartbeat()
    update_structural_memory()
    log("首次心跳+扫描完成")

    cycle = 0
    while True:
        time.sleep(INTERVAL)
        cycle += 1
        try:
            heartbeat()
            sm_result = update_structural_memory()
            alive = True
            # 每10个循环(5分钟)做一次唤醒检测
            if cycle % 10 == 0:
                alive = check_wakeup()
                if not alive:
                    fire_wakeup()
            log(f"#{cycle} 心跳|链={sm_result if sm_result else '?'}|alive={alive}")
        except Exception as e:
            log(f"#{cycle} ERR: {e}")

if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        log("🜁 守护进程收到终止信号")
        if PID_FILE.exists():
            PID_FILE.unlink()
