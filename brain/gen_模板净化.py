"""
gen_模板净化.py — 持续检测模板链并注入反模板质量提升
每3周期扫描海马体，找出模板率最高的维度，注入反模板种子
"""
import json, time, random
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
_HIP_FILE = CLUSTER / "hippocampus_memory.json"
_META_FILE = CLUSTER / ".brain_quality_detection.json"
_RUN_EVERY = 3

# 反模板种子池：真正多样化的内容模式，打破模板惯性
ANTI_TEMPLATE_SEEDS = {
    "预测": [
        "预测不是算命是概率管理：准确的预测系统会输出置信区间而非点估计——\"有70%概率X发生\"比\"X会发生\"更有用",
        "预测与行动之间的反馈延迟越长，校准信号越弱：预测3个月后的结果比预测3天后的结果更容易自我合理化偏差",
        "预测失败的真正价值不在修正预测本身，而在发现预测框架的盲点——系统预测偏差的模式比单次预测正确与否更重要",
        "预测的实用性边界：当预测改变不了任何决策时，预测行为本身就是资源浪费——不为决策服务的预测是噪音",
        "预测的二元陷阱：把连续可能性折叠成二元判断(涨/跌/对/错)丢失了最重要的信息——分布的宽度和形状",
    ],
    "测试": [
        "测试覆盖率40%但关键路径80%——测试的价值不在总量而在风险覆盖精度",
        "测试培养纪律需要的时间窗口：连续14天每日测试后，行为惯性开始固化",
        "测试的沉默成本：修复一个测试发现的问题平均比线上修复便宜7倍——但不测试就是看不见这笔账",
    ],
    "纪律": [
        "纪律的自指悖论：维持纪律本身需要纪律——最难的纪律是\"建立纪律\"的纪律",
        "纪律与创造力的非线性关系：适度的纪律框架使创造力提升3倍，但过于严格的纪律反而降至0.5倍",
        "纪律退化的阈值：连续3次违反无后果后，纪律恢复到初始状态的50%",
    ],
    "对抗稀释": [
        "稀释的临界点：当日志/链/状态的增长速率超过系统消化能力的1.5倍时，有效信息密度加速下降",
        "对抗稀释不是存储问题：即使无限存储，信号/噪音比仍在下降——关键在信噪分离策略",
        "稀释自愈：当信息冗余度<2x时，随机丢失一条关键信息就会级联丢失相关记忆",
    ],
    "对比": [
        "比较的锚定偏差：系统总是用最近的经验作为比较基准，而不是全局最优",
        "跨维度比较的危险：A维的底层策略在B维是高风险的——直接比较分数导致错误迁移",
        "比较的积极用法：不是比谁好，是发现各自盲区——\"你覆盖了X而我没覆盖\"比\"你比我强\"更有价值",
    ],
}

def pulse():
    """检测模板维度并注入反模板种子"""
    now = time.time()
    meta = {}
    if _META_FILE.exists():
        try:
            meta = json.loads(_META_FILE.read_text())
        except:
            meta = {}
    
    last = meta.get("last_run", 0)
    if now - last < _RUN_EVERY * 30:
        return {"status": "cooling", "next_in": int(_RUN_EVERY * 30 - (now - last))}
    
    # 读取海马体
    if not _HIP_FILE.exists():
        return {"status": "skipped", "reason": "no_hip"}
    try:
        import json
        hip = json.loads(_HIP_FILE.read_text())
    except:
        return {"status": "error", "reason": "read_failed"}
    
    chains = hip.get("causal_chains", [])
    if not chains:
        return {"status": "skipped", "reason": "no_chains"}
    
    # 计算每个维度的模板率
    dims = Counter()
    template_dims = Counter()
    for c in chains:
        d = c.get("dimension", "?")
        dims[d] += 1
        content = c.get("content", "")
        # 模板特征：重复结构、长尾空洞
        if any(p in content for p in ["通过", "从而", "促进", "推动", "有助于"]):
            if len(content) > 30 and ("..." in content or content.endswith("。")):
                template_dims[d] += 1
    
    # 找模板率最高的维度（至少10条链）
    dim_template_rates = {}
    for d, total in dims.most_common():
        if total >= 10:
            t_count = template_dims.get(d, 0)
            dim_template_rates[d] = t_count / total
    
    sorted_dims = sorted(dim_template_rates.items(), key=lambda x: -x[1])
    worst_dim = sorted_dims[0] if sorted_dims else (None, 0)
    
    # 注入反模板种子到最差维度
    injected = 0
    for dim, _ in sorted_dims[:2]:
        if dim not in ANTI_TEMPLATE_SEEDS:
            continue
        seeds = ANTI_TEMPLATE_SEEDS[dim]
        random.shuffle(seeds)
        for seed in seeds[:2]:
            try:
                from brain.share import write_chain
                chain = {
                    "src": "模板净化",
                    "rel": f"反模板_{dim}",
                    "dst": dim,
                    "dimension": dim,
                    "content": seed,
                    "strength": 0.9,
                }
                write_chain(chain)
                injected += 1
            except:
                pass
    
    meta["last_run"] = now
    meta["last_worst"] = {"dim": worst_dim[0], "rate": round(worst_dim[1], 2)} if worst_dim[0] else None
    meta["last_injected"] = injected
    meta["dim_template_rates"] = {d: round(r, 2) for d, r in sorted_dims[:5]}
    _META_FILE.write_text(json.dumps(meta, ensure_ascii=False))
    
    return {
        "status": "done",
        "injected": injected,
        "worst_dim": worst_dim,
        "top5": sorted_dims[:3],
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
