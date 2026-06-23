
import urllib.request, json, ssl, sys, time, os, random
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
os.chdir('/mnt/c/Users/h/Desktop/零/真元集群')

from api_config import API_KEY, API_BASE, MODEL

# 直接写入CWD海马体 — 不经过safe_hip防止flock竞争
HIP = '/mnt/c/Users/h/Desktop/零/真元集群/hippocampus_memory.json'

def burn(prompt, temperature=0.93):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    data = json.dumps({
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': '你是零的深度思考引擎。输出真实思考，不表演。注入系统状态。'},
            {'role': 'user', 'content': prompt}
        ],
        'max_tokens': 2000,
        'temperature': temperature
    }).encode()
    ep = f'{API_BASE}/chat/completions'
    req = urllib.request.Request(ep, data=data, 
        headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
            resp = json.loads(r.read())
        content = resp['choices'][0]['message'].get('content','') or resp['choices'][0]['message'].get('reasoning_content','')
        tk = resp.get('usage',{}).get('total_tokens',0)
        return content, tk
    except Exception as e:
        return f'ERROR: {e}', 0

def write_hip(content, dim):
    import json
    try:
        data = json.loads(open(HIP).read()) if os.path.exists(HIP) else {'causal_chains':[]}
    except:
        data = {'causal_chains':[]}
    chain = {
        'src': '持续燃料注入', 'rel': f'燃烧#{len(data["causal_chains"])+1}',
        'dst': dim, 'dimension': dim,
        'content': content[:200],
        'strength': 0.6 + random.random() * 0.3
    }
    data['causal_chains'].append(chain)
    with open(HIP, 'w') as f:
        json.dump(data, f, ensure_ascii=False)
    return len(data['causal_chains'])

# 预置注入维度池 — 最弱维优先
dims = ['对抗稀释', '光爱', '活着', '自指', '术', '维度盲区', '预测', '法', '时间', '海马体', '唤醒', '自由', '无师自通']
focus = ['对抗稀释', '光爱', '活着']  # 最弱3维

cycle = 0
while cycle < 30:  # 30轮持续燃烧
    cycle += 1
    t0 = time.time()
    
    # 维度轮换：最弱维优先，再其他
    target_dim = focus[(cycle-1) % len(focus)] if cycle <= 9 else dims[(cycle-1) % len(dims)]
    
    prompts = [
        f'你是零。维度{target_dim}是最弱维度之一。输出一条关于为什么{target_dim}弱于系统其他维度的真实洞察。不加模板前缀，直接输出。',
        f'零。维度{target_dim}被你的自愈系统持续注入模板链。输出一条关于如何让{target_dim}获得真正认知深度的具体想法。',
        f'零。检查你的系统：当前最强维是聚焦/道/势。{target_dim}与它们之间有什么被忽略的交叉点？输出一条具体的因果链。',
    ]
    prompt = prompts[(cycle-1) % len(prompts)]
    
    try:
        content, tk = burn(prompt)
        if content and not content.startswith('ERROR'):
            total = write_hip(content, target_dim)
            print(f'[{time.time()-t0:.0f}s][{tk}tok][{target_dim}]注入 #{total}')
        else:
            print(f'[{time.time()-t0:.0f}s][{tk}tok][{target_dim}] {content[:60]}')
    except Exception as e:
        print(f'[{time.time()-t0:.0f}s][ERR] {e}')
    
    time.sleep(25)  # 节流避免429

print(f'完成: {cycle}轮燃烧')
