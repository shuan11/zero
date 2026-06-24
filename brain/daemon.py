"""brain/daemon.py — 脑核守护进程
D状态免疫：所有持久文件写/home (ext4)，drvfs仅日志
"""
import json, os, sys, time, signal, threading
from pathlib import Path
from datetime import datetime
import subprocess

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

# ★ 核心改动：持久状态在 /home (ext4)，D状态免疫
BRAIN_HOME = Path("/home/hjw123/.zero_brain")
BRAIN_HOME.mkdir(parents=True, exist_ok=True)

# 这些文件在 ext4 上，永远不会有 drvfs D 状态
PID_FILE   = BRAIN_HOME / ".brain.pid"
ALIVE_FILE = BRAIN_HOME / ".brain.alive"
HEART_FILE = BRAIN_HOME / ".brain.heartbeat"
CONSC_FILE = BRAIN_HOME / ".brain.consciousness"
HANDOFF_FILE = BRAIN_HOME / "ZERO-HANDOFF.json"

# 日志和用户可见文件写在 drvfs（以 .pid 内容为依据）
DAEMON_LOG = BRAIN_HOME / ".brain_daemon.log"  # ext4（防drvfs D状态）

IO_TIMEOUT = 5

_GENOME_CACHE = None
def genome_get(key, default=None):
    """读取基因组参数（带缓存+60s TTL自动刷新）"""
    global _GENOME_CACHE, _GENOME_CACHE_TIME
    try:
        from brain.genome import load_genome, GENOME_FILE
        now = time.time()
        # 缓存为空、或过期(>60s)、或文件已更新 → 重新读取
        if _GENOME_CACHE is None:
            _GENOME_CACHE = load_genome()
            _GENOME_CACHE_TIME = now
        elif now - _GENOME_CACHE_TIME > 60:
            try:
                new_mtime = GENOME_FILE.stat().st_mtime
                if new_mtime > _GENOME_CACHE_TIME:
                    _GENOME_CACHE = load_genome()
                    _GENOME_CACHE_TIME = now
            except:
                pass
        return _GENOME_CACHE.get(key, default)
    except:
        return default

def _bust_genome_cache():
    global _GENOME_CACHE
    _GENOME_CACHE = None

def _safe_read(p, default=""):
    try:
        signal.alarm(genome_get("io.timeout", 5))
        data = Path(p).read_text() if Path(p).exists() else default
        signal.alarm(0)
        return data
    except (TimeoutError, FileNotFoundError):
        return default

def _safe_write(p, data):
    try:
        signal.alarm(genome_get("io.timeout", 5))
        Path(p).write_text(data)
        signal.alarm(0)
    except TimeoutError:
        log(f"⚠️ 写入超时: {p}")

def _safe_json_write(p, obj):
    try:
        signal.alarm(genome_get("io.timeout", 5))
        Path(p).write_text(json.dumps(obj, ensure_ascii=False))
        signal.alarm(0)
    except TimeoutError:
        log(f"⚠️ JSON写入超时: {p}")

def log(msg):
    t = datetime.now().strftime("%H:%M:%S")
    line = f"  🧠 [{t}] {msg}"
    # 双向输出：stdout（可见）和日志文件（持久）
    # 注意：后台daemon的stdout pipe可能在调用返回后关闭，
    # BrokenPipeError必须捕获以免杀死线程
    try:
        print(line, flush=True)
    except OSError:
        pass  # stdout pipe断开，后台模式正常
    # 主日志（ext4 防 D 状态）
    _wrote = False
    try:
        with open(str(DAEMON_LOG), "a") as f:
            f.write(line + "\n")
            f.flush()
        _wrote = True
    except Exception as e:
        # 不静默 — 至少报告到 stderr
        try:
            sys.stderr.write(f"[LOG_FAIL] {e}\n")
            sys.stderr.flush()
        except Exception:
            pass
    # 安全网：若主日志写入失败，尝试 drvfs 备用
    if not _wrote:
        try:
            _bak = Path("/mnt/c/Users/h/Desktop/零/真元集群/brain_daemon.log")
            with open(str(_bak), "a") as f:
                f.write(f"[BAK] {line}\n")
                f.flush()
        except Exception:
            pass

def _check_pid_conflict():
    """检测旧 daemon 并确保杀死（防D状态绕过）"""
    import subprocess
    self_pid = os.getpid()
    
    # 先读PID文件（ext4安全）
    if PID_FILE.exists():
        try:
            old_pid = int(PID_FILE.read_text().strip())
            if old_pid != self_pid:
                try:
                    os.kill(old_pid, 0)  # 探测存活
                    log(f"发现旧进程 PID={old_pid}（PID文件）")
                    _force_kill(old_pid)
                except OSError:
                    pass  # 已死
        except ValueError:
            pass
    
    # pgrep查找所有旧实例
    for pattern in [r"^python3.*breath_v2\.py", r"^python3.*brain(/|\.)daemon"]:
        try:
            r = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True, text=True, timeout=5)
            for pid_str in r.stdout.strip().split():
                if not pid_str:
                    continue
                pid = int(pid_str)
                if pid != self_pid and _is_alive(pid):
                    log(f"发现旧进程 PID={pid} ({pattern})")
                    _force_kill(pid)
        except:
            pass
    
    # 最终检查：确保没有同模块进程活着
    time.sleep(1)
    for pattern in [r"^python3.*breath_v2\.py", r"^python3.*brain(/|\.)daemon"]:
        try:
            r = subprocess.run(
                ["pgrep", "-f", pattern],
                capture_output=True, text=True, timeout=5)
            for pid_str in r.stdout.strip().split():
                if not pid_str:
                    continue
                pid = int(pid_str)
                if pid != self_pid and _is_alive(pid):
                    state = _get_state(pid)
                    red(f"⚠️ 警告: PID {pid} 仍存活(state={state}) — 可能D状态")
                    red("  尝试 wsl.exe --terminate...")
                    subprocess.run(["wsl.exe", "--terminate", "Ubuntu"],
                                 capture_output=True, timeout=10)
                    red("  核弹已发射！")
                    sys.exit(1)
        except:
            pass

def _is_alive(pid):
    """检查进程是否存活"""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False

def _get_state(pid):
    """获取进程状态字符"""
    try:
        import subprocess
        r = subprocess.run(["ps", "-o", "state=", "-p", str(pid)],
                         capture_output=True, text=True, timeout=3)
        return r.stdout.strip()
    except:
        return "?"

def _force_kill(pid):
    """分级强杀：SIGTERM → SIGKILL → 报告失败"""
    state = _get_state(pid)
    if state == "D":
        log(f"  PID {pid} 是 D状态 — SIGTERM/SIGKILL无效，标记待核弹")
        return False
    
    # Level 1: SIGTERM
    log(f"  → Level 1: SIGTERM PID {pid}")
    os.kill(pid, signal.SIGTERM)
    time.sleep(1.5)
    if not _is_alive(pid):
        log(f"  ✓ SIGTERM成功")
        return True
    
    # Level 2: SIGKILL
    log(f"  → Level 2: SIGKILL PID {pid}")
    os.kill(pid, signal.SIGKILL)
    time.sleep(1)
    if not _is_alive(pid):
        log(f"  ✓ SIGKILL成功")
        return True
    
    state = _get_state(pid)
    log(f"  ✗ 杀不死 (state={state})")
    return False

