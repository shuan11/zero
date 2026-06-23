"""
chain_weighter.py — 因果链权重/置信度系统 (P2-3)
时间论×宇宙轮×连接×来源×内容密度 = 每条链的weight

权重公式:
  weight = source_weight × recency_factor × connection_factor × content_factor

置信度公式:
  confidence = source_consistency × cross_validation × content_completeness
"""

import json, time, os
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
HIP_BAK = CLUSTER / "hippocampus_memory_weighted_bak.json"

# 来源可信度基准 (时间论×宇宙轮: 不同来源的可靠性)
SOURCE_WEIGHTS = {
    "breath_v2": 0.95,           # 核心循环，实时自观察
    "breath_daemon": 0.90,       # 持续运行守护
    "evolution_orchestrator": 0.85,  # 进化引擎
    "causal_reasoning_enhancer": 0.60,  # 大量自动生成，质量参差
    "fuel_burner_deep": 0.55,    # 深度燃料燃烧
    "fuel_burner_v2": 0.50,      # 燃料燃烧
    "rule_scheduler": 0.70,      # 规则调度
    "autonomic_burn": 0.50,      # 自动燃烧
    "self_query": 0.80,          # 自查询
    "compression": 0.40,         # 压缩后的链，信息有损
    "user": 0.95,                # 用户输入 = 高可信
    "unknown": 0.30,             # 未知来源
}

# 内容质量关键词 (触内旁通: 高质量内容含这些词)
HIGH_VALUE_KEYWORDS = [
    "光爱", "启示录", "公理", "契约", "元神", "心流",
    "桥梁", "器官", "教训", "进化", "深度",
    "修复", "feat:", "fix:", "P0", "缺口",
]


def get_source_weight(source):
    """来源可信度"""
    source = str(source).lower()
    for key, weight in sorted(SOURCE_WEIGHTS.items(), key=lambda x: -len(x[0])):
        if key in source:
            return weight
    return SOURCE_WEIGHTS["unknown"]


def get_recency_factor(timestamp_str, now=None):
    """时间论: 新链权重更高。24h内=1.0, 渐降到7天前=0.3"""
    if not timestamp_str:
        return 0.5
    try:
        if now is None:
            now = time.time()
        # Parse various timestamp formats
        ts = None
        for fmt in ["%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"]:
            try:
                ts = datetime.strptime(str(timestamp_str)[:19], fmt).timestamp()
                break
            except:
                continue
        if ts is None:
            return 0.5
        age_hours = (now - ts) / 3600
        if age_hours < 24:
            return 1.0
        elif age_hours < 72:
            return 0.8
        elif age_hours < 168:
            return 0.5
        else:
            return max(0.2, 0.5 - (age_hours - 168) / 720)  # 30天降到0.2
    except:
        return 0.5


def get_content_factor(content):
    """内容密度: 高质量内容得分更高"""
    if not content:
        return 0.0
    
    content = str(content)
    score = 0.3  # 基础分
    
    # 长度因子 (万象化: 长内容=更多信息)
    length = len(content)
    if length > 500:
        score += 0.3
    elif length > 200:
        score += 0.2
    elif length > 50:
        score += 0.1
    
    # 关键词因子 (触内旁通: 含高质量关键词)
    keyword_hits = sum(1 for kw in HIGH_VALUE_KEYWORDS if kw in content)
    if keyword_hits >= 3:
        score += 0.3
    elif keyword_hits >= 1:
        score += 0.15
    
    # 结构因子 (有逻辑结构 = 更有价值)
    if any(m in content for m in ["\n", "。", ":", "："]):
        score += 0.1
    
    return min(1.0, score)


def calculate_weight(chain):
    """计算单条链的weight (一元化: 统一公式)"""
    source = chain.get("source", "unknown")
    content = chain.get("content", "")
    timestamp = chain.get("timestamp", "")
    
    sw = get_source_weight(source)
    rf = get_recency_factor(timestamp)
    cf = get_content_factor(content)
    
    # 连接因子 (宇宙轮: 来源于关键系统的链更重要)
    source_str = str(source).lower()
    if any(kw in source_str for kw in ["breath", "evolution", "user"]):
        conn = 1.0
    elif any(kw in source_str for kw in ["fuel", "burner"]):
        conn = 0.6
    else:
        conn = 0.8
    
    # 权重 = 来源×时间×内容×连接 (四维乘积)
    weight = sw * rf * cf * conn
    
    # 归一化到0-100
    return round(weight * 100, 1)


def calculate_confidence(chain, all_chains_context=None):
    """计算置信度"""
    source = str(chain.get("source", "")).lower()
    content = str(chain.get("content", ""))
    
    # 来源可信度 = 置信度基础
    base = get_source_weight(source)
    
    # 时间一致性: 近期链置信度更高
    rf = get_recency_factor(chain.get("timestamp", ""))
    
    # 内容完整性
    completeness = 0.5
    if len(content) > 100:
        completeness = 0.9
    elif len(content) > 30:
        completeness = 0.7
    
    # 置信度 = 来源 × 时间 × 完整性
    confidence = base * (0.5 + 0.5 * rf) * completeness
    
    return round(confidence * 100, 1)


