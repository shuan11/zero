"""brain/gen_时间_自举.py — 时间维自举注入

时间维度当前仅4链(164x比值), 需紧急自举至基线水平。
从感知/状态/触类旁通提取时序相关内容注入时间维。
"""

from pathlib import Path
from collections import Counter
from brain.share import write_chain, read_hip

CLUSTER = Path(__file__).resolve().parent.parent

TIME_TEMPLATES = [
    "时间尺度上的{concept}构成持续演化路径",
    "{concept}在时间轴上的展开揭示深层结构",
    "跨时间段的{concept}呈现递归自相似性",
    "时序积累中的{concept}产生质变临界",
    "{concept}的时间维度映射显示非线性特征",
]

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        
        # 从感知/状态/触类旁通/洞察循环提取内容
        src_dims = ["感知", "状态", "触类旁通", "洞察循环"]
        sources = []
        for sd in src_dims:
            candidates = [c for c in chains if c.get("dimension") == sd
                         and len(c.get("content","")) > 10]
            sources.extend(candidates[:3])
        
        if not sources:
            msgs.append("时间自举: 无源链")
            return msgs
        
        import random
        injected = 0
        for s in sources:
            content = s.get("content","")[:30]
            if not content:
                continue
            template = random.choice(TIME_TEMPLATES)
            mapped = template.format(concept=content)
            write_chain({
                "src": s.get("dimension","?"),
                "rel": "时间映射",
                "dst": "时间",
                "content": f"【时间自举】{mapped}",
                "strength": 0.45,
                "dimension": "时间"
            })
            injected += 1
            
        msgs.append(f"时间自举: {injected}条注入")
    except Exception as e:
        msgs.append(f"时间自举: ! {e}")
    return msgs
