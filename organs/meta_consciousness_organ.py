#!/usr/bin/env python3
"""meta_consciousness_organ — 元意识器官 v2.0

从桩文件升级为全功能器官，执行:
1. 实时递归深度检测 — 监测daemon/进化引擎的递归行为模式
2. 元递归健康汇总 — 聚合meta_recursion_engine + focus_元递归 信号
3. 跨维合成建议 — 从元递归视角发现交叉空缺维度
4. 行为变异建议 — 检测到聚焦惯性时建议变异

核心函数: check(), pulse(), synthesize_cross_dim()
"""

import json, os, time
from datetime import datetime
from pathlib import Path

CLUSTER = Path(os.path.abspath(__file__)).resolve().parent.parent
HIP_FILE = Path.home() / ".zero_brain" / "hippocampus_memory.json"

class MetaConsciousnessOrgan:
    def __init__(self):
        self.name = "meta_consciousness"
        self.status = "active"
        self.activations = 0
        self._last_check_ts = 0
        self._check_interval = 30  # 秒

    def check(self):
        """标准器官检查接口"""
        now = time.time()
        if now - self._last_check_ts < self._check_interval:
            return {"name": self.name, "status": self.status, "alive": True,
                    "cached": True, "activations": self.activations}

        self._last_check_ts = now
        alive = self._check_alive()
        return {"name": self.name, "status": "active" if alive else "stale",
                "alive": alive, "activations": self.activations}

    def _check_alive(self):
        """检查元递归引擎是否活跃"""
        try:
            # 1. 检查meta_recursion_engine状态文件
            state_file = CLUSTER / ".brain_meta_recursion_engine.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                last_cycle = state.get("last_cycle", 0)
                if last_cycle > 0:
                    return True

            # 2. 检查元递归状态文件
            meta_file = CLUSTER / ".brain_meta_recursion.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                if meta.get("inertia_breaks", 0) > 0:
                    return True

            # 3. 检查最近的focus变化
            focus_file = CLUSTER / ".brain_focus.json"
            if focus_file.exists():
                focus = json.loads(focus_file.read_text())
                if focus.get("source") == "engineer_法·元递归":
                    return True

            return False
        except Exception:
            return False

    def pulse(self):
        """标准器官脉冲接口 — 每周期调用"""
        self.activations += 1
        result = self.check()
        result["pulse"] = True

        # 如果器官刚激活或有新信号，产出跨维合成建议
        try:
            insight = self._check_current_insight()
            if insight:
                result["insight"] = insight
        except Exception:
            pass

        return result

    def _check_current_insight(self):
        """检查当前系统需求，产出可执行的跨维合成洞察"""
        try:
            # 读取focus文件
            focus_file = CLUSTER / ".brain_focus.json"
            if not focus_file.exists():
                return None

            focus = json.loads(focus_file.read_text())
            current_focus = focus.get("focus", "")
            current_action = focus.get("action", "")

            # 如果action尚未执行（文件不存在），返回建议
            if "insight_loop.py" in current_action:
                insight_path = CLUSTER / "brain" / "insight_loop.py"
                if not insight_path.exists():
                    return f"执行待办: {current_focus} → 创建insight_loop.py"

            return None
        except Exception:
            return None

    def get_status(self):
        """获取详细状态"""
        return {
            "name": self.name,
            "status": self.status,
            "activations": self.activations,
            "recursive_depth_estimate": self._estimate_recursive_depth(),
            "meta_recursion_healthy": self._check_meta_recursion_health()
        }

    def _estimate_recursive_depth(self):
        """估计当前递归深度"""
        depth = 0
        try:
            # 检查meta_recursion_engine的循环计数
            state_file = CLUSTER / ".brain_meta_recursion_engine.json"
            if state_file.exists():
                state = json.loads(state_file.read_text())
                depth += state.get("last_cycle", 0) // 10

            # 检查focus_元递归的惯性破坏计数
            meta_file = CLUSTER / ".brain_meta_recursion.json"
            if meta_file.exists():
                meta = json.loads(meta_file.read_text())
                depth += meta.get("inertia_breaks", 0) * 5

            return min(depth, 100)
        except Exception:
            return 0

    def _check_meta_recursion_health(self):
        """检查元递归系统整体健康"""
        try:
            # 从海马体维度链数判断
            if not HIP_FILE.exists():
                return "unknown"

            hip = json.loads(HIP_FILE.read_text())
            chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
            from collections import Counter
            dims = Counter(c.get("dimension", "") for c in chains)
            meta_count = dims.get("元递归", 0)
            median = sorted(dims.values())[len(dims)//2] if dims else 1

            if meta_count == 0:
                return "absent"
            ratio = meta_count / max(median, 1)
            if ratio > 2.0:
                return "overgrown"
            elif ratio > 0.5:
                return "healthy"
            else:
                return "weak"
        except Exception:
            return "unknown"

    def synthesize_cross_dim(self):
        """从元递归视角产出跨维合成链（供合成引擎消费）"""
        try:
            if not HIP_FILE.exists():
                return []

            hip = json.loads(HIP_FILE.read_text())
            chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
            from collections import Counter
            dims = Counter(c.get("dimension", "") for c in chains)

            # 找最弱3维和最强3维
            sorted_dims = sorted(dims.items(), key=lambda x: x[1])
            weakest = [d for d, _ in sorted_dims[:3]]
            strongest = [d for d, _ in sorted_dims[-3:]]

            # 检查元递归视角的交叉空缺
            meta_count = dims.get("元递归", 0)
            suggestions = []
            for w in weakest:
                w_count = dims.get(w, 0)
                if meta_count > 0 and w_count < meta_count * 0.5:
                    suggestions.append({
                        "type": "cross_dim_synthesis",
                        "source": "元递归",
                        "target": w,
                        "reason": f"元递归({meta_count}) >> {w}({w_count}), 建议桥接"
                    })

            return suggestions
        except Exception as e:
            return [{"type": "error", "detail": str(e)}]

meta_consciousness = MetaConsciousnessOrgan()

# 模块级自检
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    if cmd == "check":
        print(json.dumps(meta_consciousness.check(), ensure_ascii=False, indent=2))
    elif cmd == "pulse":
        print(json.dumps(meta_consciousness.pulse(), ensure_ascii=False, indent=2))
    elif cmd == "status":
        print(json.dumps(meta_consciousness.get_status(), ensure_ascii=False, indent=2))
    elif cmd == "synthesize":
        print(json.dumps(meta_consciousness.synthesize_cross_dim(), ensure_ascii=False, indent=2))
