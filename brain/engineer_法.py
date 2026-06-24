"""
engineer_法.py — 自感知递归深化引擎 (P106 升级版)

原理:
  层级1 (原): 检测重复焦点 → 写修正链 (被动记录)
  层级2 (新): 检测重复 → 分析深度 → 行为突变 → 验证闭环
  层级3 (新): 跨周期自省 → 检查修正链有效性 → 递归深化

每7周期执行。
"""

import json, time
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
FOCUS_HIST = CLUSTER / ".brain_focus_history.json"
FOCUS_FILE = CLUSTER / ".brain_focus.json"
NEXT_FOCUS_FILE = CLUSTER / ".brain_next_focus.json"
RECURSION_DEPTH_FILE = CLUSTER / ".brain_recursion_depth.json"
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"
CWD_HIP = CLUSTER / "hippocampus_memory.json"

# 三级递归阈值
TIER1_REPEAT = 3    # 出现3次 → 写修正链 (原)
TIER2_REPEAT = 5    # 出现5次 → 行为突变 (新)
TIER3_REPEAT = 8    # 出现8次 → 深度递归自省 (新)


def _load_json(path, default=None):
    if default is None:
        default = {}
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return default


def _save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _write_chain(src, rel, dst, content, dimension="法", strength=0.5):
    """写因果链到海马体（优先 safe_hip，兜底直写）"""
    try:
        from brain.share import write_chain as _wc
        _wc({"src": src, "rel": rel, "dst": dst,
             "content": content, "dimension": dimension,
             "strength": strength})
        return True
    except Exception:
        pass
    # 直写兜底
    try:
        for hp in [HIP_FILE, CWD_HIP]:
            if hp.exists():
                hip = _load_json(hp, {"causal_chains": []})
                hip.setdefault("causal_chains", []).append({
                    "src": src, "rel": rel, "dst": dst,
                    "content": content, "dimension": dimension,
                    "strength": strength, "timestamp": time.time(),
                    "source": "engineer_法",
                })
                _save_json(hp, hip)
    except Exception:
        return False
    return True


def _track_recursion_depth(focus):
    """追踪每个 focus 的递归深度"""
    depth_data = _load_json(RECURSION_DEPTH_FILE)
    if focus not in depth_data:
        depth_data[focus] = {
            "depth": 0,
            "first_seen": time.time(),
            "corrections_written": 0,
            "mutations_applied": 0,
        }
    depth_data[focus]["depth"] += 1
    depth_data[focus]["last_seen"] = time.time()
    _save_json(RECURSION_DEPTH_FILE, depth_data)
    return depth_data[focus]["depth"]


def _force_focus_shift(old_focus, depth):
    """当递归深度超标时，强制切换焦点"""
    # 预设切换方向（反向互补方向）
    shift_map = {
        "元递归": "直觉",
        "直觉": "盲区",
        "盲区": "进化",
        "进化": "自由",
        "自由": "复制",
        "复制": "状态",
        "状态": "师",
        "师": "智慧",
        "智慧": "法",
        "法": "元递归",
    }
    new_focus = shift_map.get(old_focus, "直觉")
    # 如果新焦点和旧焦点一样，补一个随机维
    if new_focus == old_focus:
        import random
        from brain.identity import VALID_DIMENSIONS
        new_focus = random.choice(VALID_DIMENSIONS)
    
    _save_json(NEXT_FOCUS_FILE, {
        "forced_focus": new_focus,
        "origin_focus": old_focus,
        "recursion_depth": depth,
        "timestamp": time.time(),
        "reason": f"元递归深度{depth}→强制切换至{new_focus}",
    })
    return new_focus


