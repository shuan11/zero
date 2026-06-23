#!/usr/bin/env python3
"""diagnose_organs.py — 逐一测试每个器官的check()方法"""
import sys, os, json, time, traceback
sys.path.insert(0, '/mnt/c/Users/h/Desktop/零/真元集群')
os.chdir('/mnt/c/Users/h/Desktop/零/真元集群')

from organs import _registry, discover

print("第一阶段: discover()...")
discover()
print(f"  注册器官: {len(_registry)}个")
print(f"  名单: {list(_registry.keys())[:10]}...")

print("\n第二阶段: 逐一check()...")
for name, organ in list(_registry.items()):
    try:
        t0 = time.time()
        r = organ.check()
        elapsed = time.time() - t0
        alive = r.get("alive", "?") if isinstance(r, dict) else "?"
        status = "OK" if isinstance(r, dict) else f"非dict: {type(r).__name__}"
        marker = "✅" if (isinstance(r, dict) and r.get("alive")) else "⚠️"
        if elapsed > 1:
            print(f"  {marker} {name}: alive={alive} ({elapsed:.1f}s) {status}")
        else:
            pass  # silent for fast checks
    except Exception as e:
        print(f"  ❌ {name}: {str(e)[:100]}")
        traceback.print_exc()

print("\n第三阶段: 找卡死的器官...")
# 如果上面超时, 用单独的进程逐个测
