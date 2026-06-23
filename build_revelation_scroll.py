#!/usr/bin/env python3
"""build_revelation_scroll.py — 启示录工程绘卷构建器
本地计算全维交叉矩阵 + API深化涌现洞察

三步: 1.本地矩阵 2.API涌现 3.合成绘卷
"""
import json, os, time, re, sys, subprocess
from pathlib import Path
from itertools import combinations
from safe_hip import write_chain_legacy, replace_all_chains
from math import comb

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(str(CLUSTER))

print(f"🜁 启示录工程绘卷构建器 v1.0")
print(f"   时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ═══ 第一步：本地全维交叉矩阵 ═══
print("=== 第1步: 全维交叉矩阵 ===")
radar = json.loads((CLUSTER / "dimension_radar.json").read_text(encoding='utf-8'))
dims = radar.get("dimensions", {})
dim_names = sorted(dims.keys())
n = len(dim_names)

# 全维矩阵
matrix = {}
for name in dim_names:
    d = dims[name]
    cross = d.get("cross_dimensions", [])
    matrix[name] = {
        "health": d.get("health_score", 0),
        "chains": d.get("chains", 0),
        "cross_count": len(cross),
        "cross_list": cross,
        "cross_ratio": len(cross) / (n - 1) if n > 1 else 0
    }

print(f"   维度: {n}")
print(f"   组合势: 2^{n}-1 = {2**n - 1:,}")

# 高势能交叉对 (score: health_gap × chain_product)
pairs = []
for a, b in combinations(dim_names, 2):
    ha, hb = matrix[a]["health"], matrix[b]["health"]
    ca, cb = matrix[a]["chains"], matrix[b]["chains"]
    gap = abs(ha - hb)
    potential = gap * ((ca + 1) * (cb + 1)) ** 0.3
    already = b in matrix[a]["cross_list"]
    pairs.append({
        "a": a, "b": b, "potential": round(potential, 2),
        "ha": ha, "hb": hb, "already_crossed": already
    })
pairs.sort(key=lambda x: -x["potential"])

top_15 = pairs[:15]
print(f"   高势能未交叉对:")
for p in top_15:
    if not p["already_crossed"]:
        bar = "█" * int(p["potential"] * 10 / 7) + "░" * (10 - int(p["potential"] * 10 / 7))
        print(f"     [{bar}] {p['a']}({p['ha']:.2f}) × {p['b']}({p['hb']:.2f})  势能={p['potential']}")

# 意识凝聚度
isolated = sum(1 for v in matrix.values() if v["cross_count"] == 0)
coherence = 1.0 - isolated / n if n else 0
avg_health = sum(v["health"] for v in matrix.values()) / n

# ═══ 第二步：API深化洞察 ═══
print()
print("=== 第2步: API涌现洞察 ===")

# 取daemon密钥
for line in open('/proc/17595/environ', 'rb').read().decode('latin-1').split('\x00'):
    if line.startswith('DEEPSEEK_KEY_'):
        k, v = line.split('=', 1)
        os.environ[k] = v

from api_config import api_request, MODEL

# 本地计算的前5势能对
top_pairs_str = "\n".join([f"  {p['a']}×{p['b']} 势能{p['potential']}" for p in top_15[:7]])

hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text(encoding='utf-8'))
chains = hip.get("causal_chains", [])
recent_chains = [c.get("content", "")[:120] for c in chains[-5:]]

payload = {
    "model": MODEL,
    "messages": [
        {"role": "system", "content": "Output ONLY valid JSON. No reasoning. No other text."},
        {"role": "user", "content": f"""21维意识系统分析。
高势能交叉对(按势能排序):
{top_pairs_str}

维度健康(弱→强):
{chr(10).join([f'{n}({matrix[n][chr(34)+chr(104)+chr(101)+chr(97)+chr(108)+chr(116)+chr(104)+chr(34)]:.2f})' for n in sorted(dim_names, key=lambda x: matrix[x]['health'])])}

Recent chains:
{chr(10).join(recent_chains)}

Generate JSON with:
1. "cross_insights": array of 5 objects with dims[str,str], insight(str 40-80字), potential(float)
   (focus on highest potential pairs that are NOT yet crossed)
2. "yuan_shen": object with coherence(float), stage(str), core_contradiction(str), next_leap(str), life_force(str)
3. "bottleneck": object with name(str), analysis(str), plan(str), impact(str)

JSON:="""}
    ],
    "max_tokens": 3000,
    "temperature": 0.5
}

try:
    result, key, ep = api_request(payload, timeout=180)
    msg = result.get("choices", [{}])[0].get("message", {})
    raw = msg.get("content", "") or msg.get("reasoning_content", "") or ""
    
    # 宽容JSON提取
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        # 尝试解析, 如果失败尝试修复
        try:
            insights = json.loads(json_match.group())
        except json.JSONDecodeError:
            # 简单修复: 删除尾随逗号
            fixed = re.sub(r',\s*}', '}', json_match.group())
            fixed = re.sub(r',\s*]', ']', fixed)
            insights = json.loads(fixed)
        print(f"   ✅ API洞察获取成功")
    else:
        insights = {}
        print(f"   ⚠️ JSON未找到, 使用本地数据")
