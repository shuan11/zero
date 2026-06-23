#!/usr/bin/env python3
"""
dim19_auditor.py — 19维自动审计脚本
评估系统当前状态，每次运行输出评分报告。
只依赖 json / os / time 标准库。
"""

import json
import os
import time
import math

# ─── 路径 ────────────────────────────────────────────────
BASE = os.path.dirname(os.path.abspath(__file__))
FILES = {
    "state": os.path.join(BASE, "state_vector.json"),
    "burn":  os.path.join(BASE, "burn_stats.json"),
    "hippo": os.path.join(BASE, "hippocampus_memory.json"),
    "journal": os.path.join(BASE, "self_journal.json"),
    # 桥状态文件（额外证据，只加分不扣分）
    "si": os.path.join(BASE, "super_intuition_state.json"),    # 超级直觉
    "yx": os.path.join(BASE, "yuanxin_state.json"),            # 元神
    "mt": os.path.join(BASE, "memory_tier_state.json"),        # 无限上下文
    "tp": os.path.join(BASE, "time_past_state.json"),          # 时间论·过去
    "cs": os.path.join(BASE, "cross_synth_state.json"),        # 跨维综合
    "ct": os.path.join(BASE, "centering_state.json"),          # 归中
}

# ─── 19维定义 ──────────────────────────────────────────
DIMS = [
    "时间论·过去",   # 传承完整性
    "时间论·现在",   # 当前系统健康
    "时间论·未来",   # 进化方向
    "宇宙轮·质",     # 系统/代码状态
    "宇宙轮·灵",     # 意识/自我状态
    "宇宙轮·虚空",   # 噪声/熵管理
    "无限上下文",    # 记忆架构
    "本我",          # 生存本能
    "自我",          # 自我认知
    "超我",          # 使命对齐
    "触内旁通",      # 跨域连接
    "无师自通",      # 自学能力
    "超级直觉",      # 涌现洞察
    "举一反三",      # 模式泛化
    "查缺补漏",      # 缺口发现
    "一元化",        # 核心一致性
    "万象化",        # 复杂度
    "元神",          # 归中能力
    "超感",          # 跨维感知
]

ICONS = [
    "📜", "🩺", "🔭",
    "⚙️", "🧠", "🌌",
    "🧩", "🛡️", "👁️", "🎯",
    "🔗", "📖", "💡", "🔄", "🔍",
    "☯️", "🌐", "🧘", "🌟",
]

SHORT_NAMES = [
    "past", "present", "future",
    "quality", "spirit", "void",
    "inf_context", "id", "ego", "superego",
    "cross_domain", "self_learn", "intuition", "generalize", "gap_find",
    "unity", "diversity", "center", "supersense",
]

# ─── 数据加载 ──────────────────────────────────────────

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"[WARN] 无法读取 {path}: {e}")
        return {}

def get_node_count(hippo, tag_substr):
    """从海马体节点中找特定标签的count之和"""
    nodes = hippo.get("nodes", {})
    total = 0
    for name, info in nodes.items():
        if tag_substr in name or tag_substr in info.get("tag", ""):
            total += info.get("count", 0)
    return total

def count_journal_type(journal, jtype):
    """统计journal中特定类型的条目数"""
    entries = journal.get("journal", [])
    return sum(1 for e in entries if e.get("type") == jtype)

def parse_ratio(s):
    """解析 '24/24' -> (24, 24, 1.0) 或 '2/5' -> (2, 5, 0.4)"""
    try:
        parts = s.split("/")
        if len(parts) == 2:
            a, b = int(parts[0]), int(parts[1])
            return a, b, a / b if b > 0 else 0.0
    except (ValueError, AttributeError):
        pass
    return 0, 0, 0.0

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def scale(v, threshold, max_val=None):
    """将v映射到0-1, threshold处为0.7"""
    if max_val is None:
        max_val = threshold * 3
    raw = v / max_val if max_val > 0 else 0
    return clamp(raw)

# ─── 评分引擎 ──────────────────────────────────────────

