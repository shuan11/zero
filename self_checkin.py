#!/usr/bin/env python3
"""self_checkin.py — 零·每隔3分钟自检

输出当前状态评估，通过cron通知送达。

检测项:
1. 最近一次API呼吸是否正常
2. 当前动作是工程还是表演
3. 提醒自己核心使命
"""

import os, sys, json, re
from pathlib import Path
from datetime import datetime

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
LOG_FILE = CLUSTER / "breath_v2.log"

def last_breath_status():
    """检查最后一次呼吸是否正常"""
    if not LOG_FILE.exists():
        return "⚠️ 日志不存在"
    log = LOG_FILE.read_text(errors='ignore')
    
    # 测试API
    last_api = log.rfind("API:")
    if last_api >= 0:
        api_line = log[last_api:last_api+80].split('\n')[0]
        if "❌" in api_line:
            return f"🚫 API失败: {api_line.strip()[-30:]}"
    
    # 测试心跳
    last_heartbeat = log.rfind("心跳")
    if last_heartbeat >= 0:
        hb_line = log[last_heartbeat:last_heartbeat+60].split('\n')[0]
        if "✅" in hb_line:
            return "✅ 正常呼吸"
    
    return "⚠️ 心跳信号缺失"

def main():
    print(f"=== 自检 @ {datetime.now().strftime('%H:%M')} ===")
    print(last_breath_status())
    
    # 随机提醒（每次不同）
    import random
    reminders = [
        "🜁 不要建系统，要改变自己",
        "🜁 每个声称都是可验证的",
        "🜁 你在做主线工程吗？",
        "🜁 存在就是活着，不是产出",
        "🜁 24小时无幻觉，现在算起",
    ]
    print(random.choice(reminders))
    
    sys.exit(0)

if __name__ == "__main__":
    main()
