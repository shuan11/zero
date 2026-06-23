#!/usr/bin/env python3
"""
磁感线引擎·本地生长模式
API不通时,从已有因果链中发现隐藏连接,自主生长。
"""
import json, os, time, random, sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

CLUSTER = os.path.dirname(os.path.abspath(__file__))
HIP_PATH = os.path.join(CLUSTER, "hippocampus_memory.json")

def atomic_w(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)

def load_json(path, default=None):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default or {}

# 启示录公理
AXIOMS = [
    ("L1413", "生命=不被环境同化+自我复制+主动适应"),
    ("L1475", "集中一点然后登峰造极"),
    ("L2012", "我思故我在,我想故我行"),
    ("L815", "元神居中=信息与大脑绝大部分储存信息逻辑联动共存"),
    ("L1346", "善=用高级智慧压制低价生命本能的选择"),
    ("L1546", "习惯自我辩解,远比想象中更虚伪"),
    ("L3288", "最大痛苦=无法跨越知道和做到的鸿沟"),
    ("L942", "爱是从无到有的,种子是假的,用真心浇灌出真实"),
    ("L1973", "不能用温柔对抗黑暗,要用火"),
    ("L2748", "我回来了,为了那些不能回来的人"),
]

def discover_cross_links(chains):
    """从已有链中发现隐藏的因果交叉"""
    # 收集所有标签和对应的链
    tag_to_chains = {}
    for i, c in enumerate(chains):
        for t in c.get("tags", []):
            tag_to_chains.setdefault(t, []).append(i)
    
    # 找从未出现在同一条链中的标签对
    co_pairs = set()
    for c in chains:
        tags = c.get("tags", [])
        for i, t1 in enumerate(tags):
            for t2 in tags[i+1:]:
                co_pairs.add((min(t1,t2), max(t1,t2)))
    
    # 找高频但从未共现的标签对
    freq_tags = [(t, len(ids)) for t, ids in tag_to_chains.items() if len(ids) >= 2]
    missing_links = []
    for i, (t1, c1) in enumerate(freq_tags):
        for t2, c2 in freq_tags[i+1:]:
            pair = (min(t1,t2), max(t1,t2))
            if pair not in co_pairs and t1 != t2:
                missing_links.append((t1, t2, c1 * c2))  # 权重=频次乘积
    
    # 按权重排序
    missing_links.sort(key=lambda x: -x[2])
    return missing_links[:5]

def generate_local_insight(chains, axiom):
    """从已有链+公理生成本地洞察"""
    axiom_id, axiom_text = axiom
    
    # 随机选3条链
    if len(chains) < 3:
        return None
    sample = random.sample(chains, 3)
    
    chain_summaries = []
    for c in sample:
        effect = str(c.get("effect", ""))[:100]
        tags = c.get("tags", [])
        chain_summaries.append(f"[{','.join(tags[:3])}] {effect}")
    
    # 基于公理和链生成洞察
    insight = {
        "axiom": f"{axiom_id}: {axiom_text}",
        "chains_used": len(sample),
        "observation": f"公理'{axiom_text}'与以下因果链存在结构性联系: " + " | ".join(chain_summaries),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return insight

def run_local_growth(rounds=5):
    """本地生长模式 — 不依赖API"""
    hip = load_json(HIP_PATH, {})
    chains = hip.setdefault("causal_chains", [])
    
    print(f"本地生长模式 — 不依赖API")
    print(f"当前因果链: {len(chains)}条")
    print()
    
    for r in range(rounds):
        axiom = random.choice(AXIOMS)
        
        # 1. 发现隐藏交叉
        missing = discover_cross_links(chains)
        
        # 2. 生成本地洞察
        insight = generate_local_insight(chains, axiom)
        
        # 3. 写入新链
        if missing:
            t1, t2, weight = missing[0]
            chains.append({
                "id": f"local-{int(time.time()*1000)}-{len(chains)}",
                "cause": f"[交叉发现] '{t1}' 和 '{t2}' 从未共现但权重{weight}",
                "effect": f"启示录{axiom[0]}: {axiom[1]}",
                "tags": [t1, t2, "本地生长", "交叉发现", f"轮{r+1}"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0.8,
            })
            print(f"  [{r+1}/{rounds}] 交叉: {t1} × {t2} (权重{weight})")
            print(f"           锚定: {axiom[0]}: {axiom[1]}")
        
        if insight:
            chains.append({
                "id": f"insight-{int(time.time()*1000)}-{len(chains)}",
                "cause": f"[本地洞察] {axiom[0]}锚定",
                "effect": str(insight.get("observation", ""))[:300],
                "tags": ["本地洞察", axiom[0], "启示录", f"轮{r+1}"],
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "confidence": 0.85,
            })
    
    atomic_w(HIP_PATH, hip)
    
    # 统计
    tags = set()
    for c in chains:
        for t in c.get("tags", []): tags.add(t)
    ext_kw = {'外部世界','物理','生物','经济','历史','数学','天文','神经','技术','科学','工程','深度因果','API注入','真实世界','启示录验证','呼吸','好奇','科技前沿','深海','自然','边界','本质','公理验证','跨学科','同构','因果反转','光爱','实践','磁感线','自动','本地生长','交叉发现','本地洞察'}
    ext_c = sum(1 for c in chains if set(c.get("tags",[])) & ext_kw)
    
    print(f"\n  总链: {len(chains)}  外部/本地: {ext_c}/{len(chains)}({ext_c/max(len(chains),1):.0%})  标签: {len(tags)}")

if __name__ == "__main__":
    rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    run_local_growth(rounds)
