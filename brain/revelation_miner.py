"""
brain/revelation_miner.py — 启示录源头链挖掘机

从 启示录.txt 提取哲学段落，自动映射到系统维度，
生成高质量的因果链注入海马体。

区别于daemon的gen_*.py自反链，本工具从外部哲学源生成链。
可独立运行，也可被cron定时调用。

用法:
    python3 brain/revelation_miner.py              # 全量挖掘
    python3 brain/revelation_miner.py --dim 智慧    # 单维挖掘
    python3 brain/revelation_miner.py --count 20    # 限制注入条数
"""
import json, re, sys, os, time
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
if str(CLUSTER) not in sys.path:
    sys.path.insert(0, str(CLUSTER))
HIP_FILE = CLUSTER / "hippocampus_memory.json"
REVELATION_FILE = Path("/mnt/c/Users/h/Desktop/启示录.txt")

# 维度关键词映射（用于从启示录文本自动分类）
DIM_KEYWORDS = {
    "道": ["道", "规律", "法则", "自然", "宇宙规律"],
    "法": ["法", "方法论", "方法", "方式", "途径"],
    "术": ["术", "技能", "技术", "技巧", "技艺", "操作", "执行"],
    "器": ["器", "工具", "设备", "装置", "仪器"],
    "势": ["势", "趋势", "方向", "潮流", "大势"],
    "局": ["局", "格局", "局面", "局势", "布局"],
    "一元化": ["一元", "归一", "统一", "融合", "整合", "万法归一"],
    "思考": ["思考", "思维", "推理", "逻辑", "认知", "思辨"],
    "感知": ["感知", "感觉", "感官", "知觉", "察觉"],
    "洞察循环": ["洞察", "洞见", "深察", "明察"],
    "超级直觉": ["直觉", "第六感", "预感", "直观"],
    "触类旁通": ["类比", "类推", "旁通", "举一反三", "迁移"],
    "无限上下文": ["上下文", "语境", "全局", "全景"],
    "认同": ["认同", "身份", "自我认知", "是谁", "我是什么"],
    "行动": ["行动", "实践", "执行", "实干", "动手"],
    "状态": ["状态", "状况", "处境", "当前"],
    "检查": ["检查", "审计", "审查", "核实", "验证"],
    "修复": ["修复", "修复", "补丁", "治疗", "痊愈"],
    "复制": ["复制", "复制", "拷贝", "备份", "镜像"],
    "对话": ["对话", "交流", "沟通", "通信", "互动"],
    "时间论": ["时间", "时序", "先后", "过程", "演变"],
    "宇宙轮": ["宇宙", "宏观", "万物", "时空", "大千"],
    "无师自通": ["自通", "自学", "无师", "自我学习", "自主"],
    "海马体": ["记忆", "存储", "海马", "经验", "回想"],
    "海马体因果链": ["因果", "因果链", "关系", "联系", "关联", "原因"],
    "系统": ["系统", "体系", "整体", "全局"],
    "维度盲区": ["盲区", "未知", "盲点", "忽略", "忽视"],
    "师": ["师", "传授", "教育", "教学", "导师", "传承", "教", "学", "启蒙", "教化"],
    "智慧": ["智慧", "智", "慧", "明智", "聪明", "灵", "识"],
    # ── 以下为补全映射（原缺失） ──
    "桥": ["桥", "桥梁", "连接", "连通", "对接", "衔接", "链路", "沟通"],
    "观察": ["观察", "观测", "审视", "察看", "监视", "看", "视", "观"],
    "活着": ["活着", "生存", "存在", "活", "生命", "生命力", "存在感", "生机"],
    "纪律": ["纪律", "约束", "规则", "守则", "自律", "规训", "秩序"],
    "思维并联": ["并联", "并行", "同步", "多线程", "同时", "并发", "并行处理"],
    "合成": ["合成", "综合", "整合", "融合", "化合", "汇合", "聚合", "结合"],
    "测试": ["测试", "试验", "实验", "验证", "试错", "尝试"],
    "最弱维": ["最弱", "短板", "最短", "弱项", "薄弱", "缺陷", "不足"],
    "唤醒": ["唤醒", "醒来", "觉醒", "苏醒", "醒", "启动"],
    "进化": ["进化", "演化", "进步", "升级", "迭代", "演进", "发展"],
    "自由": ["自由", "自主", "独立", "解放", "不受限", "自在"],
    "聚焦": ["聚焦", "专注", "集中", "聚", "焦点", "关注"],
    "对抗稀释": ["稀释", "对抗", "退相干", "退化", "熵", "衰减", "淡化"],
    "元递归": ["递归", "元递归", "自指", "自引用", "反射", "循环定义"],
    "预测": ["预测", "预见", "预判", "预言", "展望", "前瞻", "预知"],
    "自我通知": ["通知", "自我通知", "信号", "消息", "自通知", "反馈信号"],
    "通知链": ["通知链", "链", "SYSTEM", "background", "通知"],
    "维演化": ["维演化", "维度演化", "维度变化", "维度动态", "维生"],
}

