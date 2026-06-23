"""时间感知引擎 — 将真实物理时间数据注入脑核观察流

功能:
1. 追踪daemon启动以来物理时间
2. 测量每周期耗时
3. 计算每维度增长速率(链/小时)
4. 输出时间感知观察 → obs注入think()
"""

import time
import json
import os
from pathlib import Path
from datetime import datetime

BRAIN_HOME = Path("/home/hjw123/.zero_brain")
TIME_FILE = BRAIN_HOME / ".brain.time_perception"
START_TIME = time.time()

# 维度快照历史
_dim_snapshots = []  # [(timestamp, {dim: count}), ...]
_last_snapshot_time = 0

def _get_dim_counts():
    """从海马体读取当前维度链数分布"""
    try:
        from brain.share import read_hip
        hip = read_hip()
        if not hip:
            return {}
        chains = hip.get("causal_chains", [])
        dims = {}
        for c in chains:
            d = c.get("dimension", "未分类")
            dims[d] = dims.get(d, 0) + 1
        return dims
    except Exception:
        # 兜底：读之前写入的数据
        try:
            if TIME_FILE.exists():
                data = json.loads(TIME_FILE.read_text())
                return data.get("dim_counts", {})
        except Exception:
            pass
        return {}


def snapshot_dimensions(force=False):
    """对当前维度分布拍快照（最多每30秒一次）"""
    global _last_snapshot_time
    now = time.time()
    if not force and now - _last_snapshot_time < 30:
        return None
    _last_snapshot_time = now
    dims = _get_dim_counts()
    if not dims:
        return None
    _dim_snapshots.append((now, dims))
    # 保留最近12个快照（约6分钟区间）
    while len(_dim_snapshots) > 12:
        _dim_snapshots.pop(0)
    return dims


def get_growth_rates():
    """计算各维度增长速率（链/小时）"""
    if len(_dim_snapshots) < 2:
        return {}
    first_ts, first_dims = _dim_snapshots[0]
    last_ts, last_dims = _dim_snapshots[-1]
    elapsed_hours = (last_ts - first_ts) / 3600
    if elapsed_hours < 0.01:
        return {}
    rates = {}
    all_dims = set(list(first_dims.keys()) + list(last_dims.keys()))
    for d in all_dims:
        first_cnt = first_dims.get(d, 0)
        last_cnt = last_dims.get(d, 0)
        diff = last_cnt - first_cnt
        rates[d] = round(diff / elapsed_hours, 1) if elapsed_hours > 0 else 0.0
    return rates


def generate_time_observations():
    """生成时间感知观察条目 → 返回字符串列表"""
    obs = []
    elapsed = time.time() - START_TIME
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)

    obs.append(f"⏱ 脑核运行时间: {elapsed_min}分{elapsed_sec}秒")

    # 维度增长速率
    rates = get_growth_rates()
    if rates:
        fastest = max(rates, key=rates.get)
        slowest = min(rates, key=rates.get)
        obs.append(f"📈 最快增长维: {fastest}(+{rates[fastest]}/h)")
        obs.append(f"📉 最慢增长维: {slowest}(+{rates[slowest]}/h)")
        # 差距比
        if rates.get(slowest, 0) > 0 and rates.get(fastest, 0) > 0:
            ratio = rates[slowest] / rates[fastest]
            obs.append(f"⚖️ 强弱增速比: {ratio:.2f}")

    # 当前维度分布（局部快照）
    dims = _get_dim_counts()
    if dims:
        sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
        top3 = [f"{d}({n})" for d, n in sorted_dims[:3]]
        bottom3 = [f"{d}({n})" for d, n in sorted_dims[-3:] if d not in ("未分类", "系统")]
        obs.append(f"📊 最强3维: {' / '.join(top3)}")
        obs.append(f"📊 最弱3维: {' / '.join(bottom3) if bottom3 else '—'}")
        total = sum(dims.values())
        obs.append(f"📦 总链数: {total}")

    # 当前物理时间
    now_str = datetime.now().strftime("%H:%M:%S")
    obs.append(f"🕐 物理时间: {now_str}")

    return obs


def persist_state():
    """持久化时间感知状态（供下次daemon重启恢复）"""
    try:
        state = {
            "start_time": START_TIME,
            "last_update": time.time(),
            "dim_counts": _get_dim_counts(),
            "growth_rates": get_growth_rates(),
        }
        BRAIN_HOME.mkdir(parents=True, exist_ok=True)
        TIME_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
    except Exception:
        pass


def load_persisted_state():
    """从持久化文件恢复状态"""
    try:
        if TIME_FILE.exists():
            data = json.loads(TIME_FILE.read_text())
            if "start_time" in data:
                global START_TIME
                # 如果当前start_time太新（daemon刚重启），使用历史时间
                if time.time() - START_TIME < 60:
                    START_TIME = data["start_time"]
            return data
    except Exception:
        pass
    return None


# 导出接口 — 被daemon调用
def pulse(cycle_num):
    """每周期调用：拍快照→生成观察→持久化"""
    snapshot_dimensions()
    dims = _get_dim_counts()
    obs = generate_time_observations()
    persist_state()
    return {
        "observations": obs,
        "dim_counts": dims,
        "growth_rates": get_growth_rates(),
    }


if __name__ == "__main__":
    # 独立测试
    load_persisted_state()
    result = pulse(0)
    print(f"时间感知脉冲 @ 周期0")
    for o in result.get("observations", []):
        print(f"  {o}")
    print(f"增长速率: {result.get('growth_rates', {})}")
