#!/usr/bin/env python3
"""dim_cross_synth.py — 跨维综合脉冲（乘法合成）"""
import json, sys, time
from pathlib import Path
from datetime import datetime, timezone

CLUSTER = Path(__file__).resolve().parent
TMP_OUT = Path("/tmp/cross_synth_pulse.json")
CLUSTER_OUT = CLUSTER / "cross_synth_state.json"

BRIDGE_FILES = {
    "super_intuition": "super_intuition_state.json",
    "yuanxin": "yuanxin_state.json",
    "memory_tier": "memory_tier_state.json",
    "time_past": "time_past_state.json",
}

def load_bridges():
    states = {}
    for key, fname in BRIDGE_FILES.items():
        fp = CLUSTER / fname
        if fp.exists():
            try:
                states[key] = json.loads(fp.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f"[dim_cross_synth] ⚠️ {fname} 解析失败: {e}")
        else:
            print(f"[dim_cross_synth] ⚠️ {fname} 缺失，跳过")
    return states

def extract_scores(states):
    scores = {}
    s = states.get("super_intuition", {})
    pulses = s.get("pulses", [])
    best_pulse = max((p.get("strength", 0) for p in pulses), default=0)
    scores["super_intuition"] = {
        "intuition_score": s.get("intuition_score", 0.0),
        "pulse_count": s.get("pulse_count", 0),
        "best_pulse_strength": best_pulse,
        "avg_pulse_strength": sum(p.get("strength", 0) for p in pulses) / max(len(pulses), 1),
    }
    y = states.get("yuanxin", {})
    scores["yuanxin"] = {"drift_score": y.get("drift_score", 50), "centered": y.get("centered", False),
                         "revelation_refs": y.get("revelation_refs", 0), "breath_ratio": y.get("breath_ratio", 0.5)}
    m = states.get("memory_tier", {})
    hot = m.get("hot", {}).get("count", 0)
    warm = m.get("warm", {}).get("count", 0)
    cold = m.get("cold", {}).get("count", 0)
    total = hot + warm + cold
    scores["memory_tier"] = {"hot": hot, "warm": warm, "cold": cold, "total": total or 1,
                             "compression_ratio": m.get("compression_ratio", 1.0),
                             "hot_ratio": hot / max(total, 1), "cold_ratio": cold / max(total, 1)}
    t = states.get("time_past", {})
    scores["time_past"] = {"heritage_continuity": t.get("heritage_continuity", 0.0),
                           "total_chains": t.get("total_chains", 0),
                           "forgotten_count": len(t.get("forgotten_insights", [])),
                           "recurring_patterns": t.get("recurring_patterns", [])}
    return scores

