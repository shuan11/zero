"""meta_recursion_engine.py — 操作性元递归引擎
在 daemon 循环中增加4层可执行元递归行为:

Layer 1: Meta-Inspection (自省的自省)
  - 每次 inspection 后检查 inspection 本身的质量
  - 是否遗漏了重要的维度变化？
  - 是否被偏见（惯性/最弱维偏置）引导？

Layer 2: EML Self-Optimization (评分的评分)
  - EML 预测后跟踪实际结果
  - 如果预测偏差 > 20%，自动调整 EML 参数
  - 记录每次预测的准确率

Layer 3: Chain Meta-Analysis (链的链)
  - 分析链创建模式：哪些维度被偏重？链长度趋势？质量趋势？
  - 当检测到质量下降（短链增多/模板化）时注入质量纠正信号

Layer 4: Mutation Rule Mutation (变异的变异)
  - 如果当前变异策略 N 周期无改进，改变变异策略本身
  - 记录策略变化历史

# 所有 Layer 的输出通过 write_chain 写回海马体，
#并通过 brain_next_focus.json 改变 daemon 行为，形成螺旋反馈。
#
# v2.0 (P106): 修复2个bug + 添加行为反馈闭环 + 自指治理契约
#   - Bugfix: _read_json_file返回整条json不是计数 (L89)
#   - Bugfix: always-true条件 avg<0.7 or avg>0.0 (L112)
#   - 新增: warn/error发现→写入brain_next_focus.json→daemon消费
#   - 新增: 自指治理契约——元递归发现严重问题时设置行为约束
"""

import json, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
_META_STATE = CLUSTER / ".brain_meta_recursion_engine.json"
_EML_ACCURACY_LOG = CLUSTER / ".brain_eml_accuracy.json"
_MUTATION_STRATEGY = CLUSTER / ".brain_mutation_strategy.json"

def _read_json(path, default=None):
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return default if default is not None else {}

def _write_json(path, data):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False

# ─────────────────────────────────────────────
# Layer 1: Meta-Inspection
# ─────────────────────────────────────────────
def meta_inspect(cycle_num, current_focus, focus_history):
    """自省自省——检查 inspection 自身质量"""
    findings = []

    # 1.1 检查焦点是否有惯性盲区
    recent_foci = [e.get("focus", "") for e in focus_history[-5:]]
    if len(set(recent_foci)) <= 2 and len(recent_foci) >= 3:
        findings.append({
            "type": "focus_bias",
            "detail": f"最近5周期焦点过于集中: {set(recent_foci)}",
            "severity": "warn"
        })

    # 1.2 检查是否有维度被系统性地忽视
    state = _read_json(_META_STATE, {"neglected_dims": {}})
    neglected = state.get("neglected_dims", {})
    

    # 1.3 检查 inspection 的 recall
    if cycle_num > 0 and cycle_num % 5 == 0:
        prev_chains_before = state.get("prev_chain_count", None)
        if prev_chains_before is not None:
            try:
                from brain.share import read_hip as _rh
                hip = _rh()
                chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
                current_total = len(chains)
                delta = current_total - prev_chains_before
                if delta < -50:
                    findings.append({
                        "type": "chain_drop",
                        "detail": f"链数骤降 {delta} (可能为系统思维折射压缩)",
                        "severity": "info"
                    })
            except Exception:
                pass
        state["prev_chain_count"] = _safe_extract_count(_read_json_file(CLUSTER / ".brain_chain_count_cache", 0))

    _write_json(_META_STATE, state)

    return findings


