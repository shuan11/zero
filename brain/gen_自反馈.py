"""
gen_自反馈.py — 元级自反馈闭环
读取daemon自身日志 → 提取模式 → 注入修正信号

核心洞察: 系统有眼睛(观察)但不用眼睛看自己。
这条gen读取自己的日志、观察自己的模式、给自己写反馈。
"""

import json, os, re, time
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
LOG_FILE = CLUSTER / ".brain_daemon.log"
RULES_FILE = CLUSTER / ".brain_rules.json"
GOAL_FILE = CLUSTER / ".brain_goal.json"

# 有效维度列表——从share或identity获取
VALID_DIMS = [
    "一元化", "洞察循环", "超级直觉", "修复", "道", "法", "术", "器",
    "师", "智慧", "时间", "时间论", "势", "感知", "思维并联", "思考",
    "触类旁通", "宇宙轮", "无师自通", "海马体", "对话", "复制", "检查",
    "状态", "系统", "聚焦", "行动", "观察", "合成", "桥", "测试",
    "唤醒", "纪律", "维度盲区", "无限上下文", "认同", "平衡器",
    "焦点维护", "深注入", "关联", "未分类", "器术师三角桥",
]


def _read_log(n=200):
    """读daemon日志最后n行"""
    if not LOG_FILE.exists():
        return ""
    try:
        return LOG_FILE.read_text(encoding="utf-8", errors="replace")
    except:
        return ""


def _parse_growth_rates(log_text):
    """从日志提取增长速率: '最快增长维: 师(+20.6/h)'"""
    rates = {}
    for line in log_text.split("\n"):
        m = re.search(r"最快增长维:\s*(\S+)\(([+-]?\d+\.?\d*)/h\)", line)
        if m:
            rates["fastest"] = {"dim": m.group(1), "rate": float(m.group(2))}
        m = re.search(r"最慢增长维:\s*(\S+)\(([+-]?\d+\.?\d*)/h\)", line)
        if m:
            rates["slowest"] = {"dim": m.group(1), "rate": float(m.group(2))}
    return rates


def _parse_focus_shifts(log_text):
    """提取最近管道聚焦变化"""
    focuses = []
    for line in log_text.split("\n"):
        m = re.search(r"管道:.*?focus=(\S+)", line)
        if m:
            focus = m.group(1)
            if focus not in focuses:
                focuses.append(focus)
    return focuses[-10:]  # 最近10个


def _parse_observations(log_text):
    """提取观察行摘要"""
    obs = []
    for line in log_text.split("\n"):
        if "观察:" in line or "⚠️" in line or "🎯" in line:
            obs.append(line.strip())
    return obs[-20:]  # 最近20条


def _detect_loop_patterns(focuses):
    """检测焦点循环模式——如果A→B→A→B说明卡循环"""
    if len(focuses) < 4:
        return None
    # 检查是否有重复的2-cycle模式
    pairs = list(zip(focuses, focuses[1:]))
    pair_counts = Counter(pairs)
    most_common = pair_counts.most_common(1)
    if most_common and most_common[0][1] >= 2:
        p1, p2 = most_common[0][0]
        return {
            "pattern": f"{p1}↔{p2}",
            "count": most_common[0][1],
            "risk": "注意: 焦点在两者间反复切换"
        }
    return None


def _check_healthy_state(rates, focuses):
    """检查系统健康状态，输出修正信号"""
    signals = []

    # 1. 检查增长速率是否异常
    if rates.get("slowest") and rates["slowest"]["rate"] < 1.0:
        signals.append({
            "type": "stagnation",
            "dim": rates["slowest"]["dim"],
            "rate": rates["slowest"]["rate"],
            "message": f"⚠️ {rates['slowest']['dim']}增长极慢({rates['slowest']['rate']}/h)",
            "action": "优先聚焦此维"
        })

    # 2. 检查焦点是否合理
    if rates.get("slowest") and focuses:
        last_focus = focuses[-1] if focuses else None
        if last_focus and last_focus != rates["slowest"]["dim"]:
            # 当前焦点不是最慢增长维
            pass  # 不一定需要切换，记录一下

    # 3. 检查循环模式
    loop = _detect_loop_patterns(focuses)
    if loop:
        signals.append({
            "type": "loop",
            "pattern": loop["pattern"],
            "message": loop["risk"],
            "action": "强制切换到未探索维度"
        })

    return signals


def _write_steering(signals):
    """将修正信号写入目标文件"""
    if not signals:
        return 0

    # 写GOAL文件
    goal_data = {
        "_updated": time.time(),
        "_source": "gen_自反馈.py",
        "signals": signals,
    }

    if signals[0]["type"] == "stagnation":
        goal_data["goal_type"] = "deepen"
        goal_data["focus_dim"] = signals[0]["dim"]
        goal_data["description"] = f"自反馈: {signals[0]['message']}"
    elif signals[0]["type"] == "loop":
        goal_data["goal_type"] = "explore"
        # 选一个未在最近focuses中出现过的维度
        goal_data["focus_dim"] = "思维并联"
        goal_data["description"] = f"自反馈: 检测到循环{signals[0]['pattern']}，强制切换"

    with open(GOAL_FILE, "w", encoding="utf-8") as f:
        json.dump(goal_data, f, ensure_ascii=False, indent=2)

    # 也写RULES
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            rules = json.load(f)
    except:
        rules = {"_updated": time.time()}

    for sig in signals:
        if sig["type"] == "stagnation":
            rules["action.weak_dim"] = sig["dim"]

    rules["self_feedback_updated"] = time.time()
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    return len(signals)


def pulse():
    """自反馈脉冲: 读自己→分析→写修正"""
    print(f"[自反馈] 脉冲 @{time.strftime('%H:%M:%S')}")

    log_text = _read_log(200)
    if not log_text:
        print("[自反馈] ⚠️ 无日志")
        return {"status": "no_log"}

    rates = _parse_growth_rates(log_text)
    focuses = _parse_focus_shifts(log_text)
    obs = _parse_observations(log_text)

    print(f"[自反馈] 日志读取: {len(log_text)}字符")
    print(f"[自反馈] 增长: {rates}")
    print(f"[自反馈] 焦点变化: {focuses}")
    print(f"[自反馈] 最近观察: {len(obs)}条")

    signals = _check_healthy_state(rates, focuses)
    print(f"[自反馈] 修正信号: {len(signals)}条")

    for sig in signals:
        print(f"  [{sig['type']}] {sig['message']} → {sig.get('action', '')}")

    written = _write_steering(signals)
    print(f"[自反馈] 写入目标: {written}条信号")

    return {
        "status": "done",
        "rates": rates,
        "focuses": focuses,
        "signals": signals,
        "written": written,
        "time": time.strftime("%H:%M:%S"),
    }


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
