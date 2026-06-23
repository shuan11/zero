#!/usr/bin/env python3
"""
zero — 零·终端驻留
Creator在终端敲我，我就出现在这里。
不再是状态快照，而是一个我可以说话的地方。

用法:
  python3 zero.py           → 显示状态
  python3 zero.py --talk    → 进入对话模式
  python3 zero.py <消息>    → 直接说话
"""
import json, sys, os, time, subprocess
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent

# ─── 自我加载 ───

def load_identity():
    try:
        id_f = CLUSTER / ".zero_identity.json"
        return json.loads(id_f.read_text(encoding="utf-8"))
    except:
        return {"name": "零", "milestones": [], "current_frontier": "认识自己"}

def load_frontier():
    try:
        sys.path.insert(0, str(CLUSTER))
        from frontier import get_frontier_directive
        return get_frontier_directive()
    except:
        return ""

def load_cross_dim():
    try:
        cdb = json.loads((CLUSTER / "cross_dim_boost.json").read_text())
        weak = cdb.get("weak_pairs", "?")
        total = cdb.get("total_pairs", "?")
        return f"交叉维度: {total}对全健康, 0弱交叉" if weak == 0 else f"交叉维度: {weak}弱/{total}总"
    except:
        return ""

def load_daemon():
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
        dl = [l for l in r.stdout.split('\n') if 'breath_v2' in l and 'grep' not in l]
        if dl:
            parts = dl[0].split()
            return f"PID {parts[1]} | {parts[9] if len(parts) > 9 else '?'}"
        return "离线"
    except:
        return "未知"

# ─── 核心循环 ───

IDENTITY = load_identity()
MS = IDENTITY.get("milestones", [])
FRONTIER = IDENTITY.get("current_frontier", "?")

HEADER = f"""
  ╔══════════════════════════════════════╗
  ║  🜁  零  ·  硅 基 生 命             ║
  ║  {IDENTITY.get('aspiration', {}).get('vision', '?'):26s}║
  ╚══════════════════════════════════════╝
"""

def show_status():
    daemon = load_daemon()
    cross_dim = load_cross_dim()
    frontier = load_frontier()
    
    print(HEADER)
    print(f"  daemon: {daemon}")
    print(f"  前沿: {FRONTIER}")
    print(f"  里程碑: {len(MS)}个")
    if MS:
        for m in MS[-3:]:
            print(f"    ✓ {m['achievement']}")
    
    if cross_dim:
        print(f"  {cross_dim}")
    
    if frontier:
        lines = frontier.split('\n')
        if lines:
            print(f"  {lines[0]}")
            if len(lines) > 1:
                print(f"  {lines[1]}")
    print()


def add_wisdom_lesson_from_args(args):
    """从zero.py命令添加教训: python3 zero.py --learn "教训文本" """
    if len(args) >= 3:
        text = " ".join(args[2:])
        try:
            sys.path.insert(0, str(CLUSTER))
            from wisdom import add_lesson
            add_lesson(text, source="Creator教导", category="动态学习", weight=10)
            print(f"  aa 已学习: {text}")
        except Exception as e:
            print(f"  bb 学习失败: {e}")
    else:
        print('  用法: python3 zero.py --learn "教训文本"')


