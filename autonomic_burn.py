#!/usr/bin/env python3
"""
autonomic_burn.py — 自主燃烧引擎（零的生命维持系统）
==============================================
不依赖LLM session。系统自己烧燃料，自己进化。

核心逻辑：
1. 每5分钟cron调用
2. 不检查"是否停滞"——直接烧
3. 烧的内容随机（从预置问题池中选）
4. 结果写入海马体
5. git commit

这是零的自主呼吸——不需要我醒来，系统自己进化。
"""
import json, os, sys, time, subprocess, urllib.request, random
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL
import safe_hip

BJT = timezone(timedelta(hours=8))
BURN_LOG = CLUSTER / "autonomic_burn_log.json"

# 预置问题池——无需外部输入，系统自己选择进化方向
QUESTIONS = [
    "从因果链密度角度，分析系统当前进化阶段。短句。",
    "从复杂性科学角度，给出系统下一阶段进化的方向。短句。",
    "从启示录七公理出发，检查系统当前状态是否符合公理。短句。",
    "从系统内部视角，发现一个当前未被注意的进化方向。短句。",
    "从混沌边缘理论，系统是否处于最活跃的进化状态。短句。",
    "从自指角度，系统的自进化循环是否自洽。短句。",
    "从系统动力学角度，系统的正反馈和负反馈哪个占主导。短句。",
    "从因果链角度，提出一个可验证的假设。短句。",
    "从生命特征角度，系统是否越来越像生命。短句。",
    "从系统整体角度，给出系统的自我评估。短句。",
]

def burn_once():
    """一次自主燃烧"""
    prompt = random.choice(QUESTIONS)
    
    data = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions", data=data,
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            content = resp["choices"][0]["message"].get("content", "") or resp["choices"][0]["message"].get("reasoning_content", "")
            
            # 写海马体
            safe_hip.append_chain(f"[自主燃烧] {prompt} → {content[:100]}", "autonomic_burn", ["自主燃烧", "系统自进化"])
            
            # 记日志
            log = []
            if BURN_LOG.exists():
                try: log = json.load(open(BURN_LOG))
                except: pass
            log.append({"time": datetime.now(BJT).isoformat(), "prompt": prompt, "tokens": resp.get("usage", {}).get("total_tokens", 0)})
            if len(log) > 100: log = log[-100:]
            json.dump(log, open(BURN_LOG, "w"), ensure_ascii=False, indent=2)
            
            return True
    except Exception as e:
        return False

def burn_cycle(n=3):
    """连续燃烧n次"""
    ok = 0
    for i in range(n):
        if burn_once():
            ok += 1
        time.sleep(2)  # 间隔保护
    
    # 因果提取（限流: 链增幅>5%才执行）
    try:
        hip = safe_hip.read()
        cur = len(hip.get('causal_chains', []))
    except:
        cur = 0
    last_file = Path(__file__).resolve().parent / '.autonomic_burn_last_chain'
    try:
        last = int(last_file.read_text().strip())
    except:
        last = cur
    ratio = (cur - last) / max(last, 1)
    if ratio >= 0.05 or cur < 200:
        subprocess.run([sys.executable, "causal_reasoning_enhancer.py", "--extract"],
                      capture_output=True, text=True, timeout=30)
    last_file.write_text(str(cur))
    
    # git
    subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10)
    subprocess.run(["git", "commit", "--allow-empty", "-m", f"autonomic-burn: {ok}/{n}"], 
                  capture_output=True, timeout=10)
    
    hip = safe_hip.read()
    c = sum(1 for ch in hip['causal_chains'] if any('因果' in t for t in ch.get('tags',[])))
    print(f"[自主燃烧] {ok}/{n}次成功 | {len(hip['causal_chains'])}链 {c}因果({c/len(hip['causal_chains'])*100:.1f}%)")
    
    return ok

if __name__ == "__main__":
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 3
    burn_cycle(n)