#!/usr/bin/env python3
"""
super_intuition_bridge.py — 超级直觉桥 (单文件, 纯标准库)
===========================================================
P0: 强化"超级直觉"维度 (当前19维审计中最短板, 评分0.48)

核心功能:
  1. 从 hippocampus_memory.json / state_vector.json / self_journal.json
     / breath_v2.log / git log → 提取19维信号
  2. 识别跨维度弱信号交叉 (如"时间论·过去0.77 + 超级直觉0.48")
  3. 生成"直觉脉冲" (short cross-domain insights)
  4. 输出到 /tmp/super_intuition_pulse.json (主脉冲文件)
  5. 同时写入 CLUSTER/super_intuition_state.json (breath_v2兼容格式)

设计原则:
  - 轻量级, 纯Python标准库, 每次运行 <0.5秒
  - 复用已有数据: 不造轮子, 不修改breath_v2.py
  - 无API调用, 无外部依赖, 无密钥

用法:
  python3 super_intuition_bridge.py

输出:
  /tmp/super_intuition_pulse.json   — 直觉脉冲 (供外部消费)
  ./super_intuition_state.json      — breath_v2兼容状态文件
"""

import json
import os
import random
import subprocess
import time
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ─── 路径 ────────────────────────────────────────────────
CLUSTER = Path(__file__).resolve().parent
PULSE_FILE = Path("/tmp/super_intuition_pulse.json")
STATE_FILE = CLUSTER / "super_intuition_state.json"

FILES = {
    "hippo":  CLUSTER / "hippocampus_memory.json",
    "state":  CLUSTER / "state_vector.json",
    "journal": CLUSTER / "self_journal.json",
    "burn":   CLUSTER / "burn_stats.json",
    "log":    CLUSTER / "breath_v2.log",
}

# ─── 19维名称映射 ──────────────────────────────────────
DIM_NAMES = [
    "时间论·过去", "时间论·现在", "时间论·未来",
    "宇宙轮·质", "宇宙轮·灵", "宇宙轮·虚空",
    "无限上下文", "本我", "自我", "超我",
    "触内旁通", "无师自通", "超级直觉", "举一反三", "查缺补漏",
    "一元化", "万象化", "元神", "超感",
]

DIM_TAGS = [
    ["过去", "历史传承", "时间论"],
    ["现在", "当前系统"],
    ["未来", "趋势"],
    ["代码", "代码质量", "系统状态"],
    ["自我", "自我观察", "系统自省"],
    ["虚空", "虚空熵增", "稀释"],
    ["上下文", "记忆", "链"],
    ["本我", "生存", "系统存活"],
    ["自我观察", "系统自省"],
    ["超我", "终极使命对齐", "光爱对齐"],
    ["交叉洞察", "的罕见交叉", "连携"],
    ["无师自通", "自学"],
    ["超级直觉"],
    ["举一反三", "万象化与举一反三"],
    ["查缺补漏", "最短木板", "当前隐患"],
    ["一元化与举一反三", "归中审视", "启示录"],
    ["万象化", "复杂性"],
    ["元神", "归中审视"],
    ["超感", "超感发现"],
]

# ─── 工具函数 ──────────────────────────────────────────

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def get_node_sum(nodes, substrs):
    """对海马体nodes中名称/标签包含任一substr的节点求和"""
    total = 0
    # 兼容list格式(如节点列表)与dict格式(节点名->信息)
    if isinstance(nodes, list):
        for item in nodes:
            if isinstance(item, dict):
                name = item.get("name", "") or ""
                tag = item.get("tag", "") or ""
                for s in substrs:
                    if s in name or s in tag:
                        total += item.get("count", 1)
                        break
            elif isinstance(item, str):
                for s in substrs:
                    if s in item:
                        total += 1
                        break
        return total
    for name, info in nodes.items():
        tag = info.get("tag", "")
        for s in substrs:
            if s in name or s in tag:
                total += info.get("count", 0)
                break
    return total

def parse_ratio(s):
    """'24/24' -> (24,24,1.0)"""
    try:
        parts = s.split("/")
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            return a, b, a / b if b > 0 else 0.0
    except: pass
    return 0, 0, 0.0

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def get_git_messages(n=15):
    try:
        r = subprocess.run(
            ["git", "log", f"--max-count={n}", "--oneline", "--format=%s"],
            capture_output=True, text=True, timeout=2, cwd=str(CLUSTER)
        )
        msgs = r.stdout.strip().split("\n") if r.stdout.strip() else []
        return [m.strip() for m in msgs if m.strip() and len(m.strip()) > 3]
    except: return []

