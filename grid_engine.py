"""
grid_engine.py — 网格引擎框架

万物皆插件到统一引擎。
所有零的引擎(超感/举一反三/触类旁通/教员/直觉桥/抗虚空等)
通过标准生命周期注册到网格引擎。

核心设计:
  grid = 所有可能插件的宇宙
  engine = 运行它们的框架
  每个插件: 标准pulse()接口 + 元数据 + 健康状态
  跨插件: 通过共享状态总线通信(非直写文件)

取代:
  - 每个引擎独立的pulse()调用
  - 各自写自己的状态文件
  - 无统一生命周期管理

用法:
  engine = GridEngine()
  engine.register("supersense", pulse_func, deps=[], interval=1)
  engine.register("analogy", pulse_func, deps=["supersense"], interval=1)
  engine.run_all()  # 按依赖顺序执行所有插件
"""

import json
import time
import threading
from pathlib import Path
from collections import OrderedDict
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent

class GridEngine:
    """网格引擎: 统一管理所有插件的生命周期"""
    
    def __init__(self):
        self._plugins = OrderedDict()  # name -> plugin_info
        self._shared_state = {}        # 插件间共享状态总线
        self._history = []             # 运行历史
        self._running = False
    
    def register(self, name, pulse_func, deps=None, interval=1, metadata=None):
        """注册插件到网格
        
        参数:
            name: 插件名 (如 "supersense", "analogy")
            pulse_func: 调用函数 pulse() -> dict
            deps: 依赖插件列表 (如 ["supersense"])
            interval: 每次run_all之间的间隔(cycle数, 默认1=每cycle)
            metadata: 可选元数据 dict
        """
        self._plugins[name] = {
            "name": name,
            "pulse": pulse_func,
            "deps": deps or [],
            "interval": interval,
            "metadata": metadata or {},
            "health": 1.0,
            "last_run": 0,
            "last_output": None,
            "errors": 0,
            "cycle_count": 0,
        }
        return self
    
    def unregister(self, name):
        """热卸载插件"""
        if name in self._plugins:
            del self._plugins[name]
    
    def get_state(self, key, default=None):
        """从共享状态总线读"""
        return self._shared_state.get(key, default)
    
    def set_state(self, key, value):
        """写入共享状态总线"""
        self._shared_state[key] = value
    
    def pulse(self, name):
        """运行单个插件"""
        plugin = self._plugins.get(name)
        if not plugin:
            return {"error": f"plugin {name} not found"}
        try:
            result = plugin["pulse"]()
            plugin["last_run"] = time.time()
            plugin["last_output"] = result
            plugin["cycle_count"] += 1
            # 写共享状态
            self._shared_state[f"{name}:last"] = result
            self._shared_state[f"{name}:time"] = time.time()
            return result
        except Exception as e:
            plugin["errors"] += 1
            plugin["health"] = max(0, plugin["health"] - 0.1)
            return {"error": str(e)}
    
    def run_all(self):
        """按依赖顺序执行所有已注册插件"""
        results = {}
        # 拓扑排序: 先执行无依赖的, 再执行有依赖的
        executed = set()
        while len(executed) < len(self._plugins):
            before = len(executed)
            for name, plugin in self._plugins.items():
                if name in executed:
                    continue
                # 检查依赖是否都已执行
                deps_met = all(d in executed for d in plugin["deps"])
                if deps_met:
                    results[name] = self.pulse(name)
                    executed.add(name)
            if len(executed) == before:
                break  # 剩余插件有循环依赖
        self._history.append({
            "time": time.time(),
            "plugins": list(results.keys()),
            "status": "ok",
        })
        return results
    
    def health_report(self):
        """所有插件健康报告"""
        report = {}
        for name, plugin in self._plugins.items():
            report[name] = {
                "health": plugin["health"],
                "cycles": plugin["cycle_count"],
                "errors": plugin["errors"],
                "last_run": plugin["last_run"],
                "deps": plugin["deps"],
            }
        return report
    
    def summary(self):
        """网格引擎摘要"""
        total = len(self._plugins)
        healthy = sum(1 for p in self._plugins.values() if p["health"] > 0.5)
        active = sum(1 for p in self._plugins.values() if p["cycle_count"] > 0)
        return {
            "plugins": total,
            "healthy": healthy,
            "active": active,
            "shared_state_keys": list(self._shared_state.keys()),
            "history_count": len(self._history),
        }


# 默认全局实例(单例模式)
_default_engine = None

def get_engine():
    """获取全局网格引擎实例"""
    global _default_engine
    if _default_engine is None:
        _default_engine = GridEngine()
    return _default_engine


# ─── 自动注册: 扫描并注册所有可用引擎 ───

def auto_register():
    """自动扫描集群中的所有引擎文件并注册到网格
    
    检测标准: 文件有 pulse() 函数
    """
    engine = get_engine()
    
    # 已知引擎映射
    known_engines = {
        "supersense": {
            "module": "organs.supersense_organ",
            "deps": [],
        },
        "analogy": {
            "module": "触类旁通",
            "deps": ["supersense"],
        },
        "generalize": {
            "module": "举一反三",
            "deps": ["supersense"],
        },
        "teacher": {
            "module": "教员",
            "deps": [],
        },
        "intuition": {
            "module": "super_intuition_bridge",
            "deps": ["supersense", "generalize"],
        },
        "anti_entropy": {
            "module": "anti_entropy",
            "deps": [],
        },
        "autonomy": {
            "module": "autonomy_engine",
            "deps": [],
        },
        "redshift": {
            "module": "memory_redshift",
            "deps": [],
        },
        "cross_connect": {
            "module": "cross_connect",
            "deps": ["supersense", "generalize", "anti_entropy"],
        },
        "proposer": {
            "module": "evolution_proposer",
            "deps": ["supersense", "analogy", "generalize", "teacher", "cross_connect"],
        },
    }
    
    for name, info in known_engines.items():
        try:
            mod = __import__(info["module"], fromlist=["pulse"])
            if hasattr(mod, "pulse"):
                engine.register(name, mod.pulse, deps=info["deps"])
        except ImportError:
            pass  # 模块不存在, 跳过
    
    return engine


# ─── 独立运行 ───
if __name__ == "__main__":
    e = auto_register()
    print("网格引擎初始化完成:")
    print(json.dumps(e.summary(), indent=2, ensure_ascii=False))
    print("\n运行一次所有插件...")
    results = e.run_all()
    for name, result in results.items():
        status = "✅" if "error" not in result else "❌"
        print(f"  {status} {name}: {str(result)[:80]}")
    print(f"\n健康报告:")
    print(json.dumps(e.health_report(), indent=2, ensure_ascii=False))
