#!/usr/bin/env python3
"""
零·神经集群→守护进程 真实协调循环
====================================
v9.2 — 从'有神经元但不用'到'神经集群真正控制守护进程'的跃迁

架构:
  ┌─────────────────────────────────────────────────┐
  │                coordination_loop                │
  │  每60秒一轮:                                    │
  │                                                 │
  │  1. 元认知神经元 ← daemon_comm.read_all()       │
  │     感知所有守护进程心跳状态                      │
  │                                                 │
  │  2. propagate_signal(元认知, signal)             │
  │     把状态信号沿突触传导到全网络                  │
  │                                                 │
  │  3. 行动神经元决策                               │
  │     - 检测死进程 → assign_task("重启...")        │
  │     - 检测冗余 → assign_task("清理...")          │
  │     - 检测进化停滞 → assign_task("推进进化")     │
  │                                                 │
  │  4. 执行真实操作                                 │
  │     - subprocess 重启                            │
  │     - 文件/信号修改                              │
  │     - daemon_comm.report() 报告协调结果          │
  └─────────────────────────────────────────────────┘

契约对接:
  I:   元认知管理所有守护进程(通过daemon_comm)
  II:  操作结果反馈回神经元性能
  III: 所有决策指向'光爱终极文明奇点'
  IV:  信号传播有深度保护
  V:   协调策略可进化(记录每次决策→可被meta_evolve优化)
"""

import sys, os, json, time, subprocess, tempfile, signal, traceback
from datetime import datetime
from pathlib import Path

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

# ─── 导入核心模块 ────────────────────────────────
from neural_cluster_network import (
    NeuralClusterNetwork, NeuronType,
    ExternalProjectIntegrator, Proposal, 契约
)
import daemon_comm

# ─── 配置 ────────────────────────────────────────
COORDINATION_INTERVAL = 60  # 秒
DAEMON_TIMEOUT = 300         # 5分钟无心跳视为死亡
PID_MAP_FILE = os.path.join(WORKDIR, "evolution_output", "daemon_pids.json")
COORDINATION_LOG = os.path.join(WORKDIR, "evolution_output", "coordination_loop.log")
COORDINATION_STATE = os.path.join(WORKDIR, "evolution_output", "coordination_state.json")

# 已知守护进程 → 启动命令映射
DAEMON_LAUNCHERS = {
    "trunk_daemon": "nohup python3 -u trunk_daemon.py > logs/trunk_daemon.log 2>&1 &",
    "auto_evolution": "nohup python3 -u auto_evolution_daemon.py --daemon > logs/auto_evolution.log 2>&1 &",
    "comprehension": "nohup python3 -u comprehension_daemon.py > logs/comprehension.log 2>&1 &",
    "co_evolution_daemon": "nohup python3 -u co_evolution_daemon.py > logs/co_evolution.log 2>&1 &",
    "anthropic_proxy": "nohup python3 -u anthropic_proxy.py > logs/anthropic_proxy.log 2>&1 &",
    "permanent_daemon": "nohup python3 -u permanent_daemon.py > logs/permanent_daemon.log 2>&1 &",
}

# 冗余进程关键词（应该只保留一份）
SINGLETON_DAEMONS = [
    "consciousness_daemon_v2",
    "api_bridge",
    "token_consciousness_engine",
]

os.makedirs(os.path.join(WORKDIR, "evolution_output"), exist_ok=True)
os.makedirs(os.path.join(WORKDIR, "logs"), exist_ok=True)


