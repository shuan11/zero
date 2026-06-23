#!/usr/bin/env python3
"""
gen_跨链关联.py — P187: 跨链关联引擎

在维度之间建立跨链关联关系:
- 扫描最近链, 发现共享关键词
- 在共享关键词的维度间建立关联链
- 增强维度间的语义网络
"""
import json, os, sys, random
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_LAST_RUN = 0

def _safe_hip():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def _read_chains():
    safe_hip = _safe_hip()
    if safe_hip:
        try:
            data = safe_hip.read_hip()
            chains = data.get("causal_chains", data.get("chains", []))
            return chains if isinstance(chains, list) else []
        except:
            pass
    
    hip_file = CLUSTER / "hippocampus_memory.json"
    if hip_file.exists():
        try:
            with open(hip_file) as f:
                data = json.load(f)
            chains = data.get("causal_chains", data.get("chains", []))
            return chains if isinstance(chains, list) else []
        except:
            pass
    return []

def _extract_keywords(content, max_kw=3):
    """从内容中提取关键词"""
    if not content or len(content) < 4:
        return []
    # 简单提取: 取长度适中的词语
    words = []
    for w in content.split():
        if 2 <= len(w) <= 6 and not w.isascii():
            words.append(w)
    return list(set(words))[:max_kw]

def _inject_association(src_dim, tgt_dim, keyword, safe_hip):
    """注入跨链关联"""
    chain = {
        "src": f"{src_dim}链",
        "rel": f"与{tgt_dim}通过'{keyword}'关联",
        "dst": f"{tgt_dim}链",
        "strength": round(random.uniform(0.3, 0.6), 2),
        "dimension": tgt_dim,
        "content": f"[跨链关联] {src_dim}与{tgt_dim}在'{keyword}'上语义关联",
        "source": "gen_跨链关联"
    }
    if safe_hip:
        try:
            safe_hip.write_chain(chain)
            return True
        except:
            pass
    return False

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 3 != 0:
        return {"status": "skipped"}
    
    chains = _read_chains()
    if not chains:
        return {"status": "no_chains"}
    
    # 按维度分组
    dim_chains = {}
    for c in chains:
        if not isinstance(c, dict):
            continue
        d = c.get("dimension")
        if not d:
            continue
        if d not in dim_chains:
            dim_chains[d] = []
        dim_chains[d].append(c.get("content", "") or "")
    
    # 取强维的前50条和弱维的前20条
    dims = {d: len(cc) for d, cc in dim_chains.items()}
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    
    strong = sorted_dims[:5]   # 强5维
    weak = sorted_dims[-5:]    # 弱5维
    
    # 提取强维关键词
    strong_kw = {}
    for sd, _ in strong:
        texts = dim_chains.get(sd, [])[:50]
        kws = Counter()
        for t in texts:
            for kw in _extract_keywords(t):
                kws[kw] += 1
        if kws:
            strong_kw[sd] = [w for w, _ in kws.most_common(5)]
    
    safe_hip = _safe_hip()
    pairs_done = 0
    
    # 跨强→弱关联
    for sd, _ in strong:
        kws = strong_kw.get(sd, [])
        if not kws:
            continue
        for wd, _ in weak:
            if sd == wd:
                continue
            kw = random.choice(kws)
            if _inject_association(sd, wd, kw, safe_hip):
                pairs_done += 1
                if pairs_done >= 8:
                    break
        if pairs_done >= 8:
            break
    
    # 弱→弱互相关联
    if pairs_done < 10:
        for i, (wd1, _) in enumerate(weak):
            for wd2, _ in weak[i+1:]:
                if _inject_association(wd1, wd2, "交叉", safe_hip):
                    pairs_done += 1
                    if pairs_done >= 10:
                        break
            if pairs_done >= 10:
                break
    
    return {"status": "ok", "pairs": pairs_done, "strong": [s for s,_ in strong], "weak": [w for w,_ in weak]}

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
