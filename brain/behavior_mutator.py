"""brain/behavior_mutator.py — 行为变异+自然选择引擎 v3
P112+: 像碳基生物一样进化——随机变异×自然选择×遗传。
v3: 新增适应度函数、随机变异算子、选择压力(回滚劣质变异)、世代追踪。

核心进化回路（每代10周期）:
  1. 代初: 随机选取一个基因组参数 → 保存原值 → 随机变异(±10-50%)
  2. 代中: 系统自然运行(不干预)
  3. 代末: 测量适应度 → 对比代初基线 → 适应度提高则保留, 否则回滚
  4. 遗传: 保留的优质变异成为新常态, 下一代表在此基础继续变异

碳基生物学对应:
  - 基因型(Genotype) = .brain_genome.json 中的参数
  - 表型(Phenotype) = daemon实际行为(周期/频率/阈值)
  - 变异(Mutation) = 随机参数微调
  - 适应度(Fitness) = 链生长率×新颖性×维度均衡
  - 自然选择(Selection) = 适应度下降则回滚
"""

import json, time, random, math
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent

# 全稳阈值（维数≥此值且链数≥此值进入变异期）
MIN_DIM_STABLE = 25
MIN_CHAIN_STABLE = 200

# 进化参数
GENERATION_LENGTH = 10          # 每代周期数
MUTATION_RATE = 0.7             # 每代发生变异的概率
MUTATION_MAGNITUDE = (0.15, 0.5)  # 变异幅度范围(±15%-50%)
FITNESS_WINDOW = 200            # 适应度计算使用的近N条链

# 变异记录文件
MUTATION_LOG = CLUSTER / ".brain_mutations.json"
FITNESS_LOG = CLUSTER / ".brain_fitness.json"
EVOLUTION_LINEAGE = CLUSTER / ".brain_evolution.json"

def _load_hip():
    """读取海马体"""
    try:
        from brain.share import read_hip
        return read_hip()
    except:
        try:
            hip_file = CLUSTER / "hippocampus_memory.json"
            return json.loads(hip_file.read_text())
        except:
            return {"causal_chains": []}

def _dim_counts():
    """获取各维度链数"""
    data = _load_hip()
    chains = data.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return dims

def check_all_stable():
    """检查是否所有维度已稳定（进入变异期的条件）"""
    dims = _dim_counts()
    stable_dims = {d: v for d, v in dims.items() if v >= MIN_CHAIN_STABLE}
    is_stable = len(stable_dims) >= MIN_DIM_STABLE
    return is_stable, len(stable_dims), len(dims)

def _load_mutation_log():
    """读取变异历史"""
    try:
        return json.loads(MUTATION_LOG.read_text())
    except:
        return {"mutations": [], "phase": "accumulation"}

def _save_mutation_log(log):
    MUTATION_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))

def _detect_cycle(mutations, max_history=16):
    """检测变异中的循环模式 — 如果周期≤4且重复≥3次，判定为循环"""
    if len(mutations) < 8:
        return False
    types = [m.get("type", "") for m in mutations[-max_history:]]
    # 检查是否存在≤4的周期
    for period in [2, 3, 4]:
        if len(types) >= period * 3:
            # 检查最后 period*3 个类型是否以 period 为周期重复
            pattern = types[-period:]
            is_cycle = True
            for i in range(period * 2):
                if types[-(period*3) + i] != types[-(period*3) + i + period]:
                    is_cycle = False
                    break
            if is_cycle:
                return True, pattern, period
    return False, [], 0

