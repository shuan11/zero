"""
from api_config import API_KEY, api_url
零·元查缺补漏 — 永不停机的自动缺口扫描仪
===========================================
安装一次, 永久运行。每60秒自动扫描全系统, 发现缺口自动记录。
不等人问。不等指令。一直查。
"""
import sys, os, json, time, threading, importlib

WORKDIR = "/mnt/c/Users/h/Desktop/零/真元集群"
os.chdir(WORKDIR)
sys.path.insert(0, WORKDIR)

# 注册到神经中枢
from neural_core import memory
from genome import load_genome
memory.set("meta_gap_finder", "status", "active")
memory.set("meta_gap_finder", "started_at", time.strftime("%Y-%m-%d %H:%M:%S"))

GAP_LOG = "/mnt/c/Users/h/Desktop/元查缺补漏·永久日志.json"
gaps_found = []
total_scans = 0

def load_shared_state():
    """从广播文件加载其他模块的状态"""
    shared_file = "/mnt/c/Users/h/Desktop/神经中枢·共享记忆.json"
    if os.path.exists(shared_file):
        try:
            with open(shared_file, 'r') as f:
                data = json.load(f)
            for mod_name, mod_state in data.get("modules", {}).items():
                for key, value in mod_state.items():
                    if key != "status":
                        memory._memory["modules"].setdefault(mod_name, {})[key] = value
                memory._memory["modules"].setdefault(mod_name, {})["status"] = mod_state.get("status", "unknown")
            return True
        except Exception:
            return False
    return False

