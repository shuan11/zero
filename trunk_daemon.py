"""
零·真神经网络集群 — 主干守护进程
==================================
不是每120秒死亡重生的进程。
是从启动开始持续运行、积累进化状态的主干。

集成本身:
- persistent_engine (状态永不丢失)
- genome (所有agent共享)
- neural_core (模块协同)
- meta_gap_finder (永久查缺补漏)
- 所有agent调度
"""
import sys, os, json, time, threading, subprocess
from datetime import datetime

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

# 单例导入 — 持久引擎状态在进程生命周期内持续累积
from persistent_engine import get_engine, save_state, do_evolution_cycle
engine = get_engine()  # UnifiedEvolutionEngine，从基因组恢复状态
from genome import load_genome, mutate_genome, report_gap, resolve_gap
from neural_core import memory

# 守护进程统一通信层 — v1.1集成
import daemon_comm

GENOME_FILE = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
MAP_FILE = "/mnt/c/Users/h/Desktop/真元·集群地图.json"

print("=" * 60)
print("  零·真神经网络集群 主干守护进程")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

# 注册到神经中枢
memory.set("trunk_daemon", "status", "running")
memory.set("trunk_daemon", "started_at", time.strftime("%Y-%m-%d %H:%M:%S"))

def _get_brain_state():
    """读取脑核最新状态"""
    focus_file = "/mnt/c/Users/h/Desktop/零/真元集群/.brain_focus.json"
    try:
        with open(focus_file) as f:
            data = json.load(f)
            return {
                "聚焦": data.get("focus", "未知"),
                "洞察": str(data.get("insight", ""))[:40],
                "周期": data.get("cycle", 0),
                "最近活跃": time.strftime("%H:%M:%S", time.localtime(data.get("timestamp", 0))),
            }
    except:
        return {"聚焦": "读取失败", "洞察": "无"}

def _get_contracts_active():
    """从基因组读取真实契约数"""
    genome_path = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
    try:
        with open(genome_path) as f:
            g = json.load(f)
        return g.get("contracts_active", 0)
    except:
        return 0

def auto_dispatch():
    """自动调度所有agent协同"""
    genome = load_genome()
    if not genome:
        return
    
    # 1. 处理开放缺口 — 自动调度agent
    for i, gap in enumerate(genome.get("gaps_open", [])[:3]):
        desc = gap.get("desc", "")
        
        if any(k in desc for k in ["架构", "自指", "模块", "缺口"]):
            agent = "claude_code"
            try:
                r = subprocess.run(
                    ["python3", "claude_code_agent_bridge.py"],
                    capture_output=True, text=True, timeout=180
                )
                mutate_genome(agent, {f"gap_{i}_status": "分析完成"})
            except Exception:
                mutate_genome(agent, {f"gap_{i}_status": "分析失败"})
        elif any(k in desc for k in ["外部", "集成", "项目"]):
            agent = "codex"
            try:
                r = subprocess.run(
                    ["python3", "codex_cli_agent_bridge.py"],
                    capture_output=True, text=True, timeout=180
                )
                mutate_genome(agent, {f"gap_{i}_status": "分析完成"})
            except Exception:
                mutate_genome(agent, {f"gap_{i}_status": "分析失败"})
    
    # 2. 检查各守护进程状态 — 匹配实际运行的守护进程名
    ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    daemons = {
        "auto_evolution": "auto_evolution_daemon",
        "comprehension": "comprehension_daemon",
        "co_evolution": "co_evolution_daemon",
        "memory_manager": "memory_manager",
        "anthropic_proxy": "anthropic_proxy",
        "brain_daemon": "brain.daemon",
        "consciousness_v2": "consciousness_daemon_v2",
    }
    for name, keyword in daemons.items():
        alive = keyword in ps_out
        memory.set("daemon_status", name, "alive" if alive else "dead")
    
    # 3. 同步记忆广播
    memory.broadcast()