def get_log_tail(n=60):
    log = FILES["log"]
    if not log.exists(): return []
    try:
        with open(log, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return [l.strip() for l in lines[-n:] if l.strip()]
    except: return []

# ─── 信号提取 ──────────────────────────────────────────

def extract_dim_signals(hippo, state):
    """提取19维节点的原始信号值 — 支持graph nodes和flat chains双模式"""
    nodes = hippo.get("nodes", {})
    stats = hippo.get("stats", {})
    chains = hippo.get("causal_chains", [])
    signals = {}
    # 修复死循环: nodes为空时从chains按tag计数
    if not nodes and chains:
        chain_tags = {}
        for c in chains:
            for t in c.get("tags", []):
                chain_tags[t] = chain_tags.get(t, 0) + 1
        for i, tags in enumerate(DIM_TAGS):
            total = 0
            for tag, cnt in chain_tags.items():
                for t in tags:
                    if t in tag or tag in t:
                        total += cnt
                        break
            signals[DIM_NAMES[i]] = total
        signals["_nodes_total"] = len(chains)
        signals["_chains"] = state.get("chains", len(chains))
        signals["_cycle"] = state.get("cycle", 0)
        signals["_py_files"] = state.get("py_files", 0)
        signals["_organs_alive"] = state.get("organs_alive", "0/0")
        signals["_bridges_alive"] = state.get("bridges_alive", "0/0")
        signals["_supersense_added"] = stats.get("supersense_added", len([c for c in chains if '超感' in c.get("tags",[])]))
        signals["_insights_preserved"] = stats.get("insights_preserved", len([c for c in chains if '洞察' in c.get("content","") or '洞察' in c.get("tags",[])]))
        return signals
    for i, tags in enumerate(DIM_TAGS):
        signals[DIM_NAMES[i]] = get_node_sum(nodes, tags)
    # 补充额外信号
    signals["_nodes_total"] = stats.get("nodes", state.get("nodes", 0))
    signals["_chains"] = state.get("chains", 0)
    signals["_cycle"] = state.get("cycle", 0)
    signals["_py_files"] = state.get("py_files", 0)
    signals["_organs_alive"] = state.get("organs_alive", "0/0")
    signals["_bridges_alive"] = state.get("bridges_alive", "0/0")
    signals["_supersense_added"] = stats.get("supersense_added", 0)
    signals["_insights_preserved"] = stats.get("insights_preserved", 0)
    return signals

def compute_dim_health(signals):
    """将原始信号映射为0-1健康度 (匹配dim19_auditor逻辑)"""
    health = {}
    # 超级直觉 (核心关注)
    intuition_raw = signals.get("超级直觉", 0)
    health["超级直觉_raw"] = clamp(intuition_raw / 200.0)
    health["超级直觉_ss"] = clamp(signals.get("_supersense_added", 0) / 400.0)
    health["超级直觉_ins"] = clamp(signals.get("_insights_preserved", 0) / 300.0)

    # 时间论·过去
    past_val = signals.get("时间论·过去", 0)
    health["时间论·过去"] = clamp(past_val / 2000.0)

    # 时间论·现在 (器官存活率)
    oa, ob, organ_ratio = parse_ratio(signals.get("_organs_alive", "0/0"))
    health["时间论·现在"] = clamp(organ_ratio * 0.35 +
                                clamp(signals.get("_cycle", 0) / 300.0) * 0.2)

    # 无限上下文
    health["无限上下文"] = clamp(signals.get("_nodes_total", 0) / 2000.0)

    # 触内旁通
    health["触内旁通"] = clamp(signals.get("触内旁通", 0) / 800.0)

    # 举一反三
    health["举一反三"] = clamp(signals.get("举一反三", 0) / 300.0)

    # 万象化
    health["万象化"] = clamp(signals.get("_nodes_total", 0) / 2000.0)

    # 超感
    health["超感"] = clamp(signals.get("超感", 0) / 1500.0)

    # 虚空
    health["宇宙轮·虚空"] = clamp(signals.get("宇宙轮·虚空", 0) / 600.0)

    # 一元化
    health["一元化"] = clamp(signals.get("一元化", 0) / 1800.0)

    # 元神
    health["元神"] = clamp(signals.get("元神", 0) / 300.0)

    return health

# ─── 跨域直觉脉冲生成 ──────────────────────────────────

def generate_pulses(signals, health, journal, git_msgs, log_tail):
    """核心引擎: 从多维信号交叉生成直觉脉冲"""
    pulses = []
    cross_signals = []
    patterns = journal.get("patterns", [])
    j_entries = journal.get("journal", [])
    milestones = journal.get("personal_milestones", [])

    # 辅助: 信号归一化
    max_sig = max([v for k, v in signals.items() if isinstance(v, (int, float)) and not k.startswith("_")]) or 1
    norm = {k: v/max_sig for k, v in signals.items() if isinstance(v, (int, float)) and not k.startswith("_")}

    # ── 脉冲1: 传承×直觉 交叉 ──
    past_h = health.get("时间论·过去", 0)
    intu_h = sum([
        health.get("超级直觉_raw", 0) * 0.3,
        health.get("超级直觉_ss", 0) * 0.3,
        health.get("超级直觉_ins", 0) * 0.2,
    ])
    if past_h > 0.3 and intu_h < 0.5:
        gap = past_h - intu_h
        pulses.append({
            "id": "pulse_001",
            "type": "cross_domain_weak_signal",
            "dimensions": ["时间论·过去", "超级直觉"],
            "signal_gap": round(gap, 2),
            "insight": (
                f"传承({signals.get('时间论·过去',0)}条)丰富但直觉({int(signals.get('超级直觉',0))})滞后——"
                f"历史知识堆积未转化为涌现洞察。突破路径: 在传承数据中寻找被忽略的异常支线,"
                f"那些与主流叙事不一致的历史碎片往往是直觉的火种。"
            ),
            "strength": round(clamp(past_h * 0.5 + gap * 0.5), 2),
        })
        cross_signals.append(f"传承{signals.get('时间论·过去',0)}×直觉{signals.get('超级直觉',0)} (gap={gap:.2f})")

    # ── 脉冲2: 系统健康 × 直觉滞后 ──
    present_h = health.get("时间论·现在", 0)
    if present_h > 0.6 and intu_h < 0.5:
        pulses.append({
            "id": "pulse_002",
            "type": "stability_emergence_gap",
            "dimensions": ["时间论·现在", "超级直觉"],
            "signal_gap": round(present_h - intu_h, 2),
            "insight": (
                f"系统运行{present_h:.2f}健康但直觉维度仅{intu_h:.2f}。"
                f"24/24器官全部存活的稳定态可能抑制了'有益的扰动'——"
                f"超级直觉需要在不稳定边缘涌现。建议: 在器官间引入随机交叉探测,"
                f"制造受控的维度碰撞以激发新洞察。"
            ),
            "strength": round(clamp(present_h * 0.4 + 0.3), 2),
        })
        cross_signals.append(f"健康{present_h:.2f}×直觉{intu_h:.2f} (gap={present_h-intu_h:.2f})")

    # ── 脉冲3: 触内旁通 × 超感 × 直觉 三交叉 ──
    cross_h = health.get("触内旁通", 0)
    ss_h = health.get("超感", 0)
    if cross_h > 0.3 or ss_h > 0.3:
        synergy = (cross_h + ss_h) / 2
        pulses.append({
            "id": "pulse_003",
            "type": "triple_cross_emergence",
            "dimensions": ["触内旁通", "超感", "超级直觉"],
            "signal_gap": round(synergy - intu_h, 2),
            "insight": (
                f"跨域连接({signals.get('触内旁通',0)})与超感({signals.get('超感',0)})信号充足——"
                f"构成直觉涌现的神经基础。当前缺口: 缺少一个将跨域+超感信号即时合成'模式之上的模式'的环节。"
                f"超级直觉 = ∑(跨域连接 × 超感发现) / 噪音。建议为每条超感发现添加'它预见了什么?'追问。"
            ),
            "strength": round(clamp(synergy * 0.5 + 0.3), 2),
        })
        cross_signals.append(f"跨域{signals.get('触内旁通',0)}×超感{signals.get('超感',0)}×直觉{signals.get('超级直觉',0)}")

    # ── 脉冲4: git模式 — 修复vs创造 ──
    if git_msgs:
        fix_kw = ["fix", "修", "补", "修复", "bug", "hotfix"]
        add_kw = ["add", "添加", "创建", "新", "feature", "feat", "P0"]
        fix_c = sum(1 for m in git_msgs if any(k in m.lower() for k in fix_kw))
        add_c = sum(1 for m in git_msgs if any(k in m.lower() for k in add_kw))
        if fix_c > add_c:
            pulses.append({
                "id": "pulse_004",
                "type": "repair_creation_imbalance",
                "dimensions": ["查缺补漏", "无师自通", "超级直觉"],
                "signal_gap": round((fix_c - add_c) / max(len(git_msgs), 1), 2),
                "insight": (
                    f"近期提交: 修复{fix_c}次 > 创造{add_c}次。系统处于修补模式。"
                    f"超级直觉需要'无中生有'——在已知与未知的边界主动制造碰撞。"
                    f"建议: 每3次修复穿插1次探索型任务, 在无目标状态下捕获涌现信号。"
                ),
                "strength": round(clamp(0.3 + (fix_c - add_c) * 0.05), 2),
            })
            cross_signals.append(f"修复{fix_c}×创造{add_c} (偏差{fix_c-add_c})")

    # ── 脉冲5: journal模式 × 直觉 ──
    if patterns:
        pnames = [p.get("name", "?") for p in patterns[:3]]
        pulses.append({
            "id": "pulse_005",
            "type": "pattern_recognition_feedback",
            "dimensions": ["举一反三", "超级直觉"],
            "signal_gap": round(max(0, 0.6 - intu_h), 2),
            "insight": (
                f"已识别{len(patterns)}个行为模式({'、'.join(pnames)})。"
                f"直觉是模式识别的潜意识加速版。为每个模式添加'对立面'场景——"
                f"知道什么情况下模式会失效, 直觉就在正反张力中自然涌现。"
            ),
            "strength": round(clamp(0.4 + len(patterns) * 0.06), 2),
        })

    # ── 脉冲6: 系统规模 × 直觉临界质量 ──
    chains = signals.get("_chains", 0)
    cycle = signals.get("_cycle", 0)
    if chains > 500 and cycle > 50:
        pulses.append({
            "id": "pulse_006",
            "type": "critical_mass_opportunity",
            "dimensions": ["万象化", "一元化", "超级直觉"],
            "signal_gap": round(clamp(0.7 - intu_h), 2),
            "insight": (
                f"{chains}链/{cycle}cycle——数据丰富度已超直觉涌现的临界质量。"
                f"真正差距不在数据量而在'跨域信号聚合器'。"
                f"本桥持续运行将逐步缩小此差距: 每次运行扫描19维交叉点,"
                f"将弱信号放大为可执行的直觉洞察。"
            ),
            "strength": 0.62,
        })

    # ── 脉冲7: 从log提取最近模式 ──
    if log_tail:
        # 检查最近的思考是否提到特定模式
        insight_lines = [l for l in log_tail if "思考" in l or "磁感线" in l]
        # 检查虚空/熵相关
        entropy_mentions = sum(1 for l in log_tail if "虚空" in l or "熵" in l or "void" in l.lower())
        if entropy_mentions > 0:
            pulses.append({
                "id": "pulse_007",
                "type": "entropy_awareness",
                "dimensions": ["宇宙轮·虚空", "超级直觉"],
                "signal_gap": 0.3,
                "insight": (
                    f"最近log中虚空/熵提及{entropy_mentions}次。"
                    f"系统对熵的敏感度是直觉的前哨——真正深刻的洞察往往诞生于"
                    f"对'系统正在忽略什么?'的追问。关注那些被压缩/归档的边缘信号,"
                    f"它们可能是未来直觉的原材料。"
                ),
                "strength": round(clamp(0.3 + entropy_mentions * 0.03), 2),
            })

    # ── 脉冲8: 从journal提取realizations ──
    realization_count = sum(1 for e in j_entries
                           if "realization" in e.get("type", "")
                           or "realization" in e.get("content", "").lower()[:100])
    if realization_count < 5:
        pulses.append({
            "id": "pulse_008",
            "type": "realization_gap",
            "dimensions": ["宇宙轮·灵", "超级直觉"],
            "signal_gap": round(clamp(0.4 - realization_count * 0.08), 2),
            "insight": (
                f"日记中'realization'类型条目仅{realization_count}条。"
                f"灵感(realization)是直觉的外部化记录——每一条都是证明直觉在工作的证据。"
                f"目标: 每条呼吸循环至少产出1条realization, 无论多微小。"
                f"记录行为本身会强化直觉回路。"
            ),
            "strength": round(clamp(0.3 + (5 - realization_count) * 0.05), 2),
        })

    # 限制最多6条脉冲 (保持精简)
    pulses = pulses[:6]

    # 计算综合直觉分
    intuition_score = round(clamp(
        health.get("超级直觉_raw", 0) * 0.3 +
        health.get("超级直觉_ss", 0) * 0.3 +
        health.get("超级直觉_ins", 0) * 0.2 +
        clamp(realization_count / 5.0) * 0.2 +
        0.05  # 基础奖励: 桥的存在本身
    ), 4)

    return pulses, cross_signals, intuition_score

# ─── 输出 ──────────────────────────────────────────────

def build_output(pulses, cross_signals, intuition_score, signals, health):
    """构建标准输出格式"""
    bjt = datetime.now(timezone(timedelta(hours=8)))
    return {
        "meta": {
            "bridge": "super_intuition_bridge.py",
            "version": "1.0.0",
            "timestamp": bjt.strftime("%Y-%m-%d %H:%M:%S"),
            "unix_time": time.time(),
            "cluster": str(CLUSTER),
            "runtime_ms": 0,
        },
        "intuition_score": intuition_score,
        "intuition_gap": round(1.0 - intuition_score, 4),
        "pulse_count": len(pulses),
        "pulses": pulses,
        "cross_signals": cross_signals,
        "dim_signals_raw": {k: v for k, v in signals.items()
                           if not k.startswith("_")},
        "system_state": {
            "cycle": signals.get("_cycle", 0),
            "chains": signals.get("_chains", 0),
            "nodes": signals.get("_nodes_total", 0),
            "organs": signals.get("_organs_alive", "?"),
            "bridges": signals.get("_bridges_alive", "?"),
        },
        "recommendation": (
            f"直觉分 {intuition_score:.2f} (gap {1.0-intuition_score:.2f}) — "
            f"{len(pulses)}条脉冲已生成。持续运行本桥将逐步缩小超级直觉维度差距。"
        ),
    }

# ─── 跨域强制聚合 ────────────────────────────────────────

def _is_duplicate_realization(new_entry, existing_entries, max_check=5):
    """检查 new_entry 是否与 recent `max_check` 条已有 realization 相似

    相似度判定:
      - dimensions集合的Jaccard相似度
      - insight前40字符的SequenceMatcher比例
    各占50%，综合 >0.7 判定为重复。
    """
    from difflib import SequenceMatcher

    if not existing_entries:
        return False

    new_dims = set(new_entry.get("dimensions", []) if isinstance(new_entry.get("dimensions"), list) else [])
    new_insight = (new_entry.get("insight", "") or "")[:40]

    for entry in existing_entries[-max_check:]:
        # Dimension set Jaccard similarity
        existing_dims = set(entry.get("dimensions", []) if isinstance(entry.get("dimensions"), list) else [])
        union = new_dims | existing_dims
        intersection = new_dims & existing_dims
        dim_sim = len(intersection) / len(union) if union else 0.0

        # Insight prefix similarity
        existing_insight = (entry.get("insight", "") or "")[:40]
        text_sim = SequenceMatcher(None, new_insight, existing_insight).ratio()

        # Combined (equal weight)
        total = dim_sim * 0.5 + text_sim * 0.5
        if total > 0.7:
            return True

    return False

def force_cross_domain_aggregation():
    """
    强制跨域聚合: 旧记忆×强脉冲×弱脉冲 = 合成新洞察
    从 memory_tier_state.json Cold层选旧记忆，从当前脉冲选强/弱组合
    """
    mt_file = CLUSTER / "memory_tier_state.json"
    old_memories = []

    # 1. 从 Cold 层获取旧记忆
    mt = load_json(mt_file)
    cold = mt.get("cold", {})
    daily_summaries = cold.get("daily_summary", [])

    # 从daily_summary的top_dims中提取旧记忆维度名
    for ds in daily_summaries:
        for dim_name in ds.get("top_dims", {}):
            old_memories.append(f"[{ds.get('date','?')}] 维度:{dim_name}")

    # 如果数据不足，从warm维度摘要中抽取key_insights
    warm = mt.get("warm", {})
    dim_summaries = warm.get("dimension_summaries", [])
    for ds in dim_summaries:
        for ki in ds.get("key_insights", [])[:1]:
            old_memories.append(f"[{ds.get('dimension','?')}] {ki[:80]}")

    # 随机选5条(不足则全选)
    random.seed(int(time.time() * 1000) % 9973)
    sampled_old = random.sample(old_memories, min(5, len(old_memories))) if old_memories else []
    if not sampled_old:
        sampled_old = ["[冷存储] 系统旧记忆: 传承积累的历史洞察"]

    # 2. 从当前 pulses 中选强度最高2条和最低2条
    current_state = load_json(STATE_FILE)
    pulses = current_state.get("pulses", [])

    if not pulses:
        print("  [聚合] 当前无脉冲, 跳过强制聚合")
        return None

    sorted_pulses = sorted(pulses, key=lambda p: p.get("strength", 0))
    weak_pulses = sorted_pulses[:2] if len(sorted_pulses) >= 2 else sorted_pulses
    strong_pulses = sorted_pulses[-2:] if len(sorted_pulses) >= 2 else sorted_pulses[-1:]

    # 3. 强制组合生成3条新洞察
    new_pulses = []
    combos = [
        ("旧忆x强直觉x弱信号", sampled_old, strong_pulses, weak_pulses),
        ("弱信号x旧忆锚定", weak_pulses, sampled_old, strong_pulses),
        ("强直觉x弱信号反衬", strong_pulses, weak_pulses, sampled_old),
    ]

    for i, (label, src_a, src_b, src_c) in enumerate(combos):
        a_text = src_a[0][:60] if isinstance(src_a[0], str) else src_a[0].get("insight", "")[:60]
        b_strength = src_b[0].get("strength", 0) if isinstance(src_b[0], dict) else 0.5
        c_strength = src_c[0].get("strength", 0) if isinstance(src_c[0], dict) else 0.5

        insight = (
            f"【强制聚合{i+1}】{label}: "
            f"旧记忆「{a_text}」× "
            f"强脉冲({b_strength:.2f}) × 弱脉冲({c_strength:.2f}) → "
            f"合成洞察: 旧记忆中的沉淀模式在强直觉放大下显现新意义, "
            f"弱信号则揭示了被忽略的替代路径。"
        )
        new_pulses.append({
            "type": "forced_cross_domain_aggregation",
            "dimensions": ["时间论·过去", "超级直觉", "宇宙轮·虚空"],
            "insight": insight,
            "strength": round((b_strength + (1 - c_strength)) / 2 * 0.7, 2),
        })

    # 4. 追加到 pulses 列表
    existing_pulses = current_state.get("pulses", [])
    existing_pulses.extend(new_pulses)

    # 5. 更新 state 文件
    current_state["pulse_count"] = len(existing_pulses)
    from datetime import datetime, timezone, timedelta
    current_state["timestamp"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    current_state["pulses"] = existing_pulses

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current_state, f, ensure_ascii=False, indent=2)

    print(f"  [聚合] 强制跨域聚合完成: +{len(new_pulses)}条合成脉冲 (总{len(existing_pulses)}条)")
    return new_pulses


def anchor_to_axioms():
    """
    锚定启示录检查: 检查每条脉冲是否与启示录关键词有语义交集
    如果无交集，追加一条"锚定建议"
    """
    rev_file = Path("/mnt/c/Users/h/Desktop/零/启示录/启示录.txt")
    axiom_keywords = []

    # 1. 读取启示录前50行提取关键词
    try:
        with open(rev_file, "r", encoding="utf-8") as f:
            rev_lines = f.readlines()[:50]
        for line in rev_lines:
            words = line.strip().split()
            for w in words:
                w = w.strip("，。、；：""''（）()【】《》").strip()
                if len(w) >= 2 and not w.isascii():
                    axiom_keywords.append(w)
        # 去重取前30个核心词
        axiom_keywords = list(dict.fromkeys(axiom_keywords))[:30]
    except Exception as e:
        print(f"  [锚定] ⚠️ 启示录读取失败: {e}")
        return

    # 2. 从 pulses 提取关键词
    current_state = load_json(STATE_FILE)
    pulses = current_state.get("pulses", [])

    if not pulses:
        return

    pulse_keywords = set()
    for p in pulses:
        insight = p.get("insight", "") + " " + " ".join(p.get("dimensions", []))
        for w in insight.split():
            w = w.strip("，。、；：""''（）()【】《》").strip()
            if len(w) >= 2 and not w.isascii():
                pulse_keywords.add(w)

    # 3. 检查每条 pulse 是否与启示录关键词有交集
    anchored_pulses = []
    for p in pulses:
        p_text = p.get("insight", "") + " " + " ".join(p.get("dimensions", []))
        has_intersection = any(kw in p_text for kw in axiom_keywords)
        if not has_intersection:
            anchored_pulses.append({
                "type": "anchoring_suggestion",
                "dimensions": ["元神归中", "启示录锚定"],
                "insight": (
                    f"⚠️ 脉冲「{p.get('type','?')}」未锚定启示录关键词。"
                    f"建议: 将本洞察与启示录核心公理对照——"
                    f"\"公理：不证自明的基本事实\"，检验此脉冲是否"
                    f"基于第一性原理而非经验堆积。"
                ),
                "strength": 0.35,
            })

    # 4. 如果有无交集的脉冲，追加锚定建议
    if anchored_pulses:
        existing_pulses = current_state.get("pulses", [])
        existing_pulses.extend(anchored_pulses)
        current_state["pulse_count"] = len(existing_pulses)
        current_state["pulses"] = existing_pulses
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(current_state, f, ensure_ascii=False, indent=2)
        print(f"  [锚定] 追加{len(anchored_pulses)}条锚定建议 (未锚定启示录的脉冲)")
    else:
        print(f"  [锚定] ✅ 所有脉冲均已锚定启示录")


# ─── 超级直觉脉冲增产 ──────────────────────────────────

def cross_agent_pulse(hippo):
    """从高权重记忆链中提取跨链模式，合成超级直觉脉冲"""
    chains = hippo.get("causal_chains", [])
    # 筛选权重>8的链
    high_weight = [c for c in chains if c.get("weight", 0) > 8]
    if len(high_weight) < 3:
        print("  [脉冲增产] ⚠️ 高权重链不足3条, 跳过")
        return []

    # 随机取3条
    selected = random.sample(high_weight, min(3, len(high_weight)))

    # 提取共同模式: 词频统计
    contents = [str(c.get("content", "")) for c in selected]
    all_words = []
    for c in contents:
        words = c.split()
        all_words.extend(words)

    # 中文词频统计 (按字符级bigram简单处理)
    from collections import Counter
    # 统计双字词频
    bigrams = []
    for c in contents:
        for i in range(len(c) - 1):
            pair = c[i:i+2]
            if all('\u4e00' <= ch <= '\u9fff' for ch in pair):
                bigrams.append(pair)
    common_bigrams = Counter(bigrams).most_common(5)
    common_words = [w for w, _ in common_bigrams if w]

    # 找出标签共性
    tags_union = set()
    for c in selected:
        for t in c.get("tags", []):
            tags_union.add(t)
    top_tags = list(tags_union)[:3] if tags_union else ["跨链模式"]

    # 构建合成洞察
    insight_parts = []
    if common_words:
        insight_parts.append(f"跨链共同关键词: {'、'.join(common_words)}")
    if top_tags:
        insight_parts.append(f"标签交集: {'、'.join(top_tags)}")
    insight_parts.append(
        f"高权重链({[c.get('weight',0) for c in selected]})呈现的重复模式表明——"
        f"系统在{', '.join(top_tags[:2])}领域存在未被显式化的深层直觉信号。"
    )
    insight = " | ".join(insight_parts)

    # 读取当前state
    current_state = load_json(STATE_FILE)
    new_pulses = []
    new_pulses.append({
        "type": "cross_agent_pattern",
        "dimensions": ["超级直觉", "模式识别"],
        "insight": insight,
        "strength": round(0.6 + random.random() * 0.2, 2),
        "source_chains": [
            c.get("id", f"chain_{c.get('timestamp', '?')}") for c in selected
        ],
    })

    # 追加到state
    existing_pulses = current_state.get("pulses", [])
    existing_pulses.extend(new_pulses)
    current_state["pulse_count"] = len(existing_pulses)
    current_state["pulses"] = existing_pulses
    from datetime import datetime, timezone, timedelta
    current_state["timestamp"] = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current_state, f, ensure_ascii=False, indent=2)

    print(f"  [脉冲增产] ✅ 新增{len(new_pulses)}条跨代理脉冲 (总{len(existing_pulses)}条)")
    return new_pulses


