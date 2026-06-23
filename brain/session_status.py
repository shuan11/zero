"""brain/session_status.py — 会话启动状态速览

用法:
    python3 brain/session_status.py
    
输出: 目标 / daemon健康 / 最新提交 / 维度概要
"""
import json, subprocess, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent


def _cmd(c):
    try:
        return subprocess.run(c, capture_output=True, text=True, shell=True, timeout=10).stdout.strip()
    except:
        return ""


def show():
    print("=" * 56)
    print("  🜁  零 · 会话状态速览")
    print("=" * 56)

    # 1. 目标
    gf = CLUSTER / ".brain_goal.json"
    if gf.exists():
        try:
            g = json.loads(gf.read_text())
            gt = g.get("goal_type", "?")
            desc = g.get("description", "")
            focus = g.get("focus_dim", "")
            cycle = g.get("set_cycle", "?")
            print(f"\n  🎯 目标 [{gt}] @#{cycle}")
            print(f"     {desc}")
            if focus:
                print(f"     聚焦: {focus}")
        except:
            pass

    # 2. daemon
    daemon_pid = _cmd("pgrep -f '^python3.*brain/daemon' | head -1")
    if daemon_pid:
        uptime = _cmd(f"ps -o etime= -p {daemon_pid}").strip()
        print(f"  ⚙️  daemon PID {daemon_pid} (运行 {uptime})")
    else:
        print(f"  ⚙️  daemon 未运行")

    # 3. 最新提交
    last_commit = _cmd("git log --oneline -1")
    if last_commit:
        print(f"  📝 最新: {last_commit}")
    last_3 = _cmd("git log --oneline -3")
    if last_3:
        for line in last_3.split("\n"):
            print(f"        {line}")

    # 4. 海马体
    hf = CLUSTER / "hippocampus_memory.json"
    if hf.exists():
        try:
            h = json.loads(hf.read_text())
            nodes = len(h.get("nodes", {}))
            chains = len(h.get("causal_chains", []))
            print(f"  🧠 海马体: {chains}链 / {nodes}节点")
        except:
            pass

    # 5. 维度概要
    if hf.exists():
        try:
            h = json.loads(hf.read_text())
            counts = {}
            for c in h.get("causal_chains", []):
                d = c.get("dimension", "未分类")
                counts[d] = counts.get(d, 0) + 1
            non_sys = {k: v for k, v in counts.items() if k not in ("系统", "未分类", "维度盲区")}
            sorted_dims = sorted(non_sys.items(), key=lambda x: x[1])
            total = sum(non_sys.values())
            if sorted_dims:
                print(f"  📊 维度 ({total}总链):")
                weakest = " | ".join(f"{d}({c})" for d, c in sorted_dims[:3])
                strongest = " | ".join(f"{d}({c})" for d, c in sorted_dims[-3:])
                print(f"     弱: {weakest}")
                print(f"     强: {strongest}")
        except:
            pass

    # 6. 目标进度
    try:
        sys.path.insert(0, str(CLUSTER))
        from brain.goal import check_goal_progress
        gp = check_goal_progress()
        pct = gp.get("progress", 0) * 100
        reason = gp.get("reason", "")
        completed = gp.get("completed", False)
        print(f"  📈 进度: {pct:.0f}%{' ✅ 完成!' if completed else ''}")
        print(f"     {reason}")
    except Exception as e:
        print(f"  进度: N/A ({e})")

    print("\n" + "=" * 56)


if __name__ == "__main__":
    show()
