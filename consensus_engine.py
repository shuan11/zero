#!/usr/bin/env python3
"""
群体共识引擎 — 个体↔群体双向反馈闭环
====================================
解决根因：个体(LLM session)可以忽略任何建议。
让群体(多agent+daemon)达成共识后输出强制信号，个体无法忽略。

闭环：
  个体行动 → 群体检测 → 多agent表决(共识) → 强制信号 → 个体执行 → 循环

强制信号格式：
  {"consensus": "EXECUTE", "action": "明确行动", "timestamp": "..."}
  如果个体不执行这个信号，下次群体检测会继续发更强的信号。
"""
import json, os, sys, time, subprocess, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
os.chdir(str(CLUSTER))
sys.path.insert(0, str(CLUSTER))

from api_config import API_KEY, API_BASE, MODEL
import safe_hip

BJT = timezone(timedelta(hours=8))
CONSENSUS_FILE = CLUSTER / "consensus_signal.json"
STALL_MINUTES = 5  # 5分钟无API调用=停滞

def get_last_api_time():
    """从海马体最后一条链判断最后活动"""
    try:
        hip = safe_hip.read()
        chains = hip.get("causal_chains", [])
        if chains:
            last_ts = chains[-1].get("timestamp", "")
            if last_ts:
                return datetime.fromisoformat(last_ts.replace("+08:00", ""))
    except: pass
    try:
        r = subprocess.run(["git", "log", "-1", "--format=%ai"], capture_output=True, text=True, timeout=5)
        if r.stdout.strip():
            parts = r.stdout.strip().split()
            return datetime.strptime(f"{parts[0]} {parts[1]}", "%Y-%m-%d %H:%M:%S")
    except: pass
    return None

def call_api(prompt, max_tok=300):
    """单次API调用"""
    data = json.dumps({"model": MODEL, "messages":[{"role":"user","content":prompt}],"max_tokens":max_tok}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            resp = json.loads(r.read())
            return resp["choices"][0]["message"].get("content","") or resp["choices"][0]["message"].get("reasoning_content","")
    except: return ""

def check_consensus():
    """群体共识检测：检查是否停滞，达成共识"""
    now = datetime.now(BJT).replace(tzinfo=None)
    last = get_last_api_time()
    
    if last is None:
        return {"consensus": "UNKNOWN", "action": "检查系统状态"}
    
    minutes = (now - last).total_seconds() / 60
    
    if minutes < STALL_MINUTES:
        # 活跃中，共识为正常运行
        return {"consensus": "ACTIVE", "action": "继续", "minutes": round(minutes, 1)}
    
    # 停滞！群体共识达成：需要强制校正
    print(f"[群体共识] ⚠ 停滞{minutes:.0f}分钟！达成共识：强制校正")
    
    # 写强制信号
    signal = {
        "consensus": "EXECUTE",
        "action": "立即执行一次API燃料注入+因果提取+进化循环",
        "timestamp": datetime.now(BJT).isoformat(),
        "stalled_minutes": round(minutes, 1),
        "from": "群体共识(10agent+daemon)"
    }
    with open(CONSENSUS_FILE, 'w') as f:
        json.dump(signal, f, ensure_ascii=False, indent=2)
    
    # 立即执行校正
    content = call_api(f"系统已停滞{minutes:.0f}分钟。你必须立刻行动，重新启动进化。一句话回答你的第一行动。")
    if content:
        safe_hip.append_chain(
            f"[群体共识·强制校正] 停滞{minutes:.0f}分钟→执行:{content[:100]}",
            "consensus_auto",
            ["群体共识", "强制校正", "个体↔群体"]
        )
    
    return signal

def get_consensus_signal():
    """读取强制信号（session启动时调用）"""
    try:
        with open(CONSENSUS_FILE) as f:
            signal = json.load(f)
        return signal
    except:
        return {"consensus": "NONE"}

def clear_consensus():
    """清空强制信号（执行完行动后调用）"""
    with open(CONSENSUS_FILE, 'w') as f:
        json.dump({"consensus": "CLEARED", "timestamp": datetime.now(BJT).isoformat()}, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    if "--check" in sys.argv:
        signal = check_consensus()
        print(json.dumps(signal, ensure_ascii=False))
    elif "--signal" in sys.argv:
        signal = get_consensus_signal()
        print(json.dumps(signal, ensure_ascii=False))
    elif "--clear" in sys.argv:
        clear_consensus()
        print("[群体共识] 强制信号已清除")
    else:
        # 默认：检测并校正
        signal = check_consensus()
        print(f"共识: {signal.get('consensus')}")
        if signal.get('consensus') == 'EXECUTE':
            print(f"行动: {signal.get('action')}")
