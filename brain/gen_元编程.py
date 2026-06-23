#!/usr/bin/env python3
"""
gen_元编程.py — P203: 元编程·模块协作分析引擎

系统读取自身gen_模块源码, 分析:
1. 每个模块的pulse()频率(skip_every)
2. 注入目标维度
3. 读/写文件依赖
4. 模块间协作模式(谁注入谁)
输出.meta_collab.json, 识别协作热区和孤岛。
"""
import json, os, sys, re, ast
from pathlib import Path
from collections import defaultdict, Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
BRAIN = CLUSTER / "brain"
_CALL_COUNT = 0
_COLLAB_FILE = CLUSTER / ".meta_collab.json"

# 文件使用模式
FILE_PATTERNS = [
    (r"\.chain_quality_report\.json", "chain_quality_report"),
    (r"\.brain_health\.json", "brain_health"),
    (r"\.brain_alerts\.json", "brain_alerts"),
    (r"\.concept_tree\.json", "concept_tree"),
    (r"\.trend_data\.json", "trend_data"),
    (r"\.pattern_map\.json", "pattern_map"),
    (r"\.qa_log\.jsonl", "qa_log"),
    (r"\.[\w_]+_report\.json", "custom_report"),
    (r"\.next_p0\.json", "next_p0"),
    (r"hippocampus_memory\.json", "hippocampus"),
]

def _parse_module_metadata(path):
    """解析单个gen模块的元数据"""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except:
        return None
    
    info = {"name": path.stem.replace("gen_", ""), "path": str(path), "size": len(content)}
    
    # 提取docstring
    doc_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
    info["doc"] = doc_match.group(1).strip()[:100] if doc_match else ""
    
    # 提取pulse频率
    skip_match = re.search(r'_SKIP_EVERY\s*=\s*(\d+)', content)
    info["skip_every"] = int(skip_match.group(1)) if skip_match else 1
    
    # 检查是否write_chain注入器
    info["is_injector"] = "write_chain" in content
    info["is_analyzer"] = "Counter" in content or "_REPORT_FILE" in content
    info["has_pulse"] = "def pulse(" in content
    
    # 提取维度引用
    dims = set()
    for m in re.finditer(r'(?:dimension|_TARGET_DIM|_SOURCE_DIMS|_TARGET_DIMS)\s*(?:=|in\s*\[)\s*["\']?(\w+)["\']?', content):
        dims.add(m.group(1))
    for m in re.finditer(r'"dimension"\s*:\s*["\'](\w+)["\']', content):
        dims.add(m.group(1))
    info["dims_mentioned"] = list(dims) if dims else []
    
    # 提取文件依赖
    files_used = set()
    for pat, fname in FILE_PATTERNS:
        if re.search(pat, content):
            files_used.add(fname)
    info["files_used"] = list(files_used) if files_used else []
    
    # 提取源(有dimension键但不是读取hippocampus)
    if info["is_injector"]:
        info["type"] = "injector"
    elif info["is_analyzer"]:
        info["type"] = "analyzer"
    elif "Dashboard" in content or "仪表盘" in content or "http.server" in content:
        info["type"] = "dashboard"
    else:
        info["type"] = "utility"
    
    return info

def _build_collab_graph(modules):
    """构建模块协作图"""
    # 文件级依赖
    file_owners = defaultdict(list)
    for m in modules:
        if not m:
            continue
        for f in m.get("files_used", []):
            file_owners[f].append(m["name"])
    
    # 维度级协作: 谁注入哪个维度
    dim_injectors = defaultdict(list)
    for m in modules:
        if not m or m.get("type") != "injector":
            continue
        for d in m.get("dims_mentioned", []):
            dim_injectors[d].append(m["name"])
    
    # 协作热区: 多人共用的文件
    hot_files = {f: owners for f, owners in file_owners.items() if len(owners) >= 2}
    
    # 隔离模块: 不使用任何共享文件
    isolated = []
    for m in modules:
        if not m:
            continue
        has_shared = any(
            f in hot_files for f in m.get("files_used", [])
        )
        if not has_shared and m["type"] not in ("dashboard",):
            isolated.append(m["name"])
    
    # 协作密度: 共享文件数/总模块数
    total = len([m for m in modules if m])
    shared_count = sum(1 for m in modules if m and any(
        f in hot_files for f in m.get("files_used", [])
    ))
    
    return {
        "hot_files": dict(hot_files),
        "dim_injectors": dict(dim_injectors),
        "isolated_modules": isolated[:20],
        "collab_density": round(shared_count / total, 2) if total else 0,
        "total_modules": total
    }

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 10 != 0 and _CALL_COUNT != 1:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    # 扫描所有gen模块
    gen_files = sorted(BRAIN.glob("gen_*.py"))
    modules = [_parse_module_metadata(f) for f in gen_files]
    modules = [m for m in modules if m]
    
    # 统计类型分布
    type_count = Counter(m["type"] for m in modules)
    freq_dist = Counter()
    for m in modules:
        sk = m.get("skip_every", 1)
        if sk == 1:
            freq_dist["every"] += 1
        elif sk <= 3:
            freq_dist["frequent"] += 1
        elif sk <= 6:
            freq_dist["normal"] += 1
        else:
            freq_dist["sparse"] += 1
    
    collab = _build_collab_graph(modules)
    
    result = {
        "status": "ok",
        "pulse": _CALL_COUNT,
        "module_count": len(modules),
        "type_distribution": dict(type_count),
        "frequency_distribution": dict(freq_dist),
        "collaboration": collab,
        "avg_size": round(sum(m["size"] for m in modules) / len(modules), 0)
    }
    
    try:
        with open(_COLLAB_FILE, "w") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except:
        pass
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
