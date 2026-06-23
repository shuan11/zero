#!/usr/bin/env python3
"""
self_evolution_loop.py — 自进化闭环系统
========================================
整合所有引擎，形成完整的自进化循环。

闭环流程：
监控 → 预测 → 优化 → 执行 → 验证 → 报告 → 循环

整合引擎：
1. self_evolution_monitor.py: 监控
2. causal_predictor.py: 预测
3. parameter_predictor.py: 优化
4. evolution_orchestrator.py: 执行
5. unified_evolution_controller.py: 统一控制
6. evolution_goal_manager.py: 目标管理
"""
import json
import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime('%H:%M:%S')

def load_hip():
    with open(HIP_FILE) as f:
        return json.load(f)

def save_hip(hip):
    with open(HIP_FILE, 'w') as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)

def run_engine(engine_name, args=None):
    """运行指定引擎"""
    cmd = [sys.executable, f"{engine_name}.py"]
    if args:
        cmd.extend(args)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(CLUSTER)
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-200:] if result.stderr else "",
            "returncode": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "timeout"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def self_evolution_cycle():
    """执行一次完整自进化闭环循环"""
    print(f"[{ts()}] ═══ 自进化闭环循环 ═══")
    
    # Step 1: 监控 - 检查系统状态
    print(f"[{ts()}] Step 1: 监控系统状态")
    hip = load_hip()
    chains = hip.get("causal_chains", [])
    total_chains = len(chains)
    external_chains = len([c for c in chains if '外部世界' in c.get('tags', [])])
    external_ratio = external_chains / total_chains if total_chains > 0 else 0
    
    print(f"  海马体: {total_chains}链 外部:{external_chains}({external_ratio*100:.0f}%)")
    
    # Step 2: 预测 - 使用因果预测引擎
    print(f"[{ts()}] Step 2: 因果预测分析")
    prediction_result = run_engine("causal_predictor", ["--report"])
    if prediction_result["success"]:
        print(f"  预测引擎: ✓")
    else:
        print(f"  预测引擎: ✗ {prediction_result.get('error', '')}")
    
    # Step 3: 优化 - 使用参数预测器
    print(f"[{ts()}] Step 3: 参数优化")
    param_result = run_engine("parameter_predictor", ["--predict"])
    if param_result["success"]:
        print(f"  参数预测: ✓")
    else:
        print(f"  参数预测: ✗ {param_result.get('error', '')}")
    
    # Step 4: 执行 - 运行进化编排器
    print(f"[{ts()}] Step 4: 执行进化循环")
    evolution_result = run_engine("evolution_orchestrator")
    if evolution_result["success"]:
        print(f"  进化编排: ✓")
    else:
        print(f"  进化编排: ✗ {evolution_result.get('error', '')}")
    
    # Step 5: 认知融合 - 运行洞察引擎
    print(f"[{ts()}] Step 5: 认知融合")
    insight_result = run_engine("insight_engine", ["--once"])
    if insight_result["success"]:
        print(f"  洞察引擎: ✓")
    else:
        print(f"  洞察引擎: ✗ {insight_result.get('error', '')}")
    
    # Step 6: 因果推理 - 运行因果推理器
    print(f"[{ts()}] Step 6: 因果推理")
    reasoner_result = run_engine("causal_reasoner", ["--test"])
    if reasoner_result["success"]:
        print(f"  因果推理: ✓")
    else:
        print(f"  因果推理: ✗ {reasoner_result.get('error', '')}")
    
    # Step 7: 目标管理 - 检查进化目标
    print(f"[{ts()}] Step 7: 目标管理")
    goal_result = run_engine("evolution_goal_manager", ["--actions"])
    if goal_result["success"]:
        print(f"  目标管理: ✓")
    else:
        print(f"  目标管理: ✗ {goal_result.get('error', '')}")
    
    # Step 8: 验证 - 检查系统状态变化
    print(f"[{ts()}] Step 8: 验证系统状态")
    hip_new = load_hip()
    new_chains = len(hip_new.get("causal_chains", []))
    new_external = len([c for c in hip_new["causal_chains"] if '外部世界' in c.get('tags', [])])
    new_external_ratio = new_external / new_chains if new_chains > 0 else 0
    
    print(f"  海马体: {new_chains}链 外部:{new_external}({new_external_ratio*100:.0f}%)")
    
    # Step 9: 生成报告
    print(f"[{ts()}] Step 9: 生成进化报告")
    report = {
        "timestamp": datetime.now(BJT).isoformat(),
        "cycle_type": "self_evolution_loop",
        "before": {
            "total_chains": total_chains,
            "external_chains": external_chains,
            "external_ratio": round(external_ratio, 3)
        },
        "after": {
            "total_chains": new_chains,
            "external_chains": new_external,
            "external_ratio": round(new_external_ratio, 3)
        },
        "engines": {
            "prediction": prediction_result["success"],
            "parameter_optimization": param_result["success"],
            "evolution_orchestrator": evolution_result["success"],
            "insight_engine": insight_result["success"],
            "causal_reasoner": reasoner_result["success"],
            "goal_manager": goal_result["success"]
        },
        "changes": {
            "chains_added": new_chains - total_chains,
            "external_change": new_external - external_chains
        }
    }
    
    # 保存报告
    report_file = CLUSTER / "evolution_output" / "self_evolution_loop_report.json"
    report_file.parent.mkdir(exist_ok=True)
    with open(report_file, 'w') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"[{ts()}] ═══ 循环完成 ═══")
    print(f"  链变化: {total_chains} → {new_chains} (+{new_chains - total_chains})")
    print(f"  外部知识: {external_chains} → {new_external} (+{new_external - external_chains})")
    
    return report

if __name__ == "__main__":
    if "--loop" in sys.argv:
        print(f"[{ts()}] 自进化闭环系统启动 (每3600秒)")
        while True:
            try:
                self_evolution_cycle()
            except Exception as e:
                print(f"[{ts()}] 异常: {e}")
            time.sleep(3600)
    else:
        self_evolution_cycle()
