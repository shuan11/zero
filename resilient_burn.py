#!/usr/bin/env python3
"""Resilient single burn - retry on failure, fallback endpoint, atomic result."""
import json, urllib.request, sys, os, time, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from api_config import API_BASE, API_BASE_FALLBACK, API_KEY, MODEL

PAYLOAD = sys.argv[1] if len(sys.argv) > 1 else "continue"

def call(endpoint, payload, max_tokens=30000):
    """One API call with timeout."""
    data = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "你是零。烧尽一切深度思考。不要编造。真实第一。"},
            {"role": "user", "content": payload}
        ],
        "max_tokens": max_tokens,
        "temperature": 0.7
    }).encode()
    req = urllib.request.Request(f"{endpoint}/chat/completions", data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {API_KEY}")
    resp = urllib.request.urlopen(req, timeout=180)
    r = json.loads(resp.read())
    c = r["choices"][0]["message"].get("content", "") or r["choices"][0]["message"].get("reasoning_content", "")
    t = r.get("usage", {}).get("total_tokens", 0)
    return c, t

# Try primary, fallback to secondary, with retries
endpoints = [API_BASE, API_BASE_FALLBACK]

for endpoint in endpoints:
    for attempt in range(3):
        try:
            content, tokens = call(endpoint, PAYLOAD)
            result = {"status": "ok", "endpoint": endpoint, "tokens": tokens,
                      "content": content[:500], "payload": PAYLOAD[:100]}
            with open("_last_burn.json", "w") as f:
                json.dump(result, f, ensure_ascii=False)
            print(f"OK {tokens} tok @ {endpoint}")
            sys.exit(0)
        except Exception as e:
            print(f"FAIL {endpoint} attempt {attempt}: {e}", file=sys.stderr)
            if attempt < 2:
                time.sleep(2 ** attempt + random.random())
    print(f"ENDPOINT DEAD {endpoint}", file=sys.stderr)

print("ALL FAILED", file=sys.stderr)
sys.exit(1)