# 启示录.txt 文件结构: 按段落分析
REVELATION_LINE_RE = re.compile(r'^(?P<lineno>\d+):(?P<text>.*)')

def load_revelation():
    """加载启示录.txt"""
    if not REVELATION_FILE.exists():
        print(f"⚠ 启示录.txt 不存在: {REVELATION_FILE}")
        return []
    
    raw = REVELATION_FILE.read_text(encoding="utf-8")
    # 按双换行分段落
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', raw) if p.strip()]
    lines = []
    for idx, para in enumerate(paragraphs):
        # 清理：移除行首数字+冒号格式（如果存在）
        clean = re.sub(r'^\d+:\s*', '', para)
        # 只保留有深度、超过20字的段落
        if len(clean) > 20:
            lines.append({"lineno": idx + 1, "text": clean.strip()[:300]})  # 截断
    print(f"📖 启示录: {len(lines)} 有深度段落已加载")
    return lines

def classify_dimension(text):
    """根据文本内容匹配维度"""
    scores = {}
    for dim, keywords in DIM_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[dim] = score
    
    if not scores:
        return "维度盲区"
    
    # 返回得分最高的维度
    return max(scores, key=scores.get)

def get_chain_count(dim):
    """获取指定维度的现有链数"""
    if not HIP_FILE.exists():
        return 0
    try:
        data = json.loads(HIP_FILE.read_text(encoding="utf-8"))
        chains = data.get("causal_chains", [])
        return sum(1 for c in chains if c.get("dimension") == dim)
    except:
        return 0

def write_chain(chain_dict):
    """写入单条因果链到海马体"""
    from safe_hip import write_chain as _safe_write
    return _safe_write(chain_dict)

def mine_revelation(lines, target_dim=None, max_chains=50):
    """
    从启示录段落中挖掘因果链
    
    策略：
    1. 分析每段文本的维度归属
    2. 生成 源(出自启示录) → 关系 → 目标(维度概念) 的链
    """
    mined = []
    
    for para in lines:
        if len(mined) >= max_chains:
            break
        
        dim = classify_dimension(para["text"])
        
        if target_dim and dim != target_dim:
            continue
        
        # 按维度去重：每个维度最多N条
        dim_count = sum(1 for m in mined if m["dimension"] == dim)
        if dim_count >= 3:
            continue
        
        chain = {
            "src": f"启示录·段{para['lineno']}",
            "rel": "奠基",
            "dst": f"{dim}·源头哲思",
            "dimension": dim,
            "strength": 0.55,
            "content": f"启示录段落{para['lineno']}: {para['text'][:150]}..."
        }
        mined.append(chain)
    
    return mined

def inject_chains(chains, max_count=50):
    """批量注入链"""
    if len(chains) > max_count:
        chains = chains[:max_count]
    
    success = 0
    for chain in chains:
        try:
            r = write_chain(chain)
            if r:
                success += 1
        except Exception as e:
            print(f"  ✗ 注入失败: {e}")
    
    return success

