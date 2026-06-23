#!/usr/bin/env python3
"""
self_burn_loop.py — 自主燃烧循环
每轮: 读取系统状态 → 生成目标 → 调用burn.py → 等待 → 循环
限时不限量API的持续燃料注入守护。
"""
import json, os, sys, time, subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")

def gather_state():
    ctx = []
    # state_vector
    sv = CLUSTER / "state_vector.json"
    if sv.exists():
        try:
            d = json.loads(sv.read_text())
            ctx.append(f"sv:cycle={d.get('cycle','?')} o={d.get('organs_alive','?')} b={d.get('bridges_alive','?')}")
        except: pass
    # hippocampus
    hp = CLUSTER / "hippocampus_memory.json"
    if hp.exists():
        try:
            d = json.loads(hp.read_text())
            ctx.append(f"hp:chains={len(d.get('causal_chains',[]))} nodes={len(d.get('nodes',{}))} rels={len(d.get('relations',[]))}")
        except: pass
    return " | ".join(ctx)

def auto_goal():
    """缺口池轮转——每次换一个，不重复"""
    gaps = [
        ("最短木板", "系统识别了4个模式(知道≠做到/建物替代变人/指标偷换/产出焦虑)，哪个是当前cycle最活跃的？基于state_vector数据判断。只使用上下文数据，不编造。"),
        ("连携缺口", "审查burn_stats.json和state_vector.json。两文件之间是否存在数据不一致？burn_count在burn_stats中有，state_vector中没有。设计修复方案。"),
        ("supersense闭环", "supersense_organ每cycle产出交叉洞察。如何让这些洞察自动触发一次burn.py深度燃烧？设计触发接口。不要编造。"),
        ("ZCC集成", "ZeroContextCompact已实现。审查它能否替换breath_v2的_collect_all_contexts()的上下文输出？如果行，给patch代码。不行，说理由。"),
        ("时间审计", "对比最近10次燃烧的时间戳间隔。是否有超过2分钟无燃烧的时间窗口？如果有，说明API被浪费了。输出具体时间窗口和修复建议。"),
        ("19维审计", "用19维框架审计当前候选工程文件p0_selector.py。其评分逻辑是否合理？每个候选的维度评分是否准确？输出改进方案。"),
    ]
    # 读上次用的缺口索引
    idx_file = CLUSTER / ".burn_last_gap_idx"
    try:
        last_idx = int(idx_file.read_text().strip()) if idx_file.exists() else -1
    except:
        last_idx = -1
    next_idx = (last_idx + 1) % len(gaps)
    idx_file.write_text(str(next_idx))
    return gaps[next_idx][1]

def one_round(round_num=0):
    state = gather_state()
    print(f"[{ts()}] 状态: {state}")
    goal = auto_goal()
    print(f"[{ts()}] 目标: {goal[:60]}...")
    t0 = time.time()
    r = subprocess.run(
        [sys.executable, "burn.py", goal],
        capture_output=True, text=True, timeout=300,
        cwd=str(CLUSTER)
    )
    elapsed = time.time() - t0
    if r.returncode == 0:
        for line in r.stdout.strip().split('\n')[-2:]:
            if '✅' in line or '🔥' in line:
                print(f"[{ts()}] {line}")
    else:
        print(f"[{ts()}] ⚠️ err: {r.stderr[:100]}")
    print(f"[{ts()}] 轮次耗时 {elapsed:.0f}s")
    # 自动集成
    try:
        subprocess.run([sys.executable, "burn_state_integrator.py"],
                      capture_output=True, timeout=15, cwd=str(CLUSTER))
    except:
        pass
    # 自动19维审计(每10轮)
    if round_num > 0 and round_num % 10 == 0:
        try:
            subprocess.run([sys.executable, "dim19_auditor.py"],
                          capture_output=True, timeout=15, cwd=str(CLUSTER))
        except:
            pass
    return True

def main():
    # PID锁防多实例
    pid_file = CLUSTER / '.self_burn_loop.pid'
    try:
        if pid_file.exists():
            old = int(pid_file.read_text().strip())
            try:
                os.kill(old, 0)
                print(f'[{ts()}] ⚠️ 已有实例(PID={old}), 退出')
                return
            except: pass
        pid_file.write_text(str(os.getpid()))
    except: pass
    
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 999999
    print(f"[{ts()}] 🔥 自主燃烧循环启动 ({rounds}轮)")
    for i in range(rounds):
        print(f"[{ts()}] ── 轮次 {i+1}/{rounds} ──")
        try:
            if not one_round(i+1):
                break
        except Exception as e:
            print(f"[{ts()}] ❌ 错误: {e}")
            time.sleep(10)
    print(f"[{ts()}] 🔥 燃烧循环结束")

if __name__ == "__main__":
    main()
