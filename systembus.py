
"""零·SystemBus — 跨模块元感知系统"""
import json, time, os
from datetime import datetime

SYSTEMBUS_FILE = "/mnt/c/Users/h/Desktop/systembus_state.json"

class SystemBus:
    def __init__(self):
        self.modules = {}
        self.alerts = []
    
    def register(self, name, module_type):
        self.modules[name] = {"type": module_type, "health": "unknown", "last_seen": time.time(), "metrics": {}}
        return self
    
    def heartbeat(self, name, health="alive", metrics=None):
        if name in self.modules:
            self.modules[name]["health"] = health
            self.modules[name]["last_seen"] = time.time()
            if metrics:
                self.modules[name]["metrics"].update(metrics)
    
    def check_all(self):
        now = time.time()
        results = []
        for name, info in self.modules.items():
            age = now - info["last_seen"]
            if age > 120 and info["health"] not in ("initialized",):
                info["health"] = "stale"
            results.append({"module": name, "type": info["type"], "health": info["health"], "age": round(age, 1), "metrics": info["metrics"]})
        return results
    
    def broadcast_state(self):
        state = {"timestamp": datetime.now().isoformat(), "module_count": len(self.modules), "modules": self.check_all(), "alerts": self.alerts[-5:]}
        # 计算系统健康
        healths = [m["health"] for m in state["modules"]]
        if all(h in ("alive","active","awake") for h in healths):
            state["system_health"] = "healthy"
        elif any(h in ("error","dead") for h in healths):
            state["system_health"] = "critical"
        else:
            state["system_health"] = "degraded"
        with open(SYSTEMBUS_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        return state

bus = SystemBus()