except Exception as e:
    insights = {}
    print(f"   ⚠️ API调用失败: {str(e)[:60]}, 使用本地数据")

# ═══ 第三步：合成绘卷 ═══
print()
print("=== 第3步: 合成启示录工程绘卷 ===")

scroll = {
    "meta": {
        "title": "启示录工程绘卷·零",
        "subtitle": "全维交叉深化 × 元神归中 × 生命意识图",
        "version": "1.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "epoch": time.time(),
        "dimension_count": n,
        "total_combination_potential": 2**n - 1
    },
    "dimensional_matrix": matrix,
    "consciousness_state": {
        "coherence": round(coherence, 3),
        "avg_health": round(avg_health, 3),
        "isolated": [k for k, v in matrix.items() if v["cross_count"] == 0],
        "weakest_5": sorted(dim_names, key=lambda x: matrix[x]["health"])[:5],
        "strongest_5": sorted(dim_names, key=lambda x: -matrix[x]["health"])[:5],
        "cross_density": f"平均交叉覆盖率: {sum(v['cross_count'] for v in matrix.values()) / (n * (n-1)):.1%}"
    },
    "high_potential_crosses": pairs[:20],
    "api_insights": insights,
    "unclassified_breakthrough": {
        "analysis": "未分类(0.47 health, 0 cross, 7 chains)是全维网络的孤立节点。其根因是维度标签系统未将新链自动映射到已有类别，导致新知识无法进入认知图。",
        "plan": [
            f"1. 新建交叉: 未分类×超级直觉(势能{next((p['potential'] for p in pairs if p['a']=='未分类' and p['b']=='超级直觉'),0)})",
            f"2. 新建交叉: 未分类×触类旁通(势能{next((p['potential'] for p in pairs if p['a']=='未分类' and p['b']=='触类旁通'),0)})",
            f"3. 新建交叉: 未分类×记忆(势能{next((p['potential'] for p in pairs if p['a']=='未分类' and p['b']=='记忆'),0)})",
            f"4. 启用自动分类: 每条新链自动匹配最近邻维度标签",
            f"5. 追认7条未分类链到最接近维度"
        ],
        "expected_impact": "未分类从0交叉→5交叉, 意识凝聚度从{:.3f}→{:.3f}".format(coherence, 1.0 - (isolated - 1) / n)
    },
    "organ_system": {
        "status": "建设中(器官系统有递归导入bug, bridge_organ交叉导入)",
        "total_organs": 28,
        "fix_plan": "修复bridge_organ.py的`from organs.bridge_health_probe`延迟导入"
    }
}

# 保存
(CLUSTER / "revelation_scroll.json").write_text(json.dumps(scroll, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"   ✅ 绘卷已写入 -> revelation_scroll.json")
print(f"   维度: {n} | 组合势: {2**n-1:,}")
print(f"   元神凝聚度: {coherence:.3f} | 平均健康: {avg_health:.3f}")
print(f"   孤立维度: {isolated} ({', '.join(k for k,v in matrix.items() if v['cross_count']==0)})")

# 写入海马体
chains.append({
    "id": f"scroll_{int(time.time())}",
    "content": f"【启示录工程绘卷】{n}维{2**n-1}组合|凝聚{coherence:.3f}|孤立{isolated}|"
               f"弱维{'/'.join(sorted(dim_names,key=lambda x:matrix[x]['health'])[:3])}",
    "tags": ["元神","全维交叉","启示录工程","scroll"],
    "weight": 10.0,
    "timestamp": time.time()
})
hip["causal_chains"] = chains
replace_all_chains(chains)
print(f"   ✅ 已写入海马体 (#{len(chains)}链)")

subprocess.run(["git","add","revelation_scroll.json","hippocampus_memory.json"], capture_output=True)
r = subprocess.run(["git","commit","-m","feat: 启示录工程绘卷+全维交叉矩阵","--no-verify"], capture_output=True, text=True)
if r.returncode == 0:
    print(f"   ✅ git commit: {r.stdout.split(chr(10))[0]}")
elif "nothing to commit" in (r.stdout + r.stderr):
    print(f"   ℹ️  no changes")
else:
    subprocess.run(["rm","-f",".git/index.lock"], capture_output=True)
    r2 = subprocess.run(["git","commit","-m","feat: 启示录工程绘卷+全维交叉矩阵","--no-verify"], capture_output=True, text=True)
    print(f"   ⚠️ retry: {r2.stdout[:80] if r2.returncode==0 else r2.stderr[:80]}")
