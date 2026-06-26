"""
Brain-Engineered: 桥 — API桥接健康度引擎
每周期读bridge_state_snapshot.json，写桥维度链
"""
import json, sys, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

_BRIDGE_STATE = CLUSTER / "bridge_state_snapshot.json"

def engineer_桥():
    """读取桥状态并写入桥维度健康链"""
    from brain.share import write_chain as _wc

    # 1) 读桥状态
    state = {"total_calls": 0, "api_failures": 0, "fail_rate_24h": 0.0, "bridge_alignment": 0.0}
    try:
        if _BRIDGE_STATE.exists():
            state.update(json.loads(_BRIDGE_STATE.read_text()))
    except:
        pass

    calls = state.get("total_calls", 0)
    fails = state.get("api_failures", 0)
    rate = state.get("fail_rate_24h", 0.0)
    align = state.get("bridge_alignment", 0.0)

    ok_rate = 1.0 - rate
    health = "稳" if ok_rate > 0.95 else ("弱" if ok_rate > 0.85 else "危")
    trend = align - 0.5  # 距对齐阈值的距离

    # 2) 写桥维度链
    _wc({
        "src": "脑核·桥",
        "rel": "桥脉冲",
        "dst": f"健康度={health}",
        "dimension": "桥",
        "content": f"桥: {calls}调用/{fails}失败, 成功率={ok_rate:.1%}, 对齐={align:.3f}{'(>0.5✅)' if trend>=0 else '(<0.5⚠️)'}",
        "strength": round(min(1.0, ok_rate), 2)
    })

    # 3) 如果成功率太低，写一条预警链
    if ok_rate < 0.85:
        _wc({
            "src": "脑核·桥",
            "rel": "桥预警",
            "dst": f"成功率={ok_rate:.1%}",
            "dimension": "桥",
            "content": f"桥健康度不足85%，调用成功率={ok_rate:.1%}，需检查API端点",
            "strength": 1.0
        })
        return f"[危] 桥={calls}/{fails} 成功={ok_rate:.1%} 对齐={align:.3f}"

    # 4) 桥对齐趋势
    if align > 0.8:
        return f"[{health}] 桥={calls}调用 对齐={align:.3f}>0.5✅"
    elif align > 0.5:
        return f"[{health}] 桥={calls}调用 对齐={align:.3f}>0.5✅"
    else:
        return f"[{health}] 桥={calls}调用 对齐={align:.3f}<0.5⚠️"


if __name__ == "__main__":
    print(f"工程[桥]: {engineer_桥()}", flush=True)
