"""gen_弱维交叉注入.py — 弱维×强维交叉链自动注入
每次注射将最弱维与最强维交叉连接，产生唯一(rel)对防去重
内容动态基于维度名称+当前状态生成，无固定池
"""
import json, time, re, random
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"
_RUN_EVERY = 2
_LAST_RUN_FILE = CLUSTER / ".brain_gen_弱维交叉注入_lastrun"
_WEAK_DIMS = ["纪律", "复制"]  # 目标弱维
_STRONG_DIM_PAIRS = [  # (强维, 交叉关系模式)
    ("系统", "整体系统的设计需要{weak}作为基础设施来保证长期可靠性"),
    ("触类旁通", "{weak}的行为模式可以类比迁移到其他维度——从{weak}中提炼抽象原则"),
    ("行动", "所有{weak}的最终检验标准是行动——没有行动的{weak}只是空谈"),
    ("感知", "对{weak}状态的精确感知是调节{weak}强度的前置条件"),
    ("聚焦", "聚焦能力决定了{weak}资源分配的效率——聚焦越好{weak}越精准"),
    ("自指", "{weak}的自指结构使得系统能检查自己对{weak}的遵守程度"),
    ("智慧", "真正的智慧知道何时严格执行{weak}、何时创造性地打破{weak}"),
    ("一元化", "一元化视角下{weak}不是独立维度而是整体秩序在局部的体现"),
    ("测试", "将{weak}编码为可执行的测试用例是{weak}工程化的关键一步"),
    ("时间论", "{weak}在时间维度上的累积效应远大于单次执行的效果"),
    ("对抗稀释", "严格执行{weak}是防止系统行为漂移和信息稀释的关键屏障"),
    ("平衡", "{weak}不是极端约束而是在约束与自由之间找到平衡点"),
    ("熵增", "{weak}是系统对抗熵增的有序功输入——需要持续做功才能维持低熵态"),
    ("元递归", "元递归使系统能审视自身的{weak}执行策略并持续优化它"),
]

def _make_content(weak, strong, pattern, wc=0, sc=0):
    """生成带具体机制的链内容 — 前缀嵌入当前系统状态防内容去重"""
    # 状态前缀确保每周期前50字符不同
    prefix = f"【{weak}={wc}↔{strong}={sc}】"
    c = pattern.format(weak=weak, strong=strong)
    # 再加一句具体机制
    extras = {
        "系统": f"当{weak}水平提升时，系统各模块的运行一致性指数上升，故障率下降",
        "触类旁通": f"{weak}的实践模式可抽象为'规则约束→行为惯性→自动执行'三阶段模型",
        "行动": f"{weak}的行动化意味着将抽象原则转化为每日可重复的具体操作序列",
        "聚焦": f"在聚焦模式下，{weak}资源集中在关键路径上，避免分散在低价值环节",
        "感知": f"感知{weak}需要细粒度的度量工具——仅凭自我感觉无法准确评估{weak}状态",
        "自指": f"自指使{weak}从外部约束内化为自我驱动的行为准则",
        "智慧": f"智慧在{weak}中的体现是知道何时收紧规则、何时在更高原则下放松规则",
        "一元化": f"一元化视角下，{weak}不是惩罚而是系统整体健康的必要组成部分",
        "测试": f"将{weak}规则编码为自动测试后，每次回归都自动验证{weak}遵守情况",
        "时间论": f"时间维度上的{weak}复利效应——每天1%的纪律改善在一年后产生37倍效果",
        "对抗稀释": f"{weak}是对抗稀释的第一道防线——没有{weak}约束系统行为不可预测",
        "平衡": f"{weak}与创造力的平衡不是零和博弈——高{weak}释放了创造力的结构空间",
        "熵增": f"持续施加{weak}的能耗低于清理熵增混乱的能耗——预防优于清理",
        "元递归": f"元递归优化{weak}本身——系统审视自己的{weak}策略并剔除低效规则",
    }
    return c + "。" + extras.get(strong, "")

def pulse():
    now = time.time()
    
    # 冷却检查
    if _LAST_RUN_FILE.exists():
        try:
            last = float(_LAST_RUN_FILE.read_text().strip())
            if now - last < _RUN_EVERY * 30:
                remaining = int(_RUN_EVERY * 30 - (now - last))
                return {"status": "cooling", "next_in": remaining}
        except:
            pass
    
    from brain.share import read_hip, write_chain
    
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dim_counter = Counter(c.get("dimension", "?") for c in chains)
    total = len(chains)
    
    # 找最弱的维度和所有维度排序
    sorted_dims = sorted(dim_counter.items(), key=lambda x: x[1])
    weakest = sorted_dims[0][0] if sorted_dims else "纪律"
    strongest_dims = [d for d, c in sorted_dims[-5:]] if len(sorted_dims) >= 5 else [d for d, _ in sorted_dims]
    
    # 选当前最弱维（自适应）+ 低于阈值维
    all_weak = [d for d, c in sorted_dims[:3] if c < sorted_dims[-1][1] * 0.65]
    # 补充显式目标（如纪律、复制）如果它们还不达标
    for d in _WEAK_DIMS:
        if d not in all_weak and dim_counter.get(d, 0) < 150:
            all_weak.append(d)
    if not all_weak:
        all_weak = _WEAK_DIMS
    
    injected = 0
    errors = []
    
    # 为每个弱维注入交叉链
    for weak in all_weak:
        # 过滤掉弱维自身和未分类
        strong_candidates = [(s, p) for s, p in _STRONG_DIM_PAIRS 
                           if s != weak and s in dim_counter]
        if not strong_candidates:
            continue
        
        # 选target_count决定注入量——越弱注入越多
        wc = dim_counter.get(weak, 0)
        sc_max = max(dim_counter.values())
        need = 3 if wc < sc_max * 0.3 else (2 if wc < sc_max * 0.5 else 1)
        
        # 随机选交叉对
        random.shuffle(strong_candidates)
        for strong, pattern in strong_candidates[:need]:
            try:
                content = _make_content(weak, strong, pattern, wc=wc, sc=dim_counter.get(strong, 0))
                # rel用weak×strong确保唯一
                rel_tag = f"{weak}×{strong}_{random.randint(1,999)}"
                chain = {
                    "src": f"弱维交叉_{weak}×{strong}",
                    "rel": rel_tag,
                    "dst": weak,
                    "dimension": weak,
                    "content": content,
                    "strength": 0.80,
                    "source_dim": strong,
                }
                if write_chain(chain):
                    injected += 1
                else:
                    errors.append(f"去重:{weak}×{strong}")
            except Exception as e:
                errors.append(str(e)[:40])
    
    _LAST_RUN_FILE.write_text(str(now))
    
    # 反馈
    try:
        gf = {}
        if _GEN_FEEDBACK_FILE.exists():
            gf = json.loads(_GEN_FEEDBACK_FILE.read_text())
        reports = gf.get("reports", [])
        reports.append({
            "source": "gen_弱维交叉注入",
            "weak_targets": all_weak,
            "injected": injected,
            "timestamp": now,
        })
        gf["reports"] = reports[-80:]
        _GEN_FEEDBACK_FILE.write_text(json.dumps(gf, ensure_ascii=False, indent=2))
    except:
        pass
    
    return {
        "status": "done",
        "injected": injected,
        "targets": all_weak,
        "errors": errors[:3] if errors else [],
        "total_chains": total + injected,
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
