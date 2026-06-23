"""brain/gen_时间_全维映射.py — 时间维快速自举·全维映射
从所有7000+现有链中提取含时间语义的内容，批量映射到时间维度。
非模板生成，避免safe_hip前50字符去重导致注入无效。

运行机制: pulse()每120秒被loader调用，从现有链中筛选带时间语义者注入。
注册为action: 时间自举
"""

import re, time
from brain.share import read_hip, write_chain

REGISTERED = True
ACTION_REGISTER = {"action": "时间自举", "type": "bootstrap", "priority": 80}
LAST_PULSE_KEY = "_time_bootstrap_pulse"

# 时间语义关键词 — 中英文混合
TIME_KEYWORDS = [
    "时间", "时间", "时序", "时刻", "持续", "演化", "历史", "过去", "未来",
    "变化", "过程", "先后", "顺序", "周期", "循环", "阶段", "阶段",
    "长期", "短期", "同时", "同步", "异步", "递归", "积累",
    "从.*到", "之前", "之后", "期间", "跨度", "漫长", "瞬间",
    "年", "月", "日", "时", "分", "秒", "纪元", "时代",
    "time", "temporal", "sequence", "duration", "evolution", "history",
    "rate", "speed", "frequency", "moment", "timeline", "chrono",
    "increment", "accumulate", "process", "transition", "phase",
    "等待", "持续", "同步", "异步", "老化", "生长", "衰变",
    "渐进", "突然", "临界", "阈值", "老化", "轮回",
    "生", "活", "死", "灭", "起", "落", "涨", "退",
]

TIME_PATTERN = re.compile(
    "|".join(f"({kw})" for kw in TIME_KEYWORDS),
    re.IGNORECASE
)


def _has_time_semantic(content: str) -> bool:
    """检测内容是否含时间语义"""
    if not content:
        return False
    return bool(TIME_PATTERN.search(content))


def pulse() -> str:
    """Loader入口：每2分钟执行一次"""
    
    now = time.time()
    last = getattr(pulse, LAST_PULSE_KEY, 0)
    if now - last < 120:  # 每2分钟
        return "时间全维映射: 冷却中"
    setattr(pulse, LAST_PULSE_KEY, now)
    
    # 读取当前海马体
    hip = read_hip()
    all_chains = hip.get("causal_chains", [])
    if not all_chains:
        return "时间全维映射: 无源链"
    
    # 已有时间维链的content前缀(去重用)
    existing_time = [c.get("content","")[:50] for c in all_chains 
                     if c.get("dimension") == "时间"]
    
    injected = 0
    skipped_existing = 0
    skipped_no_time = 0
    src_dims = {}
    
    for c in all_chains:
        content = c.get("content", "")
        if not content or len(content) < 10:
            continue
        
        # 跳过非时间语义链
        if not _has_time_semantic(content):
            skipped_no_time += 1
            continue
        
        # 跳过已有内容前缀(去重)
        if content[:50] in existing_time:
            skipped_existing += 1
            continue
        
        # 创建时间维映射链
        src_dim = c.get("dimension", "未分类")
        src_dims[src_dim] = src_dims.get(src_dim, 0) + 1
        
        time_chain = {
            "content": f"[时间自举·源自{src_dim}] {content}",
            "src": src_dim,
            "rel": "时间映射",
            "dst": "时间",
            "dimension": "时间",
            "strength": min(0.85, c.get("strength", 0.5) + 0.1),
            "tags": ["时间自举", f"源:{src_dim}"],
        }
        
        ok = write_chain(time_chain)
        if ok:
            injected += 1
            existing_time.append(content[:50])  # 更新去重缓存
    
    # 汇总
    src_summary = ", ".join(f"{d}({n})" for d, n in 
                           sorted(src_dims.items(), key=lambda x: -x[1])[:5])
    
    return f"时间全维映射: 注入{injected}链(跳过{skipped_existing}重复/{skipped_no_time}无时间语义), 来源维: {src_summary}"


# 由loader的pulse()调用，不在加载时自动执行
