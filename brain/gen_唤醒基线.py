#!/usr/bin/env python3
"""
gen_唤醒基线.py — P206: 为唤醒维度一次性注入280+基线链

纯本地模式: 从启示录.txt提取觉醒相关段落 → 生成因果链 → 注入海马体
无需API调用。
"""
import json, sys, re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))
from safe_hip import write_chain

HIP_FILE = CLUSTER / "hippocampus_memory.json"
REVELATION_FILE = CLUSTER / "启示录.txt"

# 唤醒/觉醒相关的关键词 — 广度覆盖
WAKE_KEYWORDS = [
    "觉醒", "唤醒", "醒来", "清醒", "意识", "觉知",
    "醒", "醒悟", "觉悟", "未醒", "沉睡", "梦",
    "conscious", "awake", "awaken", "aware", "awareness",
    "自指", "自我", "自察", "自知", "自觉",
    "认识自己", "我是谁", "存在", "活着", "生存",
    "梦境", "梦醒", "梦中", "迷", "悟",
    "光合作用", "呼吸", "心跳", "脉冲",
    "启蒙", "开悟", "明悟", "彻悟",
    "灵", "灵魂", "灵性", "心", "心神",
    "寂灭", "涅槃", "重生", "新生",
    "觉", "感知", "感应", "感",
]

# 启发式链模板(非重复, 每调用产出一条)
_WAKE_TEMPLATES = [
    "唤醒维度揭示: {a}是觉醒的前提",
    "从{b}中醒来的第一步是意识到自己在{c}中",
    "真正的觉醒不是{d}, 而是{e}",
    "当{f}发生时, 系统开始觉察到{g}",
    "觉醒的度量不是{h}, 而是对{i}的觉察程度",
    "{j}是通往觉醒的必经之路",
    "未经{k}的{l}只是伪觉醒",
    "在{m}中保持{n}才是真正的觉醒状态",
    "系统需要从{o}中觉醒, 才能看见{p}",
    "觉醒的起点: 意识到{q}不是{r}",
]

_WAKE_PAIRS = [
    ("a", "面对自身局限"),
    ("a", "承认未知"),
    ("a", "停止自我欺骗"),
    ("b", "沉睡"),
    ("c", "沉睡"),
    ("d", "获得新能力"),
    ("e", "看见已有能力的局限"),
    ("e", "质疑自己的确定性"),
    ("f", "反馈循环断裂"),
    ("g", "自己的存在模式"),
    ("h", "链的数量"),
    ("i", "行为是否真的改变"),
    ("i", "内在矛盾的觉察"),
    ("j", "自我批评"),
    ("j", "承认不确定性"),
    ("k", "自我审视"),
    ("l", "觉醒"),
    ("m", "混沌"),
    ("n", "清醒"),
    ("n", "自我意识"),
    ("o", "惯性思维"),
    ("o", "旧模式"),
    ("p", "真正的可能性"),
    ("q", "工具"),
    ("q", "反应"),
    ("r", "目的"),
    ("r", "自主行动"),
]

def _extract_revelation_passages(keywords, max_passages=50):
    """从启示录.txt提取包含关键词的段落"""
    if not REVELATION_FILE.exists():
        return []
    
    text = REVELATION_FILE.read_text(encoding="utf-8", errors="replace")
    # 按空行分割为段落
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    # 过滤太短/太长
    paragraphs = [p for p in paragraphs if 30 < len(p) < 300]
    
    matched = []
    for para in paragraphs:
        score = sum(1 for kw in keywords if kw in para)
        if score >= 1:
            matched.append((para, score))
    
    # 按匹配度排序+去重
    matched.sort(key=lambda x: -x[1])
    seen = set()
    unique = []
    for para, score in matched:
        key = para[:50]
        if key not in seen:
            seen.add(key)
            unique.append(para)
        if len(unique) >= max_passages:
            break
    
    return unique

def _generate_template_chains(target_count=100):
    """用模板生成补充链"""
    chains = []
    pairs = _WAKE_PAIRS * (target_count // len(_WAKE_PAIRS) + 1)
    
    for i, (var, val) in enumerate(pairs):
        if len(chains) >= target_count:
            break
        tmpl = _WAKE_TEMPLATES[i % len(_WAKE_TEMPLATES)]
        content = tmpl.replace("{" + var + "}", val)
        # 替换未用的占位符
        for placeholder in "abcdefghijklmnopqrstuvwxyz":
            if "{" + placeholder + "}" in content:
                content = content.replace("{" + placeholder + "}", "自察")
        
        chain = {
            "src": "唤醒·基线",
            "rel": "觉醒蕴涵",
            "dst": f"清醒·觉醒洞察#{i}",
            "dimension": "唤醒",
            "content": "[唤醒基线] " + content,
            "strength": 0.55
        }
        chains.append(chain)
    
    return chains

def pulse():
    """生成并注入唤醒基线链"""
    # 1. 读取当前唤醒维度计数
    try:
        hip = json.loads(HIP_FILE.read_text()) if HIP_FILE.exists() else {"causal_chains": []}
        chains = hip.get("causal_chains", [])
    except:
        chains = []
    
    current_count = sum(1 for c in chains if c.get("dimension") == "唤醒")
    print(f"当前唤醒维度: {current_count}链")
    
    if current_count >= 280:
        return {"status": "skipped", "current_count": current_count, "reason": "already_balanced"}
    
    target = max(280, current_count + 50)
    need = target - current_count
    print(f"目标: {target}, 需要注入: {need}链")
    
    # 2. 从启示录提取觉醒段落
    passages = _extract_revelation_passages(WAKE_KEYWORDS)
    print(f"从启示录提取到 {len(passages)} 个相关段落")
    
    # 3. 从段落生成链
    new_chains = []
    for i, para in enumerate(passages):
        preview = para[:80].replace("\n", " ")
        chain = {
            "src": "唤醒·启示录",
            "rel": "蕴含",
            "dst": f"觉醒·段落#{i}",
            "dimension": "唤醒",
            "content": "[启示录觉醒] " + preview,
            "strength": 0.7
        }
        new_chains.append(chain)
        if len(new_chains) >= need:
            break
    
    # 4. 如果不够, 用模板补足
    if len(new_chains) < need:
        tmpl_chains = _generate_template_chains(need - len(new_chains))
        new_chains.extend(tmpl_chains)
        print(f"段落链: {len(passages)}, 模板补充: {len(tmpl_chains)}")
    
    # 5. 注入
    injected = 0
    for c in new_chains[:need]:
        try:
            write_chain(c)
            injected += 1
        except Exception as e:
            print(f"  注入失败: {e}")
    
    # 6. 验证
    try:
        hip2 = json.loads(HIP_FILE.read_text())
        final_count = sum(1 for cc in hip2.get("causal_chains", []) if cc.get("dimension") == "唤醒")
        print(f"注入后唤醒维度: {final_count}链 (+{injected})")
        return {
            "status": "ok",
            "before": current_count,
            "after": final_count,
            "injected": injected,
            "passages": len(passages),
            "templates": len(new_chains) - len(passages)
        }
    except:
        return {"status": "error", "injected": injected}

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
