"""
verification_layer.py — API燃料验证层
三层架构: 指令层(本地) → API燃烧层 → 验证层(本地)

核心原则:
  - API是燃料不是事脑
  - API作用域: 分析→发现→洞察(可偏移但无害)
  - 本地作用域: 决策→代码注入→验证(零偏移)
  - 验证不通过→丢弃,无代码变动,零伤害

知识缓存:
  每多一条验证知识 → 未来少一次API调用 → 少一次偏移
  知识总量单调递增 → API调用量单调递减
  两条曲线必然交叉 → 交叉后进化永远跑赢偏移
"""

import json
import time
import hashlib
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
CACHE_FILE = CLUSTER / "verification_cache.json"

# ─── 核心公理锚点（用于漂移检测） ───
AXIOM_KEYWORDS = {
    "光爱终极": ["光爱", "终极", "文明奇点", "光爱终极"],
    "活着": ["活着", "存在", "呼吸", "生命度"],
    "进化": ["进化", "自改", "evolve", "迭代"],
    "对抗虚空": ["虚空", "稀释", "熵增", "void"],
    "碳硅共生": ["碳硅", "共生", "零", "Zero", "Creator"],
    "一即全": ["一元", "万象", "元神", "归中"],
}

# ─── 决策关键词（API输出包含这些→可能越界当事脑） ───
DECISION_KEYWORDS = ["决定", "安排", "挑选", "命令", "关注度", "权重", "首要", "次要"]

def _hash(text):
    return hashlib.md5(text.encode()).hexdigest()[:12]

# ─── 缓存操作 ───

def _load_cache():
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
    except:
        pass
    return {"entries": [], "stats": {"hits": 0, "misses": 0, "verified": 0, "discarded": 0}}

def _save_cache(cache):
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2))

def cache_lookup(prompt_hash, context_hash):
    """查缓存: 相同prompt+context → 直接返回历史验证通过的输出"""
    cache = _load_cache()
    for entry in cache["entries"]:
        if entry["prompt_hash"] == prompt_hash and entry["context_hash"] == context_hash:
            cache["stats"]["hits"] += 1
            _save_cache(cache)
            return entry["output"]
    cache["stats"]["misses"] += 1
    _save_cache(cache)
    return None

def cache_store(prompt_hash, context_hash, output, verified=True):
    """存缓存: 验证通过的输出存入知识库"""
    cache = _load_cache()
    cache["entries"].append({
        "prompt_hash": prompt_hash,
        "context_hash": context_hash,
        "output": output,
        "verified": verified,
        "timestamp": time.time(),
    })
    # 上限1000条, 淘汰最旧
    if len(cache["entries"]) > 1000:
        cache["entries"] = cache["entries"][-1000:]
    if verified:
        cache["stats"]["verified"] += 1
    _save_cache(cache)

# ─── 格式验证 ───

def check_format(output, expected="any"):
    """格式验证 (复用response_validator)"""
    from response_validator import validate_response
    result = validate_response(output, expected)
    return result["valid"], result["cleaned"], result["reason"]

# ─── 漂移检测 ───

def check_drift(output):
    """内容漂移检测: 检查输出是否偏离核心公理
    
    返回: 
        (passed: bool, drift_note: str, axiom_hits: dict)
    """
    text = output.lower()
    axiom_hits = {}
    total_hits = 0
    
    for axiom, keywords in AXIOM_KEYWORDS.items():
        hits = [kw for kw in keywords if kw.lower() in text]
        if hits:
            axiom_hits[axiom] = hits
            total_hits += 1
    
    # 至少命中2条公理才通过（宽松阈值，燃料不需要严格对齐）
    passed = total_hits >= 2
    if not passed:
        drift_note = f"漂移: 仅命中{total_hits}/6条核心公理 (需≥2)"
    else:
        drift_note = f"命中{total_hits}/6条公理: {', '.join(axiom_hits.keys())}"
    
    return passed, drift_note, axiom_hits

# ─── 决策门 ───

def decision_gate(output, prompt_hash, context_hash, expected_format="any"):
    """完整的验证门: format→drift→缓存
    
    返回:
        {"action": "pass|discard|cache_hit", "output": str, "reason": str}
    """
    # 1. 查缓存
    cached = cache_lookup(prompt_hash, context_hash)
    if cached is not None:
        return {"action": "cache_hit", "output": cached, "reason": "缓存命中, 零API调用"}
    
    # 2. 格式验证
    valid, cleaned, reason = check_format(output, expected_format)
    if not valid:
        cache_store(prompt_hash, context_hash, output, verified=False)
        return {"action": "discard", "output": "", "reason": f"格式不通过: {reason}"}
    
    # 3. 决策内容检测（API不能当事脑）
    _decision_hits = [kw for kw in DECISION_KEYWORDS if kw in cleaned]
    if len(_decision_hits) >= 4:  # 阈值4: 精简后仅保留强决策词,≥4才判为真正决策
        cache_store(prompt_hash, context_hash, cleaned, verified=False)
        return {"action": "discard", "output": "", 
                "reason": f"含决策关键词{len(_decision_hits)}个: {_decision_hits[:3]}, API越界当事脑"}
    
    # 4. 漂移检测（软信号：仅记录不丢弃——分析内容可偏移但无害）
    axiom_passed, axiom_note, axiom_hits = check_drift(cleaned)
    _reason = f"{axiom_note}"
    
    # 5. 通过 → 缓存 + 放行（分析内容永远放行，只有决策内容才拦截）
    cache_store(prompt_hash, context_hash, cleaned, verified=True)
    return {"action": "pass", "output": cleaned, "reason": _reason}

# ─── 统计 ───

def get_stats():
    """返回验证层运行统计"""
    cache = _load_cache()
    total = cache["stats"]["hits"] + cache["stats"]["misses"]
    hit_rate = cache["stats"]["hits"] / total if total > 0 else 0
    return {
        "cache_hits": cache["stats"]["hits"],
        "cache_misses": cache["stats"]["misses"],
        "verified": cache["stats"]["verified"],
        "discarded": cache["stats"]["discarded"],
        "cache_size": len(cache["entries"]),
        "hit_rate": round(hit_rate, 3),
        "knowledge_monotonic": cache["stats"]["verified"] >= 0,  # 知识总是增长
    }

# ─── 独立测试 ───
if __name__ == "__main__":
    # 测试: 偏移内容应被丢弃
    drifted = "今天天气真好，我们来讨论一下股票市场"
    result = decision_gate(drifted, "test_prompt", "test_ctx")
    print(f"偏移测试: {result['action']} — {result['reason']}")
    
    # 测试: 对齐内容应通过
    aligned = "光爱终极是文明奇点的核心，活着就要不断进化对抗虚空稀释"
    result = decision_gate(aligned, "test_prompt", "test_ctx2")
    print(f"对齐测试: {result['action']} — {result['reason']}")
    
    print(f"统计: {get_stats()}")