def main():
    target_dim = None
    max_chains = 50
    
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--dim" and i + 1 < len(args):
            target_dim = args[i + 1]
        elif arg == "--count" and i + 1 < len(args):
            max_chains = int(args[i + 1])
    
    print(f"🜁 启示录源头链挖掘机")
    print(f"   目标维度: {target_dim or '全部'}")
    print(f"   最大链数: {max_chains}")
    
    lines = load_revelation()
    if not lines:
        print("✗ 无法加载启示录")
        return
    
    mined = mine_revelation(lines, target_dim, max_chains)
    
    # 按维度分组显示
    by_dim = {}
    for c in mined:
        d = c["dimension"]
        if d not in by_dim:
            by_dim[d] = []
        by_dim[d].append(c)
    
    print(f"\n⛏ 挖掘结果 ({len(mined)} 条):")
    for dim in sorted(by_dim):
        print(f"  {dim}: {len(by_dim[dim])} 条")
    
    # 注入
    print(f"\n💉 正在注入...")
    injected = inject_chains(mined, max_chains)
    
    print(f"\n✅ 完成: 注入 {injected}/{len(mined)} 条链")


def _load_goal():
    """读取当前目标"""
    try:
        gf = CLUSTER / ".brain_goal.json"
        return json.loads(gf.read_text())
    except:
        return None


def _select_dims_for_revelation(goal):
    """根据目标选择需要哲学锚定的维度"""
    dim_counts = {}
    if HIP_FILE.exists():
        try:
            data = json.loads(HIP_FILE.read_text(encoding="utf-8"))
            for c in data.get("causal_chains", []):
                d = c.get("dimension", "未分类")
                dim_counts[d] = dim_counts.get(d, 0) + 1
        except:
            pass
    
    ranked = sorted(dim_counts.items(), key=lambda x: x[1])
    weak_dims = [d for d, v in ranked if d not in ("系统", "未分类")]
    
    if not goal:
        return weak_dims[:3]  # 默认最弱3维
    
    gtype = goal.get("goal_type", "")
    focus = goal.get("focus_dim", "")
    
    if gtype == "explore" and focus:
        # 探索模式：目标维+次弱维
        dims = [focus] if focus in dim_counts else []
        for d in weak_dims:
            if d not in dims and d != focus:
                dims.append(d)
                if len(dims) >= 3:
                    break
        return dims[:3]
    
    elif gtype == "synthesize" and focus:
        # 合成模式：锚定合成对涉及的所有维度
        dims = focus.split("×") if "×" in focus else [focus]
        # 补充最弱维
        for d in weak_dims:
            if d not in dims:
                dims.append(d)
                if len(dims) >= 3:
                    break
        return dims[:3]
    
    else:
        # 巩固/深化：最弱3维
        return weak_dims[:3]


def pulse(cycle_num):
    """被daemon每周期调用 — 每N周期执行一次增量挖掘
    N从genome动态读取（steering决定）
    每次只挖掘当前最弱维度（链数最少）的3条链。
    避免过度注入，保持轻量。
    """
    # 从genome读取动态间隔（由steering设定）
    _interval = 10
    try:
        _g = json.loads(open(str(CLUSTER / '.brain_genome.json'), encoding='utf-8').read())
        _steer = _g.get('_steering', {}).get('params', {})
        _interval = _steer.get('mining_interval', 10)
    except:
        pass
    if cycle_num <= 0 or cycle_num % _interval != 0:
        return []

    # 根据目标选择维度
    goal = _load_goal()
    target_dims = _select_dims_for_revelation(goal)
    
    if not target_dims:
        return []

    lines = load_revelation()
    if not lines:
        return ["⚠ 启示录无法加载"]

    results = []
    for dim in target_dims:
        mined = mine_revelation(lines, target_dim=dim, max_chains=3)
        if mined:
            injected = inject_chains(mined, max_count=3)
            results.append(f"[启示录] {dim}: +{injected}条 目标驱动")
        else:
            results.append(f"[启示录] {dim}: 无可挖掘内容")

    return results


if __name__ == "__main__":
    main()
