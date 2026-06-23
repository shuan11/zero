"""brain/evolution_view.py — 查看进化系统状态"""
import json
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent

def show_evolution_status():
    """打印完整进化状态"""
    try:
        lineage = json.loads((CLUSTER / ".brain_evolution.json").read_text())
    except:
        lineage = {"generations": [], "current_gen": 0}
    
    try:
        fitness_log = json.loads((CLUSTER / ".brain_fitness.json").read_text())
    except:
        fitness_log = {"history": []}
    
    gens = lineage.get("generations", [])
    pending = lineage.get("pending_mutation")
    fitness_history = fitness_log.get("history", [])
    
    print("=" * 60)
    print(f"🧬 进化系统状态")
    print(f"   世代: {lineage.get('current_gen', 0)}")
    print(f"   已完成世代: {len(gens)}")
    print(f"   待评估变异: {'有' if pending else '无'}")
    print()
    
    if gens:
        print("── 世系记录(最后10代) ──")
        for g in gens[-10:]:
            kept = "✅保留" if g.get("kept") else "❌淘汰"
            diff = g.get("diff", 0)
            print(f"  代#{g['generation']}: {g.get('gene','?')} {g.get('old_value','?')}→{g.get('new_value','?')} "
                  f"适应度:{g.get('baseline_fitness','?')}→{g.get('current_fitness','?')} "
                  f"({'+' if diff>0 else ''}{diff:.4f}) {kept}")
    
    if fitness_history:
        print()
        print("── 适应度轨迹(最近20周期) ──")
        for h in fitness_history[-20:]:
            phase = {"mutation": "🧬", "selection": "⚖", "running": "·"}.get(h.get("phase",""), "·")
            print(f"  [{h.get('cycle',0):>4}] 代{h.get('generation',0)} {phase} 适应度:{h.get('fitness',0):.4f}")
    
    print()
    
    # 统计
    if gens:
        kept_count = sum(1 for g in gens if g.get("kept"))
        reverted_count = sum(1 for g in gens if not g.get("kept"))
        print(f"── 统计 ──")
        print(f"   保留变异: {kept_count}/{len(gens)} ({kept_count/max(len(gens),1)*100:.0f}%)")
        print(f"   淘汰变异: {reverted_count}/{len(gens)} ({reverted_count/max(len(gens),1)*100:.0f}%)")
        avg_fitness = sum(g.get("current_fitness", 0) for g in gens) / max(len(gens), 1)
        print(f"   平均适应度: {avg_fitness:.4f}")
    
    # 当前基因组
    try:
        from brain.genome import load_genome
        g = load_genome()
        print()
        print("── 当前基因组(关键参数) ──")
        for k, v in sorted(g.items()):
            if not k.startswith("_"):
                print(f"   {k} = {v}")
    except:
        pass

if __name__ == "__main__":
    show_evolution_status()
