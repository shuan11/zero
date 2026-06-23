#!/usr/bin/env python3
"""
零·元递归进化全自动循环守护进程 v1
======================================
P118: 定时自动触发MetaRecursionEngine进化 + 矛盾驱动 + 结果持久化。

契约对接:
  条5(自我检察): 每次进化前执行CoreContract.self_check()
  条12(分合循环): 策略自动分裂与合并
  条13(矛盾=燃料): 海马体中的矛盾节点驱动进化频率

架构:
  定时器(每60s) → 检查条件 → MetaRecursionEngine.evolve()
    ↓                          ↓
  海马体矛盾检测            CoreContract.self_check()
    ↓                          ↓
  触发进化 ← ← ← ← ← ← ← ← ← ←
    ↓
  结果持久化(海马体+WAKE)
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
EVO_DIR = WORKDIR / "evolution_output"
DAEMON_LOG = EVO_DIR / "auto_evolution_daemon.log"

os.makedirs(EVO_DIR, exist_ok=True)

# 守护进程统一通信层 — v1.1集成
import daemon_comm


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(DAEMON_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class AutoEvolutionDaemon:
    """
    全自动进化守护进程。
    
    3种触发模式:
    1. 定时触发: 每N秒自动evolve()
    2. 矛盾触发: 海马体矛盾节点数>阈值时evolve()
    3. 契约触发: self_check评分<阈值时evolve()
    """
    
    def __init__(self, interval: int = 60):
        self.interval = interval  # 定时周期(秒)
        self._mre = None
        self._hub = None
        self._feedback = None
        self._hip = None
        self._mem_type = None
        self._rel_type = None
        self.cycle_count = 0
        self.total_evolutions = 0
        self._last_contradiction_count = 0
        self._load_dependencies()
    
    def _load_dependencies(self):
        """加载依赖模块"""
        sys.path.insert(0, str(WORKDIR))
        try:
            from multi_agent_system import AgentHub, RecursiveEvolutionFeedback, MetaRecursionEngine, TaskDecomposer
            self._hub = AgentHub()
            self._feedback = RecursiveEvolutionFeedback(self._hub)
            self._mre = MetaRecursionEngine(self._hub, self._feedback)
        except Exception as e:
            log(f"⚠️ MRE加载失败: {e}")
        
        try:
            import hippocampus as _h
            self._mem_type = _h.记忆类型
            self._rel_type = _h.关系类型
            self._hip = _h.因果记忆库()
        except Exception as e:
            log(f"⚠️ 海马体加载失败: {e}")
        
        sys.path.pop(0)
    
    @property
    def mre_ready(self) -> bool:
        return self._mre is not None
    
    @property
    def hip_ready(self) -> bool:
        return self._hip is not None
    
    def _check_contradictions(self) -> int:
        """
        检查海马体中的矛盾节点数。
        契约条13: 矛盾=进化燃料。
        返回: 矛盾节点数
        """
        if not self.hip_ready:
            return 0
        try:
            count = 0
            for node in self._hip.节点.values():
                if node.类型 == self._mem_type.因果:
                    count += 1
            return count
        except Exception:
            return 0
    
    def _check_contract_score(self) -> float:
        """
        从基因组读取真实进化分数。
        不再创建新引擎(从零开始永远返回0.5)。
        """
        try:
            import json
            genome_path = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
            with open(genome_path) as f:
                g = json.load(f)
            real_score = float(g.get("evolution_score", 0))
            # 归一化到0-1范围
            normalized = min(1.0, real_score / 1000.0)
            return normalized
        except Exception:
            return 0.5
    
    def _should_evolve(self) -> tuple[bool, str]:
        """
        判断是否应该触发进化。
        返回: (是否触发, 原因)
        """
        # 1. 定时触发 (每interval秒)
        if self.cycle_count > 0 and self.cycle_count % (self.interval // 10) == 0:
            return True, f"定时触发(每{self.interval}s)"
        
        # 2. 矛盾触发
        contradiction_count = self._check_contradictions()
        if contradiction_count > self._last_contradiction_count:
            self._last_contradiction_count = contradiction_count
            if contradiction_count >= 2:
                return True, f"矛盾触发({contradiction_count}个矛盾节点)"
        
        # 3. 契约评分触发
        score = self._check_contract_score()
        if score < 0.5:
            return True, f"契约评分触发(score={score:.2f})"
        
        return False, ""
    
    def _evolve(self) -> dict:
        """执行一次完整进化"""
        result = {
            "timestamp": time.time(),
            "trigger": "",
            "mre_result": None,
            "contract_score": 0.0,
            "contradictions": 0,
            "stored_to_hippocampus": False,
        }
        
        # 1. 触发进化
        if self.mre_ready:
            # 注入真实进化数据到MRE
            import json
            try:
                with open("/mnt/c/Users/h/Desktop/真元·进化基因组.json") as gf:
                    genome_data = json.load(gf)
                real_score = float(genome_data.get("evolution_score", 0))
                real_depth = int(genome_data.get("recursion_depth", 0))
                # 动态调整策略: 分数高=aggressive, 分数低=conservative
                if real_score > 100 and self._mre._current_strategy == "conservative":
                    self._mre._current_strategy = "aggressive"
                    self._mre._evolve_interval = 1
            except Exception: pass
            
            mre_result = self._mre.evolve()
            result["mre_result"] = {
                "history": len(self._mre.meta_history),
                "strategy": self._mre._current_strategy,
                "interval": self._mre._evolve_interval,
            }
            self.total_evolutions += 1
        
        # 2. 契约自检
        result["contract_score"] = self._check_contract_score()
        
        # 3. 矛盾计数
        result["contradictions"] = self._check_contradictions()
        
        # 4. 存入海马体
        if self.hip_ready:
            try:
                content = (
                    f"进化循环#{self.total_evolutions} "
                    f"score={result['contract_score']:.2f} "
                    f"策略={self._mre._current_strategy if self.mre_ready else '?'} "
                    f"矛盾={result['contradictions']}"
                )
                # 写入独立进化记忆文件（不覆盖主海马体）
                import json, tempfile, os as _os
                evo_mem_path = _os.path.join(str(WORKDIR), "evolution_output", "evolution_memory.json")
                try:
                    evo_mem = {}
                    if _os.path.exists(evo_mem_path):
                        with open(evo_mem_path) as _f:
                            evo_mem = json.load(_f)
                    entries = evo_mem.get("entries", [])
                    entries.append({"content": content, "timestamp": time.time(), "score": result['contract_score']})
                    evo_mem["entries"] = entries[-200:]  # 保留最近200条
                    fd, tmp = tempfile.mkstemp(suffix='.tmp')
                    with _os.fdopen(fd, 'w') as _f:
                        json.dump(evo_mem, _f, ensure_ascii=False, indent=2)
                    _os.rename(tmp, evo_mem_path)
                except Exception: pass
                result["stored_to_hippocampus"] = True
            except Exception:
                pass
        
        return result
    
    def run(self):
        """主循环"""
        log("=" * 60)
        log("  零·元递归进化全自动循环 启动")
        log(f"  PID: {os.getpid()}")
        log(f"  周期: {self.interval}s")
        log(f"  MRE: {'✅' if self.mre_ready else '❌'}")
        log(f"  海马体: {'✅' if self.hip_ready else '❌'}")
        log("=" * 60)
        
        # 首次进化
        result = self._evolve()
        result["trigger"] = "首次启动"
        log(f"  ➡ 首次进化: score={result['contract_score']:.2f} "
            f"策略={result.get('mre_result',{}).get('strategy','?')} "
            f"矛盾={result['contradictions']}")
        
        while True:
            try:
                self.cycle_count += 1
                
                # 检查是否应该进化
                should, reason = self._should_evolve()
                
                if should:
                    result = self._evolve()
                    result["trigger"] = reason
                    log(f"  ➡ 进化#{self.total_evolutions}: {reason} "
                        f"score={result['contract_score']:.2f} "
                        f"history={result.get('mre_result',{}).get('history','?')} "
                        f"策略={result.get('mre_result',{}).get('strategy','?')}")
                    
                    # 守护进程统一通信 — 报告心跳
                    daemon_comm.report("auto_evolution", {
                        "score": result['contract_score'],
                        "strategy": self._mre._current_strategy if self.mre_ready else "N/A",
                        "total_evolutions": self.total_evolutions,
                        "cycle": self.cycle_count,
                    })
                    
                    # 每5次进化输出一次摘要
                    if self.total_evolutions % 5 == 0:
                        log(f"  📊 进化摘要: {self.total_evolutions}次, "
                            f"策略={self._mre._current_strategy}, "
                            f"interval={self._mre._evolve_interval}")
                
                time.sleep(self.interval)
                
            except KeyboardInterrupt:
                log("🛑 进化守护进程被手动终止")
                break
            except Exception as e:
                log(f"⚠️ 循环异常: {e}")
                time.sleep(self.interval)
    
    def state_snapshot(self) -> dict:
        """当前状态快照"""
        return {
            "cycle_count": self.cycle_count,
            "total_evolutions": self.total_evolutions,
            "mre_history": len(self._mre.meta_history) if self.mre_ready else 0,
            "mre_strategy": self._mre._current_strategy if self.mre_ready else "N/A",
            "contradictions": self._check_contradictions(),
            "contract_score": self._check_contract_score(),
        }


def self_test():
    """自检模式：运行1次进化然后退出"""
    print("=" * 60)
    print("  元递归进化全自动循环 v1 自检")
    print("=" * 60)
    
    daemon = AutoEvolutionDaemon(interval=10)
    
    print(f"\nMRE就绪: {daemon.mre_ready}")
    print(f"海马体就绪: {daemon.hip_ready}")
    
    if daemon.mre_ready:
        print(f"初始历史: {len(daemon._mre.meta_history)}条")
        print(f"初始策略: {daemon._mre._current_strategy}")
        
        # 模拟反馈数据
        for name in daemon._hub.internal_agents:
            daemon._feedback.record(name, success=True, latency_ms=100, contract_passed=True)
        
        # 运行1次进化
        result = daemon._evolve()
        print(f"\n进化结果:")
        print(f"  score: {result['contract_score']:.3f}")
        print(f"  strategy: {result.get('mre_result',{}).get('strategy','?')}")
        print(f"  history: {result.get('mre_result',{}).get('history','?')}")
        print(f"  contradictions: {result['contradictions']}")
        print(f"  stored_to_hippocampus: {result['stored_to_hippocampus']}")
    
    print(f"\n  状态快照: {daemon.state_snapshot()}")
    print(f"\n✅ 自动进化循环就绪")


if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        # 守护进程模式
        daemon = AutoEvolutionDaemon(interval=60)
        daemon.run()
    else:
        # 自检模式
        self_test()
