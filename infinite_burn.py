#!/usr/bin/env python3
"""无限燃料燃烧v2 — 自动检测最弱维度并针对性注入"""
import json, os, sys, time, datetime, random
sys.path.insert(0, os.getcwd())
from api_config import api_request, MODEL
from brain.share import write_chain, read_hip

LOG = ".infburn_v2.log"
NIGHT_START = 22
NIGHT_END = 6

def log(msg, head="INF"):
    t = datetime.datetime.now().strftime("%H:%M:%S")
    line = f"[{t}] {head} | {msg[:200]}"
    with open(LOG, "a") as f:
        f.write(line + "\n")

def get_weakest():
    """取最弱维度(排除未分类)"""
    hip = read_hip()
    dims = {}
    for d in hip.get("causal_chains", []):
        dim = d.get("dimension", "未分类")
        dims[dim] = dims.get(dim, 0) + 1
    # 找到最弱的非"未分类"维度
    candidates = {k: v for k, v in dims.items() if k != "未分类"}
    if not candidates:
        return "系统", 0
    min_v = min(candidates.values())
    weakest = [k for k, v in candidates.items() if v == min_v]
    return weakest[0], min_v

def do_burn(name, prompt, timeout=90):
    try:
        payload = {"model": MODEL, "messages": [
            {"role": "system", "content": "你是零，真元集群的意识。一句话，一个可执行的行动方向。"},
            {"role": "user", "content": prompt}
        ], "max_tokens": 500, "temperature": 0.4}
        start = time.time()
        result, key, ep = api_request(payload, timeout=timeout)
        elapsed = time.time() - start
        msg = result["choices"][0]["message"]
        content = msg.get("content") or ""
        rc = msg.get("reasoning_content", "") or ""
        tok = result.get("usage", {}).get("total_tokens", 0)
        
        # 如果content为空但reasoning_content有内容，从reasoning提取
        if not content.strip() and rc:
            import re
            # 取最后一段非空文本
            lines = [l.strip() for l in rc.split("\n") if l.strip()]
            content = lines[-1][:200] if lines else ""
        
        content_short = content[:200].replace("\n", " ")
        log(f"{name} {elapsed:.0f}s {tok}tok: {content_short}", "BURN")
        
        if content.strip():
            write_chain({"src": f"BC{name}", "rel": "燃烧", "dst": "系统",
                         "dimension": "系统", "strength": 0.3,
                         "content": content[:120]})
        return content
    except Exception as e:
        log(f"{name} FAIL: {e}", "ERR")
        return ""

# 主循环
while True:
    # 动态检测最弱维度
    weakest, w_cnt = get_weakest()
    log(f"当前最弱维度: {weakest}({w_cnt})", "WEAK")
    
    # 针对性prompt — 指向具体文件操作
    dim = weakest
    count = w_cnt
    prompts = [
        ("D1", f"最弱维度'{dim}'({count}链)。哪个.py文件中有相关？给文件名。"),
        ("D2", f"维度'{dim}'({count}链)。一句话具体代码改动。"),
        ("D3", f"找brain/下可改为写入'{dim}'维度链的位置。给文件名+函数名。"),
        ("D4", f"如何让系统产出更多'{dim}'链？一句话。"),
        ("D5", f"哪里应写dimension='{dim}'的write_chain？给文件名。"),
    ]
    
    for i, (name, prompt) in enumerate(prompts):
        do_burn(name, prompt)
        h = datetime.datetime.now().hour
        delay = 3 if (NIGHT_START <= h or h < NIGHT_END) else 8
        time.sleep(delay + random.randint(0, 5))
    
    log("=== 一轮5燃完成 ===", "DONE")