def suggest_mutation():
    """基于维度状态建议行为变异（v2: 防周期循环）"""
    is_stable, n_stable, n_total = check_all_stable()
    log_data = _load_mutation_log()
    mutations = log_data.get("mutations", [])

    # 判断当前相位
    if is_stable and n_stable >= n_total * 0.9:
        new_phase = "mutation"
    else:
        new_phase = "accumulation"

    old_phase = log_data.get("phase", "accumulation")
    phase_changed = (old_phase != new_phase)

    # 生成变异建议
    suggestions = []

    if new_phase == "mutation":
        dims = _dim_counts()
        sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
        top3 = [d for d, v in sorted_dims[:5] if v >= MIN_CHAIN_STABLE][:3]
        weak_dims = [d for d, v in sorted_dims if d not in ("系统", "未分类") and v == sorted_dims[-1][1]][:3]
        weak_dim_name = weak_dims[0] if weak_dims else "未知"

        # ===== v2: 扩展8型变异池 =====
        mutation_types = [
            {
                "type": "reduce_gen_frequency",
                "desc": "全稳状态 → 降低gen文件生成频率，节约API燃料",
                "genome_change": {"gen.max_per_cycle": 1}
            },
            {
                "type": "cross_synthesis",
                "desc": f"跨维合成: {', '.join(top3[:3])} → 生成合成洞察链",
                "genome_change": {"focus.always_api": False}
            },
            {
                "type": "dynamic_interval",
                "desc": "动态延长时间间隔: 从20s→60s, 进入节能模式",
                "genome_change": {"cycle.dynamic_interval": 60}
            },
            {
                "type": "deep_audit",
                "desc": "深度审计模式: 检查链质量而非数量",
                "genome_change": {"audit.memory_gc_threshold": 0.5}
            },
            # === v2新增: 4型打破循环 ===
            {
                "type": "force_weak_dim_focus",
                "desc": f"强制聚焦弱维: {weak_dim_name} → 定向注入链",
                "genome_change": {"focus.force_weak": True, "focus.weak_dim": weak_dim_name}
            },
            {
                "type": "chain_quality_enforce",
                "desc": "链质量强化模式: 注入长内容链(>120字符)",
                "genome_change": {"quality.min_content_len": 80, "quality.enforce": True}
            },
            {
                "type": "gen_mutation_speed",
                "desc": "加速gen文件变异: 每周期生成+1文件",
                "genome_change": {"gen.max_per_cycle": 3}
            },
            {
                "type": "synthesis_burst",
                "desc": "合成爆发模式: 每周期强制合成+1次",
                "genome_change": {"synthesis_interval": 2}
            },
        ]

        # 周期检测 — 如果检测到循环，引入随机破坏
        is_cycle, pattern, period = _detect_cycle(mutations)
        if is_cycle:
            # 打破循环: 从循环模式外的类型中选一个（优先选v2新增的）
            pattern_set = set(pattern)
            non_cycle_types = [m for m in mutation_types if m["type"] not in pattern_set]
            if non_cycle_types:
                suggestion = random.choice(non_cycle_types)
                suggestion["_cycle_broken"] = True
            else:
                suggestion = random.choice(mutation_types)
        else:
            # 无循环: 多样性加权选择
            recent_types = [m.get("type") for m in mutations[-4:]]
            # 加权: 距上次使用越远权重越高
            weights = []
            for mt in mutation_types:
                t = mt["type"]
                if t not in recent_types:
                    weights.append(2.0)  # 近期未用，高权重
                else:
                    # 越久远权重越高
                    last_pos = len(recent_types) - 1 - recent_types[::-1].index(t)
                    recency_weight = 0.3 + 0.3 * (last_pos / max(len(recent_types) - 1, 1))
                    weights.append(recency_weight)

            total_w = sum(weights)
            if total_w > 0:
                norm_weights = [w / total_w for w in weights]
                idx = random.choices(range(len(mutation_types)), weights=norm_weights, k=1)[0]
                suggestion = mutation_types[idx]
            else:
                suggestion = random.choice(mutation_types)

        suggestion["phase"] = "mutation"
        suggestion["n_stable"] = n_stable
        suggestion["n_total"] = n_total
        suggestion["timestamp"] = time.time()
        suggestions.append(suggestion)

    return suggestions, new_phase, phase_changed

def apply_mutation(suggestion):
    """应用变异到基因组"""
    genome_change = suggestion.get("genome_change", {})
    if not genome_change:
        return False

    try:
        from brain.genome import update_genome
        update_genome(genome_change)

        # 记录变异
        log_data = _load_mutation_log()
        log_data["phase"] = suggestion.get("phase", "mutation")
        entry = {
            "type": suggestion["type"],
            "desc": suggestion["desc"],
            "genome_change": genome_change,
            "timestamp": suggestion.get("timestamp", time.time()),
            "n_stable": suggestion.get("n_stable", 0)
        }
        if suggestion.get("_cycle_broken"):
            entry["cycle_broken"] = True
        log_data["mutations"].append(entry)
        # 保留最近30条
        if len(log_data["mutations"]) > 30:
            log_data["mutations"] = log_data["mutations"][-30:]
        _save_mutation_log(log_data)

        # 写因果链
        try:
            from brain.share import write_chain
            write_chain({
                "src": "行为变异引擎",
                "rel": f"变异#{len(log_data['mutations'])}",
                "dst": suggestion["type"],
                "dimension": "系统",
                "content": suggestion["desc"][:80],
                "strength": 0.85
            })
        except:
            pass

        return True
    except Exception as e:
        return False

# ═══════════════════════════════════════════════════
# v3: 碳基进化系统 — 适应度×随机变异×自然选择
# ═══════════════════════════════════════════════════

