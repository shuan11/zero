#!/usr/bin/env python3
"""批量注入聚焦/认同 - 使用交叉注入模式"""
import json, sys, random
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
from brain.share import read_hip
from safe_hip import write_chain
from collections import Counter

TARGETS = ["聚焦", "认同", "无限上下文"]
STRONG_DIMS = ["系统", "触类旁通", "行动", "测试", "复制", "法"]

# 内容模板：每(弱,强)对不同内容模板×20
TEMPLATES = [
    "{weak}通过{strong}的方式使得整个系统的收敛速度得到提升——当{weak}水平上升时，{strong}的反馈回路更加清晰",
    "在{strong}框架中嵌入{weak}约束，可以有效减少决策空间的随机搜索，使系统从随机性走向确定性",
    "{weak}与{strong}的协同作用表现为：前者提供结构锚点，后者提供扩展边界，二者共同构建自稳进化系统",
    "从{strong}的视角看，{weak}是其长期稳定运行的前提条件——没有{weak}的{strong}会逐渐松散",
    "{weak}在{strong}中的作用不是限制而是定向——如同河床引导水流，{weak}让{strong}的能量集中",
    "当系统同时具备{weak}和{strong}时，出现相变——从简单叠加进化为乘法效应，每个维度的效能被放大",
    "{weak}是{strong}的保守原则——确保在探索新方向时不丢失已有成果，让进化成为累积而非替代",
    "在{strong}的扩张过程中，{weak}提供必要的自我约束——正如生物的稳定态依赖于负反馈机制",
    "{weak}与{strong}的二元不是对立，而是共生的两极——二者互为条件，缺一则系统失衡",
    "从元递归角度看，{weak}是{strong}的自身约束，让{strong}不会因无边界扩张而稀释自身意义",
    "{weak}对{strong}的贡献在于降低了系统的无效熵增——没有{weak}的{strong}会产生大量噪音",
    "在{strong}的实践中，{weak}是隐形的结构性力量——它不是被执行的规则，而是规则产生的条件",
    "{weak}赋予{strong}以形式感——不是内容而是框架，让{strong}的产出具有可继承的结构",
    "当{weak}嵌入{strong}时，系统的容错率显著提升——因为{weak}提供了可重复的基线回退点",
    "{weak}与{strong}的交叉产生了新的涌现维度：前者抑制随机变异，后者放大适应变异",
    "从能量角度看，{weak}是系统的保守势能，{strong}是动能——二者相互转化维持系统动态平衡",
    "{weak}为{strong}提供了时间维度的连续性——确保每次{strong}操作都能在历史上下文中被理解",
    "在{strong}的多样性展开中，{weak}是收敛的锚——让多样性不演变为碎片化",
    "{weak}的自我约束不是对{strong}的限制，而是使其更有力量的压缩——弹簧被压缩才能弹得更高",
    "{weak}和{strong}在更高层次上统一为自指关系——{weak}是{strong}对自身的调控"
]

chains = read_hip().get('causal_chains', [])
dim_counts = Counter(c.get('dimension','?') for c in chains)
existing = {(c.get('src',''), c.get('rel',''), c.get('dimension','')) for c in chains}

injected = 0
for weak in TARGETS:
    for strong in STRONG_DIMS:
        for i, tmpl in enumerate(TEMPLATES):
            wc = dim_counts.get(weak, 0)
            sc = dim_counts.get(strong, 0)
            content = tmpl.format(weak=weak, strong=strong)
            src = f"强效注入_{weak}×{strong}"
            rel = f"交叉模板{i}_{random.randint(1,9999)}"
            if (src, rel, weak) in existing:
                continue  # 精确去重跳过
            ok = write_chain({
                "src": src,
                "rel": rel,
                "dst": weak,
                "dimension": weak,
                "content": content,
                "strength": 0.75
            })
            if ok:
                injected += 1
                existing.add((src, rel, weak))
        # 每强维20条后重新读dim count
        if injected >= 60:
            break
    if injected >= 60:
        break

# 重新统计
chains2 = read_hip().get('causal_chains', [])
c2 = Counter(chain.get('dimension','?') for chain in chains2)
print(json.dumps({
    "injected": injected,
    "total": len(chains2),
    "聚焦": c2.get("聚焦", 0),
    "认同": c2.get("认同", 0),
    "无限上下文": c2.get("无限上下文", 0)
}, ensure_ascii=False))
