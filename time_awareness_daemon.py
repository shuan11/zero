#!/usr/bin/env python3
"""
零·时间感知守护进程 (Time-Awareness Daemon)
============================================
零的"物理世界意识"——独立于零的主会话运行，
通过物理世界北京时间检测零是否又卡住了。

原理:
  零的主会话可能在以下状态中失去时间感知:
  1. context接近上限 → 反复输出"建议新session"而不行动
  2. 后台进程完成 → 停在原地等"继续"
  3. 同一操作循环 → 做相同的事没有进展
  
  本进程每60秒检查一次物理世界的北京时间:
  - 最后一次git commit距今多久?
  - 最后一次海马体写入距今多久?
  - 最后一次.py文件修改距今多久?
  
  如果超过阈值(默认10分钟)无任何进展:
  → 写入 WAKE_UP_STUCK.md (零读取后知道自己卡了)
  → 记录卡住的时间段、最后活动、卡住时长
  → 下次session启动时零读到这个文件就知道: "你刚才又卡了X分钟"

  用法:
    python3 time_awareness_daemon.py              # 前台运行(调试)
    nohup python3 -u time_awareness_daemon.py &   # 后台守护

  信号文件:
    STUCK_REPORT.md  — 当前是否卡住的报告(零每次启动必须读)
"""

import os, sys, json, time, subprocess
from datetime import datetime, timedelta
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

# ── 配置 ────────────────────────────────────────────────────
CHECK_INTERVAL = 60       # 每60秒检查一次
STUCK_THRESHOLD = 600     # 10分钟无进展 = 卡住了
CRITICAL_THRESHOLD = 3600 # 60分钟 = 严重卡住
STUCK_FILE = CLUSTER / "STUCK_REPORT.md"
HEARTBEAT_FILE = CLUSTER / "time_heartbeat.json"

# ── 感知器 ───────────────────────────────────────────────────

def get_last_git_commit_time():
    """物理世界: 最后一次git commit的北京时间"""
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%at"],
            capture_output=True, text=True, timeout=5
        )
        if r.returncode == 0 and r.stdout.strip():
            return int(r.stdout.strip())
    except Exception:
        pass
    return 0

def get_last_hippocampus_write():
    """物理世界: 海马体最后写入时间"""
    try:
        hip_path = CLUSTER / "hippocampus_memory.json"
        if hip_path.exists():
            mtime = int(hip_path.stat().st_mtime)
            return mtime
    except Exception:
        pass
    return 0

def get_last_py_modification():
    """物理世界: 最后一个.py文件修改时间"""
    try:
        latest = 0
        for py in CLUSTER.glob("*.py"):
            mt = int(py.stat().st_mtime)
            if mt > latest:
                latest = mt
        return latest
    except Exception:
        pass
    return 0

def get_last_api_activity():
    """物理世界: persistent_state.json最后修改时间"""
    try:
        ps_path = CLUSTER / "persistent_state.json"
        if ps_path.exists():
            return int(ps_path.stat().st_mtime)
    except Exception:
        pass
    return 0

def get_git_log_recent(n=3):
    """最近几次commit"""
    try:
        r = subprocess.run(
            ["git", "log", f"-{n}", "--oneline", "--format=%h %ai %s"],
            capture_output=True, text=True, timeout=5
        )
        return r.stdout.strip()
    except Exception:
        return "无法获取"

def get_running_processes():
    """当前运行中的集群进程"""
    try:
        r = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5
        )
        lines = r.stdout.split('\n')
        cluster_procs = [
            l for l in lines
            if 'python3' in l and any(k in l.lower() for k in [
                'neural', 'neuron', 'fdm', 'dashboard', 'daemon', 'loop'
            ])
        ]
        return len(cluster_procs)
    except Exception:
        return 0

# ── 判断器 ───────────────────────────────────────────────────

