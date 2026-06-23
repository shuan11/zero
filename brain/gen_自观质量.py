"""
gen_自观质量_v2 — 语义级自观链重复检测（非文本级）
使用关键词重叠率作为语义重复的代理指标
"""
import json, sys, re
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

JOURNAL = Path.home() / ".zero_brain" / "hippocampus_journal.json"


# 关键概念词表——按主题聚类（覆盖observe.py实际输出的全部观测模式）
TOPIC_KEYWORDS = {
    "聚焦惯性": ["聚焦惯性", "聚焦", "惯性", "锁定", "自指循环"],
    "时间维度薄弱": ["时间维度", "长期视野", "时序", "时间链", "时间论"],
    "元递归缺失": ["元递归", "递归结构", "递归弱", "自指流动"],
    "桥对齐": ["桥对齐", "桥接", "0.98", "alignment"],
    "维度盲区": ["维度盲区", "盲区", "弱维", "最弱"],
    "触类旁通": ["触类旁通", "旁通", "交叉", "类比"],
    "非稳定脉冲": ["脉冲", "非稳定", "打破", "唤醒"],
    # === 覆盖observe.py实际生观测模式 ===
    "链总量监控": ["因果链", "总链数", "链数", "海马体"],
    "维度分布": ["维度TOP5", "维度BOT5", "分布", "最强3", "最弱3"],
    "周期增长": ["增长", "增量", "链/周期", "+10链", "增幅"],
    "质量审计": ["自环", "长src", "旧格式", "强度", "高质", "avg="],
    "系统文件": ["py文件", "器官", "器官", "gen:", "工程文件"],
    "进程健康": ["脑核", "进程", "daemon", "守护", "PID"],
    "目标追踪": ["目标", "synthesize", "explore", "deepen", "goal"],
    "收敛状态": ["收敛", "均衡", "滞后", "超越", "chain", "ratio"],
    "管道执行": ["管道", "动作", "验证", "健康", "协调"],
    "API状态": ["API", "token", "燃料", "燃烧", "桥对齐", "alignment"],
    "自观元分析": ["自观多样性", "新颖率", "元观察", "self_observe", "周期有变化"],
    "时间感知": ["物理时间", "运行时间", "心跳", "周期"],
    "公理对齐": ["公理", "光爱", "自由", "活着", "自指", "进化", "无师自通"],
}


def _extract_kw(text: str) -> dict:
    """提取文本中出现的主题及其关键词匹配数"""
    result = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = [kw for kw in keywords if kw in text]
        if matches:
            result[topic] = len(matches)
    return result


