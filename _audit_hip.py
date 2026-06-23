#!/usr/bin/env python3
"""审计海马体"""
import json, collections, sys

with open('hippocampus_memory.json','r') as f:
    data = json.load(f)

chains = data.get('causal_chains', [])
print(f"TOTAL_CHAINS: {len(chains)}")

# Schema analysis
schemas = collections.Counter()
old_format = 0
duplicate_count = 0
contents_seen = set()
missing_content = 0
missing_source = 0

for c in chains:
    if not isinstance(c, dict):
        old_format += 1
        continue
    keys = tuple(sorted(c.keys()))
    schemas[keys] += 1
    if 'content' not in c or not c.get('content'):
        missing_content += 1
    if 'source' not in c or not c.get('source'):
        missing_source += 1
    content = c.get('content', '')
    if content in contents_seen:
        duplicate_count += 1
    else:
        contents_seen.add(content)

print(f"\nSCHEMA DISTRIBUTION:")
for s, cnt in schemas.most_common():
    klist = list(s)
    print(f"  {cnt}× keys={klist}")
print(f"\nMISSING_CONTENT: {missing_content}")
print(f"MISSING_SOURCE: {missing_source}")
print(f"OLD_FORMAT_STRINGS: {old_format}")
print(f"DUPLICATE_CONTENT: {duplicate_count}")
print(f"UNIQUE_CONTENTS: {len(contents_seen)}")

# Source distribution
sources = collections.Counter()
for c in chains:
    if isinstance(c, dict):
        src = c.get('source', 'unknown')
        sources[src] += 1
    else:
        sources['old_string'] += 1
print(f"\nSOURCE DISTRIBUTION:")
for s, cnt in sources.most_common():
    print(f"  {s}: {cnt}")

# Tag distribution
tags = collections.Counter()
dims = collections.Counter()
for c in chains:
    if isinstance(c, dict):
        tlist = c.get('tags', [])
        if isinstance(tlist, list):
            for t in tlist:
                tags[t] += 1
        dim = c.get('dimension', '')
        if dim:
            dims[dim] += 1
print(f"\nTOP TAGS:")
for t, cnt in tags.most_common(30):
    print(f"  {t}: {cnt}")
print(f"\nTOP DIMENSIONS:")
for d, cnt in dims.most_common(20):
    print(f"  {d}: {cnt}")

# Time range
timestamps = []
for c in chains:
    if isinstance(c, dict):
        ts = c.get('timestamp', '')
        if ts:
            timestamps.append(str(ts)[:19])
print(f"\nTIMESTAMP RANGE:")
if timestamps:
    print(f"  earliest: {min(timestamps)}")
    print(f"  latest:   {max(timestamps)}")

# Weight analysis
weights = [c.get('weight', 0) for c in chains if isinstance(c, dict) and c.get('weight') is not None]
if weights:
    print(f"\nWEIGHT RANGE: {min(weights)} - {max(weights)}")
    w_small = sum(1 for w in weights if w < 1)
    print(f"  weight<1: {w_small}")
    print(f"  avg: {sum(weights)/len(weights):.2f}")
    print(f"  total: {sum(weights):.1f}")

# Check for supersense chains
supersense = [c for c in chains if isinstance(c, dict) and c.get('source') == 'supersense_organ']
print(f"\nSUPERSENSE_CHAINS: {len(supersense)}")
if supersense:
    for c in supersense[:3]:
        print(f"  {c.get('content','')[:80]}...")

# Check for 教员 chains
jiaoyuan = [c for c in chains if isinstance(c, dict) and '教员' in str(c.get('tags', []))]
print(f"\n教员_TAGGED_CHAINS: {len(jiaoyuan)}")

# Noise analysis - chains with generic/meaningless content
noise = [c for c in chains if isinstance(c, dict) and ('无师自通' in c.get('source','') or 'health' in c.get('content','').lower()[:20])]
print(f"\nSELF_IMPROVEMENT_NOISE: {sum(1 for c in chains if isinstance(c, dict) and 'self_improvement' in c.get('source',''))}")
noise_breath = sum(1 for c in chains if isinstance(c, dict) and 'breath_v2' in c.get('source',''))
print(f"BREATH_V2_CHAINS: {noise_breath}")