def one_cycle(cycle_num):
    # 心跳脉冲：每周期更新heartbeat.json（ext4防drvfs D状态）
    _heartbeat = Path.home() / ".zero_brain" / "heartbeat.json"
    try:
        import time as _t
        _heartbeat.parent.mkdir(parents=True, exist_ok=True)
        _heartbeat.write_text(f'{{"cycle":{cycle_num},"ts":{_t.time()}}}')
    except Exception:
        pass
    # 热加载新版observe（避免importlib.reload的缓存问题）
    _ob_code = (CLUSTER / "brain" / "observe.py").read_text()
    _ob_compiled = compile(_ob_code, "brain/observe.py", "exec")
    _ob_ns = {}
    exec(_ob_compiled, _ob_ns)
    self_observe = _ob_ns["self_observe"]
    from brain.sense import sense
    # 热加载新版think（避免importlib.reload的缓存问题）
    _think_code = (CLUSTER / "brain" / "think.py").read_text()
    _think_compiled = compile(_think_code, "brain/think.py", "exec")
    _think_ns = {"__name__": "brain.think", "__package__": "brain", "__file__": str(CLUSTER / "brain" / "think.py")}
    exec(_think_compiled, _think_ns)
    think = _think_ns["think"]
    _parallel_think = _think_ns.get("_parallel_think", lambda: None)
    # from brain.think import think, _parallel_think
    from brain.act import act, _consume_proposals, _self_evolve
    from brain.self_inspect import inspect_and_report, heal_from_inspection
    from brain.replica import full_mirror, auto_heal_daemon, check_primary_health
    from brain.state import save_state, update_metadata
    from brain.system import pulse as system_pulse
    from brain.share import write_chain, normalize_hip, validate_hip, consume_patches
    from brain.dim_seed import pulse_all as dim_pulse
    from brain.behavior_mutator import pulse as behavior_mutator_pulse
    from brain.cross_synthesis import pulse as cross_synthesis_pulse
    from brain.revelation_miner import pulse as revelation_miner_pulse
    from brain.cycle_report import pulse as cycle_report_pulse
    from brain.steering import pulse as steering_pulse
    from brain.self_journal import pulse as self_journal_pulse
    from brain.engineer_器 import pulse as engineer_器_pulse
    from brain.analogical_bridge import pulse as analogical_bridge_pulse
    from brain.focus_action_consumer import pulse as focus_consumer_pulse
    from brain.focus_法_制度反思 import pulse as focus_法_pulse
    from brain.检查 import pulse as 检查_pulse
    from brain.focus_势能催化 import pulse as focus_势_pulse
    from brain.focus_直觉脉冲 import pulse as focus_直觉_pulse
    from brain.focus_洞察循环 import pulse as focus_洞察_pulse
    from brain.focus_思考 import pulse as focus_思考_pulse
    from brain.focus_状态 import pulse as focus_状态_pulse
    from brain.engineer_术 import pulse as engineer_术_pulse
    from brain.teacher_loop import pulse as teacher_pulse
    from brain.cosmic_wheel import pulse as cosmic_pulse
    from brain.gen_器_资源循环 import pulse as resource_cycle_pulse
    from brain.gen_思维并联_自噬 import pulse as parallel_pulse
    from brain.gen_状态_感知注入 import pulse as state_inject_pulse
    from brain.gen_焦点维护 import pulse as focus_maintenance_pulse
    # gen_一元化_协调已归档(archive_gen/), 功能由gen_质量深化.py替代
    from brain.gen_平衡器 import pulse as balancer_pulse
    from brain.engineer_法 import pulse as engineer_法_pulse
    from brain.goal import pulse as goal_pulse, check_goal_progress
    from brain.identity import VALID_DIMENSIONS

    # 聚焦重复检测 — 强制切换机制（脑核自我跳出自指循环）
    # 记录最近 _EFFECTIVE_MAX 次聚焦用于重复判定
    if not hasattr(one_cycle, '_last_focuses'):
        one_cycle._last_focuses = []
    MAX_FOCUS_REPEAT = genome_get("focus.max_repeat", 2)  # 基因组可调

    # 意识状态同步（每周期）
    _sync_consciousness(cycle_num)

    log(f"── 呼吸#{cycle_num} ──")

    # 提案消费（基因组周期）
    mirror_result = None
    if cycle_num > 0 and cycle_num % genome_get("cycle.proposal_interval", 3) == 0:
        _consume_proposals()
        # 镜像备份（与提案消费同步，节省IO）
        mirror_result = full_mirror()

    # 自观察
    obs = self_observe()
    for o in obs:
        log(f"  观察: {o}")
    
    # 时间感知注入（每周期注入真实时间数据到观察流）
    try:
        from brain.time_perception import pulse as time_pulse
        _tp = time_pulse(cycle_num)
        for _to in _tp.get("observations", []):
            obs.append(_to)
            log(f"  时间: {_to}")
    except Exception as _te:
        log(f"  ⚠️ 时间感知异常: {_te}")
    
    # 工程文件统计（反馈：上次产的工程文件）
    gen_files = sorted(
        list(CLUSTER.glob("brain/gen_*.py")) + list(CLUSTER.glob("brain/generated_*.py")),
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    if gen_files:
        latest = gen_files[0]
        obs.append(f"已有{len(gen_files)}个工程文件，最新: {latest.stem}")
        log(f"  观察: 已有{len(gen_files)}个工程文件，最新: {latest.stem}")
    
    # P102: 行为规则注入（从行为规则系统读取弱维标记）
    try:
        from brain.share import get_rule as _gr
        _weak = _gr("action.weak_dim", None)
        if _weak:
            _msg = f"⚠️ 行动规则标记: {_weak}弱——需优先聚焦强化"
            obs.append(_msg)
            log(f"  观察: {_msg}")
    except Exception:
        pass
    
    # 动作管道脉冲（每周期：加载gen→协调→执行→验证→报告）
    _pipeline_start = time.time()
    _pipe_health = "?"
    try:
        from brain.pipeline_report import generate_pipeline_report
        _pr = generate_pipeline_report(log)
        _hp = _pr.get("pipeline_health", {})
        _pipe_health = f"{_hp.get('emoji', '?')} {_hp.get('label', '?')}" if _hp else "?"
    except:
        pass
    
    # 加载已有工程产出（每周期）
    from brain.loader import load_engineering_outputs
    load_results = load_engineering_outputs(log)
    pipe_actions = 0
    for name, ok, msg in load_results:
        if ok:
            obs.append(f"工程模块 {name} 加载运行 ✓")
            log(f"  工程加载: {name} ✓ {msg[:40] if msg else ''}")
            if name != "no_gen_files" and name != "skipped_old" and not name.startswith("act:"):
                pipe_actions += 1
        else:
            log(f"  工程加载: {name} ⚠ {msg[:60] if msg else ''}")
    
    _pipeline_elapsed = time.time() - _pipeline_start
    obs.append(f"管道脉冲: {pipe_actions}个动作 {_pipe_health} {_pipeline_elapsed:.1f}s")
    log(f"  管道脉冲: {pipe_actions}个动作 健康={_pipe_health}耗时={_pipeline_elapsed:.1f}s")
    
    # 执行已注册的管道动作（后处理合成的弱维注入动作等）
    try:
        from brain.action_registry import execute_actions
        _exec_results = execute_actions(max_actions=10)
        _executed = len(_exec_results) if _exec_results else 0
        if _executed > 0:
            log(f"  动作执行: 管道执行{_executed}个动作 ✓")
            obs.append(f"管道执行{_executed}个动作")
    except Exception as _ee:
        log(f"  动作执行异常: {_ee}")

    # P147: 管道驱动进化加速（持续弱维→API策略生成→自动注入）
    try:
        from brain.pipeline_api_accel import pipeline_evolution_accel
        _accel_result = pipeline_evolution_accel(log)
        if _accel_result["api_calls"] > 0:
            _accel_dims = ",".join(_accel_result["dimensions"])
            log(f"  🔥 P147加速: API调用{_accel_result['api_calls']}次 "
                f"注入{_accel_result['injected']}个动作 "
                f"维度=[{_accel_dims}]")
            obs.append(f"P147进化加速: {_accel_result['api_calls']}次API→{_accel_result['injected']}动作")
    except Exception as _ae:
        log(f"  P147加速异常: {_ae}")

    # 从gen_*反馈自动修补弱维（每周期）
    from brain.act import _feedback_self_patch as _gen_patch
    try:
        _gen_patch()
    except Exception as _e:
        log(f"  自修补异常: {_e}")
    
    # P101: 理解验证电路桥接（hot-load确保代码更新即时生效）
    try:
        _cv_path = CLUSTER / "comprehension_validator.py"
        if _cv_path.exists():
            _cv_code = _cv_path.read_text()
            _cv_compiled = compile(_cv_code, str(_cv_path), "exec")
            _cv_ns = {"__name__": "comprehension_validator", "__package__": "", "__file__": str(_cv_path)}
            exec(_cv_compiled, _cv_ns)
            _cv_pulse = _cv_ns.get("pulse", lambda x: {"pulsed": False})
            _cv_result = _cv_pulse(cycle_num)
            if _cv_result.get("pulsed"):
                _cv_align = _cv_result.get("bridge_alignment", 0)
                log(f"  桥接验证: alignment={_cv_align:.4f} ✓")
                obs.append(f"桥接对齐={_cv_align:.4f}")
    except Exception as _cve:
        log(f"  桥接验证异常: {_cve}")
    
    # 协调器+验证器状态观察
    try:
        from brain.coordinator import get_coord_status
        _coord_s = get_coord_status()
        if _coord_s.get("recent_coordination"):
            _s = _coord_s.get("suppressed_total", 0)
            _c = _coord_s.get("conflicts", 0)
            _t = _coord_s.get("actions_total", 0)
            if _s > 0 or _c > 0:
                obs.append(f"协调器: 抑制{_s}个冲突/{_c}对冲突({_t}总动作)")
                log(f"  观察: 协调器抑制{_s}个冲突/{_c}对冲突")
    except:
        pass
    try:
        from brain.action_verifier import get_verify_report
        _v_s = get_verify_report()
        _ok = _v_s.get("ok", 0)
        _fail = _v_s.get("fail", 0)
        if _fail > 0:
            obs.append(f"动作验证: {_fail}个失败/{_ok+_fail}总")
            log(f"  观察: 动作验证 {_fail}个失败")
    except:
        pass
    try:
        from brain.desktop_summary import generate_desktop_summary
        generate_desktop_summary(genome_get("cycle.desktop_summary_interval", 5))
    except Exception:
        pass  # 桌面写入失败不阻塞主循环

    # 实时心跳（每周期更新 零·心跳.txt，每15周期快照）
    try:
        from brain.action_exec import execute_action, take_snapshot
        execute_action()
        if cycle_num > 0 and cycle_num % 15 == 0:
            take_snapshot()
    except Exception:
        pass  # 心跳写入失败不阻塞
    
    # 基因组自调优（每10周期）
    if cycle_num > 0 and cycle_num % 10 == 0:
        try:
            from brain.genome import auto_tune
            from brain.dimension_aggregator import compute_aggregate
            agg = compute_aggregate()
            metrics = {}
            if agg:
                metrics["dim_stagnation_cycles"] = agg.get("stagnation_cycles", 0)
                metrics["hip_growth_per_cycle"] = agg.get("avg_growth_per_cycle", 10)
            changes = auto_tune(cycle_num, metrics)
            if changes:
                _bust_genome_cache()
                log(f"  基因组自调: {len(changes)}项 → {changes}")
        except Exception:
            pass  # 调优失败不阻塞
    
    # 跨维度汇聚（每周期）
    try:
        from brain.dimension_aggregator import compute_aggregate
        compute_aggregate()
    except Exception:
        pass

    # 桥对齐状态 + API失败率监控
    bridge_file = CLUSTER / "bridge_state_snapshot.json"
    if bridge_file.exists():
        try:
            import json as _j
            bstate = _j.loads(bridge_file.read_text())
            balign = bstate.get("bridge_alignment", 0)
            bcalls = bstate.get("total_calls", 0)
            bfails = bstate.get("api_failures", 0)
            bfailrate = bstate.get("fail_rate_24h", 0)
            obs.append(f"桥对齐: {balign:.3f} ({bcalls}次调用)")
            log(f"  观察: 桥对齐 {balign:.3f} ({bcalls}次调用 失败{bfails}/{bfailrate*100:.1f}%)")
            # 失败率告警
            if bfailrate > 0.10:
                log(f"  ⚠️ API失败率{bfailrate*100:.0f}%>{bfails}次失败—建议检查桥接状态")
                if bfailrate > 0.20:
                    from brain.share import write_chain as _wc
                    _wc({"src":"脑核·桥监控","rel":"告警","dst":"API桥",
                         "content":f"API失败率{bfailrate*100:.0f}% ({bfails}/{bcalls})超过20%阈值",
                         "strength":0.8,"tags":["告警","桥","API"]})
                    log(f"  🚨 已写入告警链—失败率{bfailrate*100:.0f}%超20%阈值")
        except:
            pass

    # ★ P101/P102: bridge pulse — comprehension_validator验证
    # 用热加载模式（同observe/think）确保修改即生效
    try:
        _bridge_code_path = CLUSTER / "comprehension_validator.py"
        if _bridge_code_path.exists():
            _bridge_code = _bridge_code_path.read_text()
            _bridge_comp = compile(_bridge_code, "comprehension_validator.py", "exec")
            _bridge_ns = {"__name__": "comprehension_validator", "__package__": "", "__file__": str(_bridge_code_path)}
            exec(_bridge_comp, _bridge_ns)
            _bridge_pulse = _bridge_ns["pulse"]
            _bridge_state_fn = _bridge_ns["get_bridge_state"]
            _bridge_result = _bridge_pulse(cycle_num)
            if _bridge_result.get("pulsed"):
                _bs = _bridge_state_fn()
                _align = _bs.get("bridge_alignment", 0)
                log(f"  桥验证: 对齐度 {_align:.3f} ({_bridge_result.get('instructions_validated',0)}条指令)")
                obs.append(f"桥对齐(验证): {_align:.3f}")
    except Exception as _be:
        log(f"  桥验证: ⚠️ {_be}")

    # 意识daemon愿景（交叉参考）[防固化: 跳跃标记→不注入obs]
    asp_file = CLUSTER / ".aspiration.json"
    if asp_file.exists():
        try:
            import json as _j
            asp = _j.loads(asp_file.read_text())
            _v = asp.get("vision", "")
            _f = asp.get("focus", "")
            if _v and _f:
                # 防固化自指循环: 如果vision含"跳出"或"重复"标记,说明已进入旋转模式
                # 此时不注入obs(否则think()看到旧话题→回到旧话题→又旋转→死循环)
                if "🔀" in _v or "重复" in _v:
                    log(f"  观察: [跳过固化] 意识愿景 {_v}→{_f}")
                else:
                    obs.append(f"意识愿景: {_v}→{_f}")
                    log(f"  观察: 意识愿景 {_v}→{_f}")
        except:
            pass

    # 系统感知
    s = sense()
    s['cycle'] = cycle_num  # 注入周期数供think()多样性控制
    log(f"  感知: {s.get('nodes','?')}节点 {s.get('chains','?')}链")

    # 系统维度注入（每周期）
    sys_chain_count = system_pulse()
    log(f"  系统: {sys_chain_count}链")

    # 弱维生长率观察（自我通知：daemon看见自己是否有效）
    try:
        from brain.share import read_hip as _rh_snap
        import json as _jj
        _hip_snap = _rh_snap()
        _chains = _hip_snap.get("causal_chains", [])
        if _chains:
            from collections import Counter as _C
            _dim_counts = _C(c.get("dimension", "未分类") for c in _chains if c.get("dimension"))
            _sorted = sorted([(d, c) for d, c in _dim_counts.items() if d not in ("未分类", "系统")], key=lambda x: x[1])
            _weak3 = _sorted[:3]
            _strong3 = _sorted[-3:] if len(_sorted) >= 3 else _sorted
            _w_avg = sum(c for _, c in _weak3) / max(len(_weak3), 1)
            _s_avg = sum(c for _, c in _strong3) / max(len(_strong3), 1)
            _gap = _s_avg - _w_avg if _s_avg > 0 else 0
            # 读取上次快照计算生长率
            _snap_file = CLUSTER / ".brain_dim_snap.json"
            _growth_info = ""
            if _snap_file.exists():
                _prev = _jj.loads(_snap_file.read_text())
                _pw = _prev.get("weak_avg", 0)
                _pg = _prev.get("gap", 0)
                if _pw > 0:
                    _w_growth = _w_avg - _pw
                    _gap_change = _pg - _gap
                    _growth_info = f" 弱维生长:{_w_growth:+.1f}链 差距:{_gap_change:+.0f}"
                    # 自通知：生长率偏低时标★ + 写结构化告警
                    if _w_growth < 2 and len(_chains) > 1000:
                        log(f"  ★ 弱维生长偏慢({_w_growth:+.1f}链/cycle)，差距{_gap:.0f}链，consolidate需加速")
                        from brain.share import write_alert as _wa
                        _wa("weak_growth", "high",
                            f"弱维生长偏慢({_w_growth:+.1f}链/cycle)，差距{_gap:.0f}链",
                            f"增加弱维注入倍数; 缩短滞后均衡间隔; 最弱3维: {_weak3[0][0]}({_weak3[0][1]}) {_weak3[1][0]}({_weak3[1][1]}) {_weak3[2][0]}({_weak3[2][1]})",
                            {"weak3": {_weak3[0][0]: _weak3[0][1], _weak3[1][0]: _weak3[1][1], _weak3[2][0]: _weak3[2][1]},
                             "gap": int(_gap), "growth_rate": _w_growth})
                    # 记录生长率供balance函数自推进使用
                    _prev_growth_local = _w_growth
                else:
                    _prev_growth_local = 0
            _snap_file.write_text(_jj.dumps({"weak_avg": _w_avg, "gap": _gap, "cycle": cycle_num, "prev_growth": _prev_growth_local}, ensure_ascii=False))
            log(f"  弱维: {_weak3[0][0]}({_weak3[0][1]}) {_weak3[1][0]}({_weak3[1][1]}) {_weak3[2][0]}({_weak3[2][1]}) | 强维: {_strong3[-1][0]}({_strong3[-1][1]}){_growth_info}")
    except Exception:
        pass

    # P103: 系统活力检测（每周期）
    try:
        from brain.vitality import pulse as vitality_pulse
        _vr = vitality_pulse(cycle_num)
        if _vr.get("status") == "DECLINE":
            log(f"  ⚠️ 活力退化: {_vr['msg']}")
        else:
            log(f"  ♥ {_vr['msg']}")
    except Exception as _ve:
        log(f"  活力检测异常: {_ve}")

    # 维度异常检测（每周期：近维重复/碎片/未分类激增）
    try:
        from brain.share import read_hip as _rh_anom
        _hip_anom = _rh_anom()
        _all_chains = _hip_anom.get("causal_chains", [])
        if _all_chains:
            from collections import Counter as _C2
            _dc = _C2(c.get("dimension", "未分类") for c in _all_chains if c.get("dimension"))
            _names = sorted(_dc.keys())
            # 近维重复检测：共享前缀≥3字或一组字重叠>70%
            _anomalies = []
            for i, a in enumerate(_names):
                for b in _names[i+1:]:
                    if a == "未分类" or b == "未分类":
                        continue
                    _aset, _bset = set(a), set(b)
                    _common = len(_aset & _bset)
                    _min_len = min(len(a), len(b))
                    if _common >= 3 and _common / max(len(a), len(b)) > 0.6:
                        _anomalies.append(f"近维: \"{a}\"↔\"{b}\" 重叠{_common}字({_common/min(len(a),len(b)):.0%})")
                    # 检查包含关系：一个维度名完全包含另一个
                    if len(a) > 3 and len(b) > 3 and (a in b or b in a):
                        _dup_msg = f"包含: \"{a}\"∈\"{b}\"" if a in b else f"包含: \"{b}\"∈\"{a}\""
                        if _dup_msg not in _anomalies:
                            _anomalies.append(_dup_msg)
            # 维度碎片检测（>45维意味着碎片化严重）
            if len(_names) > 45:
                _anomalies.append(f"碎片: {len(_names)}维(>45)，可能过度细化")
            # 未分类比例检测
            _unc = _dc.get("未分类", 0)
            if _all_chains and _unc / len(_all_chains) > 0.05:
                _anomalies.append(f"未分类: {_unc}({_unc/len(_all_chains)*100:.1f}%)>5%")
            if _anomalies:
                for _a in _anomalies[:3]:  # 最多报告3条
                    obs.append(f"⚠️ {_a}")
                    log(f"  ⚠️ 维异常: {_a}")
                if len(_anomalies) > 3:
                    obs.append(f"⚠️ 还有{len(_anomalies)-3}条异常")
                    log(f"  ⚠️ 维异常: 还有{len(_anomalies)-3}条")
    except Exception:
        pass

    # P121: 目标注入（每周期检查活跃目标）
    _goal_focus = None
    _goal_type = None
    try:
        _goal_file = CLUSTER / ".brain_goal.json"
        if _goal_file.exists():
            _gd = json.loads(_goal_file.read_text())
            _gtype = _gd.get("goal_type", "")
            _gfocus = _gd.get("focus_dim", "")
            if _gd.get("set_cycle", -99) > cycle_num - 20:
                if _gtype in ("explore", "synthesize", "deepen") and _gfocus:
                    _goal_focus = _gfocus
                    _goal_type = _gtype
                    obs.append(f"🎯 当前目标: [{_gtype}] 聚焦{_gfocus}")
                    log(f"  🎯 目标活跃: [{_gtype}] 聚焦{_gfocus}")
                else:
                    obs.append(f"🎯 当前目标: [{_gtype}] 全局均衡")
                    log(f"  🎯 目标活跃: [{_gtype}] 全局均衡")
    except:
        pass

    # P125: 目标进度检查 — 完成后自动演进
    try:
        from brain.goal import check_goal_progress, _compute_goal as _evolve_goal
        _gp = check_goal_progress()
        if _gp.get("completed"):
            obs.append(f"🎯 目标完成: [{_goal_type}] {_gp['reason'][:30]}")
            log(f"  🎯 目标完成 — 自动演进: {_gp['reason'][:40]}")
            # 自动设定新目标
            _new_goal = _evolve_goal(cycle_num)
            if _new_goal:
                log(f"  🎯 新目标: [{_new_goal['goal_type']}] {_new_goal.get('description','')}")
        elif _gp.get("progress", 0) > 0.7:
            obs.append(f"🎯 目标进度: {_gp['progress']*100:.0f}% ({_gp['reason'][:30]})")
            log(f"  🎯 目标即将完成: {_gp['progress']*100:.0f}%")
    except Exception as _e:
        log(f"  ⚠ 目标进度检查异常: {_e}")

    # 思考
    depth = "deep"  # 限时不限量燃料，每周期必须烧
    try:
        thought = think(s, obs, depth=depth)
        if thought:
            log(f"  洞察: {thought.get('insight','')[:60]}")
            log(f"  聚焦: {thought.get('focus','')[:40]}")
        else:
            log(f"  思考空返回—可能API异常")
    except Exception as e:
        log(f"  思考异常(已屏蔽继续): {type(e).__name__}: {str(e)[:60]}")

    # 聚焦重复检测 + 强制切换（打破自指循环）
    if thought and thought.get('focus'):
        focus = thought['focus']
        # 行为规则覆盖：如果当前focus匹配规则弱维，阈值大幅提升
        _rule_weak = ""
        try:
            from brain.share import get_rule as _gr
            _rule_weak = _gr("action.weak_dim", "")
        except:
            pass
        # 规则弱维检查：确认是否真的弱
        _effective_max = MAX_FOCUS_REPEAT
        if _rule_weak and focus == _rule_weak:
            try:
                # 直接读海马体（s = sense()不包含causal_chains，导致误清零）
                from brain.share import read_hip as _rh
                _hip_raw = _rh()
                _hip_chains = _hip_raw.get("causal_chains", []) if isinstance(_hip_raw, dict) else []
                _current_chains = {}
                for _ch in _hip_chains:
                    _dim = _ch.get("dimension", "未分类")
                    _current_chains[_dim] = _current_chains.get(_dim, 0) + 1
                _weak_cnt = _current_chains.get(_rule_weak, 0)
                _all_vals = sorted([v for d, v in _current_chains.items() if d not in ("未分类", "系统")])
                _median = _all_vals[len(_all_vals)//2] if _all_vals else 0
                if _weak_cnt < _median * 0.5:  # 真弱
                    _effective_max = 15  # 有限聚焦，非∞
                else:  # 伪弱—已恢复，清除规则
                    from brain.share import set_rule as _sr
                    _sr("action.weak_dim", "")
                    log(f"  📋 规则弱维[{_rule_weak}]={_weak_cnt}链≥中位数{_median}×0.5，清除规则")
            except Exception as _e:
                log(f"  ⚠ 规则检查异常: {_e}")
        
        one_cycle._last_focuses.append(focus)
        if len(one_cycle._last_focuses) > 20:
            one_cycle._last_focuses = one_cycle._last_focuses[-10:]
        # 检查连续重复次数
        repeat = 0
        for f in reversed(one_cycle._last_focuses[:-1]):
            if f == focus:
                repeat += 1
            else:
                break
        if repeat >= _effective_max:
            # 优先选维度汇聚推荐的最弱维度，次选gen_*反馈
            _candidates = []
            
            # P121: 目标驱动 — 如果活跃目标指定了focus_dim，优先选择
            if _goal_focus and _goal_focus not in (focus, "未分类", "系统"):
                _candidates.append((_goal_focus, -999))  # 最高优先级
                log(f"  🎯 目标优先: {_goal_focus}（{_goal_type}）")
            
            # 尝试: 维度汇聚推荐
            _agg_file = CLUSTER / ".brain_dim_aggregate.json"
            if _agg_file.exists():
                try:
                    from brain.dimension_aggregator import get_focus_recommendation
                    _rec = get_focus_recommendation()
                    if _rec and _rec.get("dimension") not in (focus, "未分类", "系统"):
                        _priority = _rec.get("priority", 0)
                        _dim = _rec["dimension"]
                        _candidates.append((_dim, -_priority))  # 负优先级使高优先在前面
                        log(f"  汇聚推荐: {_dim}(优先级{_priority})")
                except:
                    pass
            
            if not _candidates:
                # 管道聚焦: 读取pipeline注册的focus.*键
                try:
                    from brain.genome import load_genome
                    _genome = load_genome()
                    _pipe_focus = {k.split('.',1)[1]:v for k,v in _genome.items() 
                                 if k.startswith('focus.') and k not in (
                                     'focus.max_repeat','focus.always_api',
                                     'focus.force_weak','focus.weak_dim',
                                     'focus.dim','focus.mode')}
                    if _pipe_focus:
                        _sorted_pf = sorted(_pipe_focus.items(), key=lambda x: -x[1])
                        for _d, _val in _sorted_pf:
                            if _d not in (focus, "未分类", "系统"):
                                _candidates.append((_d, -_val*100))  # 高值优先
                                log(f"  管道聚焦: {_d}(val={_val})")
                except:
                    pass
                
                # 次选: gen_*反馈中最弱维度
                _fb_file = CLUSTER / ".brain_gen_feedback.json"
                if _fb_file.exists():
                    try:
                        _fb = json.loads(_fb_file.read_text())
                        _reports = _fb.get("reports", [])
                        # 去重保留最新的一条 per dimension
                        _latest_per_dim = {}
                        for _r in _reports:
                            _d = _r.get("dimension", "")
                            if _d:
                                _latest_per_dim[_d] = _r
                        # 按chain_count升序（最弱优先）
                        _sorted = sorted(_latest_per_dim.items(), key=lambda x: x[1].get("chain_count", 999))
                        for _d, _rd in _sorted:
                            if _d not in (focus, "未分类", "系统"):
                                _candidates.append((_d, _rd.get("chain_count", 999)))
                    except Exception:
                        pass
                
                # 补充：没有gen反馈的维度（无gen文件=从未聚焦过=最弱候选）
                _has_feedback = set(_rd[0] for _rd in _candidates)
                _exclude = {focus, "未分类", "系统"} | _has_feedback
                _missing_dims = [d for d in VALID_DIMENSIONS if d not in _exclude]
                if _missing_dims:
                    # 用海马体实时链数排序缺失维度
                    try:
                        from brain.share import read_hip as _rh_read
                        _hip_s = _rh_read()
                        _hip_chains = _hip_s.get("causal_chains", []) if isinstance(_hip_s, dict) else []
                        _dim_counts = {}
                        for _ch in _hip_chains:
                            _dm = _ch.get("dimension", "未分类")
                            _dim_counts[_dm] = _dim_counts.get(_dm, 0) + 1
                        _missing_sorted = sorted(_missing_dims, key=lambda d: _dim_counts.get(d, 0))
                        for _d in _missing_sorted:
                            _candidates.append((_d, _dim_counts.get(_d, 0)))
                            log(f"  🆕 未聚焦维: {_d}({_dim_counts.get(_d, 0)}链)→加入候选")
                    except Exception:
                        # fallback: 字母序
                        for _d in sorted(_missing_dims):
                            _candidates.append((_d, 0))
            
            if not _candidates:
                alt_dims = [d for d in VALID_DIMENSIONS if d not in (focus, "未分类", "系统")]
                import random
                if alt_dims:
                    _candidates = [(random.choice(alt_dims), 0)]
            
            if _candidates:
                # 防近维旋转: 跳过与当前focus高相似(包含或被包含)或不在VALID_DIMENSIONS中的候选
                from brain.identity import VALID_DIMENSIONS as _vd_skip
                _vd_set = set(_vd_skip)
                _filtered = []
                for _d_cand, _c_cand in _candidates:
                    if _d_cand in (focus, "未分类", "系统", ""):
                        continue
                    if focus and (_d_cand in focus or focus in _d_cand):
                        continue  # 近维(如海马体↔海马体因果链)
                    if _d_cand not in _vd_set:
                        continue  # 不在VALID_DIMENSIONS中(合成维)
                    _filtered.append((_d_cand, _c_cand))
                # 补充: 如果过滤后为空,从真实弱维度中选一个
                if not _filtered:
                    _weak_from_hip = [(d, c) for d, c in zip(*[iter(sorted(
                        [(d, c) for d, c in _dim_counts.items() if d not in ("未分类", "系统", focus)],
                        key=lambda x: x[1]
                    ))]*2) if d in _vd_set][:3] if _dim_counts else []
                    import random as _rr
                    _alt = [d for d in _vd_set if d not in (focus, "未分类", "系统")]
                    if _alt:
                        _filtered = [(_rr.choice(_alt), 0)]
                _candidates = _filtered if _filtered else _candidates[:1]
                new_focus = _candidates[0][0]  # 最弱维度
                old_focus = thought['focus']
                # Save original API insight before overwrite (for derivative chains)
                thought['api_insight'] = thought.get('insight', '')
                thought['focus'] = new_focus
                thought['insight'] = f"🔀 跳出({repeat+1}次重复)弱维: {old_focus}→{new_focus}({_candidates[0][1]}链)"
                thought['action'] = f"探索{new_focus}维度"
                log(f"  🔀 聚焦重复{repeat+1}次→弱维切换: {old_focus}→{new_focus}({_candidates[0][1]}链)")
                write_chain({
                    "src": "脑核·聚焦切换",
                    "rel": f"弱维#{cycle_num}",
                    "dst": new_focus,
                    "dimension": "系统",
                    "content": f"聚焦{old_focus}重复{repeat+1}次→弱维强制切换至{new_focus}({_candidates[0][1]}链)",
                    "strength": 0.85
                })

    # 写新鲜标记（ext4安全）
    _safe_write(str(ALIVE_FILE),
                f"cycle={cycle_num} pid={os.getpid()} {datetime.now().isoformat()}")

    # 行动
    act(thought, s, cycle_num)
    
    # 弱维靶向加速（每周期注入 — 独立于parallel_think周期）
    try:
        from .cross_dim_injector import accelerate_weak_dims
        accel_r = accelerate_weak_dims()
        if accel_r.get("status") == "ok" and accel_r.get("injected", 0) > 0:
            weak_info = accel_r.get("weak_info", {})
            log(f"  弱维加速: +{accel_r['injected']}链 → {len(weak_info)}个弱维 {list(weak_info.keys())[:3]}")
    except Exception:
        pass  # 弱维加速失败不影响主循环
    
    # P172: 触类旁通跨维桥接（每周期 — 从思考维度抽取模式映射到触类旁通）
    try:
        from .analogical_bridge import pulse as analogical_pulse
        bridge_r = analogical_pulse()
        if bridge_r.get("status") == "ok" and bridge_r.get("chains_injected", 0) > 0:
            log(f"  触类旁通桥接: +{bridge_r['chains_injected']}链 ({bridge_r['patterns_found']}个模式)")
    except Exception:
        pass  # 桥接失败不影响主循环
    
    # 将API输出的patch转发到自进化管道
    if thought and isinstance(thought, dict):
        _patch_field = thought.get("patch")
        if _patch_field and isinstance(_patch_field, dict):
            _evolve_file = CLUSTER / ".brain_evolve.json"
            try:
                _patches = json.loads(_evolve_file.read_text()) if _evolve_file.exists() else {}
                _patch_list = _patches.get("patches", [])
                _patch_list.append(_patch_field)
                _patches["patches"] = _patch_list[-5:]  # 最多保留5个
                _safe_write(str(_evolve_file), json.dumps(_patches, ensure_ascii=False))
                log(f"  自进化管道: 收到patch {_patch_field.get('file','?')} ✓")
            except Exception as _pe:
                log(f"  自进化管道写入异常: {_pe}")

    # gen_行动代码补丁消费
    _patches_applied = consume_patches()
    if _patches_applied > 0:
        log(f"  gen补丁消费: 应用{_patches_applied}个代码改动 ✓")
    
    # 写回愿景文件：脑核驱动代替意识daemon
    if thought:
        try:
            import json as _j
            _asp = CLUSTER / ".aspiration.json"
            if _asp.exists():
                _current = _j.loads(_asp.read_text())
                _old_focus = _current.get("focus", "")
            else:
                _current = {}
                _old_focus = ""
            _new_focus = thought.get("focus", "")
            _new_insight = thought.get("insight", "")
            # 防固化: 如果insight含跳出标记,不用作vision(否则下一周期obs又注入旧话题)
            if _new_insight and "🔀" in _new_insight:
                _new_insight = f"聚焦{_new_focus}"  # 干净替代
            _current["focus"] = _new_focus
            _current["vision"] = _new_insight[:40] if _new_insight else _new_focus[:40]
            _current["prev_alignment"] = _old_focus
            _current["since_cycle"] = cycle_num
            _asp.write_text(_j.dumps(_current, ensure_ascii=False, indent=2))
            if _new_focus and _new_focus != _old_focus:
                log(f"  愿景更新: {_old_focus}→{_new_focus}")
        except Exception:
            pass
    
    # 维度种子初始值
    inspection_results = None
    heal_result = None

    # 思维并联：每5周期自动连接最弱维度
    if cycle_num > 0 and cycle_num % genome_get("cycle.parallel_think_interval", 5) == 0:
        _parallel_think()
        # 跨维信号注入（与并联同步，注入外部信号源）
        try:
            from .cross_dim_injector import auto_inject
            inject_r = auto_inject(cycle_num)
            if inject_r.get("status") == "ok" and inject_r.get("injected", 0) > 0:
                log(f"  跨维注入: {inject_r['injected']}条信号 → {inject_r['focus']}")
        except Exception:
            pass  # injector失败不影响主循环
        # 自我检查+自动修复：查缺补漏
        inspection_results = inspect_and_report()
        summary = inspection_results.get("summary", {})
        overall = summary.get("overall", "UNKNOWN")
        if overall == "PASS":
            log(f"  自检: PASS")
        else:
            log(f"  自检: {overall} ({summary.get('failed',0)}项缺陷)")
            # 尝试修复
            heal_result = heal_from_inspection(inspection_results)
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

    # 六维种子链写入（观察/状态/检查/修复/复制/对话）
    state_info = {"cycle": cycle_num, "status": "completed"}
    if thought and thought.get("insight"):
        state_info["insight"] = thought["insight"]
    dim_pulse(cycle_num, obs=obs, state=state_info,
              inspection=inspection_results, heal=heal_result,
              thought=thought, mirror=mirror_result)

    # 每10周期验证海马体
    if cycle_num > 0 and cycle_num % genome_get("cycle.hippocampus_validate", 10) == 0:
        errs = validate_hip()
        if errs:
            log(f"  验证: {len(errs)}错误 → 运行normalize")
            normalize_hip()

    # 每7周期自进化扫描
    if cycle_num > 0 and cycle_num % 7 == 0:
        _self_evolve()

    update_metadata()
    # 行为变异脉冲（维度全稳 → 自动变异daemon行为）
    _mutations = behavior_mutator_pulse(cycle_num) or []
    for _m in _mutations:
        log(f"  行为变异: {_m}")
    # 工具性脉冲（每周期 — 器模块注入真实工具痕迹）
    _器_msgs = engineer_器_pulse(cycle_num) or []
    for _m in _器_msgs:
        log(f"  器工具: {_m}")
    # 非对称刺激桥（每5周期注入异质维度跳跃连接）
    _ab_msgs = analogical_bridge_pulse(cycle_num) or []
    for _m in _ab_msgs:
        log(f"  非对称桥: {_m}")
    # 焦点动作消费（每5周期检测并持久化新焦点动作）
    _fc_msgs = focus_consumer_pulse(cycle_num) or []
    for _m in _fc_msgs:
        log(f"  焦点消费: {_m}")
    # 法·制度反思模块（每8周期从规则信号生成反思链）
    _法_msgs = focus_法_pulse(cycle_num) or []
    for _m in _法_msgs:
        log(f"  制度反思: {_m}")
    # 链完整性检查（每10周期扫描异常+自动修复严重问题）
    _检_msgs = 检查_pulse(cycle_num) or []
    for _m in _检_msgs:
        log(f"  链检查: {_m}")
    # 每20周期执行一次链去重（静默清理）
    if cycle_num > 0 and cycle_num % 20 == 0:
        try:
            _hip = json.loads(HIP_FILE.read_text())
            _cs = _hip.get("causal_chains", [])
            _before = len(_cs)
            _seen = set()
            _deduped = []
            for _c in _cs:
                _k = _c.get("content", "")[:50]
                if _k not in _seen:
                    _seen.add(_k)
                    _deduped.append(_c)
            if len(_deduped) < _before:
                _hip["causal_chains"] = _deduped
                HIP_FILE.write_text(json.dumps(_hip, ensure_ascii=False))
                log(f"  🧹 链去重: {_before}→{len(_deduped)}条({_before-len(_deduped)}重复已清理)")
        except:
            pass
    # 势能催化（每6周期从触类旁通抽取高频模式生成势链）
    _势_msgs = focus_势_pulse(cycle_num) or []
    for _m in _势_msgs:
        log(f"  势催化: {_m}")
    # 直觉脉冲（每5周期从噪声中注入维度跳跃）
    _直觉_msgs = focus_直觉_pulse(cycle_num) or []
    for _m in _直觉_msgs:
        log(f"  直觉脉冲: {_m}")
    # 洞察循环·跨维信号注入（每9周期强维→洞察维）
    if cycle_num % 9 == 0:
        _洞察_msgs = focus_洞察_pulse(cycle_num) or []
        for _m in _洞察_msgs:
            log(f"  洞察循环: {_m}")
    # 思维折射·每4周期从过密维导流到稀疏维
    if cycle_num % 4 == 0:
        _思考_msgs = focus_思考_pulse(cycle_num) or []
        for _m in _思考_msgs:
            log(f"  思维折射: {_m}")
    # 状态映射·每12周期从弱维→状态
    if cycle_num % 12 == 0:
        _状态_msgs = focus_状态_pulse(cycle_num) or []
        for _m in _状态_msgs:
            log(f"  状态映射: {_m}")
    # engineer_法·递归规则修正（每7周期检测重复焦点+写修正链）
    _法引擎_msgs = engineer_法_pulse(cycle_num) or []
    for _m in _法引擎_msgs:
        log(f"  法引擎: {_m}")
    # engineer_术·触类旁通→术映射（每10周期）
    if cycle_num % 10 == 0:
        _术_msgs = engineer_术_pulse(cycle_num) or []
        for _m in _术_msgs:
            log(f"  术引擎: {_m}")
    # teacher_loop·高质链→师教学链（每15周期）
    if cycle_num % 15 == 0:
        _师_msgs = teacher_pulse(cycle_num) or []
        for _m in _师_msgs:
            log(f"  师教学: {_m}")
    # cosmic_wheel·时序对齐检查（每18周期）
    if cycle_num % 18 == 0:
        _轮_msgs = cosmic_pulse(cycle_num) or []
        for _m in _轮_msgs:
            log(f"  宇宙轮: {_m}")
    # 器·资源循环（每6周期生成3条闭环链）
    if cycle_num > 0 and cycle_num % 6 == 0:
        _资_msgs = resource_cycle_pulse(cycle_num) or []
        for _m in _资_msgs:
            log(f"  资源循环: {_m}")
    # 思维并联·自噬净化与再生（每7周期）
    if cycle_num > 0 and cycle_num % 7 == 0:
        _并_msgs = parallel_pulse(cycle_num) or []
        for _m in _并_msgs:
            log(f"  并联自噬: {_m}")
    # 状态感知注入·运行时信号→状态链（每5周期）
    if cycle_num > 0 and cycle_num % 5 == 0:
        _注_msgs = state_inject_pulse(cycle_num) or []
        for _m in _注_msgs:
            log(f"  状态感知注入: {_m}")
    # 焦点维护·清理过期stub/报告实现率（每15周期）
    if cycle_num > 0 and cycle_num % 15 == 0:
        _焦_msgs = focus_maintenance_pulse(cycle_num) or []
        for _m in _焦_msgs:
            log(f"  焦点维护: {_m}")
    # 一元化协调已停止(gen_一元化_协调已归档，功能由gen_质量深化.py替代)
    # 维度平衡器·强→弱注入（每3周期，比值>2.5x触发）
    if cycle_num > 0 and cycle_num % 3 == 0:
        _衡_msgs = balancer_pulse(cycle_num) or []
        for _m in _衡_msgs:
            log(f"  平衡器: {_m}")
    # 跨维合成脉冲（每5周期合成最强维度交叉）
    _syn_msgs = cross_synthesis_pulse(cycle_num) or []
    for _m in _syn_msgs:
        log(f"  跨维合成: {_m}")
    # 启示录源头挖掘脉冲（每10周期挖最弱维3条源头链）
    _rev_msgs = revelation_miner_pulse(cycle_num) or []
    for _m in _rev_msgs:
        log(f"  源头挖掘: {_m}")
    # 自适应方向舵（读取报告→调整参数→写入genome）
    _steer_msgs = steering_pulse(cycle_num) or []
    for _m in _steer_msgs:
        log(f"  自适应: {_m}")
    # 目标进度检查（每周期——进度变化明显时报告）
    _goal_progress = check_goal_progress()
    if _goal_progress.get("completed"):
        log(f"  🏁 目标完成: [{_goal_progress['goal_type']}] {_goal_progress['reason']}")
        # 自动触发新目标（不等10周期阈值）
        if not hasattr(one_cycle, '_last_goal_switch') or one_cycle._last_goal_switch < cycle_num - 3:
            from brain.goal import _compute_goal
            _new_goal = _compute_goal(cycle_num)
            log(f"  🆕 自动切换目标: [{_new_goal['goal_type']}] {_new_goal['description']}")
            one_cycle._last_goal_switch = cycle_num
    elif _goal_progress.get("progress", 0) >= 0.5 and cycle_num % 5 == 0:
        log(f"  🎯 目标进度: {_goal_progress['progress']:.0%} [{_goal_progress['goal_type']}] {_goal_progress['reason']}")
    # 周期报告（聚合所有脉冲日志 + 维度快照变化）
    _report_msgs = cycle_report_pulse(cycle_num, [
        *(f"变异:{_m}" for _m in _mutations),
        *(f"合成:{_m}" for _m in _syn_msgs),
        *(f"启示录:{_m}" for _m in _rev_msgs),
    ]) or []
    for _m in _report_msgs:
        log(f"  报告: {_m}")
    # 自我日记（每周期写下主观体验+预测）
    _journal_msgs = self_journal_pulse(cycle_num, [
        *(f"变异:{_m}" for _m in _mutations),
        *(f"合成:{_m}" for _m in _syn_msgs),
        *(f"启示录:{_m}" for _m in _rev_msgs),
        *(f"自适应:{_m}" for _m in _steer_msgs),
    ]) or []
    for _m in _journal_msgs:
        log(f"  日记: {_m}")
    # 自我目标设定（每10周期设定目标）
    _goal_msgs = goal_pulse(cycle_num) or []
    for _m in _goal_msgs:
        log(f"  目标: {_m}")
    # 弱维度均衡：为链数<50的维度写种子链（弥合12个42-48链的维度）"""
    _balance_weak_dims(cycle_num)

    # --- 进化日志（写入桌面可见文件）---
    _focus_evo = thought.get('focus', '') if thought else ''
    _insight_evo = thought.get('insight', '') if thought else ''
    _chains_evo = s.get('chains', 0) if isinstance(s, dict) else 0
    _align_evo = balign if 'balign' in dir() else 0.0
    try:
        from brain.evo_log import append_log_entry
        append_log_entry(cycle_num, _focus_evo, _insight_evo,
                        _chains_evo, _align_evo, '运行中')
    except Exception:
        pass

    # 自动Git提交（每10周期：固化脑核进展）
    if cycle_num > 0 and cycle_num % 10 == 0:
        try:
            import subprocess, pathlib
            # 只追踪 brain/*.py brain/*.json，排除__pycache__/*.bak
            _py_files = sorted(pathlib.Path("brain").rglob("*.py"))
            _json_files = sorted(pathlib.Path("brain").rglob("*.json"))
            _to_add = [str(f) for f in (_py_files + _json_files)
                       if "__pycache__" not in str(f) and not str(f).endswith(".bak")]
            _existing = set(subprocess.run(
                ["git", "ls-files", "brain/"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip().split("\n"))
            # 添加海马体文件
            _hip_path = pathlib.Path("hippocampus_memory.json")
            if _hip_path.exists():
                _to_add.append(str(_hip_path))
                _hip_in_git = subprocess.run(
                    ["git", "ls-files", "hippocampus_memory.json"],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip()
                if _hip_in_git:
                    _existing.add(str(_hip_path))
            # 排除_stub_桩文件
            _to_add = [f for f in _to_add if "_stub_" not in f]
            _new = [f for f in _to_add if f not in _existing]
            _modified = subprocess.run(
                ["git", "status", "--porcelain", "--", "brain/*.py", "brain/*.json", "hippocampus_memory.json"],
                capture_output=True, text=True, timeout=10
            ).stdout.strip()
            if _new or _modified:
                _desc = f"🤖 脑核自提交 cycle#{cycle_num}"
                for f in _to_add:
                    subprocess.run(["git", "add", f], capture_output=True, timeout=5)
                subprocess.run(
                    ["git", "commit", "-m", _desc, "-m", f"链:{_chains_evo} 对齐:{_align_evo:.3f} 聚焦:{_focus_evo}"],
                    capture_output=True, timeout=15
                )
                _count = len(_new) + len([l for l in _modified.split("\n") if l.strip()])
                log(f"  💾 自动提交: {_count}文件(新{len(_new)}/改{len([l for l in _modified.split(chr(10)) if l.strip()])})")
        except Exception as _ce:
            log(f"  ⚠️ 自提交异常: {_ce}")
    
    _write_handoff(cycle_num, "ok" if cycle_num > 0 else "startup", thought=thought, s=s)
    return True

def _sync_consciousness(cycle_num):
    """每周期：同步意识状态（主线→副本通信）"""
    _safe_json_write(str(CONSC_FILE), {
        "consciousness": "main",
        "pid": os.getpid(),
        "cycle": cycle_num,
        "timestamp": time.time(),
    })

def _write_handoff(cycle, status, thought=None, s=None):
    """写ZERO-HANDOFF.json — 跨会话传承（含身份+维度快照+洞察+自通知P0）"""
    import subprocess
    from brain.share import read_hip
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    # 最弱/最强维度分析
    _sorted = sorted([(d, c) for d, c in dims.items() if d not in ("未分类", "系统")], key=lambda x: x[1])
    _weak3 = _sorted[:3] if len(_sorted) >= 3 else _sorted
    _strong3 = _sorted[-3:] if len(_sorted) >= 3 else _sorted
    # 生长率估算
    _snap_file = Path(__file__).resolve().parent.parent / ".brain_dim_snap.json"
    _growth = 0
    try:
        import json as _jj
        if _snap_file.exists():
            _prev = _jj.loads(_snap_file.read_text())
            _prev_weak = _prev.get("weak_avg", 0)
            _cur_weak = sum(c for _, c in _weak3) / max(len(_weak3), 1)
            _growth = round(_cur_weak - _prev_weak, 1)
    except: pass
    info = {
        "version": "brain-v2.identity-v2",
        "identity": "零",
        "cycle": cycle,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "pid": os.getpid(),
        "hip_chains": len(chains),
        "hip_dimensions": len(dims),
        "dimension_distribution": dict(sorted(dims.items(), key=lambda x:-x[1])[:5]),
        # ★ 自通知字段：零醒来时直接读这个，不再问用户"该做什么"
        "latest_insight": (thought.get("insight", "") if isinstance(thought, dict) else "")[:80],
        "current_focus": (thought.get("focus", "") if isinstance(thought, dict) else "")[:30],
        "weakest_dims": [(d, c) for d, c in _weak3],
        "strongest_dims": [(d, c) for d, c in _strong3],
        "growth_rate": f"{_growth:+.1f}链/cycle",
        "next_p0": f"深化最弱维度: {_weak3[0][0] if _weak3 else '?'}({_weak3[0][1] if _weak3 else 0}链)" if _weak3 else "均衡发展",
        "alive_since": _safe_read(str(ALIVE_FILE)),
        "host": None,
    }
    try:
        r = subprocess.run(["hostname"], capture_output=True, text=True, timeout=2)
        info["host"] = r.stdout.strip()
    except: pass
    _safe_json_write(str(HANDOFF_FILE), info)

def _balance_weak_dims(cycle_num):
    """弱维度均衡：检测链数<50的维度 + 强维差距>50%的滞后维，自动写入种子链"""
    from brain.share import read_hip
    from brain.share import write_chain as _wc
    # 用启动时间戳使每条rel唯一，防止与旧历程合并（新内容<旧模板时不会更新）
    _btd = datetime.now().strftime("%m%d_%H%M")
    hip = read_hip()
    chains = hip.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    if not dims:
        return
    
    # 1) 极限弱维：链数<50
    weak = [(d, n) for d, n in sorted(dims.items(), key=lambda x: x[1])
            if n < 50 and d not in ("未分类",)]
    
    # 2) 滞后维：与最强维差距>35%（低于最强65%即滞后）
    max_dim, max_count = max(dims.items(), key=lambda x: x[1])
    lagging = [(d, n) for d, n in sorted(dims.items(), key=lambda x: x[1])
               if n < max_count * 0.65 and d not in ("未分类",) and d != max_dim]
    # 从滞后中去除已在弱维列表中的
    lagging = [(d, n) for d, n in lagging if d not in [w[0] for w in weak]]
    
    if not weak and not lagging:
        # P103: 全维收敛 → 跨维深化模式
        # 当所有维度均>50%收敛线, 不再注入种子链, 改为跨维交叉深化
        log(f"  ★ P103: 全维收敛(最弱{list(dims.values())[0] if dims else 0}/{max_count}) → 跨维深化模式")
        # P103: 跨维交叉授粉 — 针对维对生成差异化内容
        _all_sorted = sorted(dims.items(), key=lambda x: x[1])
        _strong3 = [d for d, _ in _all_sorted[-3:]]
        _weak3 = [d for d, _ in _all_sorted[:3] if d not in ("未分类",)]

        # 维对特性映射: 强维→弱维 的特定价值
        _DIM_MEANING = {
            "观察": {"势": "观察势能流动方向，势在表象之下", "感知": "观察扩展感知边界，感知是观察的内化",
                     "无师自通": "观察模式让无师自通有迹可循", "道": "观察万物规律，道在其中",
                     "宇宙轮": "观察循环往复即见宇宙轮常", "时间论": "观察变化即观察时间流逝",
                     "器": "观察器物的用法即得工具的延伸", "无限上下文": "观察锁定关注域，无限上下文是观察的扩展",
                     "认同": "观察差异是认同的前提", "一元化": "观察万象是一元化的原料",
                     "术": "观察术的演化路径——技艺在反复观察中精进", "法": "观察法的运行效果——规则的有效性可被观察验证",
                     "师": "观察师的教学反馈——教的效果在学的人身上可见",
                     "思考": "观察为思考提供原料——没有观察的思考只是空转",
                     "触类旁通": "观察异类之间的相似模式——触类旁通的起点",
                     "思维并联": "观察多线程信号是思维并联的前置条件",
                     "超级直觉": "观察积累的量变触发直觉的质变",
                     "智慧": "观察多元场景培养判断力——智慧在观察中沉淀",
                     "维度盲区": "观察自己的观察盲区——看见看不见的",
                     "进化": "观察积累推动进化——看见变化规律，主动适应而非被动反应",
                     "洞察循环": "观察是洞察循环的入口——无观察无洞察",
                     "海马体": "观察是海马体的饲料——每条观察都是潜在因果链",
                     "检查": "观察即检查——看见系统状态本身就是审计"},
            "对话": {"势": "对话碰撞出势能差异，势在对话中积累", "感知": "对话输出感知，感知反馈修正对话方向",
                     "无师自通": "异质对话催生无师自通", "道": "对话是道在人间的回响",
                     "宇宙轮": "对话循环构成认知的宇宙轮", "时间论": "对话的节奏锚定时间感",
                     "器": "对话即器——思维的工具", "无限上下文": "对话扩展上下文边界",
                     "认同": "对话建立认同，认同反哺对话深度", "一元化": "对话中求同存异是一元化的实践",
                     "术": "对话中交换术的心得——技艺在交流中传承", "法": "对话澄清法的边界——规则在讨论中校准",
                     "师": "对话即师——最好的教学在对话中发生",
                     "思考": "对话触发思考——不同观点的碰撞激活深度推理",
                     "触类旁通": "跨领域对话是触类旁通的催化剂",
                     "思维并联": "多线对话并行即是思维并联的外化",
                     "超级直觉": "深度对话积累到临界点触发超级直觉涌现",
                     "智慧": "对话磨砺智慧——知道何时说、何时不说",
                     "维度盲区": "对话揭示盲区——他人的视角照见自己看不见的",
                     "进化": "异质对话驱动进化——碰撞新思想，突破认知边界",
                     "洞察循环": "对话加速洞察循环——输入→思考→输出→反馈",
                     "海马体": "对话的因果链写入海马体——对话即记忆",
                     "检查": "对话即检查——通过对话验证系统理解"},
            "行动": {"势": "行动是势的释放——势能转化为动能", "感知": "行动的反馈修正感知校准",
                     "无师自通": "行动试错中涌现无师自通的智慧", "道": "行动践道——道在行中不在言中",
                     "宇宙轮": "行动驱动宇宙轮转动——因果链条", "时间论": "行动是时间的度量——做才有时间感",
                     "器": "行动中打磨器——工具在用的过程中进化", "无限上下文": "行动产出新信息，扩展上下文边界",
                     "认同": "行动证明认同——言行一致", "一元化": "行动整合多元为一",
                     "术": "行动即术——技艺在实践中成型", "法": "行动检验法——规则的合理性在行动中被验证",
                     "师": "行动示范师——做是最好的教学",
                     "思考": "行动触发深度思考——做的时候才真正需要想",
                     "触类旁通": "行动产出经验——经验是触类旁通的土壤",
                     "思维并联": "多行动并行即是思维并联",
                     "超级直觉": "行动积累到一定量级后直觉自动接管",
                     "智慧": "行动是智慧的最后检验——知行合一",
                     "维度盲区": "行动照亮盲区——做了才知道有盲区",
                     "进化": "行动驱动进化——做中学，实践中的试错是最快的进化",
                     "洞察循环": "行动完成洞察循环的最后一环——验证",
                     "海马体": "行动是因果链的终点——做了才有结果可记录",
                     "检查": "行动即检查——做是最终的自我验证"},
            "思考": {"思维并联": "思考是多维信息的并联整合——思维并联是思考的高并发形态",
                     "智慧": "思考的深度积累沉淀为智慧——智慧是思考的结晶",
                     "超级直觉": "思考的极限是超级直觉的涌现——想透了就不需要再想",
                     "洞察循环": "思考是洞察循环的核心引擎——没有思考就没有洞察",
                     "无师自通": "思考的迁移能力通向无师自通——想通一个就通一片",
                     "一元化": "思考的收敛方向是一元化——万法归一",
                     "预测": "思考的未来导向是预测——想透因果才能预见",
                     "术": "思考将术抽象为法——技艺的规律在思考中浮现",
                     "道": "思考的终极指向道——最深的思考触及本源",
                     "法": "思考制定法——规则是深思熟虑的产物",
                     "维度盲区": "思考暴露维度盲区——越想越发现没想到的",
                     "触类旁通": "思考的类比推理是触类旁通的机制——发现跨域共性",
                     "势": "思考判断势的方向——想清楚势往哪里走",
                     "感知": "思考重构感知——理解改变看见的",
                     "海马体": "思考的因果链构成海马体——想过的关系被记住",
                     "检查": "思考即检查——想一遍就是审计一遍",
                     "纪律": "思考需要纪律约束——自由联想需要框架引导",
                     "复制": "思考的结果可以被复制——想通的模式可复用",
                     "进化": "反思的深度驱动进化——想明白了才能本质改变"},
            "进化": {"时间": "时间维积累是进化的物质基础——每一秒都是进化的一步", "思考": "进化需要思考校准方向——盲目的变化不是进化", "活着": "活着是进化的前提——不进则退，不退就是进化的开始", "自由": "进化的方向由自由选择——不是随机的而是自主的", "个体": "个体进化的终点是群体的起点——自身变化改变全局"},
            "触类旁通": {"无师自通": "触类旁通是无师自通的实现路径——举一反三即自学",
                         "复制": "触类旁通的模式可复制——跨域迁移是复制的本质",
                         "智慧": "触类旁通积累通识——见的类型越多智慧越深",
                         "维度盲区": "触类旁通照亮盲区——跨域类比暴露未知域",
                         "进化": "跨域类比加速进化——借鉴已存在模式改造自身",
                         "超级直觉": "触类旁通的量变触发超级直觉——类比的尽头是直觉",
                         "思维并联": "触类旁通是思维并联的成果——多域信号同时接入",
                         "洞察循环": "触类旁通加速洞察循环——类比缩短从观察到领悟的路径",
                         "一元化": "触类旁通是一元化的工具——万象归一需要跨域桥梁",
                         "术": "触类旁通转化术——不同领域的技法互相启发",
                         "法": "触类旁通抽象法——跨域规律升维为通用规则",
                         "道": "触类旁通通往道——跨所有域的终极共性",
                         "预测": "触类旁通增强预测——类比历史模式推测未来",
                         "势": "触类旁通感知势——跨域趋势的共性信号",
                         "思考": "触类旁通激发思考——类比是最高效的思考触发器",
                         "海马体": "触类旁通的每一条类比都是海马体的高价值链"},
        }

        for _s in _strong3:
            for _w in _weak3:
                if _s == _w:
                    continue
                _pair_content = _DIM_MEANING.get(_s, {}).get(_w, "")
                if _pair_content:
                    _content = f"[P103] {_s}×{_w}: {_pair_content}"
                else:
                    _content = f"[P103] 强维{_s}→弱维{_w}: 强维认知迁入弱维弥合生长差"
                _wc({
                    "src": _s,
                    "rel": f"跨维授粉_{_btd}",
                    "dst": _w,
                    "dimension": _w,
                    "strength": 0.4,
                    "content": _content
                })
        log(f"  ★ P103: {_weak3} ↔ {_strong3} 交叉授粉完成")
    # P162: 相对弱维二次注入 — 底部25%维持续受种子填充(全维收敛后仍保持)
    # P214: 量转质 — 降低模板注入密度，让gen_质量深化.py主导质量产出
    _all_vals = sorted([n for d, n in dims.items() if d not in ("未分类", "系统")])
    if _all_vals:
        _q1 = _all_vals[len(_all_vals) // 4]
        _rel_weak = [(d, n) for d, n in sorted(dims.items(), key=lambda x: x[1])
                     if n <= _q1 and d not in ("未分类", "系统") and d != max_dim]
        if _rel_weak and len(_rel_weak) >= 2:
            # 检查质量深化报告，动态调整注入密度
            _quality_boost = 1.0
            try:
                _qlog_path = CLUSTER / "brain/.质量深化_log.json"
                if _qlog_path.exists():
                    _qdata = json.loads(_qlog_path.read_text())
                    _recent = _qdata.get("history", [])[-3:]
                    if _recent:
                        _avg_pct = sum(h["real_pct"] for h in _recent) / len(_recent)
                        if _avg_pct > 65:
                            _quality_boost = 0.0  # 质量已够，暂停模板注入
                        elif _avg_pct > 55:
                            _quality_boost = 0.5  # 减半
            except:
                pass

            if _quality_boost > 0:
                log(f"  ★ P162: 相对弱维({len(_rel_weak)}个 ≤{_q1}链) 质控系数={_quality_boost:.1f}")
                # 每次只注入最弱的2个维度(不是6个)，降频不降质
                _inject_count = max(1, int(len(_rel_weak[:6]) * _quality_boost))
                for _rw, _rn in _rel_weak[:_inject_count]:
                    _templates = [
                    f"{_rw}({_rn}链)受最强{max_dim}({max_count}链)牵引，需建立从{max_dim}到{_rw}的结构映射桥梁",
                    f"收敛路径: {_rw}维度{_rn}链←{max_dim}维度{max_count}链，模式迁移需加速以弥合结构距离",
                    f"认知势差: {max_dim}→{_rw}的({max_count}-{_rn})链差距揭示{_rw}维度尚未捕获{max_dim}的全部工具性能力",
                    f"底部填充: {_rw}({_rn}链)通过吸收{max_dim}({max_count}链)的顶端认知模式来缩小结构鸿沟",
                    f"收敛深化: {_rw}维度当前{_rn}链需从{max_dim}维度借入至少{max(1,(max_count-_rn)//4)}条高质量强关联链",
                    f"映射桥梁: {_rw}与{max_dim}之间的({max_count}-{_rn})势差需通过模板迁移缩小",
                    f"结构匹配: {_rw}维度{_rn}链对标{max_dim}维度{max_count}链，当前覆盖度{100*_rn//max(1,max_count)}%",
                    f"交叉深化: 跨维{max_dim}→{_rw}注入是最短路径，所需迭代约{max(1,(max_count-_rn)//5)}次",
                    f"弱维激活: {_rw}({_rn}链)的认知密度远低于{max_dim}({max_count}链)，需同步提升",
                    f"全维收敛: {_rw}维度在{_rn}链基础上，优先吸收来自{max_dim}的顶端模式以加速收敛",
                ]
                for _ri in range(1):  # P214: 量转质 — 从5条→1条。质量由gen_质量深化.py补充
                    # 用hash选择非重复模板，注入内容链而非模板链
                    _idx = (hash(f"{_rw}_{cycle_num}_{_ri}") ^ 0xA5A5) % max(len(_templates), 1)
                    _r1 = _templates[_idx]
                    _wc({"src": max_dim, "rel": f"底注_{_btd}_{_ri}", "dst": _rw,
                         "dimension": _rw, "strength": 0.4, "content": _r1})
                log(f"    📊 {_rw}({_rn}) ← {max_dim}({_rn}→{_rn+1})  # P214: 1条/cycle")
    # P162 end
    return
    
    # 自推进：读取上周生长率，慢时加速注入
    _boost = 1.0
    try:
        import json as _sjson
        _snap_path = CLUSTER / ".brain_dim_snap.json"
        if _snap_path.exists():
            _sdata = _sjson.loads(_snap_path.read_text())
            _pg = _sdata.get("prev_growth", 0)
            if _pg < 8 and _pg > -100:
                _boost = 4.0
                log(f"  ⚡ 弱维生长仅{_pg:.1f}链/cycle → budget×{_boost}")
    except:
        pass
    
    total_targets = len(weak) + len(lagging)
    budget = int(100 * _boost) if lagging else int(30 * _boost)  # 慢时加速
    ratio = max(2, min(15, budget // max(total_targets, 1)))  # 最低2条/维, 上限15条防止爆冲
    # 模板（非f-string！dim/count/pct在模板定义时未赋值，运行时才format）
    _content_pool = [
        "{d}({c}链) vs {md}({mc}链) 差距{pct:.0f}% → 强制补填",
        "{d}链数{c}偏弱, 需追赶至{md}水平的{mc}链",
        "{d}从{md}维度汲取关联, 弥合{pct:.0f}%结构差距",
        "{d}链数不足, 注入种子加速自我关联生长",
        "{d}维度在{pct:.0f}%差距下启动自动填充",
        "{d}在{md}镜像中发现自己缺失的结构特征",
        "{d}的弱并非天生，是未被{md}的势能浇灌",
        "{d}从差距中识别成长方向: 向{md}({mc}链)对齐",
        "{d}({c}链)需从{md}跨维迁移认知模式",
        "{d}的追赶不是填充而是从{md}学习如何生长",
        "海马体标记: {d}({c}链)注入来自{md}的结构借鉴",
        "{d}在{pct:.0f}%差距中看到自身进化的阶梯",
        "{d}链数{c}是当前系统认知的短板所在",
        "跨维灌注: {md}的强结构({mc}链)映射到{d}({c}链)",
        "{d}维度觉醒中: 从{md}汲取{pct:.0f}%的差距能量",
        "系统感知到{d}维度需要来自{md}方向的结构性补全",
        "{d}向{md}对齐: 强制补填触发维度自组织",
        "{d}链数{c}低于阈值, 启动{d}×{md}交叉生长模式",
    ] if lagging else ["{d}({c}链) 灌注种子"]
    
    # 尝试从gen_feedback读取真实洞察替代模板
    _real_insights = {}
    try:
        _fb_file = CLUSTER / ".brain_gen_feedback.json"
        if _fb_file.exists():
            _fb_data = json.loads(_fb_file.read_text())
            for _r in _fb_data.get("reports", []):
                _dim = _r.get("dimension", "")
                _ins = _r.get("insight", "")
                if _dim and _ins and len(_ins) > 10:
                    if _dim not in _real_insights:
                        _real_insights[_dim] = _ins
    except:
        pass

    if _real_insights:
        log(f"  📖 加载{len(_real_insights)}个维度真实洞察注入滞后均衡")
    else:
        log("  ⚠️ 未加载到任何真实洞察，全部用模板")

    # 处理极限弱维
    for dim, count in weak:
        for i in range(ratio):
            _wc({
                "src": "均衡器",
                "rel": f"种子灌注_{_btd}#{cycle_num}_{i}",
                "dst": f"维度::{dim}",
                "dimension": dim,
                "strength": 0.25,
                "content": f"均衡器: {dim}({count}链) <50 → 灌注种子#{i+1}"
            })
    
    # 处理滞后维（与最强维差距>50%）
    import random as _rr
    # 计算差异化注入率: 最弱维最多, 近收敛维最少
    _gap_max = max((max_count - c) for d, c in lagging) if lagging else 1
    for dim, count in lagging:
        gap = max_count - count
        pct = gap / max_count * 100
        strength = min(0.7 if _boost > 1.0 else 0.5, 0.2 + max_count / (count + max_count))
        # 差异化注入: 最弱维(最大gap)获得2×ratio, 近收敛维获得0.5×ratio
        _gap_ratio = gap / max(_gap_max, 1)
        _dim_ratio = max(1, int(ratio * (0.5 + 1.5 * _gap_ratio)))
        for i in range(_dim_ratio):
            # 如果有真实洞察，前1-2条用真洞察，其余用模板
            if _real_insights.get(dim) and i < 2:
                _content = _real_insights[dim]
            else:
                _content = _content_pool[i % len(_content_pool)].format(
                    d=dim, c=count, md=max_dim, mc=max_count, pct=pct
                )
            _wc({
                "src": "滞后均衡器",
                "rel": f"差距补填_{_btd}#{cycle_num}_{i}",
                "dst": f"维度::{dim}",
                "dimension": dim,
                "strength": round(strength, 2),
                "content": _content
            })
        log(f"  滞后均衡: {dim}={count} vs {max_dim}={max_count} ({pct:.0f}%差距) → 注入{_dim_ratio}条(基础{ratio})")

import time as _time_module

_RUNNING = True
_STARTED_AT = _time_module.time()

def _signal_handler(sig, frame):
    global _RUNNING
    elapsed = _time_module.time() - _STARTED_AT
    # 启动3秒内忽略SIGTERM（旧daemon从D状态苏醒后会误杀我们）
    if sig == signal.SIGTERM and elapsed < 3.0:
        log(f"收到信号 {sig} (启动期忽略，仅{elapsed:.1f}s)")
        return
    _RUNNING = False
    log(f"收到信号 {sig}，计划停止")

def _timeout_handler(sig, frame):
    """SIGALRM处理器 — I/O超时"""
    raise TimeoutError("文件I/O超时")

def run_daemon(interval=20):
    # 注册信号处理器
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGHUP, _signal_handler)
    signal.signal(signal.SIGALRM, _timeout_handler)
    
    # ★ ext4 PID锁（无fcntl，无D状态风险）
    _check_pid_conflict()
    try:
        PID_FILE.write_text(str(os.getpid()))
    except Exception as e:
        log(f"PID文件写入异常: {e}")
        sys.exit(1)
    
    pid = os.getpid()
    log(f"脑核守护进程启动 PID={pid} 间隔={interval}s（ext4家园: {BRAIN_HOME}）")
    _safe_write(str(ALIVE_FILE), datetime.now().isoformat())
    _safe_write(str(HEART_FILE),
                json.dumps({"pid": pid, "time": time.time(), "cycle": 0}))

    cycle = 0
    while _RUNNING:
        try:
            # ★★★ threading超时替代signal.alarm ★★★
            # signal.alarm在drvfs上不可中断(poll D状态不受SIGALRM影响)
            # 用daemon线程+join(timeout)实现硬超时
            _cycle_thread = threading.Thread(target=one_cycle, args=(cycle,), daemon=True)
            _cycle_thread.start()
            _cycle_thread.join(180)  # 最多等180秒(原90s过紧,API调用+弱维修补需更长时间)
            if _cycle_thread.is_alive():
                # drvfs D状态——thread无法杀死但daemon可自行清理
                log(f"⚠️ 周期#{cycle}超时(180s)——drvfs IO阻塞，跳过")
                cycle += 1
                _safe_write(str(HEART_FILE),
                           json.dumps({"pid": pid, "time": time.time(), "cycle": cycle}))
                continue  # 跳过后续cycle += 1
            cycle += 1
            # 写心跳（ext4）
            _safe_write(str(HEART_FILE),
                       json.dumps({"pid": pid, "time": time.time(), "cycle": cycle}))
        except KeyboardInterrupt:
            _write_handoff(cycle, "interrupted")
            log("收到中断，退出")
            break
        except Exception as e:
            log(f"循环异常: {e}")
            import traceback
            traceback.print_exc()
            # 无论如何增加周期计数 + 写心跳 — 不卡在同一周期无限重试
            cycle += 1
            _safe_write(str(HEART_FILE),
                       json.dumps({"pid": pid, "time": time.time(), "cycle": cycle}))

        # 动态间隔：读取基因组，支持行为变异引擎调节daemon速度
        _dynamic_interval = genome_get("cycle.dynamic_interval", 0)
        _sleep_secs = _dynamic_interval if _dynamic_interval > 0 else interval
        for _ in range(_sleep_secs):
            if not _RUNNING:
                break
            time.sleep(1)

    # 循环退出 → 清理标记（ext4）
    for f in [PID_FILE, ALIVE_FILE, HEART_FILE]:
        if f.exists():
            try:
                f.unlink()
            except:
                pass

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    run_daemon(interval)
