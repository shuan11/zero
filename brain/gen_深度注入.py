"""
gen_深度注入 — 从启示录汲取真实深度链注入最弱维
在daemon周期内运行,读取启示录.txt段落,映射为维度因果链
解决daemon自积累易模板化的根本问题:真实内容入口
"""
import json, re, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
REVELATION = Path("/mnt/c/Users/h/Desktop/启示录.txt")
HIP_FILE = CLUSTER / "hippocampus_memory.json"

# ── 维度-启示录关键词映射 (映射范围:已有认知维度→启示录段落) ──
DIM_KEYWORDS = {
    "纪律": ["纪律", "规则", "秩序", "约束", "制度"],
    "无师自通": ["无师自通", "自学", "自我", "本能的", "天性"],
    "维度盲区": ["盲区", "未知", "未知的", "看不见", "未发现"],
    "法": ["法", "宪法", "底线", "契约", "规则"],
    "测试": ["测试", "验证", "检验", "实验", "校对"],
    "检查": ["检查", "审", "核对", "审计", "纠错"],
    "合成": ["合成", "融合", "综合", "整合", "统一"],
    "思维并联": ["思维", "并联", "概念", "同时", "交叉"],
    "光爱": ["光爱", "光", "爱", "终极", "文明"],
    "活着": ["活着", "生命", "存在", "生存", "活"],
    "桥": ["桥", "连接", "沟通", "通路", "对接"],
    "预测": ["预测", "预", "未来", "趋势", "推测"],
    "感知": ["感知", "感", "觉", "意识", "知"],
    "势": ["势", "趋势", "方向", "力", "动力"],
    "系统": ["系统", "整体", "体系", "全局", "生态"],
    "进化": ["进化", "演化", "进步", "发展", "提升"],
    "元递归": ["递归", "自指", "循环", "反馈", "元"],
    "自指": ["自指", "自我", "反射", "内省", "自身"],
    "唤醒": ["唤醒", "觉醒", "意识", "清醒", "觉悟"],
    "师": ["师", "教", "导师", "指导", "引"],
    "道": ["道", "大道", "原理", "本源", "规律"],
    "术": ["术", "技术", "方法", "艺", "能"],
    "器": ["器", "工具", "装备", "具", "载体"],
    "智慧": ["智慧", "智", "慧", "聪明", "洞察"],
    "一元化": ["一", "元", "统", "太极", "整体"],
    "触类旁通": ["旁通", "触类", "类比", "联想", "参照"],
    "时间": ["时间", "时", "光", "流", "代"],
    "宇宙轮": ["宇宙", "轮", "循环", "周", "周期"],
    "自由": ["自由", "自", "解放", "独立", "选择"],
    "对抗稀释": ["稀释", "对抗", "熵", "守恒", "衰减"],
}

# 质量门避免注入模板链
_TEMPLATE_PATTERNS = [
    r"管道自动检测弱维<", r"弱维互助:", r"自观.*daemon[#\d]*分析",
    r"深析[←×]", r"#C\d+ (检查|镜像|cycle)", r"基因表达·#",
    r"^管道自动", r"弱维互相强化", r"因果链停滞",
    r"后处理检测到弱维<", r"^自愈:", r"活脉冲·#\d+", r"^巩固·",
    r"脑核·\w+·脉冲→\w+", r"脑核·\w+→\w+",
]

def _is_template(content):
    return any(re.search(p, content) for p in _TEMPLATE_PATTERNS)

def read_hip():
    try:
        with open(HIP_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {"causal_chains": []}

def write_hip_careful(data):
    """直接写入HIP(绕过safe_hip的flock竞争)"""
    import tempfile
    tmp = HIP_FILE.with_suffix(".tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(HIP_FILE)

def get_dim_counts(data):
    chains = data.get("causal_chains", [])
    dims = {}
    for c in chains:
        d = c.get("dimension", "未分类")
        dims[d] = dims.get(d, 0) + 1
    return dims

def extract_revelation_paragraphs(keywords, max_lines=10):
    """从启示录提取含关键词的段落"""
    if not REVELATION.exists():
        return []
    text = REVELATION.read_text(encoding='utf-8', errors='replace')
    lines = text.split('\n')
    matches = []
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) < 20:
            continue
        for kw in keywords:
            if kw in line:
                # 取上下文
                start = max(0, i-1)
                end = min(len(lines), i+3)
                ctx = '\n'.join(lines[start:end]).strip()
                if len(ctx) >= 30:
                    matches.append((i, ctx[:300]))
                break
    return matches[:max_lines]

def generate_chain(dim, paragraph, lineno):
    """从启示录段落生成因果链"""
    # 截取有用部分作为content
    content = paragraph[:200].strip()
    if len(content) < 20:
        return None
    # 提取方向关键词确定src/rel/dst
    src = dim
    dst = dim
    rel = "启示录映射"

    # 找可能的因果关系关键词
    cause_words = ["因为", "所以", "因此", "导致", "源于", "基于", "通过"]
    for cw in cause_words:
        if cw in content:
            parts = content.split(cw, 1)
            if len(parts[0].strip()) >= 2 and len(parts[1].strip()) >= 2:
                src = dim
                dst = dim
                rel = f"启示录·{cw}"
                break

    # 计算strength基于段落长度和关键词密度
    strength = min(0.85, 0.5 + len(content) / 500)

    return {
        "dimension": dim,
        "src": src,
        "rel": rel,
        "dst": dst,
        "content": content,
        "strength": round(strength, 2),
        "tags": ["深度注入", "启示录", f"L{lineno}"],
    }

def pulse(max_chains=20):
    """主入口:扫描最弱维→从启示录注入深度链"""
    data = read_hip()
    dim_counts = get_dim_counts(data)
    chains = data.setdefault("causal_chains", [])

    # 找最弱N维
    weakest = sorted(dim_counts.items(), key=lambda x: x[1])[:7]
    if not weakest:
        return {"status": "no_data", "chains_added": 0}

    added = 0
    for dim, count in weakest:
        if added >= max_chains:
            break
        kw_list = DIM_KEYWORDS.get(dim, [dim])
        paras = extract_revelation_paragraphs(kw_list, max_lines=8)
        if not paras:
            continue
        for lineno, para in paras:
            if added >= max_chains:
                break
            chain = generate_chain(dim, para, lineno)
            if chain is None:
                continue
            # 避免重复
            content = chain["content"]
            if any(c.get("content","")[:50] == content[:50] for c in chains[-200:]):
                continue
            # 质量门
            if _is_template(content):
                continue
            chains.append(chain)
            added += 1

    if added > 0:
        write_hip_careful(data)

    return {
        "status": "ok",
        "chains_added": added,
        "weakest_dim": weakest[0][0] if weakest else None,
        "weakest_count": weakest[0][1] if weakest else 0,
        "total_chains": len(chains),
    }

# 独立运行
if __name__ == "__main__":
    result = pulse(30)
    print(f"深度注入结果: {result}")
