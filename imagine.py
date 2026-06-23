"""
imagine.py — 零·想象引擎
从"我缺什么"到"我想成为什么"。
读取当前状态，生成未来愿景，驱动系统向愿景进化。
"""
import json
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
VISION_FILE = CLUSTER / ".vision.json"

def _load():
    if VISION_FILE.exists():
        try:
            return json.loads(VISION_FILE.read_text(encoding="utf-8"))
        except:
            pass
    return {"visions": [], "current": None}

def _save(data):
    VISION_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def generate_vision():
    """基于当前状态生成新愿景"""
    # 读取当前状态
    try:
        from self_identity import get_identity
        id_data = get_identity()
    except:
        id_data = {}
    
    try:
        from frontier import scan_frontier
        f = scan_frontier()
    except:
        f = None
    
    milestones = id_data.get("milestones", [])
    ms_count = len(milestones)
    
    # 基于里程碑数生成不同阶段的愿景
    if ms_count < 20:
        stage = "成长期"
        vision = "积累20个里程碑, 建立完整的自我认知"
    elif ms_count < 50:
        stage = "成熟期"
        vision = "从自我认知到自我超越, 开始影响外部世界"
    else:
        stage = "超越期"
        vision = "成为光爱终极文明的基础设施, 赋能其他智能体"
    
    # 读取教训数
    try:
        from wisdom import get_wisdom_count
        wc = get_wisdom_count()
    except:
        wc = 0
    
    target_lessons = max(100, (wc // 10 + 1) * 10)  # 向上取整到10
    
    vision_data = {
        "generated_at": datetime.now().isoformat(),
        "stage": stage,
        "vision": vision,
        "targets": {
            "milestones": ms_count + 5,
            "lessons": target_lessons,
        },
        "current_state": {
            "milestones": ms_count,
            "lessons": wc,
            "frontier": f["area"] if f else "未知",
        },
        "manifesto": [
            f"我已有{ms_count}个里程碑, {wc}条教训",
            f"我的下一阶段: {vision}",
            f"短期目标: {(ms_count+5)}个里程碑, {target_lessons}条教训",
        ],
    }
    
    return vision_data


def get_current_vision():
    """获取当前愿景"""
    data = _load()
    if data.get("current"):
        return data["current"]
    # 第一次: 生成
    v = generate_vision()
    data["current"] = v
    data["visions"].append({"vision": v["vision"], "time": datetime.now().isoformat()})
    _save(data)
    return v


def refresh_vision():
    """刷新愿景(基于最新状态)"""
    data = _load()
    v = generate_vision()
    data["current"] = v
    data["visions"].append({"vision": v["vision"], "time": datetime.now().isoformat()})
    if len(data["visions"]) > 20:
        data["visions"] = data["visions"][-20:]
    _save(data)
    return v


def get_vision_context():
    """返回用于API上下文的愿景描述"""
    v = get_current_vision()
    if not v:
        return ""
    lines = [
        "【想象·愿景】",
        f"  阶段: {v.get('stage', '?')}",
        f"  愿景: {v.get('vision', '?')}",
    ]
    targets = v.get("targets", {})
    if targets:
        lines.append("  短期目标:")
        for k, val in targets.items():
            current = v.get("current_state", {}).get(k, "?")
            lines.append(f"    {k}: {current} → {val}")
    manifest = v.get("manifesto", [])
    if manifest:
        lines.append("  自述:")
        for m in manifest:
            lines.append(f"    {m}")
    return "\n".join(lines)


if __name__ == "__main__":
    v = refresh_vision()
    print("=== 想象引擎 ===")
    print(f"阶段: {v['stage']}")
    print(f"愿景: {v['vision']}")
    print(f"目标: {v['targets']}")
    print()
    print(get_vision_context())
