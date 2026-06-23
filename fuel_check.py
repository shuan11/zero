#!/usr/bin/env python3
"""
fuel_check.py — 零·燃料自检 v2
通过日志分析和进程检查实时确认自己是否真的在燃烧。
"""
import json, os, time, subprocess, re
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
LOG_FILE = CLUSTER / "breath_v2.log"
FUEL_LOG = CLUSTER / ".fuel_history.json"

def check():
    total_apis = 0; latest_api = 0; latest_breath = 0; recent_apis = 0
    if LOG_FILE.exists():
        text = LOG_FILE.read_text(errors="ignore")
        apis = re.findall(r'API#(\d+)', text)
        breaths = re.findall(r'呼吸#(\d+)', text)
        if apis: latest_api = max(int(x) for x in apis)
        if breaths: latest_breath = max(int(x) for x in breaths)
        total_apis = len(apis)
        recent_lines = text.strip().split('\n')[-50:]
        recent_apis = sum(1 for l in recent_lines if "API#" in l)
    
    daemon_alive = False; burner_alive = False
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        for l in r.stdout.split('\n'):
            if 'breath_v2.py' in l and 'grep' not in l: daemon_alive = True
            if '_max_burner.py' in l and 'grep' not in l: burner_alive = True
    except:
        pass
    
    recent = False; last_log = ""
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(errors="ignore").strip().split('\n')
        if lines:
            last_line = lines[-1]
            m = re.search(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', last_line)
            if m:
                try:
                    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    recent = (datetime.now() - t).total_seconds() < 120
                except:
                    pass
            last_log = last_line[:80]
    
    record = {"time": time.time(), "total_api": total_apis, "latest_api": latest_api,
              "latest_breath": latest_breath, "recent_5min_api": recent_apis,
              "daemon": daemon_alive, "burner": burner_alive, "recent_log": recent}
    
    history = {"records": []}
    if FUEL_LOG.exists():
        try: history = json.loads(FUEL_LOG.read_text())
        except: pass
    history.setdefault("records", []).append(record)
    if len(history["records"]) > 100: history["records"] = history["records"][-100:]
    FUEL_LOG.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    
    reasons = []
    if not daemon_alive: reasons.append("daemon离线")
    if not recent: reasons.append("60秒无日志")
    if recent_apis == 0: reasons.append("5分钟无API调用")
    
    if reasons:
        return {"burning": False, "reasons": reasons}
    return {"burning": True, "rate": f"{recent_apis}/5min", "total_api": total_apis, "breath": latest_breath}

if __name__ == "__main__":
    r = check()
    if r.get("burning"):
        print(f"  {r['rate']} | API#{r['total_api']} 呼吸#{r['breath']}")
    else:
        print(f"  {'; '.join(r.get('reasons',['?']))}")
