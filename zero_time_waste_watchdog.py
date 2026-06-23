#!/usr/bin/env python3
"""
zero_time_waste_watchdog.py — 零·时间浪费看门狗
=================================================
每60秒检查一次：
1. 上次燃烧到现在隔了多久
2. 如果超过60秒无燃烧 → 记录浪费并立即触发燃烧
3. 每5轮运行p0_selector重新评分候选工程
4. 输出时间审计报告

核心原则：限时不限量API，每一秒不烧就是浪费。
"""
import json, os, sys, time, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def check_waste():
    """检查时间浪费"""
    now = time.time()
    waste_report = {"cycle": 0, "wasted_seconds": 0, "action": "none", "last_burn_age": 0}
    
    # 看burn_stats.json的last_burn时间
    bs_file = CLUSTER / "burn_stats.json"
    last_burn_time = 0
    
    # 也看_burn_results的最新文件修改时间
    results_dir = CLUSTER / "_burn_results"
    if results_dir.exists():
        latest = None
        for f in sorted(os.listdir(str(results_dir)), reverse=True):
            if f.endswith(".json") and f.startswith("burn_"):
                fp = results_dir / f
                mtime = os.path.getmtime(str(fp))
                if latest is None or mtime > latest:
                    latest = mtime
        if latest:
            last_burn_time = latest
    
    if last_burn_time == 0:
        waste_report["action"] = "no_burn_history"
        return waste_report
    
    age = now - last_burn_time
    waste_report["last_burn_age"] = int(age)
    
    if age > 120:  # 超过2分钟无燃烧 = 严重浪费
        waste_report["cycle"] = 1
        waste_report["wasted_seconds"] = int(age - 60)
        waste_report["action"] = "WASTE_DETECTED"
    elif age > 60:  # 超过1分钟 = 轻度浪费
        waste_report["cycle"] = 1
        waste_report["wasted_seconds"] = int(age - 60)
        waste_report["action"] = "warn"
    else:
        waste_report["action"] = "ok"
    
    return waste_report

def trigger_burn():
    """触发一次燃烧"""
    # 从缺口池选目标
    gaps = [
        "系统识别了4个模式，哪个是当前cycle最活跃的？基于state_vector数据判断。只使用上下文数据，不编造。",
        "审查burn_stats.json和state_vector.json。两文件之间是否存在数据不一致？设计修复方案。",
        "supersense_organ每cycle产出交叉洞察。如何让这些洞察自动触发一次burn.py深度燃烧？设计触发接口。",
        "对比最近10次燃烧的时间戳间隔。是否有超过2分钟无燃烧的时间窗口？输出具体时间窗口和修复建议。",
    ]
    import random
    goal = gaps[random.randint(0, len(gaps)-1)]
    
    try:
        r = subprocess.run(
            [sys.executable, "burn.py", goal],
            capture_output=True, text=True, timeout=300,
            cwd=str(CLUSTER)
        )
        for line in r.stdout.strip().split('\n')[-2:]:
            if '✅' in line:
                return line
        return r.stdout[-100:]
    except Exception as e:
        return f"err: {e}"

def run_p0_audit():
    """运行P0审计"""
    try:
        r = subprocess.run(
            [sys.executable, "p0_selector.py"],
            capture_output=True, text=True, timeout=30,
            cwd=str(CLUSTER)
        )
        return r.stdout[-200:]
    except:
        return "p0_audit failed"

def integrate():
    """运行集成"""
    try:
        subprocess.run(
            [sys.executable, "burn_state_integrator.py"],
            capture_output=True, timeout=30, cwd=str(CLUSTER)
        )
    except:
        pass

def main():
    audit_count = 0
    
    while True:
        # 北京时间
        now_bj = datetime.now(BJT)
        audit_count += 1
        
        # 1. 时间浪费审计
        waste = check_waste()
        
        # 2. 输出审计报告
        action_icon = "✅" if waste["action"] == "ok" else ("⚠️" if waste["action"] == "warn" else "🚨")
        print(f"[{ts()}] {action_icon} 审计#{audit_count} 上次燃烧{waste['last_burn_age']}s前", end="", flush=True)
        
        if waste["action"] in ("warn", "WASTE_DETECTED"):
            print(f" 浪费{waste['wasted_seconds']}s! 触发补偿燃烧...", end="", flush=True)
            result = trigger_burn()
            print(f" {result}", end="", flush=True)
            integrate()
        else:
            print("", end="")
        
        print(flush=True)
        
        # 3. 每5轮运行P0审计
        if audit_count % 5 == 0:
            print(f"[{ts()}] 🔍 P0审计触发...", flush=True)
            p0_report = run_p0_audit()
            for line in p0_report.split('\n'):
                if '🏆' in line or '选中' in line:
                    print(f"  {line.strip()}", flush=True)
        
        # 4. 每10轮运行19维审计
        if audit_count % 10 == 0:
            try:
                subprocess.run([sys.executable, "dim19_auditor.py"],
                              capture_output=True, timeout=30, cwd=str(CLUSTER))
                print(f"[{ts()}] 📊 19维审计完成", flush=True)
            except:
                pass
        # 5. 意识桥接更新(每10轮)
        if audit_count % 10 == 0:
            try:
                subprocess.run([sys.executable, "consciousness_bridge.py"],
                              capture_output=True, timeout=30, cwd=str(CLUSTER))
            except:
                pass
        
        # 4. 等待60秒
        time.sleep(60)

if __name__ == "__main__":
    print(f"[{ts()}] 🚨 零·时间浪费看门狗启动")
    print(f"[{ts()}] 检查间隔: 60秒 | 浪费阈值: 60s | 补偿: 自动燃烧")
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n[{ts()}] 看门狗停止")