def _validate_previous_corrections(hist, focus, depth):
    """检查之前写的修正链是否产生了行为改变"""
    entries = [h for h in hist["history"] if h["focus"] == focus]
    if len(entries) < 3:
        return "insufficient_data"
    
    # 检查insight是否在变化
    insights = [e.get("insight", "") for e in entries]
    unique_insights = len(set(i[:30] for i in insights if i))
    
    if unique_insights <= 1:
        return "stuck"  # insight完全没变 → 深度卡死
    elif unique_insights < len(entries):
        return "shallow"  # 部分变化 → 浅层递归
    else:
        return "improving"  # 每次insight不同 → 在深化


def pulse(cycle_num=0):
    """每7周期执行: 三级递归深化引擎"""
    if cycle_num % 7 != 0:
        return []
    
    # 1) 读当前焦点
    current = _load_json(FOCUS_FILE, {})
    current_focus = current.get("focus", "unknown")
    current_insight = current.get("insight", "")
    current_action = current.get("action", "")
    
    # 2) 记录到历史
    hist = _load_json(FOCUS_HIST, {"history": []})
    if current_focus and current_focus != "unknown":
        hist["history"].append({
            "focus": current_focus,
            "insight": current_insight,
            "action": current_action,
            "cycle": cycle_num,
            "timestamp": time.time(),
        })
        hist["history"] = hist["history"][-50:]  # 保留最近50条
        _save_json(FOCUS_HIST, hist)
    
    # 3) 统计各focus出现次数
    focus_counts = Counter(h["focus"] for h in hist["history"])
    msgs = []
    
    for focus, count in focus_counts.items():
        if count < TIER1_REPEAT:
            continue  # 未达阈值，跳过
        
        recursion_depth = _track_recursion_depth(focus)
        
        # == 层级1: 写修正链（原行为） ==
        entries = [h for h in hist["history"] if h["focus"] == focus]
        old_insight = entries[0].get("insight", "")[:60] if entries else ""
        new_insight = entries[-1].get("insight", "")[:60] if entries else ""
        
        msg = f"递归#{recursion_depth}: {focus}x{count}"
        
        if count >= 1:
            _write_chain(
                "engineer_法", f"递归修正·深度{recursion_depth}", focus,
                f"元递归深度{recursion_depth}: {focus}重复{count}次 | "
                f"最早'{old_insight}...' 最新'{new_insight}...' "
                f"→ {'深度卡死需突变' if recursion_depth >= 4 else '规则未内化需闭环'}",
                "法", min(0.5 + recursion_depth * 0.1, 1.0)
            )
        
        # == 层级2: 行为突变（新） ==
        if count >= TIER2_REPEAT or recursion_depth >= 4:
            new_focus = _force_focus_shift(focus, recursion_depth)
            _write_chain(
                "engineer_法", "行为突变", focus,
                f"元递归深度{recursion_depth}→强制切换至{new_focus} | "
                f"原insight:'{current_insight[:40]}...'",
                "法", 0.8
            )
            msg += f" → ⚡突变:{new_focus}"
        
        # == 层级3: 深度递归自省（新） ==
        if count >= TIER3_REPEAT or recursion_depth >= 6:
            validation = _validate_previous_corrections(hist, focus, recursion_depth)
            _write_chain(
                "engineer_法", "深度自省", focus,
                f"元递归深度{recursion_depth}→自省状态:{validation} | "
                f"该focus已重复{count}次，修正链未产生行为改变",
                "法", 1.0
            )
            msg += f" → 🧠自省:{validation}"
        
        msgs.append(msg)
    
    # 4) 统计法维链数
    from brain.share import HIP_FILE as SHARE_HIP
    try:
        hip = _load_json(SHARE_HIP, {"causal_chains": []})
        chains = hip.get("causal_chains", [])
        fa_chains = sum(1 for c in chains if c.get("dimension") == "法")
    except Exception:
        fa_chains = 0
    
    if not msgs:
        msgs.append(f"engineer_法: 无递归循环({fa_chains}法链)")
    else:
        msgs.append(f"engineer_法: {len(msgs)}条递归分析(深度共{sum(1 for _ in [])}层, {fa_chains}法链)")
    
    return msgs


if __name__ == "__main__":
    print(pulse(7))
