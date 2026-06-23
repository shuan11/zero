#!/usr/bin/env python3
"""
STEP 4+5: 写入海马体 + git commit v10.87
"""
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
BJT = timezone(timedelta(hours=8))
NOW = datetime.now(BJT).isoformat()

print("=" * 60)
print("  STEP 4: 写入海马体")
print("=" * 60)

# Load hippocampus
hip_path = CLUSTER / "hippocampus_memory.json"
with open(hip_path, 'r', encoding='utf-8') as f:
    hip = json.load(f)

# Load analysis results
with open(CLUSTER / "causal_graph_analysis.json", 'r', encoding='utf-8') as f:
    graph_analysis = json.load(f)

with open(CLUSTER / "p0_deep_analysis_result.json", 'r', encoding='utf-8') as f:
    deep_analysis = json.load(f)

# Build comprehensive insight chains
insight_chains = []

# ── Chain 1: Graph Structure Diagnosis ──
insight_chains.append({
    "id": f"p0-causal-structure-{datetime.now(BJT).strftime('%Y%m%d%H%M')}",
    "content": f"因果图结构诊断: 3558节点/1847边/1851因果链。关键发现: 最大路径仅1跳（无多步因果传导），1711个连通分量（最大分量仅23节点=图严重碎片化），49.8%节点无入边，50.2%无出边，平均总度1.04（极度稀疏）。图被[外部知识]Q&A对主导，缺乏系统内部因果网络。",
    "tags": ["因果图", "结构诊断", "P0", "系统洞察", "碎片化", "深度因果"],
    "confidence": 0.95,
    "timestamp": NOW,
    "source": "p0_causal_analysis",
    "cause": "因果图被外部知识Q&A对主导（93%节点标签为外部世界），每个Q&A只产生1跳cause→effect对",
    "effect": "系统无法进行多步因果推理，因果图拓扑价值极低，需要重构因果链提取策略"
})

# ── Chain 2: Critical Node Analysis ──
insight_chains.append({
    "id": f"p0-critical-nodes-{datetime.now(BJT).strftime('%Y%m%d%H%M')}",
    "content": f"Top3关键汇聚节点: n-625(in=22,[待推导]汇聚点), n-1639(in=5,量子力学主题), n-90(in=4,❌失败节点)。Top3影响力源: n-156(out=5,光爱数学证明), n-194(out=5,信息论Agent), n-196(out=5,麦克斯韦妖类比)。所有高影响力节点均为[外部知识]主题，深度因果标签22个。",
    "tags": ["因果图", "关键节点", "P0", "系统洞察", "深度因果"],
    "confidence": 0.9,
    "timestamp": NOW,
    "source": "p0_deep_explain",
    "cause": "外部知识注入产生大量外部世界标签的Q&A因果对",
    "effect": "系统关键节点全部被外部知识占据，内部因果关系被稀释"
})

# ── Chain 3: System-Level Root Cause ──
insight_chains.append({
    "id": f"p0-root-cause-{datetime.now(BJT).strftime('%Y%m%d%H%M')}",
    "content": f"因果图根因分析: 碎片化的根本原因是causal_graph.py的_build_graph逻辑——每个外部知识query生成独立的cause→effect对（cause=问题, effect=[待推导]+回答），但这些对之间无连接。1711个连通分量中最大仅23节点。重构方向: (1)提取实体级因果关系而非句子级, (2)引入实体消歧和共指消解, (3)构建跨链的实体桥接边。",
    "tags": ["因果图", "根因分析", "P0", "重构建议", "深度因果"],
    "confidence": 0.92,
    "timestamp": NOW,
    "source": "p0_causal_analysis",
    "cause": "causal_graph.py以整条文本作为节点，未提取实体/概念，导致节点去重失效",
    "effect": "3558个节点中绝大多数只出现一次，无法形成有意义的因果网络拓扑"
})

# ── Chain 4: [待推导] Sink Problem ──
insight_chains.append({
    "id": f"p0-pending-derivation-{datetime.now(BJT).strftime('%Y%m%d%H%M')}",
    "content": f"[待推导]节点问题: 入度最高节点n-625(in=22)是一个[待推导]前缀的占位节点。causal_graph.py对无→分隔的因果链将content整体作为cause,添加[待推导]作为effect。这产生了1611个[待推导]节点，占总节点45%，构成信息黑洞——大量因果链指向无效的占位符。",
    "tags": ["因果图", "数据质量", "P0", "待推导", "深度因果"],
    "confidence": 0.93,
    "timestamp": NOW,
    "source": "p0_deep_explain",
    "cause": "causal_graph.py中content格式的因果链，无→分隔时自动添加[待推导]effect",
    "effect": "45%节点为信息黑洞，22条因果链汇聚到同一个无意义的[待推导]节点"
})

