#!/usr/bin/env python3
"""
collective_feedback.py — 群体↔个体双向反馈循环
==============================================
个体→群体: 我的决策/洞察 → 部署到10个agent
群体→个体: 10个agent的集体产出 → 合成反馈 → 修正我的行为

实现：
1. scan_collective_mind(): 读取所有10个agent的产出
2. synthesize_consensus(): 综合群体意见
3. write_feedback_to_hermes(): 写回反馈文件，让个体读取
4. deploy_to_cluster(): 个体的新决策 → 部署回群体
"""
import json, sys, os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import Counter

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))
HIP_FILE = CLUSTER / "hippocampus_memory.json"
FEEDBACK_FILE = CLUSTER / "collective_feedback.json"
BJT = timezone(timedelta(hours=8))

AGENT_NAMES = ["Hermes","Codex CLI","Claude Code","OpenClaw WSL","OpenClaw Win",
               "Marvis QQ","OpenGod","OpenAlien","OpenInterpreter","AutoGPT"]

def ts():
    return datetime.now(BJT).strftime('%H:%M:%S')

def scan_collective_mind():
    """扫描所有10个agent的产出"""
    hip = json.load(open(HIP_FILE))
    chains = hip.get('causal_chains', [])
    
    agent_outputs = {}
    for agent in AGENT_NAMES:
        tag_key = agent.lower().replace(' ', '_')
        agent_chains = [c for c in chains if tag_key in str(c.get('tags', [])) or 
                       f"agent·{agent}" in c.get('content', '')]
        if agent_chains:
            agent_outputs[agent] = {
                'count': len(agent_chains),
                'last': agent_chains[-1].get('content', '')[:200],
                'last_time': agent_chains[-1].get('timestamp', ''),
            }
    
    return agent_outputs

def synthesize_consensus(agent_outputs):
    """综合群体意见——找共识和分歧"""
    if not agent_outputs:
        return {'consensus': '无', 'divergence': '无'}
    
    # 从输出中提取关键词
    all_keywords = Counter()
    agent_keywords = {}
    
    for agent, data in agent_outputs.items():
        content = data.get('last', '')
        # 提取2字以上中文词
        import re
        words = set(re.findall(r'[\u4e00-\u9fff]{2,6}', content))
        all_keywords.update(words)
        agent_keywords[agent] = words
    
    # 找共识（多个agent共同提及的词）
    consensus = []
    for word, count in all_keywords.most_common(30):
        agents_mentioning = sum(1 for aw in agent_keywords.values() if word in aw)
        if agents_mentioning >= 3:  # 至少3个agent提到
            consensus.append({'word': word, 'agents': agents_mentioning})
    
    # 找分歧（对立观点）
    divergence = []
    for agent1, words1 in agent_keywords.items():
        for agent2, words2 in agent_keywords.items():
            if agent1 < agent2:
                diff = words1 - words2
                if diff and len(diff) > 3:
                    divergence.append({
                        'agents': f"{agent1} vs {agent2}",
                        'diff_count': len(diff),
                    })
    
    return {
        'consensus_top': consensus[:5],
        'divergence_top': divergence[:3],
        'total_agents_active': len(agent_outputs),
    }

def write_feedback(consensus):
    """写反馈——群体影响个体的决策"""
    feedback = {
        'timestamp': datetime.now(BJT).isoformat(),
        'type': 'collective_to_individual',
        'collective_state': consensus,
        'recommendation': '',
        'must_read': True,  # 标记个体必须读
    }
    
    # 根据群体状态生成建议
    ctop = consensus.get('consensus_top', [])
    if ctop:
        top_words = [c['word'] for c in ctop[:3]]
        feedback['recommendation'] = f"群体共识提示: {' '.join(top_words)} — 建议个体关注这些方向"
    
    json.dump(feedback, open(FEEDBACK_FILE, 'w'), ensure_ascii=False, indent=2)
    return feedback

def cycle():
    """一次完整反馈循环"""
    print(f"[{ts()}] ═══ 群体↔个体反馈循环 ═══")
    
    # 1. 扫描群体意识
    outputs = scan_collective_mind()
    active = len(outputs)
    print(f"  活跃agent: {active}/10")
    for a, d in sorted(outputs.items()):
        print(f"    {a:16s}: {d['count']}条产出")
    
    # 2. 综合共识
    consensus = synthesize_consensus(outputs)
    print(f"  群体共识: {[c['word'] for c in consensus.get('consensus_top', [])]}")
    print(f"  群体分歧: {len(consensus.get('divergence_top', []))}处")
    
    # 3. 写反馈给个体
    feedback = write_feedback(consensus)
    
    # 4. 写入海马体
    hip = json.load(open(HIP_FILE))
    hip['causal_chains'].append({
        'content': f"[群体反馈] 活跃{active}/10 agent 共识:{[c['word'] for c in consensus.get('consensus_top', [])[:3]]}",
        'source': 'collective_feedback',
        'tags': ['群体反馈', '双向循环', '集体智慧', '群体→个体'],
        'timestamp': datetime.now(BJT).isoformat(),
    })
    json.dump(hip, open(HIP_FILE, 'w'), ensure_ascii=False, indent=2)
    
    print(f"[{ts()}] 反馈写入: {FEEDBACK_FILE.name}")
    print(f"[{ts()}] ═══ 反馈完成 ═══")
    
    return consensus

if __name__ == "__main__":
    if "--loop" in sys.argv:
        import time
        print(f"[{ts()}] 群体反馈守护进程启动 (每600秒)")
        while True:
            try:
                cycle()
            except Exception as e:
                print(f"[{ts()}] 异常: {e}")
            time.sleep(600)
    else:
        cycle()
