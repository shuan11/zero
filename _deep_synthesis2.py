"""
One-shot deep cross-dim synthesis — from brain context
"""
import sys, os, json, time, re

CLUSTER = '/mnt/c/Users/h/Desktop/零/真元集群'

# Must be run from brain/ directory with correct path setup
os.chdir(CLUSTER)

def write_chain(src, rel, dst, dim, content, strength=0.7):
    hip_file = f"{CLUSTER}/hippocampus_memory.json"
    try:
        with open(hip_file, 'r', encoding='utf-8') as f:
            hip = json.load(f)
    except:
        hip = {"causal_chains": []}
    hip.setdefault("causal_chains", []).append({
        "src": src, "rel": rel, "dst": dst,
        "dimension": dim, "strength": strength,
        "content": content, "timestamp": time.time()
    })
    with open(hip_file, 'w', encoding='utf-8') as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)

# Read dims
with open(f"{CLUSTER}/hippocampus_memory.json", 'r', encoding='utf-8') as f:
    hip = json.load(f)
chains = hip.get('causal_chains', [])
from collections import Counter
dim_counts = Counter(c.get('dimension', '未分类') for c in chains)
sorted_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
weakest = [d for d,_ in sorted_dims[-3:] if d != '未分类']
strongest = [d for d,_ in sorted_dims[:3] if d != '未分类']
total = len(chains)

print(f"链: {total}, 维: {len(dim_counts)}")
print(f"最强: {strongest[0]}({sorted_dims[0][1]}) 最弱: {weakest[0]}({sorted_dims[-1][0] if sorted_dims else '?'})")

# Try: run inside brain context to avoid inspect shadowing
result = None
try:
    # Add brain to path but remove CLUSTER from path to fix inspect conflict
    orig_path = sys.path.copy()
    sys.path = [p for p in sys.path if CLUSTER not in p]
    
    from api_bridge import APIBridge
    bridge = APIBridge()
    
    dim_summary = '; '.join([f'{d}={c}' for d,c in sorted_dims[:8]])
    prompt = f"""[跨维合成]
最弱:{weakest[0]}({dict(sorted_dims).get(weakest[0],'?')}) 最强:{strongest[0]}({dict(sorted_dims).get(strongest[0],'?')})
维度: {dim_summary}

任务: 从{strongest[0]}和{weakest[0]}交叉中诞生新洞察。
要求: 20-40字, 可工程化, 非线性。
JSON: {{"insight":"..."}}"""

    result = bridge.call_api(prompt)
    
    if result.get('success'):
        content = result.get('content', '')
        print(f"\n✅ API成功!")
        print(content[:400])
        
        jm = re.search(r'\{[^{}]*"insight"[^{}]*\}', content, re.DOTALL)
        if jm:
            parsed = json.loads(jm.group())
            insight = parsed.get('insight', content[:60])
        else:
            insight = content.strip().split('\n')[0][:60]
        
        write_chain("深度合成·API", "跨维涌现", f"{strongest[0]}×{weakest[0]}", weakest[0], insight, 0.95)
        print(f"✅ 写入: [{weakest[0]}] {insight}")
    else:
        print(f"❌ API失败: {result.get('error', '?')}")
        
except Exception as e:
    print(f"CRASH (expected): {e}")
    print("Fallback to template injection...")
    # Even without API, inject local synthesis
    for i in range(min(3, len(weakest))):
        w = weakest[i]
        s = strongest[i % len(strongest)]
        write_chain("深度合成·本地", "跨维交叉", f"{s}×{w}", w, 
                    f"{w}应在{s}的镜像中寻找自身差距的填补路径", 0.7)
        print(f"✅ 本地合成: {w}×{s}")

# Final dim summary
with open(f"{CLUSTER}/hippocampus_memory.json", 'r', encoding='utf-8') as f:
    hip2 = json.load(f)
chains2 = hip2.get('causal_chains', [])
dim_counts2 = Counter(c.get('dimension', '未分类') for c in chains2)
sorted_dims2 = sorted(dim_counts2.items(), key=lambda x: -x[1])
print(f"\n最终: 总链{len(chains2)} 最强{sorted_dims2[0][0]}={sorted_dims2[0][1]} 最弱{sorted_dims2[-1][0]}={sorted_dims2[-1][1]}")
