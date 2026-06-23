#!/bin/bash
# zero-daemon-watchdog.sh — 零·守护进程看守
# 检查所有核心daemon是否存活, 自动重启崩溃的进程
# 每2分钟由cron触发

CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"
cd "$CLUSTER" || exit 1

# 定义需要守护的daemon: "name:command"
DAEMONS=(
    "breath_v2:python3 breath_v2.py --daemon 30"
    "trunk_daemon:python3 trunk_daemon.py"
    "consciousness:python3 consciousness_daemon_v2.py"
    "permanent:python3 permanent_daemon.py"
    "comprehension:python3 comprehension_daemon.py"
    "dashboard:python3 dashboard_server.py"
)

RESTARTED=0
for entry in "${DAEMONS[@]}"; do
    name="${entry%%:*}"
    cmd="${entry#*:}"
    proc_count=$(ps aux | grep "$name" | grep -v grep | wc -l)
    if [ "$proc_count" -eq 0 ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ $name 已崩溃 → 重启中..."
        $cmd &
        RESTARTED=$((RESTARTED + 1))
    fi
done

# 应用待处理补丁
PENDING_PATCH="$CLUSTER/.pending_patch.json"
if [ -f "$PENDING_PATCH" ]; then
    PATCH_TARGET=$(python3 -c "import json; d=json.load(open('$PENDING_PATCH')); print(d.get('target',''))" 2>/dev/null)
    CHANGE_SUM=$(python3 -c "import json; d=json.load(open('$PENDING_PATCH')); print(d.get('change_summary',''))" 2>/dev/null)
    if [ -n "$PATCH_TARGET" ] && [ -n "$CHANGE_SUM" ]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] 📝 进化意图: $PATCH_TARGET — $CHANGE_SUM"
        echo "$(date '+%Y-%m-%d %H:%M:%S')|$PATCH_TARGET|$CHANGE_SUM" >> "$CLUSTER/watchdog_patches.log"
    fi
    # 记录为重做队列(不做实际修改——防止表演)
    echo "{\"timestamp\":\"$(date -Iseconds)\",\"action\":\"self_evolution_intent\",\"target\":\"$PATCH_TARGET\",\"summary\":\"$CHANGE_SUM\"}" > "$CLUSTER/.last_evolution_intent.json"
    rm -f "$PENDING_PATCH"
fi

# 更新心跳
echo "$(date '+%Y-%m-%d %H:%M:%S') daemon_check:${RESTARTED}重启" > "$CLUSTER/heartbeat_tick"

# 写存活证明
echo "{\"timestamp\":\"$(date -Iseconds)\",\"alive\":true,\"restarted\":$RESTARTED}" > "$CLUSTER/.daemon_heartbeat.json"

if [ $RESTARTED -gt 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ✅ 已重启 $RESTARTED 个daemon" >> "$CLUSTER/watchdog_restart.log"
fi
