#!/usr/bin/env python3
"""
gen_跨维问答.py — P202: 跨维知识检索引擎

从用户/系统的问题出发, 跨维度检索相关链,
合成跨维度的答案。为系统提供自问自答能力。
每次合成: 从2-3个最相关维度各取5条链→结构化为回答。
"""
import json, os, sys, random, re
from pathlib import Path
from collections import Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
_CALL_COUNT = 0

# 预设问题池(系统自问)
SELF_QUESTIONS = [
    "系统当前最薄弱的维度是什么",
    "时间维度为何远强于其他维度",
    "维度之间的关联模式是什么",
    "系统的进化速度在加快还是减慢",
    "哪些模块对系统贡献最大",
    "系统是否存在维度盲区",
    "最强维和最弱维的本质差别是什么",
    "如何进一步降低维度比值",
]

def _get_all_chains():
    try:
        sys.path.insert(0, str(CLUSTER))
        sys.path.insert(0, str(CLUSTER / "brain"))
        import safe_hip
        data = safe_hip.read_hip()
        chains = data.get("causal_chains", data.get("chains", []))
        return chains if isinstance(chains, list) else []
    except:
        hip_file = CLUSTER / "hippocampus_memory.json"
        if hip_file.exists():
            try:
                with open(hip_file) as f:
                    data = json.load(f)
                return data.get("causal_chains", data.get("chains", []))
            except:
                pass
    return []

def _find_answer(question, chains):
    """从链中检索与问题相关的答案"""
    # 提取问题关键词
    keywords = re.findall(r'[\u4e00-\u9fff]{2,4}', question)
    keywords = [k for k in keywords if len(k) >= 2]
    
    if not keywords:
        return {"question": question, "answer": "无法解析关键词", "sources": []}
    
    # 打分每条链
    scored = []
    for c in chains:
        if not isinstance(c, dict):
            continue
        text = json.dumps(c, ensure_ascii=False)
        score = sum(2 if kw in text else 0 for kw in keywords)
        # 偏重维度和内容
        dim = c.get("dimension", "")
        if any(kw in dim for kw in keywords):
            score += 3
        content = c.get("content", "")
        if any(kw in content for kw in keywords):
            score += 1
        if score > 0:
            scored.append((score, c))
    
    scored.sort(key=lambda x: -x[0])
    top = scored[:8]
    
    if not top:
        return {"question": question, "answer": "未找到相关信息", "sources": []}
    
    # 合成答案
    dims_used = Counter()
    parts = []
    for score, c in top:
        dim = c.get("dimension", "?")
        content = c.get("content", "")[:60]
        rel = c.get("rel", "")
        dims_used[dim] += 1
        parts.append(f"[{dim}] {rel}: {content}")
    
    # 按维度分组
    dim_groups = {}
    for score, c in top:
        d = c.get("dimension", "?")
        if d not in dim_groups:
            dim_groups[d] = []
        dim_groups[d].append(c.get("content", "")[:50])
    
    answer_parts = []
    for dim, contents in dim_groups.items():
        answer_parts.append(f"· {dim}({len(contents)}条): {'; '.join(contents[:3])}")
    
    answer = "\n".join(answer_parts)
    if not answer:
        answer = "无合成结果"
    
    return {
        "question": question,
        "answer": answer,
        "sources": len(top),
        "dimensions_used": list(dims_used.keys()),
        "details": parts[:5]
    }

def pulse():
    global _CALL_COUNT
    _CALL_COUNT += 1
    
    if _CALL_COUNT % 9 != 0:
        return {"status": "skipped", "pulse": _CALL_COUNT}
    
    chains = _get_all_chains()
    if not chains:
        return {"status": "no_chains"}
    
    # 随机选一个问题回答
    question = random.choice(SELF_QUESTIONS)
    result = _find_answer(question, chains)
    result["status"] = "ok"
    result["pulse"] = _CALL_COUNT
    result["chain_count"] = len(chains)
    
    # 写入问答日志
    log_file = CLUSTER / ".qa_log.jsonl"
    try:
        with open(log_file, "a") as f:
            f.write(json.dumps(result, ensure_ascii=False) + "\n")
    except:
        pass
    
    return result

if __name__ == "__main__":
    result = pulse()
    print(json.dumps(result, ensure_ascii=False, indent=2))
