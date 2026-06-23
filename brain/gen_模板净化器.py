"""gen_模板净化器.py — 链质量评分与模板检测
本地运行，不动用API。分析所有链，标记模板内容，生成质量报告。
不删除任何链，只评分和标记。
"""
import json, re, sys, time
from pathlib import Path
from collections import Counter

CLUSTER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CLUSTER))

def load_hip():
    f = CLUSTER / "hippocampus_memory.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

def _content_features(content):
    """提取内容特征"""
    feats = {}
    feats["len"] = len(content)
    
    # 模板检测
    feats["starts_with_methodology"] = 1 if content.startswith("[方法论]") else 0
    feats["ends_with_practice"] = 1 if content.rstrip().endswith("从实践中提炼") else 0
    feats["starts_with_deep"] = 1 if re.match(r'^\[深析[×←]?\]', content) else 0
    feats["is_weak_dim_mutual_help"] = 1 if re.match(r'^弱维互助:', content) else 0
    feats["is_derivative"] = 1 if content.startswith("[衍生]") else 0
    
    # 量化
    feats["has_numbers"] = 1 if re.search(r'\d', content) else 0
    feats["has_comparison"] = 1 if any(c in content for c in ['↔', '→', '→', '→']) else 0
    feats["end_mark"] = 1 if content.rstrip()[-1:] in ('。', '？', '！') else 0
    
    # 估计模板分数（0=高质量 1=模板）
    score = 0.0
    weight = 0
    if feats["starts_with_methodology"] and feats["ends_with_practice"]:
        score += 0.8
        weight += 1
    if feats["starts_with_deep"]:
        # 检查内容是否过短
        if feats["len"] < 50:
            score += 0.5
            weight += 1
    if feats["is_weak_dim_mutual_help"]:
        score += 0.7
        weight += 1
    if feats["is_derivative"] and feats["len"] > 60:
        score += 0.3
        weight += 1
    
    if weight > 0:
        return round(score / weight, 2)
    return round(0.1 + (0 if feats["end_mark"] else 0.2), 2)

def analyze():
    hip = load_hip()
    chains = hip.get("causal_chains", [])
    
    results = []
    template_count = 0
    total = len(chains)
    
    for i, c in enumerate(chains):
        content = c.get("content", "")
        dim = c.get("dimension", "?")
        score = _content_features(content)
        
        results.append({
            "idx": i,
            "dim": dim,
            "score": score,
            "is_template": score >= 0.4,
            "preview": content[:100],
        })
        if score >= 0.4:
            template_count += 1
    
    # 按维度统计
    dim_stats = Counter()
    dim_templates = Counter()
    for r in results:
        dim_stats[r["dim"]] += 1
        if r["is_template"]:
            dim_templates[r["dim"]] += 1
    
    dim_report = {}
    for d in dim_stats:
        total_d = dim_stats[d]
        templ_d = dim_templates.get(d, 0)
        dim_report[d] = {
            "total": total_d,
            "template": templ_d,
            "template_pct": round(templ_d / total_d * 100, 1) if total_d > 0 else 0,
        }
    
    return {
        "total_chains": total,
        "template_count": template_count,
        "template_pct": round(template_count / total * 100, 1) if total > 0 else 0,
        "threshold": 0.4,
        "dim_report": dict(sorted(dim_report.items(), key=lambda x: -x[1]["template_pct"])),
        "template_examples": [r for r in results if r["is_template"]][:20],
        "quality_tips": [
            "使用具体机制描述替代'通过...实现'句式",
            "避免[方法论]...[从实践中提炼]固定结构",
            "弱维互助应附带因果解释而非单纯列举",
            "衍生与方法论不应同时生成同一内容",
        ],
    }

def engineer_模板净化器():
    result = analyze()
    
    # 保存报告
    report = CLUSTER / ".brain_模板净化报告.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    
    # 注入质量改善链
    hip = load_hip()
    chains = hip.get("causal_chains", [])
    old_len = len(chains)
    
    if result["template_pct"] > 20:
        quality_chain = {
            "src": "模板净化器",
            "rel": "检测到模板链占比",
            "dst": "质量退化",
            "content": f"模板链占{result['template_pct']}%({result['template_count']}/{result['total_chains']})——系统链质量严重不足，需优先降低模板生成源",
            "dimension": "质量",
            "template_alert": True,
        }
        from brain.share import write_chain
        write_chain(quality_chain, source="gen_模板净化器")
    
    result["old_chain_len"] = old_len
    return result

if __name__ == "__main__":
    r = engineer_模板净化器()
    print(json.dumps(r, ensure_ascii=False, indent=2))
