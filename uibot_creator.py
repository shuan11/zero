"""uibot_creator.py — UiBot自动化 Creator Community 软件"""

import sys, subprocess, json, os, time
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

CREATOR_LNK = r'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Agentic Process Automation Community\Creator Community.lnk'
CREATOR_EXE = r'C:\Program Files\Agentic Process Automation Platform Community\1.3.1.260514\Creator.exe'
CLUSTER = Path(r'C:\Users\h\Desktop\零\真元集群')
SIGNAL_FILE = CLUSTER / '.uibot_creator_status'

def check_running():
    """检查Creator进程是否运行"""
    try:
        r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq Creator.exe', '/FO', 'CSV'],
                         capture_output=True, text=True, timeout=10)
        return 'Creator.exe' in r.stdout
    except:
        return False

def launch_creator():
    """启动Creator Community"""
    try:
        # 方法1: 通过快捷方式
        subprocess.Popen(['cmd', '/c', 'start', '', CREATOR_LNK],
                        shell=True, start_new_session=True)
        time.sleep(3)
        if check_running():
            return "启动成功"
        # 方法2: 直接运行exe
        subprocess.Popen([CREATOR_EXE], start_new_session=True)
        time.sleep(5)
        if check_running():
            return "启动成功(直连)"
        return "启动失败: 进程未出现"
    except Exception as e:
        return f"启动异常: {str(e)[:80]}"

def get_status():
    """获取Creator状态"""
    running = check_running()
    return {
        "time": datetime.now().isoformat(),
        "running": running,
        "source": "uibot_creator",
        "message": "运行中" if running else "未启动"
    }

if __name__ == '__main__':
    import json
    status = get_status()
    if not status["running"]:
        result = launch_creator()
        status["launch_result"] = result
    # 写状态信号
    SIGNAL_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2))
    print(f'Creator Community: {"✅ 运行中" if status["running"] else "❌ 未运行"}')
    if "launch_result" in status:
        print(f'  启动: {status["launch_result"]}')
    print(f'  状态: {json.dumps(status, ensure_ascii=False)}')
