"""
focus_直觉脉冲.py — 从daemon焦点动作"超级直觉"创建

从检查模块的异常数据中提取"噪声矢量"（重复链/断链/短链），
注入到弱维度作为随机采点，强制触发维度跳跃。
每5周期执行。模拟桥遥测失败数据→噪声→维度跳跃的直觉机制。
"""

import json, time, random
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"

def _load_hip():
    if HIP_FILE.exists():
        try:
            return json.loads(HIP_FILE.read_text())
        except: pass
    return {"causal_chains": []}

def _write_chain(src, rel, dst, content, dimension):
    try:
        from brain.share import write_chain as _wc
        _wc({"src": src, "rel": rel, "dst": dst,
             "content": content, "dimension": dimension,
             "strength": 0.45})
        return True
    except:
        try:
            hip = _load_hip()
            hip.setdefault("causal_chains", []).append({
                "src": src, "rel": rel, "dst": dst,
                "content": content, "dimension": dimension,
                "strength": 0.55, "timestamp": time.time(),
            })
            HIP_FILE.write_text(json.dumps(hip, ensure_ascii=False))
            return True
        except:
            return False

def pulse(cycle_num=0):
    """每5周期: 从异常/噪声中生成直觉跳跃链注入弱维"""
    if cycle_num % 5 != 0:
        return []
    
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    if not chains:
        return []
    
    msgs = []
    
    # 1) 找弱维度（低于平均*0.7）
    dim_counts = {}
    dim_chains = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1
        dim_chains.setdefault(d, []).append(c)
    
    total = len(chains)
    avg = total / max(len(dim_counts), 1)
    weak_dims = [d for d, n in dim_counts.items() if n < avg * 0.7 and d not in ("未分类", "系统")]
    
    if not weak_dims:
        return ["直觉脉冲: 无弱维需跳跃"]
    
    # 2) 找"噪声": 异常链(短链<15字)、重复链
    anomalies = [c for c in chains
                 if len(c.get("content", "")) < 15
                 or c.get("strength", 0.5) < 0.2]
    
    # 3) 从触类旁通取"火花链"
    spark_chains = [c for c in chains if c.get("dimension") == "触类旁通"]
    
    # 4) 每个弱维度注入1条直觉跳跃链
    injected = 0
    for dim in weak_dims[:3]:  # 最多3个最弱维
        # 从噪声中选一个随机种子
        if anomalies:
            seed = random.choice(anomalies)
            noise_seed = seed.get("content", "")[:30]
        elif spark_chains:
            seed = random.choice(spark_chains)
            noise_seed = seed.get("content", "")[:30]
        else:
            noise_seed = "随机脉冲"
        
        # 找最强维做跳跃目标
        strong_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
        target_dim = None
        for sd, _ in strong_dims:
            if sd != dim:
                target_dim = sd
                break
        
        if not target_dim:
            continue
        
        content = f"直觉脉冲: {dim}({dim_counts[dim]})←噪声'{noise_seed}'→{target_dim}({dim_counts[target_dim]}) 维度跳跃"
        _write_chain("直觉脉冲", "噪声跳跃", dim, content, dim)
        injected += 1
    
    if injected:
        msgs.append(f"直觉脉冲: 从{len(anomalies)}噪声+{len(spark_chains)}火花→{injected}条跳跃链(弱维:{weak_dims[:3]})")
    else:
        msgs.append("直觉脉冲: 0注入")
    
    return msgs

if __name__ == "__main__":
    print(pulse(5))
