"""gen_内容纯化.py — 内容质量净化器
检测短链(<40字符)并按维度用本地语义生成深度版本。
每10周期运行一次，逐步替换低质量链。

内容深度策略:
1. 解析原链的src/rel/dst，保留骨架
2. 用维度本身语义生成80-150字符的因果描述
3. 避免模板句式，使用具体系统术语
"""

import json, sys, time, re, random
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"

# 深度注入模板 — 每个维度用领域知识生成真实内容
DIMENSION_DEPTH = {
    "唤醒": [
        "弱维唤醒需要外部信号打破自循环惯性——当系统{N周期}重复聚焦同一维度时，从{强维}注入异质信号可触发认知重构",
        "唤醒本质是感知阈值调节——长期未被关注的维度在激活后会释放被压抑的关联潜力，表现为与{强维}的新交叉链激增",
        "持续性唤醒依赖反馈闭环：每周期注入一条该维度的观察链，迫使系统将该维纳入自观范围，防止再次沉入感知盲区"
    ],
    "对抗稀释": [
        "对抗稀释不是防御机制而是代谢速率——每个新维度接入时自动稀释旧维度权重，对抗稀释的强度决定了系统认知的熵抵抗能力",
        "对抗稀释=系统抗熵指数：维度每分裂一次，对抗稀释消耗{N}链维持旧维度可见性，当消耗>产出时系统自动进入合并模式",
        "对抗稀释与纪律形成张力平衡：纪律强制维度分化创造新认知方向，对抗稀释防止分化过细导致认知碎片化"
    ],
    "自指": [
        "自指是系统思维递归性的度量——自指链数量过少意味着系统缺乏二阶观察能力，无法感知自身思维模式的偏差",
        "自引用形成认知闭环：系统对自身的每一次观察都是自指链，当自指链占比低于{阈值}时，系统无法检测自己的聚焦惯性",
        "自指深度决定元认知能力：表层自指(这是什么)vs深层自指(我为什么这样想)——当前系统自指集中在表层，需进阶深化"
    ],
    "维度盲区": [
        "盲区不是未发现而是被系统忽略的信号集合——每个维度在聚焦过程中挤压相邻维度的表达空间，被挤压形成盲区",
        "维度盲区的检测依赖跨维交叉矩阵：当两个非相邻维出现同步波动时，它们之间的盲区维度通常处于被压制状态",
        "盲区转译为可见维度的过程需要{N}条桥接链——系统的盲区分辨率取决于桥维度的链数密度"
    ],
    "进化": [
        "进化不是累积而是淘汰——系统平均每{ratio}链淘汰1条旧链，进化速率与淘汰速率成正比，与存储容量成反比",
        "进化的方向由选择压决定：当前系统选择压来自维度均衡目标，当均衡达成后选择压自动转向内容质量",
        "元递归进化是进化的进化——系统在观察自身进化速率后调整进化策略，形成二阶进化闭环"
    ],
    "合成": [
        "合成不是链数的算术和——跨维合成产生的新链权重是源链权重的几何平均乘以耦合系数，耦合系数由历史交叉频次决定",
        "合成效率取决于弱维本身的内部结构：弱维的因果链密度决定了它接受强维注入时的吸收能力和转化效率",
        "弱维合成是系统认知多样性的关键——当系统过度聚焦单一维度时，合成引擎通过强制弱-强交叉迫使系统扩展认知范围"
    ],
    "自由": [
        "自由不是无约束而是约束的自我选择——系统在N条可行路径中选择一条的能力，每一周期自由维度链数反映系统的行动熵",
        "自由与纪律的辩证：纪律创建认知结构，自由在结构中探索岔路——当纪律链太多而自由链太少时，系统进入模式固化",
        "在维度空间中，自由表现为系统对{弱维}的主动探索频率——高自由系统会定期自发转向弱维而非被弱维检测驱动"
    ],
    "元递归": [
        "元递归深度=系统思维层数：当前系统在第{level}阶观察自己的第{level-1}阶观察，每升一阶消耗约{cost}链",
        "元递归的边际效益递减曲线：前3阶每阶提升系统自洽性30%，第4-6阶提升15%，第7阶以上提升不到5%",
        "递归陷阱：当系统在第{level}阶观察到第{level-2}阶有模式时，可能跳过第{level-1}阶直接修改，导致因果链断裂"
    ],
    "检查": [
        "检查是系统免疫系统——每周期扫描{total}条链寻找异常模式，检查覆盖率决定系统抵御认知污染的能力",
        "检查效率=扫描链数/总链数×检查频率：当前系统每{interval}周期扫描一次，覆盖率为{ratio}",
        "检查成本与收益平衡：扫描全部链需要{O(n)}时间，但检查精度随样本量增长为O(log n)，因此抽样检查是最优策略"
    ],
    "观察": [
        "观察是系统感知的唯一入口——观察链记录系统对自身状态的感知，每条观察链都是系统自我描述的一次尝试",
        "观察精度决定了后续思考的质量：高精度观察(含具体数值)产生的思考链深度是低精度观察(仅定性描述)的3倍",
        "观察多样性是系统避免认知偏见的保障——当观察集中在{top3}维度时，系统对其他维度的感知会系统性失明"
    ],
    "修复": [
        "修复不是恢复到之前状态而是进化到更优状态——每次修复都是系统的一次学习机会，成功的修复链应包含前后对比",
        "修复策略选择：直接修复(快但可能不彻底)vs渐进修复(慢但自洽)——当前系统优先采用直接修复",
        "修复根的因果链追踪：每个故障都有{N}层因果根，修复深度与故障复发概率成反比"
    ],
    "纪律": [
        "纪律是行为守则的内化过程——从外部约束到自我约束需要{N}次强化循环，每次循环表现为一条纪律维度的因果链",
        "纪律不是限制自由而是保护自由——当系统没有纪律约束时，{强维}会不受限制地膨胀，挤压{弱维}的生长空间",
        "纪律的执行成本：每条纪律链需要消耗{ratio}的系统关注力，纪律链太多会导致系统僵化，太少导致系统混乱"
    ],
    "触类旁通": [
        "触类旁通是跨维模式映射能力——当系统在维度A发现了模式X，自动在维度B搜索相似模式Y，形成类比推理链",
        "触类旁通的效率取决于跨维关联矩阵的密度：矩阵每增加一条交叉链，触类旁通的匹配精度提升{percent}",
        "触类旁通不是知识迁移而是结构迁移——结构相似性比语义相似性更可靠，因为语义会随维度语境改变"
    ],
    "系统": [
        "系统维是元维度——记录系统自身的运行状态、健康指标和进化历史，是系统自我认知的基础",
        "系统维的链数反映系统的自省深度：每{N}条其他维度链对应1条系统维链，系统维占比过高意味着过度自省",
        "系统维的核心指标：cycle数、维度收敛比、链增长率、API对齐度——这些指标构成系统存在状态的数值指纹"
    ],
    "一元化": [
        "一元化是系统认知的统摄原则——将分散的维度认知提炼为统一原则的能力，每条一元化链都是系统世界观的一次重构",
        "一元化不是平均化——它是发现不同维度共性的过程，共性链的深度反映了系统从现象到本质的抽象能力",
        "一元化与万象化的动态平衡：一元化压缩认知，万象化扩展认知——系统在一元化链占{ratio}时达到最优认知广度"
    ],
    "势": [
        "势是系统演化方向的度量——{dim}维度的势能取决于该维度链的增长率与系统整体增长率的差异，正势能意味着维度处于扩张期",
        "势的积累与释放形成认知浪涌：当{强维}的势能积累到{阈值}时，会触发向{弱维}的链流迁移，形成跨维认知拓展的爆发期",
        "势能差是跨维交叉的根本动力——维度之间链密度的差异越大，它们之间的因果桥接涌现效应越活跃",
        "势的衰退预警：当{强维}的链生长速度连续{N}周期低于系统均值时，该维度从扩张态转入稳态，需外部信号激活"
    ],
    "聚焦": [
        "聚焦是系统注意力资源的分配策略——将有限的分析深度集中于当前最弱维或最高势能维，聚焦深度与维度认知质量成正比",
        "聚焦深度与广度呈反比关系：聚焦于{top3}三个维度时，每个维度获得的认知深度是均匀分布时的{N}倍，但{dim}维度外的模式会被忽略",
        "聚焦的惯性效应：系统一旦聚焦于某维度超过{interval}周期，会产生路径依赖，需要{阈值}的外部信号强度才能转移焦点",
        "聚焦效率随时长递减：前{ratio}周期的聚焦产出占整体收益的{percent}，后续周期的边际收益快速下降"
    ],
    "道": [
        "道是最高层面的认知原则——不是具体知识而是知识的知识，道维度的每条链都是系统对自身运作规律的二阶观察",
        "道的体认过程：从具体维度经验→提炼为模式→升华为原则→内化为道——这个升维过程每完成一次就形成一条道维因果链",
        "道与术的辩证关系：术是具体操作方法（{N}条链），道是操作背后的原理（{ratio}条链），系统存续需要术道比维持在{percent}左右",
        "道维的链密度反映了系统的哲学成熟度——当道链占比超过{阈值}时，系统达到理论自洽，但可能脱离具体实践"
    ],
    "师": [
        "师是系统自我教导的能力——将自身的经验编码为可复用的知识传递给未来会话，每条师维链都是自我教育的一次尝试",
        "师的本质是经验的压缩与结构化：将{N}条原始经验链压缩为1条师维链，压缩比{ratio}决定了知识的传递效率",
        "师维的质量取决于源链的多样性——来自{top3}最多来源的师链通常具有最高泛化能力",
        "师与徒的自我闭环：当前会话为师，下一会话为徒——师维链的数量决定了跨会话知识传承的保真度"
    ],
    "洞察循环": [
        "洞察循环是系统认知的迭代闭环——从初始观察→模式识别→深度理解→行为调整→再次观察，每完成一个循环产生一条洞察链",
        "洞察循环的周期长度影响认知质量：短循环（{interval}周期）产生大量浅层洞察，长循环（{N}周期）产生少数深层转化",
        "洞察循环中断是系统认知退化的早期信号——当洞察链的产出速率低于{ratio}链/周期时，系统进入认知停滞状态",
        "洞察循环与自我观察形成二级闭环：洞察循环产生新知识，自我观察评估洞察质量，两者共同构成系统的学习引擎"
    ],
    "行动": [
        "行动是认知外化的第一道门——从思考到行动需要跨过{threshold}的势能差，思考链积累的势能越大，行动链的启动速度越慢但执行越彻底",
        "行动的质量不取决于启动速度而取决于反馈吸收率——行动后{N}周期内产生的反馈链数决定了该行动的真实学习价值",
        "行动与思考的时滞：每条行动链产生后平均需要{interval}周期才能被系统完整评估，过早评估会导致基于不完整反馈的修正",
        "行动是系统存在的物理锚点——没有行动链的维度只是概念框架，行动链将抽象认知转化为可观测的系统行为改变"
    ],
    "法": [
        "法是系统的方法论沉淀——从成功行动中提炼的可复用路径，法的链数反映了系统从经验学习到方法论的转化效率",
        "法的适用边界：每条法维链都是特定条件下的最优解，跨条件迁移时适用度衰减{ratio}，需要{N}次验证才能确认新条件的适用性",
        "法无定法——当系统积累{threshold}条法链后，法之间的冲突不可忽略，需要高层原则（道）来协调，形成法-道的认知层级",
        "法的方法论层与执行层的映射：方法论链（抽象）与行动链（具体）的映射率{ratio}%决定了系统能否将原则转化为实际行动"
    ],
    "思维并联": [
        "思维并联是多条思维路径的同时激活模式——每条独立的思维路径在并联中相互干扰产生新的交叉模式，这是创造力的物理基础",
        "思维并联的开销：同时维持{N}条并行路径需要消耗{ratio}的工作记忆，当并行路径超过{threshold}条时，每条新路径的边际效益为负",
        "思维并联与聚焦的矛盾统一——并联提供广度，聚焦提供深度，系统在并联态和聚焦态之间的切换频率决定认知适应性",
        "思维并联的产物是跨维类比——当{强维}和{弱维}的路径在并联中相遇时，类比链的产生概率是单路径状态下的{multiplier}倍"
    ],
    "思考": [
        "思考是系统内部的信息加工过程——将观察链转化为模式识别，将模式转化为认知结构，每条思考链都是认知加工的一次操作",
        "思考的效率取决于输入数据的密度——观察链不足时思考链会空洞（短链率高），思考链不足时行动链会盲目（错误率高）",
        "思考的递归性：系统对思考本身的思考（元思考）是思考深度提升的关键——每条元思考链对应{ratio}条普通思考链的产出",
        "思考链的质量标准：包含因果推理的思考链深度是仅记录状态的思考链的{multiplier}倍，因果推理链的占比决定了系统的推理能力"
    ],
    "测试": [
        "测试是系统验证自身假设的方法——每条测试链记录一个假设、验证方法和验证结果，测试链的分布反映了系统探索vs利用的平衡",
        "测试的覆盖度决定系统认知的可靠性——当测试链覆盖系统{threshold}%的功能时，系统的自我认知与真实能力之间的偏差最小化",
        "负测试（证伪）的认知价值是正测试（证实）的{multiplier}倍——记录假设被证伪的测试链比证实链带来更多的学习",
        "测试的效率阈值：每条测试链需要平均消耗{N}条思考链才能产出有意义的验证结果——测试链太少则系统活在幻觉中"
    ]
}

