#!/usr/bin/env python3
"""
classify_chains.py — 自动分类海马体中未标记的因果链
根据tag和内容将1673条"未分类"链映射到19维度之一
"""
import json
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIPPOCAMPUS = CLUSTER / "hippocampus_memory.json"
BKP = CLUSTER / "hippocampus_memory.json.pre_classify"

# 维度标签映射表
DIMENSION_KEYWORDS = {
    "一元化": ["一元", "统一", "凝聚", "归一", "本原", "合", "太极"],
    "万象化": ["万象", "多样", "多元", "展开", "发散", "万有"],
    "光爱": ["光爱", "爱", "慈悲", "善", "合作", "共生", "终极"],
    "进化": ["进化", "演化", "适应", "突变", "自然选择", "适者"],
    "超感": ["超感", "直觉", "预感", "洞察", "涌现", "第六感"],
    "时间论": ["时间", "过去", "未来", "历史", "传承", "时代", "永恒", "时刻"],
    "宇宙轮": ["宇宙", "星系", "熵", "热寂", "稀释", "虚空", "无限", "万物"],
    "记忆": ["记忆", "海马", "因果链", "hippocampus", "存储", "回忆"],
    "元神": ["元神", "元认知", "自指", "自我", "意识", "觉醒", "灵", "反思"],
    "查缺补漏": ["查缺", "补漏", "缺口", "短板", "gap", "漏洞", "不足", "缺失"],
    "触类旁通": ["触类", "旁通", "类比", "联想", "举一", "反三", "迁移"],
    "举一反三": ["举一反三", "扩展", "推广", "泛化", "一般化"],
    "教员": ["教员", "教师", "教学", "指导", "纠正", "纠偏", "学习", "教导"],
    "无师自通": ["自学习", "自学", "自主", "自进化", "自修改", "自改进", "autodidact"],
    "超级直觉": ["超直觉", "深层", "本质", "根本", "第一性"],
    "光": ["光", "照明", "照亮", "光明", "启示"],
    "因果": ["因果", "因", "果", "因为", "所以", "导致", "引发"],
    "工程": ["工程", "代码", "实现", "模块", "函数", "部署", "写", "编程"],
    "感知": ["感知", "感觉", "感受", "体验", "观察", "sense"],
}

def classify_chain(chain):
    """根据tag和content判断最匹配的维度"""
    content = (chain.get("content", "") or "") + " " + " ".join(chain.get("tags", []) or [])
    content_lower = content.lower()
    
    # 计算每个维度的匹配分数
    scores = {}
    for dim, keywords in DIMENSION_KEYWORDS.items():
        score = sum(keyword.lower() in content_lower for keyword in keywords)
        if score > 0:
            scores[dim] = score
    
    if not scores:
        return "未分类"  # 仍然无法分类
    
    # 返回分数最高的维度
    return max(scores, key=scores.get)

def main():
    if not HIPPOCAMPUS.exists():
        print(f"海马体文件不存在: {HIPPOCAMPUS}")
        return
    
    # 备份
    data = json.loads(HIPPOCAMPUS.read_text(encoding="utf-8"))
    chains = data.get("causal_chains", []) if isinstance(data, dict) else data if isinstance(data, list) else []
    
    print(f"总链数: {len(chains)}")
    
    # 统计和分类
    classified = 0
    already_classified = 0
    for i, chain in enumerate(chains):
        tags = chain.get("tags", []) or []
        if isinstance(tags, list) and "未分类" in tags and len(tags) == 1:
            # 这条链只有"未分类"标签，需要分类
            best_dim = classify_chain(chain)
            if best_dim != "未分类":
                chain["tags"] = [best_dim] + [t for t in tags if t != "未分类"]
                chain["dimension"] = best_dim
                classified += 1
        elif isinstance(tags, list) and "未分类" in tags:
            # 有未分类标签但还有其他标签
            chain["tags"] = [t for t in tags if t != "未分类"]
            already_classified += 1
        elif "dimension" not in chain or not chain.get("dimension"):
            # 没有维度信息
            best_dim = classify_chain(chain)
            chain["dimension"] = best_dim
            chain.setdefault("tags", []).append(best_dim)
            classified += 1
    
    print(f"已分类: {classified}")
    print(f"清除未分类标签: {already_classified}")
    
    # 保存
    if classified > 0 or already_classified > 0:
        with open(BKP, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        with open(HIPPOCAMPUS, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        print(f"已保存分类结果 (备份: {BKP})")
    else:
        print("无需分类")

if __name__ == "__main__":
    main()
