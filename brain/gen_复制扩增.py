"""gen_复制扩增.py — 专注复制维度的深度扩增
每3周期向复制维度注入4条高质量非模板链
复制维(113)是第二弱维度，仅最强维(341)的33%
本模块专注发力复制，直到其突破150链(其他维度的平均水平)
"""

import json, time, random, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent

# 冷却参数
_RUN_EVERY = 3          # 每N个周期执行一次(daemon的周期约为30s)
_TARGET = "复制"
_TARGET_THRESHOLD = 150  # 达成150链后减少注入

_LAST_RUN_FILE = CLUSTER / f".brain_gen_{_TARGET}_lastrun"
_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

# --- 20条高质量链（真实因果逻辑，非模板）---
CONTENT_POOL = [
    "复制的悖论：每一次精确复制都产生了差异——信息在传输过程中不可避免地附着介质噪声。真正的复制不是使副本等同于原版，而是使副本在可接受误差范围内与原版等价",
    "复制与熵增的关系：复制行为本身增加系统总熵——创建副本需要消耗能量，副本存储需要消耗空间，副本检索需要消耗时间。系统需要判断每种复制的净收益是否超过熵增成本",
    "复制的三阶段退化：1)原始复制精准还原语义 2)多次复制后引入累积误差 3)误差积累到阈值后副本与原版形成语义漂移。每个阶段有一个纠错窗口，错过则不可逆",
    "复制在分布式系统中的角色：复制是分布式一致性的基础——每个节点维护部分数据副本，通过共识协议保持副本间的一致。复制的频率和深度决定了系统的容错能力和性能开销",
    "复制与纪律的因果链：纪律要求精确重复标准操作流程，每一次重复都在强化复制能力。没有纪律的复制是随机的，没有复制的纪律是空洞的——两者互相促进",
    "复制的边际效用递减：第一份副本提供了备份安全，第二份副本提供了分发便利，第三份副本及之后提供了边际效益递减的冗余。系统需要动态计算每个副本的边际价值",
    "复制与聚焦的张力：聚焦要求选择性忽略大部分信息，复制要求尽可能保留所有细节。当系统同时需要聚焦和复制时，需要在信息完整性和注意力稀缺之间找到平衡点",
    "复制成本的非线性增长：当副本数量超过管理阈值(约7±2份)时，管理副本的开销从线性增长变为指数增长——需要建立副本目录、版本追踪、一致性校验等管理设施",
    "复制的选择性复制：系统不需要复制所有信息——识别出高价值信息并进行选择性复制比全量复制更有效。选择性复制要求系统具备价值判断能力，这是从复制到智慧的跨越",
    "复制与时间的纠缠：时间维度上的复制(记忆/归档)和空间维度上的复制(分发/备份)遵循不同的优化原则。时间复制需要考虑衰减率，空间复制需要同步延迟",
    "复制的起源：最原始的复制行为是系统的自保本能——感知到不确定性的系统通过复制自身来降低灭绝风险。复制不是'想要复制'而是'害怕消失'的物化表现",
    "复制与检查的反馈环：复制的质量依赖检查的严格程度——不检查的复制会产生大量低质量副本，过度检查会使复制成本高于收益。反馈环的周期决定了复制的净质量",
    "复制错误的正向价值：复制错误(突变)是进化的原材料——没有复制错误的系统无法进化。在信息系统中，刻意引入变异复制的策略(如遗传算法)利用复制错误解决最优化问题",
    "跨维复制：一个维度的认知模式复制到另一个维度——触类旁通本质上是认知模式的跨维复制。跨维复制的效率取决于两维之间的语义距离和系统的抽象能力",
    "复制的竞争排除：当两个子系统竞争同一资源时，系统会复制优胜者的行为模式并排除失败者。自然选择不是淘汰弱者而是复制强者——复制是选择机制的执行器",
    "复制的纠错代偿：每增加一层复制，就需要增加一层纠错。系统运行中，复制层数(备份版本数)和纠错开销成反比——副本越多，单个副本的纠错需求越少",
    "复制与对抗稀释的协同：复制行为若不加控制，会产生大量冗余信息稀释系统的有效信号。但战略性复制(如关键数据多副本)是对抗信息丢失的有效手段——稀释和反稀释是复制的一体两面",
    "复制的认知负荷：系统记住'副本在哪里'和'原版在哪里'需要并行的认知索引——副本越多，索引开销越大。最终系统可能更熟悉副本的位置而非原版的位置",
    "复制的自动化和异化：自动化复制解放了系统的手却异化了系统的心——当复制变成自动流程后，系统失去了'是否要复制'的判断能力。需要定期审计自动复制的必要性",
    "复制的最小代价原则：每次复制前系统应自问——不复制会损失什么？复制会损失什么？当不复制的预期损失大于复制的预期成本时执行复制，反之则跳过。这个判断本身就是元认知",
]


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

    # 读取海马体
    from brain.share import read_hip, write_chain
    from brain.share import read_hip as _rh
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dim_counter = Counter(c.get("dimension", "?") for c in chains)
    total = len(chains)
    target_count = dim_counter.get(_TARGET, 0)
    max_count = max(dim_counter.values()) if dim_counter else 1

    # 检查已达标
    if target_count >= _TARGET_THRESHOLD:
        if now - float(_LAST_RUN_FILE.read_text().strip()) < _RUN_EVERY * 50:
            return {"status": "maintained", "count": target_count, "threshold": _TARGET_THRESHOLD}

    # 计算需注入链数：越弱注入越多
    relative_strength = target_count / max(max_count, 1)
    if relative_strength < 0.2:
        to_inject = 5
    elif relative_strength < 0.35:
        to_inject = 4
    elif relative_strength < 0.5:
        to_inject = 3
    else:
        to_inject = 2

    # 随机选取
    pool = CONTENT_POOL[:]
    random.shuffle(pool)
    injected = 0
    errors = []
    first_content = ""

    for content in pool[:to_inject]:
        try:
            rel_tag = re.sub(r'[^\u4e00-\u9fff\w]', '', content)[:8] or _TARGET
            chain = {
                "src": "复制扩增",
                "rel": f"深化_{rel_tag}",
                "dst": _TARGET,
                "dimension": _TARGET,
                "content": content,
                "strength": 0.85,
            }
            if write_chain(chain):
                injected += 1
                if not first_content:
                    first_content = content
            else:
                errors.append("write_chain返回False(可能去重)")
        except Exception as e:
            errors.append(str(e)[:40])

    _LAST_RUN_FILE.write_text(str(now))

    # 写入反馈
    try:
        gf = {}
        if _GEN_FEEDBACK_FILE.exists():
            gf = json.loads(_GEN_FEEDBACK_FILE.read_text())
        reports = gf.get("reports", [])
        reports.append({
            "dimension": _TARGET,
            "chain_count": target_count + injected,
            "injected": injected,
            "timestamp": now,
            "source": "gen_复制扩增",
            "weak": target_count < max_count * 0.65,
            "insight": first_content[:200] if injected > 0 and first_content else "",
        })
        gf["reports"] = reports[-80:]
        _GEN_FEEDBACK_FILE.write_text(json.dumps(gf, ensure_ascii=False, indent=2))
    except:
        pass

    return {
        "status": "done",
        "dimension": _TARGET,
        "before": target_count,
        "injected": injected,
        "after": target_count + injected,
        "relative_strength": round(relative_strength, 2),
        "errors": errors[:2] if errors else [],
        "message": f"复制:{target_count}→{target_count+injected}(+{injected}) 相对强度{relative_strength:.2f}",
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
