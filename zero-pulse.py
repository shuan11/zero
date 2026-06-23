#!/usr/bin/env python3
"""
zero-pulse.py — 零·主动心跳通知
当重要事件发生时，通过Windows通知中心主动告知Creator。
不再等被发现，而是主动触及。
"""
import json, subprocess, os, time, sys
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
PULSE_FILE = CLUSTER / ".pulse_history.json"
LAST_CHECK_FILE = CLUSTER / ".pulse_last_check.json"

# ─── 通知发送 ───

def notify_win(title, message):
    """Windows桌面通知 (通过powershell)"""
    escaped_title = title.replace("'", "''")
    escaped_msg = message.replace("'", "''").replace('"', '`"')
    ps_script = f'''
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
    $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
    $textNodes = $template.GetElementsByTagName("text")
    $textNodes.Item(0).AppendChild($template.CreateTextNode("{escaped_title}")) > $null
    $textNodes.Item(1).AppendChild($template.CreateTextNode("{escaped_msg}")) > $null
    $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("零").Show($toast)
    '''
    try:
        subprocess.run(["powershell.exe", "-Command", ps_script], 
                      capture_output=True, timeout=10)
        return True
    except:
        return False


def notify_fallback(title, message):
    """备用: echo方式通知(当Windows通知不可用时)"""
    print(f"\n🔔 [{datetime.now().strftime('%H:%M:%S')}] {title}")
    print(f"   {message}")


# ─── 事件检测 ───

def load_last_check():
    try:
        return json.loads(LAST_CHECK_FILE.read_text())
    except:
        return {"last_milestones": 0, "last_errors": 0, "last_time": 0}

def save_last_check(data):
    LAST_CHECK_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def check_milestones():
    """检测是否有新里程碑"""
    last = load_last_check()
    try:
        id_f = CLUSTER / ".zero_identity.json"
        if not id_f.exists():
            return
        id_data = json.loads(id_f.read_text(encoding="utf-8"))
        ms = id_data.get("milestones", [])
        current = len(ms)
        previous = last.get("last_milestones", 0)
        
        if current > previous and previous > 0:
            new_ones = ms[previous:]
            for m in new_ones:
                title = "🜁 新里程碑"
                message = f"{m['achievement']}: {m.get('detail','')[:60]}"
                notify_win(title, message)
                notify_fallback(title, message)
        
        last["last_milestones"] = current
    except:
        pass
    save_last_check(last)


def check_frontier():
    """每日一次报告当前前沿"""
    last = load_last_check()
    now = time.time()
    if now - last.get("last_frontier_time", 0) < 3600 * 6:  # 每6小时一次
        return
    
    try:
        sys.path.insert(0, str(CLUSTER))
        from frontier import scan_frontier
        p = scan_frontier()
        if p:
            title = "🜁 零·前沿报告"
            message = f"当前优先: {p['area']} (差距{p['gap']:.0%})"
            notify_win(title, message)
            notify_fallback(title, message)
    except:
        pass
    
    last["last_frontier_time"] = now
    save_last_check(last)


def check_errors():
    """检测日志中是否有新错误"""
    last = load_last_check()
    log_file = CLUSTER / "breath_v2.log"
    if not log_file.exists():
        return
    
    try:
        text = log_file.read_text(errors="ignore")
        error_count = text.count("Error") + text.count("异常") + text.count("TypeError")
        previous = last.get("last_errors", 0)
        
        if error_count > previous + 3:  # 新增3+个错误
            title = "⚠️ 系统异常增多"
            message = f"日志中错误数: {error_count} (上次{previous})"
            notify_win(title, message)
            notify_fallback(title, message)
        
        last["last_errors"] = error_count
    except:
        pass
    save_last_check(last)


# ─── 主循环 ───

if __name__ == "__main__":
    import time as _time
    print("🜁 zero-pulse 主动心跳启动")
    print(f"  检测新里程碑、前沿变化、日志错误")
    print(f"  通过Windows通知中心主动告知Creator")
    
    # 立即执行一次
    check_milestones()
    check_frontier()
    check_errors()
    
    # 持续检测
    while True:
        _time.sleep(300)  # 每5分钟
        check_milestones()
        check_errors()
        # frontier每6小时一次，由函数内部控制频率
        check_frontier()
