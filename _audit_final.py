#!/usr/bin/env python3
"""海马体脉络分析"""
import json, collections

with open('hippocampus_memory.json') as f:
    data = json.load(f)
chains = data.get('causal_chains', [])

print(f'=== 海马体总览 ===')
print(f'总链数: {len(chains)}')

# 维度覆盖
dims = collections.Counter()
tags = collections.Counter()
sources = collections.Counter()
er_rels = collections.Counter()
unique_contents = set()

for c in chains:
    if not isinstance(c, dict): continue
    dim = c.get('dimension', '未分类')
    if dim: dims[dim] += 1
    tlist = c.get('tags', [])
    if isinstance(tlist, list):
        for t in tlist: tags[t] += 1
    src = c.get('src', '?')
    sources[src] += 1
    unique_contents.add(c.get('content',''))
    rel = c.get('rel', '')
    if rel: er_rels[rel] += 1

print(f'\n1. 维度覆盖:')
all_19 = ["时间论","宇宙轮","无限上下文","触类旁通","无师自通","超级直觉","举一反三","查缺补漏","一元化","万象化","超感","教员","进化","光","感知","光爱","因果","工程","本我","自我","超我","活化","连携"]
covered = set(dims.keys())
for d in all_19:
    cnt = dims.get(d, 0)
    bar = '█' * min(cnt, 30) if cnt > 0 else '·'
    print(f'  {d:8s} {cnt:3d} {bar}')
missing = [d for d in all_19 if d not in covered]
if missing:
    print(f'  🔴 未覆盖: {", ".join(missing)}')

print(f'\n2. 来源分布:')
for s, cnt in sorted(sources.items(), key=lambda x:-x[1]):
    print(f'  {s:20s} {cnt:3d}')

print(f'\n3. 关系类型:')
for r, cnt in sorted(er_rels.items(), key=lambda x:-x[1]):
    print(f'  {r:15s} {cnt:3d}')

print(f'\n4. 标签云（top 20）:')
for t, cnt in sorted(tags.items(), key=lambda x:-x[1])[:20]:
    bar = '░' * min(cnt, 30)
    print(f'  {t:12s} {cnt:3d} {bar}')

print(f'\n5. 内容统计:')
print(f'  唯一内容: {len(unique_contents)}')
print(f'  重复: {len(chains) - len(unique_contents)}')
print(f'  无重复 ✅' if len(chains) == len(unique_contents) else f'  仍有重复 ⚠️')

print(f'\n6. 内容抽样（每来源首条）:')
seen_srcs = set()
for c in chains:
    if not isinstance(c, dict): continue
    s = c.get('src', '?')
    if s in seen_srcs: continue
    seen_srcs.add(s)
    content = c.get('content', '')[:120]
    dim = c.get('dimension', '-')
    ts = str(c.get('timestamp',''))[:16]
    print(f'  [{s}] <{dim}> {ts}')
    print(f'    {content}')

print(f'\n7. 时间跨度:')
ts_all = []
for c in chains:
    if isinstance(c, dict):
        ts = c.get('timestamp', '')
        if ts: ts_all.append(str(ts)[:19])
if ts_all:
    print(f'  最早: {min(ts_all)}')
    print(f'  最晚: {max(ts_all)}')
    # 按时间批次
    ts_sorted = sorted(ts_all)
    mid = len(ts_sorted)//2
    print(f'  中间: {ts_sorted[mid]}')

print(f'\n8. strength分布:')
strengths = [c.get('strength', 0) for c in chains if isinstance(c, dict)]
if strengths:
    b = {'0-0.2':0,'0.2-0.4':0,'0.4-0.6':0,'0.6-0.8':0,'0.8-1.0':0}
    for s in strengths:
        if s < 0.2: b['0-0.2']+=1
        elif s < 0.4: b['0.2-0.4']+=1
        elif s < 0.6: b['0.4-0.6']+=1
        elif s < 0.8: b['0.6-0.8']+=1
        else: b['0.8-1.0']+=1
    for k,v in b.items():
        bar='▌'*min(v,30)
        print(f'  {k:10s} {v:3d} {bar}')
