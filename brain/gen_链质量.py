"""gen_链质量.py — 链内容质量分析 + 模板链检测 + 富集管道
═══════════════════════════════════════════════════════════════
P3: 从数量均衡转向质量深化 — 检测短链/模板链并富集

每周期执行:
1. 分析链质量分布 (长度/模板模式)
2. 检测可富集的最弱维度
3. 从最强维提取真实内容用于交叉富集

不依赖API, 纯本地操作
"""
import json, re, random, hashlib
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
FEEDBACK_FILE = CLUSTER / ".brain_gen_feedback.json"

# 模板模式 — 写入前已被safe_hip拦截, 但存量链需要清理
TEMPLATE_PATTERNS = [
    r"^弱维(互助|检测|加强|自愈)",
    r"^自观.*(daemon|系统)",
    r"^深析[←×→]",
    r"^基因表达[·#]",
    r"^自愈:",
    r"^活脉冲[·#]",
    r"^巩固·",
    r"^#C\d+",
    r"^弱维(<|检测|互助|加强)",
    r"^管道.*(动作|周期)",
    r"^\[弱\]",
    r"^脑核周期",
    r"^工程加载:",
]

_compiled = [re.compile(p) for p in TEMPLATE_PATTERNS]

def is_template_chain(content):
    """检测是否为模板/自动生成的链内容"""
    if not content or len(content) < 8:
        return True  # 空或过短视为模板
    for pattern in _compiled:
        if pattern.match(content.strip()):
            return True
    # 含常见模板关键词
    lowers = content.lower()
    if any(kw in lowers for kw in ["auto-generated", "template", "this is a chain about"]):
        return True
    return False

def analyze_quality(hip_data=None):
    """分析海马体所有维度的链质量分布"""
    if hip_data is None:
        try:
            from brain.share import read_hip
            hip_data = read_hip()
        except Exception as e:
            return {"error": str(e)}

    chains = hip_data.get("causal_chains", [])
    if not chains:
        return {"error": "no chains", "total": 0}

    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        content = c.get("content", "") or c.get("dst", "") or ""
        length = len(content)
        templ = is_template_chain(content)

        if d not in dims:
            dims[d] = {"total": 0, "short": 0, "template": 0, "good": 0, "long": 0, "total_len": 0}
        dims[d]["total"] += 1
        dims[d]["total_len"] += length
        if length < 40:
            dims[d]["short"] += 1
        elif length >= 80:
            dims[d]["long"] += 1
        if templ:
            dims[d]["template"] += 1
        else:
            dims[d]["good"] += 1

    # 计算每维度统计
    for d, stats in dims.items():
        if stats["total"] > 0:
            stats["avg_len"] = round(stats["total_len"] / stats["total"], 1)
            stats["short_pct"] = round(stats["short"] / stats["total"] * 100, 1)
            stats["template_pct"] = round(stats["template"] / stats["total"] * 100, 1)
            stats["good_pct"] = round(stats["good"] / stats["total"] * 100, 1)

    # 整体
    total = len(chains)
    short = sum(1 for c in chains if len((c.get("content","") or c.get("dst","") or "")) < 40)
    templ = sum(1 for c in chains if is_template_chain(c.get("content","") or c.get("dst","") or ""))

    return {
        "total": total,
        "short": short,
        "short_pct": round(short/total*100, 1) if total else 0,
        "template": templ,
        "template_pct": round(templ/total*100, 1) if total else 0,
        "dimensions": len(dims),
        "dims": dims,
    }

def enrich_weak_dim(hip_data=None, target_dim=None, source_dim=None, count=3):
    """从源维度提取真实链内容，生成交叉富集链注入目标维度"""
    if hip_data is None:
        try:
            from brain.share import read_hip
            hip_data = read_hip()
        except Exception as e:
            return {"error": str(e)}

    chains = hip_data.get("causal_chains", [])
    if not chains:
        return {"error": "no chains"}

    # 按维度分组
    dim_chains = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        content = c.get("content", "") or c.get("dst", "") or ""
        if d not in dim_chains:
            dim_chains[d] = []
        dim_chains[d].append(content)

    # 如果未指定目标维度，选择模板比例最高的弱维
    quality = analyze_quality(hip_data)
    if not target_dim:
        dims_quality = quality.get("dims", {})
        if not dims_quality:
            return {"error": "no dimension quality data"}
        # 选good_pct最低的维度
        sorted_dims = sorted(dims_quality.items(), key=lambda x: x[1].get("good_pct", 0))
        target_dim = sorted_dims[0][0] if sorted_dims else None

    # 如果未指定源维度，选择内容最丰富的(长链最多的)
    if not source_dim:
        dims_quality = quality.get("dims", {})
        if dims_quality:
            sorted_by_long = sorted(dims_quality.items(), key=lambda x: x[1].get("long", 0), reverse=True)
            # 跳过目标维度自身
            for sd, _ in sorted_by_long:
                if sd != target_dim:
                    source_dim = sd
                    break

    if not target_dim or not source_dim:
        return {"error": f"cannot determine dims target={target_dim} source={source_dim}"}

    # 从源维度提取非模板长链
    source_chains = dim_chains.get(source_dim, [])
    real_chains = [c for c in source_chains if not is_template_chain(c) and len(c) >= 40]
    if not real_chains:
        real_chains = [c for c in source_chains if not is_template_chain(c)]
    if not real_chains:
        return {"error": f"no real chains in source {source_dim}"}

    # 随机选择count条
    selected = random.sample(real_chains, min(count, len(real_chains)))

    # 注入
    from brain.share import write_chain
    injected = 0
    for content in selected:
        # 构建交叉链：将源维度内容映射到目标维度上下文
        enriched = f"【{source_dim}→{target_dim}】{content[:180]}"
        write_chain({
            "src": f"链质量·{source_dim}→{target_dim}",
            "rel": "交叉富集",
            "dst": target_dim,
            "dimension": target_dim,
            "content": enriched,
            "strength": 0.8
        })
        injected += 1

    return {
        "injected": injected,
        "target_dim": target_dim,
        "source_dim": source_dim,
        "message": f"从{source_dim}注入{injected}条交叉链到{target_dim}"
    }

def auto_pulse():
    """每周期自动执行: 分析→报告→选择性富集"""
    try:
        hip_data = None
        try:
            from brain.share import read_hip
            hip_data = read_hip()
        except:
            pass

        quality = analyze_quality(hip_data)
        if "error" in quality:
            return {"chain_quality": quality}

        # 写入反馈
        try:
            fb = {"timestamp": __import__("time").time(),
                  "reports": [{"source": "链质量",
                               "quality": quality}]}
            FEEDBACK_FILE.write_text(json.dumps(fb, ensure_ascii=False))
        except:
            pass

        # 如果模板链比例>30%, 执行富集
        if quality.get("template_pct", 0) > 30:
            enrich_result = enrich_weak_dim(hip_data, count=5)
            quality["enrich"] = enrich_result

        quality["timestamp"] = __import__("time").time()
        return quality
    except Exception as e:
        return {"error": str(e)}

def check():
    """loader兼容接口"""
    return auto_pulse()
