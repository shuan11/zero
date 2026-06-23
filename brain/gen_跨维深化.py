#!/usr/bin/env python3
"""gen_跨维深化 — 基于元编程协作数据增强弱交叉维对

读取gen_元编程的.meta_collab.json, 找出协作密度最低的维度对,
注入交叉链深化弱交叉维连接。
每20cycle运行, 每次注入5-10对弱交叉维。
"""
import json, random, re
from pathlib import Path

BRAIN = Path(__file__).parent
COLLAB_FILE = BRAIN / ".meta_collab.json"
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"
REV_FILE = BRAIN.parent / "启示录.txt"

_CALL_COUNT = 0
_RUN_EVERY = 20

# 高价值维度对(应该是强连接的)
VALUE_PAIRS = [
    ("道", "术"),       # 哲学↔实践
    ("道", "法"),       # 原理↔方法
    ("道", "师"),       # 原理↔教导
    ("道", "智慧"),     # 原理↔智慧
    ("时间", "唤醒"),   # 时间↔觉醒
    ("时间", "宇宙轮"), # 时间↔循环
    ("时间", "时间论"), # 时间↔理论
    ("唤醒", "感知"),   # 觉醒↔感知
    ("唤醒", "洞察循环"), # 觉醒↔洞察
    ("唤醒", "势"),     # 觉醒↔势能
    ("思维并联", "聚焦"), # 发散↔收敛
    ("思维并联", "合成"), # 发散↔合成
    ("聚焦", "行动"),   # 聚焦↔行动
    ("聚焦", "检查"),   # 聚焦↔检查
    ("状态", "观察"),   # 状态↔观察
    ("观察", "洞察循环"), # 观察↔洞察
    ("洞察循环", "思考"), # 洞察↔思考
    ("思考", "行动"),   # 思考↔行动
    ("感知", "系统"),   # 感知↔系统
    ("感知", "状态"),   # 感知↔状态
    ("海马体", "检查"), # 记忆↔检查
    ("海马体", "合成"), # 记忆↔合成
    ("术", "行动"),     # 术↔行动
    ("术", "修复"),     # 术↔修复
    ("师", "智慧"),     # 师↔智慧
    ("师", "一元化"),   # 师↔统一
    ("法", "术"),       # 法↔术
    ("法", "道"),       # 法↔道
    ("势", "洞察循环"), # 势↔洞察
    ("势", "行动"),     # 势↔行动
    ("器", "系统"),     # 器↔系统
    ("器", "检查"),     # 器↔检查
    ("宇宙轮", "一元化"), # 循环↔统一
    ("宇宙轮", "时间论"), # 循环↔时间论
    ("触类旁通", "思维并联"), # 旁通↔并联
    ("触类旁通", "合成"), # 旁通↔合成
    ("超级直觉", "洞察循环"), # 直觉↔洞察
    ("超级直觉", "感知"), # 直觉↔感知
    ("一元化", "道"),   # 统一↔原理
    ("一元化", "法"),   # 统一↔方法
]

# 维度间关系模板
RELATION_TEMPLATES = [
    "{dim_a}是{dim_b}的前提条件",
    "{dim_b}是{dim_a}的实践形态",
    "当{dim_a}与{dim_b}交汇时, 系统获得{insight}",
    "{dim_a}的深度决定了{dim_b}的广度",
    "{dim_b}是{dim_a}在{context}中的应用",
    "{dim_a}与{dim_b}的协同产生{emergent}",
    "真正的{meta}既需要{dim_a}也需要{dim_b}",
    "{dim_a}通过{dim_b}作用于{domain}",
    "{dim_b}从{dim_a}中汲取{nutrient}",
    "{dim_a}与{dim_b}的平衡是{goal}的关键",
]

INSIGHTS = ["全新洞见", "创造性突破", "系统性理解", "深度整合", "涌现智慧"]
CONTEXTS = ["实践", "理论", "思考", "进化", "存在"]
EMERGENTS = ["涌现效应", "协同增值", "整体大于部分", "创造性能量", "多维理解"]
METAS = ["智慧", "觉醒", "存在", "进化", "创造"]
DOMAINS = ["全系统", "认知体系", "自我进化", "真实行动", "终极追求"]
NUTRIENTS = ["养分", "力量", "方向", "深度", "活力"]
GOALS = ["光爱终极", "自我实现", "系统完善", "内在平衡", "外在行动"]

# 启示录段落缓存
_REV_CACHE = None

