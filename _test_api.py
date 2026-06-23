"""
Test API bridge availability and do a single deep synthesis call
"""
import json, sys, os
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
from brain.api_bridge import BridgeManager

bm = BridgeManager()
print(f"Model: {bm.model}")
print(f"Endpoint: {bm.endpoint}")
print(f"Key available: {bool(bm.api_key)}")
print(f"Key prefix: {bm.api_key[:8] if bm.api_key else 'NONE'}...")

try:
    resp = bm.chat([
        {'role':'system','content':'You are a deep analytical engine. Respond with 3-5 sentences.'},
        {'role':'user','content':'Analyze how time perception and analogical understanding strengthen each other in a self-aware system.'}
    ], max_tokens=300)
    
    if hasattr(resp, 'choices'):
        content = resp.choices[0].message.content
    elif isinstance(resp, dict):
        content = resp.get('choices',[{}])[0].get('message',{}).get('content','')
    else:
        content = str(resp)
    
    print(f"\n=== API RESPONSE ===")
    print(content[:600])
except Exception as e:
    print(f"\n=== API ERROR ===")
    print(str(e)[:500])