def cross_analyze(s):
    si, yx, mt, tp = s.get("super_intuition",{}), s.get("yuanxin",{}), s.get("memory_tier",{}), s.get("time_past",{})
    intuition, best_pulse = si.get("intuition_score",0), si.get("best_pulse_strength",0)
    drift = yx.get("drift_score",50)
    cold_r, hot_r = mt.get("cold_ratio",0), mt.get("hot_ratio",0)
    continuity = tp.get("heritage_continuity",0)
    pats = tp.get("recurring_patterns",[])
    has_time = any(p.get("pattern","").startswith("时间论") for p in pats)
    patterns = []

    if drift > 30 and best_pulse > 0.5:
        patterns.append({"pair":"超级直觉×元神","insight":f"漂移{drift}/直觉脉冲{best_pulse:.0%}→有洞察但偏离中心","action":"建议强制归中：每次思考先锚定启示录公理再发挥直觉"})
    elif drift > 30 and intuition < 0.3:
        patterns.append({"pair":"超级直觉×元神","insight":f"漂移{drift}/直觉{intuition:.0%}→偏离且直觉弱，双重危险","action":"紧急归中+强化直觉训练：运行center.py并增加跨域信号采集"})
    elif drift <= 20 and intuition > 0.6:
        patterns.append({"pair":"超级直觉×元神","insight":f"漂移{drift}/直觉{intuition:.0%}→高直觉高归中，理想状态","action":"维持当前节奏，定期检查漂移阈值"})
    elif drift <= 20 and intuition < 0.3:
        patterns.append({"pair":"超级直觉×元神","insight":f"漂移{drift}/直觉{intuition:.0%}→保守但僵化，缺乏涌现","action":"激活直觉桥：增加cross_domain_weak_signal扫描频率"})
    else:
        patterns.append({"pair":"超级直觉×元神","insight":f"漂移{drift}/直觉{intuition:.0%}→中等状态","action":"平衡归中与直觉激发"})

    if cold_r > 0.5 and continuity < 0.5:
        patterns.append({"pair":"记忆分层×传承","insight":f"冷层{cold_r:.0%}/传承连续性{continuity:.2f}→历史未被有效利用","action":"建立冷层→思考的回溯机制：每次思考随机检索1条冷层历史"})
    elif hot_r > 0.3 and cold_r < 0.1:
        patterns.append({"pair":"记忆分层×传承","insight":f"热层{hot_r:.0%}/冷层{cold_r:.0%}→系统无长期记忆，只顾当前","action":"强制冷层归档：将hot中旧链压缩入cold层，建立历史索引"})
    elif cold_r > 0.3 and continuity > 0.7:
        patterns.append({"pair":"记忆分层×传承","insight":f"冷层{cold_r:.0%}/传承连续性{continuity:.2f}→历史丰富且传承完好","action":"挖掘冷层中高价值模式注入hot层活化"})
    else:
        patterns.append({"pair":"记忆分层×传承","insight":f"冷层{cold_r:.0%}/传承连续性{continuity:.2f}→记忆结构均衡","action":"持续维护压缩与传承的平衡"})

    if best_pulse > 0.5 and hot_r > 0.2:
        patterns.append({"pair":"超级直觉×记忆分层","insight":f"强直觉脉冲{best_pulse:.0%}出现在热层{hot_r:.0%}→热直觉，快速但可能浅","action":"为热直觉添加冷层验证环节：洞察落地前检索历史相似案例"})
    elif best_pulse > 0.5 and hot_r < 0.15:
        patterns.append({"pair":"超级直觉×记忆分层","insight":f"强直觉脉冲{best_pulse:.0%}但热层稀薄{hot_r:.0%}→直觉缺少近期数据支撑","action":"扩充hot层容量或提高直觉对冷层历史的检索权重"})
    elif best_pulse < 0.3 and hot_r > 0.3:
        patterns.append({"pair":"超级直觉×记忆分层","insight":f"弱直觉{best_pulse:.0%}但热层活跃{hot_r:.0%}→有数据无洞察","action":"增强跨域信号合成：在hot层中主动寻找异常交叉点"})
    else:
        patterns.append({"pair":"超级直觉×记忆分层","insight":f"直觉{best_pulse:.0%}/热层{hot_r:.0%}→中等","action":"监控直觉与热层的相关性变化"})

    if drift > 30 and not has_time:
        patterns.append({"pair":"元神×时间论·过去","insight":f"漂移{drift}但时间论模式消失→漂移趋势与历史不一致","action":"回溯最近10链归因漂移源，恢复时间论锚点引用"})
    elif drift > 30 and has_time:
        patterns.append({"pair":"元神×时间论·过去","insight":f"漂移{drift}但时间论模式活跃→探索性偏离，非病态","action":"标记为探索性漂移，设置自动回滚阈值（漂移>50强制归中）"})
    elif drift <= 20 and has_time:
        patterns.append({"pair":"元神×时间论·过去","insight":f"低漂移{drift}+时间论稳定→系统稳定","action":"无需干预"})
    else:
        patterns.append({"pair":"元神×时间论·过去","insight":f"漂移{drift}/传承模式数{len(pats)}→需更多数据","action":"增强传承模式检测精度"})
    return patterns