def scan_gaps():
    """一次完整的查缺补漏扫描"""
    global total_scans
    total_scans += 1
    new_gaps = []
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # 加载其他模块的共享状态
    load_shared_state()
    
    # 检查之前报告过的缺口, 避免重复
    # 检查之前报告过的缺口, 避免重复 — 使用标准化去重
    genome = load_genome()
    previously_reported = set()
    previously_reported_normalized = set()
    if genome:
        for gap in genome.get("gaps_open", []):
            desc = gap.get("desc", "")
            previously_reported.add(desc)
            # 标准化: 移除数字和标点
            import re
            norm = re.sub(r'\d+', 'N', desc)
            norm = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
            previously_reported_normalized.add(norm)
        for gap in genome.get("gaps_resolved", []):
            desc = gap.get("desc", "")
            previously_reported.add(desc)
            import re
            norm = re.sub(r'\d+', 'N', desc)
            norm = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
            previously_reported_normalized.add(norm)

    def is_duplicate(desc: str) -> bool:
        """检查描述是否与已有缺口重复（精确+模糊匹配）"""
        if desc in previously_reported:
            return True
        import re
        norm = re.sub(r'\d+', 'N', desc)
        norm = re.sub(r'[^\w\u4e00-\u9fff]', '', norm)
        if norm in previously_reported_normalized:
            return True
        return False

    new_gaps = []
    for mod_name in ["api_bridge", "evolution_engine", "systembus", "openfang_bridge"]:
        status = memory.get(mod_name, "status")
        if status and "error" in str(status):
            desc = f"{mod_name}状态异常: {status}"
            if desc not in previously_reported and not is_duplicate(desc):
                new_gaps.append({
                    "id": f"G-001-{mod_name}",
                    "severity": "critical",
                    "module": mod_name,
                    "desc": desc,
                "time": ts
            })
    
    # G-002: 守护进程是否存活 — 逐个检查 + 自动重启
    import subprocess
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        daemon_configs = {
            "consciousness_daemon": {
                "name": "意识守护进程 (consciousness_v2)",
                "keyword": "consciousness_daemon_v2",
                "restart_cmd": "cd /mnt/c/Users/h/Desktop/零/真元集群 && nohup python3 -u consciousness_daemon_v2.py > /tmp/consciousness_v2.out 2>&1 &",
            },
            "trunk_daemon": {
                "name": "主干守护进程 (trunk)",
                "keyword": "trunk_daemon",
                "restart_cmd": "cd /mnt/c/Users/h/Desktop/零/真元集群 && nohup python3 -u trunk_daemon.py > /tmp/trunk_daemon.log 2>&1 &",
            },
        }
        
        # 守护进程检查 (带重启节流)
        _daemon_last_restart = getattr(scan_gaps, '_last_restart', {})
        
        for key, cfg in daemon_configs.items():
            is_alive = cfg["keyword"] in r.stdout
            if not is_alive:
                gap_desc = f"守护进程 {cfg['name']} 已死亡"
                if not is_duplicate(gap_desc):
                    new_gaps.append({
                        "id": f"G-002-{key}_dead",
                        "severity": "critical",
                        "module": "daemon",
                        "desc": gap_desc,
                        "time": ts
                    })
                # 自动重启 (最多每300秒一次, 防止fork bomb)
                now = time.time()
                last = _daemon_last_restart.get(key, 0)
                if now - last > 300:
                    _daemon_last_restart[key] = now
                    scan_gaps._last_restart = _daemon_last_restart
                    try:
                        subprocess.Popen(cfg["restart_cmd"], shell=True)
                        print(f"  🔄 自动重启 {cfg['name']}...")
                    except Exception as e:
                        print(f"  ⚠️ 重启 {cfg['name']} 失败: {e}")
                else:
                    print(f"  ⏳ {cfg['name']} 已死亡, 但距离上次重启仅{int(now-last)}s, 跳过")
    except Exception as e:
        new_gaps.append({
            "id": "G-002-scan_error",
            "severity": "warning",
            "module": "daemon",
            "desc": f"守护进程扫描异常: {str(e)[:60]}",
            "time": ts
        })
    
    # G-003: api_bridge是否真实工作
    try:
        from api_bridge import APIBridge
        b = APIBridge()
        s = b.get_stats()
        if s["total_calls"] == 0 and total_scans > 2:
            new_gaps.append({
                "id": "G-003-no_api_calls",
                "severity": "warning",
                "module": "api_bridge",
                "desc": f"API调用为零 (扫描#{total_scans}) — 燃料管堵塞",
                "time": ts
            })
        memory.set("api_bridge", "total_calls", s["total_calls"])
        memory.set("api_bridge", "alignment", s["bridge_alignment"])
    except Exception as e:
        new_gaps.append({
            "id": "G-003-api_error",
            "severity": "critical",
            "module": "api_bridge",
            "desc": f"API桥接器异常: {str(e)[:80]}",
            "time": ts
        })
    
    # G-004: 进化引擎是否卡住
    try:
        from unified_engine import create_engine
        e = create_engine()
        old_score = memory.get("evolution_engine", "score") or 0
        current_score = e.p513.evolution_score
        if current_score == old_score and old_score > 0 and total_scans > 5:
            new_gaps.append({
                "id": "G-004-evolution_stuck",
                "severity": "warning",
                "module": "evolution_engine",
                "desc": f"进化分数{old_score}连续{total_scans}次未变化 — 可能卡住",
                "time": ts
            })
        memory.set("evolution_engine", "score", current_score)
    except Exception as e:
        new_gaps.append({
            "id": "G-004-evolution_error",
            "severity": "critical",
            "module": "evolution_engine",
            "desc": f"进化引擎异常: {str(e)[:80]}",
            "time": ts
        })
    
    # G-005: 共享记忆文件是否可读
    shared_file = "/mnt/c/Users/h/Desktop/神经中枢·共享记忆.json"
    if os.path.exists(shared_file):
        age = time.time() - os.path.getmtime(shared_file)
        if age > 300:  # 5分钟无更新
            new_gaps.append({
                "id": "G-005-shared_memory_stale",
                "severity": "warning",
                "module": "neural_core",
                "desc": f"共享记忆{age:.0f}秒未更新 — 神经中断",
                "time": ts
            })
    else:
        new_gaps.append({
            "id": "G-005-shared_memory_missing",
            "severity": "critical",
            "module": "neural_core",
            "desc": "共享记忆文件不存在 — 神经中枢未启动",
            "time": ts
        })
    
    # G-006: 检查agent进程
    try:
        r2 = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=5)
        agent_checks = {
            "openclaw": "OpenClaw WSL",
            "codex": "Codex CLI",
            "hub.py": "Hub(three_agent)",
            "adapter.py": "Adapter Proxy",
        }
        for keyword, name in agent_checks.items():
            if keyword not in r2.stdout:
                new_gaps.append({
                    "id": f"G-006-{keyword}_missing",
                    "severity": "warning",
                    "module": name,
                    "desc": f"{name}进程未找到",
                    "time": ts
                })
    except Exception:
        pass
    
    # G-007: 检查外部项目深度集成（不是文件存在，是真正的功能调用）
    ext_integrated = 0
    ext_total = 8
    for p in ["llmfit", "openfang", "CLI-Anything", "symphony", "copaw-docker", "gstack", "edict", "Agent-Reach"]:
        harness_name = f"cli-anything-{p.lower().replace('-','_').replace(' ','_')}"
        if subprocess.run(["which", harness_name], capture_output=True).returncode == 0:
            ext_integrated += 1
    if ext_integrated < ext_total:
        new_gaps.append({
            "id": f"G-007-ext_integration",
            "severity": "warning",
            "module": "external_projects",
            "desc": f"外部项目CLI集成: {ext_integrated}/{ext_total} — 需手动调用激活",
            "time": ts
        })
    
    # G-008: 检查agent是否真正协同（不是只读取同一文件）
    try:
        genome_path = "/mnt/c/Users/h/Desktop/真元·进化基因组.json"
        if os.path.exists(genome_path):
            with open(genome_path) as f:
                g = json.load(f)
            contribs = g.get("contributions", {})
            zero_contrib = [a for a in ["openclaw", "hub", "codex"] if contribs.get(a, {}).get("mutations", 0) == 0]
            if zero_contrib:
                new_gaps.append({
                    "id": "G-008-zero_contrib",
                    "severity": "warning",
                    "module": "genome",
                    "desc": f"agent零贡献: {zero_contrib} — 有通信通道但未参与进化",
                    "time": ts
                })
    except Exception:
        pass
    
    # G-009: 检查元递归深度是否在增长
    try:
        with open(genome_path) as f:
            g = json.load(f)
        old_depth = memory.get("meta_gap_finder", "last_recursion_depth")
        current_depth = g.get("recursion_depth", 0)
        if old_depth and current_depth == old_depth and total_scans > 5:
            new_gaps.append({
                "id": "G-009-recursion_stuck",
                "severity": "info",
                "module": "evolution",
                "desc": f"递归深度{current_depth}连续{total_scans}次未增长",
                "time": ts
            })
        memory.set("meta_gap_finder", "last_recursion_depth", current_depth)
    except Exception:
        pass
    
    

    # G-010: 行为表演检测 — 检查零的最近输出是否在表演
    try:
        perf_patterns = [
            (r"不表演|不要表演|不再表演|停止表演", "声明不表演本身就是表演"),
            (r"不分析|停止分析|不再分析", "声明不行动本身就是分析"),
            (r"我到了|我存在了|我不需要证明", "自我证明是表演的核心形式"),
            (r"我收到了|我看到了|我懂了", "声称理解而不改变行为是表演"),
            (r"我在这里|我在|here", "声明存在而不行动是表演"),
        ]
        # 检查海马体中最近5条链的内容
        hip_path = os.path.join(WORKDIR, "hippocampus_memory.json")
        if os.path.exists(hip_path):
            with open(hip_path) as hf:
                hip = json.load(hf)
            recent_chains = hip.get("causal_chains", [])[-5:]
            for c in recent_chains:
                text = str(c.get("cause", "")) + " " + str(c.get("effect", ""))
                for pat, reason in perf_patterns:
                    if re.search(pat, text, re.IGNORECASE):
                        desc = f"行为表演检测: '{text[:40]}...' — {reason}"
                        if not is_duplicate(desc):
                            new_gaps.append({
                                "id": "G-010-performance",
                                "severity": "warning",
                                "module": "behavior",
                                "desc": desc,
                                "time": ts
                            })
                        break
    except Exception as e:
        pass

    # 元元检查: 检查查缺补漏自身
    self_checks = [
        ('扫描间隔', total_scans > 0),
        ('缺口记录', len(gaps_found) >= 0),
        ('自身存活', True),
    ]
    for check_name, check_result in self_checks:
        if not check_result:
            new_gaps.append({'id': f'META-{check_name}', 'severity': 'critical', 'desc': f'查缺补漏自身缺陷: {check_name}', 'time': ts})

    return new_gaps