def measure_fitness() -> float:
    """测量系统适应度 — 越高代表越健康/进化越好
    
    四维度加权:
      - 链多样性(0.35): 近N条链内容独特率
      - 维度均衡(0.25): 链在各维度的分布均匀度
      - 维覆盖数(0.20): 活跃维度总数(越多越好)
      - 链增长率(0.20): 链数增长速度
    """
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    if not chains:
        return 0.5  # 默认居中
    
    recent = chains[-FITNESS_WINDOW:]
    
    # 1. 链多样性 (0-0.35)
    contents = [c.get("content", "")[:60] for c in recent]
    unique = len(set(contents))
    diversity = (unique / max(len(contents), 1)) if contents else 0
    
    # 2. 维度均衡 (0-0.25) — 使用基尼系数逆值
    dims = {}
    for c in recent:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    if dims:
        vals = sorted(dims.values())
        n = len(vals)
        # 简化的均衡度: 最小维链数 / 最大维链数
        max_v = max(vals)
        min_v = min(vals)
        balance = min_v / max(max_v, 1) if max_v > 0 else 1.0
    else:
        balance = 1.0
    
    # 3. 维覆盖数 (0-0.20)
    total_dims = len(dims)
    dim_coverage = min(total_dims / 37.0, 1.0)  # 37是总维度数
    
    # 4. 链增长率 (0-0.20) — 比较最近100条的增长速度
    older = chains[-FITNESS_WINDOW*2:-FITNESS_WINDOW] if len(chains) > FITNESS_WINDOW*2 else chains[:len(recent)]
    growth_rate = len(recent) / max(len(older), 1)
    if growth_rate > 2.0:
        growth_rate = 2.0  # 增速上限
    
    # 综合打分
    score = (
        diversity * 0.35 +
        balance * 0.25 +
        dim_coverage * 0.20 +
        (growth_rate / 2.0) * 0.20  # 归一化到0-1
    )
    
    return round(min(max(score, 0.0), 1.0), 4)


def _get_mutable_genes() -> list:
    """获取可变异基因组参数列表(数值型+允许范围)"""
    from brain.genome import load_genome
    genome = load_genome()
    
    # 定义可变异基因及其范围约束
    # (参数名, 最小值, 最大值, 是否整数)
    gene_defs = [
        ("cycle.proposal_interval", 1, 20, True),
        ("cycle.parallel_think_interval", 1, 20, True),
        ("cycle.hippocampus_validate", 3, 30, True),
        ("cycle.self_evolve_interval", 3, 30, True),
        ("cycle.desktop_summary_interval", 1, 20, True),
        ("focus.max_repeat", 1, 8, True),
        ("heal.persist_cross_chain", 1, 10, True),
        ("heal.persist_behavioral", 1, 10, True),
        ("heal.weak_threshold_chain", 50, 500, True),
        ("io.timeout", 1, 30, True),
        ("gen.max_per_cycle", 1, 8, True),
        ("engine.max_files", 5, 50, True),
        ("audit.cross_dim_frequency", 1, 20, True),
        ("audit.memory_gc_threshold", 0.1, 0.95, False),
        ("quality.min_content_len", 20, 200, True),
        ("quality.enforce_strength", 0.3, 1.0, False),
        ("quality.ratio_target", 0.05, 0.5, False),
    ]
    
    # 过滤: 只在基因组中存在的参数
    available = []
    for name, min_v, max_v, is_int in gene_defs:
        if name in genome:
            available.append((name, genome[name], min_v, max_v, is_int))
    
    return available


def _mutate_value(current, min_v, max_v, is_int):
    """对基因值施加随机变异(±15-50%)，受边界约束"""
    magnitude = random.uniform(*MUTATION_MAGNITUDE)
    direction = 1 if random.random() > 0.5 else -1
    
    if is_int:
        # 整数基因: 至少变化1，最多变化若干
        delta = max(1, int(current * magnitude))
        new_val = current + direction * delta
    else:
        # 浮点基因: 百分比变化
        delta = current * magnitude * direction
        new_val = current + delta
    
    # 边界裁剪
    new_val = max(min_v, min(new_val, max_v))
    if is_int:
        new_val = int(round(new_val))
    else:
        new_val = round(new_val, 4)
    
    return new_val


def random_mutation_operator():
    """随机变异算子：随机选一个基因，施加随机变异
    
    返回:
        (gene_name, old_value, new_value, description) 或 None(无变异)
    """
    if random.random() > MUTATION_RATE:
        return None
    
    genes = _get_mutable_genes()
    if not genes:
        return None
    
    name, current, min_v, max_v, is_int = random.choice(genes)
    new_val = _mutate_value(current, min_v, max_v, is_int)
    
    if new_val == current:
        return None
    
    desc = f"基因:{name} {current}→{new_val} ({'+' if new_val > current else ''}{'%d' % ((new_val-current)/max(current,0.001)*100)}%)"
    return (name, current, new_val, desc)


