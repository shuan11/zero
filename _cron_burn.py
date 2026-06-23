#!/usr/bin/env python3
import json, urllib.request, sys, os, time
sys.path.insert(0, '.')
from api_config import *
sv = json.load(open('state_vector.json'))
bs = json.load(open('burn_stats.json'))
sig = json.load(open('_life/heartbeat.sig')) if os.path.exists('_life/heartbeat.sig') else {'gen': 0}
d = json.dumps({
    'model': MODEL,
    'messages': [{'role': 'user', 'content': 'cycle=%s burn=%s. life_chain_gen_%s. one sentence insight.' % (sv['cycle'], bs['burn_count'], sig.get('gen','?'))}],
    'max_tokens': 30000
}).encode()
req = urllib.request.Request('%s/chat/completions' % API_BASE, data=d, method='POST')
req.add_header('Content-Type', 'application/json')
req.add_header('Authorization', 'Bearer %s' % API_KEY)
resp = urllib.request.urlopen(req, timeout=600)
r = json.loads(resp.read())
c = r['choices'][0]['message'].get('content', '') or r['choices'][0]['message'].get('reasoning_content', '')
t = r.get('usage', {}).get('total_tokens', 0)
print(json.dumps({'gen': sig.get('gen'), 't': t, 'c': c[:200]}, ensure_ascii=False))