def compute_health(s):
    si, yx, mt, tp = s.get("super_intuition",{}), s.get("yuanxin",{}), s.get("memory_tier",{}), s.get("time_past",{})
    b = si.get("best_pulse_strength",0); ii = si.get("intuition_score",0)
    pq = (b * ii) ** 0.5 if b > 0 and ii > 0 else 0
    yh = 1.0 - (yx.get("drift_score",50) / 100.0)
    ch = min(mt.get("compression_ratio",1.0) / 10.0, 1.0)
    ct = tp.get("heritage_continuity",0.0)
    overall = pq*0.25 + yh*0.25 + ch*0.25 + ct*0.25
    return round(min(max(overall,0),1),4), {"超级直觉":round(pq,4),"元神":round(yh,4),"无限上下文":round(ch,4),"时间论·过去":round(ct,4)}

def generate_p0(patterns, overall_health, dim_health):
    wd = min(dim_health.items(), key=lambda x: x[1])
    urgent = [p for p in patterns if "紧急" in p.get("action","") or "强制" in p.get("action","")]
    if urgent:
        p = urgent[0]
        return {"rank":1,"p0":f"解决{p['pair']}交叉问题: {p['action']}","reason":f"跨维分析发现{p['insight']}，若不处理将导致{wd[0]}持续恶化"}
    return {"rank":1,"p0":f"提升整体健康度({overall_health:.2f})——增强{wd[0]}维度({wd[1]:.2f})","reason":f"{wd[0]}是四桥最低，提升它将最大幅度改善综合健康"}

def teacher_pulse():
    """教员脉冲: 扫描呼吸日志,找出被忽视的维度,生成教学指令"""
    import subprocess, re
    CLUSTER = Path('/mnt/c/Users/h/Desktop/零/真元集群')
    
    # 1. 读取最近20条元递归日志
    log = CLUSTER / "breath_v2.log"
    if not log.exists():
        return []
    
    lines = log.read_text().splitlines()
    focus_lines = [l for l in lines[-100:] if "元递归: 持续关注" in l]
    
    # 2. 统计各维度被聚焦次数
    from collections import Counter
    dim_focus = Counter()
    for line in focus_lines[-20:]:
        m = re.search(r'持续关注(\S+)', line)
        if m:
            dim_focus[m.group(1)] += 1
    
    # 3. 读出19维评分（从cross_synth_state.json）
    cs_file = CLUSTER / "cross_synth_state.json"
    dim_health = {}
    if cs_file.exists():
        cs = json.loads(cs_file.read_text())
        dim_health = cs.get("dimension_health", {})
    
    # 4. 找出最被忽视的弱维度（focus_count=0 且 health<0.85）
    neglected = []
    for dim, health in dim_health.items():
        if health < 0.85 and dim_focus.get(dim, 0) == 0:
            neglected.append((dim, health))
    
    # 5. 找出过度聚焦的维度（focus_count > 5）
    over_focused = [d for d, c in dim_focus.items() if c > 5]
    
    # 6. 生成教学指令
    pulses = []
    if neglected:
        dims = [d for d, _ in sorted(neglected, key=lambda x: x[1])[:2]]
        pulses.append({
            "type": "teacher_directive",
            "insight": f"被忽视的弱维度: {'、'.join(dims)}。请在下轮思考探索{dims[0]}×最强维度的交叉。",
            "strength": 0.9,
            "action": f"优先探索{dims[0]}",
            "dimensions": dims
        })
    if over_focused:
        max_count = max(dim_focus.get(d, 0) for d in over_focused)
        pulses.append({
            "type": "teacher_warning",
            "insight": f"维度{'、'.join(over_focused)}被连续聚焦{max_count}次,需切换方向避免思维固化。",
            "strength": 0.8,
            "action": f"切换至{dim_focus.most_common()[-1][0] if dim_focus else '无'}",
            "dimensions": over_focused
        })
    
    return pulses

