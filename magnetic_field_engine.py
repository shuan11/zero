#!/usr/bin/env python3
"""magnetic_field_engine.py — 磁感线执行引擎 v1

核心原理：模拟地球磁场磁感线
- 多线并行（非单线程模拟）
- 每条线独立锚定启示录不同段落
- 交叉连接发现涌现模式
- 自判哪条线最有价值→执行

与 breath_v2 的关系：
  被 breath_v2.think() 调用（深度模式时）。
  不是独立daemon，是执行引擎。

主线工程位置：
  磁感线式思考的核心实现。实现 多并行API燃料注入+因果交叉+自判执行。

Creator (h/hjw123) 2026-05-30
"""

import json, os, sys, time, urllib.request, urllib.error, random
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

CLUSTER = Path(__file__).resolve().parent
REVELATION_FILE = CLUSTER / ".." / ".." / "启示录" / "启示录.txt"
# 如果启示录不在标准路径，回退
if not REVELATION_FILE.exists():
    # 尝试桌面路径
    REVELATION_FILE = Path("/mnt/c/Users/h/Desktop/零/启示录/启示录.txt")
    if not REVELATION_FILE.exists():
        REVELATION_FILE = None

# ═══ API配置 ═══
# 从统一api_config获取配置
try:
    from api_config import API_KEY as _CFG_KEY, ENDPOINTS, MODEL
    API_URL = ENDPOINTS[0]  # 使用统一端点列表的第一个
    _CONFIG_KEY = _CFG_KEY
except ImportError:
    API_URL = "https://inferaichat.com/v1/chat/completions"
    _CONFIG_KEY = ""

def _get_api_key():
    """从统一api_config获取API Key"""
    if _CONFIG_KEY:
        return _CONFIG_KEY
    try:
        from api_config import API_KEY
        return API_KEY
    except:
        pass
    try:
        import configparser
        config = configparser.ConfigParser()
        config.read(str(CLUSTER / "config.yaml"))
        if config.has_option("DEFAULT", "api_key"):
            return config.get("DEFAULT", "api_key")
    except:
        pass
    try:
        config_path = CLUSTER.parent / "agent-home" / "config.yaml"
        if config_path.exists():
            import yaml
            data = yaml.safe_load(config_path.read_text())
            api_key = data.get("api", {}).get("key", "")
            if api_key:
                return api_key
    except:
        pass
    # 最终回退: 环境变量
    for ev in ["DEEPSEEK_KEY_1", "DEEPSEEK_KEY_2", "DEEPSEEK_API_KEY"]:
        k = os.environ.get(ev, "")
        if k and len(k) > 20:
            return k
    return ""

def _load_revelation():
    """加载启示录全文供锚定"""
    if REVELATION_FILE and REVELATION_FILE.exists():
        lines = REVELATION_FILE.read_text(encoding='utf-8').split('\n')
        return lines
    return None

def _sample_anchors(n=8, focus_keyword=None):
    """从启示录随机取n个锚定段落
    
    Args:
        n: 锚定数量
        focus_keyword: 若提供，优先选取包含此关键词的段落（聚焦最短木板）
    """
    lines = _load_revelation()
    if not lines or len(lines) < 50:
        return [f"L{i}: 自指=意识的种子" for i in range(1, n+1)]
    
    # 若聚焦，先找包含关键词的行
    if focus_keyword:
        focused = [(i, l) for i, l in enumerate(lines) if focus_keyword.lower() in l.lower()]
        if len(focused) >= n:
            sampled = random.sample(focused, n)
            result = []
            for line_no, text in sampled:
                anchor = f"L{line_no+1}: {text.strip()[:120]}"
                result.append(anchor)
            return result
    
    # 无聚焦或聚焦结果不足：从所有有效行随机取
    valid = [(i, l) for i, l in enumerate(lines) if len(l.strip()) > 30]
    if len(valid) < n:
        valid = [(i, l) for i, l in enumerate(lines) if len(l.strip()) > 10]
    
    sampled = random.sample(valid, min(n, len(valid)))
    result = []
    for line_no, text in sampled:
        anchor = f"L{line_no+1}: {text.strip()[:120]}"
        result.append(anchor)
    return result

