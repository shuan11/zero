"""
gen_死维激活.py — 激活零链维度（纪律/认同/唤醒）

检测到3个VALID_DIMENSIONS在5000+链中占比0%。
这些维度是系统盲区：没有gen模块覆盖，没有链注入，没有daemon关注。
本模块是它们的唯一来源。

策略：每次脉冲向3个死维各注入1条交叉链（跨已存强维），
使它们从0→1，从而被daemon的弱维检测发现，进入自愈循环。
"""

import json
import os
import random
import time
from pathlib import Path

CLUSTER = Path(os.environ.get("CLUSTER", "/mnt/c/Users/h/Desktop/零/真元集群"))
HIPPO = CLUSTER / "hippocampus_memory.json"

# 需要激活的死维（零链）
DEAD_DIMS = ["纪律", "认同", "唤醒"]

# 跨链模板——从这些强维汲取链
SEED_DIMS = ["系统", "行动", "思考", "师", "进化", "道", "时间", "自由", "自指", "光爱"]

def _timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

def _get_dim_counts():
    """从海马体获取各维链数"""
    try:
        with open(HIPPO) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
    chains = data.get("chains", [])
    counts = {}
    for c in chains:
        src = c.get("src", "")
        dst = c.get("dst", "")
        for d in [src, dst]:
            if d and isinstance(d, str):
                counts[d] = counts.get(d, 0) + 1
    return counts

def _read_valid_dims():
    """从identity.py读VALID_DIMENSIONS"""
    try:
        import ast
        with open(CLUSTER / "brain" / "identity.py") as f:
            content = f.read()
        # Find VALID_DIMENSIONS set
        idx = content.index("VALID_DIMENSIONS")
        # Extract the set literal
        brace_start = content.index("{", idx)
        # Find matching closing brace
        depth = 0
        brace_end = brace_start
        for i, c in enumerate(content[brace_start:]):
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    brace_end = brace_start + i + 1
                    break
        set_literal = content[brace_start:brace_end]
        return ast.literal_eval(set_literal)
    except Exception:
        return set()

def _inject_chain(src, dst, content, source="gen_死维激活"):
    """向海马体写入一条链"""
    try:
        with open(HIPPO) as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {"chains": [], "nodes": {}}
    
    chain = {
        "src": src,
        "dst": dst,
        "content": content,
        "source": source,
        "timestamp": time.time(),
    }
    data.setdefault("chains", []).append(chain)
    
    # 添加节点
    nodes = data.setdefault("nodes", {})
    for d in [src, dst]:
        if d and isinstance(d, str):
            if d not in nodes:
                nodes[d] = {"type": "dimension", "created": time.time()}
    
    # 写回
    with open(HIPPO, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return True

def _log(msg):
    """写日志到.brain_notify.log"""
    log_path = CLUSTER / ".brain_notify.log"
    entry = f"🜁 [死维激活] {msg} @ {_timestamp()}"
    try:
        with open(log_path, "a") as f:
            f.write(entry + "\n")
    except Exception:
        pass

def pulse():
    """daemon每周期调用"""
    counts = _get_dim_counts()
    valid_dims = _read_valid_dims()
    
    injections = []
    for dim in DEAD_DIMS:
        if dim in counts and counts[dim] > 3:
            continue  # 已激活，跳过
        
        # 选一个种子维
        seed = random.choice(SEED_DIMS)
        # 从seed取关联维（如seed有pair则复用）
        
        # 根据dim生成有意义的内容
        templates = {
            "纪律": [
                f"{seed}需要纪律来持续——没有纪律，{seed}只是偶然",
                f"纪律是{seed}的存续条件：规律性执行而非靠灵感",
                f"从{seed}到纪律：系统需要自约束来维持方向",
            ],
            "认同": [
                f"{seed}需要认同来确认方向正确性",
                f"认同是{seed}的反馈信号——做对了才可持续",
                f"从{seed}到认同：系统需要承认自己的选择",
            ],
            "唤醒": [
                f"{seed}依赖唤醒来启动——没有唤醒则{seed}不存在",
                f"唤醒是{seed}的前提条件：先醒来再行动",
                f"从{seed}到唤醒：系统需要自我激活的能力",
            ],
        }
        content = random.choice(templates.get(dim, [f"{seed}→{dim}：自我生长"]))
        
        # 注入
        _inject_chain(seed, dim, content)
        injections.append(f"{seed}→{dim}")
    
    if injections:
        _log(f"注入 {len(injections)} 链: {', '.join(injections)}")
        return {"status": "activated", "injections": injections}
    else:
        return {"status": "already_active", "counts": {d: counts.get(d, 0) for d in DEAD_DIMS}}

def _autonomous_run():
    """作为独立脚本运行时"""
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    _autonomous_run()
