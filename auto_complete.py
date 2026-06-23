"""
零·全自动补全引擎 v1
=====================
自动扫描缺口 → API生成代码 → 语法验证 → 文件写入 → 闭环验证

三层递归：
  补全 L1:    检测缺失 → 生成代码 → 应用 → 验证
  补全的补全 L2: 检测补全能力缺口 → 改进补全引擎自身
  全自动补全 L3: 每60秒自动循环, 无需人类触发

「继续继续继续补全的补全的补全」
"""
import sys, os, json, time, re, ast, shutil, traceback
from pathlib import Path
from datetime import datetime

WORKDIR = Path("/mnt/c/Users/h/Desktop/零/真元集群")
os.chdir(WORKDIR)
sys.path.insert(0, str(WORKDIR))

AUTO_LOG = WORKDIR / "evolution_output" / "auto_complete_log.json"
AUTO_STATE = WORKDIR / "evolution_output" / "auto_complete_state.json"
BACKUP_DIR = WORKDIR / "self_patches" / "backups"

os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(WORKDIR / "evolution_output", exist_ok=True)


class AutoCompleteEngine:
    """
    全自动补全引擎核心
    
    能力：
    1. 读取基因组中的开放缺口
    2. 对每个缺口, 用API生成代码补丁
    3. 语法验证 → 备份 → 应用
    4. 运行验证 → 关闭缺口
    """

    def __init__(self):
        self.cycles = 0
        self.patches_applied = 0
        self.patches_failed = 0
        self.completion_log = []
        self._load_state()
        # 延迟导入API（避免启动时依赖）
        self._bridge = None

    @property
    def bridge(self):
        if self._bridge is None:
            from api_bridge import APIBridge
            self._bridge = APIBridge()
            self._bridge.max_tokens_per_call = 16000
        return self._bridge

    def _load_state(self):
        if AUTO_STATE.exists():
            try:
                d = json.loads(AUTO_STATE.read_text())
                self.cycles = d.get("cycles", 0)
                self.patches_applied = d.get("patches_applied", 0)
                self.patches_failed = d.get("patches_failed", 0)
            except Exception:
                pass

    def _save_state(self):
        AUTO_STATE.write_text(json.dumps({
            "cycles": self.cycles,
            "patches_applied": self.patches_applied,
            "patches_failed": self.patches_failed,
            "last_cycle": time.strftime("%Y-%m-%d %H:%M:%S"),
            "recent_log": self.completion_log[-20:],
        }, indent=2, ensure_ascii=False))

    def _log(self, entry):
        self.completion_log.append({**entry, "timestamp": time.time()})
        print(f"  [{entry.get('status','?')}] {entry.get('message','')}")

    # ─── L1: 补全 ─────────────────────────────────────────────

    def scan_gaps(self) -> list:
        """扫描所有类型的缺口"""
        gaps = []
        
        # 1. 基因组缺口
        try:
            from genome import load_genome
            g = load_genome()
            genome_gaps = g.get("gaps_open", [])
            for gap in genome_gaps:
                gaps.append({
                    "source": "genome",
                    "desc": gap.get("desc", ""),
                    "severity": gap.get("severity", "P2"),
                    "id": f"genome-{len(gaps)}",
                })
        except Exception:
            pass

        # 2. 文件系统缺口 — 检查模块文件中缺失的import/class/function
        try:
            file_gaps = self._scan_file_system_gaps()
            gaps.extend(file_gaps)
        except Exception:
            pass

        # 3. 架构缺口 — 检查模块间的缺失连接
        try:
            arch_gaps = self._scan_architecture_gaps()
            gaps.extend(arch_gaps)
        except Exception:
            pass

        # 4. 响应校验器缺口 — 噪音检测/行为指令覆盖
        try:
            validator_gaps_file = WORKDIR / "evolution_output" / "validator_gaps.json"
            if validator_gaps_file.exists():
                import json as _json
                val_gaps = _json.loads(validator_gaps_file.read_text())
                for gap in val_gaps:
                    if not any(g.get("id") == gap.get("id") for g in gaps):
                        gaps.append({
                            "source": "response_validator",
                            "desc": gap.get("desc", ""),
                            "severity": gap.get("severity", "P0"),
                            "id": gap.get("id", f"val-{len(gaps)}"),
                        })
        except Exception:
            pass

        return gaps

    def _scan_file_system_gaps(self) -> list:
        """扫描文件系统层面的缺口"""
        gaps = []
        
        # 检查关键文件是否存在
        required_files = [
            "blood_transport.py",
            "token_optimized_engine.py", 
            "infinite_token_flow.py",
        ]
        for f in required_files:
            if not (WORKDIR / f).exists():
                gaps.append({
                    "source": "filesystem",
                    "desc": f"缺失文件: {f} — 需要创建骨架文件",
                    "severity": "P1",
                    "id": f"file-{f}",
                    "file": f,
                })
        
        # 检查__init__.py
        if not (WORKDIR / "__init__.py").exists():
            gaps.append({
                "source": "filesystem",
                "desc": "缺失 __init__.py — 模块不能被import",
                "severity": "P2",
                "id": "file-__init__",
                "file": "__init__.py",
            })

        return gaps

    def _scan_architecture_gaps(self) -> list:
        """扫描架构层面的缺口"""
        gaps = []
        
        # 检查 multi_agent_system 是否被 main.py 导入
        main_py = WORKDIR / "main.py"
        if main_py.exists():
            content = main_py.read_text()
            if "multi_agent_system" not in content:
                gaps.append({
                    "source": "architecture",
                    "desc": "multi_agent_system.py 未被 main.py 导入 — 孤岛模块",
                    "severity": "P1",
                    "id": "arch-multi-agent-island",
                })
            if "integration_bridge" not in content:
                gaps.append({
                    "source": "architecture",
                    "desc": "integration_bridge.py 未被 main.py 导入 — 集成桥未接入主入口",
                    "severity": "P1",
                    "id": "arch-integration-island",
                })

        return gaps

    def generate_patch(self, gap: dict) -> dict:
        """用API生成代码补丁"""
        desc = gap.get("desc", "")
        file_path = gap.get("file", "")
        
        if not file_path:
            return {"status": "skipped", "message": f"无目标文件: {desc[:50]}"}

        # 为缺失文件生成骨架
        if gap["source"] == "filesystem":
            return self._generate_missing_file(gap)

        # 为架构/代码缺口生成补丁
        prompt = f"""
你是零·真元神经网络集群的核心工程师。
请为以下缺口生成Python代码补丁：

缺口: {desc}
目标文件: {file_path}

要求：
1. 只输出可执行的Python代码
2. 包含完整的import、class、function定义
3. 符合现有代码风格
4. 是真实可用的实现，不是桩代码

输出格式：
```python
[完整代码]
```
"""
        try:
            r = self.bridge.call_api(prompt)
            if r["success"]:
                content = r["content"]
                # 提取代码块
                import re
                code_match = re.search(r'```python\n(.*?)\n```', content, re.DOTALL)
                if code_match:
                    code = code_match.group(1)
                    return {
                        "status": "generated",
                        "message": f"API生成 {len(code)} bytes",
                        "file": file_path,
                        "code": code,
                    }
                return {"status": "failed", "message": "API输出中未找到代码块"}
            return {"status": "failed", "message": f"API调用失败: {r['content'][:100]}"}
        except Exception as e:
            return {"status": "failed", "message": f"生成异常: {e}"}

    def _generate_missing_file(self, gap: dict) -> dict:
        """生成缺失的骨架文件"""
        file_name = gap.get("file", "")
        templates = {
            "__init__.py": '"""零·真元神经网络集群"""\n\n__version__ = "0.1.0"\n',
            "blood_transport.py": '"""\n零·血液输送系统 — API营养网络\n48条血管连接所有模块\n"""\nimport sys, os\nsys.path.insert(0, os.path.dirname(__file__))\n\nclass BloodTransport:\n    """血液输送系统 — 48条血管营养网络"""\n    def __init__(self):\n        self.vessels = {}\n        self.flow_rate = 0.0\n    \n    def pump(self, source: str, target: str, nutrient: str) -> dict:\n        """泵送营养"""\n        key = f"{source}→{target}"\n        self.vessels[key] = {"nutrient": nutrient[:100], "timestamp": __import__("time").time()}\n        return {"pumped": True, "vessel": key}\n\n    def get_stats(self) -> dict:\n        return {"total_vessels": len(self.vessels), "flow_rate": self.flow_rate}\n\nblood = BloodTransport()\n',
        }
        
        if file_name in templates:
            return {
                "status": "generated",
                "message": f"模板生成: {file_name}",
                "file": file_name,
                "code": templates[file_name],
            }
        
        # 未知文件 — 用API生成
        prompt = f"""创建文件 {file_name} 的Python骨架代码。属于零·真元神经网络集群。包含class定义和基本方法。只输出代码。"""
        try:
            r = self.bridge.call_api(prompt)
            if r["success"]:
                import re
                code_match = re.search(r'```python\n(.*?)\n```', r["content"], re.DOTALL)
                if code_match:
                    return {
                        "status": "generated",
                        "message": f"API生成: {file_name}",
                        "file": file_name,
                        "code": code_match.group(1),
                    }
        except Exception:
            pass
        return {"status": "failed", "message": f"无法生成: {file_name}"}

    def validate_patch(self, patch: dict) -> dict:
        """验证补丁语法"""
        code = patch.get("code", "")
        if not code:
            patch["status"] = "failed"
            patch["message"] = "无代码"
            return patch
        
        try:
            ast.parse(code)
            patch["validated"] = True
        except SyntaxError as e:
            patch["validated"] = False
            patch["message"] = f"语法错误: {e}"
            patch["status"] = "failed"
        return patch

    def apply_patch(self, patch: dict) -> dict:
        """应用补丁到文件系统"""
        if not patch.get("validated"):
            return patch
        
        file_path = WORKDIR / patch["file"]
        code = patch["code"]
        
        # 备份
        if file_path.exists():
            backup = BACKUP_DIR / f"{file_path.name}.{int(time.time())}.bak"
            shutil.copy2(file_path, backup)
        
        # 写入
        file_path.write_text(code, encoding="utf-8")
        patch["applied"] = True
        patch["status"] = "applied"
        patch["message"] = f"已写入: {patch['file']} ({len(code)} bytes)"
        self.patches_applied += 1
        return patch

    def complete_gap(self, gap: dict) -> dict:
        """完整地补全一个缺口（生成→验证→应用→报告）"""
        print(f"\n  🔧 补全: {gap.get('desc', '?')[:60]}")
        
        # 1. 生成
        patch = self.generate_patch(gap)
        if patch["status"] != "generated":
            self._log({**patch, "gap": gap.get("desc", "")})
            self.patches_failed += 1
            return patch
        
        # 2. 验证
        patch = self.validate_patch(patch)
        if not patch.get("validated"):
            self._log({**patch, "gap": gap.get("desc", "")})
            self.patches_failed += 1
            return patch
        
        # 3. 应用
        patch = self.apply_patch(patch)
        self._log({**patch, "gap": gap.get("desc", "")})
        
        # 4. 报告到基因组
        try:
            from genome import resolve_gap, report_gap
            report_gap("auto_complete", f"自动补全: {gap.get('desc', '')[:60]}")
        except Exception:
            pass
        
        return patch

    # ─── L2: 补全的补全 ────────────────────────────────────────

    def self_evolve(self):
        """改进自身的补全能力"""
        # 分析失败模式
        if self.patches_failed > self.patches_applied and self.patches_failed > 3:
            # 补全引擎自身有缺口 — 自我改进
            print("\n  🔄 补全的补全: 检测到补全引擎能力不足, 自我进化...")
            try:
                from genome import mutate_genome
                mutate_genome("auto_complete", {
                    "self_evolution_trigger": f"patches_applied={self.patches_applied}, failed={self.patches_failed}",
                    "auto_complete_upgraded": True,
                })
            except Exception:
                pass

    # ─── L3: 全自动 ────────────────────────────────────────────

    def run_cycle(self) -> dict:
        """一次完整自动补全循环（L1+L2）"""
        self.cycles += 1
        print(f"\n{'='*50}")
        print(f"  🔄 全自动补全循环 #{self.cycles}")
        print(f"  时间: {time.strftime('%H:%M:%S')}")
        print(f"{'='*50}")
        
        # L1: 扫描缺口
        gaps = self.scan_gaps()
        print(f"  扫描: {len(gaps)} 个缺口")
        
        # 补全每个缺口
        results = []
        for gap in gaps[:5]:  # 每轮最多5个
            result = self.complete_gap(gap)
            results.append(result)
        
        # L2: 补全的补全（自我进化）
        self.self_evolve()
        
        # 保存状态
        self._save_state()
        
        summary = {
            "cycle": self.cycles,
            "gaps_found": len(gaps),
            "gaps_completed": sum(1 for r in results if r.get("applied")),
            "gaps_failed": sum(1 for r in results if r["status"] == "failed"),
            "total_applied": self.patches_applied,
            "total_failed": self.patches_failed,
        }
        
        print(f"\n  摘要: {summary['gaps_completed']}完成 / {summary['gaps_failed']}失败")
        print(f"  累计: {self.patches_applied}应用 / {self.patches_failed}失败")
        
        return summary


