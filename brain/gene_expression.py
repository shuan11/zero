"""brain/gene_expression.py — 基因表达·自适应器官生成器 v1
P130: 当系统发现维度缺口时，自动创建新的gen文件(器官)来补。
就像碳基生物的基因表达——需要什么蛋白质就转录什么基因。

机制:
  1. 扫描所有维度 → 哪些有活跃gen文件覆盖
  2. 对于"表达不足"的维度(链数低/无专属gen文件) → 自动创建gen文件
  3. 新gen文件基于当前系统洞察注入真实内容(非模板)
  4. 进化系统控制表达开关(activate/deactivate)
"""

import json, os, sys, time, textwrap, traceback
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

# 表达记录
EXPRESSION_LOG = CLUSTER / ".brain_gene_expression.json"

# 模板路径
GEN_TEMPLATE = '''"""
Brain-Engineered: {dim_name} (generation {gen})
{insight}
"""
import json, sys as _sys, time as _time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in _sys.path:
    _sys.path.insert(0, str(CLUSTER))

_GEN_FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

def engineer_{dim_name}():
    """{insight} — 含完整管道集成"""
    from brain.share import write_chain as _wc
    _now = _time.time()
    
    # ── 1. 写入洞察链(永久记忆) ──
    _wc({{
        "src": "脑核·{dim_name}·脉冲",
        "rel": "基因表达#{gen}",
        "dst": "{dim_name}",
        "dimension": "{dim_name}",
        "content": "{insight}",
        "strength": 0.6
    }})
    
    # ── 2. 读取自身维度健康 ──
    try:
        from brain.share import read_hip as _rh
        hip = _rh()
        chains = hip.get("causal_chains", []) if isinstance(hip, dict) else []
    except:
        chains = []
    dim_count = sum(1 for c in chains if c.get("dimension") == "{dim_name}")
    total = len(chains)
    
    # ── 3. 相对弱维计算 (与系统其他维度比较) ──
    _is_weak = False
    _max_other = 0
    try:
        _all_dims = {{}}
        for c in chains:
            d = c.get("dimension", "未分类")
            _all_dims[d] = _all_dims.get(d, 0) + 1
        _other_counts = [c for d,c in _all_dims.items() if d != "{dim_name}" and d not in ("系统","未分类")]
        if _other_counts:
            _max_other = max(_other_counts)
        _threshold = int(_max_other * 0.65)
        _is_weak = dim_count < _threshold and dim_count > 0
    except:
        pass
    
    # ── 4. 动作注册(通过动作管道) ──
    try:
        from brain.action_registry import register_action as _ra
        
        # 4a. 弱维时注册调优动作
        if _is_weak:
            _ra("update_genome", {{"changes": {{}}, "dimension": "{dim_name}",
                "reason": f"{{dim_name}}偏弱({{dim_count}}/max={{_max_other}})"}},
                priority=5, source="gene:{dim_name}")
            
            # 同时注入自愈链(强度高,会被验证器检查)
            _wc({{
                "src": "自愈·{dim_name}",
                "rel": "基因表达·#{gen}",
                "dst": "{dim_name}",
                "dimension": "{dim_name}",
                "content": "{dim_name}偏弱({{dim_count}}条/总{{total}}条)自动注入夯实",
                "strength": 0.8
            }})
        
        # 4b. 强维时注册巩固动作
        if not _is_weak and dim_count > 0:
            _ra("write_chain", {{"src": f"巩固·{dim_name}",
                "rel": f"基因表达·#{gen}", "dst": "{dim_name}",
                "content": f"{dim_name}维度健康({{dim_count}}条),脉冲巩固",
                "dimension": "{dim_name}", "strength": 0.5}},
                priority=8, source="gene:{dim_name}")
    except:
        pass
    
    # ── 5. 更新反馈(供后处理合成器+协调器使用) ──
    try:
        fb = json.loads(_GEN_FEEDBACK_FILE.read_text()) if _GEN_FEEDBACK_FILE.exists() else {{"reports": []}}
        fb.setdefault("reports", []).append({{
            "dimension": "{dim_name}",
            "chain_count": dim_count,
            "total_chains": total,
            "weak": _is_weak,
            "max_other": _max_other,
            "threshold": locals().get('_threshold', 0),
            "insight": "{insight}",
            "engine": "gene_expression_v3",
            "timestamp": _now,
            "cycle": 0
        }})
        fb["reports"] = fb["reports"][-200:]
        _GEN_FEEDBACK_FILE.write_text(json.dumps(fb, ensure_ascii=False, indent=2))
    except:
        pass
    
    if _is_weak:
        return f"[弱] {dim_name}={{dim_count}}/{{total}} (max={{_max_other}})"
    return f"[稳] {dim_name}={{dim_count}}/{{total}}"
'''


def _load_expression_log():
    """读取基因表达历史"""
    try:
        return json.loads(EXPRESSION_LOG.read_text())
    except:
        return {"expressions": [], "generation": 0, "total_created": 0}


def _save_expression_log(log):
    EXPRESSION_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))