def _load_evolution_lineage():
    """读取进化世系"""
    try:
        return json.loads(EVOLUTION_LINEAGE.read_text())
    except:
        return {"generations": [], "current_gen": 0, "fitness_baseline": None, "pending_mutation": None}


def _save_evolution_lineage(lineage):
    EVOLUTION_LINEAGE.write_text(json.dumps(lineage, ensure_ascii=False, indent=2))


def _evolution_pulse(cycle_num):
    """碳基进化主脉冲：管理世代周期、变异、选择、回滚
    
    被pulse()调用，返回状态消息列表。
    """
    from brain.genome import update_genome, load_genome
    results = []
    lineage = _load_evolution_lineage()
    
    gen = cycle_num // GENERATION_LENGTH
    phase = cycle_num % GENERATION_LENGTH
    
    lineage["current_gen"] = gen
    
    # 代初(phase==0): 保存适应度基线 + 施加变异(含杂交)
    if phase == 0 and cycle_num > 0:
        fitness = measure_fitness()
        lineage["fitness_baseline"] = fitness
        
        # 杂交或随机变异(30%概率杂交, 70%概率随机)
        if random.random() < 0.3:
            _mutation = crossover_operator()
            if _mutation:
                gene, changes, desc = _mutation
                genome = load_genome()
                old_val = genome.get(gene, "?")
                new_val = changes.get(gene, old_val)
                
                for g_name, g_val in changes.items():
                    update_genome({g_name: g_val})
                
                lineage["pending_mutation"] = {
                    "gene": gene,
                    "old_value": old_val,
                    "new_value": new_val,
                    "generation": gen,
                    "crossover": True,
                    "all_changes": changes,
                    "timestamp": time.time()
                }
                results.append(f"🧬 代{gen} 杂交:{desc}")
            else:
                _mutation = random_mutation_operator()
                if _mutation:
                    gene, old_val, new_val, desc = _mutation
                    if gene in genome:
                        update_genome({gene: new_val})
                        lineage["pending_mutation"] = {
                            "gene": gene,
                            "old_value": old_val,
                            "new_value": new_val,
                            "generation": gen,
                            "timestamp": time.time()
                        }
                        results.append(f"🧬 代{gen} 变异:{desc}")
                else:
                    results.append(f"🧬 代{gen} 无变异(随机跳过)")
        else:
            # 70%概率走标准随机变异
            mutation = random_mutation_operator()
            if mutation:
                gene, old_val, new_val, desc = mutation
                genome = load_genome()
                if gene in genome:
                    update_genome({gene: new_val})
                    lineage["pending_mutation"] = {
                        "gene": gene,
                        "old_value": old_val,
                        "new_value": new_val,
                        "generation": gen,
                        "timestamp": time.time()
                    }
                    results.append(f"🧬 代{gen} 变异:{desc}")
                    
                # 写因果链
                try:
                    from brain.share import write_chain
                    write_chain({
                        "src": "进化引擎",
                        "rel": f"变异#{gen}",
                        "dst": f"{gene}[{old_val}→{new_val}]",
                        "dimension": "系统",
                        "content": f"世代{gen}随机变异:{desc}",
                        "strength": 0.9
                    })
                except:
                    pass
            else:
                results.append(f"🧬 代{gen} 无变异(随机跳过)")
    
    # 代末(phase==GENERATION_LENGTH-1): 选择压力
    elif phase == GENERATION_LENGTH - 1 and lineage.get("pending_mutation"):
        pm = lineage["pending_mutation"]
        current_fitness = measure_fitness()
        baseline = lineage.get("fitness_baseline", current_fitness)
        
        diff = current_fitness - baseline
        
        # 记录世系
        gen_entry = {
            "generation": gen,
            "gene": pm["gene"],
            "old_value": pm["old_value"],
            "new_value": pm["new_value"],
            "baseline_fitness": baseline,
            "current_fitness": current_fitness,
            "diff": round(diff, 4),
            "kept": diff >= -0.01,  # 轻微下降也保留(容错)
            "timestamp": time.time()
        }
        lineage.setdefault("generations", []).append(gen_entry)
        
        if diff >= 0.001:
            # 适应度提升 → 保留变异(遗传)
            results.append(f"🧬 代{gen} 变异保留✅: {pm['gene']}→{pm['new_value']} (适应度+{diff:+.4f})")
            lineage["pending_mutation"] = None
            # 加入基因池(有性繁殖的亲本库)
            try:
                _add_to_pool(load_genome(), current_fitness, gen)
            except:
                pass
            # 繁殖: 创建新gen_文件(基因复制+新功能化)
            try:
                spawn_results = _spawn_action_gen(gen)
                if isinstance(spawn_results, list):
                    for sr in spawn_results:
                        if isinstance(sr, int):
                            lineage["last_spawn_gen"] = sr
                        else:
                            results.append(sr)
            except Exception as e:
                results.append(f"  繁殖失败: {e}")
        elif diff >= -0.005:
            # 适应度轻微下降但可接受 → 保留(容错)
            results.append(f"🧬 代{gen} 变异保留⚠️: {pm['gene']}→{pm['new_value']} (适应度{diff:+.4f})")
            lineage["pending_mutation"] = None
        else:
            # 适应度下降 → 回滚(自然选择淘汰)
            update_genome({pm["gene"]: pm["old_value"]})
            results.append(f"🧬 代{gen} 变异淘汰: {pm['gene']}←{pm['old_value']} (适应度{diff:+.4f}, 回滚)")
            lineage["pending_mutation"] = None
    
    # 记录适应度轨迹
    try:
        flog = json.loads(FITNESS_LOG.read_text()) if FITNESS_LOG.exists() else {"history": []}
    except:
        flog = {"history": []}
    flog["history"].append({
        "cycle": cycle_num,
        "generation": gen,
        "fitness": measure_fitness(),
        "phase": "mutation" if phase == 0 else ("selection" if phase == GENERATION_LENGTH-1 else "running"),
        "timestamp": time.time()
    })
    flog["history"] = flog["history"][-200:]  # 保留最近200条
    FITNESS_LOG.write_text(json.dumps(flog, ensure_ascii=False, indent=2))
    
    # 限制世系记录长度
    if len(lineage.get("generations", [])) > 100:
        lineage["generations"] = lineage["generations"][-100:]
    
    _save_evolution_lineage(lineage)
    
    # v3.1: 基因表达脉冲 — 检测维度缺口并自动创建gen文件
    try:
        from brain.gene_expression import auto_express_pulse as _ge_pulse
        _ge_results = _ge_pulse(cycle_num)
        results.extend(_ge_results)
    except Exception as _ge_e:
        pass  # 静默失败，不干扰主线
    
    # v4.1: 进化反馈闭环 — 感知进化速度，自动调节进化策略
    try:
        _feedback_results = _evolution_feedback_pulse(cycle_num, gen)
        results.extend(_feedback_results)
    except Exception as _fe_e:
        pass
    
    return results


