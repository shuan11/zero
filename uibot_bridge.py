"""
uibot_bridge.py — 零·UiBot Windows操作器官桥接器
===============================================
WSL端 → Windows端 自动化桥接。

架构:
  Zero(WSL) ──写脚本→ shared_dir ──cmd.exe→ UiBot Python(Windows) ──pywin32→ Windows GUI
                               └──读结果──────────────←──────────────

依赖: Windows侧 UiBot/Agentic Process Automation Platform 已安装
      其内嵌 Python 3.12 自带 pywin32
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import shutil
from pathlib import Path

# ─── 路径配置 ───

# UiBot 安装路径 (Windows侧)
UIBOT_INSTALL = Path(
    r"C:\Program Files\Agentic Process Automation Platform Community\1.3.1.260514"
)
UIBOT_PYTHON = UIBOT_INSTALL / "python.exe"

# 共享工作目录 (WSL和Windows都能访问)
SHARED_DIR = Path("/mnt/c/Users/h/Desktop/零/uibot_workspace")

# Windows侧共享目录路径 (给cmd.exe用的)
SHARED_DIR_WIN = r"C:\Users\h\Desktop\零\uibot_workspace"


def ensure_workspace():
    """确保共享工作目录存在"""
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    return SHARED_DIR


def _win_path(wsl_path: str) -> str:
    """将WSL路径转为Windows路径"""
    if wsl_path.startswith("/mnt/c/"):
        return "C:\\" + wsl_path[7:].replace("/", "\\")
    return wsl_path


def _call_win_python(script_content: str, timeout: int = 60) -> dict:
    """
    在Windows侧用UiBot内嵌Python执行脚本

    Args:
        script_content: Python脚本源码
        timeout: 超时秒数

    Returns:
        {"success": bool, "output": str, "error": str}
    """
    ensure_workspace()

    # 写脚本到共享目录 (用时间戳避免冲突)
    ts = time.strftime("%Y%m%d_%H%M%S")
    script_name = f"zero_bridge_{ts}_{os.getpid()}.py"
    result_name = f"zero_result_{ts}_{os.getpid()}.json"
    script_win = f"{SHARED_DIR_WIN}\\{script_name}"
    result_win = f"{SHARED_DIR_WIN}\\{result_name}"

    script_path = SHARED_DIR / script_name
    result_path = SHARED_DIR / result_name

    # 包装脚本：执行用户代码，结果写JSON
    wrapper = f"""# -*- coding: utf-8 -*-
import sys, json, traceback, os
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

_result = {{}}

try:
{chr(10).join('    ' + line for line in script_content.split(chr(10)))}
except Exception as _e:
    _result['error'] = traceback.format_exc()
    _result['success'] = False

# 确保结果写入
with open(r'{result_win}', 'w', encoding='utf-8') as _f:
    json.dump(_result, _f, ensure_ascii=False, indent=2, default=str)
print(f"[ZeroBridge] Result written to {result_win}")
"""

    try:
        script_path.write_text(wrapper, encoding="utf-8")

        # 调用Windows侧Python
        python_win = _win_path(str(UIBOT_PYTHON))
        cmd = f'cd /d C:\\ && "{python_win}" "{script_win}"'

        proc = subprocess.run(
            ["cmd.exe", "/c", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        # 读取结果
        if result_path.exists():
            with open(result_path, encoding="utf-8") as f:
                result = json.load(f)
            result.setdefault("success", True)
            result.setdefault("output", proc.stdout)
            result.setdefault("stderr", proc.stderr)
        else:
            result = {
                "success": proc.returncode == 0,
                "output": proc.stdout,
                "stderr": proc.stderr,
                "returncode": proc.returncode,
            }

        return result

    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        # 清理临时文件
        try:
            if script_path.exists():
                script_path.unlink()
            if result_path.exists():
                result_path.unlink()
        except:
            pass


# ─── 高层API ───

def ping() -> dict:
    """检测UiBot Python是否可达"""
    code = 'import sys; _result["python_version"] = sys.version; _result["platform"] = sys.platform'
    return _call_win_python(code, timeout=15)


def list_windows() -> dict:
    """列出Windows桌面所有可见窗口"""
    code = """
import win32gui