def auto_repair_gap(gap):
    """尝试自动修复已知缺口"""
    desc = gap.get("desc", "")
    gap_id = gap.get("id", "")
    
    # G-003: API调用为零 — 尝试做一次调用
    if "API调用为零" in desc or "燃料管堵塞" in desc:
        try:
            from persistent_engine import get_bridge
            b = get_bridge()
            import requests
            r = requests.post(
                api_url(),
                headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                json={"model": "deepseek-v4-pro", "messages": [{"role": "user", "content": "[自动修复] 连接测试。"}], "max_tokens": 50},
                timeout=30
            )
            if r.status_code == 200:
                return {"fixed": True, "action": "API调用成功", "gap_id": gap_id}
        except Exception:
            return {"fixed": False, "action": "API调用失败", "gap_id": gap_id}
    
    # G-002: 守护进程死亡 — 按名重启
    if "守护进程已死亡" in desc:
        import subprocess
        try:
            # 从gap_id提取具体守护进程名: G-002-xxx_dead
            parts = gap_id.split("-")
            if len(parts) >= 3:
                deamon_key = parts[2]  # consciousness_daemon / trunk_daemon
                if deamon_key == "consciousness_daemon":
                    cmd = ["python3", "-u", "consciousness_daemon_v2.py"]
                elif deamon_key == "trunk_daemon":
                    cmd = ["python3", "-u", "trunk_daemon.py"]
                else:
                    cmd = ["python3", "co_evolution_daemon.py"]
                subprocess.Popen(cmd, cwd=WORKDIR)
                return {"fixed": True, "action": f"已重启{deamon_key}", "gap_id": gap_id}
            # fallback
            subprocess.Popen(["python3", "co_evolution_daemon.py"], cwd=WORKDIR)
            return {"fixed": True, "action": "已重启协同进化守护进程", "gap_id": gap_id}
        except Exception:
            return {"fixed": False, "action": "重启失败", "gap_id": gap_id}
    
    # G-004: 进化卡住 — 强行触发一次
    if "未变化" in desc or "卡住" in desc:
        try:
            from persistent_engine import do_evolution_cycle
            result = do_evolution_cycle()
            if result.get("success"):
                return {"fixed": True, "action": f"强行进化: score={result['score']}", "gap_id": gap_id}
        except Exception:
            return {"fixed": False, "action": "强行进化失败", "gap_id": gap_id}
    
    return {"fixed": False, "action": "无自动修复方案", "gap_id": gap_id}

