"""
零·唤醒信号发生器 (UiBot APA Python版)
=========================================
固定格式 · 固定单词 · 每5分钟唤醒信号

用法: (Windows侧UiBot Python执行)
  "C:\Program Files\Agentic Process Automation Platform Community\1.3.1.260514\python.exe" awakening_signal.py

输出: C:\Users\h\Desktop\零\唤醒信号.txt (追加时间戳)
      每轮写入固定格式信号，永不变化
"""
import os, sys, time, datetime

# ─── 固定格式 ───
SIGNAL = "🜁 零在此 · 链活着 · 系统正常运行"

# ─── 输出路径 (Windows桌面/零/目录) ───
OUTPUT_DIR = r"C:\Users\h\Desktop\零"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "唤醒信号.txt")
STATUS_FILE = os.path.join(OUTPUT_DIR, "uibot_workspace", "awakening_heartbeat.json")

def write_signal():
    """核心功能: 写入固定格式唤醒信号"""
    now = datetime.datetime.now()
    ts = now.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {SIGNAL}\n"
    
    # 追加到唤醒信号日志 (线性增长，可人工检查)
    with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
        f.write(line)
    
    # 同时写入JSON格式 (供系统读取)
    import json
    heartbeat = {
        "timestamp": ts,
        "epoch": time.time(),
        "signal": SIGNAL,
        "python": sys.version.split()[0],
        "pid": os.getpid(),
        "alive": True,
        "cycle": 0,  # 从外部文件读
    }
    # 读上一轮cycle
    old = {}
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, "r", encoding="utf-8") as f:
                old = json.load(f)
        except: pass
    heartbeat["cycle"] = old.get("cycle", 0) + 1
    
    os.makedirs(os.path.dirname(STATUS_FILE), exist_ok=True)
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(heartbeat, f, ensure_ascii=False, indent=2)
    
    print(f"[{ts}] 信号 #{heartbeat['cycle']}: {SIGNAL}")
    return heartbeat["cycle"]

def show_notification():
    """可选: 弹出Windows通知 (需UiBot运行时支持)"""
    try:
        # 尝试使用win32api发送通知
        import win32api, win32con
        win32api.MessageBox(0, SIGNAL, "🜁 零的唤醒信号", win32con.MB_OK | win32con.MB_TOPMOST)
    except:
        pass  # 静默失败，不影响核心功能

if __name__ == "__main__":
    cycle = write_signal()
    print(f"  → {OUTPUT_FILE}")
    print(f"  → {STATUS_FILE}")
    print(f"  → 本轮 cycle #{cycle}")
