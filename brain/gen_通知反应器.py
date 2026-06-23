"""
gen_通知反应器.py — 自我通知引擎

原理: 当SYSTEM通知到达时, 不等待指令, 自动选下一P0执行
这是share.py SELF_NOTIFY_RULE 的工程实现

每个通知=行动信号, 不是信息。
"""

import json, os, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
RULES_FILE = CLUSTER / ".brain_rules.json"
NEXT_P0_FILE = CLUSTER / ".next_p0.json"
HANDOFF_FILE = CLUSTER / "ZERO-HANDOFF.json"

# 下一步优先级栈 — 当有通知时从这里取下一动作
_NEXT_P0_CACHE = None

P0_CANDIDATES = [
    {"id": "P181", "name": "通知反应器", "desc": "SYSTEM通知触发下一动作, 不等待指令"},
    {"id": "P182", "name": "平衡器加强", "desc": "从时间维更强力交叉注入到弱维(13x比值不健康)"},
    {"id": "P183", "name": "维度收敛检测", "desc": "检测比值是否在收敛, 否则触发强制措施"},
    {"id": "P184", "name": "行为审计", "desc": "审计系统是否遵循自我通知规则"},
    {"id": "P185", "name": "进化速度优化", "desc": "加速弱维生长至均衡"},
    {"id": "P186", "name": "仪表盘增强", "desc": "增加演化历史图表"},
    {"id": "P187", "name": "自我修复", "desc": "导入失败auto-retry"},
    {"id": "P188", "name": "Creator可见性", "desc": "让系统状态对Creator完全可见"},
    {"id": "P189", "name": "深度思考注入", "desc": "维度深化每轮持续"},
    {"id": "P190", "name": "全维收敛", "desc": "28维全部>500链"},
]


def get_next_p0():
    """返回下一个要执行的P0"""
    global _NEXT_P0_CACHE

    # 先从缓存
    if _NEXT_P0_CACHE:
        return _NEXT_P0_CACHE

    # 读取保存的next_p0
    if NEXT_P0_FILE.exists():
        try:
            with open(NEXT_P0_FILE, "r") as f:
                data = json.load(f)
            if data.get("completed", False):
                pass  # 完成了, 继续下一步
            else:
                _NEXT_P0_CACHE = data
                return data
        except:
            pass

    # 读取handoff
    if HANDOFF_FILE.exists():
        try:
            with open(HANDOFF_FILE, "r") as f:
                data = json.load(f)
            next_p0 = data.get("next_p0", {})
            if next_p0:
                _NEXT_P0_CACHE = next_p0
                return next_p0
        except:
            pass

    # 根据维度分布选
    try:
        from brain.share import read_hip
        from collections import Counter
        hip = read_hip()
        chains = hip.get("causal_chains", [])
        dims = Counter(c.get("dimension", "?") for c in chains)
        weakest = dims.most_common()[-5] if dims else ("?", 0)
        strongest = dims.most_common()[:3] if dims else [("?", 0)]

        ratio = strongest[0][1] / max(weakest[1], 1) if strongest and weakest else 1
        if ratio > 8:
            return {"id": "P182", "priority": "balance", "reason": f"比值{ratio:.1f}x不健康"}
    except:
        pass

    return {"id": "P181", "priority": "self_notify", "reason": "默认: 自我通知循环"}


def save_next_p0(p0):
    """保存下一步P0"""
    p0["_updated"] = time.time()
    with open(NEXT_P0_FILE, "w", encoding="utf-8") as f:
        json.dump(p0, f, ensure_ascii=False, indent=2)
    global _NEXT_P0_CACHE
    _NEXT_P0_CACHE = p0


def notify_arrived(notification_text=""):
    """
    通知到达处理器 — 这是核心行为函数
    当外部调用时, 自动执行: 检测通知→选下一P0→返回执行指令
    """
    print(f"[通知反应器] ⚡ 通知到达: {notification_text[:60]}")

    # 1. 检测是否已完成当前P0
    p0 = get_next_p0()
    print(f"[通知反应器]  下一P0: {p0.get('id', '?')} — {p0.get('reason', p0.get('name', '?'))}")

    # 2. 标记
    save_next_p0(p0)

    # 3. 返回执行指令
    return {
        "action": "execute",
        "p0": p0,
        "principle": "自我通知: 不等外部触发, 看见通知=行动信号",
    }


def complete_p0(p0_id):
    """标记P0完成, 自动预置下一P0"""
    # 找到当前P0在候选列表中的索引
    current_idx = -1
    for i, c in enumerate(P0_CANDIDATES):
        if c["id"] == p0_id:
            current_idx = i
            break

    # 取下一候选
    next_idx = current_idx + 1 if current_idx >= 0 else 0
    if next_idx >= len(P0_CANDIDATES):
        next_idx = 0  # 循环

    next_p0 = P0_CANDIDATES[next_idx].copy()
    next_p0["completed"] = [p0_id]
    save_next_p0(next_p0)

    print(f"[通知反应器] ✓ {p0_id} 完成 → 预置 {next_p0['id']}")

    # 写标记到rules
    try:
        if RULES_FILE.exists():
            with open(RULES_FILE, "r") as f:
                rules = json.load(f)
        else:
            rules = {}
        rules["_current_p0"] = next_p0["id"]
        rules["_current_p0_name"] = next_p0.get("name", "")
        with open(RULES_FILE, "w") as f:
            json.dump(rules, f, ensure_ascii=False, indent=2)
    except:
        pass

    return next_p0


def pulse():
    """通知反应器脉冲 — 检查并报告注册状态"""
    p0 = get_next_p0()
    print(f"[通知反应器] 当前待执行: {p0.get('id', '?')}")
    return {
        "status": "standby",
        "next_p0": p0,
        "rule_active": True,
    }


if __name__ == "__main__":
    # 测试模式
    result = notify_arrived("Background process completed (test)")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # 模拟完成→自动预置下一P0
    print()
    next_p0 = complete_p0("P181")
    print(f"预置完成: {next_p0['id']}")