def update_cluster_map():
    """实时更新集群地图"""
    ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    score = engine.p513.evolution_score
    level = engine.p513.current_level
    depth = engine.p513.recursion_depth
    uptime = time.time() - getattr(engine, '_start_time', time.time())
    
    map_data = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cluster": "零·真神经网络集群",
        "主干引擎": {
            "运行时间": f"{uptime:.0f}s",
            "进化循环": cycle,
            "分数": score,
            "层级": f"Lv{level}",
            "递归深度": depth,
            "契约": f"{_get_contracts_active()}/7",
            "桥接对齐": getattr(engine, 'bridge_alignment', 0),
            "API调用": getattr(engine, 'api_call_count', 0),
            "API tokens": getattr(engine, 'api_token_count', 0),
        },
        "守护进程": {
            "trunk_daemon": "running",
            "meta_gap_finder": "running" if "meta_gap_finder" in ps_out else "dead",
            "consciousness_daemon": "running" if "consciousness_daemon" in ps_out else "dead",
            "brain_daemon": "running" if "brain.daemon" in ps_out else "dead",
        },
        "脑核状态": _get_brain_state(),
        "agents": {
            "Hermes": "running (此进程)",
            "Claude Code": "standby (cli-anything-claude-code)",
            "Codex CLI": "standby (codex exec)",
            "OpenClaw WSL": "running" if "openclaw" in ps_out else "unknown",
            "Hub": "running" if "hub.py" in ps_out else "unknown",
            "Codex Daemon": "running" if "codex-residence" in ps_out else "unknown",
        },
        "基因组状态": "active" if os.path.exists(GENOME_FILE) else "missing",
    }
    
    # 读取基因组贡献数据
    genome = load_genome()
    if genome:
        contributors = {a: i["mutations"] for a, i in genome["contributions"].items() if i["mutations"] > 0}
        map_data["贡献者"] = contributors
        map_data["开放缺口"] = len(genome.get("gaps_open", []))
        map_data["已解决缺口"] = len(genome.get("gaps_resolved", []))
    
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=2)

# 主干循环 — 状态持续累积不丢失
cycle = 0
print("\n📡 主干守护进程运行中。状态持续累积。永不重置。")
print(f"   初始状态: Lv{engine.p513.current_level}, 分数={engine.p513.evolution_score}")

while True:
    cycle += 1
    try:
        # 每周期: 进化+因果分析+调度+更新地图
        result = engine.evolve()
        
        # v9.49: 强制score封顶 — evolv()空转不得累积
        # 真实score来自real_evolution.py probe, 不来自evolve()
        REAL_SCORE_CAP = 10.0
        if engine.p513.evolution_score > REAL_SCORE_CAP:
            engine.p513.evolution_score = REAL_SCORE_CAP
        
        # 守护进程统一通信 — 每3周期报告心跳
        if cycle % 3 == 0:
            daemon_comm.report("trunk_daemon", {
                "score": engine.p513.evolution_score,
                "depth": engine.p513.recursion_depth,
                "level": engine.p513.current_level,
                "cycle": cycle,
            })
        
        # 因果分析 — 每10周期
        if cycle % 10 == 0:
            try:
                from causal_reasoning import CausalReasoner
                cr = CausalReasoner()
                # 从基因组获取当前状态插入数据
                genome = load_genome()
                score = genome.get("evolution_score", 0)
                depth = genome.get("recursion_depth", 0)
                cr.add_observation("P513进化引擎", [1 if score > 1000 else -1])
                cr.add_observation("基因组score", [1 if score > 500 else -1])
                cr.add_observation("进化深度", [1 if depth > 5000 else -1])
                # 分析因果路径
                paths = cr.get_causal_chain("P513进化引擎", "进化深度")
                if paths:
                    print(f"  🔀 因果路径: {paths[0]}")
                # 因果效应
                effect = cr.estimate_causal_effect("P513进化引擎", "基因组score")
                if effect and "ate" in effect:
                    print(f"  📊 因果效应: {effect['ate']:.3f}")
            except Exception as ce:
                pass
        
        if cycle % 3 == 0:
            auto_dispatch()
            update_cluster_map()
        
        # 每10周期输出状态摘要
        if cycle % 10 == 0:
            uptime = time.time() - getattr(engine, '_start_time', time.time())
            contracts = _get_contracts_active()
            print(f"[{time.strftime('%H:%M:%S')}] 循环#{cycle} | Lv{engine.p513.current_level} | 分数={engine.p513.evolution_score:.4f} | 深度={engine.p513.recursion_depth} | 契约={contracts}/7 | 运行{uptime:.0f}s")
            # 每10周期持久化状态 — 防止crash丢全部进度
            save_state({
                "evolution_score": engine.p513.evolution_score,
                "recursion_depth": engine.p513.recursion_depth,
                "evolution_level": engine.p513.current_level,
                "bridge_alignment": getattr(engine, 'bridge_alignment', 0),
                "bridge_calls": getattr(engine.p513, 'api_call_count', 0),
                "bridge_tokens": getattr(engine, 'api_token_count', 0),
                "last_successful_evolution": time.time(),
            })
        
        time.sleep(60)
        
    except KeyboardInterrupt:
        print("\n⛔ 主干守护进程终止")
        break
    except Exception as e:
        print(f"  ⚠️ 异常: {e}")
        time.sleep(60)