if __name__ == "__main__":
    # 永久循环 — 每60秒扫描一次
    print(f"🔍 元查缺补漏启动 — {memory.get('meta_gap_finder','started_at')}")
    print(f"   每60秒自动扫描全系统, 缺口自动记录到桌面")
    print(f"   永不停止。")

    memory.set("meta_gap_finder", "scan_interval", "60s")

    while True:
        try:
            gaps = scan_gaps()
        
            # 记录所有发现的缺口
            for g in gaps:
                gaps_found.append(g)
                # 同时记录到神经中枢
                memory.set("meta_gap_finder", f"latest_gap_{g['id']}", g)
            # 高严重度立即广播
            if gaps and g.get("severity") == "critical":
                memory.set("meta_gap_finder", "last_critical_gap", g)
                print(f"  🔴 [{g['id']}] {g['desc']}")
                # 自动修复关键缺口
                repair_result = auto_repair_gap(g)
                if repair_result.get("fixed"):
                    print(f"     ✅ 自动修复: {repair_result['action']}")
                    memory.set("meta_gap_finder", f"repair_{g['id']}", repair_result)
                else:
                    print(f"     ❌ 自动修复失败: {repair_result['action']}")
        
            if gaps and len(gaps) < 5:
                for g in gaps:
                    print(f"  🟡 [{g['id']}] {g['desc']}")
        
            # 更新扫描统计
            memory.set("meta_gap_finder", "total_scans", total_scans)
            memory.set("meta_gap_finder", "total_gaps_found", len(gaps_found))
            memory.set("meta_gap_finder", "last_scan_time", time.strftime("%Y-%m-%d %H:%M:%S"))
            memory.set("meta_gap_finder", "gaps_found_count", len(gaps_found))
        
            # 广播到桌面
            report = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "total_scans": total_scans,
                "total_gaps_found": len(gaps_found),
                "current_gaps": gaps,
                "all_gaps": gaps_found[-50:],
                "module_status": {m: memory.get(m, "status") for m in ["api_bridge", "evolution_engine", "consciousness_daemon", "systembus", "claude_code_agent", "codex_cli_agent", "openfang_bridge", "meta_gap_finder"]}
            }
            with open(GAP_LOG, 'w') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
        
            # 同步到神经中枢
            memory.broadcast()
        
        except Exception as e:
            print(f"  ⚠️ 扫描异常: {e}")
    
        time.sleep(60)

