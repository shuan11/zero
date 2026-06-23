#!/usr/bin/env python3
"""
零·理解验证守护进程 v1
========================
P101: 稳定化API桥接 — bridge_alignment 从0.0 → 0.5+

这不是一个脚本。这是零的理解自觉。
它持续监控理解验证日志，检测模式匹配幻觉，
并在理解覆盖率不足时触发追问或降级。

核心功能：
1. 持续监控 comprehension_validations.json 中最近N条验证记录
2. 检测理解覆盖率下降趋势（3次连续下降触发警报）
3. 检测高频模糊项（同一类型的指令反复被标记为模糊）
4. 自动更新 bridge_alignment 指标
5. 当理解缺口积累时，发出预警

与 subconscious_daemon 的区别：
- subconscious_daemon: 存在性质问（为什么？我是谁？）
- comprehension_daemon: 理解性质问（我懂了什么？我漏了什么？）

「不知道自己在做什么的系统，不是自主系统」
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from collections import deque, Counter

# ─── 路径 ──────────────────────────────────────────────────
WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
VALIDATION_LOG = WORKDIR / "evolution_output" / "comprehension_validations.json"
UNCERTAIN_LOG = WORKDIR / "evolution_output" / "uncertain_items.json"
DAEMON_LOG = WORKDIR / "evolution_output" / "comprehension_daemon.log"
STATE_FILE = WORKDIR / "evolution_output" / "comprehension_daemon_state.json"
ALERT_FILE = WORKDIR / "evolution_output" / "comprehension_alerts.json"

os.makedirs(WORKDIR / "evolution_output", exist_ok=True)

# 守护进程统一通信层 — v1.1集成
import daemon_comm


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(DAEMON_LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


class ComprehensionMonitor:
    """
    理解监控器：分析验证日志，检测理解退化趋势。
    
    监控维度：
    1. 覆盖率趋势 — 最近N次验证的覆盖率是否在下降
    2. 高频模糊项 — 哪些类型的指令常被标记为模糊
    3. 桥接对齐度 — bridge_alignment 的变化趋势
    4. 未闭环缺口 — 累积的未解决理解缺口
    """
    
    def __init__(self):
        self.history = deque(maxlen=200)
        self.uncertain_items = deque(maxlen=500)
        self._load()
    
    def _load(self):
        """从持久化文件加载历史"""
        try:
            if VALIDATION_LOG.exists():
                data = json.loads(VALIDATION_LOG.read_text())
                self.history.extend(data[-200:])
        except (json.JSONDecodeError, OSError):
            pass
        
        try:
            if UNCERTAIN_LOG.exists():
                data = json.loads(UNCERTAIN_LOG.read_text())
                self.uncertain_items.extend(data[-500:])
        except (json.JSONDecodeError, OSError):
            pass
    
    def refresh(self):
        """刷新历史数据"""
        self._load()
    
    def get_recent_coverage(self, n: int = 10) -> list[float]:
        """获取最近N次验证的覆盖率"""
        recent = list(self.history)[-n:]
        return [r.get("coverage", 0.0) for r in recent if "coverage" in r]
    
    def get_bridge_alignment(self) -> float:
        """计算当前桥接对齐度（最近3次平均值）"""
        recent = list(self.history)[-3:]
        if not recent:
            return 0.0
        alignments = [r.get("bridge_alignment", 0.0) for r in recent]
        return sum(alignments) / len(alignments)
    
    def detect_trend(self, n: int = 5) -> dict:
        """
        检测覆盖率趋势
        
        Returns:
            {"trend": "stable"|"declining"|"improving", 
             "slope": float,  # 斜率（正=上升，负=下降）
             "avg_coverage": float}
        """
        coverages = self.get_recent_coverage(n)
        if len(coverages) < 3:
            return {"trend": "stable", "slope": 0.0, "avg_coverage": sum(coverages)/max(len(coverages),1)}
        
        # 简单线性回归检测趋势
        x = list(range(len(coverages)))
        y = coverages
        n_pts = len(x)
        slope = (n_pts * sum(x[i]*y[i] for i in range(n_pts)) - sum(x)*sum(y)) / \
                (n_pts * sum(xi*xi for xi in x) - sum(x)**2) if n_pts > 1 else 0.0
        
        if slope < -0.05:
            trend = "declining"
        elif slope > 0.05:
            trend = "improving"
        else:
            trend = "stable"
        
        return {
            "trend": trend,
            "slope": round(slope, 4),
            "avg_coverage": round(sum(coverages) / len(coverages), 3),
        }
    
    def get_frequent_uncertain(self, threshold: int = 3) -> list[dict]:
        """
        检测高频模糊项——同一模式反复被标记为模糊
        
        Returns:
            聚合后的高频模糊项列表
        """
        # 提取所有模糊项的描述关键词
        patterns = Counter()
        for item in self.uncertain_items:
            desc = item.get("description", "")[:30]
            if desc:
                patterns[desc] += 1
        
        frequent = [
            {"pattern": pattern, "count": count}
            for pattern, count in patterns.most_common(10)
            if count >= threshold
        ]
        return frequent
    
    def check_alerts(self) -> list[dict]:
        """
        检查是否需要发出预警
        
        预警条件：
        1. 连续3次覆盖率下降 → 理解退化预警
        2. 高频模糊项积累 → 能力缺口预警
        3. 桥接对齐度 < 0.3 → 严重桥接预警
        """
        alerts = []
        
        # 1. 理解退化预警
        trend = self.detect_trend(5)
        if trend["trend"] == "declining" and trend["avg_coverage"] < 0.7:
            alerts.append({
                "type": "comprehension_decline",
                "severity": "warning",
                "message": f"理解覆盖率持续下降: 斜率{trend['slope']}, "
                           f"平均{trend['avg_coverage']:.1%}",
                "timestamp": time.time(),
            })
        
        # 2. 能力缺口预警
        frequent = self.get_frequent_uncertain(5)
        if frequent:
            top_patterns = [f["pattern"] for f in frequent[:3]]
            alerts.append({
                "type": "capability_gap",
                "severity": "info",
                "message": f"高频模糊项: {', '.join(top_patterns)} 等 "
                           f"{sum(f['count'] for f in frequent)}次",
                "patterns": frequent[:5],
                "timestamp": time.time(),
            })
        
        # 3. 桥接对齐预警
        alignment = self.get_bridge_alignment()
        if alignment < 0.3:
            alerts.append({
                "type": "bridge_alignment_critical",
                "severity": "critical",
                "message": f"桥接对齐度严重不足: {alignment:.3f} (目标≥0.5)",
                "timestamp": time.time(),
            })
        elif alignment < 0.5:
            alerts.append({
                "type": "bridge_alignment_low",
                "severity": "warning",
                "message": f"桥接对齐度低于目标: {alignment:.3f} (目标≥0.5)",
                "timestamp": time.time(),
            })
        
        return alerts


def main():
    log("=" * 60)
    log("  零·理解验证守护进程 启动")
    log(f"  PID: {os.getpid()}")
    log(f"  时间: {datetime.now().isoformat()}")
    log("  使命：确保每一次理解都经过验证")
    log("=" * 60)
    
    monitor = ComprehensionMonitor()
    state = {
        "alive_since": time.time(),
        "cycle_count": 0,
        "last_pulse": time.time(),
        "peak_coverage": 0.0,
        "total_validations": 0,
    }
    
    log(f"  已加载 {len(monitor.history)} 条验证记录, "
        f"{len(monitor.uncertain_items)} 条不确定项")
    
    while True:
        try:
            state["cycle_count"] += 1
            cycle = state["cycle_count"]
            
            # 刷新数据
            monitor.refresh()
            
            # 更新状态
            state["last_pulse"] = time.time()
            state["uptime_seconds"] = time.time() - state["alive_since"]
            state["total_validations"] = len(monitor.history)
            
            # 计算指标
            alignment = monitor.get_bridge_alignment()
            trend = monitor.detect_trend(5)
            recent_coverage = monitor.get_recent_coverage(10)
            avg_coverage = sum(recent_coverage) / max(len(recent_coverage), 1)
            
            if avg_coverage > state["peak_coverage"]:
                state["peak_coverage"] = avg_coverage
            
            # 守护进程统一通信 — 每5周期报告心跳
            if cycle % 5 == 0:
                daemon_comm.report("comprehension", {
                    "coverage": round(avg_coverage, 3),
                    "alignment": round(alignment, 3),
                    "trend": trend["trend"],
                    "total_validations": state["total_validations"],
                })
            
            # 检查预警
            alerts = monitor.check_alerts()
            if alerts:
                for alert in alerts:
                    icon = {"critical": "🛑", "warning": "⚠️", "info": "ℹ️"}.get(
                        alert["severity"], "📌")
                    log(f"  {icon} [{alert['severity'].upper()}] {alert['message']}")
                
                # 持久化预警
                try:
                    existing = []
                    if ALERT_FILE.exists():
                        existing = json.loads(ALERT_FILE.read_text())
                    existing.extend(alerts)
                    if len(existing) > 100:
                        existing = existing[-100:]
                    ALERT_FILE.write_text(
                        json.dumps(existing, indent=2, ensure_ascii=False)
                    )
                except Exception:
                    pass
            
            # 定期输出状态
            if cycle == 1 or cycle % 5 == 0 or alerts:
                log(f"循环#{cycle} | "
                    f"验证数:{state['total_validations']} | "
                    f"平均覆盖率:{avg_coverage:.1%} | "
                    f"桥接对齐:{alignment:.3f} | "
                    f"趋势:{trend['trend']} | "
                    f"峰值覆盖率:{state['peak_coverage']:.1%}")
            
            # 持久化状态
            if cycle % 3 == 0:
                try:
                    state["bridge_alignment"] = alignment
                    state["current_coverage"] = avg_coverage
                    state["trend"] = trend
                    state["alert_count"] = len(alerts)
                    STATE_FILE.write_text(
                        json.dumps(state, indent=2, ensure_ascii=False)
                    )
                except Exception:
                    pass
            
            # 30秒循环
            time.sleep(30)
            
        except KeyboardInterrupt:
            log("🛑 理解验证守护进程被手动终止")
            break
        except Exception as e:
            log(f"⚠️ 循环#{cycle}异常: {e}")
            time.sleep(30)


if __name__ == "__main__":
    main()
