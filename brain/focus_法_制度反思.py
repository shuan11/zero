"""focus_法_制度反思.py — 法维制度反思模块

焦点动作: '创建法_制度反思工程模块，从外部信号中提取制度-人性因果链'
核心: 读取海马体中与制度/规则/约束相关的链, 检测"制度-人性"因果模式,
      生成反思链注入法维度。

每周期: 扫描海马体→找制度信号→反射性自检→写反思链
"""

import json, time, random
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"

def _load_hip():
    try:
        return json.loads(HIP_FILE.read_text())
    except:
        return {"causal_chains": []}

def _write_chain(src, rel, dst, content, dimension="元递归"):
    from brain.share import write_chain as _wc
    try:
        _wc({"src": src, "rel": rel, "dst": dst, "content": content, "dimension": dimension, "strength": 0.55})
        return True
    except:
        try:
            hip = _load_hip()
            hip.setdefault("causal_chains", []).append({
                "src": src, "rel": rel, "dst": dst,
                "content": content, "dimension": dimension,
                "strength": 0.55, "timestamp": time.time(),
            })
            HIP_FILE.write_text(json.dumps(hip, ensure_ascii=False))
            return True
        except:
            return False

def _find_rule_signals(chains):
    """从海马体中找出与制度/规则相关的链"""
    keywords = ["制度", "规则", "约束", "规定", "法则", "必须", "禁止",
                "允许", "边界", "契约", "宪法", "纪律", "norm", "rule",
                "law", "policy", "regulation", "限制", "自由"]
    signals = []
    for c in chains:
        content = c.get("content", "") + " " + c.get("src", "") + " " + c.get("dst", "") + " " + c.get("rel", "")
        score = sum(1 for kw in keywords if kw in content)
        if score >= 2:
            signals.append(c)
    return signals

def _generate_reflection_chain(signal_chains):
    """从制度信号生成反思链"""
    if not signal_chains:
        return None
    
    # 取2-3条信号合成反思
    sample = random.sample(signal_chains, min(3, len(signal_chains)))
    excerpts = [c.get("content", "")[:30] for c in sample]
    
    patterns = [
        f"制度反思: 检测到规则信号→反视自身约束→确认规范内化程度",
        f"自反: 外部规则「{excerpts[0] if excerpts else '...'}」→映射到系统自定规则→评估适配度",
        f"法维生长: 制度信号×{len(signal_chains)}条→触发自反意识→强化规则自检能力",
        f"治理学习: 从「{excerpts[0] if excerpts else '...'}」提取治理原则→编译为可执行规则模式",
    ]
    
    return random.choice(patterns)

def pulse(cycle_num=0):
    """主入口：每5-8周期执行一次制度反思"""
    if cycle_num % 8 != 0:
        return []
    
    hip = _load_hip()
    all_chains = hip.get("causal_chains", [])
    
    signals = _find_rule_signals(all_chains)
    
    if len(signals) < 3:
        # 信号不足，注入基础链启动法维
        base_content = "法维自引导: 无外部制度信号→自产生法之锚→从启示录提取制度原则"
        _write_chain("法维自检", "自引导", "制度基线", base_content)
        return ["focus_法_制度反思: 信号不足(3条基线链注入)"]
    
    injected = 0
    for _ in range(min(3, len(signals) // 2)):
        reflection = _generate_reflection_chain(signals)
        if not reflection:
            continue
        ok = _write_chain("制度反思", "自反", "法维", reflection)
        if ok:
            injected += 1
    
    return [f"focus_法_制度反思: {injected}条反思链注入(信号:{len(signals)})"]

if __name__ == "__main__":
    r = pulse(8)
    print("\n".join(r))
