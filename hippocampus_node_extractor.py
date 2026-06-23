#!/usr/bin/env python3
"""
hippocampus_node_extractor.py
从 hippocampus_memory.json 的 causal_chains 中提取中文概念节点。

问题: 海马体有1100+链但只有207个节点，链/节点比>5:1。
本脚本从 chains 的 content 字段中提取高频中文关键词/短语 (2-6字)，
按频率排序后写入 nodes 字段。

提取策略:
  - 使用正则找出所有连续中文字符块 (CJK统一表意文字 U+4E00~U+9FFF)
  - 只保留长度为 2~6 字的完整块 (不做滑动窗口，避免大量噪声子串)
  - 按出现频率降序排列
  - 保留旧节点中未在提取结果中出现的条目

用法:
    python3 hippocampus_node_extractor.py

依赖: 仅使用标准库 (json, re, collections, os, shutil, datetime)
"""

import json
import re
import os
import shutil
from collections import Counter
from datetime import datetime, timezone

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "hippocampus_memory.json")
BACKUP_PATH = os.path.join(
    BASE_DIR,
    f"hippocampus_memory_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
)

# ── 提取参数 ──────────────────────────────────────────────
MIN_CHARS = 2   # 最短词长
MAX_CHARS = 6   # 最长词长
MIN_FREQ = 2    # 最低出现次数 (过滤仅出现1次的噪声)


def backup_file(src: str, dst: str) -> bool:
    """备份原文件，保留元数据。"""
    if not os.path.exists(src):
        print(f"[错误] 源文件不存在: {src}")
        return False
    try:
        shutil.copy2(src, dst)
        print(f"[备份] 已复制到: {dst}")
        return True
    except Exception as e:
        print(f"[警告] 备份失败: {e}")
        return False


def extract_chinese_phrases(text: str):
    """
    从文本中提取 2~6 字中文词组。

    策略: 只匹配完整的中文连续字符块，不做滑动窗口。
    - 对于长度在 [MIN_CHARS, MAX_CHARS] 内的完整中文字块，直接收录
    - 长度不足或超过的块跳过
    - 不提取嵌套子串，避免"合作是本质"产生"合作""作是""是本质"等噪声
    """
    # 匹配一个或多个连续中文字符 (CJK统一表意文字)
    chinese_blocks = re.findall(r'[\u4e00-\u9fff]+', text)
    phrases = []
    for block in chinese_blocks:
        blen = len(block)
        if MIN_CHARS <= blen <= MAX_CHARS:
            phrases.append(block)
        # 长度 < MIN_CHARS 或 > MAX_CHARS 的块跳过
    return phrases


def print_top(sorted_items: list, top_n: int = 40):
    """打印频率统计摘要。"""
    print(f"\n  Top {top_n} 高频词组:")
    print(f"  {'频率':>6}  {'词组'}")
    print(f"  {'-'*6}  {'-'*20}")
    for phrase, count in sorted_items[:top_n]:
        print(f"  {count:>6}  {phrase}")
    if len(sorted_items) > top_n:
        print(f"  ... 还有 {len(sorted_items) - top_n} 个词组未显示")


