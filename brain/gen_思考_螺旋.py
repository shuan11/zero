"""brain/think_spiral.py — 思考螺旋脉冲模块

自问自答机制: 从海马体链中提取弱推理模式,
构造追问链注入思考维度, 激活链式推理.
"""

import json, random
from pathlib import Path
from brain.share import write_chain, read_hip

CLUSTER = Path(__file__).resolve().parent.parent
QUESTIONS = [
    "为什么会这样?",
    "这意味着什么?",
    "和什么有关?",
    "如果相反会怎样?",
    "有什么例外?",
    "更深一层是什么?",
    "这个链条的起点是什么?",
]

def pulse(cycle_num=0):
    msgs = []
    try:
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        think_chains = [c for c in chains if c.get("dimension") == "思考" and c.get("content")]
        if not think_chains:
            msgs.append("思考螺旋: 无思考链")
            return msgs
        # 取3条思考链进行追问螺旋
        samples = random.sample(think_chains, min(3, len(think_chains)))
        for i, sc in enumerate(samples):
            content = sc.get("content", "")[:40]
            q = QUESTIONS[i % len(QUESTIONS)]
            ans = f"对'{content}'追问'{q}'→自答: "
            # 从触类旁通找关联链作为"自答"
            related = [c for c in chains if c.get("dimension") == "触类旁通" 
                       and len(c.get("content","")) > 10]
            if related:
                r = random.choice(related)
                ans += r.get("content", "")[:40]
            else:
                ans += content
            write_chain({
                "src": "思考",
                "rel": q,
                "dst": "思考",
                "content": f"【思考螺旋】{ans}",
                "strength": 0.5,
                "dimension": "思考"
            })
            msgs.append(f"思考螺旋: {q}→已注入")
    except Exception as e:
        msgs.append(f"思考螺旋: ! {e}")
    return msgs
