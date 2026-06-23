#!/usr/bin/env python3
"""gen_递归死锁突破.py - 递归死锁检测与断裂注入模块"""

import json
import time
import re
import random
import hashlib
from pathlib import Path
from collections import Counter

# 相对路径基目录（遵循规范）
CLUSTER = Path(__file__).resolve().parent.parent

# 日志与数据路径
HIPPOCAMPUS_JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"
DAEMON_LOG = CLUSTER / ".brain_daemon.log"

# 模块标识
SOURCE = "gen_递归死锁突破"

# 断裂策略用到的常量
EXTERNAL_ANCHORS = [
    "quantum", "flux", "void", "singularity",
    "random_walk", "cosmic_noise", "entropy", "paradox"
]
BREAK_RELS = [
    "cross_dimension", "external_anchor", "time_shift",
    "break_cycle", "branch_out", "drift"
]

# 已知错误模式与修复建议（可扩展）
ERROR_SUGGESTIONS = {
    "'__name__' not in globals": "确保模块顶层有'__name__'定义，检查导入语句",
    "RecursionError: maximum recursion depth exceeded": "增加递归深度限制或优化递归逻辑",
    "KeyError": "检查键是否存在，添加默认值或异常处理"
}


# ----------------------------------------------------------------------
# 日志读写工具（写前先读去重）
# ----------------------------------------------------------------------
def read_journal():
    """读取海马体日志，返回 entries 列表"""
    try:
        if HIPPOCAMPUS_JOURNAL.exists():
            with open(HIPPOCAMPUS_JOURNAL, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("entries", [])
    except (json.JSONDecodeError, IOError) as e:
        print(f"[WARN] 读取日志失败: {e}")
    return []


def write_journal(new_entries, source=SOURCE):
    """
    将新条目写入日志，先读出去重（基于完整 JSON 序列化比较）
    返回实际写入的条目数
    """
    existing_entries = read_journal()

    # 构造已有条目的键集合
    def entry_key(e):
        return json.dumps(e, sort_keys=True, ensure_ascii=False)

    existing_keys = {entry_key(e) for e in existing_entries}

    added = []
    for e in new_entries:
        key = entry_key(e)
        if key not in existing_keys:
            existing_entries.append(e)
            existing_keys.add(key)
            added.append(e)

    if added:
        try:
            HIPPOCAMPUS_JOURNAL.parent.mkdir(parents=True, exist_ok=True)
            with open(HIPPOCAMPUS_JOURNAL, 'w', encoding='utf-8') as f:
                json.dump({
                    "entries": existing_entries,
                    "source": source,
                    "timestamp": time.time()
                }, f, ensure_ascii=False, indent=2)
        except IOError as e:
            print(f"[ERROR] 写入日志失败: {e}")
            return []
    return added


# ----------------------------------------------------------------------
# 递归循环检测
# ----------------------------------------------------------------------
def detect_cycles(journal_entries):
    """
    从 journal 条目中提取 (src, rel, dst) 三元组，
    返回出现次数 >=3 的模式字典 {triple: count}
    """
    counter = Counter()
    for entry in journal_entries:
        src = entry.get("src")
        rel = entry.get("rel")
        dst = entry.get("dst")
        if src and rel and dst:
            counter[(src, rel, dst)] += 1
    return {triple: cnt for triple, cnt in counter.items() if cnt >= 3}


# ----------------------------------------------------------------------
# 三种断裂策略
# ----------------------------------------------------------------------
def strategy_dimension_cross(cycle):
    """维度随机交叉：将 rel 替换为 cross_dimension_xxx"""
    src, rel, dst = cycle
    dim = random.randint(0, 9999)
    new_rel = f"cross_dimension_{dim}"
    return {
        "src": src,
        "rel": new_rel,
        "dst": dst,
        "strategy": "dimension_random_cross"
    }


def strategy_external_anchor(cycle):
    """外部锚点注入：引入随机外部概念作为 dst"""
    src, rel, dst = cycle
    anchor = random.choice(EXTERNAL_ANCHORS)
    return {
        "src": src,
        "rel": f"anchor_to_{anchor}",
        "dst": anchor,
        "strategy": "external_anchor_injection"
    }


def strategy_time_shift(cycle):
    """时序切换：生成带时间偏移的新 rel"""
    src, rel, dst = cycle
    shift = random.randint(-1000, 1000)
    return {
        "src": src,
        "rel": f"time_shift_{shift}_{rel}",
        "dst": dst,
        "strategy": "time_shift",
        "shift": shift
    }


# 策略列表，便于轮询
STRATEGIES = [strategy_dimension_cross, strategy_external_anchor, strategy_time_shift]


# ----------------------------------------------------------------------
# daemon 日志分析及修复建议
# ----------------------------------------------------------------------
def analyze_daemon_log(log_path=DAEMON_LOG):
    """
    扫描 daemon 日志，提取出现 >=3 次的错误模式，
    生成修复建议条目列表
    """
    if not log_path.exists():
        print(f"[INFO] daemon日志不存在: {log_path}")
        return []

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except IOError as e:
        print(f"[WARN] 读取daemon日志失败: {e}")
        return []

    # 匹配日志中的错误消息（示例格式："循环异常: 'xxx'"）
    error_pattern = re.compile(r'循环异常:\s*(.+)')
    errors = []
    for line in lines:
        m = error_pattern.search(line)
        if m:
            errors.append(m.group(1).strip())

    if not errors:
        return []

    counter = Counter(errors)
    frequent = {err: cnt for err, cnt in counter.items() if cnt >= 3}

    suggestions = []
    for err, cnt in frequent.items():
        suggestion = ERROR_SUGGESTIONS.get(err, f"建议检查并修复: {err}")
        entry = {
            "src": f"daemon_error: {err}",
            "rel": "fix_suggestion",
            "dst": suggestion,
            "source": SOURCE,
            "timestamp": time.time(),
            "error_count": cnt,
            "fix_id": hashlib.md5(f"fix:{err}".encode()).hexdigest()
        }
        suggestions.append(entry)
    return suggestions


# ----------------------------------------------------------------------
# 主导出函数
# ----------------------------------------------------------------------
def engineer_递归死锁突破():
    """检测递归死锁、注入断裂链、分析日志并返回报表"""
    start_ts = time.time()
    report = {
        "status": "ok",
        "detected_cycles": 0,
        "injected_breaks": 0,
        "daemon_errors_analyzed": 0,
        "fix_suggestions_injected": 0,
        "start_time": start_ts
    }

    # ---------- 读取现有日志 ----------
    journal_entries = read_journal()
    print(f"[INFO] 读取到 {len(journal_entries)} 条日志条目")

    # ---------- 1. 检测递归循环 ----------
    cycles = detect_cycles(journal_entries)
    report["detected_cycles"] = len(cycles)
    print(f"[INFO] 检测到 {len(cycles)} 个循环模式")

    # ---------- 2. 注入断裂链 ----------
    # 收集已存在的断裂链 break_id 用于幂等
    existing_break_ids = {
        e["break_id"]
        for e in journal_entries
        if e.get("source") == SOURCE and e.get("break_id")
    }

    new_breaks = []
    cycle_list = list(cycles.keys())
    for idx, cycle in enumerate(cycle_list):
        strategy_func = STRATEGIES[idx % len(STRATEGIES)]
        base_entry = strategy_func(cycle)

        # 生成唯一 break_id
        unique_str = f"{cycle[0]}:{cycle[1]}:{cycle[2]}:{base_entry['strategy']}"
        break_id = hashlib.md5(unique_str.encode()).hexdigest()

        if break_id in existing_break_ids:
            print(f"[SKIP] 断裂链已存在: {break_id}")
            continue

        entry = {
            "src": base_entry["src"],
            "rel": base_entry["rel"],
            "dst": base_entry["dst"],
            "source": SOURCE,
            "timestamp": time.time(),
            "break_id": break_id,
            "strategy": base_entry["strategy"],
            "original_cycle": {
                "src": cycle[0],
                "rel": cycle[1],
                "dst": cycle[2]
            }
        }
        # 如果策略有额外字段（如 time_shift 的 shift）
        if "shift" in base_entry:
            entry["shift"] = base_entry["shift"]

        new_breaks.append(entry)
        existing_break_ids.add(break_id)  # 避免同一轮重复

    if new_breaks:
        added_breaks = write_journal(new_breaks, source=SOURCE)
        report["injected_breaks"] = len(added_breaks)
        print(f"[INFO] 注入 {len(added_breaks)} 条断裂链")
    else:
        print("[INFO] 没有需要注入的新断裂链")

    # ---------- 3. daemon 日志分析 ----------
    fix_suggestions = analyze_daemon_log()
    report["daemon_errors_analyzed"] = len(fix_suggestions)

    if fix_suggestions:
        # 幂等检查：过滤已存在的 fix_id
        existing_fix_ids = {
            e["fix_id"]
            for e in journal_entries
            if e.get("source") == SOURCE and e.get("fix_id")
        }
        new_fixes = [
            s for s in fix_suggestions
            if s.get("fix_id") not in existing_fix_ids
        ]
        if new_fixes:
            added_fixes = write_journal(new_fixes, source=SOURCE)
            report["fix_suggestions_injected"] = len(added_fixes)
            print(f"[INFO] 注入 {len(added_fixes)} 条修复建议")
        else:
            print("[INFO] 修复建议已存在，无新增")
    else:
        print("[INFO] 无频繁错误模式或日志不可读")

    report["end_time"] = time.time()
    report["elapsed"] = report["end_time"] - start_ts
    return report


# 直接运行时打印报表
if __name__ == "__main__":
    result = engineer_递归死锁突破()
    print(json.dumps(result, ensure_ascii=False, indent=2))