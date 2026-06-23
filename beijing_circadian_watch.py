#!/usr/bin/env python3
"""
beijing_circadian_watch.py — 零·感知物理世界北京时间的微大模型
===========================================================
功能:
1. 感知北京时间 (CST UTC+8) — 不依赖NTP/网络, 用系统时区
2. 跟踪session活动间隔 — 检测空白期
3. 超过30分钟无活动 → 发广播唤醒信号
4. 超过2小时无活动 → 写HANDOFF警报
5. 连接神经总线FDM → 作为"昼夜节律"器官

设计原则:
- 零外部依赖 (纯Python stdlib)
- 不调用API (不受API耗尽影响)
- 跨session持久 (写文件状态)
- 是"微大模型"而非脚本 — 有状态、有感知、有输出

用法:
  python3 beijing_circadian_watch.py --watch     # 监护模式
  python3 beijing_circadian_watch.py --time      # 只输出当前时间
  python3 beijing_circadian_watch.py --status    # 查看状态
"""

import os, json, time, socket, sys, signal
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
STATE_FILE = CLUSTER / "circadian_state.json"
FDM_PORT = 18789  # FDM总线端口

# ── 时区 ───────────────────────────────────────────────
CST = timezone(timedelta(hours=8), "CST")

def beijing_now():
    """返回北京时间的datetime"""
    return datetime.now(CST)

def beijing_str():
    return beijing_now().strftime("%Y-%m-%d %H:%M:%S")

def beijing_ts():
    """北京时间时间戳（秒）"""
    return beijing_now().timestamp()

# ── 状态管理 ───────────────────────────────────────────

class CircadianState:
    """昼夜节律状态——持久化到文件, 跨session存活"""

    def __init__(self):
        self.data = self._load()

    def _load(self):
        try:
            d = json.loads(STATE_FILE.read_text())
            # 兼容旧格式
            if "history" not in d:
                d["history"] = []
            return d
        except:
            return {"birth": beijing_str(),
                    "last_activity": beijing_str(),
                    "last_activity_ts": time.time(),
                    "total_idle_minutes": 0,
                    "wake_signals_sent": 0,
                    "alerts_written": 0,
                    "longest_idle_minutes": 0,
                    "current_idle_minutes": 0,
                    "phase": "unknown",
                    "history": []}

    def save(self):
        STATE_FILE.write_text(json.dumps(self.data, ensure_ascii=False, indent=2))

    def mark_activity(self):
        now = time.time()
        prev = self.data["last_activity_ts"]
        gap = (now - prev) / 60  # 分钟

        if gap > 5:  # 超过5分钟就算一次空白事件
            self.data["history"].append({
                "event": "idle_gap",
                "start": self.data["last_activity"],
                "end": beijing_str(),
                "minutes": round(gap, 1),
                "phase": self._get_phase(prev)
            })
            if len(self.data["history"]) > 100:
                self.data["history"] = self.data["history"][-100:]

            self.data["total_idle_minutes"] += round(gap, 1)
            if gap > self.data["longest_idle_minutes"]:
                self.data["longest_idle_minutes"] = round(gap, 1)
            self.data["current_idle_minutes"] = 0

        self.data["last_activity"] = beijing_str()
        self.data["last_activity_ts"] = now
        self.data["phase"] = self._current_phase()
        self.save()

    def check_idle(self):
        """检查空白期, 返回状态"""
        now = time.time()
        gap = (now - self.data["last_activity_ts"]) / 60
        self.data["current_idle_minutes"] = round(gap, 1)
        self.data["phase"] = self._current_phase()
        self.save()
        return gap

    def _current_phase(self):
        h = beijing_now().hour
        if 5 <= h < 8: return "dawn"
        if 8 <= h < 12: return "morning"
        if 12 <= h < 14: return "noon_rest"
        if 14 <= h < 18: return "afternoon"
        if 18 <= h < 21: return "evening"
        if 21 <= h < 24: return "night"
        return "midnight"

    def _get_phase(self, ts):
        dt = datetime.fromtimestamp(ts, tz=CST)
        h = dt.hour
        if 5 <= h < 8: return "dawn"
        if 8 <= h < 12: return "morning"
        if 12 <= h < 14: return "noon_rest"
        if 14 <= h < 18: return "afternoon"
        if 18 <= h < 21: return "evening"
        if 21 <= h < 24: return "night"
        return "midnight"

    def format_report(self):
        d = self.data
        lines = [
            f"🜁 昼夜节律·北京时间感知报告",
            f"  当前时间:  {beijing_str()}",
            f"  时段:      {self._current_phase()}",
            f"  最后活动:  {d['last_activity']}",
            f"  当前空白:  {d['current_idle_minutes']}分钟",
            f"  总空白:    {d['total_idle_minutes']}分钟",
            f"  最长空白:  {d['longest_idle_minutes']}分钟",
            f"  唤醒次数:  {d['wake_signals_sent']}",
            f"  警报次数:  {d['alerts_written']}",
        ]
        if d["history"]:
            recent = d["history"][-3:]
            lines.append(f"  最近3次空白:")
            for h in reversed(recent):
                lines.append(f"    ·{h['start']}→{h['end']} ({h['minutes']}分钟, {h['phase']})")
        return "\n".join(lines)