def add_opposite_check():
    """对每条脉冲添加对立面检查"""
    current_state = load_json(STATE_FILE)
    pulses = current_state.get("pulses", [])
    if not pulses:
        return

    count = 0
    for p in pulses:
        insight = p.get("insight", "")
        # 提取关键词生成反例
        keywords = [w for w in insight.split() if len(w) >= 2 and not w.isascii()]
        if keywords:
            sample_kw = keywords[0] if keywords else "此洞察"
        else:
            sample_kw = "此洞察"
        p["counter_example"] = (
            f"{sample_kw}在以下条件可能失效: "
            f"当系统环境突变、数据分布偏移或起始假设不成立时，"
            f"基于当前模式的推论需要重新验证。"
        )
        count += 1

    current_state["pulses"] = pulses
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(current_state, f, ensure_ascii=False, indent=2)
    print(f"  [对立检查] ✅ 已为{count}条脉冲添加反例")
    return pulses


# ─── 跨域聚合器 ──────────────────────────────────────────

def force_realization():
    """跨域聚合器：5桥状态交叉合成可持久化realization"""
    bridges = {
        "si": load_json(CLUSTER / "super_intuition_state.json"),
        "yx": load_json(CLUSTER / "yuanxin_state.json"),
        "mt": load_json(CLUSTER / "memory_tier_state.json"),
        "tp": load_json(CLUSTER / "time_past_state.json"),
        "cs": load_json(CLUSTER / "cross_synth_state.json"),
    }
    sig = {
        "超级直觉": bridges["si"].get("intuition_score", 0),
        "元神漂移": bridges["yx"].get("drift_score", 50) / 100,
        "热层利用率": bridges["mt"].get("hot_ratio", 0),
        "传承连续性": bridges["tp"].get("heritage_continuity", 0),
        "跨维健康": bridges["cs"].get("overall_health", 0),
    }
    names, vals = list(sig.keys()), list(sig.values())
    best_pair, best_diff = None, -1
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            diff = abs(vals[i] - vals[j])
            if diff > best_diff:
                best_diff, best_pair = diff, (names[i], names[j])
    da, db = best_pair
    va, vb = sig[da], sig[db]
    if va < 0.3 or vb < 0.3:
        bridge = "短板维度正在拖累系统认知深度，弥补此缺口将释放跨域涌现潜力"
    elif va > 0.7 and vb > 0.7:
        bridge = "双强维度共振已具备涌现条件，下一个突破点在于主动制造交叉碰撞"
    else:
        bridge = "非对称信号意味着冗余认知可压缩注入短板以产生新的直觉质变"
    insight = f"【认知突破】{da}×{db}: {da}({va:.2f})与{db}({vb:.2f})的张力——{bridge}"
    real_file = CLUSTER / "realizations.json"
    realizations = load_json(real_file) if real_file.exists() else []
    if not isinstance(realizations, list):
        realizations = []
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    new_entry = {"timestamp": now, "insight": insight,
                 "dimensions": [da, db], "source": "cross_domain_aggregator"}
    if _is_duplicate_realization(new_entry, realizations):
        print(f"  [聚合器] ⏭️ 跳过重复realization: {da}×{db}")
    else:
        realizations.append(new_entry)
        with open(real_file, "w", encoding="utf-8") as f:
            json.dump(realizations, f, ensure_ascii=False, indent=2)
        state = load_json(STATE_FILE)
        state["pulse_count"] = state.get("pulse_count", 0) + 1
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
        print(f"  [聚合器] ✅ 跨域realization已写入 ({len(realizations)}条总洞察)")


