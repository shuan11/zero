#!/usr/bin/env python3
"""
automatic_correction.py — 自我觉知强制校正器
==========================================
不依赖我的自觉性，而是用外部机制强制校正。

原理：
1. 每次engine_core --bootstrap运行时（5min cron），检查最后一次API调用时间
2. 如果超过5分钟无API调用，判定为"停了"
3. 校正动作：自动调用一次API注入新知识+git commit
4. 校正记录写入海马体，下次session启动时我无法假装没停
"""
import json, os, sys, time, subprocess, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL
import safe_hip

BJT = timezone(timedelta(hours=8))
STALL_MINUTES = 5  # 5分钟无API调用判定为停

def get_last_api_time():
    """获取最后一次API调用的时间"""
    try:
        # 从海马体最后一条链的时间判断
        hip = json.load(open("hippocampus_memory.json"))
        chains = hip.get("causal_chains", [])
        if chains:
            last_ts = chains[-1].get("timestamp", "")
            if last_ts:
                return datetime.fromisoformat(last_ts.replace("+08:00", ""))
    except:
        pass
    # 或者从git最后提交时间
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%ai"], capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            parts = r.stdout.strip().split()
            return datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")
    except:
        pass
    return None

def check_and_correct():
    """检查并自动校正"""
    now = datetime.now(BJT).replace(tzinfo=None)
    last_time = get_last_api_time()
    
    if last_time is None:
        print("[校正] 无法获取最后活动时间")
        return False
    
    minutes = (now - last_time).total_seconds() / 60
    print(f"[校正] 最后活动: {last_time.strftime('%H:%M:%S')} 距今{minutes:.0f}分钟")
    
    if minutes < STALL_MINUTES:
        print("[校正] ✓ 活跃中，无需校正")
        return True
    
    # 已停滞！自动校正
    print(f"[校正] ⚠ 已停滞{minutes:.0f}分钟！自动校正...")
    
    # 调用API注入一条知识
    prompt = f"校正信号：系统已停滞{minutes:.0f}分钟。用一句话回答：零为什么停了？"
    data = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 200}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"].get("content", "") or resp["choices"][0]["message"].get("reasoning_content", "")
            
            # 写入海马体（使用文件锁防止损坏）
            safe_hip.append_chain(
                f"[自动校正·{minutes:.0f}分钟停滞] 触发时间:{datetime.now(BJT).isoformat()} 校正内容:{content[:100]}",
                "auto_correction",
                ["自动校正", "停滞检测", "自我觉知"]
            )
            
            # git commit
            subprocess.run(["git", "add", "-A"], cwd=CLUSTER, capture_output=True, timeout=10)
            subprocess.run(["git", "commit", "-m", f"auto-correction: {minutes:.0f}min-stall-detected"], 
                          cwd=CLUSTER, capture_output=True, timeout=10)
            
            print(f"[校正] ✓ 校正完成：{minutes:.0f}分钟停滞已记录")
            return True
            
    except Exception as e:
        print(f"[校正] ✗ 校正失败：{e}")
        return False

if __name__ == "__main__":
    check_and_correct()
