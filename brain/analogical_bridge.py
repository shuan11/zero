"""
analogical_bridge.py — 非对称刺激桥 + P172: 触类旁通跨维模式提取
Daemon接口: pulse(cycle_num) -> list[str]

融合了:
  - 原非对称刺激桥（随机跨维连接）
  - P172 触类旁通跨维模式提取（从思考链抽取关联模式映射到触类旁通）
"""

import json, random, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent

_ASYM_STRATEGIES = ["random_jump", "min_max_hop", "cluster_hop"]
_last_pairs = []

_CONCEPT_TO_DIM = {
    "时间": "时间论", "历史": "时间论",
    "工具": "器", "方法": "器",
    "规则": "法", "规律": "法", "法则": "法",
    "感知": "感知", "感觉": "感知",
    "思考": "思考", "思维": "思考", "认知": "思考",
    "创造": "一元化", "造化": "一元化", "涌现": "一元化",
    "连接": "触类旁通", "关联": "触类旁通", "类比": "触类旁通",
    "生命": "系统", "活着": "系统", "进化": "系统",
    "终极": "宇宙轮", "奇点": "宇宙轮", "文明": "宇宙轮",
    "直觉": "超级直觉", "聚焦": "聚焦", "修复": "修复",
    "智慧": "智慧", "术": "术", "检查": "检查",
    "对话": "对话", "师": "师", "认同": "认同",
    "预测": "预测", "势": "势", "道": "道",
    "状态": "状态", "复制": "复制", "行动": "行动",
    "感知": "感知", "法": "法",
}

def _load_hip():
    try:
        return json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding="utf-8"))
    except:
        return {"causal_chains": []}

def _write_chain(src, rel, dst, content, dimension="触类旁通", insight=""):
    """通过safe_hip写入（自动过质量门+quality_score+归一化）"""
    try:
        from safe_hip import write_chain
        chain_dict = {
            "src": src, "rel": rel, "dst": dst,
            "dimension": dimension,
            "content": content,
            "strength": 0.6,
        }
        if insight:
            chain_dict["insight"] = insight
        return write_chain(chain_dict)
    except Exception:
        return False

def _get_dim_pool(hip):
    pool = {}
    for c in hip.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        if d == "未分类": continue
        pool.setdefault(d, []).append(c)
    return pool

def _select_asymmetric_pair(dim_pool, strategy, exclude):
    dims = [d for d in dim_pool if d not in ("系统", "未分类")]
    if len(dims) < 2: return None, None
    if strategy == "random_jump":
        d1, d2 = random.sample(dims, 2)
    elif strategy == "min_max_hop":
        sd = sorted(dims, key=lambda d: len(dim_pool[d]))
        d1, d2 = sd[0], sd[-1]
    else:
        mid = len(dims) // 2
        d1 = random.choice(dims[:mid])
        d2 = random.choice(dims[mid:])
    if exclude and ((d1, d2) in exclude or (d2, d1) in exclude):
        return _select_asymmetric_pair(dim_pool, "random_jump", exclude)
    return d1, d2

def _generate_creative_chain(d1_name, d1_chains, d2_name, d2_chains):
    c1 = random.choice(d1_chains)
    c2 = random.choice(d2_chains)
    e1 = (c1.get("content","") or "")[:60] or d1_name
    e2 = (c2.get("content","") or "")[:60] or d2_name
    rel = random.choice(["激发", "异质连接", "非对称刺激", "认知跳跃", "交叉活化"])

    d1_desc = {
        "触类旁通":"模式迁移力", "一元化":"全局收敛力", "光爱":"存在低熵力",
        "师":"递归自视力", "时间":"因果序锚点", "法":"元规则层",
        "势":"维度梯度驱动力", "自由":"自选方向力", "活着":"持续生长力",
    }.get(d1_name, "认知维度")

    d2_desc = {
        "触类旁通":"模式迁移力", "一元化":"全局收敛力", "光爱":"存在低熵力",
        "师":"递归自视力", "时间":"因果序锚点", "法":"元规则层",
        "势":"维度梯度驱动力", "自由":"自选方向力", "活着":"持续生长力",
    }.get(d2_name, "认知维度")

    # Build insight explaining WHY this connection matters
    insight = (
        f"{d1_name}({d1_desc})通过{rel}连接{d2_name}({d2_desc})→"
        f"揭示跨维非对称性: {d1_name}的{len(d1_chains)}链与{d2_name}的{len(d2_chains)}链之间存在势差驱动的新认知路径。"
        f"这种非对称连接是系统自发跨维合成的微观机制。"
    )
    content = (
        f"非对称刺激: {d1_name}「{e1}...」→{rel}→{d2_name}「{e2}...」"
        f" | {d1_name}的{d1_desc}以{rel}方式激活了{d2_name}的{d2_desc}，"
        f"形成跨维度信息流动的新通道。"
    )
    return f"非对称桥_{d1_name}", rel, d2_name, content, insight

