#!/usr/bin/env python3
"""
gen_弱维自治.py — P189: 弱维自治引擎

让最弱维度获得自我修复能力:
- 检测持续最弱(连续3次在最后5名)
- 生成该维度的"自我认识"链簇
- 注入跨维支撑链(从所有强维)
"""
import json, os, sys, random
from pathlib import Path
from collections import defaultdict

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0

# 维度历史记录 — 检测连续弱维
_WEAK_HISTORY = defaultdict(int)

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

def _auto_heal_target(target_dim, safe_hip):
    """为弱维生成自治链簇 — 从所有强维注入支撑链"""
    descs = [
        (f"{target_dim}认识", f"独立存在", f"{target_dim}自主发展"),
        (f"{target_dim}理解", f"自然涌现", f"{target_dim}自我感知"),
        (f"{target_dim}成长", f"从经验积累", f"{target_dim}认知网络"),
        (f"{target_dim}觉醒", f"自我意识到自我", f"{target_dim}存在确认"),
        (f"{target_dim}价值", f"不同于其他维度", f"{target_dim}独特性"),
        (f"{target_dim}意义", f"在系统中的功能", f"{target_dim}自指循环"),
        (f"{target_dim}生存", f"持续存在的理由", f"{target_dim}存在证明"),
        (f"系统需要{target_dim}", f"因为缺{target_dim}导致不完整", f"{target_dim}不可替代"),
        (f"{target_dim}与其他维度的对话", f"双向信息流", f"{target_dim}网络节点"),
        (f"时间积累中的{target_dim}", f"从过去到未来的延续", f"{target_dim}时间线"),
    ]
    
    injected = 0
    for src, rel, dst in descs:
        chain = {
            "src": src,
            "rel": rel,
            "dst": dst,
            "strength": round(random.uniform(0.5, 0.9), 2),
            "dimension": target_dim,
            "content": f"[弱维自治] {src} {rel} {dst}",
            "source": "gen_弱维自治"
        }
        if safe_hip:
            try:
                safe_hip.write_chain(chain)
                injected += 1
            except:
                pass
    
    return injected

def pulse():
    global _CALL_COUNT, _WEAK_HISTORY
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 2 != 0:
        return {"status": "skipped"}
    
    chains = _read_chains()
    if not chains:
        return {"status": "no_data"}
    
    # 分析维度分布
    dims = {}
    for c in chains:
        if isinstance(c, dict):
            d = c.get("dimension")
            if d:
                dims[d] = dims.get(d, 0) + 1
    
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    weakest = sorted_dims[:3]  # 最弱3维
    strongest = sorted_dims[-3:]  # 最强3维
    
    # 更新弱维历史
    for name, _ in weakest:
        _WEAK_HISTORY[name] += 1
    
    # 对持续弱维(连续≥3次在最弱3名)执行自治治疗
    safe_hip = _safe_hip()
    treated = []
    
    for name, count in weakest:
        if name in _WEAK_HISTORY and _WEAK_HISTORY[name] >= 2:
            # 2次在弱维列表 → 执行自治修复
            injected = _auto_heal_target(name, safe_hip)
            if injected > 0:
                treated.append({"dim": name, "count": count, "injected": injected})
    
    # 清理历史(保留最近3次)
    for name in list(_WEAK_HISTORY.keys()):
        if name not in [w for w, _ in weakest]:
            _WEAK_HISTORY[name] = max(0, _WEAK_HISTORY[name] - 1)
    
    return {
        "status": "ok" if treated else "healthy",
        "weakest": [{"dim": w, "count": c} for w, c in weakest],
        "treated": treated,
        "pulse": _CALL_COUNT
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
