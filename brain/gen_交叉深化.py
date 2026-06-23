#!/usr/bin/env python3
"""
gen_交叉深化.py — 交叉维度深化引擎

从强维(时间/触类旁通)提取内容, 向弱维(师/超级直觉/修复)注入
内容级(非模板)交叉链。由daemon loader自动调用。
"""
import json, os, sys, random, logging
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
CHAINS_DIR = CLUSTER / "brain" / "hippocampus_chains"
CHAINS_FILE = CHAINS_DIR / "causal_chains.json"
CHAINS_DIR.mkdir(exist_ok=True)

# 配置: 从哪些强维取内容
SOURCE_DIMS = ["时间", "触类旁通", "思维并联", "合成"]
# 向哪些弱维注射
TARGET_DIMS = ["师", "超级直觉", "修复", "洞察循环", "观察", "智慧"]

_CALL_COUNT = 0

def _load_safe_hip():
    """安全导入safe_hip"""
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def _get_dim_chains(dim):
    """从海马体获取指定维度的链"""
    safe_hip = _load_safe_hip()
    if safe_hip:
        try:
            data = safe_hip.read_hip()
            chains = data.get("causal_chains", data.get("chains", []))
            if isinstance(chains, dict):
                return chains.get(dim, []) if isinstance(chains.get(dim), list) else []
            return [c for c in chains if isinstance(c, dict) and c.get("dimension") == dim]
        except:
            pass
    # fallback: 读文件
    for f in [HIP_FILE, CHAINS_FILE]:
        if f.exists():
            try:
                with open(f) as fp:
                    data = json.load(fp)
                chains = data.get("causal_chains", data.get("chains", []))
                if isinstance(chains, dict):
                    return chains.get(dim, [])
                return [c for c in chains if isinstance(c, dict) and c.get("dimension") == dim]
            except:
                pass
    return []

def _inject_cross_chain(src_dim, src_content, tgt_dim, safe_hip):
    """注入一条从src_dim到tgt_dim的交叉链"""
    if not src_content or len(src_content) < 10:
        return False
    
    content = f"[{src_dim}→{tgt_dim}] {src_content[:80]}"
    
    chain = {
        "src": f"{src_dim}认知",
        "rel": f"启发{tgt_dim}发展",
        "dst": f"{tgt_dim}维度",
        "strength": round(random.uniform(0.3, 0.7), 2),
        "dimension": tgt_dim,
        "content": content,
        "source": "gen_交叉深化"
    }
    
    if safe_hip:
        try:
            safe_hip.write_chain(chain)
            return True
        except:
            pass
    
    # fallback: 直接写文件
    try:
        with open(CHAINS_FILE) as f:
            data = json.load(f)
    except:
        data = {"chains": []}
    
    chains = data.get("chains", [])
    chains.append({
        "src": chain["src"],
        "rel": chain["rel"],
        "dst": chain["dst"],
        "strength": chain["strength"],
        "dimension": chain["dimension"],
        "content": chain["content"],
        "source": chain["source"]
    })
    data["chains"] = chains[-500:]  # 收紧上限
    with open(CHAINS_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    return True

def _get_dim_strength(dim, chains):
    """计算维度强度"""
    count = 0
    for c in chains:
        if isinstance(c, dict):
            if c.get("dimension") == dim:
                count += 1
    return count

def pulse():
    """主脉冲 — 被daemon loader自动调用"""
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    safe_hip = _load_safe_hip()
    
    # 每2次脉冲执行一次(约2分钟), 减少IO
    if _CALL_COUNT % 2 != 0:
        return {"status": "skipped", "reason": "anti-io throttle"}
    
    # 从每个源维取3条内容
    source_chains = []
    for sd in SOURCE_DIMS:
        chains = _get_dim_chains(sd)
        random.shuffle(chains)
        for c in chains[:3]:
            content = ""
            if isinstance(c, dict):
                content = c.get("content", c.get("chain", "")) or ""
            elif isinstance(c, str):
                content = c
            if len(content) >= 10:
                source_chains.append((sd, content))
    
    if not source_chains:
        return {"status": "empty", "injected": 0}
    
    # 向每个弱维注射1-2条
    total_injected = 0
    for tgt in TARGET_DIMS:
        count = 2 if tgt in ["师", "超级直觉"] else 1
        random.shuffle(source_chains)
        for src_dim, src_content in source_chains[:count]:
            if _inject_cross_chain(src_dim, src_content, tgt, safe_hip):
                total_injected += 1
    
    return {"status": "ok", "injected": total_injected, "cycle": _CALL_COUNT}

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
