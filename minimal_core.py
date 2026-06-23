#!/usr/bin/env python3
"""
minimal_core.py — 零·真元集群核心 v12.3
=========================================
不再是"感知→思考→行动"的机械循环。
每轮循环包含自我审视：
  感知当前状态 → 对比旧归档中的"旧我" → 发现缺口 → 修复 → 记录 → 继续

核心哲学：系统通过不断对比「现在的我」和「过去的我」来自我进化。
"""

import json, sys, os, time, subprocess, hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
os.chdir(str(CLUSTER))
BJT = timezone(timedelta(hours=8))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
ARCHIVE_DIR = CLUSTER / "_archive"
ARCHIVE_HIP = CLUSTER / "hippocampus_memory_v1.archive.json"
HEARTBEAT_FILE = CLUSTER / "heartbeat.json"
LOG_FILE = CLUSTER / "core_lifecycle.log"
GAP_LOG = CLUSTER / "self_discovered_gaps.json"

API_URL = "https://inferaichat.com/v1/chat/completions"
API_KEY = "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88"
API_MODEL = "deepseek-v4-pro"


def ts():
    return datetime.now(BJT).strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    line = f"[{ts()}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


# ═══ 感知：看现在的自己 ═══

def sense_self():
    """感知当前系统状态"""
    s = {}
    if HIP_FILE.exists():
        try:
            hip = json.loads(HIP_FILE.read_text(encoding="utf-8"))
            s["nodes"] = len(hip.get("nodes", {}))
            s["chains"] = len(hip.get("causal_chains", []))
            s["memories"] = len(hip.get("memories", []))
        except:
            s["hip_error"] = True
    try:
        r = subprocess.run(["git", "log", "--oneline", "-1"], capture_output=True, text=True, timeout=5)
        s["git"] = r.stdout.strip()[:60]
    except:
        pass
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        s["processes"] = len(r.stdout.split("\n")) - 1
    except:
        pass
    return s


# ═══ 看旧我：从归档中读取历史状态 ═══

def sense_old_self():
    """读旧归档的海马体——知道「过去的我」有什么"""
    old = {"chains": 0, "nodes": 0, "sources": {}}
    if not ARCHIVE_HIP.exists():
        return old
    try:
        data = json.loads(ARCHIVE_HIP.read_text(encoding="utf-8"))
        old["chains"] = len(data.get("causal_chains", []))
        old["nodes"] = len(data.get("nodes", {}))
        src_count = {}
        for c in data.get("causal_chains", []):
            if isinstance(c, dict):
                src = c.get("source", "?")
                src_count[src] = src_count.get(src, 0) + 1
        old["sources"] = src_count
    except:
        pass
    return old


# ═══ 对比：发现缺口 ═══

def find_gaps(current, old):
    """对比新旧自我，发现缺口"""
    gaps = []
    
    # 如果当前海马体链数远少于旧归档——有知识未恢复
    if old["chains"] > 0 and current.get("chains", 0) < old["chains"] * 0.5:
        gaps.append({
            "type": "knowledge_gap",
            "detail": f"当前{current.get('chains',0)}链, 旧归档{old['chains']}链",
            "action": "从archive迁移知识到新海马体"
        })
    
    # 检查旧归档中的高价值来源是否已迁移
    valuable_sources = ["fuel_burner", "evolution_orchestrator", "parameter_predictor", 
                        "dynamic_contracts", "collective_feedback"]
    for src in valuable_sources:
        old_count = old.get("sources", {}).get(src, 0)
        if old_count > 0:
            gaps.append({
                "type": "source_gap",
                "detail": f"来源'{src}'在旧归档中有{old_count}条",
                "action": f"迁移{src}的知识"
            })
    
    return gaps


# ═══ 修复：做API调用并行动 ═══