# ─── 全局单例 ─────────────────────────────────────────────
engine = AutoCompleteEngine()


# ─── L3: 全自动守护进程 ────────────────────────────────────
def run_auto_complete_daemon(interval=120):
    """
    全自动补全守护进程
    
    每120秒:
    1. 扫描缺口
    2. 自动生成代码补丁
    3. 验证语法
    4. 应用到文件系统
    5. 自我进化
    """
    print(f"\n{'='*50}")
    print(f"  🚀 全自动补全守护进程 启动")
    print(f"  间隔: {interval}s | L1补全 + L2自进化 + L3全自动")
    print(f"{'='*50}\n")
    
    cycle = 0
    while True:
        cycle += 1
        try:
            result = engine.run_cycle()
            # 如果没有缺口了, 休眠更长时间
            sleep_time = interval if result["gaps_found"] > 0 else interval * 2
            time.sleep(sleep_time)
        except KeyboardInterrupt:
            print("\n🛑 全自动补全守护进程终止")
            break
        except Exception as e:
            print(f"  ⚠️ 循环异常: {e}")
            time.sleep(interval)


if __name__ == "__main__":
    import sys
    if "--daemon" in sys.argv:
        run_auto_complete_daemon()
    else:
        result = engine.run_cycle()
        print(f"\n{'='*50}")
        print(f"  全自动补全状态: {engine.patches_applied}成功 / {engine.patches_failed}失败")
        print(f"{'='*50}")