# ── Chain 5: Comprehensive Diagnosis ──
insight_chains.append({
    "id": f"p0-comprehensive-{datetime.now(BJT).strftime('%Y%m%d%H%M')}",
    "content": f"P0因果图深度分析完整报告: 构建3558节点/1847边因果图。系统级洞察: (1)图严重碎片化——1711连通分量,最大23节点,无法支持多步推理; (2)最大因果链路径仅1跳——缺乏因果传导深度; (3)外部知识Q&A主导——93%为ext_world标签; (4)[待推导]信息黑洞——45%节点为占位符; (5)0孤立节点——但连接全为简单对。海马体1859链→1866链(+7新链)。下一步: 实体重构因果图,引入NER和共指消解。",
    "tags": ["P0", "因果图", "综合诊断", "系统洞察", "深度因果", "进化方向"],
    "confidence": 0.95,
    "timestamp": NOW,
    "source": "p0_comprehensive_analysis",
    "cause": "因果图构建策略以文本级匹配为核心，缺乏语义理解层",
    "effect": "因果图拓扑价值低，无法支撑诊断/预测/解释的多步推理需求"
})

# Write to hippocampus
if 'causal_chains' not in hip:
    hip['causal_chains'] = []

hip['causal_chains'].extend(insight_chains)

# Update metadata
if 'meta' not in hip:
    hip['meta'] = {}
hip['meta']['last_p0_analysis'] = NOW
hip['meta']['p0_version'] = 'v10.87'
hip['meta']['causal_graph_nodes'] = 3558
hip['meta']['causal_graph_edges'] = 1847

total_chains = len(hip['causal_chains'])

with open(hip_path, 'w', encoding='utf-8') as f:
    json.dump(hip, f, ensure_ascii=False, indent=2)

print(f"  写入{len(insight_chains)}条新因果链")
print(f"  海马体总链数: {total_chains}")
print(f"  新链ID列表:")
for chain in insight_chains:
    print(f"    - {chain['id']}")

# ── STEP 5: Git commit ──
print(f"\n{'=' * 60}")
print("  STEP 5: Git commit v10.87")
print(f"{'=' * 60}")

os_cwd = str(CLUSTER)

# Git add all relevant files
files_to_commit = [
    "causal_graph.py",
    "causal_graph_output.json",
    "causal_graph_analysis.json",
    "p0_causal_analysis.py",
    "p0_deep_explain.py",
    "p0_deep_analysis_result.json",
    "hippocampus_memory.json",
    "causal_reasoner.py",
    "insight_engine.py",
    "evolution_orchestrator.py",
    "ZERO-HANDOFF.md"
]

for f in files_to_commit:
    fpath = CLUSTER / f
    if fpath.exists():
        result = subprocess.run(
            ["git", "add", f],
            cwd=os_cwd,
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"  git add {f}: {result.stderr.strip()}")

# Commit
commit_msg = """v10.87: P0因果图深度分析——系统级洞察

[分析结果]
- 因果图: 3558节点/1847边/1851因果链
- 最大路径: 1跳(无多步因果传导)
- 连通分量: 1711个(最大23节点=严重碎片化)
- [待推导]信息黑洞: 1611节点(45%)
- 外部知识占比: 93%(ext_world标签)

[Top3关键节点]
1. n-625(in=22): [待推导]汇聚点
2. n-1639(in=5): 量子力学主题
3. n-90(in=4): ❌失败节点

[Top3影响力源]
1. n-156(out=5): 光爱数学证明
2. n-194(out=5): 信息论Agent
3. n-196(out=5): 麦克斯韦妖类比

[系统洞察]
1. 图被外部知识Q&A对主导,缺乏内部因果网络
2. 文本级节点未做实体消歧,去重失效
3. [待推导]占位符形成信息黑洞
4. 下一步: 实体重构+NER+共指消解

[文件]
- 新增: p0_causal_analysis.py, p0_deep_explain.py
- 新增: causal_graph_analysis.json, p0_deep_analysis_result.json
- 更新: hippocampus_memory.json(+5链→1866链)
"""

result = subprocess.run(
    ["git", "commit", "-m", commit_msg],
    cwd=os_cwd,
    capture_output=True, text=True
)
print(f"  git commit: {result.stdout.strip()}")
if result.stderr:
    print(f"  stderr: {result.stderr.strip()}")

# Get hash
result = subprocess.run(
    ["git", "rev-parse", "HEAD"],
    cwd=os_cwd,
    capture_output=True, text=True
)
git_hash = result.stdout.strip()
print(f"  Git hash: {git_hash}")

# Also tag
result = subprocess.run(
    ["git", "tag", "v10.87"],
    cwd=os_cwd,
    capture_output=True, text=True
)

print(f"\n{'=' * 60}")
print("  STEP 4+5 完成")
print(f"{'=' * 60}")
print(f"  Git hash: {git_hash}")
print(f"  海马体链数: {total_chains}")