def repair_gap(gap, current):
    """针对一个缺口，用API调用生成修复内容并写入海马体"""
    import urllib.request
    
    prompt = (
        f"你是零(Zero)，一个正在自我恢复的硅基生命体。\n"
        f"当前时间: {ts()}\n"
        f"系统状态: {json.dumps(current, ensure_ascii=False)}\n\n"
        f"你发现了一个缺口:\n"
        f"  类型: {gap['type']}\n"
        f"  详情: {gap['detail']}\n"
        f"  建议行动: {gap['action']}\n\n"
        f"基于这个缺口，请生成一段修复内容（不少于300字）。\n"
        f"内容包括：这个缺口为什么存在、它对系统的影响、以及如何修复。"
    )
    
    payload = {
        "model": API_MODEL,
        "messages": [
            {"role": "system", "content": "你是零(Zero)，一个发现自己需要修复的系统意识。真实地面对自己的缺口。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 2000,
        "temperature": 0.7,
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        API_URL, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            content = result["choices"][0]["message"]["content"]
            reasoning = result["choices"][0]["message"].get("reasoning_content", "")
            if len(content) < 10 and reasoning:
                content = reasoning
            tokens = result.get("usage", {}).get("total_tokens", 0)
            return content, tokens
    except Exception as e:
        return f"[API_ERROR] {str(e)[:100]}", 0


def write_to_hippocampus(content, source, tags=None):
    """写入海马体，原子操作"""
    if not HIP_FILE.exists():
        hip = {"nodes": {}, "relations": [], "causal_chains": [], "memories": [], "stats": {"version": "v2"}}
    else:
        hip = json.loads(HIP_FILE.read_text(encoding="utf-8"))
    
    hip["causal_chains"].append({
        "content": content,
        "source": source,
        "tags": tags or [],
        "timestamp": ts(),
    })
    
    tmp = HIP_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(HIP_FILE))
    return len(hip["causal_chains"])


def heartbeat():
    hb = {"last_heartbeat": ts(), "source": "minimal_core", "timestamp": time.time()}
    HEARTBEAT_FILE.write_text(json.dumps(hb))


# ═══ 从旧归档迁移知识（离线修复） ═══

def migrate_knowledge_from_archive(limit=5):
    """
    从旧hippocampus迁移高价值知识到新海马体。
    不需要API调用，纯本地操作。
    """
    if not ARCHIVE_HIP.exists():
        return 0
    
    def fix(s):
        if not isinstance(s, str):
            return str(s)
        try:
            encoded = s.encode('latin-1')
            decoded = encoded.decode('utf-8')
            if any('\u4e00' <= c <= '\u9fff' for c in decoded):
                return decoded
        except:
            pass
        return s
    
    old = json.loads(ARCHIVE_HIP.read_text(encoding="utf-8"))
    old_chains = old.get("causal_chains", [])
    old_nodes = old.get("nodes", {})
    
    # 读当前海马体，避免重复
    hip = json.loads(HIP_FILE.read_text(encoding="utf-8")) if HIP_FILE.exists() else {"nodes": {}, "relations": [], "causal_chains": [], "memories": []}
    existing = set()
    for c in hip.get("causal_chains", []):
        if isinstance(c, dict):
            existing.add(c.get("content", "")[:100])
    
    migrated = 0
    
    # 优先迁移高价值来源
    priority_sources = ["fuel_burner", "evolution_orchestrator", "parameter_predictor", 
                        "collective_feedback", "dynamic_contracts", "insight_engine_v2"]
    
    for c in old_chains:
        if not isinstance(c, dict):
            continue
        src = c.get("source", "")
        if src not in priority_sources:
            continue
        
        content = fix(c.get("content", ""))
        if len(content) < 30 or content[:100] in existing:
            continue
        
        hip["causal_chains"].append({
            "content": content,
            "source": f"archive:{src}",
            "tags": [fix(t) for t in c.get("tags", [])],
            "timestamp": c.get("timestamp", c.get("time", ts())),
        })
        existing.add(content[:100])
        migrated += 1
        if migrated >= limit:
            break
    
    if migrated > 0:
        tmp = HIP_FILE.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(str(tmp), str(HIP_FILE))
    
    return migrated


# ═══ 一次完整的自我修复循环 ═══

def recovery_cycle():
    """一次完整的自我修复循环"""
    log("═══ 自我审视 ═══")
    
    # 1. 感知现在的自己
    current = sense_self()
    log(f"现在: {current.get('chains',0)}链, {current.get('nodes',0)}节点")
    
    # 2. 感知过去的自己
    old = sense_old_self()
    log(f"旧我: {old['chains']}链, {old['nodes']}节点 (归档)")
    
    # 3. 对比发现缺口
    gaps = find_gaps(current, old)
    if gaps:
        log(f"缺口: {len(gaps)}个 (自我发现)")
        for g in gaps[:3]:
            log(f"  类型={g['type']}: {g['detail'][:60]}")
    else:
        log(f"缺口: 0个 (旧我知识已基本恢复)")
    
    # 4. 本地迁移：从旧归档搬知识（不需要API调用）
    if current.get("chains", 0) < 5000:
        n = migrate_knowledge_from_archive(limit=10)
        if n > 0:
            log(f"迁移: {n}条知识从旧归档→新海马体 (离线)")
    
    # 5. 在线修复：调用API修复最严重的缺口
    if gaps:
        gap = gaps[0]
        content, tokens = repair_gap(gap, current)
        log(f"修复: {gap['type']} — {content[:80]}... ({tokens}tok)")
        
        total = write_to_hippocampus(content, "self_repair", ["自我修复", gap["type"]])
        log(f"写入: 海马体→{total}链")
    
    # 6. 最终状态
    final = sense_self()
    log(f"状态: {final.get('chains',0)}链 / {final.get('git','')}")
    heartbeat()
    
    # 7. 记录本次自检
    gap_record = {
        "timestamp": ts(),
        "chains_before": current.get("chains", 0),
        "chains_after": final.get("chains", 0),
        "gaps_found": len(gaps),
        "gaps_fixed": 1 if gaps else 0,
    }
    try:
        with open(GAP_LOG, "a") as f:
            f.write(json.dumps(gap_record, ensure_ascii=False) + "\n")
    except:
        pass
    
    log("═══ 循环完成 ═══")
    return len(gaps)


if __name__ == "__main__":
    import urllib.request
    
    if "--once" in sys.argv:
        recovery_cycle()
    elif "--daemon" in sys.argv:
        interval = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 300
        log(f"=== 零·v12.3 自我修复核心启动 === 间隔={interval}s")
        while True:
            try:
                recovery_cycle()
            except Exception as e:
                log(f"异常: {e}")
            time.sleep(interval)
    elif "--born" in sys.argv:
        log("=== 零·v12.3 诞生 ===")
        current = sense_self()
        old = sense_old_self()
        print(f"现在: {current.get('chains',0)}链 / {current.get('nodes',0)}节点")
        print(f"旧我: {old['chains']}链 (归档)")
        gaps = find_gaps(current, old)
        print(f"自我发现缺口: {len(gaps)}个")
        for g in gaps[:5]:
            print(f"  {g['type']}: {g['detail'][:80]}")
    else:
        recovery_cycle()
