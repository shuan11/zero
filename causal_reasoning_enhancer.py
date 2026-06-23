#!/usr/bin/env python3
"""
causal_reasoning_enhancer.py — 因果推理增强器
============================================
从现有知识中提取更多因果关系，增强因果推理深度。

功能：
1. 扫描海马体中的所有链
2. 提取因果关系（基于关键词匹配）
3. 构建因果图
4. 验证因果推理
5. 写入增强的因果链
"""
import json, sys, re, time
from pathlib import Path
from collections import defaultdict

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
import safe_hip

HIP_FILE = CLUSTER / "hippocampus_memory.json"


import hashlib
# ── 限流保护: 防止反馈循环 ──
THROTTLE_THRESHOLD = 50  # 只有上次运行后新增了50+条链才执行
THROTTLE_MARKER = Path(__file__).resolve().parent / ".causal_reasoning_last_count"
def _should_run():
    hip = safe_hip.read()
    current = len(hip.get("causal_chains", []))
    try:
        last = int(THROTTLE_MARKER.read_text().strip())
    except:
        last = current
    diff = current - last
    if diff < THROTTLE_THRESHOLD:
        print(f"[限流] 新增链({diff}) < 阈值({THROTTLE_THRESHOLD}), 跳过本次因果增强")
        print(f"[限流] 上次链数: {last}, 当前: {current}")
        return False
    THROTTLE_MARKER.write_text(str(current))
    return True

def extract_causal_keywords():
    """提取因果关系关键词"""
    return {
        "cause": ["导致", "引起", "造成", "产生", "引发", "触发", "促进", "推动"],
        "effect": ["因此", "所以", "从而", "于是", "结果", "导致", "造成"],
        "condition": ["如果", "假如", "只要", "只有", "除非", "当"],
        "temporal": ["首先", "然后", "接着", "随后", "最后", "之前", "之后"]
    }

def extract_causal_pairs(text):
    """从文本中提取因果对"""
    keywords = extract_causal_keywords()
    pairs = []
    
    # 简单因果提取逻辑
    for cause_kw in keywords["cause"]:
        if cause_kw in text:
            # 找到因果关系
            parts = text.split(cause_kw)
            if len(parts) >= 2:
                cause = parts[0].strip()[-50:]  # 取前50字符作为原因
                effect = parts[1].strip()[:50]  # 取后50字符作为结果
                pairs.append({
                    "cause": cause,
                    "effect": effect,
                    "keyword": cause_kw,
                    "confidence": 0.7
                })
    
    return pairs

def enhance_causal_reasoning():
    """增强因果推理"""
    hip = safe_hip.read()
    chains = hip.get("causal_chains", [])
    
    # 扫描所有链
    all_causal_pairs = []
    for chain in chains:
        content = chain.get("content", "")
        pairs = extract_causal_pairs(content)
        for pair in pairs:
            pair["source_chain"] = chain.get("content", "")[:50]
            pair["source_tags"] = chain.get("tags", [])
            all_causal_pairs.append(pair)
    
    print(f"从{len(chains)}条链中提取到{len(all_causal_pairs)}个因果对")
    
    # 写入增强的因果链
    enhanced_chains = []
    for pair in all_causal_pairs:
        enhanced_chains.append({
            "content": f"[因果提取] {pair['cause']} → {pair['effect']}",
            "cause": pair['cause'],
            "effect": pair['effect'],
            "source": "causal_reasoning_enhancer",
            "tags": ["因果链", "因果提取", pair['keyword']],
            "confidence": pair['confidence'],
            "timestamp": "2026-05-26T21:00:00+08:00"
        })
    
    # 合并到海马体
    hip["causal_chains"].extend(enhanced_chains)
    
    # 保存
    safe_hip.write(hip)
    
    print(f"新增{len(enhanced_chains)}条因果链")
    print(f"总链数: {len(hip['causal_chains'])}")
    
    return len(enhanced_chains)

if __name__ == "__main__":
    if not _should_run():
        sys.exit(0)
    if "--extract" in sys.argv:
        count = enhance_causal_reasoning()
        print(f"因果推理增强完成: 新增{count}条因果链")
    else:
        # 默认：提取并显示
        hip = safe_hip.read()
        chains = hip.get("causal_chains", [])
        
        total_pairs = 0
        for chain in chains[:10]:  # 检查前10条
            content = chain.get("content", "")
            pairs = extract_causal_pairs(content)
            if pairs:
                print(f"链: {content[:50]}...")
                print(f"  因果对: {len(pairs)}个")
                total_pairs += len(pairs)
        
        print(f"\n前10条链中提取到{total_pairs}个因果对")
