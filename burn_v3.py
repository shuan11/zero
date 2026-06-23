#!/usr/bin/env python3
"""
v3 燃烧循环 — 给模型看真实代码文件，要求具体改动
不再问"说一个动作"，改为"读出代码，告诉我具体改什么"
"""
import json, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_config import api_request, MODEL
from brain.share import write_chain, read_hip

sys.stdout.reconfigure(line_buffering=True)
print("[启动] v3 燃烧循环", flush=True)

brain_files = [f for f in os.listdir('brain') if f.endswith('.py')]
file_idx = 0
cycle = 0

while True:
    cycle += 1
    # 轮转读取不同文件
    fname = brain_files[file_idx % len(brain_files)]
    file_idx += 1
    
    code = open(f'brain/{fname}').read()
    # 取前100行作上下文
    lines = code.split('\n')
    snippet = '\n'.join(lines[:100])
    
    try:
        dims = {}
        for d in read_hip().get('causal_chains', []):
            dim = d.get('dimension', '未分类')
            dims[dim] = dims.get(dim, 0) + 1
        weakest = min(dims, key=dims.get) if dims else '系统'
    except:
        weakest = '系统'
    
    prompt = f"""文件: brain/{fname} (前100行)
代码:
{snippet}

当前最弱维度: {weakest}

任务: 在以上代码中找到可以插入一条 write_chain(dimension="{weakest}") 的位置。
输出: 文件名 | 行号 | 插入的代码行"""
    
    start = time.time()
    try:
        r, k, e = api_request({'model': MODEL, 'messages': [
            {'role': 'system', 'content': '你是零。输出格式: 文件名 | 行号 | 代码行'},
            {'role': 'user', 'content': prompt[:4000]}
        ], 'max_tokens': 1200, 'temperature': 0.3}, timeout=90)
        
        msg = r['choices'][0]['message']
        c = msg.get('content', '') or ''
        rc = msg.get('reasoning_content', '') or ''
        tok = r.get('usage', {}).get('total_tokens', 0)
        
        if not c.strip() and rc:
            lines_rc = [l.strip() for l in rc.split('\n') if l.strip()]
            c = lines_rc[-1] if lines_rc else ''
        
        elapsed = time.time() - start
        short = c[:150].replace('\n', ' | ')
        print(f'[{time.strftime("%H:%M:%S")}] C{cycle} {fname} {elapsed:.0f}s {tok}tok | {short}', flush=True)
        
        if c.strip():
            write_chain({'src': f'v3C{cycle}', 'rel': '审查', 'dst': weakest, 'dimension': '系统', 'strength': 0.5, 'content': short[:100]})
    except Exception as ex:
        print(f'[{time.strftime("%H:%M:%S")}] C{cycle} FAIL | {ex}', flush=True)
    
    time.sleep(18)