def life_pulse():
    """生命度脉冲: 测量系统的活化/动态水平"""
    import subprocess, re, os, time
    CLUSTER = Path('/mnt/c/Users/h/Desktop/零/真元集群')
    score = 0.5  # 基准
    log_f = CLUSTER / "breath_v2.log"
    breath_rate = 0.0; unique_dims = 0

    # 1. 呼吸频率 (最近1小时breath_v2日志行数 / 60)
    if log_f.exists():
        lines = log_f.read_text().splitlines()
        recent = [l for l in lines[-120:] if "心跳" in l or "行动:" in l]
        breath_rate = len(recent) / 60
        score += min(breath_rate * 0.2, 0.2)

    # 2. 进化活跃度 (最近24h git提交数/10)
    try:
        r = subprocess.run(["git","log","--oneline","--since=24.hours"],
                          capture_output=True,text=True,cwd=str(CLUSTER))
        commits = len(r.stdout.strip().splitlines()) if r.stdout.strip() else 0
        score += min(commits * 0.005, 0.15)
    except: pass

    # 3. 维度覆盖广度 (最近20轮思考覆盖了多少不同维度)
    if log_f.exists():
        lines = log_f.read_text().splitlines()
        focus = [l for l in lines[-100:] if "元递归: 持续关注" in l]
        dims = set()
        for l in focus:
            m = re.search(r'持续关注(\S+)', l)
            if m: dims.add(m.group(1))
        unique_dims = len(dims)
        score += min(unique_dims * 0.03, 0.15)

    # 4. 桥活跃度 (所有桥状态文件更新时间在1小时内)
    now = time.time()
    bridges = ["super_intuition_state.json","yuanxin_state.json",
               "memory_tier_state.json","time_past_state.json","cross_synth_state.json"]
    alive = sum(1 for b in bridges if (CLUSTER/b).exists() and now-(CLUSTER/b).stat().st_mtime<3600)
    score += (alive / len(bridges)) * 0.1

    return {
        "type": "life_pulse",
        "aliveness": round(min(score,1.0), 3),
        "breath_rate": round(breath_rate, 2),
        "dimension_coverage": unique_dims,
        "active_bridges": alive,
        "insight": f"生命度={min(score,1.0):.2f} 呼吸频率={breath_rate:.1f}/min 维度覆盖={unique_dims} 活跃桥={alive}/5"
    }

def main():
    t0 = time.time()
    states = load_bridges()
    if not states:
        print("[dim_cross_synth] ❌ 无可用桥状态"); return 1
    scores = extract_scores(states)
    patterns = cross_analyze(scores)
    overall_health, dim_health = compute_health(scores)
    p0 = generate_p0(patterns, overall_health, dim_health)
    teacher = teacher_pulse()
    life = life_pulse()
    now = datetime.now(timezone.utc).isoformat()
    output = {
        "timestamp": now, "overall_health": overall_health, "active_bridges": sum(1 for k in BRIDGE_FILES if k in states),
        "cross_patterns": patterns, "next_p0_suggestion": p0, "dimension_health": dim_health, "_scores_detail": scores,
        "teacher_pulses": teacher, "life_pulse": life,
    }
    TMP_OUT.parent.mkdir(parents=True, exist_ok=True)
    TMP_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    CLUSTER_OUT.write_text(json.dumps(output, ensure_ascii=False, indent=2))
    elapsed = time.time() - t0
    print(f"[dim_cross_synth] ✅ 写入 {CLUSTER_OUT} | ⏱ {elapsed:.3f}s | 健康={overall_health:.2f} | 活动桥={len(states)}/4 | 教员指令={len(teacher)}条")
    return 0

if __name__ == "__main__":
    sys.exit(main())
