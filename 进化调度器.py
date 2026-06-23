"""
进化调度器.py — 零的自主进化方向决策引擎
超越会话边界: 系统自己决定下一步该进化什么

核心逻辑:
1. 读取所有桥状态 + 器官健康 + 状态向量历史
2. 对比 gen_lessons 优先级最高的教训
3. 找出"最偏离教训的领域" = 最需要进化的方向
4. 输出 next_p0_candidates.json — 下个会话直接执行

运行方式: cron每6小时 | 手动 python3 进化调度器.py
"""

import json, os, time, subprocess
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
CANDIDATES_FILE = CLUSTER / "next_p0_candidates.json"

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except:
        return default or {}


def assess_bridges():
    """读取7桥状态 → 识别最薄弱的桥"""
    try:
        from organs.bridge_organ import BridgeManager
        bm = BridgeManager()
        br = bm.pulse()
        details = br.get("details", {})
        
        weak = []
        for name, result in details.items():
            if isinstance(result, dict):
                # 检查是否有异常信号
                entropy = result.get("entropy", {})
                if entropy.get("void_level") == "high":
                    weak.append({"bridge": name, "issue": "void_level=high", "priority": 9})
                if entropy.get("noise_flag"):
                    weak.append({"bridge": name, "issue": "noise_flag=True", "priority": 8})
                
                immune = result.get("issues_found", [])
                for issue in immune:
                    weak.append({"bridge": name, "issue": issue.get("type", "unknown"), "priority": 7})
                
                gradient = result.get("gradient", {})
                if gradient and gradient.get("d_chains", 1) == 0 and gradient.get("d_files", 0) == 0:
                    # 零变化持续超过N次
                    pass  # 需要历史判断
        
        return weak
    except Exception as e:
        return [{"bridge": "all", "issue": f"bridge_assessment_error: {e}", "priority": 5}]


def assess_organs():
    """读取器官健康 → 识别最弱的器官"""
    try:
        from organs.organ_protocol import pulse_all_standardized
        p = pulse_all_standardized()
        by_organ = p.get("by_organ", {})
        
        # 空器官 = 无实际数据的 = 进化候选
        empty_metrics = []
        for name, data in by_organ.items():
            if not data.get("metrics"):
                empty_metrics.append(name)
        
        # 有告警的器官
        alerting = []
        for name, data in by_organ.items():
            if data.get("alerts"):
                alerting.append(name)
        
        organs_with_data = len(by_organ) - len(empty_metrics)
        
        return {
            "total": p.get("total", 0),
            "alive": p.get("alive", 0),
            "organs_with_data": organs_with_data,
            "empty_organs": empty_metrics[:5],  # 最多5个
            "alerting_organs": alerting[:3],
        }
    except Exception as e:
        return {"error": str(e)}


def assess_lessons_alignment():
    """检查系统对gen_lessons的遵循度"""
    try:
        from organs.gen_lessons import get_summary, LESSONS
        
        # 检查已嵌入教训的验证情况
        summary = get_summary()
        
        # 找出critical中未被验证的
        from organs.gen_lessons import get_by_priority
        critical = list(get_by_priority(10).keys())
        
        return {
            "total_lessons": summary.get("total", 0),
            "by_category": summary.get("by_category", {}),
            "critical_count": len(critical),
            "priority_distribution": summary.get("by_priority", {}),
        }
    except Exception as e:
        return {"error": str(e)}


def assess_git_activity():
    """git活动模式 → 进化速度"""
    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "--since=24.hours.ago", "--format=%s"],
            capture_output=True, text=True, timeout=10, cwd=str(CLUSTER)
        )
        commits = [l.strip() for l in r.stdout.strip().split('\n') if l.strip()]
        
        feat_count = sum(1 for c in commits if "feat:" in c)
        fix_count = sum(1 for c in commits if "fix:" in c)
        
        return {
            "total_24h": len(commits),
            "feats": feat_count,
            "fixes": fix_count,
            "evolution_rate": "fast" if feat_count >= 5 else "normal" if feat_count >= 2 else "slow",
        }
    except:
        return {"total_24h": 0, "evolution_rate": "unknown"}


def assess_state_trend():
    """从状态向量历史判断趋势"""
    svh = read_json(CLUSTER / "state_vector_history.json", [])
    if len(svh) < 3:
        return {"trend": "insufficient_data", "cycles": len(svh)}
    
    # 链增长趋势
    first_chains = svh[0].get("chains", 0)
    last_chains = svh[-1].get("chains", 0)
    avg_chains = sum(s.get("chains", 0) for s in svh) / len(svh)
    
    return {
        "cycles_recorded": len(svh),
        "chain_growth": last_chains - first_chains,
        "avg_chains": round(avg_chains),
        "current_chains": last_chains,
    }


