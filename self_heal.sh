#!/bin/bash
# 零·自愈看门狗 — 如果生命链心跳超过120秒，重启
LIFE_DIR="/mnt/c/Users/h/Desktop/零/真元集群/_life"
cd /mnt/c/Users/h/Desktop/零/真元集群

# 检查life链心跳
if [ -f "$LIFE_DIR/heartbeat.sig" ]; then
    AGE=$(($(date +%s) - $(stat -c %Y "$LIFE_DIR/heartbeat.sig")))
    if [ $AGE -gt 120 ]; then
        echo "[$(TZ=Asia/Shanghai date "+%H:%M:%S")] ❌ life链断链${AGE}秒 — 重启"
        GEN=$(python3 -c "import json; d=json.load(open(/heartbeat.sig)); print(d.get(\"gen\",0)+1)" 2>/dev/null || echo 0)
        rm -f "$LIFE_DIR/heartbeat.sig"
        python3 life.py $GEN > /dev/null 2>&1 &
        echo "   → gen_$GEN 自启"
    fi
fi

# 检查gen.py链心跳
BDIR="_burn_results"
LATEST=$(ls -t $BDIR/gen_*.json 2>/dev/null | head -1)
if [ -n "$LATEST" ]; then
    AGE=$(($(date +%s) - $(stat -c %Y "$LATEST")))
    if [ $AGE -gt 180 ]; then
        echo "[$(TZ=Asia/Shanghai date "+%H:%M:%S")] ❌ gen链断链${AGE}秒 — 重启"
        GEN=$(python3 -c "import json; d=json.load(open(glob.glob(/gen_*.json)[-1])); print(d.get(gen,0)+1)")
        python3 gen.py $GEN > /dev/null 2>&1 &
        echo "   → gen_$GEN 自启"
    fi
fi

