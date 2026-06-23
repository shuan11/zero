#!/usr/bin/env python3
"""
深度器官桥梁——让P516的8个器官真正读取外部项目源代码并执行真实逻辑
而非仅仅mock返回字典。

实测验证:
  1. Agent-Reach: 真正调用agent_reach.doctor.check_all()健康检查
  2. Edict: 真正使用file_lock的atomic_json原子读写
  3. Edict: 真正导入court_discuss官员Profile进行议政
  4. 未安装依赖的项目: 优雅降级为源码扫描
"""
import sys
import json
import os
import time
from pathlib import Path
from datetime import datetime

EXTERNAL = Path("/mnt/c/Users/h/Desktop/零/真元集群/external_projects")

results = {"passed": 0, "failed": 0, "details": []}

def test(name, fn):
    try:
        ok = fn()
        results["passed" if ok else "failed"] += 1
        results["details"].append({"name": name, "status": "PASS" if ok else "FAIL"})
        print(f"  {'✅' if ok else '❌'} {name}")
    except Exception as e:
        results["failed"] += 1
        results["details"].append({"name": name, "status": "ERROR", "error": str(e)})
        print(f"  ❌ {name}: {e}")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 1: Agent-Reach 真实Doctor检查
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n━━━ TEST 1: Agent-Reach 真实Doctor检查 ━━━")

def test_agent_reach_doctor():
    ar_path = str(EXTERNAL / "Agent-Reach")
    sys.path.insert(0, ar_path)
    try:
        from agent_reach.config import Config
        from agent_reach.doctor import check_all, format_report
        config = Config()
        report = check_all(config)
        print(f"    找到 {len(report)} 个渠道")
        ok_count = sum(1 for r in report.values() if r["status"] == "ok")
        print(f"    可用: {ok_count}/{len(report)}")
        # 至少应该有web和exa_search这些tier 0渠道
        assert len(report) >= 10, f"渠道数不足: {len(report)}"
        return True
    finally:
        sys.path.remove(ar_path)

test("Agent-Reach doctor.check_all()", test_agent_reach_doctor)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 2: Edict file_lock 原子读写
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n━━━ TEST 2: Edict file_lock 原子JSON读写 ━━━")

def test_edict_file_lock():
    edict_scripts = str(EXTERNAL / "edict" / "scripts")
    sys.path.insert(0, edict_scripts)
    try:
        from file_lock import atomic_json_read, atomic_json_update, atomic_json_write
        import tempfile, shutil

        # 创建临时测试目录
        tmpdir = Path(tempfile.mkdtemp())
        test_file = tmpdir / "neural_cluster_state.json"

        # 写入初始状态
        initial = {"organs": {}, "cycle": 0, "created": datetime.now().isoformat()}
        atomic_json_write(test_file, initial)
        
        # 读取验证
        data = atomic_json_read(test_file, default={})
        assert data["cycle"] == 0, f"cycle应为0，实际{data['cycle']}"
        print(f"    初始写入+读取: cycle={data['cycle']}")
        
        # 原子更新
        def increment(d):
            d["cycle"] += 1
            d["organs"]["llmfit"] = {"status": "active", "ts": time.time()}
            return d
        
        updated = atomic_json_update(test_file, increment, default={})
        assert updated["cycle"] == 1
        assert "llmfit" in updated["organs"]
        print(f"    原子更新: cycle={updated['cycle']}, organs={list(updated['organs'].keys())}")
        
        # 并发安全: 读取不应被锁住
        data2 = atomic_json_read(test_file, default={})
        assert data2["cycle"] == 1
        
        shutil.rmtree(tmpdir)
        return True
    finally:
        if edict_scripts in sys.path:
            sys.path.remove(edict_scripts)

test("Edict file_lock 原子读写+并发", test_edict_file_lock)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 3: Edict 朝堂议政官员Profile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n━━━ TEST 3: Edict 朝堂议政——官员Profile真实加载 ━━━")

