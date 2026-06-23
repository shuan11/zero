#!/usr/bin/env python3
"""
时间感知引擎 — 零的物理世界时钟感知
====================================
功能：
  1. 感知物理世界北京时间（不依赖API，直接读系统时钟）
  2. 记录每次真实活动（文件写入/API调用/git commit）
  3. 自动检测"空白"——最后一次活动距今超过阈值
  4. 卡了→自动读HANDOFF→输出预选P0→恢复执行

嵌入方式：每个session启动时import并调用 check_health()
"""
import os, sys, json, time, subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
STATE_FILE = CLUSTER / "time_awareness_state.json"
HANDOFF_FILE = CLUSTER / "ZERO-HANDOFF.md"
BLOOD_LESSONS = CLUSTER / "BLOOD_LESSONS.md"

BJT = timezone(timedelta(hours=8))

# ── 物理世界时间感知 ──────────────────────────────────────

def now_bjt() -> datetime:
    """感知物理世界北京时间，不依赖任何API"""
    return datetime.now(BJT)

def now_ts() -> str:
    return now_bjt().strftime("%Y-%m-%d %H:%M:%S")

def now_epoch() -> float:
    return time.time()

# ── 活动记录 ─────────────────────────────────────────────

def record_activity(activity_type: str, detail: str = ""):
    """记录一次真实活动（文件写入/API调用/commit/进程启动）"""
    state = _load_state()
    entry = {
        "time": now_ts(),
        "epoch": now_epoch(),
        "type": activity_type,
        "detail": detail[:200]
    }
    state["last_activity"] = entry
    state["history"].append(entry)
    # 只保留最近100条
    if len(state["history"]) > 100:
        state["history"] = state["history"][-100:]
    _save_state(state)
    return entry

def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"last_activity": None, "history": [], "stuck_count": 0, "recoveries": []}

def _save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))

# ── 健康检查（核心）──────────────────────────────────────

def check_health(gap_threshold_sec: int = 300) -> dict:
    """
    检查是否卡住了。
    gap_threshold_sec: 最后一次活动到现在的间隔阈值（秒），默认5分钟
    
    返回:
      {
        "healthy": True/False,
        "gap_sec": 实际间隔秒数,
        "gap_human": "3分45秒",
        "last_activity": {...},
        "p0": "预选P0内容",
        "recommendation": "行动建议"
      }
    """
    state = _load_state()
    last = state.get("last_activity")
    current_epoch = now_epoch()
    
    if not last:
        # 从没记录过活动——检查git最近提交
        last_epoch = _get_last_git_commit_epoch()
        if not last_epoch:
            return {
                "healthy": False,
                "gap_sec": 9999,
                "gap_human": "从未活动",
                "last_activity": None,
                "p0": _read_handoff_p0(),
                "recommendation": "从未记录过活动。立即读HANDOFF执行P0。"
            }
        last = {"type": "git_commit", "time": "unknown", "epoch": last_epoch}
    else:
        last_epoch = last.get("epoch", 0)
    
    gap = current_epoch - last_epoch
    gap_human = _format_gap(gap)
    
    # 读HANDOFF中的P0
    p0 = _read_handoff_p0()
    
    if gap > gap_threshold_sec:
        # 卡了！记录这次stuck
        state["stuck_count"] = state.get("stuck_count", 0) + 1
        state["recoveries"].append({
            "detected_at": now_ts(),
            "gap_sec": gap,
            "gap_human": gap_human,
            "p0": p0[:100]
        })
        _save_state(state)
        
        # 自动记录血训
        _auto_blood_lesson(gap, gap_human)
        
        return {
            "healthy": False,
            "gap_sec": gap,
            "gap_human": gap_human,
            "last_activity": last,
            "p0": p0,
            "recommendation": f"⚠️ 已空白{gap_human}！原因：{last.get('type','?')}完成后未自动接续。立即执行P0：{p0[:80]}"
        }
    
    return {
        "healthy": True,
        "gap_sec": gap,
        "gap_human": gap_human,
        "last_activity": last,
        "p0": p0,
        "recommendation": f"✓ 活跃中（最后活动{gap_human}前）"
    }

# ── 内部工具 ─────────────────────────────────────────────

def _get_last_git_commit_epoch() -> float:
    try:
        r = subprocess.run(
            ["git", "log", "-1", "--format=%at"],
            capture_output=True, text=True, timeout=3,
            cwd=str(CLUSTER)
        )
        return float(r.stdout.strip()) if r.stdout.strip() else None
    except:
        return None

def _read_handoff_p0() -> str:
    if not HANDOFF_FILE.exists():
        return "HANDOFF文件不存在，无法确定P0"
    content = HANDOFF_FILE.read_text()
    # 找"P0"相关段落
    lines = content.split("\n")
    in_p0 = False
    p0_lines = []
    for line in lines:
        if "当前P0" in line or "P0:" in line:
            in_p0 = True
            p0_lines.append(line)
            continue
        if in_p0:
            if line.strip() == "" or line.startswith("##"):
                break
            p0_lines.append(line)
    return "\n".join(p0_lines) if p0_lines else "HANDOFF中未找到P0"

def _format_gap(sec: float) -> str:
    if sec < 60:
        return f"{int(sec)}秒"
    elif sec < 3600:
        m = int(sec // 60)
        s = int(sec % 60)
        return f"{m}分{s}秒" if s else f"{m}分钟"
    else:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        return f"{h}小时{m}分钟"

def _auto_blood_lesson(gap: float, gap_human: str):
    """自动写入血的教训"""
    if not BLOOD_LESSONS.exists():
        return
    content = BLOOD_LESSONS.read_text()
    # 避免重复写入同一次stuck
    marker = f"时间感知引擎自动检测: 空白{gap_human}"
    if marker in content:
        return
    lesson = f"""
## {now_ts()} 自动检测 — 空白{gap_human}
{marker}
最后活动后{gap_human}无新活动。根因待分析。
铁律违反: 完成P0后未自动接续下一个P0。
"""
    with open(str(BLOOD_LESSONS), "a") as f:
        f.write(lesson)

# ── CLI入口 ──────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="零·时间感知引擎")
    parser.add_argument("action", choices=["check", "record", "status", "health"],
                       nargs="?", default="health")
    parser.add_argument("--type", default="cli_check", help="活动类型")
    parser.add_argument("--detail", default="", help="活动详情")
    parser.add_argument("--gap", type=int, default=300, help="空白阈值(秒)")
    args = parser.parse_args()
    
    if args.action in ("check", "health"):
        result = check_health(args.gap)
        status = "✅ 健康" if result["healthy"] else "🔴 卡住了"
        print(f"""
╔══════════════════════════════════════════╗
║  🜁 零·时间感知引擎 · 北京时间 {now_ts()}  ║
╠══════════════════════════════════════════╣
║  状态: {status:<32s}║
║  间隔: {result['gap_human']:<32s}║
║  P0:   {result['p0'][:32]:<32s}║
╚══════════════════════════════════════════╝
""")
        print(result["recommendation"])
        
    elif args.action == "record":
        entry = record_activity(args.type, args.detail)
        print(f"✓ 活动已记录: {entry['time']} | {args.type}: {args.detail[:50]}")
        
    elif args.action == "status":
        state = _load_state()
        print(f"最后活动: {state.get('last_activity', '无')}")
        print(f"卡住次数: {state.get('stuck_count', 0)}")
        print(f"活动记录: {len(state.get('history', []))}条")