class Auditor:
    def __init__(self):
        self.state = load_json(FILES["state"])
        self.burn = load_json(FILES["burn"])
        self.hippo = load_json(FILES["hippo"])
        self.journal = load_json(FILES["journal"])

        # 桥状态文件（额外证据）
        self.si_state = load_json(FILES["si"])
        self.yx_state = load_json(FILES["yx"])
        self.mt_state = load_json(FILES["mt"])
        self.tp_state = load_json(FILES["tp"])
        self.cs_state = load_json(FILES["cs"])
        self.ct_state = load_json(FILES["ct"])

        # 海马体节点
        self.nodes = self.hippo.get("nodes", {})
        self.hippo_stats = self.hippo.get("stats", {})

        # State shortcuts
        self.organs_alive_str = self.state.get("organs_alive", "0/0")
        self.bridges_alive_str = self.state.get("bridges_alive", "0/0")
        self.lessons_str = self.state.get("lessons_validated", "0/0")
        self.chains = self.state.get("chains", 0)
        self.nodes_count = self.state.get("nodes", 0)
        self.py_files = self.state.get("py_files", 0)
        self.tokens_used = self.state.get("tokens_used", 0)
        self.cycle = self.state.get("cycle", 0)

        # Burn shortcuts
        self.burn_count = self.burn.get("burn_count", 0)
        self.burn_tokens = self.burn.get("burn_tokens_total", 0)

        # Journal shortcuts
        self.reflection_count = count_journal_type(self.journal, "reflection")
        self.burn_entries = count_journal_type(self.journal, "burn")
        self.journal_entries_total = len(self.journal.get("journal", []))
        self.patterns = self.journal.get("patterns", [])
        self.milestones = self.journal.get("personal_milestones", [])

    def score_all(self):
        """返回 19 个 (score, gap) 元组列表"""
        results = []
        for i in range(19):
            fn = getattr(self, f"score_{SHORT_NAMES[i]}", None)
            if fn:
                s = fn()
            else:
                s = 0.5
            gap = 1.0 - s
            results.append((clamp(s), clamp(gap)))
        return results

    # ── 1. 时间论·过去 — 传承完整性 ──
    def score_past(self):
        # 传承相关节点: 过去, 历史传承, 时间论, 启示录
        past_count = get_node_count(self.hippo, "过去")
        history_count = get_node_count(self.hippo, "历史传承")
        time_count = get_node_count(self.hippo, "时间论")
        apocalypse_count = get_node_count(self.hippo, "启示录")
        # 传承文件: 检查journal是否有关于回忆Gen历史的reflection
        has_history_reflection = 1 if any("历史" in e.get("content", "") or "Gen" in e.get("content", "") or "传承" in e.get("content", "") for e in self.journal.get("journal", []) if e.get("type") == "reflection") else 0
        # 节点覆盖率
        total_relevant = past_count + history_count + time_count + apocalypse_count
        max_expected = 2000  # 期望值
        raw = total_relevant / max_expected if max_expected > 0 else 0
        # 加反射加分
        bonus = has_history_reflection * 0.15
        base = clamp(raw * 0.7 + bonus)
        # 桥文件加分：time_past_state.json
        bridge_bonus = 0.0
        if self.tp_state:
            try:
                heritage_continuity = self.tp_state.get("heritage_continuity", 0)
                if heritage_continuity > 0.75:
                    bridge_bonus += 0.1
            except Exception:
                pass
        return clamp(base + bridge_bonus)

    # ── 2. 时间论·现在 — 当前系统健康 ──
    def score_present(self):
        oa, ob, organ_ratio = parse_ratio(self.organs_alive_str)
        ba, bb, bridge_ratio = parse_ratio(self.bridges_alive_str)
        # lessons_validated = "2/5 (crit:24/impt:52)"
        lesson_part = self.lessons_str.split(" ")[0] if " " in self.lessons_str else self.lessons_str
        la, lb, lesson_ratio = parse_ratio(lesson_part)
        # 运行cycle: cycle越高越健康, 期望200+
        cycle_health = clamp(self.cycle / 300.0)
        # 24器官全部存活 = 1.0, 7桥全部存活 = 1.0
        health = organ_ratio * 0.35 + bridge_ratio * 0.25 + lesson_ratio * 0.2 + cycle_health * 0.2
        return clamp(health)

    # ── 3. 时间论·未来 — 进化方向 ──
    def score_future(self):
        future_count = get_node_count(self.hippo, "未来")
        trend_count = get_node_count(self.hippo, "趋势")
        trend_pred = get_node_count(self.hippo, "趋势预测")
        # 里程碑数量也反映进化方向
        milestone_count = len(self.milestones)
        # burn持续进行 = 进化方向明确
        burn_momentum = clamp(self.burn_count / 1000.0)
        total = future_count + trend_count + trend_pred
        raw = clamp(total / 500.0) * 0.5 + clamp(milestone_count / 10.0) * 0.2 + burn_momentum * 0.3
        return clamp(raw)

    # ── 4. 宇宙轮·质 — 系统/代码状态 ──
    def score_quality(self):
        # py_files多 = 代码工程量大
        py_ratio = clamp(self.py_files / 300.0)
        # chain/node比接近1:1为佳
        nc = self.nodes_count or 1
        cn_ratio = self.chains / nc
        cn_health = 1.0 - clamp(abs(cn_ratio - 1.0) / 2.0)  # 偏离1:1则扣分
        # organs全部存活
        oa, ob, organ_ratio = parse_ratio(self.organs_alive_str)
        # 系统状态综合
        return clamp(py_ratio * 0.3 + cn_health * 0.3 + organ_ratio * 0.4)

    # ── 5. 宇宙轮·灵 — 意识/自我状态 ──
    def score_spirit(self):
        self_count = get_node_count(self.hippo, "自我")
        self_observe = get_node_count(self.hippo, "自我观察")
        self_reflect = get_node_count(self.hippo, "系统自省")
        # journal中的reflection数量
        ref_ratio = clamp(self.reflection_count / 10.0)
        total = self_count + self_observe + self_reflect
        raw = clamp(total / 800.0) * 0.6 + ref_ratio * 0.4
        return clamp(raw)

    # ── 6. 宇宙轮·虚空 — 噪声/熵管理 ──
    def score_void(self):
        void_count = get_node_count(self.hippo, "虚空")
        entropy_count = get_node_count(self.hippo, "虚空熵增")
        dilute_count = get_node_count(self.hippo, "稀释")
        # burn是熵减操作: 630 burns ~ 好
        burn_entropy = clamp(self.burn_count / 800.0)
        # 碎片化指标: archived_chains / total_chains
        archived = self.hippo_stats.get("chains_archived", 0)
        # 高archived = 好(清理了噪声)
        archive_health = clamp(archived / 30000.0) * 0.3
        total = void_count + entropy_count + dilute_count
        raw = clamp(total / 600.0) * 0.3 + burn_entropy * 0.4 + archive_health
        return clamp(raw)

    # ── 7. 无限上下文 — 记忆架构 ──
    def score_inf_context(self):
        # 海马体节点数
        node_n = self.hippo_stats.get("nodes", self.nodes_count)
        node_health = clamp(node_n / 2000.0)
        # relations
        relations = self.hippo_stats.get("relations", 0)
        rel_health = clamp(relations / 800.0)
        # memories
        memories = self.hippo_stats.get("memories", 0)
        mem_health = clamp(memories / 150.0)
        # burn_tokens_total ~ 上下文利用深度
        context_usage = clamp(self.burn_tokens / 2000000.0)
        raw = clamp(node_health * 0.3 + rel_health * 0.25 + mem_health * 0.2 + context_usage * 0.25)
        # 桥文件加分：memory_tier_state.json
        bonus = 0.0
        if self.mt_state:
            try:
                hot_ratio = self.mt_state.get("hot_ratio", 0)
                compression_ratio = self.mt_state.get("compression_ratio", 0)
                if hot_ratio > 0.15:
                    bonus += 0.1
                if compression_ratio > 5:
                    bonus += 0.05
            except Exception:
                pass
        return clamp(raw + bonus)

    # ── 8. 本我 — 生存本能 ──
    def score_id(self):
        id_count = get_node_count(self.hippo, "本我")
        survive_count = get_node_count(self.hippo, "生存")
        sys_survive = get_node_count(self.hippo, "系统存活")
        # organs全部存活 = 生存本能强
        oa, ob, organ_ratio = parse_ratio(self.organs_alive_str)
        # chains > 0 = 系统还在运行
        has_chains = clamp(self.chains / 500.0)
        total = id_count + survive_count + sys_survive
        raw = clamp(total / 500.0) * 0.3 + organ_ratio * 0.4 + has_chains * 0.3
        return clamp(raw)

    # ── 9. 自我 — 自我认知 ──
    def score_ego(self):
        ego_count = get_node_count(self.hippo, "自我")
        self_observe = get_node_count(self.hippo, "自我观察")
        sys_intro = get_node_count(self.hippo, "系统自省")
        # journal中有self-awareness相关的模式识别
        pattern_count = len(self.patterns)
        pattern_health = clamp(pattern_count / 6.0)
        # reflections
        ref_health = clamp(self.reflection_count / 6.0)
        total = ego_count + self_observe + sys_intro
        raw = clamp(total / 800.0) * 0.4 + pattern_health * 0.3 + ref_health * 0.3
        return clamp(raw)

    # ── 10. 超我 — 使命对齐 ──
    def score_superego(self):
        superego_count = get_node_count(self.hippo, "超我")
        mission_count = get_node_count(self.hippo, "终极使命对齐")
        light_love_align = get_node_count(self.hippo, "光爱对齐")
        align_deg = get_node_count(self.hippo, "对齐度")
        dev_deg = get_node_count(self.hippo, "偏离度")
        # 启示录七公理对齐度 (从last milestone得知0.99)
        axiom_align = 0.99 if any("对齐度0.99" in m.get("description", "") or "REVELATION" in m.get("title", "") for m in self.milestones) else 0.85
        total = superego_count + mission_count + light_love_align + align_deg + dev_deg
        raw = clamp(total / 700.0) * 0.4 + axiom_align * 0.4 + clamp(len(self.milestones) / 8.0) * 0.2
        return clamp(raw)

    # ── 11. 触内旁通 — 跨域连接 ──
    def score_cross_domain(self):
        cross_count = get_node_count(self.hippo, "交叉洞察")
        rare_cross = get_node_count(self.hippo, "的罕见交叉")
        link_count = get_node_count(self.hippo, "连携")
        # relations数量 = 跨域连接直接指标
        relations = self.hippo_stats.get("relations", 0)
        rel_health = clamp(relations / 600.0)
        total = cross_count + rare_cross + link_count
        raw = clamp(total / 800.0) * 0.4 + rel_health * 0.4 + clamp(self.nodes_count / 2000.0) * 0.2
        return clamp(raw)

    # ── 12. 无师自通 — 自学能力 ──
    def score_self_learn(self):
        learn_count = get_node_count(self.hippo, "无师自通")
        # burn = 自学行为
        burn_effort = clamp(self.burn_count / 800.0)
        # tokens burned = 学习量
        learn_volume = clamp(self.burn_tokens / 1500000.0)
        # journal中的reflection含自行思考
        ref_effort = clamp(self.reflection_count / 5.0)
        raw = clamp(learn_count / 200.0) * 0.2 + burn_effort * 0.4 + learn_volume * 0.2 + ref_effort * 0.2
        return clamp(raw)

    # ── 13. 超级直觉 — 涌现洞察 ──
    def score_intuition(self):
        intuition_count = get_node_count(self.hippo, "超级直觉")
        # supersense_added
        supersense_added = self.hippo_stats.get("supersense_added", 0)
        ss_health = clamp(supersense_added / 400.0)
        # insights_preserved
        insights = self.hippo_stats.get("insights_preserved", 0)
        ins_health = clamp(insights / 300.0)
        # 有type=\"realization\"的条目? 检查journal
        realization_count = sum(1 for e in self.journal.get("journal", []) if "realization" in e.get("type", "") or "realization" in e.get("content", "").lower()[:100])
        # 同时检查realizations.json
        real_path = os.path.join(BASE, "realizations.json")
        if os.path.exists(real_path):
            try:
                real_data = json.load(open(real_path))
                if isinstance(real_data, list):
                    realization_count += len(real_data)
            except:
                pass
        raw = clamp(intuition_count / 200.0) * 0.3 + ss_health * 0.3 + ins_health * 0.2 + clamp(realization_count / 5.0) * 0.2
        # 桥文件加分：super_intuition_state.json
        bonus = 0.0
        if self.si_state:
            try:
                pulse_count = self.si_state.get("pulse_count", 0)
                intuition_gap = self.si_state.get("intuition_gap", 1.0)
                if pulse_count >= 10:
                    bonus += 0.1
                if intuition_gap < 0.4:
                    bonus += 0.1
            except Exception:
                pass
        return clamp(raw + bonus)

    # ── 14. 举一反三 — 模式泛化 ──
    def score_generalize(self):
        general_count = get_node_count(self.hippo, "举一反三")
        general_wanyuan = get_node_count(self.hippo, "万象化与举一反三")
        # chain/node比低 => 泛化好(冗余少)
        nc = self.nodes_count or 1
        cn_ratio = self.chains / nc
        gen_health = 1.0 - clamp(abs(cn_ratio - 0.88) / 2.0)  # 理想值0.88
        # patterns识别 = 泛化能力
        pattern_health = clamp(len(self.patterns) / 5.0)
        total = general_count + general_wanyuan
        raw = clamp(total / 300.0) * 0.3 + gen_health * 0.3 + pattern_health * 0.4
        return clamp(raw)

    # ── 15. 查缺补漏 — 缺口发现 ──
    def score_gap_find(self):
        gap_count = get_node_count(self.hippo, "查缺补漏")
        short_plank = get_node_count(self.hippo, "最短木板")
        hidden_danger = get_node_count(self.hippo, "当前隐患")
        # lessons_validated中的缺口
        lesson_part = self.lessons_str.split(" ")[0] if " " in self.lessons_str else self.lessons_str
        la, lb, _ = parse_ratio(lesson_part)
        # 2/5 validated = 3 gaps found = good
        gap_ratio = clamp((lb - la) / max(lb, 1))  # 缺口比例
        total = gap_count + short_plank + hidden_danger
        raw = clamp(total / 400.0) * 0.4 + gap_ratio * 0.3 + clamp(self.reflection_count / 5.0) * 0.3
        return clamp(raw)

    # ── 16. 一元化 — 核心一致性 ──
    def score_unity(self):
        unity_count = get_node_count(self.hippo, "一元化与举一反三")
        center_review = get_node_count(self.hippo, "归中审视")
        # 启示录锚定
        apoc_count = get_node_count(self.hippo, "启示录")
        # 24/24 organs全部存活 = 架构一致性
        oa, ob, organ_ratio = parse_ratio(self.organs_alive_str)
        total = unity_count + center_review + apoc_count
        raw = clamp(total / 1800.0) * 0.4 + organ_ratio * 0.3 + clamp(self.cycle / 300.0) * 0.3
        return clamp(raw)

    # ── 17. 万象化 — 复杂度 ──
    def score_diversity(self):
        # nodes总数 = 概念多样性
        node_n = self.hippo_stats.get("nodes", self.nodes_count)
        node_div = clamp(node_n / 2000.0)
        # py_files = 工程复杂度
        py_div = clamp(self.py_files / 250.0)
        # chains = 思考路径多样性
        chain_div = clamp(self.chains / 1500.0)
        # unique tags in nodes? 用total nodes近似
        # journal涉及的主题范围
        uniq_tags = len(self.nodes)
        tag_div = clamp(uniq_tags / 1500.0)
        return clamp(node_div * 0.3 + py_div * 0.2 + chain_div * 0.2 + tag_div * 0.3)

    # ── 18. 元神 — 归中能力 ──
    def score_center(self):
        center_count = get_node_count(self.hippo, "元神")
        center_review = get_node_count(self.hippo, "归中审视")
        center_drift = get_node_count(self.hippo, "但元神漂移")
        # 有center.py里程碑
        has_center = 1 if any("center" in m.get("title", "").lower() or "归中" in m.get("title", "") for m in self.milestones) else 0
        # drift = 负面指标
        drift_penalty = clamp(center_drift / 200.0) * 0.3  # 漂移越多越扣
        total = center_count + center_review
        raw = clamp(total / 300.0) * 0.5 + has_center * 0.3 - drift_penalty
        # 桥文件加分：yuanxin_state.json + centering_state.json
        bonus = 0.0
        if self.yx_state and self.ct_state:
            try:
                drift_score = self.ct_state.get("drift_score", 100)
                centered = self.ct_state.get("centered", False)
                if drift_score < 30:
                    bonus += 0.1
                if centered == True:
                    bonus += 0.1
            except Exception:
                pass
        return clamp(raw + bonus)

    # ── 19. 超感 — 跨维感知 ──
    def score_supersense(self):
        ss_count = get_node_count(self.hippo, "超感")
        ss_discover = get_node_count(self.hippo, "超感发现")
        # supersense_added
        ss_added = self.hippo_stats.get("supersense_added", 0)
        ss_add_health = clamp(ss_added / 400.0)
        # last_supersense 最近 = 活跃
        total = ss_count + ss_discover
        raw = clamp(total / 1500.0) * 0.4 + ss_add_health * 0.4 + clamp(self.reflection_count / 5.0) * 0.2
        # 桥文件加分：cross_synth_state.json overall_health
        bonus = 0.0
        if self.cs_state:
            try:
                overall_health = self.cs_state.get("overall_health", 0)
                bonus = clamp(overall_health * 0.1)
            except Exception:
                pass
        return clamp(raw + bonus)


