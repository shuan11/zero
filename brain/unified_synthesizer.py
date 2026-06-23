"""
一元化合成器 — 从各维度精选高质量链，桥对齐过滤，合并注入
Daemon gen file 动作→真实工程: 创建一元化合成器
"""

import json
from pathlib import Path
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"
MIN_CHAINS_PER_DIM = 5
ALIGN_THRESHOLD = 0.9  # 桥对齐度阈值

def _load_hip():
    """加载海马体"""
    if HIP_FILE.exists():
        try:
            return json.loads(HIP_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"causal_chains": []}

def _save_hip(data):
    """安全写回海马体"""
    try:
        HIP_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except:
        return False

def pulse(cycle_num=None):
    """主入口: 从各维度精选高质量链，合成注入"""
    if cycle_num and cycle_num % 10 != 0:
        return None  # 每10周期执行一次
    
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    
    # 按维度分组
    dim_groups = defaultdict(list)
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_groups[d].append(c)
    
    # 每个维度取前高质量链（长内容+高强度=高质量）
    selected = []
    for dim, dim_chains in dim_groups.items():
        if dim == "未分类":
            continue
        sorted_chains = sorted(
            dim_chains,
            key=lambda c: len(c.get("content", "")) * (c.get("strength", 0.5) or 0.5),
            reverse=True
        )
        selected.extend(sorted_chains[:MIN_CHAINS_PER_DIM])
    
    # 过滤: 桥对齐度>0.9
    aligned = [c for c in selected if c.get("strength", 0) >= ALIGN_THRESHOLD]
    if not aligned:
        aligned = selected[:5]  # 降级: 选前5条
    if not aligned:
        return None
    
    # 合并: 从每个维度选1条，交叉合成
    new_chains = []
    dim_order = [c.get("dimension") for c in aligned[:5]]
    for i in range(min(10, len(aligned))):
        c = aligned[i]
        src = c.get("src", "未知")
        dst = c.get("dst", "未知")
        content = c.get("content", "")
        dim = c.get("dimension", "一元化")
        
        new_chain = {
            "src": f"一元化合成",
            "rel": f"{src}↔{dst}",
            "dst": f"一元化·{dim}",
            "content": f"一元化合成: [{dim}] {content[:60]}... (桥对齐)",
            "dimension": "一元化",
            "strength": 0.7,
            "tags": ["一元化", "合成", dim],
            "timestamp": __import__("time").time()
        }
        new_chains.append(new_chain)
    
    # 去重后注入
    existing_keys = {(c.get("src",""), c.get("rel",""), c.get("dst","")) for c in chains}
    added = 0
    for nc in new_chains:
        key = (nc["src"], nc["rel"], nc["dst"])
        if key not in existing_keys:
            chains.append(nc)
            existing_keys.add(key)
            added += 1
    
    hip["causal_chains"] = chains
    if _save_hip(hip):
        return f"[一元化合成] 注入{added}条一元化链 (从{len(dim_groups)}维精选{len(selected)}条过滤)"
    return None

if __name__ == "__main__":
    r = pulse(10)
    print(r)