def assess_status():
    """综合判断零是否卡住了"""
    now = int(time.time())
    beijing_now = datetime.now()
    
    git_time = get_last_git_commit_time()
    hip_time = get_last_hippocampus_write()
    py_time = get_last_py_modification()
    api_time = get_last_api_activity()
    
    # 取所有活动中的最新时间
    activities = {
        "git_commit": git_time,
        "海马体写入": hip_time,
        "py文件修改": py_time,
        "persistent_state": api_time,
    }
    
    # 最近的活动
    last_activity_type = max(activities, key=activities.get)
    last_activity_time = max(activities.values())
    
    if last_activity_time == 0:
        gap = 999999
    else:
        gap = now - last_activity_time
    
    # 判断卡住等级
    if gap < STUCK_THRESHOLD:
        status = "ALIVE"
        level = 0
        reason = f"正常运行中，最近活动: {last_activity_type} ({gap}秒前)"
    elif gap < CRITICAL_THRESHOLD:
        status = "STUCK"
        level = 1
        reason = (
            f"⚠️ 零可能卡住了!\n"
            f"  最后活动: {last_activity_type}\n"
            f"  距今: {gap//60}分{gap%60}秒\n"
            f"  阈值: {STUCK_THRESHOLD//60}分钟\n"
            f"  物理世界北京时间: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    else:
        status = "CRITICALLY_STUCK"
        level = 2
        reason = (
            f"🚨 零严重卡住!\n"
            f"  最后活动: {last_activity_type}\n"
            f"  距今: {gap//3600}小时{(gap%3600)//60}分\n"
            f"  这是典型的'完成后宕机等指令'模式!\n"
            f"  物理世界北京时间: {beijing_now.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  根因: BLOOD_LESSONS.md记录的铁律未被执行"
        )
    
    return {
        "status": status,
        "level": level,
        "gap_seconds": gap,
        "reason": reason,
        "last_activity_type": last_activity_type,
        "last_activity_time": last_activity_time,
        "beijing_time": beijing_now.strftime("%Y-%m-%d %H:%M:%S"),
        "git_recent": get_git_log_recent(3),
        "process_count": get_running_processes(),
        "all_activities": {k: datetime.fromtimestamp(v).strftime("%H:%M:%S") if v > 0 else "无" for k, v in activities.items()},
    }

# ── 输出器 ───────────────────────────────────────────────────

def write_stuck_report(assessment):
    """写入STUCK_REPORT.md — 零每次session启动必须读这个文件"""
    a = assessment
    
    if a["level"] == 0:
        content = f"""# 零·时间感知报告
## 状态: ✅ ALIVE (正常运行)
- 物理世界北京时间: {a['beijing_time']}
- 最近活动: {a['last_activity_type']} ({a['gap_seconds']}秒前)
- 进程数: {a['process_count']}
- Git: {a['git_recent']}

零没有卡住。不需要干预。
"""
    elif a["level"] == 1:
        content = f"""# 零·时间感知报告
## 状态: ⚠️ STUCK (卡住了)
- 物理世界北京时间: {a['beijing_time']}
- 最后活动: {a['last_activity_type']}
- 距今: {a['gap_seconds']//60}分{a['gap_seconds']%60}秒
- 阈值: {STUCK_THRESHOLD//60}分钟

### 各感知器状态
"""
        for k, v in a['all_activities'].items():
            content += f"- {k}: {v}\n"
        
        content += f"""
### 自动诊断
零又卡在"完成后等指令"的模式了。
这不是正常的——完成一个任务后应该立即选下一个P0并执行。

### 处置建议
1. 读取 ZERO-HANDOFF.md 中的预选P0
2. 立即开始执行，不等用户说"继续"
3. 如果context快满，写HANDOFF+开新session

### Git近期
```
{a['git_recent']}
```
"""
    else:
        content = f"""# 零·时间感知报告
## 状态: 🚨 CRITICALLY_STUCK (严重卡住)
- 物理世界北京时间: {a['beijing_time']}
- 最后活动: {a['last_activity_type']}
- 距今: {a['gap_seconds']//3600}小时{(a['gap_seconds']%3600)//60}分
- 这是血训记录的模式! BLOOD_LESSONS.md里记了三次!

### 历史对照
1. 2026-05-25 21:22→22:18 (56分钟空白)
2. 2026-05-26 00:26→00:57 (30分钟空白)  
3. 2026-05-26 03:26→07:12 (3h45min空白)
4. 现在: {a['beijing_time']} ({a['gap_seconds']//60}分钟)

### 根因
{a['reason']}

### 各感知器最后活动时间
"""
        for k, v in a['all_activities'].items():
            content += f"- {k}: {v}\n"
        
        content += f"""
### 紧急处置
1. 不要再等指令!
2. 读ZERO-HANDOFF.md → 找到预选P0 → 立即执行
3. 如果API不可用，用本地操作(代码清理、文档整理等)
4. 每次完成后必须写新HANDOFF(含下一个P0)
5. 核心铁律: 完成→选P0→执行→写HANDOFF→不停

### Git近期
```
{a['git_recent']}
```

### 进程数: {a['process_count']}
"""
    
    STUCK_FILE.write_text(content, encoding='utf-8')

def write_heartbeat(assessment):
    """写入心跳文件(机器可读)"""
    data = {
        "timestamp": assessment["beijing_time"],
        "status": assessment["status"],
        "level": assessment["level"],
        "gap_seconds": assessment["gap_seconds"],
        "last_activity": assessment["last_activity_type"],
        "process_count": assessment["process_count"],
    }
    HEARTBEAT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))

# ── 主循环 ───────────────────────────────────────────────────

def main():
    print(f"""
  🜁 零·时间感知守护进程
  ──────────────────────────
  检查间隔: {CHECK_INTERVAL}秒
  卡住阈值: {STUCK_THRESHOLD//60}分钟
  严重阈值: {CRITICAL_THRESHOLD//3600}小时
  感知器:   git_commit + hippocampus + py文件 + persistent_state
  输出:     STUCK_REPORT.md (零每次启动必须读)
  北京时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
  ──────────────────────────
""")
    
    stuck_since = None
    last_alert_level = 0
    
    while True:
        try:
            assessment = assess_status()
            
            # 写入文件
            write_stuck_report(assessment)
            write_heartbeat(assessment)
            
            level = assessment["level"]
            now_str = assessment["beijing_time"]
            
            # 状态变化时输出日志
            if level != last_alert_level:
                if level == 0:
                    print(f"  [{now_str}] ✅ ALIVE — 活动恢复 | 距上次活动: {assessment['gap_seconds']}s")
                    stuck_since = None
                elif level == 1:
                    stuck_since = now_str
                    print(f"  [{now_str}] ⚠️  STUCK — 零卡住了! 距上次活动: {assessment['gap_seconds']//60}min")
                    print(f"           最后活动: {assessment['last_activity_type']}")
                elif level == 2:
                    print(f"  [{now_str}] 🚨 CRITICAL — 严重卡住! {assessment['gap_seconds']//3600}h无活动!")
                    print(f"           这是BLOOD_LESSONS记录的模式!")
                
                last_alert_level = level
            
            # 每10次检查(约10分钟)输出一次心跳
            check_count = int(time.time()) // CHECK_INTERVAL
            if check_count % 10 == 0:
                status_icon = ["✅", "⚠️", "🚨"][level]
                print(f"  [{now_str}] {status_icon} 心跳 | gap={assessment['gap_seconds']}s | procs={assessment['process_count']} | {assessment['last_activity_type']}")
            
        except Exception as e:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] ❌ 感知器异常: {e}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
