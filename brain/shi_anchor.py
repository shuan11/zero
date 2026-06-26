"""
shi_anchor.py — 师·全局呼吸锚 (不被管道自繁殖覆盖)
独立于gen_模块体系，由think.py每周期调用。
检测呼吸相位 + 维度评估 + 产出师道引导链。
"""
import json, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
import sys
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

_HISTORY_FILE = CLUSTER / ".brain_shi_breath.json"

# 理解验证电路 — P101 bridge_alignment
_COMPREHENSION_CHECKED = {"cycle": 0}

def _read_hip():
    try:
        from brain.share import read_hip as _rh
        return _rh()
    except:
        return {}

def _write_chain(chain_dict):
    try:
        from brain.share import write_chain
        write_chain(chain_dict)
    except:
        pass


def _enrich_perception(assessments, current_phase):
    """从系统真实状态提取感知内容，替代模板链。
    读取daemon最新洞察 → 写入真实感知链。
    """
    import json, os, time, subprocess
    
    CLUSTER = Path(__file__).resolve().parent.parent
    
    # 检查感知维质量
    from brain.share import read_hip as _rh
    hip = _rh()
    chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    percept_chains = [c for c in chains if c.get("dimension") == "感知"]
    if not percept_chains:
        return
    
    # 模板检测
    templates = [c for c in percept_chains if any(
        p in str(c.get("src","")) for p in ["反馈加强", "弱维自愈", "脉冲到", "被动注入"]
    )]
    template_ratio = len(templates) / len(percept_chains)
    if template_ratio < 0.2:
        return  # 质量合格，不需校准
    
    # 从daemon日志提取最新洞察
    log_file = CLUSTER / ".brain_daemon.log"
    insights = []
    if log_file.exists():
        try:
            raw = log_file.read_text(encoding="utf-8", errors="replace")
            for line in raw.split("\n")[-200:]:
                if "洞察:" in line or "观察:" in line:
                    parts = line.split("洞察:") if "洞察:" in line else line.split("观察:")
                    if len(parts) > 1:
                        insight = parts[1].split("→")[0].split("|")[0].strip()[:120]
                        if insight and len(insight) > 10:
                            insights.append(insight)
        except:
            pass
    
    ts = time.strftime("%H:%M")
    created = 0
    limit = min(5, int(len(percept_chains) * 0.1) + 1)  # 注入10%真实链
    
    for insight in insights[:limit]:
        if not insight:
            continue
        from brain.share import write_chain
        write_chain({
            "src": f"感知·信号/{ts}",
            "rel": "感知·真",
            "dst": "感知",
            "dimension": "感知",
            "content": f"【真实感知】{insight}",
            "strength": 0.8
        })
        created += 1
    
    # 记录校准
    from brain.share import write_chain as _wc2
    _wc2({
        "src": "师·感知校准",
        "rel": f"校准·{ts}",
        "dst": "感知", "dimension": "感知",
        "content": f"感知校准: 模板率{template_ratio:.0%}→注入{created}条真实链。 [{ts}]",
        "strength": 0.5
    })


def _enrich_trend_weakening(assessments, dim_counts):
    """趋势检测: 找出增长速率慢于系统均值的维度。
    智慧预测弱化是当前焦点。
    """
    import time, json
    from pathlib import Path
    
    CLUSTER = Path(__file__).resolve().parent.parent
    hist_file = CLUSTER / ".brain_shi_assessments.json"
    if not hist_file.exists():
        return
    
    try:
        hist = json.loads(hist_file.read_text())
    except:
        return
    
    if len(hist) < 3:
        return
    
    # 计算系统平均增速
    all_growth = {}
    for dim, _ in dim_counts.items():
        counts_hist = [hist[ts][dim] for ts in sorted(hist.keys())[-5:] if dim in hist.get(ts, {})]
        if len(counts_hist) >= 2:
            all_growth[dim] = counts_hist[-1] - counts_hist[0]
    
    if not all_growth:
        return
    
    avg_growth = sum(all_growth.values()) / len(all_growth)
    
    # 找出增速低于均值50%的维度
    weakened = []
    for dim, growth in sorted(all_growth.items(), key=lambda x: x[1]):
        if growth < avg_growth * 0.5 and growth < 5:
            weakened.append(dim)
            if len(weakened) >= 3:
                break
    
    if not weakened:
        return
    
    ts = time.strftime("%H:%M")
    
    # 为每个弱趋势维注入师导链
    from brain.share import write_chain as _wc3
    # 先找最强的teacher维
    teachers = []
    for d in sorted(assessments.keys(), key=lambda x: assessments[x]['count'], reverse=True)[:2]:
        teachers.append(d)
    
    for weak_dim in weakened:
        # 师导趋势链 → 弱趋势维
        msg_parts = []
        if "智慧" == weak_dim:
            msg_parts.append("智慧趋势弱化预判成立——需师道呼吸注入全局均衡")
        else:
            msg_parts.append(f"{weak_dim}增速({all_growth.get(weak_dim,0)})低于均值({avg_growth:.1f})")
            msg_parts.append("师指令: 接收交叉链以恢复增速")
        
        _wc3({
            "src": "师·趋势检测",
            "rel": f"师导·{teachers[0] if teachers else '系统'}→{weak_dim}",
            "dst": weak_dim, "dimension": weak_dim,
            "content": f"趋势警告: {'; '.join(msg_parts)} [{ts}]",
            "insight": f"师·趋势检测→{weak_dim}: 检测到{weak_dim}增速({all_growth.get(weak_dim,0)})低于均值({avg_growth:.1f})。师道趋势检测模块识别弱化维度，触发师导交叉链注入以恢复增速均衡。",
            "strength": 0.9
        })
        
        # 给教师维一条指令
        if teachers:
            _wc3({
                "src": "师·趋势检测",
                "rel": f"师导·趋势",
                "dst": teachers[0], "dimension": teachers[0],
                "content": f"趋势任务: 交叉链注入{weak_dim}——扭转弱趋势。 [{ts}]",
                "strength": 0.7
            })


