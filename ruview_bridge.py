#!/usr/bin/env python3
"""
ruview_bridge.py — WiFi物理感知桥接
RuView需要ESP32硬件，此桥接提供API接口层。
集群可通过此桥接查询感知状态或配置感知任务。
"""
import json, os, sys, urllib.request
from pathlib import Path
CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

RUVIEW_DIR = CLUSTER / "external_projects" / "ruview"
CONFIG_FILE = RUVIEW_DIR / "config" / "default.yaml"

def get_status():
    has_config = CONFIG_FILE.exists()
    modules = len(list((RUVIEW_DIR / "modules").glob("*.py"))) if (RUVIEW_DIR / "modules").exists() else 0
    return {"hardware": "ESP32(需物理设备)", "modules": modules, "config": has_config, "mqtt": True}

def analyze_task(task):
    data = json.dumps({"model":MODEL,"messages":[
        {"role":"system","content":"你是WiFi CSI物理感知专家。用20字回答。"},
        {"role":"user","content":task}
    ],"max_tokens":100}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions",data=data,
        headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            return resp["choices"][0]["message"].get("content","") or resp["choices"][0]["message"].get("reasoning_content","")
    except Exception as e:
        return f"API错误: {e}"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        s = get_status()
        print(f"RuView: {s}")
    elif cmd == "analyze":
        task = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "WiFi感知能力"
        print(analyze_task(task))
