import sys, os, json

CONTENT = r'''
"""
uibot_bridge.py -- 零 UiBot Windows操作器官桥接器
WSL端 -> Windows端 自动化桥接。
"""

import os, sys, json, time, subprocess
from pathlib import Path

UIBOT_INSTALL = Path(r"C:\Program Files\Agentic Process Automation Platform Community\1.3.1.260514")
UIBOT_PYTHON = UIBOT_INSTALL / "python.exe"
SHARED_DIR = Path("/mnt/c/Users/h/Desktop/零/uibot_workspace")
SHARED_DIR_WIN = r"C:\Users\h\Desktop\零\uibot_workspace"

def ensure_workspace():
    SHARED_DIR.mkdir(parents=True, exist_ok=True)
    return SHARED_DIR

def _call_win_python(script_content, timeout=60):
    ensure_workspace()
    ts = time.strftime("%Y%m%d_%H%M%S")
    pid = os.getpid()
    script_name = f"zb_{ts}_{pid}.py"
    result_name = f"zr_{ts}_{pid}.json"
    sp = SHARED_DIR / script_name
    rp = SHARED_DIR / result_name
    rw = f"{SHARED_DIR_WIN}\\{result_name}"

    indented = '\n'.join('    ' + line for line in script_content.split('\n'))
    wrapper = '# coding=utf-8\nimport sys,json,traceback,os\n'
    wrapper += "sys.stdout.reconfigure(encoding='utf-8')\n"
    wrapper += "sys.stderr.reconfigure(encoding='utf-8')\n"
    wrapper += '_result={}\n'
    wrapper += 'try:\n'
    wrapper += indented + '\n'
    wrapper += 'except Exception as _e:\n'
    wrapper += "    _result['error']=traceback.format_exc()\n"
    wrapper += "    _result['success']=False\n"
    wrapper += "with open(r'" + rw + "','w',encoding='utf-8') as _f:\n"
    wrapper += "    json.dump(_result,_f,ensure_ascii=False,indent=2,default=str)\n"

    try:
        sp.write_text(wrapper, encoding='utf-8')
        pwin = str(UIBOT_PYTHON).replace('/mnt/c/', 'C:\\').replace('/', '\\')
        cmd = f'cd /d C:\\ && "{pwin}" "{SHARED_DIR_WIN}\\{script_name}"'
        proc = subprocess.run(["cmd.exe","/c",cmd], capture_output=True, text=True, timeout=timeout)
        if rp.exists():
            with open(rp, encoding='utf-8') as f:
                result = json.load(f)
            result.setdefault("success", True)
            result.setdefault("output", proc.stdout)
            result.setdefault("stderr", proc.stderr)
        else:
            result = {"success": proc.returncode==0, "output": proc.stdout, "stderr": proc.stderr}
        return result
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Timeout {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        try:
            if sp.exists(): sp.unlink()
            if rp.exists(): rp.unlink()
        except: pass

def ping():
    return _call_win_python('import sys; _result["v"]=sys.version; _result["p"]=sys.platform', timeout=15)

def list_windows():
    code = 'import win32gui; wins=[]\ndef cb(h,_):\n t=win32gui.GetWindowText(h)\n if t and win32gui.IsWindowVisible(h): wins.append({"h":h,"t":t,"c":win32gui.GetClassName(h)})\nwin32gui.EnumWindows(cb,None)\n_result["windows"]=wins\n_result["count"]=len(wins)'
    return _call_win_python(code, timeout=30)

def exec_notepad():
    code = 'import subprocess,time,win32gui,win32con\np=subprocess.Popen(["notepad.exe"])\ntime.sleep(1.5)\nwins=[]\ndef cb(h,_):\n t=win32gui.GetWindowText(h)\n if t and ("记事本" in t or "Notepad" in t): wins.append(h)\nwin32gui.EnumWindows(cb,None)\nhwnd=wins[0] if wins else None\n_result["hwnd"]=hwnd\nif hwnd:\n win32gui.ShowWindow(hwnd,win32con.SW_SHOW)\n win32gui.SetForegroundWindow(hwnd)\n time.sleep(0.5)\n _result["status"]="ok"\nelse:\n _result["status"]="nf"'
    return _call_win_python(code, timeout=30)

def screenshot():
    code = 'import win32gui,win32ui,win32con\nfrom PIL import Image\nhd=win32gui.GetDesktopWindow()\nl,t,r,b=win32gui.GetWindowRect(hd)\nw,h=r-l,b-t\nddc=win32gui.GetWindowDC(hd)\nidc=win32ui.CreateDCFromHandle(ddc)\nmdc=idc.CreateCompatibleDC()\nbm=win32ui.CreateBitmap()\nbm.CreateCompatibleBitmap(idc,w,h)\nmdc.SelectObject(bm)\nmdc.BitBlt((0,0),(w,h),idc,(0,0),win32con.SRCCOPY)\nbi=bm.GetInfo()\nbs=bm.GetBitmapBits(True)\nimg=Image.frombuffer("RGB",(bi["bmWidth"],bi["bmHeight"]),bs,"raw","BGRX",0,1)\nmdc.DeleteDC();idc.DeleteDC()\nwin32gui.ReleaseDC(hd,ddc)\nimg.save(r"' + SHARED_DIR_WIN.replace('\\', '\\\\') + r'" + "\\\\screenshot.png","PNG")\n_result["file"]=r"' + SHARED_DIR_WIN.replace('\\', '\\\\') + r'" + "\\\\screenshot.png"\n_result["w"]=w;_result["h"]=h'
    return _call_win_python(code, timeout=30)

def system_info():
    code = 'import platform,os\n_result["os"]=str(platform.uname())\n_result["cpu"]=os.cpu_count()\n_result["host"]=platform.node()\n_result["user"]=os.environ.get("USERNAME","")'
    return _call_win_python(code, timeout=15)

if __name__ == "__main__":
    cmds = {"ping": ping, "windows": list_windows, "screenshot": screenshot, "notepad": exec_notepad, "info": system_info}
    if len(sys.argv) > 1 and sys.argv[1] in cmds:
        r = cmds[sys.argv[1]]()
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print("Usage: ... <ping|windows|screenshot|notepad|info>")
'''

target = "/mnt/c/Users/h/Desktop/零/真元集群/uibot_bridge.py"
with open(target, 'w', encoding='utf-8') as f:
    f.write(CONTENT.strip())
print(f"Written {len(CONTENT)} bytes to {target}")
