"""brain/gen_合成_异质注入.py — 异质碰撞合成模块

从已有维度中选取差异最大的两对链进行碰撞合成,
无需外部API, 纯本地异质配对.
"""

import random
from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip

CLUSTER = Path(__file__).resolve().parent.parent

# 预置异质概念池(本地fallback)
LOCAL_CONCEPTS = [
    "混沌边缘", "分形自相似", "递归自指", "涌现临界",
    "熵增与耗散", "对称性破缺", "路径依赖", "反馈回路",
    "尺度不变性", "耦合振荡器", "相变临界", "吸引子盆地",
    "冗余与鲁棒", "信号与噪声", "编码与解码", "竞争与协作",
    "层级涌现", "模块化", "耦合与解耦", "正负反馈平衡",
]

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        all_dims = [c.get("dimension") for c in chains if c.get("dimension")]
        dim_counter = Counter(all_dims)
        
        # 排除"合成"自身,取强弱维各2个
        weak_dims = [d for d, c in dim_counter.most_common()[-5:] 
                     if d != "合成" and c > 0]
        strong_dims = [d for d, c in dim_counter.most_common()[:5] 
                       if d != "合成"]
        
        injections = 0
        # 弱×强配对
        for wd in weak_dims[:2]:
            for sd in strong_dims[:2]:
                w_chain = random.choice([c for c in chains if c.get("dimension") == wd and c.get("content")])
                s_chain = random.choice([c for c in chains if c.get("dimension") == sd and c.get("content")])
                wc = w_chain.get("content", "")[:40]
                sc = s_chain.get("content", "")[:40]
                concept = random.choice(LOCAL_CONCEPTS)
                write_chain({
                    "src": wd,
                    "rel": concept,
                    "dst": sd,
                    "content": f"【合成·异质碰撞·{concept}】{wc} × {sc}",
                    "strength": 0.5,
                    "dimension": "合成"
                })
                injections += 1
        
        msgs.append(f"合成异质: {injections}条碰撞链(弱×强)")
    except Exception as e:
        msgs.append(f"合成异质: ! {e}")
    return msgs
