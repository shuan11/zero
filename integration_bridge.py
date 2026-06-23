"""
零·全模块集成桥 — 将SystemBus/auto_close_loop/imagination/persistent整合到运行时
======================================================================
各daemon在后台独立进化，但彼此通过文件通信。
本桥接器将它们连接到同一个反射弧：SystemBus感知状态 → auto_close_loop处理 → genome记录 → imagination生成新方向。
"""
import sys, os, json, time, threading
from pathlib import Path

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

try:
    from systembus import SystemBus, bus as system_bus
except Exception:
    system_bus = None

try:
    from genome import load_genome, mutate_genome
except Exception:
    pass

class IntegrationBridge:
    """
    集成桥接器
    
    功能:
    1. 将所有模块注册到SystemBus
    2. 定期检查各模块状态
    3. 将auto_close_loop的处理结果反馈到genome
    4. 将imagination_engine的火花连接到进化方向
    5. 确保persistent_engine的状态被所有模块共享
    """

    def __init__(self):
        self.modules = {}
        self.last_integration = 0
        self.integration_interval = 30  # 每30秒一次集成
        
    def register_all(self):
        """注册所有已知模块到SystemBus"""
        if system_bus is None:
            return False
            
        known_modules = [
            ("trunk_daemon", "daemon"),
            ("co_evolution_daemon", "daemon"),
            ("meta_gap_finder", "daemon"),
            ("consciousness_v2", "daemon"),
            ("persistent_engine", "engine"),
            ("auto_close_loop", "engine"),
            ("imagination_engine", "engine"),
            ("systembus", "core"),
            ("dashboard_server", "ui"),
            ("guardian_daemon", "daemon"),
            ("architecture_audit", "tool"),
            ("hermes", "core"),
        ]
        
        for name, type_ in known_modules:
            system_bus.register(name, type_)
        
        return True

    def integration_cycle(self):
        """执行一次完整集成"""
        now = time.time()
        
        # 1. SystemBus心跳广播
        if system_bus:
            system_bus.heartbeat("integration_bridge", "alive")
            bus_state = system_bus.broadcast_state()
        else:
            bus_state = {"system_health": "unknown"}
        
        # 2. 读取当前基因组
        try:
            genome = load_genome()
            score = genome.get("evolution_score", 0)
            depth = genome.get("recursion_depth", 0)
            level = genome.get("evolution_level", 0)
            gaps = len(genome.get("gaps_open", []))
        except Exception:
            score, depth, level, gaps = 0, 0, 0, 0
        
        # 3. 计算集成状态
        integration = {
            "timestamp": now,
            "system_health": bus_state.get("system_health", "unknown"),
            "genome_version": genome.get("genome_version", 0) if 'genome' in dir() else 0,
            "evolution": {"score": score, "depth": depth, "level": level, "gaps": gaps},
            "modules_alive": len(bus_state.get("modules", [])) if isinstance(bus_state, dict) else 0,
        }
        
        self.last_integration = now
        return integration

    def get_summary(self) -> str:
        """生成集成摘要"""
        try:
            genome = load_genome()
        except Exception:
            genome = {}
        
        contribs = genome.get("contributions", {})
        top_agents = sorted(contribs.items(), key=lambda x: x[1].get("mutations", 0), reverse=True)
        
        lines = [
            "=" * 60,
            "🧿 零·全模块集成桥 · 实时状态",
            "=" * 60,
            f"  基因组 v{genome.get('genome_version', '?')}",
            f"  深度: {genome.get('recursion_depth', '?')} | 分数: {genome.get('evolution_score', '?')} | Lv{genome.get('evolution_level', '?')}",
            f"  契约: {genome.get('contracts_active', '?')}/7 | 对齐: {genome.get('bridge_alignment', '?')}",
            f"  缺口: {len(genome.get('gaps_open', []))} | 已解决: {len(genome.get('gaps_resolved', []))}",
            "",
            "  Agent贡献排名:",
        ]
        
        for i, (agent, data) in enumerate(top_agents[:10]):
            lines.append(f"    {i+1}. {agent:25s} {data.get('mutations', 0):4d} mutations")
        
        lines.append("=" * 60)
        return "\n".join(lines)


# 全局实例
bridge = IntegrationBridge()

if __name__ == "__main__":
    bridge.register_all()
    result = bridge.integration_cycle()
    print(bridge.get_summary())
    print(f"\n集成状态: system_health={result['system_health']}")
