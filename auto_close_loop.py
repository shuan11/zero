#!/usr/bin/env python3
"""
零·自动闭环系统 — gap→triage→fix→verify
========================================
meta_gap_finder只发现缺口，这个模块修复缺口。
每次被health_check.sh或cron调用，扫描一次，修复可修的gap。

修复规则：
  daemon dead  → 检查脚本是否存在，若存在则重启
  evolution_stuck → 触发本地进化
  recursion_stuck → 触发meta_recursion
  external_projects  → 只报告（需要人工判断）
"""

import sys, os, json, time, subprocess
from pathlib import Path

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(WORKDIR))
sys.path.insert(0, str(WORKDIR))

LOGFILE = WORKDIR / "logs" / "auto_close_loop.log"
LOGFILE.parent.mkdir(exist_ok=True)

def log(msg):
    line = f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")
    print(line)

def load_gaps():
    """从neural_working_memory.json读取meta_gap_finder的缺口"""
    nwm_path = WORKDIR / "neural_working_memory.json"
    if not nwm_path.exists():
        return {}
    with open(nwm_path) as f:
        nwm = json.load(f)
    gaps_section = nwm.get("modules", {}).get("meta_gap_finder", {})
    gaps = {}
    for k, v in gaps_section.items():
        if k.startswith("latest_gap_") and isinstance(v, dict):
            gaps[v["id"]] = v
    return gaps

def fix_daemon_gap(gap):
    """重启死亡的守护进程"""
    desc = gap.get("desc", "")
    # 从描述中推断进程名
    proc_map = {
        "永久意识守护进程": "permanent_daemon.py",
        "意识守护进程": "consciousness_daemon_v2.py",
        "auto_evolution": "auto_evolution_daemon.py",
        "co_evolution": "co_evolution_daemon.py",
        "comprehension": "comprehension_daemon.py",
    }
    script = None
    for key, val in proc_map.items():
        if key in desc:
            script = val
            break
    if script is None:
        return False, f"无法从描述推断脚本: {desc[:60]}"

    script_path = WORKDIR / script
    if not script_path.exists():
        return False, f"脚本不存在: {script}"

    # 检查是否已在运行
    proc_name = script.replace(".py", "")
    r = subprocess.run(["pgrep", "-f", proc_name], capture_output=True, text=True)
    if r.returncode == 0:
        return True, f"{proc_name} 已在运行 (PID {r.stdout.strip()})"

    # 重启
    log_path = WORKDIR / "logs" / f"{proc_name}.log"
    log_path.parent.mkdir(exist_ok=True)
    subprocess.Popen(
        ["python3", "-u", str(script_path)],
        stdout=open(log_path, "a"),
        stderr=subprocess.STDOUT,
        cwd=str(WORKDIR),
        start_new_session=True,
    )
    time.sleep(2)
    r2 = subprocess.run(["pgrep", "-f", proc_name], capture_output=True, text=True)
    if r2.returncode == 0:
        return True, f"{proc_name} 重启成功 (PID {r2.stdout.strip()})"
    return False, f"{proc_name} 重启失败"

def fix_evolution_stuck(gap):
    """进化卡住 → 触发本地进化"""
    try:
        from persistent_engine import get_engine, save_state
        engine = get_engine()
        s0 = engine.p513.evolution_score
        for _ in range(500):
            engine.evolve()
        save_state({
            "evolution_score": engine.p513.evolution_score,
            "recursion_depth": engine.p513.recursion_depth,
        })
        delta = engine.p513.evolution_score - s0
        return True, f"score +{delta:.1f}"
    except Exception as e:
        return False, f"进化失败: {str(e)[:80]}"

def fix_recursion_stuck(gap):
    """递归卡住 → 触发meta_recursion"""
    try:
        from persistent_engine import get_engine, save_state
        engine = get_engine()
        m0 = engine.p513.p513["meta_recursion_count"]
        for depth in range(1, 4):
            try:
                engine.meta_recursion(depth=depth)
            except Exception:
                pass
        m1 = engine.p513.p513["meta_recursion_count"]
        save_state({"meta_recursions": m1})
        return True, f"meta_rec +{m1 - m0}"
    except Exception as e:
        return False, f"元递归失败: {str(e)[:80]}"

# 修复分派表
FIXERS = {
    "daemon": fix_daemon_gap,
    "evolution_engine": fix_evolution_stuck,
    "evolution": fix_recursion_stuck,
}

def main():
    log("═══ auto_close_loop 开始 ═══")
    gaps = load_gaps()
    log(f"发现 {len(gaps)} 个未解决缺口")

    fixed = 0
    skipped = 0
    failed = 0

    for gap_id, gap in gaps.items():
        module = gap.get("module", "unknown")
        fixer = FIXERS.get(module)
        if fixer is None:
            skipped += 1
            continue

        success, msg = fixer(gap)
        if success:
            log(f"  ✅ {gap_id}: {msg}")
            fixed += 1
        else:
            log(f"  ❌ {gap_id}: {msg}")
            failed += 1

    log(f"═══ 完成: 修复 {fixed}, 跳过 {skipped}, 失败 {failed} ═══")
    return fixed

if __name__ == "__main__":
    main()