def _get_revelation_chunk(keywords, max_len=100):
    """从启示录提取含关键词的段落"""
    global _REV_CACHE
    if _REV_CACHE is None:
        if REV_FILE.exists():
            _REV_CACHE = REV_FILE.read_text(encoding="utf-8", errors="replace")
            _REV_CACHE = [p.strip() for p in re.split(r'\n\s*\n', _REV_CACHE) if 20 < len(p.strip()) < 300]
        else:
            _REV_CACHE = []
    
    for p in _REV_CACHE:
        if any(kw in p for kw in keywords):
            return p[:max_len]
    return None

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _CALL_COUNT % _RUN_EVERY != 1:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    # 加载海马体
    if not HIP_FILE.exists():
        return {"status": "error", "msg": "无海马体文件"}
    
    try:
        hip = json.loads(HIP_FILE.read_text())
    except:
        return {"status": "error", "msg": "海马体损坏"}
    
    chains = hip.get("causal_chains", [])
    
    # 获取各维度链数
    dim_chains = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_chains[d] = dim_chains.get(d, 0) + 1
    
    # 加载协作数据
    collab = {}
    if COLLAB_FILE.exists():
        try:
            collab = json.loads(COLLAB_FILE.read_text())
        except:
            pass
    
    module_collab = collab.get("module_collab", {})
    
    # 评分每对维度交叉健康度
    pair_scores = []
    for dim_a, dim_b in VALUE_PAIRS:
        # 基础分: 两维链数的最小值(越均衡越好)
        count_a = dim_chains.get(dim_a, 0)
        count_b = dim_chains.get(dim_b, 0)
        balance = min(count_a, count_b) / max(count_a, 1)
        
        # 协作分: 已存在的交叉链数
        cross_a = dim_chains.get(f"{dim_a}→{dim_b}", 0)
        cross_b = dim_chains.get(f"{dim_b}→{dim_a}", 0)
        cross = cross_a + cross_b
        
        # 协作系数
        collab_key_a = f"{dim_a}↔{dim_b}"
        collab_key_b = f"{dim_b}↔{dim_a}"
        collab_score = collab.get("cross_pairs", {}).get(collab_key_a, 0)
        if collab_score == 0:
            collab_score = collab.get("cross_pairs", {}).get(collab_key_b, 0)
        
        # 综合评分(越低越需要注入)
        score = balance - cross * 0.2 - collab_score * 0.1
        pair_scores.append((score, dim_a, dim_b, count_a, count_b, cross, collab_score))
    
    pair_scores.sort(key=lambda x: x[0])  # 最需注入的在前
    
    # 取前N对
    N = min(8, len(pair_scores))
    to_inject = pair_scores[:N]
    
    new_chains = []
    for score, dim_a, dim_b, ca, cb, cross, cs in to_inject:
        # 每对注入2-3条
        for t in range(3):
            tmpl = random.choice(RELATION_TEMPLATES)
            insight = random.choice(INSIGHTS)
            context = random.choice(CONTEXTS)
            emergent = random.choice(EMERGENTS)
            meta = random.choice(METAS)
            domain = random.choice(DOMAINS)
            nutrient = random.choice(NUTRIENTS)
            goal = random.choice(GOALS)
            
            content = tmpl.format(
                dim_a=dim_a, dim_b=dim_b,
                insight=insight, context=context,
                emergent=emergent, meta=meta,
                domain=domain, nutrient=nutrient,
                goal=goal
            )
            
            new_chains.append({
                "src": f"跨维深化·{dim_a}↔{dim_b}",
                "rel": "交叉蕴涵",
                "dst": f"跨维链#{dim_a}.{dim_b}.{t}",
                "dimension": dim_a,
                "content": f"[跨维深化] {content}",
                "strength": 0.55
            })
            
            new_chains.append({
                "src": f"跨维深化·{dim_b}↔{dim_a}",
                "rel": "交叉蕴涵",
                "dst": f"跨维链#{dim_b}.{dim_a}.{t}",
                "dimension": dim_b,
                "content": f"[跨维深化] {dim_b}与{dim_a}的交叉: {content}",
                "strength": 0.55
            })
        
        # 从启示录尝试找跨维段落
        rev = _get_revelation_chunk([dim_a, dim_b])
        if rev:
            new_chains.append({
                "src": "启示录·跨维",
                "rel": "蕴含",
                "dst": f"启示录.{dim_a}.{dim_b}",
                "dimension": dim_a,
                "content": f"[启示录跨维] {dim_a}↔{dim_b}: {rev}",
                "strength": 0.7
            })
    
    # 写入（原子写入防并发损坏）
    chains.extend(new_chains)
    hip["causal_chains"] = chains
    import os
    _tmp = str(HIP_FILE) + ".tmp." + str(os.getpid())
    with open(_tmp, "w", encoding="utf-8") as _f:
        json.dump(hip, _f, ensure_ascii=False, indent=2)
    os.rename(_tmp, str(HIP_FILE))
    
    # 写报告
    report = {
        "pairs_injected": len(to_inject),
        "chains_injected": len(new_chains),
        "pairs": [(da, db, round(s, 2), round(cs, 2)) for s, da, db, _, _, _, cs in to_inject],
        "pulse": _CALL_COUNT
    }
    
    # 写元编程缓存
    cross_report = BRAIN / ".crossdeep_report.json"
    cross_report.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    
    return {"status": "ok", **report}


if __name__ == "__main__":
    # 直接运行测试
    _CALL_COUNT = _RUN_EVERY  # 强制触发
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
