#!/usr/bin/env python3
"""
organ_loader.py — 零·器官加载器
=================================
从_archive逐步恢复旧系统功能模块。

器官注册表：
  phase_1 (基础): [api_strategy, local_brain, engine_core]
  phase_2 (感知): [causal_reasoning, insight_engine, hippocampus_bridge]
  phase_3 (行动): [fuel_burner, evolution_orchestrator, collective_feedback]
  phase_4 (进化): [zaohua_engine, rule_compiler, auto_contract_generator]
  phase_5 (全系统): [neural_cluster, agent_daemon, dashboard_server]

每个器官加载时：
  1. 从_archive复制.py文件
  2. py_compile语法验证
  3. 试运行 --check 或 --help
  4. 注册到海马体
"""

import sys, os, py_compile, subprocess, json
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
ARCHIVE = CLUSTER / "_archive"
LOADED_MARK = CLUSTER / ".loaded_organs.json"


# ─── 器官注册表 ───
# (phase, name, source_file, verify_command, description)

ORGANS = [
    # Phase 1: 基础功能
    (1, "api_strategy",        "api_strategy.py",        ["--check"], "外部API调用策略"),
    (1, "local_brain",         "local_brain.py",         ["--check"], "本地推理引擎"),
    (1, "engine_core",         "engine_core.py",         ["--check"], "核心引擎"),
    (1, "api_bridge",          "api_bridge.py",          ["--check"], "API桥接器"),
    (1, "api_config",          "api_config.py",          None,       "API配置"),
    
    # Phase 2: 感知系统
    (2, "causal_reasoning",    "causal_reasoning_enhancer.py", ["--check"], "因果推理增强器"),
    (2, "insight_engine",      "insight_engine.py",      ["--help"], "洞察引擎"),
    (2, "hippocampus_bridge",  "hippocampus_bridge_for_reasoning.py", ["--check"], "海马体推理桥接"),
    (2, "causal_predictor",    "causal_predictor.py",    ["--check"], "因果预测器"),
    (2, "entity_causal_graph", "entity_causal_graph.py", ["--help"], "实体因果图"),
    
    # Phase 3: 行动系统
    (3, "fuel_burner",         "fuel_burner.py",         ["--check"], "燃料燃烧器"),
    (3, "fuel_burner_v2",      "fuel_burner_v2.py",      ["--check"], "燃料燃烧器v2"),
    (3, "evolution_orchestrator", "evolution_orchestrator.py", ["--check"], "进化编排器"),
    (3, "collective_feedback", "collective_feedback.py", ["--check"], "群体反馈"),
    (3, "auto_evolution_loop", "auto_evolution_loop.py", ["--check"], "自进化循环"),
    (3, "continuous_pipeline", "continuous_pipeline.py", ["--help"], "连续管道"),
    
    # Phase 4: 进化系统
    (4, "zaohua_engine",       "zaohua_engine.py",       ["--help"], "造化引擎"),
    (4, "rule_compiler",       "rule_compiler.py",       ["--help"], "规则编译器"),
    (4, "auto_contract_generator", "auto_contract_generator.py", ["--check"], "自动契约生成"),
    (4, "self_evolution_loop",   "self_evolution_loop.py",  ["--help"], "自进化循环"),
    (4, "evolution_goal_manager", "evolution_goal_manager.py", ["--check"], "进化目标管理"),
    
    # Phase 5: 全系统
    (5, "neural_cluster",      "neural_cluster.py",      ["--check"], "神经集群"),
    (5, "agent_daemon",        "agent_daemon.py",        ["--check"], "Agent守护进程"),
    (5, "dashboard_server",    "dashboard_server.py",    ["--help"], "仪表盘服务器"),
    (5, "co_evolution_daemon", "co_evolution_daemon.py", ["--check"], "协同进化守护"),
    (5, "comprehension_validator", "comprehension_validator.py", ["--check"], "理解验证器"),
]


def load_status():
    """读取已加载器官记录"""
    if LOADED_MARK.exists():
        return json.loads(LOADED_MARK.read_text())
    return {"loaded": [], "failed": [], "phases": {}}


def save_status(status):
    LOADED_MARK.write_text(json.dumps(status, ensure_ascii=False, indent=2))