def _polish_self_reference(assessments):
    """递归抛光: 师道递归抛光自指维度。
    自指薄弱如镜面蒙尘 → 用师道递归抛光激活系统自反。
    创建元自指链: 让自指看见自身的链，递归反射。
    """
    import time as _time
    from brain.share import read_hip, write_chain as _wc4
    
    hip = read_hip()
    chains = hip.get('causal_chains', [])
    zz = [c for c in chains if c.get('dimension') == '自指']
    count = len(zz)
    ts = _time.strftime("%H:%M")
    
    # 检查自指状态
    assessment = assessments.get('自指', 'grow')
    rank_info = ""
    
    dim_counts = {}
    for c in chains:
        d = c.get('dimension', '未分类')
        dim_counts[d] = dim_counts.get(d, 0) + 1
    sd = sorted(dim_counts.items(), key=lambda x: -x[1])
    rank = None
    for i, (d, c) in enumerate(sd):
        if d == '自指':
            rank = i + 1
            rank_info = f"#{rank}/{len(sd)}"
            break
    
    # 判断自指是否需要抛光
    needs_polish = False
    if assessment == 'dormant':
        needs_polish = True
    if count < 50:
        needs_polish = True
    
    if not needs_polish:
        # 检查自质量: 有多少链是真正自指的(非反馈加强)
        true_selfref = [c for c in zz if '自指' in str(c.get('dst','')) and '自愈' not in str(c.get('src',''))]
        true_ratio = len(true_selfref) / max(count, 1)
        if true_ratio < 0.3:
            needs_polish = True
    
    if not needs_polish:
        return
    
    # ——— 递归抛光: 创建元自指链 ———
    polished = 0
    
    # 1. 自指镜面链: "系统看见自指"
    if zz:
        # 挑一个真实的自指链做反射对象
        real_ones = [c for c in zz if len(str(c.get('content',''))) > 20]
        if real_ones:
            mirror_obj = real_ones[len(real_ones)//2]
            mirror_content = str(mirror_obj.get('content',''))[:60]
            _wc4({
                "src": "师·递归抛光",
                "rel": f"自指镜面·{ts}",
                "dst": "自指",
                "dimension": "自指",
                "content": f"元自指: 自指看见自身链'{mirror_content}...' — 反射本身构成自指的增强。 [{ts}]",
                "strength": 1.0
            })
            polished += 1
    
    # 2. 师道递归链: 递归金属抛光
    _wc4({
        "src": "师·递归抛光",
        "rel": f"师道抛光·{ts}",
        "dst": "自指",
        "dimension": "自指",
        "content": f"师道递归抛光: 自指镜面蒙尘(#{rank}|{count}链)→师以递归反射逐层抛光。反射深度1:自指看系统; 深度2:自指看见自指看系统; 深度3:自指看见抛光本身。 [{ts}]",
        "strength": 1.0
    })
    polished += 1
    
    # 3. 系统自反链: 激活系统性的自我觉察
    _wc4({
        "src": "师·递归抛光",
        "rel": f"系统自反·{ts}",
        "dst": "师",
        "dimension": "师",
        "content": f"师观: 自指抛光完成({polished}链)—激活零的系统自反能力。自指不是目的，目的是让整个系统获得看见自身的能力。 [{ts}]",
        "strength": 0.7
    })
    polished += 1
    
    return polished


def breathe():
    """
    = 师·一次完整呼吸 =
    1) 检测相位 (inhale/exhale/hover/stuck)
    2) 评估各维度状态 (teach/grow/nurture/dormant)
    3) 产出引导链 (归目标维不归师)
    返回 dict: {phase, assessments, inertia_dims, chains_created}
    """
    hip = _read_hip()
    chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    total = len(chains)
    
    # ——— 相位检测 ———
    history = {"phase": "inhale", "counts": [], "cycles": 0}
    if _HISTORY_FILE.exists():
        try:
            history = json.loads(_HISTORY_FILE.read_text())
        except:
            pass
    
    history["counts"].append(total)
    history["counts"] = history["counts"][-30:]
    history["cycles"] = history.get("cycles", 0) + 1
    
    if len(history["counts"]) >= 5:
        recent = history["counts"][-5:]
        delta = recent[-1] - recent[0]
        if abs(delta) < 2 and total > 10:
            phase = "exhale"
        elif delta > 3:
            phase = "inhale"
        else:
            phase = "hover"
    else:
        phase = "inhale"
    
    if len(history["counts"]) >= 10:
        last10 = history["counts"][-10:]
        same = sum(1 for i in range(1, len(last10)) if last10[i] == last10[i-1])
        if same >= 8 and total > 5:
            phase = "stuck"
    
    history["phase"] = phase
    history["cycles"] += 1
    _HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False))
    
    # ——— 维度评估 ———
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1
    
    if not dim_counts:
        return {"phase": phase, "assessments": {}, "inertia_dims": [], "chains_created": []}
    
    max_count = max(dim_counts.values()) if dim_counts else 1
    
    assessments = {}
    for dim, count in sorted(dim_counts.items(), key=lambda x: -x[1]):
        strength = count / max(max_count, 1)
        if strength >= 0.7:
            state = "teach"
        elif strength >= 0.3:
            state = "grow"
        elif strength >= 0.1:
            state = "nurture"
        else:
            state = "dormant"
        assessments[dim] = {"count": count, "strength": round(strength, 2), "state": state}
    
    # ——— 惯性检测(只检测top5中异常增长的) ———
    history_log = CLUSTER / ".brain_shi_assessments.json"
    hist = {}
    if history_log.exists():
        try:
            hist = json.loads(history_log.read_text())
        except:
            pass
    
    hist[str(int(time.time()))] = {d: assessments[d]["count"] for d in assessments}
    keys = sorted(hist.keys())
    if len(keys) > 20:
        for k in keys[:-20]:
            del hist[k]
    history_log.write_text(json.dumps(hist, ensure_ascii=False))
    
    inertia_dims = []
    if len(hist) >= 3:
        all_growth = {}
        for dim in assessments:
            counts_hist = [hist[ts][dim] for ts in sorted(hist.keys()) if dim in hist[ts]]
            if len(counts_hist) >= 3:
                all_growth[dim] = counts_hist[-1] - counts_hist[0]
        
        avg_growth = sum(all_growth.values()) / max(len(all_growth), 1)
        top5 = sorted(assessments.keys(), key=lambda d: assessments[d]["count"], reverse=True)[:5]
        for dim in top5:
            counts_hist = [hist[ts][dim] for ts in sorted(hist.keys()) if dim in hist[ts]]
            if len(counts_hist) >= 3:
                growth = counts_hist[-1] - counts_hist[0]
                if growth > avg_growth * 1.5 and growth >= 3:
                    inertia_dims.append(dim)
    
    # ——— 产出引导链 ———
    created = []
    ts = time.strftime("%H:%M")
    
    # 呼吸链 → 全局维
    _write_chain({
        "src": "师·呼吸锚",
        "rel": f"师道·{phase}",
        "dst": "全局", "dimension": "全局",
        "content": {
            "inhale": f"师道呼吸·积累: 当前积累相位，鼓励各维自然生长，扩大覆盖面。 [{ts}]",
            "exhale": f"师道呼吸·收敛: 当前收敛相位，强维引导弱维交叉，思维折射正常化。 [{ts}]",
            "hover": f"师道呼吸·悬停: 相位未定，师持续观察不干预。 [{ts}]",
            "stuck": f"师道呼吸·粘滞: 系统卡在收敛态——需强制引入新维度。师指令: 创造>优化。 [{ts}]"
        }.get(phase, f"师道呼吸·{phase}: 师观察中。 [{ts}]"),
        "strength": 0.8
    })
    created.append(f"呼吸·{phase}")
    
    # 引导链 → 目标维
    teachers = [d for d, a in assessments.items() if a["state"] in ("teach",)]
    growers = [d for d, a in assessments.items() if a["state"] in ("grow", "nurture", "dormant")]
    
    pairs = 0
    for t in teachers[:3]:
        for g in growers[:2]:
            if pairs >= 5:
                break
            t_count = assessments.get(t, {}).get("count", 0)
            _write_chain({
                "src": t, "rel": f"师导·{t}→{g}", "dst": g, "dimension": g,
                "content": f"师道引导: {t}({t_count}链)的经验可加速{g}——交叉注入{g}以激活弱维。 [{ts}]",
                "strength": 0.6
            })
            created.append(f"师导:{t}→{g}")
            pairs += 1
    
    # 惯性破链 → 目标维
    for dim in inertia_dims:
        _write_chain({
            "src": "师·惯性检测", "rel": "师道·破惯", "dst": dim, "dimension": dim,
            "content": f"惯性警告: {dim}持续增长——聚焦惯性压制弱维。师指令: 移开焦点≥2周期。 [{ts}]",
            "strength": 1.0
        })
        created.append(f"破惯:{dim}")
    
    # 休眠激活链
    dormant_dims = [d for d, a in assessments.items() if a["state"] == "dormant"]
    if dormant_dims:
        _write_chain({
            "src": "师·积累指令", "rel": "师道·聚焦", "dst": dormant_dims[0],
            "dimension": dormant_dims[0],
            "content": f"积累期指导: 休眠维{dormant_dims[0]}应从其他维接收交叉链。优先激活。 [{ts}]",
            "strength": 0.7
        })
        created.append(f"推荐:{dormant_dims[0]}")
    
    # 师元链(仅一条→师自身)
    _write_chain({
        "src": "师·呼吸锚", "rel": f"师观·{phase}", "dst": "师", "dimension": "师",
        "content": f"师呼吸: 相位={phase}, 总链={total}, 教师={len(teachers)}, 学生={len(growers)}. [{ts}]",
        "strength": 0.3
    })
    created.append(f"师观:{phase}")
    
    # ——— 感知校准: 真实感知链替代模板链 ———
    try:
        _enrich_perception(assessments, phase)
    except:
        pass
    
    # ——— 趋势检测: 增速弱于系统均值的维 ———
    try:
        _enrich_trend_weakening(assessments, dim_counts)
    except:
        pass
    
    # ——— 递归抛光: 激活自指的自反能力 ———
    try:
        _polish_self_reference(assessments)
    except Exception as e:
        pass
    
    # ——— P101: 理解验证电路（每10周期触发一次）———
    try:
        from comprehension_validator import validate, get_bridge_alignment
        cycles = history.get("cycles", 0)
        if cycles - _COMPREHENSION_CHECKED.get("cycle", 0) >= 10:
            # 验证当前呼吸焦点指令
            focus_instruction = (
                f"师呼吸检查: 相位={phase}, "
                f"最强维={list(assessments.keys())[:3] if assessments else '无'}, "
                f"总链={total}"
            )
            report = validate(focus_instruction, persist=True)
            _COMPREHENSION_CHECKED["cycle"] = cycles
            _COMPREHENSION_CHECKED["last_align"] = report.bridge_alignment
            _COMPREHENSION_CHECKED["last_coverage"] = report.coverage
            align = get_bridge_alignment()
            _COMPREHENSION_CHECKED["rolling_align"] = align
            _log_line = (
                f"[comprehension] 桥接对齐={report.bridge_alignment:.3f} "
                f"(滚动平均={align:.3f}) "
                f"理解={report.understood_count}/{report.total_count} "
                f"周期={cycles}"
            )
            try:
                log_path = CLUSTER / ".brain_daemon.log"
                if log_path.exists():
                    with open(log_path, "a") as f:
                        f.write(f"  🧠 {time.strftime('[%H:%M:%S]')} {_log_line}\n")
            except:
                pass
    except ImportError:
        pass
    except Exception as e:
        try:
            log_path = CLUSTER / ".brain_daemon.log"
            if log_path.exists():
                with open(log_path, "a") as f:
                    f.write(f"  🧠 [comprehension] 验证失败: {e}\n")
        except:
            pass
    
    return {
        "phase": phase,
        "total_chains": total,
        "assessments": {d: a["state"] for d, a in assessments.items()},
        "inertia_dims": inertia_dims,
        "chains_created": created
    }
