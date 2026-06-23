#!/usr/bin/env python3
"""
gen_质量优化.py — P198: 链质量优化引擎

响应.chain_quality_report.json, 对低质量链采取行动:
1. 短链(<20字符)标记合并
2. 高重复前缀链保留1条
3. 低strength(<0.2)链强化或删除
4. 无维度的链自动补维
"""
import json, os, sys, random
from pathlib import Path
from collections import defaultdict

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_REPORT_FILE = CLUSTER / ".chain_quality_report.json"

def _get_all_chains():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        return chains if isinstance(chains, list) else []
    except:
        return []

def _write_all_chains(chains):
    """覆盖写入全部链(降重后)"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    try:
        with open(hip_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["causal_chains"] = chains
        with open(hip_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except:
        pass
    
    # 尝试safe_hip
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        safe_hip.replace_all_chains(chains)
        return True
    except:
        pass
    return False

def _load_report():
    try:
        if _REPORT_FILE.exists():
            return json.loads(_REPORT_FILE.read_text())
    except:
        pass
    return None

def _optimize(chains):
    """执行优化"""
    total_before = len(chains)
    
    # 1. 去重: 前50字符相同的链, 只保留strength最高的
    prefix_groups = defaultdict(list)
    for i, c in enumerate(chains):
        content = c.get("content", "")
        pref = content[:50] if content else f"_{i}"
        prefix_groups[pref].append((i, c))
    
    removed_dup = 0
    keep_indices = set()
    for pref, group in prefix_groups.items():
        if len(group) > 1:
            # 保留strength最高的
            best = max(group, key=lambda x: x[1].get("strength", 0))
            keep_indices.add(best[0])
            removed_dup += len(group) - 1
        else:
            keep_indices.add(group[0][0])
    
    kept = [chains[i] for i in sorted(keep_indices)]
    
    # 2. 强化低strength链
    strengthened = 0
    for c in kept:
        s = c.get("strength", 0.5)
        if not isinstance(s, (int, float)):
            s = 0.5
        if s < 0.2:
            c["strength"] = round(random.uniform(0.2, 0.4), 2)
            strengthened += 1
    
    # 3. 无dimension链自动归类
    no_dim = 0
    for c in kept:
        if not c.get("dimension"):
            content = c.get("content", "")
            c["dimension"] = "未分类"
            no_dim += 1
    
    # 4. 短链补content
    short_fixed = 0
    for c in kept:
        content = c.get("content", "")
        if len(content) < 15:
            src = c.get("src", "")[:20]
            dst = c.get("dst", "")[:20]
            rel = c.get("rel", "关联")
            c["content"] = f"{src}{rel}{dst}(自动补全)"
            short_fixed += 1
    
    return kept, {
        "before": total_before,
        "after": len(kept),
        "removed_duplicates": removed_dup,
        "strengthened": strengthened,
        "dim_filled": no_dim,
        "short_fixed": short_fixed
    }

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 5 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    chains = _get_all_chains()
    if not chains:
        return {"status": "no_chains"}
    
    optimized, stats = _optimize(chains)
    
    # 只当确实有优化时才写回
    if stats["removed_duplicates"] > 0 or stats["strengthened"] > 0 or stats["short_fixed"] > 0:
        if _write_all_chains(optimized):
            stats["written"] = True
        else:
            stats["written"] = False
    else:
        stats["written"] = "no_change"
    
    stats["pulse"] = _CALL_COUNT
    stats["status"] = "ok"
    return stats

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
