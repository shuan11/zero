"""
零·真协同进化永续守护进程 v2
=============================
使用 persistent_engine 确保进化状态跨进程持久不归零。
每轮循环: 读取持久状态 → 处理缺口→ 进化 → 突变基因组 → 更新地图
"""
import sys, os, json, time, subprocess

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

from genome import load_genome, mutate_genome, report_gap
from persistent_engine import do_evolution_cycle, load_state, save_state

GENOME_FILE = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
MAP_FILE = "/mnt/c/Users/h/Desktop/真元·集群地图.json"

print("=" * 60)
print("  零·真协同进化引擎 v2 (持久进化)")
print(f"  {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

cycle = 0

def update_map():
    """更新集群地图"""
    ps_out = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5).stdout
    state = load_state()
    
    map_data = {
        "version": "v2-auto",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "拓扑结构": {
            "co_evolution_daemon": {"状态": "运行中", "间隔": "120s"},
            "meta_gap_finder": {"状态": "运行中" if "meta_gap_finder" in ps_out else "死亡", "间隔": "60s"},
            "persistent_engine": {"状态": "活跃", "持久状态文件": "persistent_state.json"},
            "Hermes": {"状态": "运行中" if "hermes" in ps_out else "未知"},
            "OpenClaw": {"状态": "运行中" if "openclaw" in ps_out else "未知"},
            "Codex Daemon": {"状态": "运行中" if "codex-residence" in ps_out else "未知"},
            "Hub": {"状态": "运行中" if "hub.py" in ps_out else "未知"},
        },
        "进化状态": {
            "分数": state.get("evolution_score", 0),
            "层级": state.get("evolution_level", 0),
            "递归深度": state.get("recursion_depth", 0),
            "API调用": state.get("bridge_calls", 0),
        }
    }
    with open(MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(map_data, f, ensure_ascii=False, indent=2)

print("\n📡 12秒后开始第一轮...")
time.sleep(12)

while True:
    cycle += 1
    try:
        print(f"\n🔄 协同进化 #{cycle} [{time.strftime('%H:%M:%S')}]")
        
        # 1. 读取基因组和持久状态
        genome = load_genome()
        state = load_state()
        print(f"  状态: score={state.get('evolution_score',0):.4f}, Lv={state.get('evolution_level',0)}, depth={state.get('recursion_depth',0)}")
        
        # 2. 处理开放缺口
        open_gaps = genome.get("gaps_open", [])
        if open_gaps:
            gap = open_gaps[0]
            print(f"  处理缺口: {gap.get('desc','')[:60]}")
            try:
                subprocess.run(["python3", "claude_code_agent_bridge.py"], capture_output=True, text=True, timeout=120)
                report_gap("claude_code", f"分析完成: {gap.get('desc','')[:50]}")
            except Exception:
                pass
        
        # 3. 执行进化（使用持久引擎，不归零）
        result = do_evolution_cycle()
        if result.get("success"):
            print(f"  进化: score={result['score']:.4f}, Lv={result['level']}, depth={result['depth']}")
            mutate_genome("co_evolution_daemon", {
                "evolution_score": result["score"],
                "evolution_level": result["level"],
                "recursion_depth": result["depth"],
            })
        elif result.get("skipped"):
            print(f"  跳过: {result.get('reason','')}")
        else:
            print(f"  进化异常: {result.get('error','')}")
        
        # 4. 更新地图
        update_map()
        
    except Exception as e:
        print(f"  ⚠️ 异常: {e}")
    
    time.sleep(120)