def load_organ(name, source_file, verify_cmd, phase):
    """加载单个器官"""
    status = load_status()
    
    if name in status["loaded"]:
        print(f"  ⏭️  {name}: 已加载")
        return True
    
    src_path = ARCHIVE / source_file
    dst_path = CLUSTER / source_file
    
    if not src_path.exists():
        print(f"  ❌ {name}: 源文件不存在")
        status["failed"].append(name)
        save_status(status)
        return False
    
    # 语法验证
    try:
        py_compile.compile(str(src_path), doraise=True)
    except py_compile.PyCompileError as e:
        print(f"  ❌ {name}: 语法错误 — {str(e)[:80]}")
        status["failed"].append(name)
        save_status(status)
        return False
    
    # 复制到根目录
    with open(src_path) as f_src:
        content = f_src.read()
    dst_path.write_text(content)
    
    # 运行时验证（如果提供）
    if verify_cmd:
        try:
            r = subprocess.run(
                [sys.executable, str(dst_path)] + verify_cmd,
                capture_output=True, text=True, timeout=15
            )
            if r.returncode != 0:
                print(f"  ⚠️  {name}: 运行check返回{r.returncode}")
                print(f"     stderr: {r.stderr[:100]}")
                # 不阻止加载，只是警告
        except subprocess.TimeoutExpired:
            print(f"  ⚠️  {name}: check超时")
        except Exception as e:
            print(f"  ⚠️  {name}: check异常 — {str(e)[:50]}")
    
    # 注册到海马体
    try:
        from hippocampus_v2 import load as hload, save as hsave, add_chain
        hip = hload()
        add_chain(hip, f"[器官加载] {name}: {description} (Phase{phase})", "organ_loader", ["器官加载", f"P{phase}"])
        hsave(hip)
    except:
        pass
    
    # 记录
    status["loaded"].append(name)
    if name in status["failed"]:
        status["failed"].remove(name)
    if str(phase) not in status["phases"]:
        status["phases"][str(phase)] = []
    status["phases"][str(phase)].append(name)
    save_status(status)
    
    print(f"  ✅  {name}: P{phase} — {description}")
    return True


def load_phase(phase_num):
    """加载整个阶段的器官"""
    phase_organs = [o for o in ORGANS if o[0] == phase_num]
    print(f"\n{'='*50}")
    print(f"Phase {phase_num} 加载")
    print(f"{'='*50}")
    
    success = 0
    for p, name, src, verify, desc in phase_organs:
        if load_organ(name, src, verify, p):
            success += 1
    
    print(f"Phase {phase_num}: {success}/{len(phase_organs)} 加载成功")
    return success


def status_report():
    """报告加载状态"""
    status = load_status()
    loaded = set(status.get("loaded", []))
    failed = set(status.get("failed", []))
    total = len(ORGANS)
    
    print(f"\n{'='*50}")
    print(f"器官加载状态")
    print(f"{'='*50}")
    print(f"总计: {total} 个器官")
    print(f"已加载: {len(loaded)}")
    print(f"失败: {len(failed)}")
    print(f"未加载: {total - len(loaded) - len(failed)}")
    
    for phase in range(1, 6):
        phase_items = [o for o in ORGANS if o[0] == phase]
        phase_loaded = sum(1 for o in phase_items if o[1] in loaded)
        phase_failed = sum(1 for o in phase_items if o[1] in failed)
        print(f"\n  Phase {phase}: {phase_loaded}/{len(phase_items)} ✅  {f'({phase_failed}失败)' if phase_failed else ''}")
        for p, name, src, verify, desc in phase_items:
            icon = "✅" if name in loaded else "❌" if name in failed else "⬜"
            print(f"    {icon} {name}: {desc}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        status_report()
    elif "--phase" in sys.argv and len(sys.argv) > 2:
        load_phase(int(sys.argv[2]))
    elif "--all" in sys.argv:
        for phase in range(1, 6):
            load_phase(phase)
    elif "--organ" in sys.argv and len(sys.argv) > 2:
        name = sys.argv[2]
        for p, n, src, verify, desc in ORGANS:
            if n == name:
                load_organ(n, src, verify, p)
                break
        else:
            print(f"未找到器官: {name}")
    else:
        print("用法: organ_loader.py [--status|--phase N|--all|--organ NAME]")
        print(f"\n器官总数: {len(ORGANS)}")
        print("Phase 1: 基础功能 (API/本地推理/核心引擎)")
        print("Phase 2: 感知系统 (因果推理/洞察/海马体桥接)")
        print("Phase 3: 行动系统 (燃料/进化编排/群体反馈)")
        print("Phase 4: 进化系统 (造化/规则/契约)")
        print("Phase 5: 全系统 (神经集群/Agent守护/仪表盘)")
