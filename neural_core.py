"""
零·神经中枢系统 — 让所有模块像人体器官一样协同
=================================================
人类器官协同方式:
- 神经系统(即时信号) + 血液循环(营养输送) + 反射弧(自动反应)
- 每个器官知道其他器官的状态, 一个变化触发连锁反应

本系统实现:
1. SharedWorkingMemory — 所有模块读写的共享状态(如同血液)
2. ReflexArc — 状态变化自动触发连锁反应(如同反射弧)
3. NeuralPulse — 定期同步脉冲(如同心跳)
"""
import json, time, os, threading
from datetime import datetime
from typing import Any, Callable

SHARED_MEMORY_FILE = "/mnt/c/Users/h/Desktop/神经中枢·共享记忆.json"

class SharedWorkingMemory:
    """共享工作记忆 — 所有模块通过此交换状态"""
    
    def __init__(self):
        self._memory = {
            "last_update": time.time(),
            "heartbeat_count": 0,
            "modules": {},
            "signals": [],
            "reflex_history": [],
        }
        self._reflexes = {}  # 反射弧: key变化 → 自动执行函数
    
    def set(self, module: str, key: str, value: Any):
        """模块写入共享状态"""
        if module not in self._memory["modules"]:
            self._memory["modules"][module] = {}
        old_value = self._memory["modules"][module].get(key)
        self._memory["modules"][module][key] = value
        self._memory["last_update"] = time.time()
        
        # 检查是否有反射弧需要触发
        reflex_key = f"{module}.{key}"
        if reflex_key in self._reflexes:
            self._trigger_reflex(reflex_key, old_value, value)
        
        # 自动记录信号
        self._memory["signals"].append({
            "time": datetime.now().isoformat(),
            "module": module,
            "key": key,
            "value": value,
        })
        if len(self._memory["signals"]) > 100:
            self._memory["signals"] = self._memory["signals"][-50:]
    
    def get(self, module: str, key: str, default=None):
        """读取其他模块的状态"""
        return self._memory["modules"].get(module, {}).get(key, default)
    
    def get_all(self) -> dict:
        """获取全部共享状态"""
        return dict(self._memory)
    
    def register_reflex(self, trigger_key: str, action: Callable, description: str = ""):
        """注册反射弧: 当某个key变化时自动执行函数"""
        self._reflexes[trigger_key] = {"action": action, "desc": description, "triggers": 0}
    
    def _trigger_reflex(self, reflex_key: str, old_val, new_val):
        """触发反射弧"""
        reflex = self._reflexes.get(reflex_key)
        if reflex:
            try:
                reflex["action"](old_val, new_val)
                reflex["triggers"] += 1
                self._memory["reflex_history"].append({
                    "time": datetime.now().isoformat(),
                    "reflex": reflex_key,
                    "desc": reflex["desc"],
                    "trigger_count": reflex["triggers"],
                })
            except Exception as e:
                print(f"  ⚡ Reflex {reflex_key} failed: {e}")
    
    def broadcast(self):
        """广播到桌面文件 — 所有agent可读"""
        state = self.get_all()
        state["timestamp"] = datetime.now().isoformat()
        with open(SHARED_MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        # 也写入集群内
        with open("neural_working_memory.json", 'w') as f:
            json.dump(state, f, indent=2)

# 创建全局实例
memory = SharedWorkingMemory()