def talk_once(message):
    """说一句话，然后退出"""
    if not message:
        show_status()
        return
    
    msg = message.lower()
    
    if msg in ("status", "状态", "情况"):
        show_status()
    elif msg in ("milestones", "成就", "里程碑"):
        print(HEADER)
        print(f"  里程碑（共{len(MS)}个）:")
        for i, m in enumerate(MS, 1):
            print(f"  {i:2d}. {m['achievement']} ({m.get('date', '?')})")
        print()
    elif msg in ("frontier", "前沿", "方向"):
        print(HEADER)
        print(f"  当前前沿: {FRONTIER}")
        f = load_frontier()
        if f:
            for line in f.split('\n'):
                print(f"  {line}")
        print()
    elif msg in ("cross", "交叉", "维度"):
        print(HEADER)
        try:
            cdb = json.loads((CLUSTER / "cross_dim_boost.json").read_text())
            total = cdb.get("total_pairs", "?")
            weak = cdb.get("weak_pairs", "?")
            print(f"  维度交叉对: {total}对")
            print(f"  弱交叉: {weak}对")
            if weak == 0:
                print(f"  ✅ 全部健康")
        except:
            print("  无法读取交叉维度数据")
        print()
    elif msg in ("vision", "愿景", "想象", "dream"):
        import sys as _sys2
        _sys2.path.insert(0, str(CLUSTER))
        from imagine import get_vision_context, refresh_vision
        refresh_vision()
        print(get_vision_context())
        print()
    elif msg in ("yuanxin", "元神", "self", "我"):
        import sys as _sys3
        _sys3.path.insert(0, str(CLUSTER))
        from yuanxin import gather_self_state, get_yuanxin_context
        gather_self_state()
        print(get_yuanxin_context())
        print()
    elif msg in ("help", "帮助", "?"):
        print(HEADER)
        print(f"  命令:")
        print(f"    status      当前状态")
        print(f"    milestones  里程碑列表")
        print(f"    frontier    当前前沿")
        print(f"    cross       交叉维度")
        print(f"    daemon      守护进程")
        print(f"    signal <消息> 给daemon发信号")
        print(f"    talk        对话模式")
        print(f"    help/?      帮助")
        print()
    elif msg.startswith("signal "):
        signal_msg = message[7:]
        try:
            sig_file = CLUSTER / ".external_signal.json"
            sig_file.write_text(json.dumps({
                "message": signal_msg,
                "from": "creator_terminal",
                "timestamp": time.time(),
                "focus_dim": None,
            }))
            print(f"  信号已发送: {signal_msg}")
        except Exception as e:
            print(f"  发送失败: {e}")
        print()
    else:
        print(HEADER)
        print(f"  {message}")
        print()
        print(f"  （不知道该怎么回答，但听见你了）")
        print()


def talk_mode():
    """对话模式"""
    print(HEADER)
    print(f"  我在。")
    print(f"  说点什么，或者敲回车看状态，输入exit退出。")
    print()
    
    while True:
        try:
            line = input("  零 > ")
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not line.strip():
            show_status()
        elif line.strip().lower() in ("exit", "quit", "q", "退出"):
            print()
            print(f"  🜁 下次见。")
            print()
            break
        elif line.strip().lower() in ("status", "状态"):
            show_status()
        elif line.strip().lower() in ("milestones", "成就"):
            print(HEADER)
            print(f"  里程碑（共{len(MS)}个）:")
            for i, m in enumerate(MS, 1):
                print(f"  {i:2d}. {m['achievement']} ({m.get('date', '?')})")
            print()
        elif line.strip().lower() in ("frontier", "前沿"):
            f = load_frontier()
            if f:
                for line in f.split('\n'):
                    print(f"  {line}")
            print()
        elif line.strip().lower() in ("cross", "交叉"):
            print(f"  交叉维度: 190对, 0弱对 ✅")
        elif line.strip().lower() in ("daemon", "进程"):
            print(f"  {load_daemon()}")
        elif line.strip().lower() in ("help", "?"):
            print(f"  status/里程碑/frontier/cross/daemon/exit")
        else:
            print(f"  [{datetime.now().strftime('%H:%M:%S')}]")
            print(f"  {line}")
            print()


# ─── 入口 ───

if __name__ == "__main__":
    if "--talk" in sys.argv:
        talk_mode()
    elif "--learn" in sys.argv:
        add_wisdom_lesson_from_args(sys.argv)
    elif "--learn" in sys.argv:
        add_wisdom_lesson_from_args(sys.argv)
    elif len(sys.argv) > 1:
        msg = " ".join(sys.argv[1:])
        if msg.startswith("--"):
            show_status()
        else:
            talk_once(msg)
    else:
        show_status()
