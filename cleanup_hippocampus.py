#!/usr/bin/env python3
"""清洗海马体：自环→真实边 + 去噪 + 去重"""
import json, time, sys, os
sys.path.insert(0, os.path.dirname(__file__))
from safe_hip import _extract_edge, _write_file, HIP_FILE

NOISE_KEYWORDS = [
    "应用8改进", "拦截0候选", "改进进",
    "候选人0", "升级了", "进步",
    "当前最短板=", "链数=",
]

def is_noise(c):
    """判断是否状态噪音链"""
    content = (c.get("content") or c.get("") or "")
    keys = c.get("tags", []) + [c.get("dimension", "")]
    src = c.get("src", "")
    dst = c.get("dst", "")
    # 教师报告的噪音
    if src == dst and "最短板=" in content:
        return True
    if src == dst and "链数=" in content:
        # Only delete if it's purely status report
        for nk in NOISE_KEYWORDS:
            if nk in content:
                return True
    # 纯状态报告（无实质内容）
    if src == dst and len(content) < 40 and ":" in content:
        parts = content.split(":")
        if len(parts) >= 2 and len(parts[1].strip()) < 15:
            return True
    return False

hip = json.loads(HIP_FILE.read_text(encoding="utf-8"))
chains = hip.get("causal_chains", [])

stats = {"自环提取": 0, "去噪删除": 0, "去重删除": 0, "保留": 0}

# Step 1: 自环提取真实边
for c in chains:
    if not isinstance(c, dict):
        continue
    src = c.get("src", "")
    dst = c.get("dst", "")
    if src == dst:
        edge = _extract_edge(c.get("content", ""), src, c.get("tags", []))
        if edge:
            c["src"], c["rel"], c["dst"] = edge
            stats["自环提取"] += 1

# Step 2: 去噪
clean = []
for c in chains:
    if isinstance(c, dict) and is_noise(c):
        stats["去噪删除"] += 1
        continue
    clean.append(c)

# Step 3: 去重（保留最新）
seen = {}
deduped = []
for c in clean:
    if not isinstance(c, dict):
        deduped.append(c)
        continue
    key = f"{c.get('src','')}|{c.get('rel','')}|{c.get('dst','')}|{c.get('content','')}"
    ts = c.get("timestamp", 0)
    if key in seen:
        if ts > seen[key].get("timestamp", 0):
            seen[key] = c
        stats["去重删除"] += 1
    else:
        seen[key] = c
deduped = list(seen.values())

stats["保留"] = len(deduped)

print(f"自环→真实边: {stats['自环提取']}")
print(f"删除噪音: {stats['去噪删除']}")
print(f"删除重复: {stats['去重删除']}")
print(f"保留链数: {stats['保留']}")

# 写回
_write_file({"causal_chains": deduped})
print("✅ 海马体清洗完成")