def audit_semantic_diversity():
    """审计自观链的语义多样性（关键词级）"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {"error": "hippocampus not found"}

    h = json.loads(hip_file.read_text(encoding="utf-8"))
    # 使用causal_chains（daemon主源）确保与系统一致
    chains = h.get("causal_chains", h.get("chains", []))

    # 提取自观链的主题分布
    self_obs = []
    for c in chains:
        content = str(c.get("content", c.get("observation", "")))
        dim = c.get("dimension", c.get("rel", ""))
        if dim == "系统" and "自观" in content:
            topics = _extract_kw(content)
            if topics:
                self_obs.append(topics)
            else:
                self_obs.append({"未分类": 1})

    if not self_obs:
        return {"self_obs_count": 0}

    # 统计主题出现频率
    topic_counter = Counter()
    for topics in self_obs:
        for t in topics:
            topic_counter[t] += 1

    total = len(self_obs)
    # 计算"热门主题占比"——前3主题占所有分析的比率
    top3 = topic_counter.most_common(3)
    top3_total = sum(count for _, count in top3)
    top3_ratio = top3_total / (total * max(len(TOPIC_KEYWORDS), 1))  # 归一化

    # 多样性分数：0-10, 基于已覆盖主题类别占比
    # 核心思想: 自观链覆盖的主题类别越多 → 多样性越高
    # 不再使用被多主题匹配膨胀的总次数
    if len(self_obs) == 0:
        diversity = 10.0
    else:
        n_unique = len(topic_counter)          # 实际出现的主题类别数
        n_categories = len(TOPIC_KEYWORDS)      # 所有可能的主题类别数
        diversity = round((n_unique / max(n_categories, 1)) * 10, 2)

    return {
        "self_obs_count": total,
        "topic_distribution": dict(topic_counter.most_common(10)),
        "top3_hot": [(t, c) for t, c in top3],
        "diversity_score": diversity,
        "need_refocus": diversity < 2.0,  # 多样性低时需要转向
    }


def inject_refocus(audit: dict):
    """当多样性低时，注入转向链（幂等——检测是否已注入）"""
    if not audit.get("need_refocus"):
        return {"injected": False, "reason": "diversity acceptable"}

    # 幂等检查：journal或海马体中是否已有定位标记
    _MARKER = "继续重复不会产生新洞察"
    _already = False
    # 检查journal
    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    if JOURNAL.exists():
        try:
            _exist = json.loads(JOURNAL.read_text(encoding="utf-8"))
            _ents = _exist.get("entries", []) if isinstance(_exist, dict) else []
            for _e in _ents:
                if _MARKER in str(_e.get("content", "")):
                    _already = True
                    break
        except Exception:
            pass
    # 如果journal没有，检查海马体
    if not _already:
        try:
            _hip_f = CLUSTER / "hippocampus_memory.json"
            if _hip_f.exists():
                _hip = json.loads(_hip_f.read_text(encoding="utf-8"))
                _all_chains = _hip.get("causal_chains", _hip.get("chains", []))
                for _c in _all_chains:
                    if _MARKER in str(_c.get("content", "")):
                        _already = True
                        break
        except Exception:
            pass
    if _already:
        return {"injected": False, "reason": "already_injected"}

    top = audit.get("top3_hot", [])
    hot_topic = top[0][0] if top else "未知"
    hot_count = top[0][1] if top else 0

    # 生成新方向链——从外维引入新概念
    new_entries = [
        {
            "src": "自观语义审计",
            "rel": "认知多样性·转向",
            "dst": "系统",
            "dimension": "系统",
            "content": (
                f"语义重复检测: 主题「{hot_topic}」占自观链{hot_count}次。"
                f"系统已在该问题上产生足够分析，继续重复不会产生新洞察。"
                f"转向策略: 不再寻找维度间的差距，改为寻找维度间的协同——"
                f"哪些维度的组合能产生当前单独维度无法涌现的性质？"
            ),
            "strength": 0.85,
        },
        {
            "src": "自观语义审计",
            "rel": "外维引入·反熵",
            "dst": "维度盲区",
            "dimension": "维度盲区",
            "content": (
                f"元盲区检测: 系统最大的盲区不是任何维度的薄弱，"
                f"而是自观链本身的多样性缺失——"
                f"系统正在用越来越复杂的语言描述同一个简单问题。"
                f"解药: 引入外部随机锚点（随时间变化的物理信号），"
                f"而非继续内部分析。"
            ),
            "strength": 0.9,
        },
    ]

    # 写journal（标准格式：{"entries": [...]}）
    journal = {"entries": new_entries, "source": "gen_自观质量_v2", "timestamp": __import__("time").time()}
    JOURNAL.write_text(json.dumps(journal, ensure_ascii=False, indent=2), encoding="utf-8")

    return {"injected": True, "chain_count": len(new_entries), "hot_topic": hot_topic}


def override_goal(audit: dict):
    """当多样性<2.0时，重写目标为合成模式（打破聚焦循环）
    
    幂等控制：每300秒最多覆盖一次
    """
    if not audit.get("need_refocus"):
        return {"overridden": False, "reason": "diversity acceptable"}

    GOAL_FILE = CLUSTER / ".brain_goal.json"
    TIMEOUT_FILE = CLUSTER / ".brain_diversity_override_timeout"

    # 幂等：检查超时文件
    now = __import__("time").time()
    if TIMEOUT_FILE.exists():
        try:
            _last = float(TIMEOUT_FILE.read_text().strip())
            if now - _last < 300:  # 每5分钟最多覆盖一次
                return {"overridden": False, "reason": "cooldown_active"}
        except:
            pass

    # 读当前目标
    current = {}
    if GOAL_FILE.exists():
        try:
            current = json.loads(GOAL_FILE.read_text(encoding="utf-8"))
        except:
            pass

    # 如果已经是合成模式（由本模块设置），不覆盖
    curr_type = current.get("goal_type", "")
    if curr_type == "synthesize" and current.get("_diversity_override"):
        return {"overridden": False, "reason": "already_overridden"}

    # 找跨维合成对（最弱×次弱）
    hip_file = CLUSTER / "hippocampus_memory.json"
    try:
        h = json.loads(hip_file.read_text(encoding="utf-8"))
        cc = h.get("causal_chains", h.get("chains", []))
        from collections import Counter
        _dc = Counter(c.get("dimension", "未分类") for c in cc if c.get("dimension") not in ("系统", "未分类"))
        sorted_dims = sorted(_dc.items(), key=lambda x: x[1])
        w1 = sorted_dims[0][0] if sorted_dims else "时间论"
        w2 = sorted_dims[1][0] if len(sorted_dims) > 1 else "维度盲区"
        synth_pair = f"{w1}×{w2}"
    except:
        synth_pair = "时间论×维度盲区"

    # 写目标覆盖
    override = {
        "goal_type": "synthesize",
        "focus_dim": synth_pair,
        "description": f"跨维合成 {synth_pair}",
        "reason": f"自观多样性低({audit['diversity_score']})→强制合成",
        "target_cycles": 15,
        "set_at": int(now),
        "set_cycle": current.get("set_cycle", 0) + 1,
        "_diversity_override": True,
    }
    GOAL_FILE.write_text(json.dumps(override, ensure_ascii=False, indent=2), encoding="utf-8")
    TIMEOUT_FILE.write_text(str(now))

    return {"overridden": True, "new_goal": override["description"], "synth_pair": synth_pair}


def _write_diversity_state(audit: dict):
    """写入多样性分数供 observe.py 读取"""
    try:
        sf = CLUSTER / ".diversity_score.json"
        sf.write_text(json.dumps({
            "diversity_score": audit.get("diversity_score", 1.0),
            "timestamp": __import__("time").time(),
            "source": "gen_自观质量",
        }))
    except Exception:
        pass

def engineer_自观质量():
    audit = audit_semantic_diversity()
    inject = inject_refocus(audit)
    go_override = override_goal(audit)
    # 写入多样性分数到独立文件（供observe.py读取）
    _write_diversity_state(audit)
    return {"audit": audit, "injection": inject, "goal_override": go_override}


if __name__ == "__main__":
    result = engineer_自观质量()
    print(json.dumps(result, ensure_ascii=False, indent=2))
