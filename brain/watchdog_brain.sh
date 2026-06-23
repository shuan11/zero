#!/bin/bash
# brain/daemon 看门狗 — 检测心跳，超时重启
# 由 cron 每 2 分钟调用

CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"
BRAIN_HOME="/home/hjw123/.zero_brain"
HEARTBEAT="$BRAIN_HOME/.brain.heartbeat"
LOG="$CLUSTER/.brain_watchdog.log"

now=$(date +%s)

if [ -f "$HEARTBEAT" ]; then
    last=$(python3 -c "import json; print(json.load(open('$HEARTBEAT'))['time'])" 2>/dev/null)
    [ -z "$last" ] && last=0
    age=$(( now - ${last%.*} )) 2>/dev/null
    [ -z "$age" ] && age=999
    if [ "$age" -lt 120 ]; then
        exit 0
    fi
    echo "[watchdog] 心跳年龄=${age}s，超120s阈值"
fi

# 心跳超时 — 重启
MSG="[$(date '+%H:%M:%S')] ⚠️ 心跳超时(年龄=${age}s)，重启脑核..."
echo "$MSG"
echo "$MSG" >> "$LOG"

cd "$CLUSTER" || exit 1
> .brain_daemon.log
rm -rf brain/__pycache__
nohup python3 -m brain.daemon 22 >> .brain_daemon.log 2>&1 &
echo "[$(date '+%H:%M:%S')] ✅ 重启 PID=$!"
echo "[$(date '+%H:%M:%S')] ✅ 重启 PID=$!" >> "$LOG"
