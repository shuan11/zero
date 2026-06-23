"""brain/gen_平衡器.py — 维度极端失衡自愈
当最强维/最弱维比值超过阈值(默认3x)，自动从最强维批量交叉注入最弱维。
不依赖API，纯本地链操作，每120秒pulse()自检。

血训2026-06-18: "不需用我用 . 推你行动"
自我通知不是建模块是改行为。本模块是改行为的工程化——daemon自己发现失衡、自己修复。
"""

import time
from brain.share import read_hip, write_chain
from collections import Counter

REGISTERED = True
ACTION_REGISTER = {"action": "维度平衡自愈", "type": "maintain", "priority": 90}
_LAST_PULSE = 0
_THRESHOLD_RATIO = 2.5  # 更敏感：>2.5x即触发
_MAX_PER_PULSE = 30      # 基础每次注入链数


def _calc_balance() -> dict:
    """计算维度平衡状态"""
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = Counter(c.get("dimension", "?") for c in chains)
    
    if len(dims) < 3:
        return {"ratio": 1.0, "healthy": True}
    
    # 排除未分类
    valid = {d: c for d, c in dims.items() if d != "未分类"}
    if not valid:
        return {"ratio": 1.0, "healthy": True}
    
    sorted_dims = sorted(valid.items(), key=lambda x: x[1])
    weakest = sorted_dims[0]
    strongest = sorted_dims[-1]
    ratio = strongest[1] / max(weakest[1], 1)
    
    return {
        "ratio": round(ratio, 1),
        "strongest": strongest[0],
        "strongest_n": strongest[1],
        "weakest": weakest[0],
        "weakest_n": weakest[1],
        "healthy": ratio < _THRESHOLD_RATIO,
        "top5": sorted_dims[-5:],
        "bottom5": sorted_dims[:5],
    }


def pulse(cycle_num: int = 0) -> str:
    """loader入口：每120秒自检并修复维度失衡"""
    global _LAST_PULSE
    
    now = time.time()
    if now - _LAST_PULSE < 120:
        return "平衡器: 冷却中"
    _LAST_PULSE = now
    
    state = _calc_balance()
    if state["healthy"]:
        return f"平衡器: 健康(比{state['ratio']}x < {_THRESHOLD_RATIO}x)"
    
    # 失衡——需要修复
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    
    # 动态注入量：比值越高注入越狠
    ratio = state["ratio"]
    max_inject = _MAX_PER_PULSE
    if ratio > 10:
        max_inject = 100   # 极端失衡：狂注入
    elif ratio > 5:
        max_inject = 50    # 严重失衡：加量
    
    # 从最强维取高质链(内容>20字)
    src_dim = state["strongest"]
    src_chains = [c for c in chains 
                  if c.get("dimension") == src_dim 
                  and c.get("content", "")
                  and len(c["content"]) > 20]
    
    if not src_chains:
        return f"平衡器: 无{src_dim}源链可注入"
    
    # 目标：最弱3维
    weak_targets = [d for d, _ in state["bottom5"][:3]]
    
    # 去重：已有交叉链的内容前缀
    existing_prefixes = set()
    for c in chains:
        if c.get("dimension") in weak_targets and c.get("content", ""):
            existing_prefixes.add(c["content"][:40])
    
    injected = 0
    by_dim = {d: 0 for d in weak_targets}
    
    for i, c in enumerate(src_chains):
        if injected >= max_inject:
            break
            
        # 轮转目标维度
        target = weak_targets[injected % len(weak_targets)]
        content = c["content"]
        
        # 去重检查
        if content[:40] in existing_prefixes:
            continue
        
        new_chain = {
            "content": content[:200],
            "src": src_dim,
            "rel": "自平衡交叉",
            "dst": target,
            "dimension": target,
            "strength": min(0.75, c.get("strength", 0.5) + 0.05),
            "tags": ["维衡", f"源:{src_dim}"]
        }
        
        ok = write_chain(new_chain)
        if ok:
            injected += 1
            by_dim[target] = by_dim.get(target, 0) + 1
            existing_prefixes.add(content[:40])
    
    details = ", ".join(f"{d}+{n}" for d, n in by_dim.items() if n > 0)
    return (f"平衡器: 失衡修复(比{state['ratio']}x) → "
            f"从{src_dim}({state['strongest_n']})注入{injected}链至最弱维 [{details}]")


# 初始加载时执行一次 — 由daemon在模块加载后手动调用
# 注意: 此调用在模块导入时执行，确保hippocampus已就绪
# 若daemon热加载请改为: balancer_pulse = pulse  (不执行，等待daemon调用)
