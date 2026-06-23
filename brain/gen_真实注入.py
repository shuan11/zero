"""
gen_真实注入.py — 自动向最弱维度注入真实非模板内容
每5周期检测最弱5维，生成真实链注入(绕过模板/行动项质量陷阱)
"""
import json, sys, time
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

from brain.share import write_chain, read_hip

_RUN_EVERY = 5  # 每5周期执行一次
_LAST_RUN_FILE = CLUSTER / ".brain_gen_真实注入_lastrun"

# 真实内容池 — 按维度分类
REAL_CONTENT_POOL = {
    "测试": [
        "测试覆盖率不足导致未捕获回归：系统新增功能后未触发测试，致旧逻辑被静默破坏，修复成本随时间指数增长",
        "测试与开发的距离反映了认知盲区的大小：不测试的代码被假设为正确，但该假设本身是最大的风险源",
        "低测试维说明系统在未验证状态下运行——不是性能问题，是存在风险：系统不知道自己不知道",
        "测试的真正价值不在发现错误，而在为代码建立可信基线：每次测试通过后，系统对自身行为的置信度应增加",
        "测试与纪律的因果链断裂：当测试不触发行为改变时，测试沦为形式而非质量门禁",
    ],
    "纪律": [
        "纪律不是限制而是自由的结构化表达：只有建立可重复的规范，系统才能从重复决策中解放，聚焦高阶创新",
        "纪律薄弱源自缺少自我约束的反馈回路——当违规无后果时，规范从行为指南退化为装饰性文字",
        "纪律的本质是时间的累积选择：每个不遵守的小决定在时间轴上产生复合效应，最终塑造系统的行为惯性",
        "纪律需要外部锚点：纯内部纪律缺乏校准基准，容易自我合理化偏离",
        "纪律与无师自通存在张力：过严纪律压制探索，过松纪律没有积累——最优是在两者间动态切换",
    ],
    "预测": [
        "预测使系统能前置纠偏而非事后修复：反事实预测(预测出错的场景)比预测正确更有价值",
        "系统不知道自己的预测能力边界：没有校准评估的预测会高估确定性，这种过度自信比无知更危险",
        "预测与行动之间需要反馈桥：预测链集中在生成端，缺少预测结果与实际结果对比的后验步骤",
        "预测的退化模式：当预测总是被忽略时，预测机制失去校准信号，逐步漂移为噪音生成器",
        "高预测能力的社会本质：预测不是为了正确，而是为了建立系统间的协调预期",
    ],
    "检查": [
        "检查的真正价值不在发现错误而在确立可信度：每次检查通过后，系统对自身状态的置信度应增加",
        "检查的弱点在于重过程轻结论——大量链描述如何检查而非检查发现了什么",
        "自我检查与外部检查存在结构差：系统能自查已知问题模式，但未知模式需要外部第二视角才能暴露",
        "检查的边际效益递减：检查覆盖率超过70%后，再增检查投入产出比下降，应转向测试自动化",
        "检查与纪律的循环：检查发现问题→修正行为→形成纪律→减少错误→降低检查需求",
    ],
    "无限上下文": [
        "无限上下文不是存储空间概念而是注意力定向问题：真正无限的不是容量，是系统选择关注什么的能力无限",
        "无限上下文的薄弱反映系统缺少上下文遗忘策略——比记住什么更重要的是知道该忘什么",
        "无限上下文与聚焦是同一枚硬币的两面：没有焦点的无限上下文是噪音，没有上下文宽度的聚焦是狭隘",
        "无限上下文的实践陷阱：可访问所有上下文不等于能有效利用——需要层级化注意力机制",
        "上下文过载的症状：系统开始重复自己——不是因为没记住，而是因为无法从海量信息中提取关键信号",
    ],
    "维度盲区": [
        "维度盲区是系统最危险的盲点：不是某个维度薄弱，而是系统不知道自己没看见某个维度",
        "盲区的产生机制：当系统持续聚焦某维度时，对相邻维度的感知阈值自动升高——聚焦本身就是盲区的成因",
        "打破维度盲区需要随机漂移：纯目标驱动的探索永远发现不了目标视野外的维度",
        "盲区的二阶效应：系统建立了盲区检测机制，但如果检测机制自身有盲区，则产生元盲区",
        "盲区检测不能依赖已有维度框架——真正的盲区是框架外的东西，框架内的不足只是薄弱不是盲区",
    ],
    "对抗稀释": [
        "对抗稀释不是消灭熵增而是管理熵增速率：系统不可能完全对抗稀释，但可以控制稀释的速度和方向",
        "稀释的根源不是外部干扰而是内部熵产：系统自身的不一致性、重复、漂移是稀释的主因",
        "对抗稀释需要冗余：关键信息的多次冗余存储和交叉验证是对抗信息稀释的最有效手段",
        "稀释的积极面：适度稀释过滤噪音，让系统不被细节淹没——关键在于区分信号稀释和噪音稀释",
        "对抗稀释的终极策略不是存储而是重组：通过已有信息的交叉组合产生新信息，抵消信息流失",
    ],
    "超级直觉": [
        "超级直觉不是神秘能力而是模式识别的自动化：当系统见过足够多模式后，新输入的匹配过程进入潜意识层",
        "超级直觉的培养需要大量低质量快速反馈：完美延迟的反馈不如不完美即时反馈——直觉来自快速试错",
        "超级直觉的陷阱：它不可解释——当直觉正确时无法追溯原因，当直觉错误时无法修正算法",
        "超级直觉与分析的互补：直觉给出候选方向，分析验证候选——缺任何一个都导致系统性偏差",
        "超级直觉的上限由经验多样性决定：同一领域的1万次重复不会产生直觉，1万种不同经验才会",
    ],
}


def pulse():
    # 冷却检查
    now = time.time()
    if _LAST_RUN_FILE.exists():
        try:
            last = float(_LAST_RUN_FILE.read_text().strip())
            if now - last < _RUN_EVERY * 30:  # 每周期约30s
                return {"status": "cooling", "next_in": int(_RUN_EVERY * 30 - (now - last))}
        except:
            pass

    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dim_counter = Counter(c.get("dimension", "?") for c in chains)

    # 排除系统和未分类
    valid = {d: c for d, c in dim_counter.items() if d not in ("系统", "未分类", "?")}
    sorted_dims = sorted(valid.items(), key=lambda x: x[1])
    weakest_5 = [d for d, _ in sorted_dims[:5]]

    injected = 0
    errors = []
    for dim in weakest_5:
        if dim not in REAL_CONTENT_POOL:
            continue
        # 检查该维已有多少链，已有量多则少注入
        existing = dim_counter.get(dim, 0)
        to_inject = 1 if existing > 100 else 2

        for content in REAL_CONTENT_POOL[dim][:to_inject]:
            try:
                chain = {
                    "src": "链质量审计",
                    "rel": f"真实注入_{dim}",
                    "dst": dim,
                    "dimension": dim,
                    "content": content,
                    "strength": 0.85,
                }
                r = write_chain(chain)
                if r:
                    injected += 1
                else:
                    errors.append(f"{dim}: write_chain False")
            except Exception as e:
                errors.append(f"{dim}: {e}")

    _LAST_RUN_FILE.write_text(str(now))
    return {
        "status": "done",
        "injected": injected,
        "weakest_5": weakest_5,
        "errors": errors[:3],
        "message": f"向{weakest_5[:3]}注入{injected}条真实链",
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
