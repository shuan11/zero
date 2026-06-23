"""focus_action_consumer.py — 焦点动作消费桥

读取.brain_focus.json中的action字段, 检测新动作, 自动生成对应模块。
闭环: daemon思考→动作→模块→验证→反馈。

每cycle检查: 有未消费动作? → 构建模块文件 → 注册到daemon → 标记已消费
"""

import json, os, subprocess, sys, time
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
FOCUS_FILE = CLUSTER / ".brain_focus.json"
CONSUMED_LOG = CLUSTER / ".brain_consumed_actions.json"

def load_consumed():
    if CONSUMED_LOG.exists():
        try:
            return json.loads(CONSUMED_LOG.read_text())
        except:
            return {"consumed": [], "modules": {}}
    return {"consumed": [], "modules": {}}

def save_consumed(data):
    CONSUMED_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2))

def check_and_consume():
    """主入口：读取焦点动作，检测新动作，消费它"""
    if not FOCUS_FILE.exists():
        return ["focus_action_consumer: 无焦点文件"]
    
    try:
        focus = json.loads(FOCUS_FILE.read_text())
    except:
        return ["focus_action_consumer: 无法解析焦点文件"]
    
    action = focus.get("action", "").strip()
    focus_name = focus.get("focus", "")
    cycle = focus.get("cycle", 0)
    
    if not action:
        return ["focus_action_consumer: 无动作"]
    
    consumed = load_consumed()
    
    # 用动作内容前50字作唯一指纹
    fingerprint = action[:50]
    if fingerprint in consumed["consumed"]:
        return [f"focus_action_consumer: 动作已消费({focus_name})"]
    
    # 验证是否已被手动实现（检查有对应模块文件）
    module_map = _detect_existing_modules(action, focus_name)
    if module_map:
        mark_consumed(fingerprint, module_map)
        return [f"focus_action_consumer: 检测到已有模块 {module_map}，标记已消费"]
    
    # 尝试自动生成模块
    module_name = _gen_module_from_action(action, focus_name)
    if module_name:
        mark_consumed(fingerprint, module_name)
        return [f"focus_action_consumer: 自动创建模块 {module_name} ✅"]
    
    return [f"focus_action_consumer: 无法消费动作({focus_name}) — 需手动创建"]

def mark_consumed(fp, module_name):
    consumed = load_consumed()
    consumed["consumed"].append(fp)
    consumed["modules"][fp] = {
        "module": module_name,
        "focus": "",
        "timestamp": time.time()
    }
    # 写反馈链到海马体（让daemon知道动作已消费）
    _write_feedback_chain(fp, module_name)
    # 最多保留20条历史
    if len(consumed["consumed"]) > 20:
        consumed["consumed"] = consumed["consumed"][-20:]
    save_consumed(consumed)

def _detect_existing_modules(action, focus_name):
    """检查action对应的模块是否已存在——严格精确匹配"""
    import re
    # 优先精确匹配: focus_{focus_name}.py
    exact = Path("brain") / f"focus_{focus_name}.py"
    if exact.exists():
        return exact.stem
    # 从action引用文本提取名: 'XXX模块' 或 "XXX模块"
    m = re.search(r"'([^']+?)模块'|\"([^\"]+?)模块\"", action)
    if m:
        name = m.group(1) or m.group(2)
        for f in Path("brain").glob("*.py"):
            if f.stem == f"gen_{name}" or f.stem == f"focus_{name}":
                return f.stem
    # 兜底: 严格=0，返回None让自动建新桩
    return None

def _gen_module_from_action(action, focus_name):
    """从动作描述自动生成模块桩"""
    import re
    
    # 提取模块名: "创建'XXX模块'" → XXX
    m = re.search(r"'([^']+)'|\"([^\"]+)\"|模块", action)
    if not m:
        return None
    
    # 安全模块名：只保留中英文数字下划线
    raw = (m.group(1) or m.group(2) or focus_name).strip()
    safe = re.sub(r'[^\u4e00-\u9fff\w]', '_', raw)
    safe = re.sub(r'_+', '_', safe).strip('_')
    if not safe:
        safe = focus_name
    
    module_file = CLUSTER / "brain" / f"focus_{safe}.py"
    if module_file.exists():
        return f"focus_{safe}"  # 已存在
    
    # 提取insight作为docstring
    try:
        focus_data = json.loads(FOCUS_FILE.read_text())
        insight = focus_data.get("insight", "")
    except:
        insight = ""
    
    content = f'''"""
focus_{safe}.py — 由焦点动作自动生成

焦点: {focus_name}
动作: {action}
洞察: {insight}

TODO: 实现具体逻辑
"""

import json, time
from pathlib import Path
from brain.share import write_chain, log

def pulse(cycle_num=0):
    """每周期调用"""
    log(f"  focus_{safe}: 模块加载，待实现")
    return [f"focus_{safe}: 桩已加载"]

if __name__ == "__main__":
    pulse(0)
'''
    module_file.write_text(content)
    return f"focus_{safe}"

def _write_feedback_chain(fp, module_name):
    """写反馈链: 焦点动作→模块已建 (让daemon知道)"""
    try:
        from brain.share import write_chain as _wc
        action_preview = fp[:40]
        _wc({"src": "焦点消费桥", "rel": "动作已消费", "dst": module_name,
            "content": f"焦点动作已消费: {action_preview}... → 模块: {module_name}",
            "dimension": "系统", "strength": 0.4})
    except:
        pass  # 反馈链不是关键路径

def pulse(cycle_num=0):
    """每周期主入口"""
    if cycle_num % 5 != 0:
        return []
    return check_and_consume()

if __name__ == "__main__":
    r = pulse(5)
    print("\\n".join(r))