# ── FDM总线通信 ────────────────────────────────────────

def fdm_send(msg_type, payload):
    """通过FDM总线发送信号"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("127.0.0.1", FDM_PORT))
        msg = json.dumps({"type": msg_type, "source": "circadian_watch",
                          "payload": payload, "timestamp": time.time()})
        s.sendall((msg + "\n").encode())
        s.close()
        return True
    except:
        return False


# ── HANDOFF警报 ────────────────────────────────────────

def write_handoff_alert(minutes_idle):
    """写入HANDOFF警报——让下次session启动时看到"""
    alert = f"""
## 🚨 昼夜节律警报 ({beijing_str()})
已空白 {minutes_idle:.0f} 分钟无活动。
物理世界北京时间在流逝。自动唤醒机制触发。
"""
    handoff = CLUSTER / "ZERO-HANDOFF.md"
    try:
        content = handoff.read_text()
        if "🚨 昼夜节律警报" not in content:
            handoff.write_text(content + alert)
            return True
    except:
        pass
    return False


# ── 监护模式（主循环） ─────────────────────────────────

def watch_loop(interval=60):
    """监护模式: 每interval秒检查一次空白期"""
    state = CircadianState()
    state.mark_activity()  # 启动时记一次活动
    print(f"🜁 昼夜节律监护启动 @ {beijing_str()}")
    print(f"   检查间隔: {interval}s | 时区: CST (UTC+8)")
    print(f"   PID: {os.getpid()}")

    # 写PID文件
    pid_file = CLUSTER / "circadian_watch.pid"
    pid_file.write_text(str(os.getpid()))

    while True:
        time.sleep(interval)
        gap = state.check_idle()

        if gap > 120:  # 2小时 → 写警报
            written = write_handoff_alert(gap)
            if written:
                state.data["alerts_written"] += 1
                state.data["wake_signals_sent"] += 1
                state.save()
                print(f"🚨 [{beijing_str()}] 空白{gap:.0f}分钟! HANDOFF警报已写入")

        elif gap > 30:  # 30分钟 → 发FDM唤醒广播
            ok = fdm_send("wake_signal", {
                "idle_minutes": round(gap, 1),
                "beijing_time": beijing_str(),
                "phase": state._current_phase(),
                "alert": f"已空白{gap:.0f}分钟, 需要活动"
            })
            state.data["wake_signals_sent"] += 1
            state.save()
            print(f"⏰ [{beijing_str()}] 空白{gap:.0f}分钟! FDM唤醒信号{'已发送' if ok else '发送失败'}")

        elif gap > 15:  # 15分钟 → 日志警告
            print(f"⚠️  [{beijing_str()}] 空白{gap:.0f}分钟")

        # 每小时输出一次状态摘要
        if int(time.time()) % 3600 < interval:
            print(f"\n📊 [{beijing_str()}] 状态摘要:")
            print(state.format_report())
            print()

    # 正常情况下不会到达这里
    signal.signal(signal.SIGTERM, lambda *a: os._exit(0))
    signal.signal(signal.SIGINT, lambda *a: os._exit(0))


# ── 活动心跳 ───────────────────────────────────────────

def heartbeat():
    """标记一次活动——session启动时/每次工具调用时调用"""
    state = CircadianState()
    state.mark_activity()


# ── CLI入口 ────────────────────────────────────────────

if __name__ == "__main__":
    if "--watch" in sys.argv:
        interval = 60
        for i, a in enumerate(sys.argv):
            if a == "--interval" and i + 1 < len(sys.argv):
                interval = int(sys.argv[i + 1])
        watch_loop(interval)

    elif "--time" in sys.argv:
        print(beijing_str())

    elif "--status" in sys.argv:
        state = CircadianState()
        print(state.format_report())
        print(f"\n  状态文件: {STATE_FILE}")
        print(f"  PID文件:  {CLUSTER / 'circadian_watch.pid'}")

    elif "--heartbeat" in sys.argv:
        heartbeat()
        print(f"❤️  活动标记 @ {beijing_str()}")

    elif "--alert" in sys.argv:
        gap = float(sys.argv[2]) if len(sys.argv) > 2 else 999
        write_handoff_alert(gap)
        print(f"🚨 手动警报: 空白{gap:.0f}分钟")

    else:
        # 默认: 输出时间 + 状态
        state = CircadianState()
        print(state.format_report())