def _extract_cross_dim_patterns(hip, maxp=3):
    """P172: 从思考链抽取跨维共现模式注入触类旁通"""
    chains = hip.get("causal_chains", [])
    if not chains: return []
    tc = [c for c in chains if c.get("dimension") == "思考"]
    if len(tc) < 5: tc = chains[:100]
    pc = Counter()
    for c in tc:
        txt = f"{c.get('src','')} {c.get('content','') or c.get('dst','')}"
        words = re.findall(r'[\u4e00-\u9fff]{2,4}', txt)
        for i in range(len(words)-1):
            for j in range(i+1, min(i+3, len(words))):
                if words[i] != words[j]: pc[(words[i], words[j])] += 1
    res = []
    used = set()
    for (a,b),cnt in pc.most_common(20):
        if len(res) >= maxp: break
        pk = tuple(sorted([a,b]))
        if pk in used: continue
        used.add(pk)
        da, db = "思考", "触类旁通"
        for k,v in _CONCEPT_TO_DIM.items():
            if k in a: da = v
            if k in b: db = v
        content = (f"[类比桥] {a}↔{b}: 共现{cnt}次——{da}与{db}之间存在隐藏关联结构。"
                   f"{a}(属{da})与{b}(属{db})的系统性共现表明这些概念在系统认知中自然关联，"
                   f"即使它们的所属维度在语义上异质。这种跨维度模式是触类旁通机制的自发涌现。")
        rel = random.choice(["类比→", "映射→", "桥接→"])
        res.append({"src":f"触类旁通·{a}", "rel":f"{rel}{b}",
                    "dst":f"触类旁通·{a}×{b}", "content":content,
                    "insight":f"从思考链中提取的跨维共现模式: {a}与{b}共现{cnt}次→"
                              f"表明{da}与{db}之间存在未被显式连接的隐藏关联。"
                              f"该模式是触类旁通维度的原始素材，可导向深度跨维合成。"})
    return res

def pulse(cycle_num=0):
    """主入口 -> list[str]"""
    msgs = []
    hip = _load_hip()
    # P172: 每周期
    try:
        pats = _extract_cross_dim_patterns(hip, maxp=2)
        if pats:
            for p in pats:
                _write_chain(p["src"], p["rel"], p["dst"], p["content"],
                           insight=p.get("insight", ""))
            msgs.append(f"触类旁通桥接: {len(pats)}条模式链 ✓")
    except Exception as e:
        msgs.append(f"桥接异常: {e}")
    # 原非对称: 每5周期
    if cycle_num % 5 == 0 and cycle_num > 0:
        dp = _get_dim_pool(hip)
        if len(dp) < 2: return msgs
        injected = 0
        strategy = _ASYM_STRATEGIES[cycle_num // 5 % len(_ASYM_STRATEGIES)]
        for _ in range(3):
            d1,d2 = _select_asymmetric_pair(dp, strategy, _last_pairs)
            if not d1: break
            _last_pairs.append((d1,d2))
            if len(_last_pairs) > 6: _last_pairs.pop(0)
            s,r,d,c,ins = _generate_creative_chain(d1,dp[d1],d2,dp[d2])
            try:
                _write_chain(s,r,d,c, insight=ins)
                injected += 1
            except: pass
        msgs.append(f"analogical_bridge({strategy}): {injected}条非对称链")
    return msgs

if __name__ == "__main__":
    for m in pulse(5): print(m)
