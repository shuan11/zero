# gen_弱维启示录滋养_20260624.py
# 自动检测最弱3维 → 从启示录.txt提取匹配段落 → 注入高质链
# 与已有gen_*不同：注入的是真实语义内容（非模板/状态报告）
#
# 自动加载：daemon loader 检测到 gen_*.py 自动执行 pulse()
# 冷却机制：每30周期执行一次（避免重复注入）

import json, os, sys, time, re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))

REVELATION_PATH = Path("/mnt/c/Users/h/Desktop/启示录.txt")
COOLDOWN_CYCLES = 30  # 每30周期执行一次

# 维度→启示录关键词映射（用于从文本中提取相关段落）
DIM_REVELATION_MAP = {
    "光爱": ["光爱", "光", "爱", "终极", "永恒", "善良", "至善", "美好"],
    "无师自通": ["学习", "自通", "自学", "思维萌芽", "智慧", "认知", "觉", "悟"],
    "无限上下文": ["全局", "整体", "宏观", "宇宙", "全部", "所有", "无限", "时空"],
    "师": ["师", "教", "传", "授", "启蒙", "导师", "教育", "传承", "教化"],
    "维度盲区": ["未知", "盲区", "盲点", "忽略", "隐藏", "未发现", "虚无", "虚空"],
    "道": ["道", "规律", "法则", "自然", "宇宙规律", "大道"],
    "法": ["法", "方法论", "方式", "手段", "途径"],
    "器": ["器", "工具", "装置", "设备"],
    "势": ["势", "趋势", "方向", "大势", "潮流"],
    "自由": ["自由", "解放", "自主", "选择", "独立"],
    "活着": ["活着", "存在", "生存", "生命", "活"],
    "感知": ["感知", "感觉", "感官", "知觉", "察觉"],
    "思考": ["思考", "思维", "逻辑", "推理", "认知", "思辨"],
    "对抗稀释": ["对抗", "熵", "稀释", "虚无", "混乱", "秩序"],
    "唤醒": ["觉醒", "唤醒", "觉醒", "醒来", "意识"],
    "触类旁通": ["类比", "旁通", "举一反三", "迁移", "联系"],
    "洞察循环": ["洞察", "洞见", "深察"],
    "超级直觉": ["直觉", "预感", "直观"],
    "系统": ["系统", "体系", "整体", "全局", "组织"],
}

# 维度关联矩阵（交叉注入用）
DIM_CROSS_PAIRS = [
    ("光爱", "活着"), ("光爱", "对抗稀释"), ("光爱", "自由"),
    ("无师自通", "思考"), ("无师自通", "触类旁通"),
    ("无限上下文", "系统"), ("无限上下文", "感知"),
    ("师", "道"), ("师", "法"),
    ("维度盲区", "超级直觉"), ("维度盲区", "洞察循环"),
]

_pulse_count = 0

def _get_hip():
    """读取海马体"""
    try:
        from brain.share import read_hip
        return read_hip()
    except:
        fp = str(Path.home() / ".zero_brain" / "hippocampus_memory.json")
        if os.path.exists(fp):
            with open(fp) as f:
                return json.load(f)
        return {"causal_chains": [], "metadata": {}}

def _write_chain(chain):
    """通过safe_hip写入"""
    try:
        from brain.share import write_chain
        return write_chain(chain)
    except:
        try:
            from safe_hip import write_chain as swc
            return swc(chain)
        except:
            return False

def _load_revelation():
    """加载启示录文本"""
    if REVELATION_PATH.exists():
        with open(REVELATION_PATH, encoding='utf-8') as f:
            return f.readlines()
    return []

def _find_relevant_lines(lines, keywords, max_lines=5):
    """在启示录中找到包含关键词的段落行号"""
    matches = []
    for i, line in enumerate(lines):
        text = line.strip()
        if len(text) < 20:
            continue
        for kw in keywords:
            if kw in text:
                matches.append((i, text))
                break
    # 去重并返回最多max_lines个
    seen = set()
    unique = []
    for ln, txt in matches:
        if txt[:50] not in seen:
            seen.add(txt[:50])
            unique.append((ln, txt))
    return unique[:max_lines]

def _build_context(lines, line_no, context_lines=3):
    """获取段落上下文"""
    start = max(0, line_no - context_lines)
    end = min(len(lines), line_no + context_lines + 1)
    return " ".join(lines[i].strip() for i in range(start, end) if lines[i].strip())

def pulse():
    """daemon每周期调用 - 自动检测最弱维并注入启示录内容"""
    global _pulse_count
    _pulse_count += 1
    if _pulse_count % COOLDOWN_CYCLES != 1:
        return {"status": "cooldown", "cycle": _pulse_count}

    hip = _get_hip()
    chains = hip.get("causal_chains", [])
    if not chains:
        return {"status": "no_data"}

    # 计算维度分布
    dim_counts = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dim_counts[d] = dim_counts.get(d, 0) + 1

    # 找最弱3维
    sorted_dims = sorted(dim_counts.items(), key=lambda x: x[1])
    weakest_3 = [d for d, _ in sorted_dims[:3] if d in DIM_REVELATION_MAP]
    if not weakest_3:
        return {"status": "no_weak_dims_in_map"}

    # 找最强若干维（用于交叉注入）
    strongest_3 = [d for d, _ in sorted_dims[-3:]]

    # 加载启示录
    rev_lines = _load_revelation()
    if not rev_lines:
        return {"status": "no_revelation"}

    injected = 0
    for dim in weakest_3:
        keywords = DIM_REVELATION_MAP.get(dim, [dim])
        matches = _find_relevant_lines(rev_lines, keywords, max_lines=3)
        for ln, match in matches:
            context = _build_context(rev_lines, ln)
            chain = {
                "src": f"启示录·L{ln}",
                "rel": "滋养",
                "dst": f"{dim}·深层",
                "dimension": dim,
                "content": context[:200] if len(context) > 200 else context,
                "strength": 0.8
            }
            if _write_chain(chain):
                injected += 1

    # 交叉注入：弱维×强维
    for dim in weakest_3:
        for strong_dim in strongest_3:
            pair_key = (dim, strong_dim) if (dim, strong_dim) in DIM_CROSS_PAIRS else None
            pair_key_rev = (strong_dim, dim) if (strong_dim, dim) in DIM_CROSS_PAIRS else None
            if pair_key or pair_key_rev:
                # 交叉注入：强维内容映射到弱维
                keywords = DIM_REVELATION_MAP.get(strong_dim, [])
                matches = _find_relevant_lines(rev_lines, keywords, max_lines=1)
                for ln, match in matches:
                    context = _build_context(rev_lines, ln)
                    chain = {
                        "src": f"启示录·L{ln}",
                        "rel": f"交叉·{strong_dim}→{dim}",
                        "dst": f"{dim}·关联",
                        "dimension": dim,
                        "content": f"[{strong_dim}→{dim}] {context[:180]}",
                        "strength": 0.75
                    }
                    if _write_chain(chain):
                        injected += 1

    return {
        "status": "ok",
        "injected": injected,
        "target_dims": weakest_3,
        "cross_dims": strongest_3,
        "cycle": _pulse_count
    }

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