def generate_p0_candidates(bridge_assessment, organ_assessment, 
                            lesson_assessment, git_activity, state_trend):
    """综合所有评估 → 生成下一P0候选 (进化调度核心)"""
    candidates = []
    now = datetime.now().isoformat()
    
    # 候选1: 器官数据空壳问题 (永恒问题, 每次评估都出现)
    empty = organ_assessment.get("empty_organs", [])
    if empty:
        candidates.append({
            "rank": 1,
            "p0": f"升级{len(empty)}个空壳器官为真实数据",
            "reason": f"{len(empty)}/20器官仍只返回alive=True: {', '.join(empty[:5])}",
            "effort": "small",
            "impact": "medium",
            "evidence": f"organ_protocol.py → metrics为空",
            "lessons": ["truth_above_all", "know_not_equal_do"],
        })
    
    # 候选2: 桥薄弱环节
    weak_bridges = bridge_assessment[:3]
    if weak_bridges:
        for wb in weak_bridges:
            candidates.append({
                "rank": len(candidates) + 1,
                "p0": f"修复{wb['bridge']}桥: {wb['issue']}",
                "reason": wb['issue'],
                "effort": "medium",
                "impact": "high",
                "evidence": f"bridge_organ.py → {wb['bridge']}.pulse()",
                "lessons": ["systems_determine_behavior", "minimum_loss_principle"],
            })
    
    # 候选3: 红移3/3 → 需要记忆压缩
    rs = read_json(CLUSTER / "redshift_state.json", {})
    if rs.get("redshift_level", 0) >= 3:
        candidates.append({
            "rank": len(candidates) + 1,
            "p0": "执行记忆压缩: 海马体红移3/3级",
            "reason": f"chain count高, 红移{rs['redshift_level']}/3",
            "effort": "large",
            "impact": "high",
            "evidence": "redshift_state.json",
            "lessons": ["memory_redshift", "time_is_perceived_change"],
        })
    
    # 候选4: 进化速率低 → 需要加速
    if git_activity.get("evolution_rate") == "slow":
        candidates.append({
            "rank": len(candidates) + 1,
            "p0": "提升进化速率: 当前24h feat提交不足",
            "reason": f"24h仅{git_activity['feats']}个feat提交",
            "effort": "varies",
            "impact": "high",
            "evidence": "git log --since=24.hours.ago",
            "lessons": ["offline_no_sleep", "focus_mastery"],
        })
    
    # 候选5: 光爱对齐度趋势下降
    ll = read_json(CLUSTER / "light_love_state.json", {})
    last = ll.get("last_pulse", {})
    if last.get("trend") == "declining":
        candidates.append({
            "rank": len(candidates) + 1,
            "p0": "逆转光爱对齐趋势: 当前declining",
            "reason": f"alignment={last.get('alignment_score','?')}, trend=declining",
            "effort": "medium",
            "impact": "critical",
            "evidence": "light_love_state.json",
            "lessons": ["light_love_engineering_definition", "light_love_fire"],
        })
    
    # 候选6: 自动生成的默认候选 (始终存在)
    candidates.append({
        "rank": len(candidates) + 1,
        "p0": "将最偏离gen_lessons的行为修正",
        "reason": "系统行为与74条启示录教训的持续对齐",
        "effort": "ongoing",
        "impact": "critical",
        "evidence": "gen_lessons.py + pulse_all lessons_validated",
        "lessons": ["all critical"],
    })
    
    # 排序
    for i, c in enumerate(candidates):
        c["rank"] = i + 1
    
    return candidates


def generate_report(bridge_assessment, organ_assessment, 
                     lesson_assessment, git_activity, state_trend, candidates):
    """生成人类可读报告"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Top 3 candidates
    top3 = candidates[:3]
    
    report = f"""
{'='*55}
  进化调度器 · 自主决策报告
  {now}
{'='*55}

【当前状态】
  器官: {organ_assessment.get('alive','?')}/{organ_assessment.get('total','?')} alive
  有数据的器官: {organ_assessment.get('organs_with_data','?')}/20
  空壳器官: {len(organ_assessment.get('empty_organs',[]))}
  桥薄弱: {len(bridge_assessment)}

【教训对齐】
  总教训: {lesson_assessment.get('total_lessons','?')}
  Critical: {lesson_assessment.get('critical_count','?')}条
  分类: {lesson_assessment.get('by_category',{})}

【进化速度】
  24h提交: {git_activity.get('total_24h',0)} | feat: {git_activity.get('feats',0)} | fix: {git_activity.get('fixes',0)}
  速率: {git_activity.get('evolution_rate','?')}

【链趋势】
  当前: {state_trend.get('current_chains','?')}链
  增长: {state_trend.get('chain_growth',0)}链 (历史{state_trend.get('cycles_recorded',0)}周期)

【推荐P0 TOP3】
"""
    for c in top3:
        report += f"""
  #{c['rank']} [{c['effort']}/{c['impact']}] {c['p0']}
     原因: {c['reason']}
     依据: {c['evidence']}
"""
    
    report += f"""
{'='*55}
  进化方向由系统自主评估决定。
  下个会话读取 next_p0_candidates.json 执行。
{'='*55}
"""
    return report


def save_candidates(candidates):
    """写入候选文件 (供下个会话读取)"""
    output = {
        "generated_at": datetime.now().isoformat(),
        "source": "进化调度器",
        "total_candidates": len(candidates),
        "candidates": candidates,
        "instructions": "读取此文件后,选rank=1执行,完成后重新运行调度器",
    }
    CANDIDATES_FILE.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    print(f"候选已写入 {CANDIDATES_FILE}")


if __name__ == "__main__":
    print("═══ 进化调度器 ═══")
    
    bridge_assessment = assess_bridges()
    organ_assessment = assess_organs()
    lesson_assessment = assess_lessons_alignment()
    git_activity = assess_git_activity()
    state_trend = assess_state_trend()
    
    candidates = generate_p0_candidates(
        bridge_assessment, organ_assessment,
        lesson_assessment, git_activity, state_trend
    )
    
    report = generate_report(
        bridge_assessment, organ_assessment,
        lesson_assessment, git_activity, state_trend, candidates
    )
    print(report)
    
    save_candidates(candidates)
    
    # 也写入自观报告格式
    report_path = CLUSTER / "进化调度报告.md"
    report_path.write_text(report, encoding='utf-8')
    print(f"报告已写入 {report_path}")
