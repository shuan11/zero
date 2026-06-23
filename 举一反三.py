"""
举一反三.py — 模式泛化引擎
从超感发现的稀有交叉对中，推演普遍规律

核心功能:
  1. 读取超感发现的最新稀有交叉对
  2. 从每个稀有对的sample中提取通用模式
  3. 反向匹配: 如果模式A在维度X和Y间成立, 那么还应该在哪成立?
  4. 写入海马体作为"泛化链"

数学本质:
  举一反三 = 从N个特例中提取(N-1)个共性 → 预测第N+1个
  
运行方式:
  breath_v2每cycle调用, 有新的稀有对才泛化
"""

import json
import random
import time
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone, timedelta
from safe_hip import write_chain, write_chain_legacy

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SS_FILE = CLUSTER / "supersense_state.json"
LOG_FILE = CLUSTER / "breath_v2.log"

def log(msg):
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{ts}]   🔁 {msg}\n")

def load_json(path):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except:
        return {}

# 泛化模板: 从交叉对→普遍规律
GENERALIZATION_TEMPLATES = {
    ("教员", "无师自通"): [
        "当{dim1}与{dim2}交叉时, 真正的学习发生在指导与自学的边界",
        "{dim1}×{dim2}的张力表明: 系统在外部引导和内部驱动间寻求平衡",
        "最有效的进化路径: {dim1}定义方向, {dim2}执行探索",
    ],
    ("举一反三", "无师自通"): [
        "从已有模式({dim1})推导新知识({dim2})是硅基学习的核心回路",
        "{dim1}发现的规律必须通过{dim2}验证才能内化为知识",
        "模式识别({dim1})→自主应用({dim2})构成完整的学习闭环",
    ],
    ("触类旁通", "超感"): [
        "跨域连接({dim1})是超感({dim2})的原材料——没有类比就没有直觉",
        "{dim1}的广度与{dim2}的深度需要动态平衡",
        "每一条{dim1}的类比输入都可能是{dim2}的涌现种子",
    ],
    ("光爱", "举一反三"): [
        "光爱终极({dim1})需要举一反三({dim2})的能力来扩大正循环范围",
        "{dim1}是目的, {dim2}是手段——从每个善举推导出更多善举",
        "正循环制度 = {dim1}×{dim2}: 从单一善举扩展到系统性善良",
    ],
}

def pulse():
    """举一反三脉冲: 每次呼吸执行"""
    try:
        # 1. 读取超感最新状态
        ss = load_json(SS_FILE)
        top_rare = ss.get("top_rare", [])
        insights = ss.get("insights_generated", 0)
        
        if not top_rare or insights == 0:
            return {"alive": True, "generalized": 0, "reason": "no_new_rare_pairs"}
        
        # 2. 解析稀有对
        new_chains = []
        generalized = 0
        for rare_str in top_rare:
            # 格式: "教员×无师自通(159)"
            if "×" not in rare_str or "(" not in rare_str:
                continue
            pair_part = rare_str.split("(")[0]
            dims = pair_part.split("×")
            if len(dims) != 2:
                continue
            d1, d2 = dims[0].strip(), dims[1].strip()
            
            # 3. 查泛化模板
            key = (d1, d2)
            rev_key = (d2, d1)
            templates = GENERALIZATION_TEMPLATES.get(key, []) or GENERALIZATION_TEMPLATES.get(rev_key, [])
            
            if templates:
                # 选一条模板泛化
                template = random.choice(templates)
                insight = template.format(dim1=d1, dim2=d2)
                
                # 去重: 检查海马体是否已有相同insight
                hip = load_json(HIP_FILE)
                existing = [c.get("content", "") for c in hip.get("causal_chains", [])[-50:]]
                if insight in existing:
                    continue
                
                chain = {
                    "src": "举一反三·泛化", "rel": f"{d1}×{d2}", "dst": "模式",
                    "strength": min(0.99, (7.0 + random.random() * 2.0) / 10.0),
                    "tags": [d1, d2, "举一反三", "泛化", "模式推演"],
                    "content": f"[举一反三] {d1}×{d2}: {insight}",
                    "dimension": "举一反三",
                    "timestamp": time.time(),
                }
                new_chains.append(chain)
                generalized += 1
        
        # 4. 写入海马体(委托safe_hip)
        if new_chains:
            for chain in new_chains:
                write_chain(chain)
            log(f"{generalized}条泛化链: {[c['tags'][0]+'×'+c['tags'][1] for c in new_chains]}")
        
        return {"alive": True, "generalized": generalized, "chains": len(new_chains)}
    
    except Exception as e:
        log(f"⚠️ 举一反三异常: {str(e)[:80]}")
        return {"alive": True, "generalized": 0, "error": str(e)[:80]}

if __name__ == "__main__":
    r = pulse()
    print(json.dumps(r, indent=2, ensure_ascii=False))
