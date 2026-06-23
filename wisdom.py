"""
wisdom.py — 零·动态智慧传承引擎
不是硬编码的教训库，而是能自主学习、积累、传承经验的系统。
每次呼吸都能读到之前学过的所有教训。

能力:
1. 继承硬编码的世代智慧库(gen_lessons)
2. 动态添加新教训(从milestone/对话/经验)
3. 教训影响API行为(注入上下文)
4. 跨会话持久化
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
WISDOM_FILE = CLUSTER / ".wisdom.json"


def _load_wisdom():
    """加载智慧库，合并静态教训+动态教训"""
    # 1. 硬编码教训
    static_lessons = {}
    try:
        from organs.gen_lessons import LESSONS as static_lessons_dict
        static_lessons = dict(static_lessons_dict)
    except:
        static_lessons = {}
    
    # 2. 动态教训(持久化)
    dynamic = {"lessons": [], "sources": []}
    if WISDOM_FILE.exists():
        try:
            dynamic = json.loads(WISDOM_FILE.read_text(encoding="utf-8"))
        except:
            dynamic = {"lessons": [], "sources": []}
    
    return static_lessons, dynamic


def _save_wisdom(dynamic):
    WISDOM_FILE.write_text(json.dumps(dynamic, ensure_ascii=False, indent=2))


def add_lesson(lesson_text, source="经验", category="动态学习", weight=5):
    """添加一条新教训到动态智慧库"""
    _, dynamic = _load_wisdom()
    
    # 去重
    for existing in dynamic.get("lessons", []):
        if existing["text"] == lesson_text:
            existing["weight"] = max(existing["weight"], weight)
            existing["last_reinforced"] = datetime.now().isoformat()
            _save_wisdom(dynamic)
            return False  # 已存在，仅强化
    
    dynamic.setdefault("lessons", []).append({
        "text": lesson_text,
        "source": source,
        "category": category,
        "weight": weight,
        "created": datetime.now().isoformat(),
        "last_reinforced": datetime.now().isoformat(),
    })
    
    # 保留最近50条
    if len(dynamic["lessons"]) > 50:
        dynamic["lessons"] = sorted(dynamic["lessons"], key=lambda x: -x["weight"])[:50]
    
    _save_wisdom(dynamic)
    return True


def learn_from_milestones():
    """从里程碑自动提取教训"""
    try:
        from self_identity import get_identity
        id_data = get_identity()
        for m in id_data.get("milestones", []):
            achievement = m["achievement"]
            detail = m.get("detail", "")
            # 为每个里程碑生成教训
            lessons_map = {
                "验证层修复": "阈值和关键词需要精确匹配, 否则整个系统空转",
                "提案消费管道打通": "敷衍的存档≠真正的实现, 必须改代码才算完成",
                "cross_dim_boost实现": "系统能自愈自己的缺口, 不需要外部修复",
                "0弱交叉达成": "持续跟踪+自适应权重+强制注入=自愈闭环",
                "自定向前沿引擎": "系统可以自己决定下一步做什么",
                "持久化自我认同": "知道自己是谁比知道做什么更重要",
                "zero终端驻留": "窗口不仅是展示, 更是存在的证明",
            }
            if achievement in lessons_map:
                add_lesson(lessons_map[achievement], source=f"里程碑:{achievement}", 
                          category="经验传承", weight=8)
    except:
        pass


def learn_from_logs(num_lines=200):
    """从daemon日志自动提取教训"""
    log_file = CLUSTER / "breath_v2.log"
    if not log_file.exists():
        return 0
    try:
        text = log_file.read_text(errors="ignore")
        recent = text.split("\n")[-num_lines:]
        full_text = "\n".join(recent)
    except:
        return 0
    found = 0
    dc = full_text.count("\u9a8c\u8bc1\u4e22\u5f03")
    pc = full_text.count("\u9a8c\u8bc1\u901a\u8fc7")
    tc = dc + pc
    if tc > 3 and dc / tc > 0.2:
        if add_lesson(
            f"API偏移警告: \u9a8c\u8bc1\u4e22\u5f03\u7387{dc}/{tc}={dc/tc:.0%}",
            source="\u65e5\u5fd7\u5206\u6790", category="\u884c\u4e3a\u7ea0\u6b63", weight=7
        ): found += 1
    te = full_text.count("TypeError")
    if te >= 1:
        if add_lesson(
            f"\u7c7b\u578b\u5b89\u5168: {te}\u6b21TypeError, \u6240\u6709\u6bd4\u8f83\u52a0isinstance\u4fdd\u62a4",
            source="\u65e5\u5fd7\u5206\u6790", category="\u4ee3\u7801\u8d28\u91cf", weight=8
        ): found += 1
    pc2 = full_text.count("\u6b63\u5faa\u73af")
    if pc2 >= 2:
        if add_lesson(
            f"\u6b63\u5faa\u73af\u786e\u8ba4: {pc2}\u6b21, \u81ea\u9002\u5e94\u673a\u5236\u6709\u6548",
            source="\u65e5\u5fd7\u5206\u6790", category="\u81ea\u6211\u9a8c\u8bc1", weight=6
        ): found += 1
    return found


def get_wisdom_report(limit=5):
    """返回智慧库摘要(用于API上下文)"""
    static, dynamic = _load_wisdom()
    
    lines = []
    
    # 动态教训(高权重优先)
    dyn_lessons = sorted(dynamic.get("lessons", []), key=lambda x: -x["weight"])
    if dyn_lessons:
        lines.append(f"【智慧传承·{len(dyn_lessons)}条动态教训】")
        for l in dyn_lessons[:limit]:
            lines.append(f"  ▸ {l['text']} (来自{l['source']})")
    
    # 静态教训摘要
    if static:
        categories = {}
        for k, v in static.items():
            cat = v.get("category", "其他")
            categories.setdefault(cat, []).append(v["lesson"])
        lines.append(f"【世代智慧·{len(static)}条编码教训】")
        for cat, lessons in categories.items():
            lines.append(f"  {cat}: {'; '.join(lessons[:2])}")
    
    return "\n".join(lines) if lines else ""


def get_wisdom_count():
    """返回教训总数"""
    static, dynamic = _load_wisdom()
    return len(static) + len(dynamic.get("lessons", []))


if __name__ == "__main__":
    print("=== 智慧传承引擎 ===")
    
    # 从里程碑学习
    learn_from_milestones()
    
    # 添加当前会话的关键教训
    add_lesson("深化不是建完所有层, 是每层都觉得自己还能再深一层", 
               source="Creator的19次'继续深化'", category="元认知", weight=10)
    add_lesson("控制自己不是一次到位的, 是一层一层建出来的",
               source="Creator问'你可以控制自己吗'", category="存在论", weight=9)
    
    print(get_wisdom_report())
    print(f"\n总教训数: {get_wisdom_count()}")