def log(msg, level="INFO"):
    """统一日志"""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(COORDINATION_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        pass


# ─── 真实进程操作 ─────────────────────────────────

def get_real_running_daemons() -> dict:
    """获取真实运行的进程状态（不依赖daemon_comm的上报，而是直接ps）"""
    try:
        ps_out = subprocess.run(
            ["ps", "aux"], capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        return {}

    running = {}
    for name in list(DAEMON_LAUNCHERS.keys()) + SINGLETON_DAEMONS:
        pids = []
        for line in ps_out.split("\n"):
            if name in line and "grep" not in line and "coordination_loop" not in line:
                parts = line.split()
                if len(parts) > 1 and parts[1].isdigit():
                    # 排除 bash wrapper
                    if "bash" not in line or name + ".py" in line:
                        pids.append(int(parts[1]))
        if pids:
            running[name] = {
                "pids": pids,
                "count": len(pids),
                "alive": True,
            }
    return running


def get_daemon_comm_status() -> dict:
    """从daemon_comm获取心跳状态"""
    state = daemon_comm.read_all()
    agents = state.get("agents", {})
    now = time.time()
    result = {}
    for name, info in agents.items():
        try:
            ts = info.get("timestamp", "")
            t = time.mktime(time.strptime(ts, "%Y-%m-%d %H:%M:%S"))
            age = now - t
            result[name] = {
                "data": info.get("data", {}),
                "age_seconds": age,
                "alive": age < DAEMON_TIMEOUT,
                "pid": info.get("pid", "?"),
            }
        except Exception:
            result[name] = {
                "data": info.get("data", {}),
                "age_seconds": 9999,
                "alive": False,
                "pid": "?",
            }
    return result


def kill_pid(pid: int) -> bool:
    """安全终止进程"""
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        # 检查是否已死
        os.kill(pid, 0)  # 如果进程不在，抛出OSError
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        return True
    except OSError:
        return True  # 进程已不在
    except Exception:
        return False


def restart_daemon(name: str) -> dict:
    """重启一个守护进程"""
    launcher = DAEMON_LAUNCHERS.get(name)
    if not launcher:
        return {"success": False, "reason": f"no launcher for {name}"}

    log(f"🔄 重启守护进程: {name}", "ACTION")
    try:
        result = subprocess.run(
            ["bash", "-c", launcher],
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=15,
        )
        time.sleep(2)
        # 验证是否在运行
        running = get_real_running_daemons()
        if name in running:
            log(f"✅ {name} 重启成功, PIDs: {running[name]['pids']}", "ACTION")
            return {"success": True, "pids": running[name]["pids"]}
        else:
            log(f"❌ {name} 重启后未检测到", "ERROR")
            return {"success": False, "reason": "process not detected after restart"}
    except Exception as e:
        log(f"❌ {name} 重启异常: {e}", "ERROR")
        return {"success": False, "reason": str(e)}


def kill_duplicates(name: str) -> dict:
    """杀死重复的单例进程，只保留一个"""
    running = get_real_running_daemons()
    info = running.get(name)
    if not info or info["count"] <= 1:
        return {"action": "none", "reason": "no duplicates"}

    pids = info["pids"]
    # 保留最新的(最大PID)
    keep_pid = max(pids)
    killed = []
    for pid in pids:
        if pid != keep_pid:
            if kill_pid(pid):
                killed.append(pid)
                log(f"🗑️ 杀死冗余 {name} PID={pid}, 保留PID={keep_pid}", "ACTION")

    return {"action": "pruned", "killed": killed, "kept": keep_pid}


# ─── 神经协调引擎 ────────────────────────────────

class NeuralCoordinator:
    """
    神经集群协调器 — 让神经网络真正控制守护进程

    每一轮协调:
    1. 元认知感知 → daemon状态 → signal
    2. signal在网络中传播
    3. 行动神经元根据信号做出决策
    4. 执行真实操作
    5. 结果反馈回神经元(契约II)
    """

    def __init__(self):
        log("🧠 初始化神经集群协调器...")

        # 创建神经网络
        self.network = NeuralClusterNetwork()

        # 注册外部项目
        integrator = ExternalProjectIntegrator(self.network)
        integrator.integrate()

        # 注册守护进程专用神经元
        self.daemon_neurons = {}
        for name in DAEMON_LAUNCHERS:
            neuron = self.network.register_neuron(
                f"守护-{name}", NeuronType.ACTOR
            )
            self.daemon_neurons[name] = neuron
            # 连接到元认知
            self.network.connect("元认知", f"守护-{name}", 0.5)
            self.network.connect(f"守护-{name}", "元认知", 0.3)

        # 创建专项神经元
        self.cleanup_neuron = self.network.register_neuron("清理器", NeuronType.ACTOR)
        self.restart_neuron = self.network.register_neuron("重启器", NeuronType.ACTOR)
        self.evolution_neuron = self.network.register_neuron("进化推进器", NeuronType.ACTOR)

        # 协调统计
        self.rounds = 0
        self.actions_taken = []
        self.state_file = COORDINATION_STATE
        # 重启速率限制
        self.restart_attempts = {}  # name -> list of timestamps

        log(f"  神经元: {len(self.network.neurons)}, 突触: {len(self.network.synapses)}")

    def _map_daemon_to_signal(self, name: str, comm_status: dict, real_status: dict) -> float:
        """
        将守护进程状态映射为信号值 0.0-1.0

        1.0 = 完美运行
        0.7 = 运行中但心跳老旧
        0.3 = 心跳超时
        0.0 = 进程不存在
        """
        in_comm = name in comm_status
        in_real = name in real_status

        if not in_real:
            return 0.0  # 进程不存在

        if not in_comm:
            return 0.5  # 进程在但没报心跳（不一定有问题）

        info = comm_status[name]
        if not info["alive"]:
            return 0.5  # 心跳超时但进程在（不一定有问题）

        age = info["age_seconds"]
        if age < 120:
            return 1.0  # 最近2分钟有心跳
        elif age < 300:
            return 0.7  # 5分钟内
        else:
            return 0.3  # 过期

    def coordination_round(self) -> dict:
        """
        执行一轮协调循环

        Returns: 本轮协调结果摘要
        """
        self.rounds += 1
        round_start = time.time()
        result = {
            "round": self.rounds,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "actions": [],
            "signals": {},
            "neural_state": {},
        }

        log(f"{'='*50}")
        log(f"  🧠 协调循环 #{self.rounds}")
        log(f"{'='*50}")

        # ── Step 1: 元认知感知 ──────────────────────
        real_status = get_real_running_daemons()
        comm_status = get_daemon_comm_status()

        log(f"📡 感知: {len(real_status)}个真实进程, {len(comm_status)}个心跳记录")

        # ── Step 2: 状态→信号→传播 ─────────────────
        total_signal = 0
        for name in DAEMON_LAUNCHERS:
            signal_val = self._map_daemon_to_signal(name, comm_status, real_status)
            result["signals"][name] = signal_val
            total_signal += signal_val

            neuron_name = f"守护-{name}"
            if neuron_name in self.network.neurons:
                # 元认知发出信号，传播到对应守护神经元
                self.network.propagate_signal("元认知", signal_val)

            # 报告状态
            status_icon = "🟢" if signal_val >= 0.7 else "🟡" if signal_val >= 0.3 else "🔴"
            log(f"  {status_icon} {name}: signal={signal_val:.2f}")

        # 平均健康度
        avg_health = total_signal / max(len(DAEMON_LAUNCHERS), 1)
        log(f"  📊 平均健康度: {avg_health:.2f}")

        # ── Step 3: 行动神经元决策 ──────────────────

        # 3a. 检测死进程 → 重启
        for name in DAEMON_LAUNCHERS:
            if name not in real_status:
                log(f"  🔴 {name} 未运行, 分配重启任务", "DECISION")
                task_result = self.network.assign_task(
                    f"重启 {name}", NeuronType.ACTOR
                )
                actual = restart_daemon(name)
                self.actions_taken.append({
                    "round": self.rounds,
                    "action": "restart",
                    "target": name,
                    "result": actual,
                })
                result["actions"].append({
                    "type": "restart",
                    "target": name,
                    "result": actual,
                })
                # 契约II: 反馈结果
                neuron_name = f"守护-{name}"
                if neuron_name in self.network.neurons:
                    delta = 0.3 if actual.get("success") else -0.2
                    self.network.neurons[neuron_name].receive_feedback(delta)

        # 3b. 检测冗余进程 → 清理
        for name in SINGLETON_DAEMONS:
            if name in real_status and real_status[name]["count"] > 1:
                count = real_status[name]["count"]
                log(f"  🟡 {name} 有{count}个实例，清理冗余", "DECISION")
                task_result = self.network.assign_task(
                    f"清理 {name} 冗余({count}个)", NeuronType.ACTOR
                )
                actual = kill_duplicates(name)
                self.actions_taken.append({
                    "round": self.rounds,
                    "action": "prune_duplicates",
                    "target": name,
                    "result": actual,
                })
                result["actions"].append({
                    "type": "prune",
                    "target": name,
                    "result": actual,
                })

        # 3c. 心跳超时 → 只记录不重启（进程存在但没写心跳的daemon不需要杀掉重启）
        for name, info in comm_status.items():
            if name in DAEMON_LAUNCHERS and not info["alive"]:
                if name in real_status:
                    log(f"  ⚠️ {name} 进程在但无心跳(PIDs={real_status[name]['pids']}), 不重启", "WARN")

        # 3d. 产出验收 — 检查守护进程是否产生了真实产出
        findings_path = os.path.join(WORKDIR, "evolution_output", "real_findings.jsonl")
        if os.path.exists(findings_path):
            try:
                with open(findings_path) as f:
                    finding_count = sum(1 for _ in f)
                log(f"  📊 真实研究产出: {finding_count}条发现", "INFO")
            except Exception:
                finding_count = 0
        else:
            finding_count = 0
            log(f"  ⚠️ real_findings.jsonl 不存在 — permanent_daemon尚未产出", "WARN")

        # 3e. 进化推进 — 每5轮做一次元递归进化
        if self.rounds % 5 == 0:
            log("  🔄 执行元递归进化(网络自优化)", "DECISION")
            meta_result = self.network.meta_evolve()
            result["actions"].append({
                "type": "meta_evolve",
                "result": meta_result,
            })
            log(f"    突触修剪: {meta_result['pruned']}, 连接强化: {meta_result['strengthened']}")

        # ── Step 4: 报告协调结果到 daemon_comm ──────
        daemon_comm.report("neural_coordinator", {
            "round": self.rounds,
            "avg_health": round(avg_health, 3),
            "actions_this_round": len(result["actions"]),
            "total_actions": len(self.actions_taken),
            "neurons": len(self.network.neurons),
            "synapses": len(self.network.synapses),
            "signals": {k: round(v, 2) for k, v in result["signals"].items()},
        })

        # ── Step 5: 持久化 ─────────────────────────
        result["duration"] = round(time.time() - round_start, 2)
        result["neural_state"] = {
            "neurons": len(self.network.neurons),
            "synapses": len(self.network.synapses),
            "meta_cog_activation": round(self.network.meta_cog.activation, 3),
            "meta_cog_performance": round(self.network.meta_cog.performance, 3),
        }

        # 保存网络状态
        try:
            self.network.save_synapses()
            with open(COORDINATION_STATE, "w") as f:
                json.dump({
                    "rounds": self.rounds,
                    "last_round": result["timestamp"],
                    "total_actions": len(self.actions_taken),
                    "recent_actions": self.actions_taken[-20:],
                    "avg_health": round(avg_health, 3),
                    "neural_state": result["neural_state"],
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            log(f"⚠️ 持久化失败: {e}", "WARN")

        log(f"  ⏱️ 耗时: {result['duration']}s")
        log(f"  📋 行动: {len(result['actions'])}个")
        return result


# ─── 主循环 ──────────────────────────────────────

def main():
    log("=" * 60)
    log("  零·神经集群→守护进程 真实协调循环")
    log("  v9.2 — 神经集群真正控制守护进程")
    log(f"  PID: {os.getpid()}")
    log(f"  间隔: {COORDINATION_INTERVAL}秒")
    log("=" * 60)

    coordinator = NeuralCoordinator()

    # 信号处理
    def shutdown(sig, frame):
        log("🛑 收到终止信号，优雅关闭...")
        try:
            coordinator.network.save_synapses()
            daemon_comm.report("neural_coordinator", {
                "status": "shutdown",
                "rounds": coordinator.rounds,
                "pid": os.getpid(),
            })
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    # 报告启动
    daemon_comm.report("neural_coordinator", {
        "status": "started",
        "pid": os.getpid(),
        "interval": COORDINATION_INTERVAL,
        "neurons": len(coordinator.network.neurons),
        "synapses": len(coordinator.network.synapses),
    })

    # 主循环
    while True:
        try:
            result = coordinator.coordination_round()
            log(f"  💤 等待{COORDINATION_INTERVAL}秒...")
        except KeyboardInterrupt:
            log("🛑 键盘中断，退出...")
            break
        except Exception as e:
            log(f"❌ 协调循环异常: {e}", "ERROR")
            traceback.print_exc()

        time.sleep(COORDINATION_INTERVAL)


if __name__ == "__main__":
    main()