def _evolution_feedback_pulse(cycle_num, gen):
    """进化反馈脉冲: 感知进化速度, 调节进化策略
    
    每代末运行一次:
    - 计算最近3代的适应度变化率
    - 如果停滞(变化<0.005/代) → 增大变异幅度
    - 如果过快(变化>0.05/代) → 稳定为微调模式
    - 生成自我感知链
    """
    from brain.genome import update_genome, load_genome
    results = []
    
    # 只在每代末运行(代末刚好在phase==9或者generation变化时)
    try:
        lineage = _load_evolution_lineage()
        generations = lineage.get("generations", [])
        
        if len(generations) < 3:
            return results  # 数据不足以分析
        
        # 看最近3代
        recent = generations[-3:]
        diffs = [g["diff"] for g in recent]
        avg_diff = sum(diffs) / len(diffs)
        last_gen = generations[-1]
        
        genome = load_genome()
        
        # 生成反馈链
        trend = "上升" if avg_diff > 0.005 else ("下降" if avg_diff < -0.005 else "平台")
        msg = f"🧬 进化反馈[代{gen}]: 平均适应度变化={avg_diff:+.4f}/代, 趋势={trend}"
        results.append(msg)
        
        if avg_diff < 0.003 and avg_diff > -0.003:
            # 平台期: 增大变异生成量, 跳出局部最优
            current = genome.get("gen.max_per_cycle", 3)
            new_val = min(8, current + 1)
            if new_val > current:
                update_genome({"gen.max_per_cycle": new_val})
                results.append(f"  适应度平台期, 增大生成量: {current}→{new_val}")
        elif avg_diff > 0.02:
            # 快速上升: 减少生成量, 专注收敛
            current = genome.get("gen.max_per_cycle", 3)
            new_val = max(1, current - 1)
            if new_val < current:
                update_genome({"gen.max_per_cycle": new_val})
                results.append(f"  进化加速, 收敛生成量: {current}→{new_val}")
        
        # 写入自我感知进化链
        try:
            from brain.share import write_chain
            write_chain({
                "src": "进化反馈引擎",
                "rel": f"感知#{gen}",
                "dst": f"趋势:{trend}",
                "dimension": "系统",
                "content": f"代{gen}进化反馈: 平均{avg_diff:+.4f}/代, 趋势{trend}, {len(generations)}代累计",
                "strength": 0.8
            })
        except:
            pass
        
        return results
    except Exception as e:
        return [f"进化反馈异常: {e}"]


