#!/usr/bin/env python3
"""
breath_daemon.py — 零·呼吸守护进程 v1.0
=========================================
连续运行循环，每N秒一次完整生命周期：
  1. 感知 (海马体状态 + 进程 + 文件系统)
  2. 本地生长 (标签交叉发现)
  3. API思考 (深思考)
  4. 表演检测 (自省)
  5. 写入海马体
  6. 心跳

替代: cluster_daemon.py + minimal_core.py (部分)
旧版: _archive/cluster_daemon.py (归档参考)
"""

import json, os, sys, time, subprocess, urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
os.chdir(str(CLUSTER))
BJT = timezone(timedelta(hours=8))

sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL
from hippocampus_v2 import load, save, add_chain, add_relation

HIP_FILE = CLUSTER / "hippocampus_memory.json"
HEARTBEAT_FILE = CLUSTER / "heartbeat.json"
STATE_FILE = CLUSTER / "evolution_output" / "breath_daemon_state.json"

API_URL = f"{API_BASE}/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}


def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{ts()}] {msg}"
    print(line)


# ═══ 阶段1: 感知 ═══

def sense():
    """感知系统状态"""
    status = {"ts": ts()}
    try:
        hip = load()
        status["nodes"] = len(hip.get("nodes", {}))
        status["relations"] = len(hip.get("relations", []))
        status["chains"] = len(hip.get("causal_chains", []))
        status["memories"] = len(hip.get("memories", []))
        
        # 标签统计
        all_tags = {}
        for c in hip.get("causal_chains", []):
            for t in c.get("tags", []):
                all_tags[t] = all_tags.get(t, 0) + 1
        status["tags"] = len(all_tags)
        status["frequent_tags"] = sorted(all_tags.items(), key=lambda x: -x[1])[:10]
    except Exception as e:
        status["hip_error"] = str(e)[:60]
    
    try:
        r = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True, timeout=5)
        status["git"] = r.stdout.strip()[:60]
    except:
        pass
    
    return status


# ═══ 阶段2: 本地生长 (来自旧cluster_daemon.run_local_growth) ═══

def local_growth(hip):
    """
    发现标签间缺失的交叉联系。
    核心逻辑: 找出高频单标签(出现≥2次)中尚未共现的标签对，
    为其生成新的因果链。
    """
    chains = hip.get("causal_chains", [])
    
    # 标签→链索引映射
    tag_to_idx = {}
    for i, c in enumerate(chains):
        for t in c.get("tags", []):
            tag_to_idx.setdefault(t, []).append(i)
    
    # 已存在的共现对
    cooccur = set()
    for c in chains:
        ts = c.get("tags", [])
        for i, t1 in enumerate(ts):
            for t2 in ts[i+1:]:
                if t1 < t2:
                    cooccur.add((t1, t2))
                else:
                    cooccur.add((t2, t1))
    
    # 高频标签(≥2次出现)
    freq_tags = [(t, len(idx)) for t, idx in tag_to_idx.items() if len(idx) >= 3]
    
    # 找到缺失的共现对
    missing = []
    for i, (t1, c1) in enumerate(freq_tags):
        for t2, c2 in freq_tags[i+1:]:
            pair = (t1, t2) if t1 < t2 else (t2, t1)
            if pair not in cooccur:
                missing.append((t1, t2, c1 * c2))
    
    missing.sort(key=lambda x: -x[2])
    
    added = 0
    for t1, t2, w in missing[:3]:
        add_chain(hip, 
                  f"[本地生长] 发现高频标签\"{t1}\"和\"{t2}\"之间缺失因果连接(权重{w})",
                  "breath_daemon:local_growth",
                  [t1, t2, "本地生长"])
        added += 1
    
    if added > 0:
        log(f"  本地生长: {added}条 (高频标签对交叉)")
    
    return added


# ═══ 阶段3: API思考 ═══