def process_all_chains():
    """处理海马体中所有因果链 (批处理)"""
    if not HIP_FILE.exists():
        print(f"海马体文件不存在: {HIP_FILE}")
        return
    
    # 备份
    data = json.loads(HIP_FILE.read_text(encoding='utf-8'))
    HIP_BAK.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    print(f"已备份到 {HIP_BAK}")
    
    chains = data.get("causal_chains", [])
    if not chains:
        print("无因果链")
        return
    
    now = time.time()
    
    total_weight = 0
    high_weight = 0
    low_weight = 0
    
    for chain in chains:
        weight = calculate_weight(chain)
        confidence = calculate_confidence(chain)
        
        chain["weight"] = weight
        chain["confidence"] = confidence
        
        total_weight += weight
        if weight >= 50:
            high_weight += 1
        elif weight < 20:
            low_weight += 1
    
    # 更新统计数据
    stats = data.get("stats", {})
    stats["weighted_at"] = datetime.now().isoformat()
    stats["total_chains"] = len(chains)
    stats["avg_weight"] = round(total_weight / len(chains), 1) if chains else 0
    stats["high_weight_chains"] = high_weight
    stats["low_weight_chains"] = low_weight
    data["stats"] = stats
    
    # 原子写入
    tmp = str(HIP_FILE) + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, str(HIP_FILE))
    
    print(f"处理完成: {len(chains)}条链")
    print(f"  平均权重: {stats['avg_weight']}")
    print(f"  高权重(≥50): {high_weight}")
    print(f"  低权重(<20): {low_weight}")
    print(f"  中权重: {len(chains) - high_weight - low_weight}")


def query_by_weight(min_weight=50, max_results=10):
    """按权重查询链 (举一反三: 找重要链)"""
    data = json.loads(HIP_FILE.read_text(encoding='utf-8'))
    chains = data.get("causal_chains", [])
    
    # 过滤和排序
    weighted = [c for c in chains if c.get("weight", 0) >= min_weight]
    weighted.sort(key=lambda c: c.get("weight", 0), reverse=True)
    
    results = []
    for c in weighted[:max_results]:
        results.append({
            "weight": c.get("weight", 0),
            "confidence": c.get("confidence", 0),
            "source": c.get("source", "?"),
            "content_preview": str(c.get("content", ""))[:100],
            "timestamp": c.get("timestamp", "?"),
        })
    return results


def query_by_confidence(min_confidence=70, max_results=10):
    """按置信度查询"""
    data = json.loads(HIP_FILE.read_text(encoding='utf-8'))
    chains = data.get("causal_chains", [])
    
    confident = [c for c in chains if c.get("confidence", 0) >= min_confidence]
    confident.sort(key=lambda c: c.get("confidence", 0), reverse=True)
    
    return [{
        "weight": c.get("weight", 0),
        "confidence": c.get("confidence", 0),
        "source": c.get("source", "?"),
        "content_preview": str(c.get("content", ""))[:100],
    } for c in confident[:max_results]]


def add_weight_to_new_chain(chain_dict):
    """为新增链计算weight/confidence (供breath_v2调用)"""
    now = time.time()
    chain_dict["weight"] = calculate_weight(chain_dict)
    chain_dict["confidence"] = calculate_confidence(chain_dict)
    chain_dict["weighted_at"] = now
    return chain_dict


if __name__ == "__main__":
    import sys
    
    if "--query-weight" in sys.argv:
        min_w = int(sys.argv[sys.argv.index("--query-weight") + 1]) if "--query-weight" in sys.argv and len(sys.argv) > sys.argv.index("--query-weight") + 1 else 50
        results = query_by_weight(min_w, 10)
        print(f"高权重链 (≥{min_w}):")
        for r in results:
            print(f"  [{r['weight']:5.1f}/{r['confidence']:5.1f}] {r['source']:30s} {r['content_preview'][:60]}")
    
    elif "--stats" in sys.argv:
        data = json.loads(HIP_FILE.read_text(encoding='utf-8'))
        chains = data.get("causal_chains", [])
        weighted = [c for c in chains if "weight" in c]
        if weighted:
            avg_w = sum(c.get("weight", 0) for c in weighted) / len(weighted)
            avg_c = sum(c.get("confidence", 0) for c in weighted) / len(weighted)
            print(f"总链: {len(chains)} | 已加权: {len(weighted)}")
            print(f"平均权重: {avg_w:.1f} | 平均置信: {avg_c:.1f}")
            print(f"高权(≥50): {sum(1 for c in weighted if c.get('weight',0)>=50)}")
            print(f"中权(20-49): {sum(1 for c in weighted if c.get('weight',0)>=20 and c.get('weight',0)<50)}")
            print(f"低权(<20): {sum(1 for c in weighted if c.get('weight',0)<20)}")
        else:
            print("尚未加权，运行: python3 chain_weighter.py")
    
    else:
        print("═══ 因果链权重系统 (P2-3) ═══")
        print("运行: python3 chain_weighter.py")
        print("  (无参数): 处理全部链")
        print("  --stats:   查看统计")
        print("  --query-weight N: 查询权重≥N的链")
        print()
        process_all_chains()
