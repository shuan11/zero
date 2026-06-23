"""brain/cross_synthesis.py — P113: 跨维合成引擎
当所有维度稳定后，从多个强维度中提取交叉洞察，生成合成链。

机制:
  1. 选当前最强的3-5个维度（链数最多）
  2. 从每个维度提取代表性链内容
  3. 用这些内容生成[[甲×乙×丙]]格式的合成链
  4. 合成链同时标记多个维度
  5. 写入海马体作为高价值知识
"""

import json, random, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent

SYNTHESIS_LOG = CLUSTER / ".brain_synthesis.json"

# ═══ 模块级: 启动仪表盘(仅导入时执行一次) ═══
try:
    import threading
    from brain.zero_dashboard import start_dashboard as _start_dash
    _dash_thread = threading.Thread(target=lambda: _start_dash(21420), daemon=True)
    _dash_thread.start()
except Exception:
    pass  # 仪表盘可选

def _load_goal():
    """读取当前目标"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        return json.loads(gf.read_text())
    except:
        return None

def _check_synthesis_staleness(log_data=None):
    """检查合成是否陷入同质化——最后N条是否都是同一组维度"""
    if log_data is None:
        log_data = _load_synthesis_log()
    syntheses = log_data.get("syntheses", [])
    if len(syntheses) < 5:
        return False  # 数据不足，不视为同质化
    recent = syntheses[-5:]
    # 检查是否所有recent合成都使用相同的维度对
    # 用集合比较：如果每条的维度组合都一样→同质化
    dim_sets = [frozenset(s.get("dimensions", [])) for s in recent]
    if len(set(dim_sets)) <= 2:
        return True  # 最后5条只有1-2种维度组合→同质化
    return False

def _stale_dim_pairs(log_data=None):
    """找出最近未使用过的维度对（以打破同质化）"""
    ranked = [(d, v) for d, v in _dim_rank() if d not in ("系统", "未分类")]
    all_dims = [d for d, _ in ranked]
    if len(all_dims) < 4:
        return _random_dim_trio(all_dims)
    if log_data is None:
        log_data = _load_synthesis_log()
    recent_pairs = set()
    for s in log_data.get("syntheses", [])[-20:]:
        dims = sorted(s.get("dimensions", []))
        for i in range(len(dims)):
            for j in range(i+1, len(dims)):
                recent_pairs.add((dims[i], dims[j]))
    # 从弱维+强维交叉中找未用过的对
    weak_dims = [d for d, _ in ranked[-6:]]  # 后6个弱维度
    strong_dims = [d for d, _ in ranked[:6]]  # 前6个强维度
    import random
    random.shuffle(weak_dims)
    random.shuffle(strong_dims)
    for wd in weak_dims:
        for sd in strong_dims:
            if wd == sd:
                continue
            if (wd, sd) not in recent_pairs and (sd, wd) not in recent_pairs:
                return [sd, wd, all_dims[2]]  # 强×弱 + 第3强
    return _random_dim_trio(all_dims)

def _random_dim_trio(all_dims):
    """随机选3个维度（至少跨首尾）"""
    import random
    if len(all_dims) >= 6:
        # 从强中弱各选1个
        return [all_dims[0], all_dims[len(all_dims)//2], all_dims[-1]]
    random.shuffle(all_dims)
    return all_dims[:3]

def _select_dims_for_synthesis(goal):
    """根据目标选择合成维度对，含同质化检测"""
    ranked = [(d, v) for d, v in _dim_rank() if d not in ("系统", "未分类")]
    log_data = _load_synthesis_log()
    
    # 检测同质化——如果最近合成都是同一批维度，切换到新组合
    if _check_synthesis_staleness(log_data):
        novel = _stale_dim_pairs(log_data)
        # 将新颖组合写入goal（后续cycle会读取）
        if goal:
            goal["_novel_pair"] = "stale_break"
        return novel[:3]
    
    if not goal:
        return [d for d, v in ranked[:3]]
    
    gtype = goal.get("goal_type", "")
    focus = goal.get("focus_dim", "")
    
    if gtype == "synthesize" and focus:
        # 使用目标指定的维度对
        dims = focus.split("×")
        available = {d for d, _ in ranked}
        valid = [d for d in dims if d in available]
        if len(valid) >= 2:
            return valid[:3]  # 目标维度优先
        # 如果目标维度不在排名中，补充最强维度
        for d, v in ranked:
            if d not in valid:
                valid.append(d)
                if len(valid) >= 3:
                    break
        return valid[:3]
    
    elif gtype == "explore" and focus:
        # 探索模式：包含目标维度
        dims = [focus]
        for d, v in ranked:
            if d not in dims and d != focus:
                dims.append(d)
                if len(dims) >= 3:
                    break
        return dims[:3]
    
    elif gtype == "deepen":
        # 深化模式：最强2维 + 随机第3
        top3 = [d for d, v in ranked[:3]]
        return top3
    
    else:
        # 巩固/默认：最强3维
        return [d for d, v in ranked[:3]]

def _load_hip():
    try:
        from brain.share import read_hip
        return read_hip()
    except:
        hip_file = CLUSTER / "hippocampus_memory.json"
        return json.loads(hip_file.read_text())

def _dim_rank():
    """获取维度链数排名"""
    data = _load_hip()
    chains = data.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    sorted_dims = sorted(dims.items(), key=lambda x: -x[1])
    return sorted_dims

def _sample_chains(dim, n=5):
    """从指定维度采样n条链"""
    data = _load_hip()
    chains = data.get("causal_chains", [])
    dim_chains = [c for c in chains if c.get("dimension") == dim]
    random.shuffle(dim_chains)
    return dim_chains[:n]

def _load_synthesis_log():
    try:
        return json.loads(SYNTHESIS_LOG.read_text())
    except:
        return {"syntheses": [], "last_synthesis_cycle": -1}

def _save_synthesis_log(log):
    SYNTHESIS_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))

def synthesize(cycle_num):
    """执行跨维合成 — 含交叉创生优先"""
    from brain.share import write_chain as _wc
    log_data = _load_synthesis_log()
    # 兼容旧格式—确保关键字段存在
    if "syntheses" not in log_data:
        log_data["syntheses"] = []
    
    # 目标感知维度选择
    _goal = _load_goal()
    _goal_dims = _select_dims_for_synthesis(_goal)
    ranked = [(d, v) for d, v in _dim_rank() if d not in ("系统", "未分类")]
    
    # 使用目标感知选择或回退top3
    dim_names = _goal_dims if len(_goal_dims) >= 3 else [d for d, v in ranked[:3]]
    if len(dim_names) < 2:
        return [], "维度太少(<2)"
    
    # ═══ 交叉创生路径（优先）═══
    try:
        # 兼容包内导入和直接运行
        try:
            from brain.gen_合成 import _synthesize_locally
        except ImportError:
            from .gen_合成 import _synthesize_locally
        
        # 对前两维做交叉创生
        cross_insight = _synthesize_locally(dim_names[:2])
        if cross_insight:
            combo = "×".join(dim_names[:2])
            synthesis_content = f"工程·合成: {cross_insight['insight'][:200]}"
            
            # 写入海马体
            _wc({
                "src": "合成",
                "rel": f"交叉创生#{len(log_data['syntheses'])+1}",
                "dst": dim_names[0],
                "dimension": "合成",
                "content": synthesis_content,
                "strength": 0.9,
                "tags": dim_names[:2] + ["启示录工程·交叉创生"]
            })
            
            # 记录日志
            log_data["syntheses"].append({
                "cycle": cycle_num,
                "dimensions": dim_names[:2],
                "content": synthesis_content[:80],
                "type": "cross_creation",
                "revelation": cross_insight.get("revelation", ""),
                "timestamp": time.time()
            })
            if len(log_data["syntheses"]) > 30:
                log_data["syntheses"] = log_data["syntheses"][-30:]
            _save_synthesis_log(log_data)
            
            return [f"交叉创生: {combo} → {cross_insight.get('revelation', '')}"], True
    except Exception as e:
        pass  # 交叉创生失败，回退旧路径
    # 采样链
    samples = {}
    for dim in dim_names:
        samples[dim] = _sample_chains(dim, 3)
    
    # 提取代表性内容
    excerpts = []
    for dim, chains in samples.items():
        for c in chains:
            content = c.get("content", c.get("dst", ""))[:60]
            if content:
                excerpts.append(f"[{dim}] {content}")
    
    if len(excerpts) < 3:
        return [], "样本不足"
    
    # 选择3条代表性内容（每个维度至少1条）
    selected = []
    for dim in dim_names:
        dim_excerpts = [e for e in excerpts if e.startswith(f"[{dim}]")]
        if dim_excerpts:
            selected.append(dim_excerpts[0])
    
    if len(selected) < 2:
        return [], "代表性内容不足"
    
    # 构建合成链内容
    combo = "×".join(dim_names)
    tag = f"[[{combo}]]"
    content_parts = "\n".join(selected[:3])
    synthesis_content = f"{tag} 跨维合成#{len(log_data['syntheses'])+1}:{dim_names[0]}×{dim_names[1]}×{dim_names[2]} \n{content_parts}"
    
    # 写入海马体
    try:
        from brain.share import write_chain
        write_chain({
            "src": f"跨维合成引擎·{combo}",
            "rel": f"合成#{len(log_data['syntheses'])+1}",
            "dst": dim_names[0],
            "dimension": dim_names[0],  # 主维度
            "content": synthesis_content[:120],
            "strength": 0.9,
            "tags": dim_names  # 多维度标记
        })
        
        # 记录日志
        log_data["syntheses"].append({
            "cycle": cycle_num,
            "dimensions": dim_names,
            "content": synthesis_content[:80],
            "excerpts": selected,
            "timestamp": time.time()
        })
        if len(log_data["syntheses"]) > 30:
            log_data["syntheses"] = log_data["syntheses"][-30:]
        _save_synthesis_log(log_data)
        
        return [f"跨维合成: {combo} → {synthesis_content[:40]}..."], True
    except Exception as e:
        return [f"合成异常: {e}"], False

def pulse(cycle_num):
    """每周期脉冲 — 间隔从genome动态读取。目标感知合成维度选择"""
    # 从genome读取动态间隔（由steering设定）
    _interval = 5
    try:
        import json
        _g = json.loads(open(str(CLUSTER / '.brain_genome.json'), encoding='utf-8').read())
        _steer = _g.get('_steering', {}).get('params', {})
        _interval = _steer.get('synthesis_interval', 5)
    except:
        pass
    if cycle_num <= 0 or cycle_num % _interval != 0:
        return []
    
    msgs, ok = synthesize(cycle_num)
    
    # ═══ 集成洞察刺激桥 ═══
    try:
        from brain.insight_stimulus_bridge import pulse as _isp
        _isp_result = _isp(cycle_num)
        if _isp_result:
            msgs.append(_isp_result)
    except Exception:
        pass  # 刺激桥可选，失败不影响合成
    
    # 仪表盘已在模块级启动，此处不再重复
    
    # ═══ 集成一元化合成器 ═══
    try:
        from brain.unified_synthesizer import pulse as _usp
        _us_result = _usp(cycle_num)
        if _us_result:
            msgs.append(_us_result)
    except Exception:
        pass  # 合成器可选
    
    return msgs