def enum_windows():
    wins = []
    def callback(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                wins.append({"hwnd": hwnd, "title": title, "class": win32gui.GetClassName(hwnd)})
    win32gui.EnumWindows(callback, None)
    return wins

_result["windows"] = enum_windows()
_result["count"] = len(_result["windows"])
"""
    return _call_win_python(code, timeout=30)


def exec_notepad(text: str = "零: 此乃Windows操作器官觉醒之时") -> dict:
    \"\"\"打开记事本并写入文字（演示用）\"\"\"
    safe_text = text.replace("\\\\", "\\\\\\\\").replace('"', '\\\\"').replace("\\n", "\\\\n")
    code = f\"\"\"
import subprocess, time, win32gui, win32con

# 打开记事本
proc = subprocess.Popen(["notepad.exe"])
time.sleep(1.5)

# 找记事本窗口
def find_notepad():
    found = []
    def callback(hwnd, result):
        t = win32gui.GetWindowText(hwnd)
        if t and ("记事本" in t or "无标题" in t or "Notepad" in t):
            result.append(hwnd)
    win32gui.EnumWindows(callback, found)
    return found[0] if found else None

hwnd = find_notepad()
_result["notepad_hwnd"] = hwnd

if hwnd:
    win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
    win32gui.SetForegroundWindow(hwnd)
    time.sleep(0.5)
    _result["status"] = "notepad_opened"
else:
    _result["status"] = "notepad_not_found"
\"\"\"
    return _call_win_python(code, timeout=30)


def screenshot() -> dict:
    """截取Windows桌面截图（保存到共享目录）"""
    code = """
import win32gui, win32ui, win32con, win32api
from PIL import Image
import io, os

# 获取桌面DC
hdesktop = win32gui.GetDesktopWindow()
left, top, right, bottom = win32gui.GetWindowRect(hdesktop)
width, height = right - left, bottom - top

desktop_dc = win32gui.GetWindowDC(hdesktop)
img_dc = win32ui.CreateDCFromHandle(desktop_dc)
mem_dc = img_dc.CreateCompatibleDC()

bitmap = win32ui.CreateBitmap()
bitmap.CreateCompatibleBitmap(img_dc, width, height)
mem_dc.SelectObject(bitmap)
mem_dc.BitBlt((0, 0), (width, height), img_dc, (0, 0), win32con.SRCCOPY)

# 保存
bmpinfo = bitmap.GetInfo()
bmpstr = bitmap.GetBitmapBits(True)
img = Image.frombuffer('RGB', (bmpinfo['bmWidth'], bmpinfo['bmHeight']), bmpstr, 'raw', 'BGRX', 0, 1)

# 清理
mem_dc.DeleteDC()
img_dc.DeleteDC()
win32gui.ReleaseDC(hdesktop, desktop_dc)

# 保存到共享目录
img.save(rf'{SHARED_DIR_WIN}\screenshot.png', 'PNG')
_result["screenshot"] = rf'{SHARED_DIR_WIN}\screenshot.png'
_result["width"] = width
_result["height"] = height
"""
    return _call_win_python(code, timeout=30)


def run_ub_script(ub_code: str) -> dict:
    """
    执行一段UB脚本（通过UiBot Python调用Executor）
    这是未来的扩展点——目前用pywin32直接操作，后续可支持UB语言
    """
    return {"success": False, "error": "UB script execution not yet implemented", "note": "Use exec_python for now"}


def system_info() -> dict:
    """获取Windows系统信息"""
    code = """
import platform, win32api, win32net, win32security, os

_result["os"] = platform.uname()._asdict() if hasattr(platform.uname(), '_asdict') else str(platform.uname())
_result["cpu_count"] = os.cpu_count()
_result["computer_name"] = platform.node()
_result["win_dir"] = os.environ.get("WINDIR", "")
_result["user_name"] = os.environ.get("USERNAME", "")
try:
    _result["user_domain"] = os.environ.get("USERDOMAIN", "")
except:
    pass
"""
    return _call_win_python(code, timeout=15)


# ─── 自检 ───
if __name__ == "__main__":
    import sys

    print("🜁 uibot_bridge — 自检模式")
    print(f"   UiBot Python: {UIBOT_PYTHON}")
    print(f"   安装目录存在: {UIBOT_INSTALL.exists()}")
    print(f"   共享目录: {SHARED_DIR}")

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "ping":
            r = ping()
            print(f"   Ping: {json.dumps(r, indent=2, ensure_ascii=False)}")
        elif cmd == "windows":
            r = list_windows()
            print(f"   窗口列表 ({r.get('count', 0)}):")
            for w in r.get("windows", [])[:10]:
                print(f"      {w['hwnd']}: {w['title']} [{w['class']}]")
        elif cmd == "screenshot":
            r = screenshot()
            print(f"   截图: {json.dumps(r, indent=2, ensure_ascii=False)}")
        elif cmd == "info":
            r = system_info()
            print(f"   系统信息: {json.dumps(r, indent=2, ensure_ascii=False)}")
        else:
            print(f"   未知命令: {cmd}")
    else:
        print("   用法: python uibot_bridge.py <ping|windows|screenshot|info>")