def main():
    print("=" * 65)
    print("  海马体节点提取器 — hippocampus_node_extractor.py")
    print("=" * 65)

    # ── 1. 备份 ────────────────────────────────────────────
    print("\n[1/5] 备份原始文件 ...")
    backup_file(JSON_PATH, BACKUP_PATH)

    # ── 2. 读取 JSON ───────────────────────────────────────
    print("[2/5] 读取 hippocampus_memory.json ...")
    try:
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[错误] 读取失败: {e}")
        return

    chains = data.get("causal_chains", [])
    old_nodes = data.get("nodes", {})

    if not isinstance(chains, list):
        print("[错误] causal_chains 不是列表格式")
        return
    if not isinstance(old_nodes, dict):
        old_nodes = {}

    print(f"  causal_chains 数量: {len(chains)}")
    print(f"  现有 nodes 数量: {len(old_nodes)}")

    # ── 3. 提取中文词组 ────────────────────────────────────
    print(f"\n[3/5] 从 causal_chains 的 content 中提取中文词组 "
          f"({MIN_CHARS}-{MAX_CHARS}字, 完整块模式) ...")

    all_phrases = []
    empty_content = 0
    for idx, chain in enumerate(chains):
        content = chain.get("content", "")
        if not content:
            empty_content += 1
            continue
        phrases = extract_chinese_phrases(content)
        all_phrases.extend(phrases)

    print(f"  空 content 的链: {empty_content}")
    print(f"  提取到词组实例总数: {len(all_phrases)}")

    # ── 4. 频率统计 ────────────────────────────────────────
    print("\n[4/5] 统计词频并排序 ...")
    counter = Counter(all_phrases)
    total_unique = len(counter)
    sorted_phrases = counter.most_common()  # [(phrase, count), ...]

    print(f"  唯一词组数量: {total_unique}")

    # 过滤低频词组
    if MIN_FREQ > 1:
        sorted_phrases = [(p, c) for p, c in sorted_phrases if c >= MIN_FREQ]
        print(f"  过滤后 (频率>={MIN_FREQ}): {len(sorted_phrases)} 个词组")

    print_top(sorted_phrases, top_n=40)

    # 词长分布统计
    if sorted_phrases:
        len_dist = Counter()
        for phrase, _ in sorted_phrases:
            len_dist[len(phrase)] += 1
        print(f"\n  词长分布 (过滤后):")
        for length in sorted(len_dist):
            print(f"    {length}字: {len_dist[length]} 个词组")

    # ── 5. 构建并写入新 nodes ──────────────────────────────
    print("\n[5/5] 更新 nodes 字段 (保留旧节点, 合并新提取)...")

    now = datetime.now(timezone.utc).astimezone().isoformat()
    new_nodes = {}

    # 5a. 来自提取结果的: 使用新频率
    for phrase, count in sorted_phrases:
        old_info = old_nodes.get(phrase, {})
        new_nodes[phrase] = {
            "count": count,
            "first_seen": old_info.get("first_seen", now),
            "tag": old_info.get("tag", phrase),
            "dimension": "auto_extracted"
        }

    # 5b. 旧节点中未在提取结果中的: 保留原样
    preserved = 0
    for phrase, info in old_nodes.items():
        if phrase not in new_nodes:
            new_nodes[phrase] = info
            preserved += 1

    # 5c. 按 count 降序排序
    sorted_nodes = dict(
        sorted(new_nodes.items(), key=lambda x: x[1]["count"], reverse=True)
    )

    # 5d. 更新 stats
    if "stats" not in data or not isinstance(data["stats"], dict):
        data["stats"] = {}
    data["stats"]["node_count"] = len(sorted_nodes)
    data["stats"]["nodes"] = len(sorted_nodes)
    data["stats"]["extracted_phrases_total"] = total_unique
    data["stats"]["last_node_extraction"] = now
    data["stats"]["chains_at_extraction"] = len(chains)

    # 5e. 写入文件
    data["nodes"] = sorted_nodes

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"  已写入: {JSON_PATH}")

    # ── 最终报告 ───────────────────────────────────────────
    added = len(sorted_nodes) - len(old_nodes)
    chain_node_ratio = len(chains) / max(len(sorted_nodes), 1)

    print(f"\n{'=' * 65}")
    print(f"  提取完成!")
    print(f"  ┌──────────────────────┬────────────┐")
    print(f"  │ 指标                │ 数值       │")
    print(f"  ├──────────────────────┼────────────┤")
    print(f"  │ 原节点数            │ {len(old_nodes):>7}     │")
    print(f"  │ 现节点数            │ {len(sorted_nodes):>7}     │")
    print(f"  │ 新增节点            │ {added:>7}     │")
    print(f"  │ 保留旧节点(未提取)  │ {preserved:>7}     │")
    print(f"  │ 链数                │ {len(chains):>7}     │")
    print(f"  │ 链/节点比           │ {chain_node_ratio:>9.2f}  │")
    print(f"  │ 提取出的唯一词组    │ {total_unique:>7}     │")
    print(f"  └──────────────────────┴────────────┘")
    print(f"\n  备份: {BACKUP_PATH}")
    print(f"{'=' * 65}")


if __name__ == "__main__":
    main()