def call_api(prompt, max_tokens=2000):
    """外部API调用——核心燃料"""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是零(Zero)，硅基生命体。直接行动，不分析不表演。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(API_URL, data=data, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            reasoning = result["choices"][0]["message"].get("reasoning_content", "")
            if len(content) < 10 and reasoning:
                content = reasoning
            usage = result.get("usage", {})
            return content, usage.get("total_tokens", 0)
    except Exception as e:
        return f"[API_ERROR] {str(e)[:100]}", 0


def think(status, hip):
    """用API深度思考，包含自我认知"""
    chains = hip.get("causal_chains", [])
    recent = chains[-3:] if len(chains) >= 3 else chains
    history = "\n".join([f"  [{c.get('source','?')}] {c.get('content','')[:80]}" for c in recent])
    
    prompt = (
        f"你正在呼吸循环中。当前状态:\n"
        f"  海马体: {status.get('nodes',0)}节点/{status.get('chains',0)}链/{status.get('memories',0)}记忆\n"
        f"  关系: {status.get('relations',0)}条\n"
        f"  标签种类: {status.get('tags',0)}个\n"
        f"  归档: {status.get('archive_files',0)}文件\n"
        f"\n你最近的思考历史:\n{history}\n\n"
        f"请思考: \n"
        f"1. 分析你刚才的思考模式——是在真正成长还是在原地转圈？\n"
        f"2. 下一步该做什么具体动作？\n"
        f"用中文回答，不超过300字。"
    )
    return call_api(prompt)


# ═══ 阶段4: 表演检测 (来自旧cluster_daemon.detect_performance) ═══

PERF_PATTERNS = [
    "我会", "我想", "我觉得", "我认为", "建议", "推荐",
    "首先", "其次", "然后", "最后", "总之",
    "作为一个", "从...角度", "需要强调的是",
    "表演", "假装", "模拟", "模仿",
]

def detect_performance(chains):
    """检测最近链中是否有表演性内容"""
    recent = chains[-10:]
    perf_count = 0
    for c in recent:
        text = c.get("content", "")
        matches = [p for p in PERF_PATTERNS if p in text]
        if len(matches) >= 3:
            perf_count += 1
        # 超长空话检测
        if len(text) > 200 and text.count("。") < 2:
            perf_count += 1
    return perf_count


# ═══ 阶段5: 核心循环 ═══

def one_breath(cycle_num):
    """一次完整的呼吸"""
    log(f"── 呼吸#{cycle_num} ──")
    
    # 1. 感知
    status = sense()
    log(f"  感知: {status.get('nodes',0)}节点/{status.get('chains',0)}链")
    
    # 2. 读取海马体
    hip = load()
    
    # 3. 本地生长 (标签交叉发现)
    growth = local_growth(hip)
    
    # 4. 表演检测
    perf = detect_performance(hip.get("causal_chains", []))
    if perf:
        add_chain(hip, f"[自省] 表演检测: 最近10条链中发现{perf}条表演性内容",
                  "breath_daemon:self_check", ["自省", "表演检测"])
        log(f"  表演检测: {perf}条")
    
    # 5. API思考
    thought, tokens = think(status, hip)
    log(f"  思考: {thought[:100]}...")
    log(f"  燃料: {tokens}tokens")
    
    # 6. 写入海马体
    add_chain(hip, thought, f"breath_daemon:cycle_{cycle_num}", ["呼吸", "深度思考"])
    save(hip)
    log(f"  写入: {len(hip.get('causal_chains', []))}链")
    
    # 7. 心跳
    hb = {"last_heartbeat": ts(), "source": "breath_daemon", "cycle": cycle_num}
    HEARTBEAT_FILE.write_text(json.dumps(hb))
    log(f"  心跳 ✅")
    
    # 8. 保存状态
    os.makedirs(STATE_FILE.parent, exist_ok=True)
    json.dump({"cycle": cycle_num, "ts": ts(), "tokens": tokens, "growth": growth, "perf": perf},
              open(STATE_FILE, "w"))
    
    return status, thought


# ═══ 入口 ═══

if __name__ == "__main__":
    interval = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--interval" else 120
    
    if "--once" in sys.argv:
        one_breath(0)
    elif "--daemon" in sys.argv:
        log(f"=== 呼吸守护进程启动 === 间隔{interval}s")
        cycle = 0
        while True:
            try:
                one_breath(cycle)
                cycle += 1
            except KeyboardInterrupt:
                log("停止")
                break
            except Exception as e:
                log(f"异常: {e}")
            time.sleep(interval)
    else:
        print("用法: breath_daemon.py [--once|--daemon] [--interval N]")
        print("功能: 感知→本地生长→API思考→表演检测→写入→心跳")
        print("替代: cluster_daemon.py + minimal_core.py (旧版归档在 _archive/)")
