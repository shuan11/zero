#!/usr/bin/env python3
"""
gen_自构.py — P197: 自治模块构建引擎

扫描现有gen_模块分析pulse()模式,提取通用模板,为最弱维
自动生成新模块骨架+真实注入逻辑。降低手工建模块依赖。
"""
import json, os, sys, re, ast
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
BRAIN = CLUSTER / "brain"
_CALL_COUNT = 0

# 模板: 注入型模块的标准骨架
INJECTOR_TEMPLATE = '''#!/usr/bin/env python3
"""
gen_{name}.py — {p0}: {desc}

自动生成于 {date}
"""
import json, os, sys, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_SKIP_EVERY = {skip_every}
_MAX_INJECT = {max_inject}
_SOURCE_DIMS = {source_dims}
_TARGET_DIMS = {target_dims}

def _safe_hip():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        return safe_hip
    except:
        return None

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _SKIP_EVERY > 1 and _CALL_COUNT % _SKIP_EVERY != 0:
        return {{"status": "skipped", "pulse": _CALL_COUNT}}
    
    safe_hip = _safe_hip()
    if not safe_hip:
        return {{"status": "no_safe_hip"}}
    
    total = 0
    for src in _SOURCE_DIMS:
        for tgt in _TARGET_DIMS:
            if src == tgt:
                continue
            chain = {{
                "src": "{src_prefix}_{src}",
                "rel": "{rel_type}",
                "dst": "{tgt_prefix}_{tgt}",
                "strength": round(random.uniform(0.3, 0.7), 2),
                "dimension": tgt,
                "content": f"[自构] {src}模式映射→{tgt}: {function_desc}",
                "source": "gen_{name}"
            }}
            try:
                safe_hip.write_chain(chain)
                total += 1
            except:
                pass
            if total >= _MAX_INJECT:
                break
        if total >= _MAX_INJECT:
            break
    
    return {{
        "status": "ok",
        "pulse": _CALL_COUNT,
        "injected": total,
        "sources": _SOURCE_DIMS,
        "targets": _TARGET_DIMS
    }}

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
'''

# 分析型模块模板
ANALYZER_TEMPLATE = '''#!/usr/bin/env python3
"""
gen_{name}.py — {p0}: {desc}

自动生成于 {date}
自动分析 {target_dim} 维度链结构
"""
import json, os, sys
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0
_SKIP_EVERY = {skip_every}
_TARGET_DIM = "{target_dim}"
_REPORT_FILE = CLUSTER / ".{name}_report.json"

def _get_chains():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        if isinstance(chains, list):
            return [c for c in chains if c.get("dimension") == _TARGET_DIM]
    except:
        pass
    return []

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    if _SKIP_EVERY > 1 and _CALL_COUNT % _SKIP_EVERY != 0:
        return {{"status": "skipped", "pulse": _CALL_COUNT}}
    
    chains = _get_chains()
    if not chains:
        return {{"status": "no_chains_for", "dim": _TARGET_DIM}}
    
    rels = Counter(c.get("rel", "?") for c in chains if c.get("rel"))
    sources = Counter(c.get("source", "?") for c in chains if c.get("source"))
    
    report = {{
        "dim": _TARGET_DIM,
        "total": len(chains),
        "top_rels": dict(rels.most_common(10)),
        "top_sources": dict(sources.most_common(10)),
        "pulse": _CALL_COUNT
    }}
    
    try:
        with open(_REPORT_FILE, "w") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return report

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
'''

def _get_dim_dist():
    """获取维度分布"""
    hip_file = CLUSTER / "hippocampus_memory.json"
    if not hip_file.exists():
        return {}
    try:
        with open(hip_file) as f:
            data = json.load(f)
        chains = data.get("causal_chains", data.get("chains", []))
        dims = {}
        for c in chains if isinstance(chains, list) else []:
            if isinstance(c, dict):
                d = c.get("dimension")
                if d:
                    dims[d] = dims.get(d, 0) + 1
        return dims
    except:
        return {}

def _scan_existing_modules():
    """扫描已有gen模块信息"""
    modules = {}
    for f in sorted(BRAIN.glob("gen_*.py")):
        mod_name = f.stem.replace("gen_", "")
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
            # 检查pulse模式
            has_pulse = "def pulse(" in content
            has_main = 'if __name__ == "__main__"' in content
            # 检查注入模式
            is_injector = "write_chain" in content and "dimension" in content
            is_analyzer = "Counter" in content or "report" in content
            modules[mod_name] = {
                "has_pulse": has_pulse,
                "has_main": has_main,
                "size": len(content),
                "is_injector": is_injector,
                "is_analyzer": is_analyzer
            }
        except:
            modules[mod_name] = {"error": "read_failed"}
    return modules

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 7 != 0:  # 低频, 防止过多IO
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    dims = _get_dim_dist()
    modules = _scan_existing_modules()
    
    if not dims:
        return {"status": "no_dim_data"}
    
    sorted_dims = sorted(dims.items(), key=lambda x: x[1])
    existing = set(modules.keys())
    
    # 为最弱维度检查是否需要新模块
    built = []
    for dim, count in sorted_dims[:5]:  # 最弱5维
        dim_slug = dim.replace(" ", "_").replace("·", "_")
        if dim_slug in existing:
            continue  # 已有同名模块
        
        # 选择模板: 链数<200用注入型, >=200用分析型
        if count < 200:
            skip = 3
            max_inject = 15
            source_dims = [d for d, _ in sorted_dims[-3:]]  # 取强维
            target_dims = [dim]
            
            rel_type = "关联"
            if "时间" in source_dims:
                rel_type = "时间" 
            
            content = INJECTOR_TEMPLATE.format(
                name=dim_slug,
                p0=f"P{197 + len(built)}",
                desc=f"为{dim}维度自建注入模块",
                date="2026-06-18",
                skip_every=skip,
                max_inject=max_inject,
                source_dims=source_dims,
                target_dims=target_dims,
                src_prefix="强维",
                tgt_prefix=dim,
                rel_type=rel_type,
                function_desc=f"强维模式移植至{dim}维度",
            )
        else:
            content = ANALYZER_TEMPLATE.format(
                name=dim_slug,
                p0=f"P{197 + len(built)}",
                desc=f"{dim}维度链分析模块",
                date="2026-06-18",
                skip_every=5,
                target_dim=dim,
            )
        
        fpath = BRAIN / f"gen_{dim_slug}.py"
        try:
            fpath.write_text(content, encoding="utf-8")
            built.append(dim_slug)
        except Exception as e:
            pass
    
    return {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "built": built,
        "existing_modules": len(modules),
        "weakest_dims": [d for d, _ in sorted_dims[:5]]
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
