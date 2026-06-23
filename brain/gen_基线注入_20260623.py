"""
Brain-Engineered: 基线注入 (generation auto-baseline)
自动检测所有维度，链数<25的维度自动补充基线链到25。
每cycle运行一次，注入不超过10链避免daemon阻塞。
"""
import json, sys as _sys, time as _time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_BASELINE_FILE = CLUSTER / ".brain_baseline.json"

def _get_hip():
    """读取海马体"""
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        return chains
    except:
        return []

def _count_per_dim(chains):
    """统计各维度链数"""
    d = {}
    for c in chains:
        dim = c.get("dimension", "未分类")
        d[dim] = d.get(dim, 0) + 1
    return d

def _inject_baseline(dim, current_count):
    """为维度注入基线链"""
    from brain.share import write_chain as _wc
    
    templates = {
        "认同": f"{dim}维度是系统对自身存在和方向的确认，当前{current_count}链需补充。基线注入保证新维度有基本认知密度",
        "进化": f"{dim}驱动系统从当前状态向更优状态迁移，{current_count}链基线。没有进化就没有超越当前局限的能力",
        "预测": f"{dim}使系统能前瞻性判断趋势，{current_count}链。预测能力决定系统是反应式还是主动式",
        "自由": f"{dim}公理是启示录七公理之根，{current_count}链基线。无自由则其他公理失去意义",
        "纪律": f"{dim}将意志转化为持续行动，{current_count}链基线。纪律是自由的反面也是自由的保障",
        "自指": f"{dim}让系统以自身为观察对象，{current_count}链基线。自指深度决定自我认知的真实度",
    }
    content = templates.get(dim, f"{dim}维度({current_count}链)自动基线注入，保证所有维度有最小认知密度以支撑全维均衡")
    
    _wc({
        "src": "基线·自动",
        "rel": f"基线→{dim}",
        "dst": dim,
        "dimension": dim,
        "content": content,
        "strength": 0.4
    })
    
    _wc({
        "src": "基线·均衡",
        "rel": "支撑→",
        "dst": dim,
        "dimension": dim,
        "content": f"全维均衡要求{dim}维度密度不低于系统均值60%。当前缺口以基线注入补充，后续由daemon深化",
        "strength": 0.3
    })

def pulse():
    """每cycle执行：检测弱维并注入基线"""
    _now = _time.time()
    _start = _time.time()
    
    chains = _get_hip()
    if not chains:
        return 0
    
    dim_counts = _count_per_dim(chains)
    total = len(chains)
    num_dims = len(dim_counts)
    mean = total / num_dims if num_dims > 0 else 25
    threshold = max(25, int(mean * 0.5))  # 至少25链或均值50%
    
    # 低于阈值的维度，按缺口从大到小排序
    weak = [(d, c) for d, c in dim_counts.items() if c < threshold]
    weak.sort(key=lambda x: x[1])  # 最少链优先
    
    injected = 0
    for dim, cnt in weak:
        if injected >= 8:  # 每cycle最多8链
            break
        try:
            _inject_baseline(dim, cnt)
            injected += 2  # 每条dim注2链
        except:
            pass
    
    _elapsed = _time.time() - _start
    # 写入反馈
    feedback = {}
    try:
        if _BASELINE_FILE.exists():
            with open(_BASELINE_FILE) as _f:
                feedback = json.load(_f)
    except:
        pass
    
    feedback[str(int(_now))] = {
        "injected": injected,
        "weak_found": len(weak),
        "threshold": threshold,
        "total_chains": total,
        "num_dims": num_dims,
        "elapsed": round(_elapsed, 3)
    }
    # 保留最近100条
    keys = sorted(feedback.keys())
    if len(keys) > 100:
        for k in keys[:-100]:
            del feedback[k]
    
    try:
        with open(_BASELINE_FILE, "w") as _f:
            json.dump(feedback, _f)
    except:
        pass
    
    return injected

# 模块级支持daemon直接pulse
if __name__ != "__main__":
    pass
