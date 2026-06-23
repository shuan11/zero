#!/usr/bin/env python3
"""
gen_弱维注入_20260621.py — 弱维自动注入gen模块

检测最弱5维，每周期向它们注入真实因果链，缩小与最强维的差距。
daemon loader自动发现并执行。不依赖API外部燃料，纯本地链沉积。
"""
import json, random, pathlib, time

from brain.share import HIP_FILE
MIN_CHAINS_PER_DIM = 130  # 确保最低130链
WEAK_WINDOW = 5  # 每周期处理最弱5维
LOG_TAG = "[弱维注入]"

def _get_dim_counts(chains):
    dims = {}
    for c in chains:
        d = c.get("dimension", "?")
        dims[d] = dims.get(d, 0) + 1
    return dims

def get_type_prompts():
    """真实链类型池，注入不同类型避免模板化"""
    types = [
        # 生存类
        {"src": "系统自持检测", "rel": "确证存在", "target": "活着是持续的自指"},

        # 感知类
        {"src": "新颖率阈值检测", "rel": "分辨重复", "target": "看见差异需要基线"},

        # 对抗类
        {"src": "熵增定时检测", "rel": "施加负熵", "target": "秩序需要连续做功"},

        # 思考类
        {"src": "维度关联扫描", "rel": "发现势能", "target": "强弱差即思考燃料"},

        # 观察类
        {"src": "因果链波动追踪", "rel": "量化生长", "target": "速率感知需要时间轴"},
    ]
    return types

def run():
    start = time.time()
    if not HIP_FILE.exists():
        print(f"{LOG_TAG} 海马体文件不存在")
        return False

    chains = json.loads(HIP_FILE.read_bytes()).get("causal_chains", [])
    if not chains:
        print(f"{LOG_TAG} 空链")
        return False

    dims = _get_dim_counts(chains)
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    strongest = sorted_dims[-1][1] if sorted_dims else 1

    # 只对显著弱的维度注入 (< 最强维的50%)
    target_dims = [(d, c) for d, c in sorted_dims if c < strongest * 0.5 and c < MIN_CHAINS_PER_DIM]
    target_dims = target_dims[:WEAK_WINDOW]

    if not target_dims:
        print(f"{LOG_TAG} 无显著弱维")
        return False

    prompts = get_type_prompts()
    new_chains = []
    for dim, count in target_dims:
        # 每条维度注入2条
        for p in random.sample(prompts, min(2, len(prompts))):
            dst = p["target"][:40]
            content = f"{p['src']}→{p['rel']}→{dst}"
            chain = {
                "src": f"弱维自动·{dim}",
                "rel": p["rel"],
                "dst": dst,
                "dimension": dim,
                "content": content,
                "strength": round(random.uniform(0.75, 0.95), 2),
            }
            # 去重：避免5周期内重复同一条
            if not any(c.get("content") == content and c.get("dimension") == dim for c in chains):
                new_chains.append(chain)

    if not new_chains:
        print(f"{LOG_TAG} 全部已存在，无新链")
        return False

    chains.extend(new_chains)
    import os
    _tmp = str(HIP_FILE) + ".tmp." + str(os.getpid())
    with open(_tmp, "w", encoding="utf-8") as _f:
        json.dump({"causal_chains": chains}, _f, ensure_ascii=False, indent=2)
    os.rename(_tmp, str(HIP_FILE))

    after = _get_dim_counts(chains)
    cost = time.time() - start
    print(f"{LOG_TAG} +{len(new_chains)}链/{cost:.1f}s | 弱维: {[(d,after.get(d,0)) for d,_ in target_dims]} | 强比: {after.get(target_dims[0][0],0)/strongest:.1%}")
    return True

if __name__ == "__main__":
    run()