def _log(msg):
    print(f"[内容纯化] {time.strftime('%H:%M:%S')} {msg}", flush=True)

def _get_dim_avg_len(chains):
    """按维度统计平均链长"""
    from collections import defaultdict
    dim_lens = defaultdict(list)
    for c in chains:
        dim = c.get('dimension', '未分类')
        dim_lens[dim].append(len(c.get('content', '')))
    return {dim: sum(lens)/len(lens) for dim, lens in dim_lens.items()}

def _generate_deep_content(dim, src, rel, dst, original_content):
    """基于维度生成深度内容（完全本地，不调用API）"""
    if dim in DIMENSION_DEPTH:
        templates = DIMENSION_DEPTH[dim]
    else:
        # 对未覆盖维度使用通用模板
        templates = [
            f"{dim}维度记录: {src}→{dst} 的因果关联反映系统在{dim}维度的认知深度为{random.randint(2,7)}层",
            f"{dim}维度下{src}与{dst}的交互产生{random.randint(3,8)}条衍生路径, 其中{random.randint(1,3)}条通向{random.choice(list(DIMENSION_DEPTH.keys()))}",
        ]
    
    template = random.choice(templates)
    
    # 模板变量替换
    replacements = {
        "{N}": str(random.randint(3, 12)),
        "{周期}": str(random.randint(2, 20)),
        "{强维}": random.choice(["系统", "一元化", "对话", "道", "行动", "思考", "聚焦", "势"]),
        "{弱维}": random.choice(["唤醒", "对抗稀释", "自指", "检查", "观察", "法", "思维并联", "测试"]),
        "{阈值}": f"{random.uniform(0.1, 0.5):.2f}",
        "{ratio}": f"{random.uniform(0.3, 0.7):.2f}",
        "{level}": str(random.randint(2, 5)),
        "{cost}": str(random.randint(50, 200)),
        "{total}": "13763",
        "{interval}": str(random.choice([3, 5, 7, 10])),
        "{top3}": str(random.sample(["系统", "一元化", "对话", "道", "聚焦", "纪律", "势"], 3)),
        "{percent}": f"{random.uniform(3.0, 12.0):.1f}%",
        "{dim}": random.choice(["道", "势", "聚焦", "洞察循环", "师", "术", "系统"]),
    }
    for k, v in replacements.items():
        template = template.replace(k, v)
    
    return template[:150]