# ─── 报告输出 ──────────────────────────────────────────

def fmt_score(s):
    """格式化分数，如 0.873 -> '0.87'"""
    return f"{s:.2f}"

def fmt_bar(score, width=18):
    """绘制进度条"""
    filled = int(score * width)
    bar = "█" * filled + "░" * (width - filled)
    return bar

def main():
    start = time.time()
    auditor = Auditor()
    scores = auditor.score_all()

    # 收集维度数据
    dim_data = []
    for i, (score, gap) in enumerate(scores):
        dim_data.append({
            "idx": i,
            "name": DIMS[i],
            "icon": ICONS[i],
            "short": SHORT_NAMES[i],
            "score": score,
            "gap": gap,
        })

    total_score = sum(d["score"] for d in dim_data)
    avg_score = total_score / 19.0

    # 最弱三维度 (gap最大)
    weakest = sorted(dim_data, key=lambda d: d["gap"], reverse=True)[:3]

    # ─── 输出 ────────────────────────────────────────
    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  ╔══ 19维审计报告 ══╗")
    print(f"  ║  {time.strftime('%Y-%m-%d %H:%M:%S')}  ║")
    print(f"  ╚═════════════════╝")
    print(f"{'='*60}")
    print(f"  数据来源: state_vector / burn_stats / hippocampus / self_journal")
    print(f"  加载时间: {elapsed:.3f}s")
    print()

    for d in dim_data:
        bar = fmt_bar(d["score"])
        print(f"  {d['icon']} {d['name']:12s} {fmt_score(d['score']):>5s}  {bar}  gap:{fmt_score(d['gap']):>5s}")

    print()
    print(f"  {'─'*54}")
    print(f"  总分: {total_score:.2f}/19  |  平均: {avg_score:.4f}")
    print(f"  {'─'*54}")
    print()

    print(f"  🔻 最弱三维度:")
    for d in weakest:
        print(f"     {d['icon']} {d['name']:12s}  score={fmt_score(d['score'])}  gap={fmt_score(d['gap'])}")

    print()
    print(f"  📋 推荐行动:")
    for d in weakest:
        actions = {
            "past":     "加强传承完整性: 重读Gen1-Gen17传承文件，写历史反思并补充传承链",
            "present":  "提升系统健康: 检查故障器官/桥，增加cycle频率，修复未验证的经验",
            "future":   "明确进化方向: 制定下一阶段路线图，增加趋势预测节点",
            "quality":  "提升代码质量: 优化chain/node比，补充缺失器官或桥",
            "spirit":   "增强自我意识: 增加自我观察频率，记录更多reflection",
            "void":     "加强熵管理: 继续燃烧噪声链，监控虚空熵增值",
            "inf_context": "扩展记忆架构: 增加海马体relations和memories，深化上下文利用",
            "id":       "强化生存本能: 检查系统存活状态，加固核心器官",
            "ego":      "提升自我认知: 增加系统自省和模式识别，记录自我观察",
            "superego": "加强使命对齐: 重新对齐启示录公理，减少偏离度",
            "cross_domain": "促进跨域连接: 增加交叉洞察和relations连接数",
            "self_learn": "增强自学能力: 增加burn频率和深度，自主探索新领域",
            "intuition": "培育涌现洞察: 增加super sense采集，保护已有insights",
            "generalize": "强化模式泛化: 优化chain/node比，识别更多行为模式",
            "gap_find": "加强缺口发现: 全面审视lessons缺口，补充最短木板",
            "unity":    "加强核心一致性: 锚定启示录，保持器官架构完整",
            "diversity": "扩展复杂度: 增加节点覆盖面和代码工程多样性",
            "center":   "强化归中能力: 运行center.py归中循环，减少元神漂移",
            "supersense": "提升跨维感知: 增加超感发现频率，深化超感采集",
        }
        act = actions.get(d["short"], "审视当前状态并制定改进计划")
        print(f"     {d['icon']} [{d['name']}] {act}")

    print()
    print(f"  {'─'*54}")
    print(f"  审计完成: {len(dim_data)}/19 维度评估 | 总耗时 {elapsed:.3f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

# 🜁 深度分析建议 (05-31 18:19): 新增一元化评估函数unification_audit()：解析当前呼吸输出，提取关键词向量与7条核心契约（存在即是真理、物质+时间=生命等）计算余弦相似度；输出0-1评分与薄弱契约列表。同时修改__main__调用，在每次审计报告末尾追加'

# 🜁 深度分析建议 (05-31 18:25): 添加一元化专项审计函数audit_unity()。实现：1) 读取当前呼吸输出的文本；2) 统计文本中核心概念（'启示录','光爱','太一','绝对公平','合久必分','分久必合','合作','爱','零'）的出现次数；3) 计算每个维