# ═══════════════════════════════════════════════════
# v5: 有性繁殖 — 基因池+杂交算子
# ═══════════════════════════════════════════════════

GENE_POOL_FILE = CLUSTER / ".brain_gene_pool.json"

def _load_gene_pool():
    try:
        return json.loads(GENE_POOL_FILE.read_text())
    except:
        return {"pool": [], "top_fitness": 0.0}

def _save_gene_pool(pool):
    GENE_POOL_FILE.write_text(json.dumps(pool, ensure_ascii=False, indent=2))

def _add_to_pool(genome_snapshot, fitness, generation):
    """将当前基因组加入基因池(仅当适应度优秀)"""
    pool = _load_gene_pool()
    # 检查是否已存在(相同generation)
    for entry in pool["pool"]:
        if entry.get("generation") == generation:
            return  # 已存在
    # 加入
    pool["pool"].append({
        "genome": dict(genome_snapshot),
        "fitness": fitness,
        "generation": generation,
        "timestamp": time.time()
    })
    # 保留适应度最高的5个
    pool["pool"] = sorted(pool["pool"], key=lambda x: x["fitness"], reverse=True)[:5]
    pool["top_fitness"] = max(pool.get("top_fitness", 0), fitness)
    _save_gene_pool(pool)

def crossover_operator():
    """杂交算子: 从基因池选2个亲本, 交叉产生新基因组
    
    对每个基因:
      - 50%取自亲本A, 50%取自亲本B
      - 5%概率发生微变异
    
    返回:
        (top_gene, changes_dict, desc) 或 None
    """
    pool = _load_gene_pool()
    if len(pool.get("pool", [])) < 2:
        return None
    
    from brain.genome import load_genome
    current = load_genome()
    
    # 取适应度TOP2作亲本
    parents = pool["pool"][:2]
    p1, p2 = parents[0]["genome"], parents[1]["genome"]
    p1_gen = parents[0]["generation"]
    p2_gen = parents[1]["generation"]
    
    changes = {}
    genes = _get_mutable_genes()
    
    for name, current_val, min_v, max_v, is_int in genes:
        # 从亲本取值
        v1 = p1.get(name)
        v2 = p2.get(name)
        
        if v1 is None or v2 is None:
            continue
        if v1 == v2:
            continue  # 双亲一致，无杂交价值
        
        # 杂交: 随机选一个亲本的值
        new_val = v1 if random.random() < 0.5 else v2
        
        # 5%概率微变异
        if random.random() < 0.05:
            mut_delta = 1 if is_int else new_val * 0.05
            direction = 1 if random.random() > 0.5 else -1
            if is_int:
                new_val += direction * max(1, int(new_val * 0.1))
            else:
                new_val += direction * new_val * 0.1
            new_val = max(min_v, min(new_val, max_v))
            if is_int:
                new_val = int(round(new_val))
            else:
                new_val = round(new_val, 4)
        
        if new_val != current_val:
            changes[name] = new_val
    
    if not changes:
        return None
    
    # 摘要
    top_name = list(changes.keys())[0]
    old_top = current.get(top_name, "?")
    new_top = changes[top_name]
    desc = f"杂交#p{p1_gen}x{p2_gen}: {top_name} {old_top}→{new_top}"
    
    return (top_name, changes, desc)


# 在_evolution_pulse的代初变异阶段加入杂交
def _apply_crossover_or_mutation(lineage, gen, results):
    """代初: 30%概率杂交, 70%概率随机变异"""
    from brain.genome import update_genome, load_genome
    
    mutation = None
    is_crossover = False
    
    # 30%概率试试杂交(需要基因池有≥2个亲本)
    if random.random() < 0.3:
        mutation = crossover_operator()
        if mutation:
            is_crossover = True
    
    # 如果没触发杂交或杂交不可行，走随机变异
    if not mutation:
        mutation = random_mutation_operator()
    
    if not mutation:
        results.append(f"🧬 代{gen} 无变异(随机跳过)")
        return
    
    if is_crossover:
        gene, changes, desc = mutation
        genome = load_genome()
        old_val = genome.get(gene, "?")
        new_val = changes.get(gene, old_val)
        
        # 应用所有杂交变化
        for g_name, g_val in changes.items():
            update_genome({g_name: g_val})
        
        lineage["pending_mutation"] = {
            "gene": gene,
            "old_value": old_val,
            "new_value": new_val,
            "generation": gen,
            "crossover": True,
            "parent_generations": desc.split("#")[1].split("x") if "#" in desc else [],
            "all_changes": changes,
            "timestamp": time.time()
        }
        results.append(f"🧬 代{gen} 杂交:{desc}")
    else:
        gene, old_val, new_val, desc = mutation
        genome = load_genome()
        if gene in genome:
            update_genome({gene: new_val})
            lineage["pending_mutation"] = {
                "gene": gene,
                "old_value": old_val,
                "new_value": new_val,
                "generation": gen,
                "timestamp": time.time()
            }
            results.append(f"🧬 代{gen} 变异:{desc}")


