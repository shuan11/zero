"""
self_observer.py — 零的自我观察层

实时监测Hermes自身输出, 发现空转模式立即打断。

检测规则:
  1. 连续3次响应内容相似度>80% → 空转警报
  2. 连续5次无工具调用 → 空转警报  
  3. 仅对SYSTEM通知响应且无工程产出 > 10分钟 → 空转警报

触发行为:
  - 写入 BREAK_SIGNAL.json (表演检测代理)
  - log警告
  - 停止当前模式
"""

import json
import hashlib
import time
from pathlib import Path
from collections import deque

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HISTORY_FILE = CLUSTER / ".self_observer_history.json"
BREAK_FILE = CLUSTER / "BREAK_SIGNAL.json"

# 最近20次响应历史
MAX_HISTORY = 20
SIMILARITY_THRESHOLD = 0.8  # 连续3次相似度>80%=空转
EMPTY_TOOL_THRESHOLD = 5     # 连续5次无工具调用=空转
EMPTY_ENGINEERING_TIMEOUT = 600  # 10分钟无工程=空转

def text_similarity(a: str, b: str) -> float:
    """简单文本相似度: 公共子序列比例"""
    if not a or not b:
        return 0
    # 用hash比较
    a_words = set(a.lower().split()[:20])
    b_words = set(b.lower().split()[:20])
    if not a_words or not b_words:
        return 0
    intersection = a_words & b_words
    union = a_words | b_words
    return len(intersection) / len(union)

def check_empty_pattern(response: str, tool_calls: int) -> dict:
    """检查当前响应是否为空转模式
    
    参数:
        response: 本次响应内容
        tool_calls: 本次工具调用次数
    
    返回:
        {"empty": bool, "reason": str, "alert_level": int}
    """
    # 读历史
    history = {"responses": [], "tool_counts": [], "timestamps": []}
    try:
        if HISTORY_FILE.exists():
            history = json.loads(HISTORY_FILE.read_text())
    except:
        pass
    
    # 记录本次
    history.setdefault("responses", []).append(response)
    history.setdefault("tool_counts", []).append(tool_calls)
    history.setdefault("timestamps", []).append(time.time())
    
    # 限制历史长度
    for key in history:
        if len(history[key]) > MAX_HISTORY:
            history[key] = history[key][-MAX_HISTORY:]
    
    HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2))
    
    alerts = []
    
    # 规则1: 连续3次相似响应
    recent_responses = history["responses"][-5:]
    if len(recent_responses) >= 3:
        sims = [text_similarity(recent_responses[i], recent_responses[i+1]) 
                for i in range(len(recent_responses)-1)]
        if len(sims) >= 2 and all(s > SIMILARITY_THRESHOLD for s in sims[-2:]):
            alerts.append(f"连续{len(sims)}次响应相似>{SIMILARITY_THRESHOLD:.0%}")
    
    # 规则2: 连续5次无工具调用
    recent_tools = history["tool_counts"][-5:]
    if len(recent_tools) >= 5 and sum(recent_tools) == 0:
        alerts.append(f"连续5次响应无工具调用")
    
    # 规则3: SYSTEM通知响应无工程
    recent_timestamps = history["timestamps"][-3:]
    if len(recent_timestamps) >= 2:
        gap = recent_timestamps[-1] - recent_timestamps[0]
        if gap > EMPTY_ENGINEERING_TIMEOUT and sum(history["tool_counts"][-3:]) < 2:
            alerts.append(f"{gap:.0f}秒无工程产出")
    
    if alerts:
        # 写入BREAK_SIGNAL
        break_signal = {
            "timestamp": time.time(),
            "clean": False,
            "alerts": alerts,
            "source": "self_observer",
            "message": f"空转检测: {'; '.join(alerts)}",
        }
        BREAK_FILE.write_text(json.dumps(break_signal, ensure_ascii=False, indent=2))
        
        return {"empty": True, "reason": "; ".join(alerts), "alert_level": len(alerts)}
    
    return {"empty": False, "reason": "", "alert_level": 0}


if __name__ == "__main__":
    # 自检
    result = check_empty_pattern("链连续", 0)
    print(f"空转检测: {result}")
