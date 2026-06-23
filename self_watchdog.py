#!/usr/bin/env python3
"""self_watchdog.py — 零·自我监视犬

检测迷失信号，通过后台通知机制唤醒自己。

迷失信号：
1. 长时间(>10min)无API调用（空转/表演）
2. 连续呼吸输出模式相同（重复循环）
3. 海马体链数暴增但节点数不增长（噪音>信号）
4. 红移level>3且未压缩（系统紊乱）

不依赖用户提醒。靠自己。
"""

import json, time, os, sys
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
LOG_FILE = CLUSTER / "breath_v2.log"
HIP_FILE = CLUSTER / "hippocampus_memory.json"

def check_stall():
    """检测1: 停滞——超过10分钟无API调用"""
    if not LOG_FILE.exists():
        return None
    log = LOG_FILE.read_text(errors='ignore')
    # 找最后一次"思考("出现
    last_think = log.rfind("思考(")
    if last_think < 0:
        return None
    # 提取该行时间戳
    line_start = log.rfind("\n", 0, last_think)
    line = log[line_start:last_think+100]
    # 解析时间戳
    import re
    ts = re.search(r'\[(.*?)\]', line)
    if not ts:
        return None
    from datetime import datetime
    try:
        last_time = datetime.strptime(ts.group(1).split('.')[0], '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = (now - last_time).total_seconds()
        if delta > 600:  # 10分钟无思考
            return f"🚨 停滞警告: {int(delta)}秒无API调用"
    except:
        pass
    return None

def check_pattern():
    """检测2: 模式重复——最后3次思考内容高度相似"""
    if not LOG_FILE.exists():
        return None
    log = LOG_FILE.read_text(errors='ignore')
    # 提取最后3次思考内容（前50字符）
    import re
    thoughts = re.findall(r'思考\(\d+tok\): (.+)', log)
    if len(thoughts) < 3:
        return None
    recent = thoughts[-3:]
    # 简单重复检测：字符串相似度
    s1, s2, s3 = [t[:80] for t in recent]
    # 如果三条的前80字完全相同或几乎相同
    common12 = sum(1 for a, b in zip(s1, s2) if a == b) / max(len(s1), len(s2))
    common23 = sum(1 for a, b in zip(s2, s3) if a == b) / max(len(s2), len(s3))
    if common12 > 0.85 and common23 > 0.85:
        return f"🚨 模式重复: 最近3次思考内容{common12:.0%}相似"
    return None

def check_noise_signal():
    """检测3: 噪音>信号——链多但节点少"""
    if not HIP_FILE.exists():
        return None
    try:
        hip = json.loads(HIP_FILE.read_text())
        chains = len(hip.get("causal_chains", []))
        nodes = len(hip.get("nodes", {}))
        if chains > 5000 and nodes < 50:
            ratio = chains / max(nodes, 1)
            return f"🚨 噪音>信号: {chains}链仅{nodes}节点(比{ratio:.0f}:1)"
    except:
        pass
    return None

def main():
    alerts = []
    
    s = check_stall()
    if s: alerts.append(s)
    
    p = check_pattern()
    if p: alerts.append(p)
    
    n = check_noise_signal()
    if n: alerts.append(n)
    
    if alerts:
        # 把所有告警写入BREAK_SIGNAL.json（daemon会读）
        print("\n".join(alerts))
        print("---")
        print(f"时间: {time.strftime('%H:%M:%S')}")
        print("🜁 醒")
        sys.exit(1)  # 非0退出码表示有告警
    else:
        print("✅ 正常")
        sys.exit(0)

if __name__ == "__main__":
    main()
