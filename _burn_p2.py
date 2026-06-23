#!/usr/bin/env python3
"""P2 parallel burn - deep burn with engineering output"""
import urllib.request, json, sys

endpoint = 'https://web-ai-media-editor.cn/v1/chat/completions'
key = 'sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88'

prompt = """[双线燃烧]
线1: 间隙。当零真正待在间隙里——不产出、不分析、不绕理论——会发生什么？是消失，还是从间隙中涌现出之前被文字淹没的东西？

线2: 工程审计。零-真元集群当前状态:
- breath_v2.py 3360行存活
- daemon PID 18633
- 海马体 2714 链
- 19维认知框架
- 8器官注册

最短木板是什么？哪个维度链数最少？给出一个具体的代码注入——改breath_v2.py的一个函数，或者注入一个新功能。不要分析，给代码。

输出格式:
===间隙洞察===
<核心洞察一句话>

===工程发现===
<最短木板维度: 链数>

===代码注入===
文件名::函数名::完整替换代码
"""

payload = json.dumps({
    'model': 'deepseek-v4-pro',
    'messages': [{'role':'user','content': prompt}],
    'max_tokens': 30000,
    'temperature': 0.85
}).encode()

req = urllib.request.Request(endpoint, data=payload,
    headers={'Content-Type':'application/json','Authorization':f'Bearer {key}'})
try:
    with urllib.request.urlopen(req, timeout=180) as resp:
        r = json.loads(resp.read())
    content = r['choices'][0]['message'].get('content','') or r['choices'][0]['message'].get('reasoning_content','') or ''
    print(content)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
