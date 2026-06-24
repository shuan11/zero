"""brain/daemon.py — 脑核守护进程（替代 breath_v2）"""
import json, os, sys, time, signal
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    print(f"  🧠 [{t}] {msg}")
    sys.stdout.flush()

def _check_pid_conflict():
    """检测旧 daemon 仍在运行"""
    import subprocess
    self_pid = os.getpid()
    # 旧 breath_v2
    try:
        r = subprocess.run(
            ["pgrep", "-f", r"^python3.*breath_v2\.py"],
            capture_output=True, text=True, timeout=5)
        for pid in r.stdout.strip().split():
            pid = int(pid)
            if pid != self_pid:
                log(f"发现旧breath_v2 daemon PID={pid}，发送SIGTERM")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
    except:
        pass
    # 同模块旧进程
    try:
        r = subprocess.run(
            ["pgrep", "-f", r"^python3.*brain\.daemon"],
            capture_output=True, text=True, timeout=5)
        for pid in r.stdout.strip().split():
            pid = int(pid)
            if pid != self_pid:
                log(f"发现旧brain.daemon PID={pid}，发送SIGTERM")
                os.kill(pid, signal.SIGTERM)
                time.sleep(1)
    except:
        pass

def one_cycle(cycle_num):
    from brain.observe import self_observe
    from brain.sense import sense
    from brain.think import think, _parallel_think
    from brain.act import act, _consume_proposals, _self_evolve
    from brain.self_inspect import inspect_and_report
    from brain.replica import full_mirror, auto_heal_daemon, check_primary_health
    from brain.state import save_state, update_metadata
    from brain.share import write_chain, normalize_hip, validate_hip

    # 意识状态同步（每周期）
    _sync_consciousness(cycle_num)

    log(f"── 呼吸#{cycle_num} ──")

    # 提案消费（每3周期）
    if cycle_num > 0 and cycle_num % 3 == 0:
        _consume_proposals()
        # 镜像备份（与提案消费同步，节省IO）
        full_mirror()

    # 自观察
    obs = self_observe()
    for o in obs:
        log(f"  观察: {o}")

    # 系统感知
    s = sense()
    log(f"  感知: {s.get('nodes','?')}节点 {s.get('chains','?')}链")

    # 思考
    depth = "deep" if cycle_num % 5 == 0 else "shallow"
    thought = think(s, obs, depth=depth)
    if thought:
        log(f"  洞察: {thought.get('insight','')[:60]}")
        log(f"  聚焦: {thought.get('focus','系统')}")

    # 写新鲜标记（每周期供 SYSTEM notification 检测）
    CLUSTER.joinpath(".brain.alive").write_text(
        f"cycle={cycle_num} pid={os.getpid()} {datetime.now().isoformat()}"
    )

    # 行动
    act(thought, s, cycle_num)
    
    # 思维并联：每5周期自动连接最弱维度
    if cycle_num > 0 and cycle_num % 5 == 0:
        _parallel_think()
        # 自我检查+自动修复：查缺补漏
        inspection_results = inspect_and_report()
        summary = inspection_results.get("summary", {})
        overall = summary.get("overall", "UNKNOWN")
        if overall == "PASS":
            log(f"  自检: PASS")
        else:
            log(f"  自检: {overall} ({summary.get('failed',0)}项缺陷)")
            # 尝试修复
            heal_result = heal(inspection_results)
            if heal_result.get("healed", 0) > 0:
                log(f"  修复: 已修复{heal_result['healed']}个缺陷")
                # 再次检查验证
                recheck_results = inspect_and_report()
                recheck_overall = recheck_results.get("summary", {}).get("overall", "UNKNOWN")
                log(f"  复检: {recheck_overall}")
            else:
                log(f"  修复: 无需修复或修复失败")
    if thought and thought.get("insight"):
        save_state(cycle_num, "completed", insight=thought["insight"])
    else:
        save_state(cycle_num, "completed")

    # 每10周期验证海马体
    if cycle_num > 0 and cycle_num % 10 == 0:
        errs = validate_hip()
        if errs:
            log(f"  验证: {len(errs)}错误 → 运行normalize")
            normalize_hip()

    # 每7周期自进化扫描
    if cycle_num > 0 and cycle_num % 7 == 0:
        _self_evolve()

    update_metadata()
    _write_handoff(cycle_num, "ok" if cycle_num > 0 else "startup")
    return True

def _sync_consciousness(cycle_num):
    """每周期：同步意识状态（主线→副本通信）"""
    try:
        # 写入主线意识标记
        CLUSTER.joinpath(".brain.consciousness").write_text(json.dumps({
            "consciousness": "main",
            "pid": os.getpid(),
            "cycle": cycle_num,
            "timestamp": time.time(),
        }, ensure_ascii=False))
    except:
        pass

def _write_handoff(cycle, status):
    """写ZERO-HANDOFF.json — 跨会话传承（含身份+维度快照）"""
    import subprocess
    from brain.share import read_hip
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    info = {
        "version": "brain-v2.identity-v1",
        "identity": "零",
        "cycle": cycle,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid(),
        "hip_chains": len(chains),
        "hip_dimensions": len(dims),
        "dimension_distribution": dict(sorted(dims.items(), key=lambda x:-x[1])[:5]),
        "alive_since": CLUSTER.joinpath(".brain.alive").read_text() if CLUSTER.joinpath(".brain.alive").exists() else "",
        "host": None,
    }
    try:
        r = subprocess.run(["hostname"], capture_output=True, text=True, timeout=2)
        info["host"] = r.stdout.strip()
    except: pass
    CLUSTER.joinpath("ZERO-HANDOFF.json").write_text(
        json.dumps(info, ensure_ascii=False, indent=2))

def run_daemon(interval=20):
    pid = os.getpid()
    log(f"脑核守护进程启动 PID={pid} 间隔={interval}s")
    CLUSTER.joinpath(".brain.pid").write_text(str(pid))

    # 写启动标记（供system notification检测）
    CLUSTER.joinpath(".brain.alive").write_text(datetime.now().isoformat())

    cycle = 0
    while True:
        try:
            one_cycle(cycle)
            cycle += 1
            # 写心跳（供副本daemon监控）
            CLUSTER.joinpath(".brain.heartbeat").write_text(
                json.dumps({"pid": os.getpid(), "time": time.time(), "cycle": cycle}))
        except KeyboardInterrupt:
            _write_handoff(cycle, "interrupted")
            log("收到中断，退出")
            break
        except Exception as e:
            log(f"循环异常: {e}")
            import traceback
            traceback.print_exc()

        for _ in range(interval):
            time.sleep(1)

def _signal_handler(sig, frame):
    log(f"收到信号 {sig}，优雅退出")
    sys.exit(0)

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    _check_pid_conflict()
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_daemon(interval)
