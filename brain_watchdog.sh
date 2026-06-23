#!/bin/bash
# brain_watchdog.sh — 脑核守护进程看门狗
# 每5分钟检查 daemon 是否活着，死了就重启
CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"
# ★ ext4 PID路径 — brain/daemon.py 写 PID 到 /home/hjw123/.zero_brain/ 避免 D状态
#   看门狗必须检查同一路径，否则每分钟误判daemon死亡
PIDFILE="/home/hjw123/.zero_brain/.brain.pid"
LOGFILE="$CLUSTER/.brain_watchdog.log"

# 检查daemon是否运行
if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        # 活着，正常退出
        exit 0
    fi
fi

# daemon死了，重启
cd "$CLUSTER"
rm -rf brain/__pycache__
nohup python3 -m brain.daemon 25 >> "$CLUSTER/.brain_daemon.log" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PIDFILE"
echo "$(date '+%Y-%m-%d %H:%M:%S') 看门狗重启 daemon PID=$NEW_PID" >> "$LOGFILE"
echo 重启 daemon PID=$NEW_PID
