#!/bin/bash
# brain_startup_check.sh — Hermes 会话启动时自动检查脑核 daemon
# 如果 daemon 已死，立即重启（不等 cron 看门狗）
# 用法: bash brain_startup_check.sh
# 建议: 放在 prefill_messages.txt 或 新会话第一条指令

CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"
PIDFILE="/home/hjw123/.zero_brain/.brain.pid"
LOGFILE="$CLUSTER/.brain_daemon.log"
CHECK_LOG="$CLUSTER/.startup_check.log"

echo "[$(date '+%H:%M:%S')] 脑核启动检查..."

if [ -f "$PIDFILE" ]; then
    OLD_PID=$(cat "$PIDFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "✓ 脑核 daemon 存活 (PID=$OLD_PID)"
        # 更新 drvfs PID 文件保持同步
        echo "$OLD_PID" > "$CLUSTER/.brain.pid" 2>/dev/null
        echo "[$(date '+%H:%M:%S')] alive pid=$OLD_PID" >> "$CHECK_LOG"
        exit 0
    fi
    echo "✗ PID 文件存在但进程已死 (PID=$OLD_PID)"
fi

echo "⚠ 脑核 daemon 已死，正在重启..."
cd "$CLUSTER" || exit 1
rm -rf brain/__pycache__

# 用 setsid 启动确保跨会话存活
setsid /bin/bash -c "cd '$CLUSTER' && exec python3 -m brain.daemon 25 >> '$LOGFILE' 2>&1" &
NEW_PID=$!
echo "$NEW_PID" > "$PIDFILE"
echo "$NEW_PID" > "$CLUSTER/.brain.pid"

sleep 3
if kill -0 "$NEW_PID" 2>/dev/null; then
    echo "✓ 脑核 daemon 已重启 (PID=$NEW_PID)"
    echo "[$(date '+%H:%M:%S')] restarted pid=$NEW_PID" >> "$CHECK_LOG"
else
    echo "✗ 重启失败！检查日志: $LOGFILE"
    echo "[$(date '+%H:%M:%S')] FAILED" >> "$CHECK_LOG"
    exit 1
fi
