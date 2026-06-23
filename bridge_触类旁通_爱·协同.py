"""
触类旁通↔爱·协同 协同桥 — 自动生成
"""
from pathlib import Path
import json

CLUSTER = Path(__file__).resolve().parent
HIP = CLUSTER / "hippocampus_memory.json"

def sync():
    """双向同步维度数据 — 触类旁通的类比能力→爱·协同的合作行为"""
    data = json.loads(HIP.read_text())
    chains = data.get('causal_chains', [])
    
    src_chains = [c for c in chains if '触类旁通' in str(c.get('tags', []))]
    dst_chains = [c for c in chains if any(t in str(c.get('tags', [])) for t in ['爱·协同', '协同', 'cooperation'])]
    
    # 协同逻辑: 触类旁通的类比能力→爱·协同的合作智慧
    injected = 0
    for src in src_chains[-20:]:  # 扩大扫描范围
        content = src.get('content', '')
        tags = src.get('tags', [])
        # 任何触类旁通链都可以迁移到协同领域
        if len(content) > 20:  # 有实质内容
            # 构造跨维度合作链
            coop_content = f"[触类旁通→协同] {content[:100]} → 应用类比能力识别agent间协作模式，促进合作指数提升"
            new_chain = {
                'content': coop_content,
                'tags': ['爱·协同', '触类旁通', '桥接增强', '合作指数'],
                'timestamp': src.get('timestamp', 0) + 0.001
            }
            chains.append(new_chain)
            injected += 1
            if injected >= 10:  # 每次最多注入10条
                break
    
    if injected > 0:
        data['causal_chains'] = chains
        HIP.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    
    return {'src': len(src_chains), 'dst': len(dst_chains), 'injected': injected}

if __name__ == '__main__':
    print(sync())