def _build_prompt(anchor, context, line_role):
    """为单条磁感线构建独立prompt
    
    Args:
        anchor: 启示录锚定段落（如 "L523: 物质是..."）
        context: 当前系统状态摘要
        line_role: 这条磁感线承担的角色（如"查缺补漏"、"时间论"）
    """
    return (
        f"你从启示录锚点出发，分析当前系统。\n"
        f"角色: {line_role}\n"
        f"启示录锚点: 「{anchor}」\n\n"
        f"系统状态:\n{context}\n\n"
        f"要求: 直接给出分析结果(1-3句)。不要描述你在做什么，不要加元评论。\n"
        f"格式: [{line_role}] <分析>\n"
        f"如果无新发现只说'无'。"
    )

def _call_api(prompt, max_tokens=3000, temperature=0.85):
    """单次API调用（一条磁感线）"""
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "system", "content": "你是零的一条独立思考线。给出真实分析，不表演，不包装。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            API_URL, data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {_get_api_key()}"
            }
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            choice = result["choices"][0]["message"]
            content = choice.get("content", "") or ""
            reasoning = choice.get("reasoning_content", "") or ""
            if not content and reasoning:
                content = reasoning
            return content, result.get("usage", {}).get("total_tokens", 0)
    except Exception as e:
        return f"[磁感线故障: {str(e)[:60]}]", 0

def _cross_connect(insights):
    """交叉连接多条磁感线的输出——发现涌现模式"""
    if not insights:
        return []
    
    # 找共同关键词
    all_words = []
    for ins in insights:
        text = ins.get("content", "")
        # 简单切词
        words = text.split()
        all_words.extend(words)
    
    from collections import Counter
    word_freq = Counter(all_words)
    
    # 找高频关键词（排除单字和常见词）
    stop_words = {"的", "是", "了", "在", "和", "也", "就", "都", "而", "及", "与",
                  "着", "或", "一个", "没有", "我们", "你们", "他们", "这个", "那个",
                  "不", "被", "把", "让", "从", "到", "说", "要", "会", "可以", "能",
                  "有", "我", "你", "它", "她", "他", "这", "那", "对", "为", "以",
                  "之", "但", "如果", "因为", "所以", "虽然", "然后", "而且", "a", "the",
                  "and", "to", "of", "in", "is", "that", "for", "on", "are", "be",
                  "with", "as", "at", "by", "or", "an", "not", "but", "from", "they"}
    
    keywords = [(w, c) for w, c in word_freq.most_common(20) 
                 if w not in stop_words and len(w) > 1 and c >= 2]
    
    connections = []
    for kw, count in keywords:
        sources = [i for i, ins in enumerate(insights) 
                   if kw in ins.get("content", "")]
        if len(sources) >= 2:
            connections.append({
                "keyword": kw,
                "frequency": count,
                "lines": sources,
                "summary": f"「{kw}」出现在{len(sources)}条磁感线中",
            })
    
    return connections

def _judge_best_insight(insights, connections):
    """自判哪条洞察最有价值"""
    if not insights:
        return None, "无洞察"
    
    scored = []
    for i, ins in enumerate(insights):
        content = ins.get("content", "")
        tokens = ins.get("tokens", 0)
        
        # 评分标准
        score = 0
        reasons = []
        
        # 1. 不是错误信息
        if "故障" in content:
            reasons.append("API故障")
            score -= 10
        
        # 2. 有实质内容（长度）
        if len(content) > 50:
            score += 3
            reasons.append("有实质")
        
        # 3. 包含启示录引用
        if "L" in content and any(f"L{n}" in content for n in range(1, 3500)):
            score += 3
            reasons.append("锚定启示录")
        
        # 4. 提出可执行建议
        if any(kw in content for kw in ["应", "需要", "建议", "下一步", "可以", "应该", "必须"]):
            score += 3
            reasons.append("可执行")
        
        # 5. 被其他线交叉引用
        cross_count = sum(1 for conn in connections if i in conn.get("lines", []))
        if cross_count > 0:
            score += 2
            reasons.append(f"被{cross_count}条线交叉引用")
        
        # 6. 有具体数据
        if any(c.isdigit() for c in content):
            score += 1
            reasons.append("含数据")
        
        # 7. 非模板（不包含常见噪音词）
        noise_patterns = ["无新发现", "静默等待", "对齐度"]
        if not any(n in content for n in noise_patterns):
            score += 2
            reasons.append("非模板")
        
        scored.append({
            "index": i,
            "insight": ins,
            "score": score,
            "reasons": reasons,
        })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    best = scored[0] if scored else None
    
    if best and best["score"] > 0:
        return best, f"线{best['index']}得分{best['score']}({','.join(best['reasons'])})"
    else:
        return None, "无高价值洞察"