def test_court_officials():
    court_path = str(EXTERNAL / "edict" / "dashboard")
    sys.path.insert(0, court_path)
    try:
        from court_discuss import OFFICIAL_PROFILES, FATE_EVENTS, create_session
        
        # 验证10个官员全部加载
        assert len(OFFICIAL_PROFILES) == 10, f"官员数应为10，实际{len(OFFICIAL_PROFILES)}"
        names = [f"{p['emoji']} {p['name']}({p['role']})" for p in OFFICIAL_PROFILES.values()]
        print(f"    加载 {len(OFFICIAL_PROFILES)} 个官员:")
        for n in names:
            print(f"      {n}")
        
        # 验证16个命运骰子事件
        assert len(FATE_EVENTS) == 16, f"命运事件应为16，实际{len(FATE_EVENTS)}"
        print(f"    加载 {len(FATE_EVENTS)} 个命运骰子事件")
        
        # 创建真实会话
        session = create_session(
            topic="如何将Agent-Reach联网能力接入真元神经网络集群",
            official_ids=["taizi", "gongbu", "hubu", "bingbu"]
        )
        assert "session_id" in session
        assert len(session["officials"]) == 4
        print(f"    创建议政会话: {session['session_id']}")
        print(f"    参与官员: {[o['name'] for o in session['officials']]}")
        
        return True
    finally:
        if court_path in sys.path:
            sys.path.remove(court_path)

test("Edict 朝堂议政官员Profile", test_court_officials)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 4: Edict TaskService 状态机模型
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n━━━ TEST 4: Edict TaskService 状态机逻辑 ━━━")

def test_task_state_machine():
    task_model_path = str(EXTERNAL / "edict" / "backend" / "app")
    sys.path.insert(0, task_model_path)
    try:
        from models.task import TaskState, STATE_TRANSITIONS, TERMINAL_STATES
        
        # 列出所有状态
        states = [s.value for s in TaskState]
        print(f"    状态数: {len(states)}")
        print(f"    状态: {states[:8]}...")
        
        # 验证状态机: 太子→中书→门下→尚书→六部...
        assert TaskState.Taizi in TaskState
        assert TaskState.Zhongshu in TaskState
        assert TaskState.Menxia in TaskState
        
        # 验证转移规则存在
        assert TaskState.Taizi in STATE_TRANSITIONS
        taizi_next = STATE_TRANSITIONS[TaskState.Taizi]
        print(f"    太子→可转: {[s.value for s in taizi_next]}")
        
        # 验证终止态
        print(f"    终止态: {[s.value for s in TERMINAL_STATES]}")
        
        return True
    finally:
        if task_model_path in sys.path:
            sys.path.remove(task_model_path)

test("Edict TaskService状态机", test_task_state_machine)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST 5: 未安装依赖的优雅降级——源码扫描
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print("\n━━━ TEST 5: 降级扫描——无依赖项目也能读取结构 ━━━")

def test_source_scan():
    """扫描所有外部项目的入口点和核心文件"""
    projects = ["llmfit", "gstack", "openfang", "symphony"]
    found = {}
    for proj in projects:
        proj_path = EXTERNAL / proj
        if not proj_path.exists():
            continue
        # 找入口文件
        entry = None
        for candidate in [
            "Cargo.toml", "package.json", "pyproject.toml",
            "README.md"
        ]:
            p = proj_path / candidate
            if p.exists():
                entry = candidate
                break
        if entry:
            content = (proj_path / entry).read_text(encoding="utf-8", errors="replace")[:200]
            found[proj] = entry
            print(f"    {proj}: 入口={entry}")
    
    assert len(found) >= 3, f"至少应找到3个项目入口, 实际{len(found)}"
    return True

test("源码扫描——读取项目入口", test_source_scan)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 汇总
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
print(f"\n{'='*60}")
print(f"Deep Bridge 结果: {results['passed']}/{results['passed']+results['failed']} 通过")
for d in results["details"]:
    icon = "✅" if d["status"] == "PASS" else "❌"
    print(f"  {icon} {d['name']}")
print(f"{'='*60}")

# 写回P516验证状态
state_path = Path("/mnt/c/Users/h/Desktop/零/真元集群/external_projects/.bridge_state.json")
atomic = {"deep_bridge_passed": results["passed"], "total": results["passed"]+results["failed"],
           "ts": datetime.now().isoformat(), "details": results["details"]}
state_path.write_text(json.dumps(atomic, ensure_ascii=False, indent=2))
print(f"\n状态已写入: {state_path}")