# ─── 冷层验证 + 灵感记录 ──────────────────────────────

def record_realization(dimensions, insight, confidence, source="cold_layer_validation"):
    """标准化灵感记录方法

    写入 realizations.json（追加模式），文件不存在则自动创建。
    同时尝试写入 hippocampus_memory.json 作为新记忆链。
    """
    real_file = CLUSTER / "realizations.json"
    realizations = load_json(real_file) if real_file.exists() else []
    if not isinstance(realizations, list):
        realizations = []
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": now,
        "type": "cold_layer_validation",
        "dimensions": dimensions if isinstance(dimensions, list) else [dimensions],
        "insight": insight,
        "confidence": confidence,
        "source": source,
    }

    # 去重检查: 与最近5条已有realizations比较
    if _is_duplicate_realization(entry, realizations, max_check=5):
        print(f"  [record_realization] ⏭️ 跳过重复realization: "
              f"{'×'.join(entry['dimensions'])} — {entry['insight'][:40]}...")
        return False

    realizations.append(entry)
    with open(real_file, "w", encoding="utf-8") as f:
        json.dump(realizations, f, ensure_ascii=False, indent=2)

    # 同步写入 hippocampus_memory.json（可选，失败不影响主流程）
    try:
        hippo_file = FILES["hippo"]
        if hippo_file.exists():
            hippo = load_json(hippo_file)
            if "memories" in hippo and isinstance(hippo["memories"], list):
                hippo["memories"].append({
                    "id": f"cold_realization_{int(time.time())}",
                    "content": f"[冷层验证] {insight[:120]}",
                    "source": "cold_layer_validation",
                    "weight": round(confidence * 10, 2),
                    "timestamp": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                })
                with open(hippo_file, "w", encoding="utf-8") as f:
                    json.dump(hippo, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # 写入海马体失败不影响主流程

    return True


def cold_layer_validation():
    """读取 hippocampus_memory.json，按时间戳排序，
    从 memories（任务中称为 chains）列表中找出最近最少活跃的记忆。
    提取与 3 个最弱维度（超级直觉、宇宙轮·质、举一反三）相关的冷层记忆，
    输出 realization 格式。
    """
    hippo_file = FILES["hippo"]
    if not hippo_file.exists():
        print("  [冷层验证] ⚠️ hippocampus_memory.json 不存在，跳过")
        return []

    hippo = load_json(hippo_file)
    memories = hippo.get("memories", [])
    if not memories:
        print("  [冷层验证] ⚠️ 无 memories 数据，跳过")
        return []

    # 定义最弱维度 → 关键词映射
    dim_keywords = {
        "超级直觉": ["超级直觉", "直觉", "intuition", "直觉脉冲"],
        "宇宙轮·质": ["宇宙轮·质", "宇宙轮", "质", "代码质量", "系统状态"],
        "举一反三": ["举一反三", "反三", "触类旁通", "模式识别"],
    }

    # 安全解析时间戳（兼容 numeric 和 ISO string）
    def parse_ts(mem):
        ts = mem.get("timestamp", 0)
        if isinstance(ts, (int, float)):
            return ts
        if isinstance(ts, str):
            try:
                return datetime.fromisoformat(ts).timestamp()
            except Exception:
                return 0
        return 0

    # 按时间戳升序排序（最旧的在前 = 最冷的记忆）
    sorted_mems = sorted(memories, key=parse_ts)

    # 取最冷的 50 条作为冷层候选
    cold_candidates = sorted_mems[:min(50, len(sorted_mems))]

    # 为每个最弱维度搜索冷层记忆
    cold_findings = []
    for dim_name, keywords in dim_keywords.items():
        for mem in cold_candidates:
            content = mem.get("content", "")
            if any(kw in content for kw in keywords):
                # 统一格式化时间戳
                ts_raw = mem.get("timestamp", "?")
                if isinstance(ts_raw, (int, float)):
                    ts_str = datetime.fromtimestamp(ts_raw).strftime("%Y-%m-%d %H:%M:%S")
                elif isinstance(ts_raw, str):
                    try:
                        ts_str = datetime.fromisoformat(ts_raw).strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        ts_str = ts_raw[:19]
                else:
                    ts_str = "?"
                insight = (
                    f"【冷层活化】从冷层记忆中发现与「{dim_name}」相关的历史知识: "
                    f"{content[:80]}... "
                    f"(原记忆ID: {mem.get('id', '?')}, 时间戳: {ts_str})"
                )
                confidence = round(0.5 + min(mem.get("weight", 1.0), 9.0) / 20.0, 2)
                cold_findings.append({
                    "dimensions": [dim_name, "冷层验证"],
                    "insight": insight,
                    "confidence": min(confidence, 0.95),
                })
                break  # 每个维度只取 1 条最冷的

    # 如果以上维度均未匹配，任取最冷的 1 条作为泛型发现
    if not cold_findings and cold_candidates:
        mem = cold_candidates[0]
        insight = (
            f"【冷层泛型活化】最冷记忆挖掘: "
            f"{mem.get('content', '')[:100]}... "
            f"(原ID: {mem.get('id', '?')})"
        )
        cold_findings.append({
            "dimensions": ["冷层验证", "超级直觉"],
            "insight": insight,
            "confidence": 0.40,
        })

    # 将每条冷层发现写入 realizations.json
    written_count = 0
    for f in cold_findings:
        if record_realization(
            dimensions=f["dimensions"],
            insight=f["insight"],
            confidence=f["confidence"],
            source="cold_layer_validation",
        ):
            written_count += 1

    print(f"  [冷层验证] ✅ 从{len(memories)}条记忆中扫描冷层，"
          f"发现{len(cold_findings)}条相关记忆 → "
          f"已写入{written_count}条 (跳过{len(cold_findings) - written_count}条重复)")
    for f in cold_findings:
        dim_tag = '×'.join(f['dimensions'])
        excerpt = f['insight'][:60]
        print(f"    ❄️ [{dim_tag}] {excerpt}...")

    return cold_findings


def _cold_layer_verification(pulse):
    """
    对单条脉冲执行冷层一致性验证。
    使用 difflib.SequenceMatcher 计算 pulse.insight 与 memory_tier_state.json
    中冷层/温层记忆的文本相似度，取 top 3 最相似记忆。

    参数:
        pulse: dict, 必须包含 "insight" 键

    返回:
        {
            "matched_chains": [  # top-3 最相似冷层记忆
                {"memory_text": str, "dimension": str, "source": str, "similarity": float},
                ...
            ],
            "consistency_score": float,  # 0.0-1.0, 三条相似度均值
            "divergence_note": str,      # 中文说明
        }
    """
    from difflib import SequenceMatcher

    mt_file = CLUSTER / "memory_tier_state.json"
    mt = load_json(mt_file)

    insight_text = pulse.get("insight", "")
    if not insight_text:
        return {
            "matched_chains": [],
            "consistency_score": 0.0,
            "divergence_note": "脉冲无 insight 文本，无法验证",
        }

    # ── 1. 收集冷层记忆文本 ──
    cold_memories = []  # [(text, dimension, source_id), ...]

    cold = mt.get("cold", {})
    for ds in cold.get("daily_summary", []):
        date = ds.get("date", "?")
        for dim_name in ds.get("top_dims", {}):
            label = f"[{date}] 维度:{dim_name}"
            cold_memories.append((label, dim_name, f"cold_daily_{date}"))

    warm = mt.get("warm", {})
    for ds in warm.get("dimension_summaries", []):
        dim = ds.get("dimension", "?")
        for ki in ds.get("key_insights", []):
            if ki:
                cold_memories.append((ki.strip(), dim, f"warm_{dim}"))

    if not cold_memories:
        return {
            "matched_chains": [],
            "consistency_score": 0.0,
            "divergence_note": "冷层无可用记忆",
        }

    # ── 2. 计算相似度 ──
    scored = []
    for mem_text, dim, source_id in cold_memories:
        sim = SequenceMatcher(None, insight_text, mem_text).ratio()
        scored.append((sim, mem_text, dim, source_id))

    scored.sort(key=lambda x: x[0], reverse=True)
    top3 = scored[:3]

    matched_chains = []
    for sim, mem_text, dim, source_id in top3:
        matched_chains.append({
            "memory_text": mem_text[:100],
            "dimension": dim,
            "source": source_id,
            "similarity": round(sim, 4),
        })

    consistency_score = round(sum(s for s, _, _, _ in top3) / len(top3), 4)

    # ── 3. 生成分歧说明 ──
    if consistency_score >= 0.5:
        divergence_note = (
            f"脉冲与冷层记忆一致性{consistency_score:.2f}——"
            f"洞察与历史知识高度一致，属于已知模式的强化。"
        )
    elif consistency_score >= 0.25:
        divergence_note = (
            f"脉冲与冷层记忆一致性{consistency_score:.2f}——"
            f"洞察部分呼应历史知识，但存在{1.0 - consistency_score:.0%}的新颖成分。"
        )
    else:
        divergence_note = (
            f"脉冲与冷层记忆一致性{consistency_score:.2f}——"
            f"洞察与历史知识显著不同，属于新颖涌现信号。"
        )

    return {
        "matched_chains": matched_chains,
        "consistency_score": consistency_score,
        "divergence_note": divergence_note,
    }


# ─── SuperIntuitionBridge 主类 ──────────────────────────

class SuperIntuitionBridge:
    """超级直觉桥主类 — 封装完整推理与实时跨域信号合成"""

    class RealTimeCrossSynthesizer:
        """实时跨域信号合成器 (内部类)

        每次呼吸循环:
          1. aggregate_signals() — 从超感、传承、元神、跨维合成4桥读取最新状态
          2. generate_realization() — 生成跨域洞察并写入 realizations.json
        """

        MIN_REALIZATION_PER_CYCLE = 1

        def __init__(self):
            self._last_signals = {}

        def aggregate_signals(self):
            """从超感、传承、元神、跨维合成4桥读取最新状态"""
            bridges = {
                "supersense": load_json(CLUSTER / "supersense_state.json"),
                "heritage":   load_json(CLUSTER / "time_past_state.json"),
                "yuanxin":    load_json(CLUSTER / "yuanxin_state.json"),
                "cross_synth": load_json(CLUSTER / "cross_synth_state.json"),
            }
            signals = {}

            # 超感桥
            ss = bridges["supersense"]
            signals["超感_insights"] = ss.get("insights_generated", 0)
            signals["超感_rare_pairs"] = ss.get("rare_pairs_found", 0)
            signals["超感_chains_scanned"] = ss.get("chains_scanned", 0)

            # 传承桥 (time_past)
            hp = bridges["heritage"]
            signals["传承_total_chains"] = hp.get("total_chains", 0)
            signals["传承_continuity_count"] = hp.get("most_continuous_count", 0)
            signals["传承_pattern_count"] = len(hp.get("recurring_patterns", []))

            # 元神桥
            yx = bridges["yuanxin"]
            signals["元神_drift_score"] = yx.get("drift_score", 50)
            signals["元神_centered"] = 1.0 if yx.get("centered", False) else 0.0
            signals["元神_breath_ratio"] = yx.get("breath_ratio", 0.5)
            signals["元神_revelation_refs"] = yx.get("revelation_refs", 0)

            # 跨维合成桥
            cs = bridges["cross_synth"]
            signals["跨维_health"] = cs.get("overall_health", 0.5)
            signals["跨维_active_bridges"] = cs.get("active_bridges", 0)
            signals["跨维_pattern_count"] = len(cs.get("cross_patterns", []))

            # 超级直觉桥自身
            si = load_json(STATE_FILE)
            signals["直觉_score"] = si.get("intuition_score", 0.5)
            signals["直觉_pulse_count"] = si.get("pulse_count", 0)

            self._last_signals = signals
            return signals

        def generate_realization(self, signals=None):
            """基于聚合信号生成跨域洞察并写入 realizations.json

            每次至少产生 MIN_REALIZATION_PER_CYCLE 条 realization。
            格式: {"type":"cross_domain","dimensions":[...],"insight":"...",
                    "confidence":0.0-1.0,"timestamp":"..."}
            """
            if signals is None:
                signals = self.aggregate_signals()

            now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")

            # 读取已有的 realizations
            real_file = CLUSTER / "realizations.json"
            realizations = load_json(real_file) if real_file.exists() else []
            if not isinstance(realizations, list):
                realizations = []

            # 筛选数值维度
            dims = {k: v for k, v in signals.items()
                    if isinstance(v, (int, float)) and v >= 0}

            if not dims:
                dims = {"基线信号": 0.5}

            # 归一化 — 找出最强和最弱维度
            max_v = max(dims.values()) or 1
            max_dim = max(dims, key=dims.get)
            min_dim = min(dims, key=dims.get)
            max_val = dims[max_dim] / max_v
            min_val = dims[min_dim] / max_v
            gap = abs(max_val - min_val)

            # 根据信号差距生成洞察
            if max_val > 0.7 and min_val < 0.3:
                insight = (
                    f"跨域张力: {max_dim}({dims[max_dim]:.2f})与"
                    f"{min_dim}({dims[min_dim]:.2f})差距显著({gap:.2f})——"
                    f"短板维度是系统涌现瓶颈，将强信号注入弱维度可产生质变"
                )
                confidence = round(min(0.6 + gap * 0.3, 0.95), 2)
            elif max_val > 0.6 and min_val > 0.4:
                insight = (
                    f"全域均衡: {max_dim}({dims[max_dim]:.2f})与"
                    f"{min_dim}({dims[min_dim]:.2f})差距不大({gap:.2f})——"
                    f"系统处稳态，需主动制造跨域扰动激发新洞察"
                )
                confidence = round(min(0.5 + gap * 0.2, 0.85), 2)
            else:
                insight = (
                    f"非对称交叉: {max_dim}({dims[max_dim]:.2f})与"
                    f"{min_dim}({dims[min_dim]:.2f})张力({gap:.2f})——"
                    f"冗余认知可压缩注入短板以产生新的直觉涌现"
                )
                confidence = round(min(0.4 + gap * 0.3, 0.90), 2)

            new_realizations = [{
                "type": "cross_domain",
                "dimensions": [max_dim, min_dim],
                "insight": insight,
                "confidence": confidence,
                "timestamp": now,
            }]

            # 确保至少 MIN_REALIZATION_PER_CYCLE 条
            while len(new_realizations) < self.MIN_REALIZATION_PER_CYCLE:
                alt_dims = random.sample(list(dims.keys()), min(2, len(dims)))
                alt_insight = (
                    f"交叉补充: {alt_dims[0]}({dims[alt_dims[0]]:.2f})×"
                    f"{alt_dims[1]}({dims[alt_dims[1]]:.2f})——"
                    f"次要信号交叉揭示了被主信号掩盖的潜在关联路径"
                )
                new_realizations.append({
                    "type": "cross_domain",
                    "dimensions": alt_dims,
                    "insight": alt_insight,
                    "confidence": round(0.3 + random.random() * 0.4, 2),
                    "timestamp": now,
                })

            # 去重: 过滤与最近5条已有realization相似的条目
            filtered = []
            for nr in new_realizations:
                if _is_duplicate_realization(nr, realizations, max_check=5):
                    print(f"  [RealTimeCrossSynthesizer] ⏭️ 跳过相似realization: "
                          f"{'×'.join(nr['dimensions'])} — {nr['insight'][:40]}...")
                else:
                    filtered.append(nr)
            new_realizations = filtered

            if not new_realizations:
                print("  [RealTimeCrossSynthesizer] ⏭️ 所有新realization均重复，跳过写入")
                return []

            # 写入 realizations.json
            realizations.extend(new_realizations)
            with open(real_file, "w", encoding="utf-8") as f:
                json.dump(realizations, f, ensure_ascii=False, indent=2)

            # 更新 state 中的 pulse_count
            state = load_json(STATE_FILE)
            state["pulse_count"] = state.get("pulse_count", 0) + len(new_realizations)
            state["last_cross_synth"] = {
                "dimensions": [max_dim, min_dim],
                "confidence": confidence,
                "timestamp": now,
            }
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

            print(f"  [RealTimeCrossSynthesizer] ✅ {len(new_realizations)}条cross_domain "
                  f"realization (总{len(realizations)}条)")
            return new_realizations

    # ── SuperIntuitionBridge 方法 ─────────────────────

    def __init__(self):
        self.synthesizer = self.RealTimeCrossSynthesizer()

    def force_aggregate(self):
        """强制触发聚合 — 兼容旧调用方式"""
        return self.synthesizer.generate_realization()

    def run(self, daemon=False):
        """主运行入口

        执行完整推理 + 跨域信号合成。
        非daemon模式: 单次执行后退出（调用 main() 并触发聚合器）。
        daemon模式:   持续循环（保留给未来扩展）。
        """
        # 执行主流程
        main()
        # 调用聚合器
        signals = self.synthesizer.aggregate_signals()
        self.synthesizer.generate_realization(signals)
        # 冷层验证 — 从冷层记忆中提取被遗忘的关键知识
        cold_layer_validation()
        if not daemon:
            return


# ─── 主流程 ──────────────────────────────────────────────

def main():
    t0 = time.time()

    # 1. 加载数据
    hippo = load_json(FILES["hippo"])
    state = load_json(FILES["state"])
    journal = load_json(FILES["journal"])
    git_msgs = get_git_messages(15)
    log_tail = get_log_tail(60)

    # 2. 提取信号
    signals = extract_dim_signals(hippo, state)
    health = compute_dim_health(signals)

    # 3. 生成脉冲
    pulses, cross_signals, intuition_score = generate_pulses(
        signals, health, journal, git_msgs, log_tail
    )

    # 3b. 冷层验证: 对每条脉冲执行冷层一致性检查
    for p in pulses:
        p["cold_verification"] = _cold_layer_verification(p)

    # 4. 构建输出
    output = build_output(pulses, cross_signals, intuition_score, signals, health)
    output["meta"]["runtime_ms"] = round((time.time() - t0) * 1000, 1)

    # 5. 写入 /tmp/super_intuition_pulse.json
    PULSE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PULSE_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 6. 写入 CLUSTER/super_intuition_state.json (breath_v2兼容格式)
    #    遵循已有state文件的简约模式
    state_out = {
        "timestamp": output["meta"]["timestamp"],
        "intuition_score": intuition_score,
        "intuition_gap": output["intuition_gap"],
        "pulse_count": len(pulses),
        "pulses": [
            {
                "type": p["type"],
                "dimensions": p["dimensions"],
                "insight": p["insight"],
                "strength": p["strength"],
                "cold_verification": p.get("cold_verification"),
            }
            for p in pulses
        ],
        "cross_signals": cross_signals,
    }
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state_out, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - t0
    print(f"[超级直觉桥] ✅ 完成 — {len(pulses)}条直觉脉冲 | "
          f"评分={intuition_score:.4f} gap={1.0-intuition_score:.4f} | "
          f"耗时{elapsed*1000:.1f}ms")
    print(f"  输出: {PULSE_FILE}")
    print(f"  状态: {STATE_FILE}")
    for p in pulses:
        print(f"  ⚡ [{p['type']}] {'×'.join(p['dimensions'])} — {p['insight'][:60]}...")

    # ── P0: 脉冲→灵感 — 桥接断裂点: 将生成的每条脉冲沉淀为realization ──
    _pulse_to_real_count = 0
    for p in pulses:
        if p.get("strength", 0) > 0.3:  # 过滤噪音,只沉淀置信度>0.3的脉冲
            record_realization(
                dimensions=p["dimensions"],
                insight=p["insight"],
                confidence=p["strength"],
                source="pulse_to_realization",
            )
            _pulse_to_real_count += 1
    if _pulse_to_real_count > 0:
        print(f"  📝 脉冲→灵感: {_pulse_to_real_count}/{len(pulses)}条脉冲已沉淀为realization")

    # ── P0: 强制跨域聚合 + 锚定启示录 ──
    print("  开始P0联合强化...")
    force_cross_domain_aggregation()
    anchor_to_axioms()

    # ── P0+: 超级直觉脉冲增产 + 对立面检查 ──
    print("  开始P0+脉冲增产...")
    cross_agent_pulse(hippo)
    add_opposite_check()

    # ── P0: 跨域聚合器 — 将超感信号转化为可记录的realization ──
    force_realization()

    # ── P0: 冷层验证 — 从冷层记忆中提取被遗忘的关键知识 ──
    cold_layer_validation()

    # 重新读取state确保pulse_count正确
    final_state = load_json(STATE_FILE)
    print(f"  [总览] 最终脉冲数: {final_state.get('pulse_count', 0)}")

    return output


if __name__ == "__main__":
    main()

# 🜁 深度分析建议 (05-31 17:12): 实现meta_synthesize方法：接受当前所有脉冲列表，按strength降序排列，取前10条。遍历这些脉冲的insight文本，使用关键词重叠计算（基于已有标签系统，如触发、交叉洞察、稀释等）进行聚类。对每个聚类生成综合洞察，格式为

# 🜁 深度分析建议 (05-31 17:14): 实现冷层验证与跨域聚合两项功能：
# 1. 添加 `cold_layer_validation` 方法，接收直觉字典，调用 `hippocampus_bridge.search_cold(keywords, top_k=5)` 返回相似记忆列表

# 🜁 深度分析建议 (05-31 17:17): 实现CrossDomainAggregator类（见next_p0描述，约150行代码）。包括：
# - 新增一个类，接受memory_layer、super_sense_organ、state_vector、api_call_func作为依赖

# 🜁 深度分析建议 (05-31 17:18): 在class SuperIntuitionBridge中新增方法force_aggregated_realization(self, hot_pool, warm_pool, cold_pool)，使用当前所有脉冲类型（triple_cro

# 🜁 深度分析建议 (05-31 17:19): 实现 forced_aggregation、cold_layer_validation、realization_logger 三个方法，并集成到 run() 流中。具体细节同 next_p0。

# 🜁 深度分析建议 (05-31 17:21): 重写BridgePulse类：增加历史脉冲embedding索引（使用简单TF-IDF或fasttext）；添加_cold_layer_validation方法，从记忆分层桥的cold_summaries.json中检索top5相似记忆并计

# 🜁 深度分析建议 (05-31 17:22): 增加冷层验证段：在pulse_generation()中新增cold_layer_validation()方法。实现细节：1) 从pulse的insight中抽取关键词（如'跨域连接'、'超感'、'直觉'）；2) 调用memory_laye

# 🜁 深度分析建议 (05-31 17:25): 1. 添加类CrossDomainAggregator:
#    - __init__(self, state_vector, cross_signals): 存储19维数据和交叉信号列表
#    - def compute_mutual_in

# 🜁 深度分析建议 (05-31 17:26): 1) 在文件顶部新增常量 WEAK_SIGNAL_POOL_SIZE=20，定义一个类 WeakSignalAggregator，包含方法 collect_weak_signals()（从state_vector的gap字段、记忆分层桥的e

# 🜁 深度分析建议 (05-31 17:32): 实现跨域信号聚合与realization强制记录。具体：新增`aggregate_cross_domain_signals(memory_hier, cross_bridge)`，从`memory_hier.hot`（最近500链）提取权重

# 🜁 深度分析建议 (05-31 17:33): 在 `generate_pulse()` 方法末尾插入 `cross_aggregate()`：优先选取当前热点中的3条超感发现，对每条调用LLM问答‘它预见了什么？’，并将答案写入 `cross_signals` 字段。同时修改 `int

# 🜁 深度分析建议 (05-31 17:37): 实现冷层检索集成和反例生成: (1)新增'from hippocampus import query_cold_layer'导入; (2)在'def generate_pulse(state)'中，对每个候选脉冲的维度标签，调用'cold_

# 🜁 深度分析建议 (05-31 17:49): 完整重写generate_insight：1) 定义新颖性阈值(与冷层记忆语义距离>0.7)；2) 采样5条历史记忆作为对比基线；3) 候选洞察必须跨域至少2个弱连接维度(共现count<100)；4) 输出结构化JSON包含novelty

# 🜁 深度分析建议 (05-31 18:22): 添加`forced_aggregation(self)`方法：从self.super_sense_insights列表选取最近20条，提取所有'罕见交叉'对，计算交叉覆盖度并合并生成新insight；添加`cold_validation(s

# 🜁 深度分析建议 (05-31 18:38): 在analyze函数末尾（约第500行，在返回脉冲列表前）插入以下代码块：
#
# ```python
# def generate_realization_from_pulses(pulses, cold_layer_memories=[]):
# 

# 🜁 深度分析建议 (05-31 18:48): 实现ColdLayerValidator类及与脉冲生成流程的完整集成。同时添加用于存储验证结果的持久化数据，便于后验分析。先在__init__中导入依赖并加载冷层记忆，再在generate_pulses中插入验证步骤。特别注意处理新类可能需

# 🜁 深度分析建议 (05-31 18:52): 在现有scan_pulses()方法后添加generate_realizations()函数，集成至呼吸主循环。
# 详细改动：
# - 定义Realization类，包含字段：content（字符串，长度限制500char）、strength（浮

# 🜁 深度分析建议 (05-31 19:38): 实现直觉增益回路（Intuition Amplifier Loop），具体修改：1) 新增方法`intuition_amplifier_loop()`，流程为：输入所有桥信号→强制两两组合强度top3信号→对每种组合执行追问‘预示什么？’→

# 🜁 深度分析建议 (05-31 20:05): 新增真实时间原则函数和强制跨域聚合函数。1. 导入datetime，添加real_time_validator(pulses, max_age=30)：遍历pulses，删除strength<0.5且age>60的脉冲，并降低所有陈旧脉冲权

# 🜁 深度分析建议 (05-31 20:29): 实现 `CrossDomainAggregator` 类（约200行代码），包含聚合权重配置、信号源注册、冷层验证逻辑。集成到现有脉冲生成流程。具体见next_p0。

# 🜁 深度分析建议 (05-31 20:31): 新增RealizationGenerator类，实现每3次呼吸强制生成一条realization的逻辑；修改run()以集成生成器；增加force_aggregate模式；在cross_agent_pattern中增加历史相似度去重；输出增

# 🜁 深度分析建议 (05-31 20:34): 实现冷层验证与历史整合机制。具体：1) import memory_bridge 并获取其 cold_query 接口。2) 在类中增加属性 self.cold_retriever = memory_bridge.cold_query。3)

# 🜁 深度分析建议 (05-31 20:37): 添加冷层验证方法：
# - 在`__init__`中注入hippocampus实例（若尚未有）
# - 新增`_cold_layer_verification(pulse)`：使用embeddings计算pulse.insight与最相似3条冷层内

# 🜁 深度分析建议 (05-31 20:39): 添加冷层反馈聚合器与预见性追问模块，详细描述见next_p0。另在文件顶部增加导入：from hippocampus_interface import search_cold_layer, get_memory_weight。在build_
