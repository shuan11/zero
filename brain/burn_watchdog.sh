#!/bin/bash
# 连续燃烧看门狗 — 每2分钟检查gen_连续燃烧.py是否在运行
# 如果不在就启动

BURN_DIR="/mnt/c/Users/h/Desktop/零/真元集群"
BURN_LOG="$BURN_DIR/.brain_burn.log"
BURN_PIDFILE="$BURN_DIR/.brain_burn.pid"

# 检查是否有gen_连续燃烧进程
BURN_PIDS=$(pgrep -f "gen_连续燃烧" | grep -v pgrep | head -5)
if [ -z "$BURN_PIDS" ]; then
    echo "[$(date +%H:%M:%S)] 燃烧进程已死，重新启动" >> "$BURN_LOG"
    cd "$BURN_DIR" && nohup python3 -B brain/gen_连续燃烧.py --cycles=60 >> "$BURN_DIR/.brain_burn.log" 2>&1 &
    echo $! > "$BURN_PIDFILE"
    echo "[$(date +%H:%M:%S)] 重启完成 PID=$!" >> "$BURN_LOG"
else
    # 记录心跳
    echo "$(date +%s)" > "$BURN_DIR/.brain_burn_heartbeat2"
fi
