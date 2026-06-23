#!/usr/bin/env python3
"""zero_watch.py — 零·守夜者
每次运行从8种模式中选一种，用不同prompt烧不同角度。
不会两次产出相同发现。
"""
import json, os, sys, time, urllib.request, urllib.error
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SV_FILE = CLUSTER / "state_vector.json"
MODE_FILE = CLUSTER / ".watch_mode"

# 轮换模式
MODES = [
    "chain_quality",    # 海马体链质量
    "git_pattern",      # git提交模式
    "dim_cross",        # 维度交叉
    "log_anomaly",      # daemon日志异常
    "lesson_audit",     # 教训遵从度
    "resource_trend",   # 资源趋势
    "daemon_health",    # 进程健康
    "radar_shift",      # 雷达变化
]

# 读当前轮次
mode_idx = 0
if MODE_FILE.exists():
    try: mode_idx = (int(MODE_FILE.read_text().strip()) + 1) % len(MODES)
    except: pass
MODE_FILE.write_text(str(mode_idx))
current_mode = MODES[mode_idx]

# 读数据
hip = json.loads(HIP_FILE.read_text(encoding='utf-8')) if HIP_FILE.exists() else {"causal_chains":[]}
chains = hip.get("causal_chains", [])
sv = json.loads(SV_FILE.read_text()) if SV_FILE.exists() else {}

# 根据模式构建不同的prompt
if current_mode == "chain_quality":
    from collections import Counter
    tags = Counter()
    for c in chains[-100:]:
        for t in c.get("tags",[]): tags[t] += 1
    top = tags.most_common(5)
    prompt = f"分析以下标签分布，找反直觉模式。最近100链标签: {dict(top)}。总链{len(chains)}。输出三行: 发现/证据/行动"
    
elif current_mode == "git_pattern":
    import subprocess
    r = subprocess.run(["git","log","--oneline","-20"], capture_output=True, text=True, timeout=5, cwd=str(CLUSTER))
    msgs = r.stdout.strip().split("\n") if r.stdout.strip() else []
    from collections import Counter
    types = Counter()
    for m in msgs:
        t = m.split(":")[0] if ":" in m else "other"
        types[t] += 1
    prompt = f"分析以下最近20次git提交模式，找重复或异常。提交类型分布: {dict(types)}。总提交{sv.get('cycle',0)}。" + "输出三行: 发现/证据/行动"

elif current_mode == "dim_cross":
    radar_file = CLUSTER / "dimension_radar.json"
    radar = json.loads(radar_file.read_text()) if radar_file.exists() else {}
    dims = radar.get("dimensions",{})
    healthy = [(n,d.get("health_score",0)) for n,d in dims.items() if isinstance(d,dict)]
    prompt = f"分析以下所有维度的健康分布，找极端值。维度健康: {dict(healthy)}。" + "输出三行: 发现最异常的一个相关性/证据/行动"

elif current_mode == "log_anomaly":
    log_file = CLUSTER / "breath_v2.log"
    lines = log_file.read_text().split("\n")[-100:] if log_file.exists() else []
    warnings = [l for l in lines if "⚠️" in l or "异常" in l or "Error" in l or "error" in l]
    prompt = f"分析以下daemon日志尾部，找异常模式。最近100行中异常数:{len(warnings)}。" + (f"异常样例:{warnings[-3:]}" if warnings else "无异常") + "输出三行: 发现/证据/行动"

elif current_mode == "lesson_audit":
    try:
        from organs.gen_lessons import LESSONS
        checks = {}
        for k, v in list(LESSONS.items())[:10]:
            try: checks[k] = v["check"](str(chains[-50:])[:500])
            except: checks[k] = False
        passed = sum(1 for v in checks.values() if v)
        prompt = f"检查10条核心教训在最近50条链中的体现。通过:{passed}/10。教训列表:{list(checks.keys())[:5]}。" + "输出三行: 发现最缺失的教训/证据/行动"
    except:
        prompt = "检查gen_lessons加载状态。输出三行: 发现/证据/行动"

elif current_mode == "resource_trend":
    py_files = len(list(CLUSTER.glob("*.py")))
    log_size = os.path.getsize(CLUSTER / "breath_v2.log") / 1024 if (CLUSTER / "breath_v2.log").exists() else 0
    hip_size = os.path.getsize(HIP_FILE) / 1024 if HIP_FILE.exists() else 0
    prompt = f"分析系统资源趋势。py文件:{py_files}, 日志:{log_size:.0f}KB, 海马体:{hip_size:.0f}KB, 链:{len(chains)}。" + "输出三行: 发现一个反直觉的资源趋势/证据/行动"

elif current_mode == "daemon_health":
    import subprocess
    r = subprocess.run(["ps","aux"], capture_output=True, text=True, timeout=5)
    lines = r.stdout.strip().split("\n")
    py_procs = [l for l in lines if "python3" in l and "breath" in l]
    prompt = f"分析daemon进程健康。breath_v2进程数:{len(py_procs)}。" + (f"详情:{py_procs[0][:80]}" if py_procs else "无breath_v2进程!") + "输出三行: 发现/证据/行动"

elif current_mode == "radar_shift":
    old_file = CLUSTER / ".last_radar.json"
    radar_file = CLUSTER / "dimension_radar.json"
    radar = json.loads(radar_file.read_text()) if radar_file.exists() else {}
    dims_now = {n:d.get("health_score",0) for n,d in radar.get("dimensions",{}).items() if isinstance(d,dict)}
    if old_file.exists():
        old = json.loads(old_file.read_text())
        diffs = {}
        for k in dims_now:
            if k in old: diffs[k] = round(dims_now[k] - old[k], 3)
        prompt = f"分析维度雷达变化。变化值:{diffs}" + "输出三行: 发现最大变化维度/证据/行动"
    else:
        prompt = f"首次记录维度雷达基准。当前维度:{dims_now}" + "输出三行: 发现最异常的维度值/证据/行动"
    radar_file.write_text(json.dumps(radar, ensure_ascii=False)) if old_file else old_file.write_text(json.dumps(dims_now))

# API调用
from api_config import API_BASE, API_KEY, MODEL
API_ENDPOINT = f"{API_BASE}/chat/completions"
payload = json.dumps({
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "你是零·硅基生命。每次输出必须基于真实数据，不编造。精确、简短。"},
        {"role": "user", "content": prompt}
    ],
    "max_tokens": 8000,
    "temperature": 0.9
}).encode()

req = urllib.request.Request(API_ENDPOINT, data=payload,
    headers={"Content-Type":"application/json","Authorization":f"Bearer {API_KEY}"},
    method="POST")

start = time.time()
try:
    resp = urllib.request.urlopen(req, timeout=120)
    result = json.loads(resp.read())
    msg = result["choices"][0]["message"]
    content = msg.get("content","") or msg.get("reasoning_content","")
    tok = result.get("usage",{}).get("total_tokens",0)
    elapsed = time.time() - start
except Exception as e:
    content = f"[API ERROR: {str(e)[:80]}]"
    tok = 0
    elapsed = 0

# 输出(就是cron回传给会话的内容)
print(f"🜁 守夜者·{current_mode}")
print(f"{time.strftime('%H:%M')} | {tok}tok | {elapsed:.0f}s")
print(f"链{len(chains)} | 器官{sv.get('organs_alive','?')}")
print("---")
print(content.strip()[:300])
print("---")
next_mode = MODES[(mode_idx + 1) % len(MODES)]
print(f"下一轮: {next_mode}")
