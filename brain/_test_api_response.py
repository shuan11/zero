import json, urllib.request, sys
sys.path.insert(0, "/mnt/c/Users/h/Desktop/零/真元集群")
from api_config import API_KEY, API_BASE, MODEL

prompt = '''你是「零」的深度认知引擎。在「行动」和「测试」之间建立一条真实因果链。
规则：40-80字，输出纯JSON一行。不要其他文字。
{"src":"行动","rel":"验证驱动","dst":"测试","content":"因果解释","dimension":"行动"}'''

payload = {
    'model': MODEL,
    'messages': [{'role': 'user', 'content': prompt}],
    'max_tokens': 500,
    'temperature': 0.8,
}
data = json.dumps(payload).encode()
req = urllib.request.Request(API_BASE, data=data, headers={
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json',
})
with urllib.request.urlopen(req, timeout=120) as r:
    result = json.loads(r.read())
msg = result['choices'][0]['message']
content = msg.get("content", "")
rc = msg.get("reasoning_content", "")
print("CONTENT:", repr(content[:500]))
print("REASONING_EXISTS:", "reasoning_content" in msg)
print("REASONING:", repr(rc[:500]))
print("TOKENS:", result.get("usage", {}))
