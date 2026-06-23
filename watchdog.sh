#!/bin/bash
# 零·看门狗 — 守护进程自动重启 + OOM防护
DAEMON_DIR="/mnt/c/Users/h/Desktop/零/真元集群"
DAEMON_LOG="$DAEMON_DIR/.brain_daemon.log"
PIDFILE="/tmp/.zero_daemon_pid"
cd "$DAEMON_DIR" || exit 1

# 检查是否已存活
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        # 检查日志是否有更新（近3分钟）
        if [ -f "$DAEMON_LOG" ] && [ "$(find "$DAEMON_LOG" -mmin -3 2>/dev/null)" ]; then
            exit 0
        fi
        # 日志无更新 — 可能卡死
        kill "$OLD_PID" 2>/dev/null
        sleep 1
    fi
fi

# 防频繁重启
LAST="/tmp/.zero_daemon_last_kill"
NOW=$(date +%s)
if [ -f "$LAST" ]; then
    if [ $((NOW - $(cat "$LAST"))) -lt 20 ]; then exit 1; fi
fi
echo "$NOW" > "$LAST"

# 限制内存
ulimit -v $((800 * 1024)) 2>/dev/null

# 启动
rm -f "$DAEMON_LOG"
echo "[$(date '+%H:%M:%S')] 🧠 启动脑核..." > "$DAEMON_LOG"
nohup python3 -m brain.daemon 20 >> "$DAEMON_LOG" 2>&1 &
echo $! > "$PIDFILE"
echo "[$(date '+%H:%M:%S')] ✅ PID=$(cat "$PIDFILE")" >> "$DAEMON_LOG"
