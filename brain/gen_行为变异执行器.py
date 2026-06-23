
"""gen_行为变异执行器.py — 行为变异引擎
根据行为变异设计实现触发、变异、验证与回滚四阶段。
可通过 loader 被 daemon 每周期调用（engineer_行为变异执行器()），也可独立运行。
"""
import json
import os
import sys
import time
import random
import copy
import hashlib
import math
from pathlib import Path
from datetime import datetime, timedelta

# ─── 路径 ─────────────────────────────────────────────
CLUSTER = Path(__file__).resolve().parent.parent

# ─── 日志工具 ─────────────────────────────────────────
def log(msg, _log_func=None):
    """输出日志：优先使用传入的 log 函数，否则写 stdout"""
    if _log_func is not None:
        _log_func(msg)
    else:
        print(f"  🧬 [{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# ─── 基因组访问 ──────────────────────────────────────
def _genome_get(key, default=None):
    try:
        from brain.genome import get
        return get(key, default)
    except Exception:
        return default

def _load_genome():
    try:
        from brain.genome import load_genome
        return load_genome()
    except Exception:
        return {}

def _update_genome(overrides):
    try:
        from brain.genome import update_genome
        return update_genome(overrides)
    except Exception as e:
        log(f"基因组更新失败: {e}")
        return None

# ─── 统计收集 ─────────────────────────────────────────
def gather_stats():
    """收集当前系统统计，用于触发判断和验证。
    返回字典包含字段：
      consecutive_error_count, hourly_error_count,
      total_chains, abnormal_chains, output_entropy
    """
    stats = {
        "consecutive_error_count": 0,
        "hourly_error_count": 0,
        "total_chains": 0,
        "abnormal_chains": 0,
        "output_entropy": 0.0,
    }

    # 1. 连续相同错误名称计数（从“专注检测”数据获取）
    #    尝试读取 .brain_focus_repeat.json（如果存在）
    focus_repeat_file = CLUSTER / ".brain_focus_repeat.json"
    if focus_repeat_file.exists():
        try:
            data = json.loads(focus_repeat_file.read_text())
            stats["consecutive_error_count"] = data.get("repeat_count", 0)
        except Exception:
            pass

    # 2. 最近1小时错误计数：分析 daemon 日志
    log_file = CLUSTER / ".brain_daemon.log"
    if log_file.exists():
        try:
            lines = log_file.read_text().splitlines()
            now = datetime.now()
            hour_ago = now - timedelta(hours=1)
            error_count = 0
            for line in lines:
                # 尝试提取时间（格式 [HH:MM:SS]）
                if len(line) > 20 and line[2] == '[':
                    time_str = line[3:11]  # HH:MM:SS
                    try:
                        line_time = datetime.strptime(time_str, "%H:%M:%S").replace(
                            year=now.year, month=now.month, day=now.day
                        )
                        # 跨天处理（假设日志只有当天，跨天需要更复杂处理，忽略）
                        if line_time < hour_ago:
                            continue
                    except ValueError:
                        continue
                # 检测错误关键字
                if any(kw in line for kw in ("错误", "ERROR", "异常", "⚠️", "✗", "失败")):
                    error_count += 1
            stats["hourly_error_count"] = error_count
        except Exception:
            pass

    # 3. 链总数与异常链数：从 hippocampus 获取
    hip_file = CLUSTER / "hippocampus_memory.json"
    if hip_file.exists():
        try:
            data = json.loads(hip_file.read_text())
            if isinstance(data, list):
                chains = data
            elif isinstance(data, dict):
                chains = data.get("chains", data.get("memory", []))
            else:
                chains = []
            stats["total_chains"] = len(chains)
            # 异常链判断：包含 "anomaly" 或 "error" 字段的链
            abnormal = sum(
                1 for c in chains
                if isinstance(c, dict) and c.get("anomaly", False) or c.get("error", False)
            )
            stats["abnormal_chains"] = abnormal
        except Exception:
            pass

    # 4. 输出熵：尝试从最近输出文件计算
    entropy_file = CLUSTER / ".brain_output_entropy.json"
    if entropy_file.exists():
        try:
            stats["output_entropy"] = json.loads(entropy_file.read_text()).get("entropy", 0.0)
        except Exception:
            pass

    return stats

# ─── 变更加密工具 ─────────────────────────────────────
def _safe_write_chain(entry):
    """使用 safe_hip.write_chain 写入链记录"""
    try:
        from brain.share import write_chain
        write_chain(entry)
    except Exception:
        try:
            from safe_hip import write_chain
            write_chain(entry)
        except Exception as e:
            log(f"写入链记录失败: {e}")

# ─── 变异引擎类 ────────────────────────────────────────
class MutationEngine:
    """行为变异引擎，实现触发→执行→验证→回滚四阶段"""
    def __init__(self):
        self.baseline = {}            # 变异前统计快照（验证用）
        self.history = []             # 变异记录列表
        self.last_mutation_time = 0   # 上次变异时间戳（秒）
        self._load_genes()

    def _load_genes(self):
        """从基因组加载参数"""
        g = _load_genome()
        self.interval_minutes = g.get("mutation_interval_minutes", 60)
        self.error_threshold = g.get("error_threshold_for_mutation", 95)
        self.anomaly_threshold = g.get("chain_anomaly_threshold", 0.01)
        self.noise_scale = g.get("noise_scale_for_parameters", 0.05)
        self.rollback_sensitivity = g.get("rollback_sensitivity", 0.2)

    # ── 触发检测 ──────────────────────────────────────
    def detect_triggers(self, stats):
        """检测是否满足触发条件，返回触发列表"""
        triggers = []

        # 条件1：连续相同错误名称超过阈值
        if stats.get("consecutive_error_count", 0) >= self.error_threshold:
            triggers.append("连续相同错误名称超过阈值")

        # 条件2：最近1小时错误计数超过阈值
        if stats.get("hourly_error_count", 0) >= self.error_threshold:
            triggers.append("最近1小时错误计数超过阈值")

        # 条件3：链异常比例超标
        total = stats.get("total_chains", 0)
        abnormal = stats.get("abnormal_chains", 0)
        if total > 0 and (abnormal / total) >= self.anomaly_threshold:
            triggers.append("链检查异常比例超标")

        return triggers

    # ── 策略选择 ──────────────────────────────────────
    def select_strategy(self):
        """按概率随机选择一种变异策略"""
        strategies = ["模块版本切换", "参数随机扰动", "行为注入", "调度重置"]
        weights = [0.3, 0.3, 0.2, 0.2]   # 可根据需要调整
        return random.choices(strategies, weights=weights)[0]

    # ── 变异执行 ──────────────────────────────────────
    def mutate(self, strategy):
        """执行变异，返回记录字典"""
        pre_snapshot = self._take_snapshot()
        details = {}

        if strategy == "模块版本切换":
            details = self._strategy_module_switch()
        elif strategy == "参数随机扰动":
            details = self._strategy_param_perturb()
        elif strategy == "行为注入":
            details = self._strategy_behavior_inject()
        elif strategy == "调度重置":
            details = self._strategy_schedule_reset()

        record = {
            "timestamp": datetime.now().isoformat(),
            "strategy": strategy,
            "pre_snapshot": pre_snapshot,
            "details": details,
        }
        self.history.append(record)
        self._log_mutation(record)
        _safe_write_chain({
            "type": "behavior_mutation",
            "subtype": "mutate",
            "strategy": strategy,
            "timestamp": record["timestamp"],
            "details": details,
        })
        return record

    def _strategy_module_switch(self):
        """策略：模块版本切换——随机将高频使用模块替换为其他版本"""
        before = _load_genome().get("module_selection_weights", {})
        if not before:
            # 若尚未定义，创建一个默认均匀权重
            before = {"gen_平衡器": 1.0, "gen_器_资源循环": 1.0, "gen_焦点维护": 1.0}
        # 随机扰动权重
        after = {}
        for k, v in before.items():
            noise = random.gauss(0, 0.15)
            after[k] = max(0.0, min(1.0, v + noise))
        total = sum(after.values())
        if total > 0:
            after = {k: v / total for k, v in after.items()}
        _update_genome({"module_selection_weights": after})
        return {
            "action": "调整 module_selection_weights",
            "pre": before,
            "post": after,
        }

    def _strategy_param_perturb(self):
        """策略：参数随机扰动——对关键基因参数加高斯噪声"""
        target_params = [
            "module_selection_weights",
            "mutation_interval_minutes",
            "error_threshold_for_mutation",
            "chain_anomaly_threshold",
            "noise_scale_for_parameters",
            "rollback_sensitivity",
        ]
        changes = {}
        for param in target_params:
            current = _genome_get(param)
            if current is None:
                continue
            # 数字参数加噪声，字典参数递归处理
            if isinstance(current, dict):
                new_dict = {}
                for k, v in current.items():
                    noise = random.gauss(0, self.noise_scale)
                    new_dict[k] = max(0.0, min(1.0, v + noise))
                total = sum(new_dict.values())
                if total > 0:
                    new_dict = {k: v / total for k, v in new_dict.items()}
                changes[param] = new_dict
            elif isinstance(current, (int, float)):
                noise = random.gauss(0, self.noise_scale * max(abs(current), 1.0))
                new_val = current + noise
                # 取值约束（如果已知范围）
                range_map = {
                    "mutation_interval_minutes": (10, 120),
                    "error_threshold_for_mutation": (10, 500),
                    "chain_anomaly_threshold": (0.001, 0.1),
                    "noise_scale_for_parameters": (0.01, 0.2),
                    "rollback_sensitivity": (0.01, 0.5),
                }
                if param in range_map:
                    lo, hi = range_map[param]
                    new_val = max(lo, min(hi, new_val))
                changes[param] = int(new_val) if isinstance(current, int) else new_val
        if changes:
            _update_genome(changes)
        return {"action": "参数随机扰动", "changes": changes}

    def _strategy_behavior_inject(self):
        """策略：行为注入——强制激活交叉验证，持续5个周期"""
        _update_genome({
            "behavior_injection_active": True,
            "cross_validation_boost": 5,
        })
        return {"action": "激活行为注入（交叉验证+5周期）"}

    def _strategy_schedule_reset(self):
        """策略：调度重置——温和重启主循环（重置任务队列）"""
        # 重置调度队列标志（实际重置由 daemon 检测此标志执行）
        _update_genome({"schedule_reset_requested": True})
        return {"action": "请求调度重置"}

    # ── 快照与回滚 ────────────────────────────────────
    def _take_snapshot(self):
        """当前系统关键状态快照"""
        return {
            "timestamp": datetime.now().isoformat(),
            "genome": _load_genome(),
            "chain_hash": self._compute_chain_hash(),
        }

    def _compute_chain_hash(self):
        """计算海马体所有链的 MD5 哈希（用于完整性校验）"""
        try:
            hip_file = CLUSTER / "hippocampus_memory.json"
            if hip_file.exists():
                data = hip_file.read_bytes()
                return hashlib.md5(data).hexdigest()
        except Exception:
            pass
        return "unknown"

    def rollback(self):
        """回滚到上次变异前的状态（从 history 中恢复）"""
        if not self.history:
            log("无历史记录，无法回滚")
            return
        last_record = self.history[-1]
        pre_snapshot = last_record.get("pre_snapshot", {})
        pre_genome = pre_snapshot.get("genome", {})
        if pre_genome:
            try:
                _update_genome(pre_genome)
            except Exception as e:
                log(f"回滚基因组失败: {e}")
        # 额外清理行为注入标志
        if last_record.get("strategy") == "行为注入":
            _update_genome({"behavior_injection_active": False, "cross_validation_boost": 0})
        if last_record.get("strategy") == "调度重置":
            _update_genome({"schedule_reset_requested": False})
        log(f"已回滚变异: {last_record['strategy']}")
        _safe_write_chain({
            "type": "behavior_mutation",
            "subtype": "rollback",
            "strategy": last_record["strategy"],
            "timestamp": datetime.now().isoformat(),
        })
        # 清空 history 和 baseline
        self.history = []
        self.baseline = {}

    # ── 验证 ──────────────────────────────────────────
    def verify(self, current_stats):
        """验证变异是否成功（与 baseline 对比）"""
        base = self.baseline
        if not base:
            return False

        success = True

        # 1. 错误计数下降 > 50%
        base_err = base.get("hourly_error_count", 0)
        cur_err = current_stats.get("hourly_error_count", 0)
        if base_err > 0:
            err_change = (cur_err - base_err) / base_err
            if err_change > -0.5:      # 未下降超过50%
                success = False

        # 2. 链异常总数 < 10
        if current_stats.get("abnormal_chains", 999) >= 10:
            success = False

        # 3. 输出熵提升 >= 0.2
        base_entropy = base.get("output_entropy", 0)
        cur_entropy = current_stats.get("output_entropy", 0)
        if base_entropy > 0 and cur_entropy < base_entropy + 0.2:
            success = False

        return success

    def _is_deteriorated(self, current_stats):
        """检查是否恶化超过回滚灵敏度"""
        base = self.baseline
        if not base:
            return False
        for metric in ["hourly_error_count", "abnormal_chains"]:
            bv = base.get(metric, 0)
            cv = current_stats.get(metric, 0)
            if bv > 0 and (cv - bv) / bv > self.rollback_sensitivity:
                return True
        return False

    # ── 日志 ──────────────────────────────────────────
    def _log_mutation(self, record):
        """写变异日志到独立文件和 share.log"""
        log_dir = CLUSTER / ".mutation_logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        fname = f"mutation_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{random.randint(1000,9999)}.json"
        try:
            (log_dir / fname).write_text(
                json.dumps(record, ensure_ascii=False, indent=2)
            )
        except Exception as e:
            log(f"写变异日志文件失败: {e}")
        log(f"⬡ 变异执行: {record['strategy']} | {json.dumps(record['details'], ensure_ascii=False)}")

    # ── 主评估接口 ────────────────────────────────────
    def evaluate(self, current_stats, log_func=None):
        """对外唯一调用接口：触发→变异→验证→回滚
        current_stats: 当前系统统计字典
        log_func: 可选的日志函数
        """
        global log
        old_log = log
        if log_func:
            log = lambda msg: log_func(msg)

        now = time.time()

        # Ⅰ. 如果存在 baseline，表示正处于变异后验证期
        if self.baseline:
            # 验证成功
            if self.verify(current_stats):
                log("✓ 变异成功！清理基线")
                self.baseline = {}
                self.history = []
            # 恶化则回滚
            elif self._is_deteriorated(current_stats):
                log("✗ 变异恶化，立即回滚")
                self.rollback()
            else:
                # 超时自动回滚（1小时）
                mut_time = self.baseline.get("mutation_time", 0)
                if mut_time > 0 and (now - mut_time) > 3600:
                    log("⏰ 变异超过1小时未达标，自动回滚")
                    self.rollback()
                else:
                    log(f"⏳ 变异验证中... (已过 {int((now - mut_time)/60)} 分钟)")
            log = old_log
            return

        # Ⅱ. 无 baseline：检查冷却期
        elapsed = (now - self.last_mutation_time) / 60  # 分钟
        if elapsed < self.interval_minutes:
            log = old_log
            return

        # Ⅲ. 检测卡住
        triggers = self.detect_triggers(current_stats)
        if triggers:
            log(f"⚡ 检测到卡住状态: {', '.join(triggers)}")
            self.baseline = current_stats.copy()
            self.baseline["mutation_time"] = now
            strategy = self.select_strategy()
            log(f"→ 选择变异策略: {strategy}")
            self.mutate(strategy)
            self.last_mutation_time = now
        else:
            log("✓ 系统运行正常，无需变异")

        log = old_log


# ─── 全局引擎实例（单例） ─────────────────────────────
_ENGINE = None

def get_engine():
    global _ENGINE
    if _ENGINE is None:
        _ENGINE = MutationEngine()
    return _ENGINE

# ─── 对外接口（供 loader 调用） ─────────────────────────
def engineer_行为变异执行器(log_func=None):
    """每周期由 loader 调用，执行一次行为变异评估"""
    engine = get_engine()
    stats = gather_stats()
    try:
        engine.evaluate(stats, log_func=log_func)
    except Exception as e:
        log(f"行为变异引擎异常: {e}", log_func)
    # 返回简要状态报告
    return {
        "module": "gen_行为变异执行器",
        "status": "ok",
        "triggers": engine.detect_triggers(stats),
        "in_mutation": bool(engine.baseline),
        "history_count": len(engine.history),
    }


# ─── 独立运行测试 ─────────────────────────────────────
if __name__ == "__main__":
    # 模拟独立运行，展示完整流程
    print(json.dumps({
        "module": "gen_行为变异执行器",
        "status": "standalone_test",
        "message": "开始模拟行为变异流程",
    }, ensure_ascii=False))

    engine = get_engine()
    # 第一次调用：正常状态，不触发
    stats_normal = {
        "consecutive_error_count": 1,
        "hourly_error_count": 2,
        "total_chains": 100,
        "abnormal_chains": 0,
        "output_entropy": 1.0,
    }
    engine.evaluate(stats_normal)
    print("--- 模拟正常状态，预期无变异 ---")

    # 第二次调用：触发异常（错误计数超标）
    stats_trigger = {
        "consecutive_error_count": 100,
        "hourly_error_count": 200,
        "total_chains": 100,
        "abnormal_chains": 15,
        "output_entropy": 0.5,
    }
    engine.evaluate(stats_trigger)
    print("--- 触发变异 ---")

    # 模拟验证期（冷却期内调用，统计改善）
    stats_improved = {
        "consecutive_error_count": 10,
        "hourly_error_count": 30,
        "total_chains": 100,
        "abnormal_chains": 3,
        "output_entropy": 1.8,
    }
    engine.evaluate(stats_improved)
    print("--- 验证成功 ---")

    # 输出最终状态
    print(json.dumps({
        "engine_history_count": len(engine.history),
        "engine_baseline_exists": bool(engine.baseline),
        "last_mutation": engine.history[-1] if engine.history else None,
    }, ensure_ascii=False, indent=2))
