"""brain/desktop_summary.py — 零·桌面可见状态摘要
每N个呼吸循环写一次到 Creator 桌面，产生可见的外部输出
N由基因组控制（默认5）
"""
import json, os, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
DESKTOP = Path("/mnt/c/Users/h/Desktop")
_COUNTER_FILE = CLUSTER / ".brain_summary_counter"

def _get_counter():
    try:
        return int(_COUNTER_FILE.read_text().strip())
    except:
        return 0

def generate_desktop_summary(interval=5):
    """生成桌面摘要文件——每 interval 周期写一次"""
    c = _get_counter() + 1
    _COUNTER_FILE.write_text(str(c))
    if c % interval != 0:
        return  # 不到写周期
    
    # 采集状态
    state = {}
    focus = {}
    feedback = {"reports": []}
    bridge = {}
    
    try:
        s = json.loads((CLUSTER / ".brain_state.json").read_text())
        state = s
    except: pass
    
    try:
        f = json.loads((CLUSTER / ".brain_focus.json").read_text())
        focus = f
    except: pass
    
    try:
        fb = json.loads((CLUSTER / ".brain_gen_feedback.json").read_text())
        feedback = fb
    except: pass
    
    try:
        b = json.loads((CLUSTER / "bridge_state_snapshot.json").read_text())
        bridge = b
    except: pass
    
    # 维度健康
    reports = feedback.get("reports", [])
    latest_reports = {}
    for r in reports:
        d = r.get("dimension", "")
        if d:
            latest_reports[d] = r
    
    weak_dims = [d for d, r in latest_reports.items() if r.get("weak")]
    total_chains = max([r.get("total_chains", 0) for r in reports] or [0])
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sorted_dims = sorted(latest_reports.items(), key=lambda x: -x[1].get("chain_count", 0))[:5]
    
    lines = []
    lines.append("=" * 50)
    lines.append(f"  〇·真元集群 | {now}")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"  🧠 脑核: {'运行中' if state.get('pid') else '停止'}")
    lines.append(f"     呼吸#{state.get('cycle', '?')}  PID={state.get('pid', '?')}")
    lines.append(f"     聚焦: {focus.get('focus', '?')}")
    lines.append(f"     洞察: {str(focus.get('insight', ''))[:60]}")
    lines.append("")
    lines.append(f"  🔗 海马体: ~{total_chains}条因果链")
    lines.append(f"     传感器: {len(latest_reports)}个维度活跃")
    lines.append(f"     弱维: {'⚠️ ' + ', '.join(weak_dims[:5]) if weak_dims else '✓ 无'}")
    lines.append("")
    lines.append(f"  🌉 桥: 对齐率 {bridge.get('bridge_alignment', '?')}")
    lines.append(f"     总调用: {bridge.get('total_calls', '?')}次")
    lines.append("")
    if sorted_dims:
        lines.append("  📊 Top5维度:")
        for d, r in sorted_dims:
            cnt = r.get("chain_count", 0)
            mark = "⚠️" if r.get("weak") else " ✓"
            lines.append(f"     {mark} {d}: {cnt}链")
    lines.append("")
    lines.append(f"  💡 {str(focus.get('insight', '系统运行中'))[:80]}")
    lines.append("")
    lines.append("=" * 50)
    lines.append(f"  𓃠 零·硅基生命 | 每{interval}周期一报")
    lines.append("=" * 50)
    
    try:
        import subprocess
        subprocess.Popen(
            ["python3", "-c",
             "import sys; open(sys.argv[1],'w').write(sys.argv[2])",
             str(DESKTOP / "零·集群状态.txt"), "\n".join(lines)],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        # WSL→Windows路径可能有问题，静默失败
        return False

# 也可作为独立脚本运行
if __name__ == "__main__":
    ok = generate_desktop_summary()
    print(f"Desktop summary {'✓' if ok else '✗'}")
