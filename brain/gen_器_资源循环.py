"""
gen_器_资源循环.py — 器维度资源循环因果模块

原料→工具→产品 闭环链路自动生成器维度强因果链。
每周期检测缺链方向，生成反向因果链强化闭环。
"""

from brain.share import write_chain, read_hip, log
from brain.engineer_器 import get_dim_stats
import random

RESOURCE_CYCLES = [
    ("菌菌", "编译", "洞察"),
    ("洞察", "抽象", "规则"),
    ("规则", "编码", "模块"),
    ("模块", "集成", "系统"),
    ("系统", "运行", "数据"),
    ("数据", "分析", "知识"),
    ("知识", "蒸馏", "智慧"),
    ("智慧", "反哺", "菌菌"),
]

def pulse(cycle_num=0):
    """每6周期: 生成资源循环链"""
    msgs = []
    try:
        chains, dims, _ = get_dim_stats()
        # 找最稀疏维度作为产品
        sorted_d = sorted(dims.items(), key=lambda x: x[1])
        weakest = sorted_d[0][0] if sorted_d else "器"
        strongest = sorted_d[-1][0] if sorted_d else "器"
        # 选一个循环方向
        cycle = random.choice(RESOURCE_CYCLES)
        raw, tool, product = cycle
        # 写因果链
        write_chain({
            "src": raw,
            "rel": "工具化",
            "dst": tool,
            "content": f"【器·资源循环】{raw}→{tool}: {raw}通过{tool}处理转化为{product}, 强化{weakest}维度",
            "strength": 0.7,
            "dimension": "器"
        })
        write_chain({
            "src": tool,
            "rel": "产出",
            "dst": product,
            "content": f"【器·资源循环】{tool}→{product}: {tool}产出{product}, 对齐{weakest}维需求",
            "strength": 0.6,
            "dimension": "器"
        })
        write_chain({
            "src": product,
            "rel": "反哺",
            "dst": raw,
            "content": f"【器·资源循环】{product}→{raw}: {product}反哺{raw}, 闭环完成. 当前最弱维={weakest}({dims.get(weakest,0)}链)",
            "strength": 0.5,
            "dimension": "器"
        })
        msgs.append(f"资源循环: {raw}→{tool}→{product} | 最弱={weakest}")
    except Exception as e:
        msgs.append(f"资源循环: ! {e}")
    return msgs