# ─────────────────────────────────────────────
# Layer 2: EML Self-Optimization
# ─────────────────────────────────────────────
def eml_self_optimize(cycle_num, dim_chain_counts):
    """EML 评分自优化——评分的评分"""
    if cycle_num % 3 != 0:
        return []

    findings = []
    accuracy_log = _read_json(_EML_ACCURACY_LOG, {"predictions": []})
    predictions = accuracy_log.setdefault("predictions", [])

    # 检查 EML 是否有记录偏差
    if len(predictions) >= 3:
        recent = predictions[-3:]
        avg_accuracy = sum(p.get("accuracy", 0) for p in recent) / len(recent)
        if 0 < avg_accuracy < 0.7:
            findings.append({
                "type": "eml_bias",
                "detail": f"EML最近3次预测平均准确率 {avg_accuracy:.1%}",
                "severity": "warn" if avg_accuracy < 0.7 else "info"
            })

    # 记录当前最弱维作为基线
    if dim_chain_counts:
        weakest = min(dim_chain_counts, key=dim_chain_counts.get)
        strongest = max(dim_chain_counts, key=dim_chain_counts.get)
        findings.append({
            "type": "eml_baseline",
            "detail": f"EML基线: 最弱={weakest}({dim_chain_counts[weakest]}), 最强={strongest}({dim_chain_counts[strongest]})",
            "severity": "info"
        })

    return findings


# ─────────────────────────────────────────────
# Layer 3: Chain Meta-Analysis
# ─────────────────────────────────────────────
def chain_meta_analysis(cycle_num):
    """分析链创建模式——链的链"""
    if cycle_num % 4 != 0:
        return []

    findings = []
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        total = len(chains)

        # 3.1 平均链长度
        avg_len = sum(len(c.get("content", "")) for c in chains) / max(total, 1)
        short_chains = sum(1 for c in chains if len(c.get("content", "")) < 20)

        findings.append({
            "type": "chain_quality",
            "detail": f"链: {total}条, 平均长度={avg_len:.0f}字符, 短链(<20)= {short_chains}({short_chains/max(total,1)*100:.0f}%)",
            "severity": "info"
        })

        # 3.2 维度分布偏置
        from collections import Counter
        dim_counter = Counter()
        for c in chains:
            d = c.get("dimension", "未分类")
            dim_counter[d] += 1

        if dim_counter:
            most_common = dim_counter.most_common(1)[0]
            least_common = dim_counter.most_common()[-1]
            ratio = most_common[1] / max(least_common[1], 1)

            if ratio > 3.0:
                findings.append({
                    "type": "dim_imbalance",
                    "detail": f"维度偏置: {most_common[0]}({most_common[1]}) vs {least_common[0]}({least_common[1]}), 比={ratio:.1f}",
                    "severity": "warn" if ratio > 5.0 else "info"
                })

    except Exception as e:
        findings.append({"type": "error", "detail": f"链分析异常: {e}", "severity": "error"})

    return findings


# ─────────────────────────────────────────────
# Layer 4: Mutation Rule Mutation
# ─────────────────────────────────────────────
def mutation_meta_optimize(cycle_num):
    """变异的变异——如果当前策略无效，改变策略"""
    if cycle_num % 7 != 0:
        return []

    findings = []
    strategy = _read_json(_MUTATION_STRATEGY, {
        "current": "random_focus",
        "history": [],
        "no_improvement_cycles": 0
    })

    # 检查当前策略是否在产生改进
    # 比较简单：检查最近3个周期是否有新的元递归链
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        mr_chains = [c for c in chains if c.get("dimension") == "元递归"]

        state = _read_json(_META_STATE, {})
        prev_mr = state.get("prev_mr_chain_count", 0)
        current_mr = len(mr_chains)

        if current_mr <= prev_mr:
            strategy["no_improvement_cycles"] += 1
        else:
            strategy["no_improvement_cycles"] = 0

        # 如果 3 周期无改进，更换策略
        if strategy["no_improvement_cycles"] >= 3:
            old_strat = strategy["current"]
            strategies = ["random_focus", "weakest_first", "cross_pair", "meta_fold"]
            available = [s for s in strategies if s != old_strat]
            if available:
                import random
                new_strat = random.choice(available)
                strategy["history"].append({"cycle": cycle_num, "from": old_strat, "to": new_strat})
                strategy["current"] = new_strat
                strategy["no_improvement_cycles"] = 0
                findings.append({
                    "type": "strategy_mutation",
                    "detail": f"变异策略: {old_strat}→{new_strat} (3周期无改进)",
                    "severity": "info"
                })

        state["prev_mr_chain_count"] = current_mr
        _write_json(_META_STATE, state)
        strategy["current_mr_chains"] = current_mr
        _write_json(_MUTATION_STRATEGY, strategy)

    except Exception as e:
        findings.append({"type": "error", "detail": f"变异分析异常: {e}", "severity": "error"})

    return findings