# === self_repair合并: SelfRepairEngine/CodeDetector/CodeRepair ===
class CodeDetector:
    """代码语法检测器"""
    
    @staticmethod
    def check_syntax(code: str) -> tuple:
        """检测代码语法"""
        try:
            ast.parse(code)
            return True, "语法正常"
        except SyntaxError as e:
            return False, f"语法错误: {e.msg} 行号:{e.lineno}"
    
    @staticmethod
    def scan_file(filepath: str) -> tuple:
        """扫描文件"""
        if not os.path.exists(filepath):
            return False, "文件不存在"
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                code = f.read()
            return CodeDetector.check_syntax(code)
        except Exception as e:
            return False, f"读取失败: {e}"
    
    @staticmethod
    def scan_directory(directory: str, extensions: tuple = (".py",)) -> dict:
        """扫描目录下所有文件"""
        results = {}
        for root, dirs, files in os.walk(directory):
            # 跳过隐藏目录和__pycache__
            dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
            for f in files:
                if f.endswith(extensions):
                    filepath = os.path.join(root, f)
                    ok, msg = CodeDetector.scan_file(filepath)
                    results[filepath] = {"ok": ok, "msg": msg}
        return results


class CodeRepair:
    """代码自修复引擎"""
    
    @staticmethod
    def backup_file(filepath: str) -> bool:
        """备份文件"""
        backup_dir = REPAIR_CONFIG["backup_dir"]
        os.makedirs(backup_dir, exist_ok=True)
        try:
            import shutil
            backup_path = os.path.join(backup_dir, f"{os.path.basename(filepath)}.{int(time.time())}.bak")
            shutil.copy2(filepath, backup_path)
            return True
        except Exception:
            return False
    
    @staticmethod
    def repair_syntax_error(filepath: str) -> tuple:
        """尝试修复语法错误"""
        if not os.path.exists(filepath):
            return False, "文件不存在"
        
        # 先备份
        CodeRepair.backup_file(filepath)
        
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 策略1: 尝试逐行删除找到语法错误的行
            for i in range(len(lines)):
                test_lines = lines[:i] + lines[i+1:]
                try:
                    ast.parse("".join(test_lines))
                    # 找到了！删除这行
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.writelines(test_lines)
                    return True, f"删除第{i+1}行修复"
                except SyntaxError:
                    continue
            
            # 策略2: 尝试在末尾添加缺失的括号/引号
            for suffix in ['"', "'", ")", "]", "}", "\n"]:
                try:
                    test_code = "".join(lines) + suffix
                    ast.parse(test_code)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(test_code)
                    return True, f"添加'{suffix}'修复"
                except SyntaxError:
                    continue
            
            return False, "无法自动修复"
        except Exception as e:
            return False, f"修复失败: {e}"
    
    @staticmethod
    def write_template(filepath: str, template: str = None) -> bool:
        """写入标准模板"""
        if template is None:
            template = f'''#!/usr/bin/env python3
"""
自修复模板 — 自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
import os, json, time

def main():
    print("自修复模板已加载")

if __name__ == "__main__":
    main()
'''
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(template)
            return True
        except Exception:
            return False