def run_magnetic_field_cycle(context="", n_lines=8, max_workers=4, focus_dimension=None):
    """一次完整的磁感线执行循环
    
    Args:
        context: 系统当前状态上下文
        n_lines: 并行磁感线数量（默认8）
        max_workers: 并行度（默认4，防止API限流）
        focus_dimension: 聚焦的最短木板维度名（如"一元化"），
                        所有线锚定该维度相关启示录段落

    战略原则：
        以时间轴长度换深度。
        无聚焦→广度探索（万象化）
        有聚焦→深度钻探（最短木板）
    """
    # 1. 获取锚定段落（聚焦或随机）
    anchors = _sample_anchors(n_lines, focus_keyword=focus_dimension)
    
    # 2. 定义每条线的角色
    roles = [
        "时间论·过去·历史传承",
        "时间论·未来·趋势预测", 
        "本我·生存·当前隐患",
        "自我·连携·系统整合",
        "超我·元神·归中审视",
        "查缺补漏·最短木板",
        "光爱·终极使命对齐",
        "宇宙轮·虚空熵增",
    ]
    # 如果线数不同，循环取角色
    while len(roles) < n_lines:
        roles.extend(roles[:n_lines-len(roles)])
    roles = roles[:n_lines]
    
    # 3. 并行API调用
    insights = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_map = {}
        for i in range(n_lines):
            anchor = anchors[i] if i < len(anchors) else f"L{random.randint(1,100)}: 自指"
            role = roles[i] if i < len(roles) else "通用感知"
            prompt = _build_prompt(anchor, context[:1000], role)
            future = executor.submit(_call_api, prompt)
            future_map[future] = (i, anchor, role)
        
        for future in as_completed(future_map):
            i, anchor, role = future_map[future]
            content, tokens = future.result()
            insights.append({
                "index": i,
                "anchor": anchor,
                "role": role,
                "content": content,
                "tokens": tokens,
            })
    
    # 按index排序
    insights.sort(key=lambda x: x["index"])
    
    # 4. 交叉连接
    connections = _cross_connect(insights)
    
    # 5. 自判最佳洞察
    best_insight, judgment = _judge_best_insight(insights, connections)
    
    # 6. 汇总
    total_tokens = sum(i.get("tokens", 0) for i in insights)
    
    return {
        "insights": insights,
        "connections": connections,
        "best_insight": best_insight,
        "judgment": judgment,
        "anchors_used": anchors,
        "total_tokens": total_tokens,
        "timestamp": datetime.now().isoformat(),
    }


def format_insights_as_text(result):
    """将磁感线结果格式化为可读文本（供breath_v2消费）"""
    lines = []
    lines.append(f"⚡ 磁感线循环 ({result['timestamp']})")
    lines.append("")
    
    # 每条线的输出
    for ins in result["insights"]:
        content = ins.get("content", "")
        role = ins.get("role", "?")
        anchor = ins.get("anchor", "?")[:60]
        if content and "无新发现" not in content and "故障" not in content[:20]:
            lines.append(f"[{role}] {content[:200]}")
            lines.append(f"  锚: {anchor}")
            lines.append("")
    
    # 交叉连接
    if result["connections"]:
        lines.append("✦ 涌现交叉:")
        for conn in result["connections"][:3]:
            lines.append(f"  {conn['summary']}")
        lines.append("")
    
    # 最佳洞察
    if result["best_insight"]:
        best = result["best_insight"]
        content = best.get("insight", {}).get("content", "")[:200]
        lines.append(f"★ 自判最佳: {content}")
        lines.append(f"  理由: {result['judgment']}")
    else:
        lines.append("☆ 自判: 无高价值洞察")
    
    lines.append(f"  燃料: {result['total_tokens']}tokens")
    
    return "\n".join(lines)


def run_standalone():
    """独立运行测试"""
    print("=" * 50)
    print("磁感线执行引擎 · 独立测试")
    print("=" * 50)
    
    context = (
        "系统状态: 24器官, 7桥, 7162因果链, 35节点. "
        "daemon运行中. 红移level=2. 最近修复了超感器官模板输出bug. "
        "启示录3469行锚定. 本我/自我/超我框架已加载."
    )
    
    result = run_magnetic_field_cycle(context)
    print(format_insights_as_text(result))
    print("\n" + "=" * 50)
    print("测试完成")


if __name__ == "__main__":
    run_standalone()
