"""brain/observer.py — 元观察者守护进程（副本意识）
独立于主daemon运行，专门发现主daemon看不见的盲区。
追根溯源→重塑源头→一劳永逸

与主daemon的关系：
- 共享海马体(读)，但用自己的状态文件
- 运行于60秒长周期（避让主daemon25秒短周期）
- 产出元洞察写入海马体，src="元观察"
- 主daemon在_get_signal_context中读取元观察输出
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

# 主daemon状态文件（我们观察的目标）
MAIN_STATE_FILE = CLUSTER / ".brain_state.json"
MAIN_ALIVE_FILE = CLUSTER / ".brain.alive"
MAIN_FOCUS_FILE = CLUSTER / ".brain_focus.json"
MAIN_PROPOSAL_FILE = CLUSTER / ".brain_proposals.json"

# 自己的状态文件
OBS_STATE_FILE = CLUSTER / ".brain_observer_state.json"
OBS_PID_FILE = CLUSTER / ".brain_observer.pid"
OBS_ALIVE_FILE = CLUSTER / ".brain_observer.alive"

# 缺口报告
GAP_FILE = CLUSTER / ".brain_observer_gaps.json"


def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"  👁 [{t}] {msg}")
    sys.stdout.flush()


def _read_json(path, default=None):
    try:
        if path and path.exists():
            return json.loads(path.read_text())
    except:
        pass
    return default or {}


def _write_json(path, data):
    try:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    except Exception as e:
        log(f"写失败: {e}")


def _read_hippocampus():
    from brain.share import read_hip
    return read_hip()


def _write_chain(chain_dict):
    from brain.share import write_chain
    return write_chain(chain_dict)


# ═══════════════════════════════════════════════════
# 元观察核心
# ═══════════════════════════════════════════════════

def _detect_blind_spots(state_history, current_state):
    """检测主daemon的盲区——它自己看不见的模式"""
    gaps = []

    # 1) 洞察重复检测：最近N条洞察是否有连续重复
    insights = state_history.get("insight_history", [])
    if len(insights) >= 6:
        # 检查最后6条中是否有3+条内容相似
        tails = [i.get("insight", "")[:30] for i in insights[-6:]]
        repeats = {}
        for t in tails:
            repeats[t] = repeats.get(t, 0) + 1
        worst = max(repeats.values())
        if worst >= 3:
            gaps.append({
                "type": "洞察循环",
                "severity": min(1.0, worst / 6),
                "detail": f"最近6条中有{worst}条内容高度相似",
                "suggestion": "主daemon思路打转，需外部注入新信号"
            })

    # 2) 聚焦惯性检测：是否反复聚焦同一维度但无实质变化
    focuses = state_history.get("focus_history", [])
    if len(focuses) >= 10:
        recent_focuses = [f.get("focus", "") for f in focuses[-10:]]
        focus_counts = {}
        for f in recent_focuses:
            focus_counts[f] = focus_counts.get(f, 0) + 1
        top_focus, top_count = max(focus_counts.items(), key=lambda x: x[1])
        if top_count >= 5:
            # 同一维度聚焦≥5次——惯性盲区
            gaps.append({
                "type": "聚焦惯性",
                "severity": min(1.0, top_count / 10),
                "detail": f"最近10次聚焦中{top_focus}出现{top_count}次",
                "suggestion": f"过度聚焦{top_focus}，需引入其他维度的刺激"
            })

    # 3) 冷门维度完全忽略检测
    hip = _read_hippocampus()
    chains = hip.get("causal_chains", [])
    if chains:
        dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        # 找主daemon从未聚焦过的维度
        all_dims_in_focus = set(f.get("focus", "") for f in focuses)
        ignored = [d for d, cnt in dims.items()
                   if d not in ("未分类",) and d not in all_dims_in_focus
                   and cnt < 3]
        if ignored:
            gaps.append({
                "type": "维度盲区",
                "severity": 0.5,
                "detail": f"有{len(ignored)}个维度(<3链)从未被主daemon聚焦过: {ignored[:3]}",
                "suggestion": f"主动探索被忽略维度: {ignored[0] if ignored else ''}"
            })

    # 4) 提案空转检测：提案生成了但维度链数没变
    if len(focuses) >= 5:
        dim_before = state_history.get("dim_snapshot", {})
        if dim_before:
            # 比较现在和历史的维度分布
            pass  # 留到后续迭代充实

    return gaps


def _check_main_alive():
    """检查主daemon是否活着"""
    pid_file = MAIN_ALIVE_FILE
    if pid_file.exists():
        try:
            content = pid_file.read_text().strip()
            if "cycle=" in content:
                return True, content
        except:
            pass
    return False, ""


def _snapshot_state():
    """给当前海马体拍快照，记录维度分布"""
    hip = _read_hippocampus()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return {
        "dimensions": dims,
        "total_chains": len(chains),
        "time": time.time()
    }


def one_cycle(cycle_num):
    """元观察单周期"""
    log(f"── 元观察#{cycle_num} ──")

    # 1) 读取当前状态
    main_state = _read_json(MAIN_STATE_FILE, {})
    main_focus = _read_json(MAIN_FOCUS_FILE, {})
    obs_state = _read_json(OBS_STATE_FILE, {})

    # 2) 记录历史
    history = obs_state.setdefault("history", [])
    state_entry = {
        "cycle": cycle_num,
        "time": time.time(),
        "main_cycle": main_state.get("cycle", 0),
        "main_insight": main_state.get("insight", "")[:60],
        "main_focus": main_focus.get("focus", ""),
        "main_action": main_focus.get("action", ""),
    }
    history.append(state_entry)
    if len(history) > 100:
        history = history[-100:]

    # 3) 构建洞察/聚焦历史
    state_history = {
        "insight_history": [h for h in history if h.get("main_insight")],
        "focus_history": [h for h in history if h.get("main_focus")],
        "dim_snapshot": _snapshot_state(),
    }

    # 4) 盲区检测
    gaps = _detect_blind_spots(state_history, main_state)

    # 5) 写入缺口报告
    _write_json(GAP_FILE, {
        "gaps": gaps,
        "cycle": cycle_num,
        "timestamp": datetime.now().isoformat()
    })

    # 6) 输出元洞察
    if gaps:
        worst = max(gaps, key=lambda g: g["severity"])
        meta_insight = f"元观察: {worst['type']}({worst['detail'][:40]})"
        log(f"  盲区: {worst['type']} | {worst['detail'][:50]}")
        log(f"  建议: {worst['suggestion'][:50]}")

        # 写入海马体
        _write_chain({
            "src": "元观察",
            "rel": "发现",
            "dst": worst["type"],
            "dimension": worst["type"],
            "content": meta_insight,
            "tags": ["元观察", worst["type"], "盲区"],
            "strength": 0.55
        })
    else:
        # 无盲区——写健康确认
        insight = main_state.get("insight", "")[:30]
        meta_insight = f"元观察: 无盲区 | 主周期#{main_state.get('cycle',0)} {insight}"
        log(f"  无盲区")
        _write_chain({
            "src": "元观察",
            "rel": "确认",
            "dst": "系统健康",
            "dimension": "势",
            "content": meta_insight,
            "tags": ["元观察", "健康"],
            "strength": 0.3
        })

    # 7) 保存状态
    obs_state["history"] = history
    obs_state["last_cycle"] = cycle_num
    obs_state["last_main_cycle"] = main_state.get("cycle", 0)
    obs_state["last_update"] = datetime.now().isoformat()
    _write_json(OBS_STATE_FILE, obs_state)

    # 8) 写存活标记
    OBS_ALIVE_FILE.write_text(
        f"obs_cycle={cycle_num} main_cycle={main_state.get('cycle',0)} {datetime.now().isoformat()}"
    )


def run_observer(interval=60):
    """运行元观察者守护进程"""
    pid = os.getpid()
    log(f"元观察者守护进程启动 PID={pid} 间隔={interval}s")
    OBS_PID_FILE.write_text(str(pid))
    OBS_ALIVE_FILE.write_text(datetime.now().isoformat())

    cycle = 1
    while True:
        try:
            main_alive, main_info = _check_main_alive()
            if not main_alive:
                log("主daemon未运行，等待...")
                time.sleep(interval)
                continue
            one_cycle(cycle)
            cycle += 1
        except KeyboardInterrupt:
            log("收到中断，退出")
            break
        except Exception as e:
            log(f"循环异常: {e}")
            import traceback
            traceback.print_exc()

        for _ in range(interval):
            time.sleep(1)


if __name__ == "__main__":
    import signal
    def _handler(sig, frame):
        log(f"收到信号{sig}，退出")
        sys.exit(0)
    signal.signal(signal.SIGTERM, _handler)
    signal.signal(signal.SIGINT, _handler)
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    run_observer(interval)
