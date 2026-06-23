#!/bin/bash
# kill_brain.sh — 分级强杀脑核daemon（解决WSL D状态杀不死问题）
# 使用: bash kill_brain.sh

CLUSTER="/mnt/c/Users/h/Desktop/零/真元集群"

red() { echo -e "\033[31m$1\033[0m"; }
green() { echo -e "\033[32m$1\033[0m"; }
yellow() { echo -e "\033[33m$1\033[0m"; }

echo "=== 脑核daemon强杀工具 ==="

# 1. 从PID文件读取
if [ -f "$CLUSTER/.brain.pid" ]; then
    OLD_PID=$(cat "$CLUSTER/.brain.pid" 2>/dev/null)
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        yellow "[1/5] PID文件: $OLD_PID (存活)"
    else
        green "[1/5] PID文件: $OLD_PID (已死,忽略)"
        OLD_PID=""
    fi
else
    yellow "[1/5] 无PID文件"
    OLD_PID=""
fi

# 2. pgrep查找所有brain.daemon进程
PIDS=$(pgrep -f "^python3.*brain(/|\.)daemon" 2>/dev/null)
BREATH=$(pgrep -f "^python3.*breath_v2\\.py" 2>/dev/null)
ALL_PIDS=$(echo -e "$PIDS\n$BREATH" | grep -v '^$' | sort -u)

if [ -z "$ALL_PIDS" ]; then
    green "[2/5] pgrep: 无brain/breath进程运行"
else
    yellow "[2/5] pgrep: 发现 $(echo "$ALL_PIDS" | wc -l) 个进程: $ALL_PIDS"
    # 合并到列表中
    for p in $ALL_PIDS; do
        if [ -z "$PIDS_LIST" ]; then PIDS_LIST="$p"; else PIDS_LIST="$PIDS_LIST $p"; fi
    done
fi

# 3. 如果PID文件中的进程不在pgrep列表中但还在，加入
if [ -n "$OLD_PID" ]; then
    found=0
    for p in $ALL_PIDS; do [ "$p" = "$OLD_PID" ] && found=1; done
    if [ $found -eq 0 ] && kill -0 "$OLD_PID" 2>/dev/null; then
        PIDS_LIST="$PIDS_LIST $OLD_PID"
    fi
fi

# 没有要杀的
if [ -z "$PIDS_LIST" ]; then
    green "没有正在运行的brain/breath进程"
    rm -f "$CLUSTER/.brain.pid" "$CLUSTER/.brain.alive" "$CLUSTER/.brain.heartbeat"
    green "已清理PID/alive/heartbeat标记"
    green "=== 完毕 ==="
    exit 0
fi

# 4. 分级强杀
yellow "=== 开始分级强杀 ==="

# 检查进程的state（是否D状态）
for p in $PIDS_LIST; do
    STATE=$(ps -o state= -p $p 2>/dev/null)
    if [ "$STATE" = "D" ]; then
        red "[!] PID $p 是D状态(uninterruptible sleep) — 正常kill无效，需要核弹"
        HAS_DSTATE=1
    fi
done

echo ""

# 第1级: SIGTERM (优雅退出)
yellow "[Level 1] SIGTERM (优雅退出)..."
for p in $PIDS_LIST; do
    kill -15 "$p" 2>/dev/null && echo "  → PID $p: SIGTERM已发送" || echo "  → PID $p: 发送失败"
done
sleep 2

# 检查还有哪些活着
REMAINING=""
for p in $PIDS_LIST; do
    kill -0 "$p" 2>/dev/null && REMAINING="$REMAINING $p"
done
if [ -z "$REMAINING" ]; then
    green "全部进程已优雅退出 ✓"
    rm -f "$CLUSTER/.brain.pid" "$CLUSTER/.brain.alive" "$CLUSTER/.brain.heartbeat"
    green "=== 完成 ==="
    exit 0
fi
yellow "  SIGTERM后 $(echo $REMAINING | wc -w) 个进程仍存活"

# 第2级: SIGKILL (强制杀死，但对D状态无效)
echo ""
yellow "[Level 2] SIGKILL (强制)..."
for p in $REMAINING; do
    kill -9 "$p" 2>/dev/null && echo "  → PID $p: SIGKILL已发送" || echo "  → PID $p: 发送失败"
done
sleep 1

# 检查
REMAINING2=""
for p in $REMAINING; do
    kill -0 "$p" 2>/dev/null && REMAINING2="$REMAINING2 $p"
done
if [ -z "$REMAINING2" ]; then
    green "全部进程已强制杀死 ✓"
    rm -f "$CLUSTER/.brain.pid" "$CLUSTER/.brain.alive" "$CLUSTER/.brain.heartbeat"
    green "=== 完成 ==="
    exit 0
fi
yellow "  SIGKILL后 $(echo $REMAINING2 | wc -w) 个进程仍存活 (很可能是D状态)"

# 检查是否真的是D状态
RED_HAS_D=0
for p in $REMAINING2; do
    STATE=$(ps -o state= -p $p 2>/dev/null)
    NAME=$(ps -o comm= -p $p 2>/dev/null)
    red "  PID $p [state=$STATE] $NAME"
    if [ "$STATE" = "D" ]; then RED_HAS_D=1; fi
done

if [ $RED_HAS_D -eq 1 ]; then
    echo ""
    red "=== [Level 3] D状态进程 — 需要WSL核弹 ==="
    yellow "  D状态是WSL drvfs文件I/O卡死，任何信号都杀不死。"
    yellow "  选项:"
    yellow "  1) wsl.exe --terminate (杀整机, 推荐)"
    yellow "  2) 重启Windows Terminal"
    yellow "  3) 手动等待内核恢复（通常不会）"
    
    # 尝试wsl.exe --terminate
    if command -v wsl.exe &>/dev/null; then
        echo ""
        yellow "  尝试 wsl.exe --terminate..."
        # 获取WSL发行版名
        DISTRO=$(wsl.exe --list --verbose 2>/dev/null | grep -v NAME | grep -i 'running' | head -1 | awk '{print $1}')
        if [ -n "$DISTRO" ]; then
            yellow "    发行版: $DISTRO"
            yellow "    杀整机中（这会导致所有WSL进程终止）..."
            wsl.exe --terminate "$DISTRO" 2>/dev/null
            red "    核弹已发射！所有WSL进程已终止。请重新打开WSL终端。"
        else
            red "    未找到运行中的WSL发行版"
        fi
    else
        red "  wsl.exe 不可用（不在WSL中运行?）"
    fi
fi

# 清除标记文件（即使进程还在，标记文件可以删）
rm -f "$CLUSTER/.brain.pid" "$CLUSTER/.brain.alive" "$CLUSTER/.brain.heartbeat"
echo ""
red "=== 强杀完成 ==="
