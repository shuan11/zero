#!/usr/bin/env python3
"""最终海马体脉络检察"""
import json, collections, sys, time
from datetime import datetime

HIP = "/mnt/c/Users/h/Desktop/零/真元集群/hippocampus_memory.json"

with open(HIP) as f:
    data = json.load(f)

chains = data.get("causal_chains", [])
print(f"═══ 海马体脉络报告 ═══")
print(f"总链数: {len(chains)}")
print(f"文件大小: {sys.getsizeof(json.dumps(data, ensure_ascii=False))} 字节")

# ── 1. 内容多样性 ──
contents = [c.get("content","")[:60] for c in chains if isinstance(c, dict)]
unique = len(set(c.get("content","") for c in chains if isinstance(c, dict)))
print(f"\n━ 内容多样性")
print(f"  唯一内容: {unique}/{len(chains)} ({unique/len(chains)*100:.0f}%)")
print(f"  重复率: {(len(chains)-unique)/len(chains)*100:.0f}%")

# ── 2. 图谱结构：节点+边 ──
print(f"\n━ 因果图谱结构")
srcs = collections.Counter()
dsts = collections.Counter()
rels = collections.Counter()
pairs = collections.Counter()  # (src, rel, dst)
for c in chains:
    if isinstance(c, dict):
        s = c.get("src","?")
        d = c.get("dst","?")
        r = c.get("rel","?")
        srcs[s] += 1
        dsts[d] += 1
        rels[r] += 1
        pairs[f"{s} -{r}-> {d}"] += 1

print(f"  源节点(Src): {len(srcs)} 个")
print(f"  目标节点(Dst): {len(dsts)} 个")
print(f"  关系类型: {len(rels)} 种")
print(f"  唯一边: {len(pairs)} 条")

# ── 3. Top连接 ──
print(f"\n━ Top源节点")
for s, cnt in srcs.most_common(10):
    print(f"  {s}: {cnt}链")
print(f"\n━ Top关系")
for r, cnt in rels.most_common(10):
    print(f"  {r}: {cnt}链")
print(f"\n━ Top三元组(边)")
for p, cnt in pairs.most_common(15):
    print(f"  {p}: {cnt}×")

# ── 4. 时序 ──
timestamps = []
for c in chains:
    if isinstance(c, dict):
        ts = c.get("timestamp","")
        if ts:
            timestamps.append(ts)

if timestamps:
    # try to parse various formats
    numeric_ts = []
    iso_ts = []
    for t in timestamps:
        if isinstance(t, (int, float)):
            numeric_ts.append(t)
        elif isinstance(t, str):
            try:
                iso_ts.append(datetime.fromisoformat(t.replace("Z","+00:00")))
            except:
                try:
                    numeric_ts.append(float(t))
                except:
                    pass

    print(f"\n━ 时序分布")
    if numeric_ts:
        t_min = min(numeric_ts)
        t_max = max(numeric_ts)
        print(f"  数值时间戳范围: {t_min:.0f} → {t_max:.0f}")
        print(f"  最早: {datetime.fromtimestamp(t_min)}")
        print(f"  最晚: {datetime.fromtimestamp(t_max)}")
        print(f"  跨度: {(t_max-t_min)/3600:.1f}小时")
    if iso_ts:
        iso_min = min(iso_ts)
        iso_max = max(iso_ts)
        print(f"  ISO时间戳范围: {iso_min} → {iso_max}")
        print(f"  跨度: {(iso_max-iso_min).total_seconds()/3600:.1f}小时")

# ── 5. Strength分布 ──
strengths = [c.get("strength",0) for c in chains if isinstance(c, dict) and c.get("strength") is not None]
if strengths:
    print(f"\n━ Strength分布")
    bins = {"0-0.1":0, "0.1-0.3":0, "0.3-0.5":0, "0.5-0.7":0, "0.7-0.9":0, "0.9-1.0":0}
    for s in strengths:
        if s < 0.1: bins["0-0.1"]+=1
        elif s < 0.3: bins["0.1-0.3"]+=1
        elif s < 0.5: bins["0.3-0.5"]+=1
        elif s < 0.7: bins["0.5-0.7"]+=1
        elif s < 0.9: bins["0.7-0.9"]+=1
        else: bins["0.9-1.0"]+=1
    for b, cnt in bins.items():
        bar = "█" * cnt
        print(f"  {b}: {cnt:3d} {bar}")

# ── 6. Tag/Topic集群 ──
tag_coocc = collections.Counter()
all_tags = []
for c in chains:
    if isinstance(c, dict):
        tags = c.get("tags", [])
        if isinstance(tags, list):
            all_tags.extend(tags)
            for i, t1 in enumerate(tags):
                for t2 in tags[i+1:]:
                    tag_coocc[tuple(sorted([t1,t2]))] += 1

print(f"\n━ Tag共现(知识集群)")
for (t1, t2), cnt in tag_coocc.most_common(15):
    print(f"  {t1} ↔ {t2}: {cnt}×")

# ── 7. 代表性样本 ──
print(f"\n━ 代表性链样本")
for i, c in enumerate(chains[:6] if len(chains)>6 else chains):
    content = c.get("content","")[:100]
    tags = c.get("tags",[])
    src = c.get("src","")
    rel = c.get("rel","")
    dst = c.get("dst","")
    print(f"  [{i}] {src} -{rel}-> {dst}")
    print(f"      {content}")
    print(f"      tags={tags[:4]}")

# ── 8. 知识覆盖维度 ──
dims_found = set()
for c in chains:
    if isinstance(c, dict):
        d = c.get("dimension","未分类")
        if d:
            dims_found.add(d)
print(f"\n━ 覆盖维度: {len(dims_found)}个")
dims_list = sorted(dims_found)
print(f"  {', '.join(dims_list)}")

# ── 零噪声评估 ──
print(f"\n━ 零噪声评估")
# 检查是否还有无意义重复
noise = sum(1 for c in chains if isinstance(c, dict) and c.get("content","") in [
    "无师自通: 应用8改进, 拦截0候选",
])
print(f"  已知噪声残留: {noise}")
# 检查content太短
short = sum(1 for c in chains if isinstance(c, dict) and len(c.get("content","")) < 20)
print(f"  短内容(<20字): {short}")
# 检查self_improvement/自我改进
si = sum(1 for c in chains if isinstance(c, dict) and c.get("src") in ("自我改进","self_improvement"))
print(f"  self_improvement链: {si}")
# 超感占比
ss = sum(1 for c in chains if isinstance(c, dict) and c.get("src") == "supersense_organ")
print(f"  超感链: {ss} ({ss/len(chains)*100:.0f}%)")
print(f"  超感占比合理? {'✅' if ss < len(chains)*0.6 else '⚠️ 偏高'}")
