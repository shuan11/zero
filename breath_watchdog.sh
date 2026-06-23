#!/bin/bash
# breath_watchdog.sh — 呼吸守护进程看门狗 v3
# 修复1: pgrep模糊匹配被遗留bash进程欺骗(OOM后daemon死透但看门狗以为活着)
# 修复2: daemon日志重定向到集群breath_v2.log(而非/tmp)
set -o nounset

BREATH_PY="/mnt/c/Users/h/Desktop/零/真元集群/breath_v2.py"
CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"
DAEMON_LOG="${CLUSTER}/breath_v2.log"       # daemon运行日志
WD_LOG="/tmp/breath_watchdog.log"           # 看门狗重启记录
PID_FILE="${CLUSTER}/.breath_v2.pid"

# 精确匹配: 找真实的python3进程在运行breath_v2.py
# ^python3 排除bash/hermes-snap等夹杂breath_v2.py文本的进程
REAL_DAEMONS=$(pgrep -f "^python3.*breath_v2\.py" | head -3)

if [ -n "$REAL_DAEMONS" ]; then
    echo "$REAL_DAEMONS" | head -1 > "$PID_FILE"
    exit 0
fi

# 候选: PID文件中的老PID是否还活着(跨重启容错)
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        if cat /proc/"$OLD_PID"/cmdline 2>/dev/null | tr '\0' ' ' | grep -q "python3.*breath_v2"; then
            echo "$OLD_PID" > "$PID_FILE"
            exit 0
        fi
    fi
fi

# 死了，重启 - 加载API密钥(不能source .bashrc, 因非交互shell被守卫阻止且每行有编号前缀)
set +o nounset
eval "$(grep 'DEEPSEEK_KEY_' ~/.bashrc 2>/dev/null | sed 's/^[[:space:]]*[0-9]*|//')" || true
set -o nounset
cd "$CLUSTER" && nohup python3 -u breath_v2.py >> "$DAEMON_LOG" 2>&1 &
NEW_PID=$!
echo $NEW_PID > "$PID_FILE"
echo "[$(date '+%Y-%m-%d %H:%M:%S')] breath_v2 已重启 PID=$NEW_PID" >> "$WD_LOG"