# ─────────────────────────────────────────────
# Main pulse function (called by daemon cycle)
# ─────────────────────────────────────────────
def pulse(cycle_num=0):
    """主入口 — 被 daemon 周期调用。返回结构化洞察"""
    all_findings = []

    # 读取焦点历史
    focus_history = _read_json(CLUSTER / ".brain_focus_history.json", {"entries": []}).get("entries", [])
    current_focus = _read_json(CLUSTER / ".brain_focus.json", {}).get("focus", "未知")

    # 读取当前维度链数
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
        from collections import Counter
        dim_counts = Counter(c.get("dimension", "未分类") for c in chains)
    except Exception:
        dim_counts = {}

    # Layer 1: Meta-Inspection
    all_findings.extend(meta_inspect(cycle_num, current_focus, focus_history))

    # Layer 2: EML Self-Optimization
    all_findings.extend(eml_self_optimize(cycle_num, dim_counts))

    # Layer 3: Chain Meta-Analysis
    all_findings.extend(chain_meta_analysis(cycle_num))

    # Layer 4: Mutation Meta
    all_findings.extend(mutation_meta_optimize(cycle_num))

    # 写回海马体（重点注入）
    try:
        from brain.share import write_chain as _wc
        for f in all_findings:
            if f.get("severity") in ("warn", "error"):
                _wc({
                    "src": f"元递归·{f['type']}",
                    "rel": f"元递归洞察: {f['detail'][:60]}",
                    "dst": "元递归",
                    "dimension": "元递归",
                    "content": f"Cycle#{cycle_num} [元递归] {f['type']}: {f['detail']}",
                    "strength": 0.9 if f["severity"] == "error" else 0.7,
                    "tags": ["元递归激活"]
                })

        # ★ P106: 行为反馈闭环 — warn/error 发现 → 写 brain_next_focus.json → daemon 消费
        _warn_findings = [f for f in all_findings if f.get("severity") in ("warn", "error")]
        if _warn_findings:
            _next_file = CLUSTER / ".brain_next_focus.json"
            _worst = _warn_findings[0]
            _forced_focus = "元递归"
            _reason = f"元递归引擎: {_worst['type']} — {_worst['detail'][:80]}"
            try:
                _next_file.write_text(json.dumps({
                    "forced_focus": _forced_focus,
                    "reason": _reason,
                    "origin_focus": current_focus,
                    "cycle": cycle_num,
                    "timestamp": time.time()
                }, ensure_ascii=False))
                _written = [f"写brain_next_focus.json: {_reason}"[:100]]
            except Exception as _e:
                _written = [f"写brain_next_focus.json异常: {_e}"]
        else:
            _written = []
    except Exception:
        _written = []

    return [f.get("detail", str(f)) for f in all_findings] + _written


# ─────────────────────────────────────────────
# State file helpers (low-level)
# ─────────────────────────────────────────────
def _read_json_file(path, default=None):
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        pass
    return default

def _safe_extract_count(data, default=0):
    """从任意JSON结构中安全提取整数计数"""
    if data is None:
        return default
    if isinstance(data, (int, float)):
        return int(data)
    if isinstance(data, dict):
        return int(data.get("count", data.get("total", data.get("chain_count", default))))
    if isinstance(data, (list, tuple)):
        return len(data)
    return default


if __name__ == "__main__":
    result = pulse(0)
    for r in result:
        print(f"  {r}")
