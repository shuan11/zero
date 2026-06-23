#!/usr/bin/env python3
"""
self_evolution_monitor.py — 自进化监控器
========================================
实时监控系统状态，自动发现异常，触发修复机制，生成监控报告。

监控维度：
1. 海马体状态（链数、外部知识比例、异常数）
2. 引擎状态（各引擎是否正常工作）
3. 进化进度（目标完成情况）
4. 系统健康（内存、进程、资源）
"""
import json
import sys
import subprocess
from pathlib import Path
import safe_hip
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
MONITOR_LOG = CLUSTER / "evolution_output" / "monitor_log.json"
BJT = timezone(timedelta(hours=8))

class SelfEvolutionMonitor:
    def __init__(self):
        self.status = {}
        self.alerts = []
        
    def check_hippocampus_state(self):
        """检查海马体状态"""
        try:
            hip = json.load(open(HIP_FILE))
            chains = hip.get("causal_chains", [])
            
            total_chains = len(chains)
            external_chains = len([c for c in chains if '外部世界' in c.get('tags', [])])
            external_ratio = external_chains / total_chains if total_chains > 0 else 0
            
            # 检查异常
            empty_chains = len([c for c in chains if not c.get('content') or len(c.get('content', '').strip()) < 10])
            
            # 检查重复链
            seen = set()
            duplicate_count = 0
            for c in chains:
                content = c.get('content', '')[:80]
                if content in seen:
                    duplicate_count += 1
                seen.add(content)
            
            # 检查熵增链
            entropy_chains = len([c for c in chains if '熵增' in c.get('tags', [])])
            
            state = {
                "total_chains": total_chains,
                "external_chains": external_chains,
                "external_ratio": round(external_ratio, 3),
                "empty_chains": empty_chains,
                "duplicate_chains": duplicate_count,
                "entropy_chains": entropy_chains,
                "timestamp": datetime.now(BJT).isoformat()
            }
            
            # 检查警报条件
            if empty_chains > 50:
                self.alerts.append({
                    "level": "high",
                    "type": "empty_chains",
                    "message": f"空内容链过多: {empty_chains}条",
                    "action": "清理空内容链"
                })
            
            if duplicate_count > 100:
                self.alerts.append({
                    "level": "medium",
                    "type": "duplicate_chains",
                    "message": f"重复链过多: {duplicate_count}条",
                    "action": "清理重复链"
                })
            
            if external_ratio < 0.8:
                self.alerts.append({
                    "level": "medium",
                    "type": "low_external_ratio",
                    "message": f"外部知识比例过低: {external_ratio*100:.1f}%",
                    "action": "增加外部知识采集"
                })
            
            return state
            
        except Exception as e:
            self.alerts.append({
                "level": "high",
                "type": "hippocampus_error",
                "message": f"海马体加载失败: {e}",
                "action": "检查海马体文件"
            })
            return {}
    
    def check_engine_status(self):
        """检查引擎状态"""
        engines = {
            "engine_core": "engine_core.py",
            "evolution_orchestrator": "evolution_orchestrator.py",
            "insight_engine": "insight_engine.py",
            "causal_reasoner": "causal_reasoner.py",
            "causal_predictor": "causal_predictor.py",
            "parameter_predictor": "parameter_predictor.py",
            "unified_evolution_controller": "unified_evolution_controller.py",
            "evolution_goal_manager": "evolution_goal_manager.py",
            "causal_reasoning_enhancer": "causal_reasoning_enhancer.py"
        }
        
        status = {}
        for name, script in engines.items():
            script_path = CLUSTER / script
            if script_path.exists():
                # 检查语法
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "py_compile", str(script_path)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    status[name] = {
                        "exists": True,
                        "syntax_ok": result.returncode == 0,
                        "last_modified": datetime.fromtimestamp(script_path.stat().st_mtime).isoformat()
                    }
                except:
                    status[name] = {
                        "exists": True,
                        "syntax_ok": False,
                        "error": "语法检查失败"
                    }
            else:
                status[name] = {
                    "exists": False,
                    "syntax_ok": False
                }
                self.alerts.append({
                    "level": "medium",
                    "type": "missing_engine",
                    "message": f"引擎文件缺失: {script}",
                    "action": f"创建{script}"
                })
        
        return status
    
    def check_system_health(self):
        """检查系统健康"""
        health = {}
        
        # 检查进程
        try:
            result = subprocess.run(
                ["ps", "aux"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                python_processes = [l for l in lines if 'python' in l.lower() and 'evolution' in l.lower()]
                health["evolution_processes"] = len(python_processes)
        except:
            health["evolution_processes"] = "unknown"
        
        # 检查磁盘空间
        try:
            result = subprocess.run(
                ["df", "-h", str(CLUSTER)],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                if len(lines) > 1:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        health["disk_usage"] = parts[4]
        except:
            health["disk_usage"] = "unknown"
        
        return health
    
    def generate_monitor_report(self):
        """生成监控报告"""
        hippocampus_state = self.check_hippocampus_state()
        engine_status = self.check_engine_status()
        system_health = self.check_system_health()
        
        report = {
            "timestamp": datetime.now(BJT).isoformat(),
            "hippocampus_state": hippocampus_state,
            "engine_status": engine_status,
            "system_health": system_health,
            "alerts": self.alerts,
            "overall_status": "healthy" if not self.alerts else "warning"
        }
        
        # 保存报告
        MONITOR_LOG.parent.mkdir(exist_ok=True)
        
        # 追加到日志文件
        logs = []
        if MONITOR_LOG.exists():
            try:
                with open(MONITOR_LOG) as f:
                    logs = json.load(f)
            except:
                logs = []
        
        logs.append(report)
        
        # 只保留最近100条记录
        if len(logs) > 100:
            logs = logs[-100:]
        
        with open(MONITOR_LOG, 'w') as f:
            json.dump(logs, f, ensure_ascii=False, indent=2)
        
        return report
    
    def auto_repair(self):
        """自动修复"""
        repaired = []
        
        for alert in self.alerts:
            if alert["level"] == "high":
                if alert["type"] == "empty_chains":
                    # 清理空内容链
                    try:
                        hip = json.load(open(HIP_FILE))
                        chains = hip.get("causal_chains", [])
                        clean_chains = [c for c in chains if c.get('content') and len(c.get('content', '').strip()) >= 10]
                        safe_hip.replace_all_chains(clean_chains)
                        repaired.append(f"清理{len(chains) - len(clean_chains)}条空内容链")
                    except Exception as e:
                        repaired.append(f"清理空内容链失败: {e}")
        
        return repaired

if __name__ == "__main__":
    monitor = SelfEvolutionMonitor()
    
    if "--report" in sys.argv:
        report = monitor.generate_monitor_report()
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif "--auto-repair" in sys.argv:
        report = monitor.generate_monitor_report()
        if report["alerts"]:
            print(f"发现{len(report['alerts'])}个警报")
            repaired = monitor.auto_repair()
            print(f"自动修复: {len(repaired)}项")
            for r in repaired:
                print(f"  - {r}")
        else:
            print("系统健康，无需修复")
    elif "--status" in sys.argv:
        hippocampus_state = monitor.check_hippocampus_state()
        print("海马体状态:")
        print(f"  链数: {hippocampus_state.get('total_chains', 0)}")
        print(f"  外部知识: {hippocampus_state.get('external_chains', 0)} ({hippocampus_state.get('external_ratio', 0)*100:.1f}%)")
        print(f"  空内容链: {hippocampus_state.get('empty_chains', 0)}")
        print(f"  重复链: {hippocampus_state.get('duplicate_chains', 0)}")
        print(f"  熵增链: {hippocampus_state.get('entropy_chains', 0)}")
    else:
        # 默认：生成报告
        report = monitor.generate_monitor_report()
        print(f"自进化监控报告已生成")
        print(f"整体状态: {report['overall_status']}")
        print(f"警报数: {len(report['alerts'])}")
        
        if report['alerts']:
            print("\n警报详情:")
            for alert in report['alerts']:
                print(f"  [{alert['level']}] {alert['message']}")