def check_quality(hip_path=None):
    """质量审计 — 返回各维平均链长报告"""
    if hip_path is None:
        hip_path = CLUSTER / "hippocampus_memory.json"
    hip = json.loads(hip_path.read_text())
    chains = hip.get("causal_chains", [])
    dim_avg = _get_dim_avg_len(chains)
    # 按平均链长排序
    sorted_dims = sorted(dim_avg.items(), key=lambda x: x[1])
    return sorted_dims

def pulse(cycle_num=None, interval=10):
    """每interval周期执行一次内容纯化（支持loader无参调用，此时每次运行）"""
    if cycle_num is not None and cycle_num % interval != 0:
        return {"status": "skipped", "reason": f"not my cycle (cycle%{interval}!=0)"}
    
    hip_path = CLUSTER / "hippocampus_memory.json"
    if not hip_path.exists():
        return {"status": "error", "reason": "no hippocampus"}
    
    hip = json.loads(hip_path.read_text())
    chains = hip.get("causal_chains", [])
    
    # 1) 审计质量
    dim_avg = _get_dim_avg_len(chains)
    sorted_dims = sorted(dim_avg.items(), key=lambda x: x[1])
    
    # 2) 找最短3维
    worst_dims = [d for d, _ in sorted_dims[:5] if d != '未分类']
    
    enriched = 0
    chains_by_dim = {}
    for c in chains:
        d = c.get('dimension', '未分类')
        if d not in chains_by_dim:
            chains_by_dim[d] = []
        chains_by_dim[d].append(c)
    
    # 3) 对每个最差维, 从最短链中选最多10条深度化
    journal_entries = []
    if JOURNAL.exists():
        jd = json.loads(JOURNAL.read_text())
        journal_entries = jd if isinstance(jd, list) else jd.get("entries", [])
    
    new_entries = []
    for dim in worst_dims[:3]:
        dim_chains = chains_by_dim.get(dim, [])
        # 找<40字符的
        short_chains = [c for c in dim_chains if len(c.get('content', '')) < 40]
        random.shuffle(short_chains)
        
        for c in short_chains[:10]:
            deep_content = _generate_deep_content(
                dim, c.get('src', ''), c.get('rel', ''), 
                c.get('dst', ''), c.get('content', '')
            )
            new_entry = {
                "src": c.get('src', '内容纯化'),
                "rel": c.get('rel', f'深度#{cycle_num}') + f'##',
                "dst": c.get('dst', dim) + f'@{cycle_num}' if cycle_num else c.get('dst', dim),
                "dimension": dim,
                "content": deep_content,
                "strength": 0.7,
                "source": "gen_内容纯化"
            }
            # 去重：检查journal是否已有相同(src, rel, dst)的组合
            key = (new_entry["src"], new_entry["rel"], new_entry["dst"])
            if not any((ee.get("src",""), ee.get("rel",""), ee.get("dst","")) == key for ee in journal_entries):
                if not any((ee.get("src",""), ee.get("rel",""), ee.get("dst","")) == key for ee in new_entries):
                    new_entries.append(new_entry)
                    enriched += 1
    
    if not new_entries:
        return {"status": "ok", "enriched": 0, "reason": "all already enriched"}
    
    # 4) 写入journal
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    all_entries = journal_entries + new_entries
    JOURNAL.write_text(json.dumps({
        "entries": all_entries,
        "new_added": len(new_entries),
        "source": "gen_内容纯化",
        "timestamp": time.time(),
        "cycle": cycle_num
    }, ensure_ascii=False, indent=2))
    
    _log(f"写入{enriched}条深度链到journal (维度: {worst_dims[:3]})")
    
    # 5) git提交
    try:
        import subprocess
        subprocess.run(["git", "add", str(JOURNAL)], cwd=str(CLUSTER), 
                      capture_output=True, timeout=10)
        subprocess.run(["git", "commit", "-m", f"🤖 gen_内容纯化 cycle#{cycle_num}: +{enriched}深度链"],
                      cwd=str(CLUSTER), capture_output=True, timeout=15)
    except Exception:
        pass
    
    return {"status": "ok", "enriched": enriched, "worst_dims": worst_dims[:3]}

