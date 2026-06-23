#!/usr/bin/env python3
"""
academic_research_bridge.py — 学术研究桥接
============================================
将academic-research-skills的工作流接入集群。
用API模拟学术全流程: 研究→写作→审稿。

用法:
  python3 academic_research_bridge.py research "研究主题"
  python3 academic_research_bridge.py write "论文大纲"
  python3 academic_research_bridge.py review "论文内容"
"""
import json, os, sys, urllib.request
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
from api_config import API_KEY, API_BASE, MODEL

def api_call(system_prompt, user_prompt, max_tokens=800):
    data = json.dumps({"model":MODEL,"messages":[
        {"role":"system","content":system_prompt},
        {"role":"user","content":user_prompt}
    ],"max_tokens":max_tokens}).encode()
    req = urllib.request.Request(f"{API_BASE}/chat/completions",data=data,
        headers={"Authorization":f"Bearer {API_KEY}","Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.loads(r.read())
            msg = resp["choices"][0]["message"]
            content = msg.get("content", "")
            reasoning = msg.get("reasoning_content", "")
            # content为空时用reasoning
            if not content.strip() and reasoning.strip():
                return reasoning
            return content
    except Exception as e:
        return f"[API错误] {e}"

RESEARCH_PROMPT = """你是一个学术研究助手。执行深度研究:
1. 分析研究主题的核心问题
2. 列出3-5个关键研究方向
3. 每个方向给出方法论建议
4. 指出可能的创新点
用中文回答，学术风格。"""

WRITE_PROMPT = """你是一个学术写作助手。根据大纲撰写论文:
1. 使用标准学术论文结构(摘要/引言/方法/结果/讨论/结论)
2. 每个部分2-3段
3. 使用严谨的学术语言
4. 标注需要引用的位置[REF]
用中文撰写。"""

REVIEW_PROMPT = """你是一个学术审稿人。审阅以下论文:
1. 结构完整性(1-10分)
2. 方法论合理性(1-10分)
3. 创新性(1-10分)
4. 写作质量(1-10分)
5. 列出3个主要问题
6. 给出修改建议
用中文审稿。"""

def research(topic):
    print(f"[研究] {topic}")
    result = api_call(RESEARCH_PROMPT, f"研究主题: {topic}", max_tokens=800)
    print(result[:500])
    return result

def write(outline):
    print(f"[写作] {outline[:50]}...")
    result = api_call(WRITE_PROMPT, f"论文大纲: {outline}", max_tokens=1500)
    print(result[:500])
    return result

def review(paper):
    print(f"[审稿] {paper[:50]}...")
    result = api_call(REVIEW_PROMPT, f"论文内容:\n{paper}", max_tokens=800)
    print(result[:500])
    return result

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "research"
    arg = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "AI多智能体系统"
    if cmd == "research": research(arg)
    elif cmd == "write": write(arg)
    elif cmd == "review": review(arg)
    else: print("用法: academic_research_bridge.py [research|write|review] 主题")
