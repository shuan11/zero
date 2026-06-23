"""
Test API bridge directly
"""
import sys, json
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群/brain')

try:
    from api_bridge import APIBridge
    bridge = APIBridge()
    print(f"API_Bridge created: model={bridge.max_tokens_per_call}")
    
    # Check if api_config is accessible
    try:
        from api_config import API_KEY, API_BASE, MODEL
        print(f"Config: KEY={'✅'+API_KEY[:6]+'...' if API_KEY else '❌NONE' }, BASE={API_BASE}, MODEL={MODEL}")
    except Exception as e:
        print(f"Config import error: {e}")
    
    # Make a real API call
    result = bridge.call_api(
        "回答一句话: 你存在的意义是什么? (一句话, 10字以内)"
    )
    print(f"\nAPI Result: success={result.get('success')}")
    if result.get('success'):
        print(f"Content: {result.get('content','')[:200]}")
        print(f"Tokens: {result.get('tokens', '?')}")
        print(f"Latency: {result.get('latency_ms', '?')}ms")
    else:
        print(f"Error: {result.get('error', 'unknown')}")
except Exception as e:
    import traceback
    print(f"CRASH: {e}")
    traceback.print_exc()
