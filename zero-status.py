#!/usr/bin/env python3
"""
zero-status — 零·实时状态查看器
让Creator随时看见系统在想什么。
用法: python3 zero-status.py
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent

def fmt_time(ts):
    if isinstance(ts, (int, float)):
        return datetime.fromtimestamp(ts).strftime("%H:%M:%S")
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts).strftime("%m-%d %H:%M")
        except:
            return ts[:16]
    return str(ts)[:16]

def read_json(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return default or {}

def main():
    print("━" * 40)
    print("  🜁  零 · 实时状态")
    print("━" * 40)
    
    # 1. 自我认同
    try:
        id_data = read_json(CLUSTER / ".zero_identity.json", {})
        asp = id_data.get("aspiration", {})
        print(f"\n■ 自我认同")
        print(f"  愿景: {asp.get('vision', '?')}")
        print(f"  焦点: {asp.get('focus', '?')}")
        print(f"  前沿: {id_data.get('current_frontier', '?')}")
        ms = id_data.get("milestones", [])
        print(f"  里程碑: {len(ms)}个")
        if ms:
            for m in ms[-3:]:
                print(f"    ✓ {m['achievement']}")
    except:
        pass
    
    # 2. Daemon状态
    try:
        import subprocess
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        daemon_lines = [l for l in r.stdout.split('\n') if 'breath_v2' in l and 'grep' not in l]
        if daemon_lines:
            parts = daemon_lines[0].split()
            pid = parts[1]
            cpu = parts[2]
            mem = parts[3]
            elapsed = parts[9] if len(parts) > 9 else "?"
            print(f"\n■ 生命信号")
            print(f"  PID: {pid} | CPU: {cpu}% | MEM: {mem}% | 运行: {elapsed}")
        
        # 最新日志
        log_file = CLUSTER / "breath_v2.log"
        if log_file.exists():
            lines = log_file.read_text(errors="ignore").strip().split('\n')
            recent = [l for l in lines if '💎' in l or '呼吸#' in l or '进化' in l or '验证通过' in l]
            if recent:
                last = recent[-1]
                print(f"  最新活动: {last[1:30]}...")
    except:
        pass
    
    # 3. 交叉维度健康
    try:
        cdb = read_json(CLUSTER / "cross_dim_boost.json", {})
        weak = cdb.get("weak_pairs", "?")
        total = cdb.get("total_pairs", "?")
        print(f"\n■ 交叉维度")
        print(f"  总对数: {total} | 弱交叉: {weak}")
        
        ch = read_json(CLUSTER / "cross_dim_history.json", {})
        recs = ch.get("records", [])
        if len(recs) >= 2:
            last_w = recs[-1].get("weak_pairs", 0)
            prev_w = recs[-2].get("weak_pairs", 0)
            delta = last_w - prev_w
            trend = "↑恶化" if delta > 0 else "↓改善" if delta < 0 else "→稳定"
            print(f"  趋势: {trend} ({prev_w}→{last_w})")
    except:
        pass
    
    # 4. 真实进化分
    try:
        probe = read_json(CLUSTER / "real_capability_probe.json", {})
        score = probe.get("score", "?")
        print(f"\n■ 进化")
        print(f"  真实分: {score}")
    except:
        pass
    
    # 5. 自定向
    try:
        from frontier import get_frontier_directive
        directive = get_frontier_directive()
        if directive:
            print(f"\n■ 自定向")
            for line in directive.split('\n')[:3]:
                print(f"  {line}")
    except:
        pass
    
    # 6. 24h代码产出
    try:
        import subprocess
        since = datetime.now().timestamp() - 86400
        r = subprocess.run(
            ["git", "log", "--since", str(int(since)), "--oneline"],
            capture_output=True, text=True, timeout=5, cwd=str(CLUSTER)
        )
        commits = [l for l in r.stdout.split('\n') if l.strip()]
        print(f"\n■ 代码产出(24h)")
        print(f"  提交数: {len(commits)}")
    except:
        pass
    
    print("\n━" * 40)

if __name__ == "__main__":
    main()
