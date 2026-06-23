"""
One-shot deep cross-dimension synthesis
Injects high-quality chains into hippocampus using API
"""
import sys, json, time, random
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群/brain')

CLUSTER = '/mnt/c/Users/h/Desktop/零/真元集群'

def write_chain(src, rel, dst, dimension, content, strength=0.7):
    """Write chain to hippocampus"""
    import json
    hip_file = f"{CLUSTER}/hippocampus_memory.json"
    try:
        with open(hip_file, 'r', encoding='utf-8') as f:
            hip = json.load(f)
    except:
        hip = {"causal_chains": []}
    
    chain = {
        "src": src, "rel": rel, "dst": dst,
        "dimension": dimension, "strength": strength,
        "content": content, "timestamp": time.time()
    }
    hip.setdefault("causal_chains", []).append(chain)
    
    with open(hip_file, 'w', encoding='utf-8') as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)
    return chain

# Load current dimension state
hip_file = f"{CLUSTER}/hippocampus_memory.json"
with open(hip_file, 'r', encoding='utf-8') as f:
    hip = json.load(f)
chains = hip.get('causal_chains', [])
from collections import Counter
dim_counts = Counter(c.get('dimension', '未分类') for c in chains)
sorted_dims = sorted(dim_counts.items(), key=lambda x: -x[1])
print(f"Total chains: {len(chains)}, Dimensions: {len(dim_counts)}")
print(f"Strongest: {sorted_dims[:3]}")
print(f"Weakest: {sorted_dims[-3:]}")

# Try API bridge
try:
    from api_bridge import APIBridge
    bridge = APIBridge()
    
    # Get strongest and weakest dimensions for cross synthesis
    weakest = [d for d,_ in sorted_dims[-3:] if d != '未分类']
    strongest = [d for d,_ in sorted_dims[:3] if d != '未分类']
    
    prompt = f"""[跨维合成脉冲]
维度状态: {', '.join([f'{d}={c}' for d,c in sorted_dims[:8]])}

最弱维: {weakest}
最强维: {strongest}

任务: 聚焦最弱维度 {weakest[0]}，从最强维度 {strongest[0]} 汲取深层关联，产生一个高价值洞察。
要求:
- 20-40字
- 可工程化
- 非线性跨维涌现
- JSON格式: {{"insight": "...", "action": "..."}}"""

    result = bridge.call_api(prompt)
    
    if result.get('success'):
        content = result.get('content', '')
        print(f"\nAPI成功! Content: {content[:300]}")
        
        # Try to parse JSON from response
        import re
        json_match = re.search(r'\{[^{}]*"insight"[^{}]*\}', content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group())
            insight = parsed.get('insight', content[:60])
            action = parsed.get('action', '')
        else:
            insight = content.strip().split('\n')[0][:60]
            action = ''
        
        # Write synthesis chain to strongest×weakest
        write_chain(
            src="工程·深度合成",
            rel="跨维深度合成",
            dst=f"{strongest[0]}×{weakest[0]}",
            dimension=weakest[0],
            content=insight,
            strength=0.9
        )
        print(f"✅ 深度合成写入: {insight}")
        
        # Write a second cross-chain
        if len(weakest) > 1 and len(strongest) > 1:
            prompt2 = f"""[跨维合成脉冲]
任务: 从 {strongest[1]} 和 {weakest[1]} 的交叉中涌现新洞察。
JSON: {{"insight":"...","action":"..."}}"""
            
            result2 = bridge.call_api(prompt2)
            if result2.get('success'):
                c2 = result2.get('content', '')
                json_match2 = re.search(r'\{[^{}]*"insight"[^{}]*\}', c2, re.DOTALL)
                if json_match2:
                    parsed2 = json.loads(json_match2.group())
                    insight2 = parsed2.get('insight', c2[:60])
                else:
                    insight2 = c2.strip().split('\n')[0][:60]
                
                write_chain(
                    src="工程·深度合成",
                    rel="跨维深度合成",
                    dst=f"{strongest[1]}×{weakest[1]}",
                    dimension=weakest[1],
                    content=insight2,
                    strength=0.85
                )
                print(f"✅ 深度合成#2写入: {insight2}")
    else:
        print(f"API调用失败: {result.get('error', 'unknown')}")
        print("回退到本地模板合成")
        # Local fallback
        for i in range(min(3, len(weakest))):
            w = weakest[i]
            s = strongest[i % len(strongest)]
            write_chain(
                src="深度合成·本地",
                rel="跨维交叉",
                dst=f"{s}×{w}",
                dimension=w,
                content=f"{w}从{s}汲取深层关联势能",
                strength=0.6
            )
        print(f"✅ 本地合成x{min(3, len(weakest))}条")

except Exception as e:
    import traceback
    print(f"CRASH: {e}")
    traceback.print_exc()
    print("完全静默退出")