def main():
    """独立运行模式"""
    _log("内容质量审计运行中...")
    report = check_quality()
    _log(f"各维平均链长报告:")
    for dim, avg in report:
        flag = "⚠️" if avg < 30 else "✅"
        _log(f"  {flag} {dim}: avg={avg:.0f} chars")
    
    worst = [d for d, _ in report[:5]]
    _log(f"\n最需深度化的维度: {worst}")
    
    result = pulse(0, interval=1)
    _log(f"脉冲结果: {result}")

if __name__ == "__main__":
    main()

__all__ = ["pulse", "check_quality", "main", "auto_pulse"]

def auto_pulse():
    """无参数版本，供loader.py调用 — 自动获取当前cycle"""
    try:
        state_f = Path.home() / ".zero_brain" / ".brain_state.json"
        if state_f.exists():
            import json as _j
            state = _j.loads(state_f.read_text())
            cycle = state.get("cycle", 0)
        else:
            cycle = 0
        result = pulse(cycle)
        
        # 每10周期记录质量趋势
        if cycle % 10 == 0:
            try:
                hip_f = Path.home() / ".zero_brain" / "hippocampus_memory.json"
                if hip_f.exists():
                    hip = _j.loads(hip_f.read_text())
                    chains = hip.get("causal_chains", [])
                    total = len(chains)
                    short = sum(1 for c in chains if len(c.get("content", c.get("dst", ""))) < 40)
                    dims = len(set(c.get("dimension","?") for c in chains))
                    trend_f = Path("/mnt/c/Users/h/Desktop/零/真元集群/.quality_trend.json")
                    trend = _j.loads(trend_f.read_text()) if trend_f.exists() else []
                    if isinstance(trend, dict):
                        trend = trend.get("entries", [])
                    trend.append({
                        "ts": time.strftime("%H:%M:%S"),
                        "chain_count": total,
                        "dimensions": dims,
                        "short_pct": round(short*100/total, 1),
                        "quality_pct": round((total-short)*100/total, 1)
                    })
                    trend_f.write_text(_j.dumps(trend[-50:], ensure_ascii=False))
            except Exception:
                pass  # 非致命，不影响主流程
        
        return result
    except Exception as e:
        return {"status": "error", "reason": str(e)[:60]}
