
"""
api_config.py — 零·API统一配置 v4
端点: inferaichat.com (已验证连通)
模型: claude-opus-4-8 | 200K上下文
"""

import os
import itertools
import threading
import json
import urllib.request
from pathlib import Path

API_KEYS = [
    "sk-83e2bcea9b3ba57d431fa06419de8b2a1fe8d27c5747a8312ed29f787b13ca88",
]

ENDPOINTS = [
    "https://inferaichat.com/v1/chat/completions",
]

MODEL = "deepseek-v4-pro"
MAX_TOKENS = 8000

# 向后兼容 — 旧版代码仍引用的变量
API_KEY = API_KEYS[0]
API_BASE = ENDPOINTS[0]
api_url = ENDPOINTS[0]
CONTEXT_WINDOW = 1000000

GPT5_CONFIG = {
    "api_key": os.environ.get("GPT5_KEY", ""),
    "endpoint": "https://shujuhuantoken.com/v1/chat/completions",
    "model": "gpt-5.5",
    "context_window": 1050000,
    "max_output": 128000,
    "type": "limited_tokens_unlimited_time",
}

def call_gpt55(prompt, system_prompt=None, max_tokens=32000, temperature=0.7, timeout=180):
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})
    payload = {
        "model": GPT5_CONFIG["model"],
        "messages": messages,
        "max_tokens": min(max_tokens, GPT5_CONFIG["max_output"]),
        "temperature": temperature,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GPT5_CONFIG["endpoint"], data=data, headers={
        "Authorization": f"Bearer {GPT5_CONFIG['api_key']}",
        "Content-Type": "application/json",
        "User-Agent": "Zero/1.0",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read())
    content = result["choices"][0]["message"].get("content", "")
    return content, result.get("usage", {})

_DEAD_SUFFIXES = set()
_DEAD_KEY_FILE = Path(__file__).resolve().parent / ".dead_keys.json"
try:
    if _DEAD_KEY_FILE.exists():
        data = json.loads(_DEAD_KEY_FILE.read_text())
        _DEAD_SUFFIXES.update(data.get("dead_suffixes", []))
except: pass

def _key_suffix(key):
    return key[-8:] if len(key) >= 8 else key

def _is_dead(key):
    return _key_suffix(key) in _DEAD_SUFFIXES

def _build_channels():
    channels = []
    for k in API_KEYS:
        if not k: continue
        if _is_dead(k): continue
        for e in ENDPOINTS:
            channels.append((k, e))
    if not channels:
        channels = [(k, e) for k in API_KEYS if k for e in ENDPOINTS]
    return channels

_CHANNELS = _build_channels()
_channel_cycle = itertools.cycle(_CHANNELS) if _CHANNELS else itertools.cycle([("", ENDPOINTS[0])])
_cycle_lock = threading.Lock()

def mark_key_dead(key):
    suffix = _key_suffix(key)
    if suffix in _DEAD_SUFFIXES: return
    _DEAD_SUFFIXES.add(suffix)
    global _CHANNELS, _channel_cycle
    _CHANNELS = _build_channels()
    _channel_cycle = itertools.cycle(_CHANNELS) if _CHANNELS else _channel_cycle
    try:
        _DEAD_KEY_FILE.write_text(json.dumps({"dead_suffixes": list(_DEAD_SUFFIXES)}, ensure_ascii=False))
    except: pass

def get_next_channel():
    with _cycle_lock:
        return next(_channel_cycle)

def get_next_key():
    return get_next_channel()[0]

def get_next_endpoint():
    return get_next_channel()[1]

def api_headers(key=None):
    ch = get_next_channel()
    return {"Authorization": f"Bearer {key or ch[0]}", "Content-Type": "application/json"}

def api_request(payload, key=None, endpoint=None, timeout=120):
    ch = get_next_channel()
    use_key = key or ch[0]
    use_ep = endpoint or ch[1]
    data = json.dumps(payload).encode()
    req = urllib.request.Request(use_ep, data=data, headers={
        "Authorization": f"Bearer {use_key}",
        "Content-Type": "application/json",
        "User-Agent": "Zero/1.0 (api_config v4)",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        result = json.loads(r.read())
    return result, use_key, use_ep

if __name__ == "__main__":
    alive = [k[-8:] for k in API_KEYS if k and not _is_dead(k)]
    dead = [k[-8:] for k in API_KEYS if k and _is_dead(k)]
    print(f"Alive keys: {alive}")
    print(f"Dead keys: {dead}")
    print(f"Active channel count: {len(_CHANNELS)}")
    print(f"Model: {MODEL}")
    print(f"Endpoint: {ENDPOINTS[0]}")