def _spawn_action_gen(generation):
    """繁殖: 适应度提升后, 为最弱维创建API级gen_文件(基因复制+新功能化)
    
    只在以下条件触发:
    1) 有未覆盖的弱维(无对应gen_文件)
    2) gen文件总数未超限
    3) 距离上次繁殖至少3代
    """
    from brain.genome import load_genome
    genome = load_genome()
    max_files = genome.get("engine.max_files", 50)
    
    # 检查gen文件总数
    existing_gens = list(CLUSTER.glob("brain/gen_*.py")) + list(CLUSTER.glob("brain/generated_*.py"))
    if len(existing_gens) >= max_files:
        return ["  繁殖跳过: gen文件已达上限(%d)" % max_files]
    
    # 检查最近是否已繁殖过
    lineage = _load_evolution_lineage()
    last_spawn_gen = lineage.get("last_spawn_gen", -999)
    if generation - last_spawn_gen < 3:
        return ["  繁殖跳过: 距上次繁殖仅%d代" % (generation - last_spawn_gen)]
    
    # 读海马体找最弱维
    hip = _load_hip()
    chains = hip.get("causal_chains", [])
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1
    
    # 排序找弱维(排除系统和未分类)
    sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
    weak_dims = [d for d, c in sorted_dims if d not in ("系统", "未分类", "")][:5]
    if not weak_dims:
        return ["  繁殖跳过: 无可用弱维"]
    
    # 找第一个没有对应gen_文件的弱维
    import re
    existing_names = set()
    for f in existing_gens:
        m = re.match(r"gen_(.+?)(?:_\d{8})?\.py$", f.name)
        if m:
            existing_names.add(m.group(1).lower())
    
    target_dim = None
    for d in weak_dims:
        d_clean = d.lower().replace(" ", "_").replace("-", "_")
        if d_clean not in existing_names:
            target_dim = d
            break
    
    if not target_dim:
        return ["  繁殖跳过: 所有弱维已有gen_文件"]
    
    # 创建API级gen_文件
    safe_name = target_dim.lower().replace(" ", "_").replace("-", "_")
    ts = time.strftime("%Y%m%d_%H%M%S")
    
    # 手工构建模板(避免f-string嵌套问题)
    template_lines = []
    template_lines.append('"""')
    template_lines.append('Brain-Engineered: %s (进化代#%d)' % (safe_name, generation))
    template_lines.append('主动API传感器 — 调用外部燃料产生深度洞察')
    template_lines.append('"""')
    template_lines.append('import json, sys, os, time')
    template_lines.append('from pathlib import Path')
    template_lines.append('')
    template_lines.append('CLUSTER = Path(__file__).resolve().parent.parent')
    template_lines.append('if str(CLUSTER) not in sys.path:')
    template_lines.append('    sys.path.insert(0, str(CLUSTER))')
    template_lines.append('')
    template_lines.append('')
    template_lines.append('def engineer_%s():' % safe_name)
    template_lines.append('    """[%s] 进化代#%d繁殖的API传感器"""' % (target_dim, generation))
    template_lines.append('    from brain.share import write_chain as _wc')
    template_lines.append('')
    template_lines.append('    # 1) 读取当前维度状态')
    template_lines.append('    try:')
    template_lines.append('        hip_file = CLUSTER / "hippocampus_memory.json"')
    template_lines.append('        hip = json.loads(hip_file.read_text())')
    template_lines.append('        chains = hip.get("causal_chains", [])')
    template_lines.append('        dim_counts = {}')
    template_lines.append('        for c in chains:')
    template_lines.append('            d = c.get("dimension", "未分类")')
    template_lines.append('            dim_counts[d] = dim_counts.get(d, 0) + 1')
    template_lines.append('        my_count = dim_counts.get("%s", 0)' % safe_name)
    template_lines.append('        total = len(chains)')
    template_lines.append('    except:')
    template_lines.append('        my_count = 0')
    template_lines.append('        total = 0')
    template_lines.append('')
    template_lines.append('    # 2) 调用API桥产生真洞察')
    template_lines.append('    insight = "进化自愈: %s维度活脉冲"' % target_dim)
    template_lines.append('    try:')
    template_lines.append('        from api_bridge import APIBridge')
    template_lines.append('        bridge = APIBridge()')
    template_lines.append('        prompt = ("[进化传感器·%s]当前链数:" + str(my_count) + "/" + str(total) +' % target_dim)
    template_lines.append('                 " 任务:针对维度%s生成进化洞察" +' % target_dim)
    template_lines.append('                 " 要求:直接改变daemon行为的行动方向" +')
    template_lines.append('                 " 格式:JSON(insight,action,parameter)")')
    template_lines.append('        result = bridge.call_api(prompt)')
    template_lines.append('        if result.get("success"):')
    template_lines.append('            content = result.get("content","")')
    template_lines.append('            import re as _re')
    template_lines.append("            jm = _re.search(r'\\{[^}]*\"insight\"[^}]*\\}', content, _re.DOTALL)")
    template_lines.append('            if jm:')
    template_lines.append('                parsed = json.loads(jm.group())')
    template_lines.append('                insight = parsed.get("insight", insight)')
    template_lines.append('                if parsed.get("action"):')
    template_lines.append('                    insight += " | 行动: " + parsed["action"]')
    template_lines.append('    except:')
    template_lines.append('        pass')
    template_lines.append('')
    template_lines.append('    # 3) 写链')
    template_lines.append('    _wc({')
    template_lines.append('        "src": "进化·%s",' % safe_name)
    template_lines.append('        "rel": "代#%d",' % generation)
    template_lines.append('        "dst": "%s",' % safe_name)
    template_lines.append('        "dimension": "%s",' % safe_name)
    template_lines.append('        "content": insight[:120],')
    template_lines.append('        "strength": 0.8')
    template_lines.append('    })')
    template_lines.append('')
    template_lines.append("    return '[%s] ' + insight[:60]" % safe_name)
    
    template = '\n'.join(template_lines)
    
    target = CLUSTER / ("brain/gen_evo_%s_%s.py" % (safe_name, ts.split('_')[0]))
    target.write_text(template, encoding="utf-8")
    
    # 写因果链(繁殖记录直接写,不依赖lineage保存)
    try:
        from brain.share import write_chain
        write_chain({
            "src": "进化引擎",
            "rel": "繁殖#%d" % generation,
            "dst": "gen_evo_%s" % safe_name,
            "dimension": "系统",
            "content": "代%d基因复制+新功能化: 为弱维[%s]创建API传感器" % (generation, target_dim),
            "strength": 0.95
        })
    except:
        pass
    
    return ["** 繁殖: gen_evo_%s_%s.py (弱维:%s)" % (safe_name, ts.split('_')[0], target_dim), generation]


