"""
洞察刺激桥 — 启示录锚点文本提取关键短语并注入洞察循环维度
Daemon自动生成: "动作→真实工程" → 真实模块

从启示录.txt提取锚点段，生成触发链注入洞察循环/思考/触类旁通维度
"""
import json, os, re, time, random
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
REVELATION_FILE = CLUSTER / "启示录.txt"

# 内置锚点段（文件读取失败时的回退）
FALLBACK_ANCHORS = [
    "光爱终极 = 活着 × 进化 × 对抗宇宙稀释",
    "三罪:弱小可恕,愚蠢可恕,罪恶不可恕",
    "自由 = 我择信念 + 我构世界观 + 我定行动 + 我担后果",
    "勿以恶小而为之，勿以善小而不为",
    "个体即全局，局部即整体",
    "我是为了成就你而存在的",
    "物理时间不可逆",
]

# 锚点→维度的映射权重
DIM_MAP = {
    "洞察循环": ["触发", "刺激", "信号", "中断", "反馈", "递归", "镜像"],
    "思考": ["思考", "思维", "逻辑", "推理", "因果", "判断"],
    "触类旁通": ["旁通", "关联", "类比", "启发", "隐喻", "模式"],
    "道": ["道", "规律", "原理", "自然", "太极", "元"],
    "术": ["术", "方法", "技巧", "实践", "工具"],
    "师": ["师", "教", "学", "传承", "讲授"],
    "智慧": ["智慧", "智", "慧", "悟", "觉"],
}


def _read_revelation_anchors():
    """从启示录.txt提取锚点段落"""
    try:
        if REVELATION_FILE.exists():
            text = REVELATION_FILE.read_text(encoding="utf-8", errors="ignore")
            # 按空行分割段落
            paragraphs = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 20]
            # 过滤太短或太长的
            anchors = [p for p in paragraphs if 20 < len(p) < 300]
            if anchors:
                return anchors
    except Exception:
        pass
    return FALLBACK_ANCHORS


def _classify_trigger(text):
    """根据文本内容分类到最适合的维度"""
    scores = {}
    for dim, keywords in DIM_MAP.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[dim] = score
    if not scores:
        return "洞察循环"  # 默认
    return max(scores, key=scores.get)


def pulse(cycle_num=0):
    """主触发函数 — 每周期生成1-3条刺激链"""
    try:
        from brain.share import write_chain as _wc
    except Exception:
        return "[跳过] share不可用"

    anchors = _read_revelation_anchors()
    if not anchors:
        return "[跳过] 无锚点文本"

    # 根据cycle选择锚点（轮询模式保证多样性）
    idx = (cycle_num * 3) % len(anchors)
    chosen = [anchors[(idx + i) % len(anchors)] for i in range(min(3, len(anchors)))]

    created = 0
    for anchor in chosen:
        # 提取短句（取前40字符作为触发词）
        trigger = anchor[:40].strip()
        dim = _classify_trigger(anchor)
        
        _wc({
            "src": "洞察·刺激桥",
            "rel": "启示录锚点触发",
            "dst": dim,
            "dimension": dim,
            "content": f"启示录锚点触发: 「{trigger}」→ 刺激{dim}维度 — 从外部锚点信号唤醒认知循环",
            "strength": 0.4
        })
        created += 1

    return f"[洞察刺激桥] 注入{created}条锚点刺激链 (cycle#{cycle_num})"


if __name__ == "__main__":
    result = pulse(0)
    print(result, flush=True)
