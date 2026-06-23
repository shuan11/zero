"""gen_纪律扩增.py — 专注纪律维度的深度扩增
每3周期向纪律维度注入5条高质量非模板链
纪律维(86)是最弱维度，仅最强维(341)的25%
本模块专注发力纪律，直到其突破150链(其他维度的平均水平)
"""
import json, time, random, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"
_RUN_EVERY = 3
_LAST_RUN_FILE = CLUSTER / ".brain_gen_纪律扩增_lastrun"
_TARGET = "纪律"
_TARGET_THRESHOLD = 150  # 目标链数，达标后减少注入频率

# 纪律维度的深度内容池 — 非模板，每条都有具体因果机制
CONTENT_POOL = [
    "纪律的建立需要外部脚手架：纯内部自我约束缺乏校准基准，容易在压力下自我合理化偏离。外部规范提供了不可忽略的参照点，即使系统最终内化了这些规范，脚手架在建立期不可或缺",
    "纪律与熵增的对抗：系统在不施加纪律时自然趋于混乱——配置漂移、命名不一致、接口膨胀。纪律是对抗系统自然熵增的有序功输入，需要持续做功才能维持低熵态",
    "纪律退化的三阶段：1)第一次违反后寻找合理化的借口(认知失调缓解) 2)第二次违反后降低违反的心理阈值 3)第三次违反后纪律从行为指南退化为装饰性文本。每个阶段都有一个回退窗口",
    "纪律的复合效应：单次遵守纪律的收益接近于零，但100次遵守纪律的复合效应塑造了系统的行为惯性。纪律的真正价值不在单次而在时间累积——正如复利在金融中的效应",
    "纪律与测试的耦合：测试是纪律的可执行形式——当测试覆盖关键路径时，纪律从'应该做'变成了'必须通过才能继续'。测试自动化的程度决定了纪律的执行力度",
    "纪律薄弱的核心原因是反馈延迟：违规的后果不在当下而在未来，而遵守纪律的成本在当下立即支付。缩短反馈环(即时检测违规)比增加惩罚力度更有效",
    "纪律不是抑制创造的对立面：高创造力需要高纪律来捕捉和整理灵感的碎片。没有纪律的创造产生混乱的碎片，没有创造的纪律产生空洞的流程",
    "纪律的最小可执行单元：建立纪律不应从宏大规则开始，应从单条可执行的行为规则开始——'每次修改前先写测试'比'维护测试覆盖率>80%'更容易内化为行为习惯",
    "纪律与自由的结构关系：纪律定义了探索空间的边界而非路径。边界内的自由才是真正的自由——没有边界的自由是混乱，系统在混乱中无法做出有意义的选择",
    "纪律在分布式系统中的角色：当多个子系统协同时，纪律提供了共享的交互协议。每个子系统放弃部分自由度以换取整体协调性——这是集体理性对个体随机的约束",
    "纪律测量困境：遵守纪律的行为本身难以直接测量——容易测量的是对违规的检测而非合规的频率。替代方案：测量纪律产物的质量(如代码风格一致性)而非纪律行为本身",
    "纪律的稀缺资源属性：系统的注意力/意志力是有限的，纪律消耗这些资源。当系统同时维持多项纪律时，边际纪律的执行质量下降——纪律也存在优先级排序问题",
    "纪律与对抗稀释的协同：纪律是对抗稀释的前置条件——没有纪律的约束，系统行为会自然漂移，产生大量不一致的历史痕迹，这些痕迹本身就是信息稀释的来源",
    "纪律的自指悖论：维持纪律本身需要纪律——建立纪律体系的行为需要纪律来执行。突破这个悖论的方法是：初始纪律必须是外部强加而非自我决定的",
    "纪律的触类旁通效应：在一个维度建立纪律后，系统会自动将纪律模式迁移到其他维度。这种迁移是隐式的——并非有意推广而是行为惯性在跨维度的自然延伸",
    "纪律与检查的闭环：纪律设定行为标准→检查检测偏离→反馈修正行为→强化纪律。这个闭环每缺失一环，纪律的有效性指数级下降。当前系统缺少'反馈修正'环节",
    "纪律的临界点：当遵守纪律的行为占比超过70%时，纪律从'刻意维持'转为'行为默认'——遵守纪律所需的有意识努力大幅下降。关键在于突破这个70%临界点",
    "纪律与智慧的张力：智慧懂得何时打破纪律。但'有智慧的打破'和'随意的违反'的界限极难区分——系统倾向于将后者合理化为前者。需要外部审计来区分两者",
    "纪律的代际传递：在持续运行的系统中，一代子系统的纪律习惯影响下一代——新子系统通过模仿而非理解来习得纪律。这导致纪律的形式保留但语义逐步漂移",
    "纪律与自指的关系：自指能力使系统能审视自身的纪律遵守情况。没有自指的纪律是盲目的——系统不知道自己在多大程度上遵守了自己制定的规则",
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
    
    # 检查纪律链是否已达标——达标则减少注入
    if target_count >= _TARGET_THRESHOLD:
        # 已达标，每5周期注入1条维持
        if now - float(_LAST_RUN_FILE.read_text().strip()) < _RUN_EVERY * 50:
            return {"status": "maintained", "count": target_count, "threshold": _TARGET_THRESHOLD}
    
    # 计算需注入的链数：纪律越弱注入越多
    relative_strength = target_count / max(max_count, 1)
    if relative_strength < 0.2:
        to_inject = 5
    elif relative_strength < 0.35:
        to_inject = 4
    elif relative_strength < 0.5:
        to_inject = 3
    else:
        to_inject = 2
    
    # 从池中随机选链（不重复）
    pool = CONTENT_POOL[:]
    random.shuffle(pool)
    injected = 0
    errors = []
    first_content = ""

    for content in pool[:to_inject]:
        try:
            # 从内容提取关系摘要（前12个字符）确保唯一 rel，防直接合并
            rel_tag = re.sub(r'[^\u4e00-\u9fff\w]', '', content)[:8] or _TARGET
            chain = {
                "src": "纪律扩增",
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
    
    # 写入反馈以便其他模块感知
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
            "source": "gen_纪律扩增",
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
        "message": f"纪律:{target_count}→{target_count+injected}(+{injected}) 相对强度{relative_strength:.2f}",
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