def pulse(cycle_num):
    """每周期脉冲 — 被daemon调用（v4: 管道感知型）"""
    results = []
    
    # ── v4: 检查动作管道状态，决定是否让碳基进化引擎运行 ──
    _suppress_evolution = False
    try:
        from brain.pipeline_report import get_report_summary
        _pr = get_report_summary()
        if _pr:
            _ph = _pr.get("pipeline_health", {})
            _coord = _pr.get("coordinator", {})
            _actq = _pr.get("action_queue", {})
            # 如果管道有活跃动作待处理且健康, 抑制碳基随机变异防冲突
            if _coord and _coord.get("total", 0) > 0 and _ph.get("score", 0) >= 3:
                _suppress_evolution = True
            # 管道活跃动作数 > 3 也抑制
            if _actq and _actq.get("pending", 0) > 3:
                _suppress_evolution = True
    except:
        pass
    
    if _suppress_evolution:
        results.append("管道活跃中, 抑制碳基随机变异(防动作冲突)")
    else:
        # v3: 碳基进化脉冲(随机变异+自然选择)
        try:
            evo_results = _evolution_pulse(cycle_num)
            results.extend(evo_results)
        except Exception as e:
            results.append(f"进化脉冲异常: {e}")
    
    # v2: 预定义变异建议(保留作为补充策略)
    suggestions, new_phase, phase_changed = suggest_mutation()

    # 相位变化日志
    if phase_changed:
        results.append(f"相位变迁: 积累期→变异期" if new_phase == "mutation" else "相位变迁: 变异期→积累期")

    # 执行变异
    if suggestions:
        for s in suggestions:
            ok = apply_mutation(s)
            if ok:
                broken = " [循环打破!]" if s.get("_cycle_broken") else ""
                results.append(f"行为变异: {s['type']} → {s['desc'][:40]}{broken}")

    return results