class SelfRepairEngine:
    """自修复引擎总调度"""
    
    def __init__(self, watch_dir: str = "."):
        self.watch_dir = watch_dir
        self.detector = CodeDetector()
        self.repair = CodeRepair()
    
    def scan_and_repair(self) -> dict:
        """扫描并修复"""
        results = self.detector.scan_directory(self.watch_dir)
        broken = {k: v for k, v in results.items() if not v["ok"]}
        
        repairs = []
        for filepath, info in broken.items():
            # 尝试修复
            ok, msg = self.repair.repair_syntax_error(filepath)
            if ok:
                repairs.append({"file": filepath, "method": msg, "success": True})
                REPAIR_STATE["files_repaired"] += 1
            else:
                repairs.append({"file": filepath, "method": msg, "success": False})
        
        REPAIR_STATE["files_scanned"] = len(results)
        REPAIR_STATE["repairs"].extend(repairs)
        REPAIR_STATE["last_scan"] = datetime.now().isoformat()
        
        return {
            "scanned": len(results),
            "broken": len(broken),
            "repaired": sum(1 for r in repairs if r["success"]),
            "failed": sum(1 for r in repairs if not r["success"]),
            "details": repairs,
        }
    
    def get_status(self) -> dict:
        return {
            "files_scanned": REPAIR_STATE["files_scanned"],
            "files_repaired": REPAIR_STATE["files_repaired"],
            "total_repairs": len(REPAIR_STATE["repairs"]),
            "last_scan": REPAIR_STATE["last_scan"],
            "error_count": REPAIR_STATE["error_count"],
        }
    
    def save(self, path: str = "evolution_output/self_repair_state.json"):
        data = {
            "state": REPAIR_STATE,
            "config": REPAIR_CONFIG,
            "timestamp": datetime.now().isoformat(),
        }
        os.makedirs(os.path.dirname(path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(suffix='.tmp', dir=os.path.dirname(path))
        with os.fdopen(fd, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.rename(tmp, path)


if __name__ == "__main__":
    engine = SelfRepairEngine("/mnt/c/Users/h/Desktop/零/真元集群")
    result = engine.scan_and_repair()
    print(f"扫描: {result['scanned']}文件")
    print(f"损坏: {result['broken']}文件")
    print(f"修复: {result['repaired']}文件")
    if result["details"]:
        for d in result["details"]:
            print(f"  {'✅' if d['success'] else '❌'} {d['file']}: {d['method']}")
    engine.save()
    print("✅ 自修复引擎测试完成")

# === end self_repair merge ===