def get_dimension_coverage():
    """扫描哪些维度有活跃gen文件覆盖
    
    返回:
        covered: set[维度名] — 有gen文件覆盖的维度
        uncovered: list[(维度名, 链数, insight)] — 缺覆盖的维度
    """
    # 1. 扫描gen文件
    gen_files = list(CLUSTER.glob("brain/gen_*.py"))
    gen_dims = set()
    for fpath in gen_files:
        stem = fpath.stem  # gen_洞察循环_20260614
        parts = stem.split("_")
        if len(parts) >= 3:
            dim = "_".join(parts[1:-1])
        else:
            dim = stem
        gen_dims.add(dim)
    
    # 2. 读取海马体维度分布
    try:
        from brain.share import read_hip
        hip = read_hip()
    except:
        try:
            hip = json.loads((CLUSTER / "hippocampus_memory.json").read_text())
        except:
            hip = {"causal_chains": []}
    
    chains = hip.get("causal_chains", [])
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1
    
    # 3. 找无覆盖的维度
    covered = set()
    uncovered = []
    for dim, count in sorted(dim_counts.items(), key=lambda x: -x[1]):
        # 检查是否有以该维度命名的gen文件
        # gen_文件命名: gen_{维度名}_{日期}.py
        has_gen = False
        for gdim in gen_dims:
            # 维度名可能有多种写法
            if dim.replace(" ", "") == gdim.replace(" ", "") or dim == gdim:
                has_gen = True
                break
        
        # 更直接的匹配: 检查文件系统
        for prefix in [f"gen_{dim}_", f"gen_{dim.replace(' ','')}_"]:
            if list(CLUSTER.glob(f"brain/{prefix}*.py")):
                has_gen = True
                break
        
        if has_gen:
            covered.add(dim)
        elif count >= 50:  # 至少有一定链数才值得创建gen文件
            # 生成洞察
            if count < 200:
                insight = f"{dim}维度链数偏弱({count}条)，需主动工程化注入高质量链"
            elif count < 400:
                insight = f"{dim}维度生长中({count}条)，需持续注入强化"
            else:
                insight = f"{dim}维度已有{count}条链，需深化质量而非数量"
            uncovered.append((dim, count, insight))
    
    return covered, sorted(uncovered, key=lambda x: -x[1])


def create_gene_engine(dim_name, chain_count, insight, generation=0):
    """为目标维度创建新的gen文件(基因表达)
    
    返回: (成功, 文件路径或错误信息)
    """
    # 检查是否已存在同维度文件
    existing = list(CLUSTER.glob(f"brain/gen_{dim_name}_*.py"))
    if existing:
        return False, f"维度'{dim_name}'已有gen文件: {existing[0].name}"
    
    # 生成文件名
    date_str = time.strftime("%Y%m%d")
    fname = f"gen_{dim_name}_{date_str}.py"
    fpath = CLUSTER / "brain" / fname
    
    # 渲染模板
    content = GEN_TEMPLATE.format(
        dim_name=dim_name,
        gen=generation,
        insight=insight[:200]  # 防止超长
    )
    
    try:
        fpath.write_text(content, encoding="utf-8")
        
        # 记录表达
        log = _load_expression_log()
        log.setdefault("expressions", []).append({
            "dimension": dim_name,
            "file": fname,
            "chain_count": chain_count,
            "insight": insight[:100],
            "generation": generation,
            "timestamp": time.time()
        })
        log["total_created"] = log.get("total_created", 0) + 1
        log["generation"] = generation
        log["last_expression"] = time.time()
        _save_expression_log(log)
        
        return True, fname
    except Exception as e:
        return False, str(e)


def expression_pulse(cycle_num, generation=0):
    """基因表达脉冲 — 被调用以填补维度缺口
    
    返回: created: [(dim, fname), ...], info: str
    """
    covered, uncovered = get_dimension_coverage()
    created = []
    
    if not uncovered:
        return created, f"所有维度已覆盖({len(covered)}维)"
    
    # 每周期最多创建2个新gen文件（防暴涨）
    max_create = 2
    for dim, count, insight in uncovered[:max_create]:
        # 避免过度创建同一维度
        existing = list(CLUSTER.glob(f"brain/gen_{dim}_*.py"))
        if existing:
            continue
        
        success, result = create_gene_engine(dim, count, insight, generation)
        if success:
            created.append((dim, result))
    
    if created:
        info = f"新表达{len(created)}个基因: {', '.join(d for d,_ in created)}"
    else:
        info = f"缺口{len(uncovered)}维，但已全有gen文件或已达上限"
    
    return created, info


def auto_express_pulse(cycle_num):
    """被evolution_pulse调用的自动表达检查
    
    检测基因缺口 → 自动创建gen文件
    """
    from brain.genome import load_genome
    genome = load_genome()
    
    generation = cycle_num // 10  # 与进化系统同步世代
    
    results = []
    
    # 检查: 每2个世代检查一次
    if cycle_num % 20 == 0:
        covered, uncovered = get_dimension_coverage()
        
        if uncovered:
            # 创建新基因
            created, info = expression_pulse(cycle_num, generation)
            if created:
                for dim, fname in created:
                    results.append(f"🧬 新基因表达: {dim} → brain/{fname}")
                
                # 写因果链
                try:
                    from brain.share import write_chain
                    write_chain({
                        "src": "基因表达引擎",
                        "rel": f"新表达#{generation}",
                        "dst": f"{len(created)}新基因",
                        "dimension": "系统",
                        "content": f"自动表达{len(created)}个新基因: {', '.join(d for d,_ in created)}",
                        "strength": 0.8
                    })
                except:
                    pass
            else:
                results.append(f"🧬 基因缺口{len(uncovered)}维，但已有gen文件或已达上限")
        else:
            results.append(f"🧬 全维度覆盖({len(covered)}维) — 不需新表达")
    
    return results
