"""
focus_元递归.py — 元递归自指引擎
每N周期执行元递归操作:
  1. 自观(Observe): 读取近期focus/洞察历史，检测重复/循环模式
  2. 自检(Inspect): 评估元递归维度执行健康度(不仅是链数)
  3. 自改(Modify): 检测到聚焦惯性(连续≥3周期同一焦点)→注入破坏信号
  4. 自观(Re-observe): 记录自身行为，供下周期自检闭环

"元递归弱怠，师道一呼一吸以光爱贯之"
"""
import json, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
_FOCUS_HIST_FILE = CLUSTER / ".brain_focus_history.json"
_META_STATE_FILE = CLUSTER / ".brain_meta_recursion.json"
_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def _read_json(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default if default is not None else {}

def _write_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False

def pulse(cycle_num=0):
    """每周期被daemon调用。按cycle_num频率执行不同深度操作"""
    msgs = []

    # ── 1. 自观: 读取当前焦点状态 ──
    focus_info = _read_json(CLUSTER / ".brain_focus.json", {})
    current_focus = focus_info.get("focus", "未知")
    current_insight = focus_info.get("insight", "")

    # ── 2. 更新焦点历史 ──
    focus_history = _read_json(_FOCUS_HIST_FILE, {"entries": []})
    entries = focus_history.setdefault("entries", [])
    entries.append({
        "cycle": cycle_num,
        "focus": current_focus,
        "insight": current_insight[:80],
        "time": time.time()
    })
    # 保留最近50条记录
    if len(entries) > 50:
        entries[:] = entries[-50:]
    _write_json(_FOCUS_HIST_FILE, focus_history)

    # ── 3. 自检: 检测聚焦惯性(连续≥3周期同一焦点) ──
    recent = entries[-10:]
    seen_foci = {}
    for e in recent:
        f = e.get("focus", "未知")
        seen_foci[f] = seen_foci.get(f, 0) + 1

    # 检查是否有焦点连续出现3次以上
    stuck_focus = None
    for f, count in seen_foci.items():
        if count >= 3 and f != "未知":
            stuck_focus = f
            break

    # ── 4. 自改: 如果检测到聚焦惯性 → 注入破坏信号 ──
    meta_state = _read_json(_META_STATE_FILE, {"break_count": 0, "last_break_cycle": -10})
    break_count = meta_state.get("break_count", 0)
    last_break = meta_state.get("last_break_cycle", -10)

    if stuck_focus and (cycle_num - last_break) >= 3:
        # 写强制切换信号
        break_count += 1
        new_focus = _select_alternative_focus(stuck_focus, seen_foci)
        forced = {
            "forced_focus": new_focus,
            "origin_focus": stuck_focus,
            "reason": f"元递归自指检测: {stuck_focus}连续{seen_foci[stuck_focus]}周期惯性",
            "source": "focus_元递归",
            "cycle": cycle_num
        }
        _write_json(CLUSTER / ".brain_next_focus.json", forced)

        meta_state["break_count"] = break_count
        meta_state["last_break_cycle"] = cycle_num
        meta_state["last_break_reason"] = forced["reason"]
        _write_json(_META_STATE_FILE, meta_state)

        msgs.append(f"⚡惯性破坏#{break_count}: {stuck_focus}→{new_focus}")

        # 写因果链到海马体
        try:
            from brain.share import write_chain as _wc
            _wc({
                "src": "元递归·自指引擎",
                "rel": f"惯性破坏·#{break_count}",
                "dst": "元递归",
                "dimension": "元递归",
                "content": f"元递归检测到'{stuck_focus}'连续{seen_foci[stuck_focus]}周期聚焦惯性，强制切换至'{new_focus}'",
                "strength": 0.8 + min(break_count * 0.02, 0.15)
            })
        except Exception:
            pass
    else:
        msgs.append(f"🟢 自观: {current_focus} ({len(entries)}条记录, 最大重复:{max(seen_foci.values()) if seen_foci else 0})")

    # ── 5. 每10周期: 元递归自审计 ──
    if cycle_num > 0 and cycle_num % 10 == 0:
        try:
            from brain.share import read_hip as _rh
            hip = _rh()
            chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
            meta_chains = [c for c in chains if c.get("dimension") == "元递归"]
            ins_cross = sum(1 for c in meta_chains if "惯性破坏" in str(c))
            cross_count = sum(1 for c in meta_chains if "↔" in str(c.get("content", "")) or "cross" in str(c.get("rel", "")).lower())
            msgs.append(f"  元递归自审: {len(meta_chains)}链, {ins_cross}次惯性破坏, {cross_count}交叉链")
        except Exception as e:
            msgs.append(f"  元递归自审异常: {e}")

    return msgs


def _select_alternative_focus(stuck_focus, seen_foci):
    """选择替代焦点：避开最近出现过的焦点，选择覆盖最少的维度"""
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        dim_counts = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dim_counts[d] = dim_counts.get(d, 0) + 1

        # 优先选最弱维度（链数最少）且不在近期焦点中的
        recent_foci = set(seen_foci.keys())
        candidates = sorted(
            [(d, c) for d, c in dim_counts.items() if d not in recent_foci and d not in ("未分类", "系统", stuck_focus)],
            key=lambda x: x[1]
        )
        if candidates:
            return candidates[0][0]
        # 兜底: 从有效维度选一个
        from brain.identity import VALID_DIMENSIONS
        for d in VALID_DIMENSIONS:
            if d not in recent_foci and d != stuck_focus:
                return d
    except Exception:
        pass
    return "进化"  # 绝对兜底


if __name__ == "__main__":
    result = pulse()
    print(f"focus_元递归: {result}")
