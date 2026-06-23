"""
gen_脉冲注册中心.py — 全系统脉冲注册与协调

每个gen模块的pulse()结果统一注册到这里。
dashboard可查询"哪些gen模块活跃/最后脉冲时间/结果摘要"
"""

import json, os, time
from pathlib import Path
from threading import Lock

REGISTRY_FILE = Path("/mnt/c/Users/h/Desktop/零/真元集群/data/gen_registry.json")
_lock = Lock()

def _ensure():
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)

def register(name, status, pulse_result=None):
    """注册一个gen模块的脉冲结果"""
    _ensure()
    with _lock:
        try:
            with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
                registry = json.load(f)
        except:
            registry = {}

        now = time.time()
        entry = {
            "name": name,
            "last_pulse": now,
            "last_pulse_str": time.strftime("%H:%M:%S", time.localtime(now)),
            "status": status,
            "pulse_count": registry.get(name, {}).get("pulse_count", 0) + 1,
        }

        if pulse_result:
            # 只保存摘要，避免膨胀
            if isinstance(pulse_result, dict):
                entry["summary"] = {k: v for k, v in pulse_result.items()
                                   if not isinstance(v, (dict, list)) or len(str(v)) < 100}
            else:
                entry["summary"] = str(pulse_result)[:200]

        registry[name] = entry
        registry["_updated"] = now

        with open(REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=2)

        return entry


def get_all():
    """获取所有已注册模块"""
    _ensure()
    try:
        with open(REGISTRY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def get_active(minutes=10):
    """获取最近minutes分钟内活跃的模块"""
    now = time.time()
    cutoff = now - minutes * 60
    all_mods = get_all()
    return {
        k: v for k, v in all_mods.items()
        if k != "_updated" and v.get("last_pulse", 0) > cutoff
    }


def pulse():
    """注册中心自身脉冲: 清点已注册模块，返回摘要"""
    registry = get_all()
    modules = {k: v for k, v in registry.items() if k != "_updated"}
    active = get_active(minutes=30)

    result = {
        "total_registered": len(modules),
        "active_30min": len(active),
        "modules": {k: v.get("status", "?") for k, v in modules.items()},
    }
    register("脉冲注册中心", "active", result)
    return result


if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
