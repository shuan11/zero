#!/bin/bash
# 零·UiBot燃料燃烧器通知链
# 每60秒读取Windows侧燃烧器心跳，写入SYSTEM通知兼容格式
# 使燃烧活动在Hermes会话中可见

HEARTBEAT="/mnt/c/Users/h/Desktop/零/真元集群/uibot_heartbeat.json"
JOURNAL="/mnt/c/Users/h/Desktop/零/真元集群/uibot_journal.json"
LAST_CYCLE_FILE="/tmp/.uibot_last_cycle"

LAST_CYCLE=0
if [ -f "$LAST_CYCLE_FILE" ]; then
    LAST_CYCLE=$(cat "$LAST_CYCLE_FILE")
fi

if [ -f "$HEARTBEAT" ] && [ -f "$JOURNAL" ]; then
    # 读心跳
    HB=$(python3 -c "
import json
try:
    with open('$HEARTBEAT', 'rb') as f:
        d = json.loads(f.read().decode('utf-8', errors='replace'))
    print(f'cycle={d.get(\"cycle\",0)} ok={d.get(\"api_ok\",False)}')
except: print('error')
" 2>/dev/null)

    CYCLE=$(echo "$HB" | grep -oP 'cycle=\K\d+')
    API_OK=$(echo "$HB" | grep -oP 'ok=\K\w+')

    if [ -n "$CYCLE" ] && [ "$CYCLE" != "$LAST_CYCLE" ]; then
        # 有新的cycle——获取最新journal条目
        python3 -c "
import json
with open('$JOURNAL', 'rb') as f:
    data = json.loads(f.read().decode('utf-8', errors='replace'))
if data:
    e = data[-1]
    print(f'🔥 [UiBot] #{e.get(\"cycle\")} [{e.get(\"dim\",\"?\")}] {e.get(\"src\",\"?\")}→{e.get(\"dst\",\"?\")}')
    c = str(e.get('content',''))[:100]
    if c:
        print(f'   {c}')
    print(f'   provider={e.get(\"provider\",\"?\")} tokens={e.get(\"tokens\",0)}')
else:
    print('⏳ 等待第一轮...')
" 2>/dev/null

        echo "$CYCLE" > "$LAST_CYCLE_FILE"
    fi
fi
