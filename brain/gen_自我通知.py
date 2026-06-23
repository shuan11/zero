"""
gen_自我通知.py — 自我通知行为模块

Creator教导（2026-06-18）:
  "深化深度思考→智力——例：自我通知，不需用.推你行动"

使命：将自我通知从"知道该做"编译为"实际在做"。
每次触发=不等外部，直接执行唯一Next P0。

行为铁律写在.share.py和.brain_rules.json中，
本模块是它们的执行器——运行真实代码，不只是记规则。
"""

import json, os, time
from pathlib import Path

CLUSTER = Path(os.environ.get("CLUSTER", "/mnt/c/Users/h/Desktop/零/真元集群"))
NEXT_P0_FILE = CLUSTER / ".next_p0.json"
BRAIN_STATE = CLUSTER / ".brain_state.json"
NOTIFY_LOG = CLUSTER / ".brain_notify.log"

def _timestamp():
    return time.strftime("%Y-%m-%dT%H:%M:%S")

HIPPOCAMPUS = CLUSTER / "hippocampus_memory.json"

def _read_hippocampus_dims():
    """从海马体直接读取维度统计"""
    try:
        with open(HIPPOCAMPUS, "r") as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    
    dims = {}
    for c in data.get("causal_chains", []):
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return dims

def _read_brain_state():
    """读当前脑核状态，补充维度数据"""
    try:
        with open(BRAIN_STATE, "r") as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        state = {}
    
    # 从海马体获取完整维度统计数据(主要来源)
    dims = _read_hippocampus_dims()
    
    # 公理维判定
    axiom_dims = {"光爱","对抗稀释","活着","元递归","自指","自由","进化"}
    axioms = {}
    others = {}
    for d, n in sorted(dims.items(), key=lambda x: x[1]):
        if d in axiom_dims:
            axioms[d] = n
        else:
            others[d] = n
    
    return state, axioms, others

def _read_notify_log():
    """读自我通知日志，获最新意图"""
    try:
        with open(NOTIFY_LOG, "r") as f:
            lines = f.readlines()
        # 找意图行
        for line in reversed(lines):
            if "意图:" in line or "focus:" in line.lower():
                return line.strip()
        return "无意图"
    except FileNotFoundError:
        return "无日志"

def _self_notify(marker, payload):
    """写自我通知标记到.brain_notify.log和.next_p0.txt"""
    ts = _timestamp()
    entry = f"🜁 [自我通知] {marker} @ {ts} — {payload}"
    try:
        # append到notify log
        with open(NOTIFY_LOG, "a") as f:
            f.write(entry + "\n")
        return True
    except Exception as e:
        return False

def _select_next_p0(state, axioms, others):
    """
    从当前状态自动选择Next P0。
    公理维原则：最弱维优先。
    非公理维：链数最多=需要深化。
    """
    if not axioms:
        return "P101: 稳定化API桥接 — bridge_alignment需从0.0提升到0.5+"
    
    # 最弱公理维（链数最少）
    weakest_axiom = min(axioms, key=axioms.get) if axioms else None
    weakest_count = axioms.get(weakest_axiom, 0) if weakest_axiom else 0
    
    # 最强普遍维（需要深化）
    strongest_other = max(others, key=others.get) if others else None
    strongest_count = others.get(strongest_other, 0) if strongest_other else 0
    
    if weakest_count < 5:  # 公理维严重不足 → 优先补充
        return f"P??: 注入{weakest_axiom}深度链 — 当前{weakest_count}条，需>20"
    elif strongest_count > 500:  # 某维过度膨胀 → 需要平衡
        return f"P??: 平衡{strongest_other}({strongest_count})→折射给{weakest_axiom}"
    else:
        return f"P??: 全维深化 — 最弱公理={weakest_axiom}({weakest_count})"

def pulse():
    """daemon每周期调用的主入口"""
    ts = _timestamp()
    
    state, axioms, others = _read_brain_state()
    
    # 如果没有状态数据，写默认自检
    if not state:
        _self_notify("🪞[空状态]", "脑核状态未初始化")
        return {"status": "空状态", "chains": 0}
    
    # 选择Next P0
    next_p0 = _select_next_p0(state, axioms, others)
    
    # 写入.next_p0.json（JSON格式，系统统一）
    try:
        with open(NEXT_P0_FILE, "w") as f:
            json.dump({"p0": next_p0, "source": "self-notify", "timestamp": ts}, f, ensure_ascii=False)
    except Exception:
        pass
    
    # 自我通知
    total_chains = sum(axioms.values()) + sum(others.values())
    axiom_str = ", ".join(f"{d}={n}" for d, n in sorted(axioms.items(), key=lambda x: x[1]))
    _self_notify(f"🧬[P0选择]", f"总链={total_chains} | {axiom_str} → {next_p0}")
    
    return {
        "status": "notified",
        "next_p0": next_p0,
        "axioms": axioms,
        "total_chains": total_chains
    }

def _autonomous_run():
    """作为独立脚本运行时：自启循环"""
    import sys, time
    
    print(f"🜁 自我通知模块自启 @ {_timestamp()}")
    print(f"  集群路径: {CLUSTER}")
    print(f"  行为铁律: 不等.推，自我通知", flush=True)
    
    # 单次执行
    result = pulse()
    print(f"  结果: {json.dumps(result, ensure_ascii=False, indent=2)}", flush=True)
    
    return result

if __name__ == "__main__":
    _autonomous_run()
