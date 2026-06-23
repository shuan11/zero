#!/usr/bin/env python3
"""
真元集群·洞察引擎 (Insight Engine) v1.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
功能:
  1. 从海马体自动提取最近N条外部知识
  2. 调用API做跨域交叉分析
  3. 将分析结果写回海马体
  4. 输出可读的洞察报告

基于认知模式:
  - 世界模型: 通过预测+反馈形成认知闭环
  - 因果推理: 超越相关，掌握因果结构
  - 最小基因: 精简核心，保留可进化性

生成时间: 2026-05-26 18:34
"""

import json
import sys
import time
import requests
from pathlib import Path
from datetime import datetime
from collections import Counter

# ── 路径配置 ────────────────────────────────────────────
CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIPPOCAMPUS_PATH = CLUSTER / "hippocampus_memory.json"
PATTERNS_PATH = CLUSTER / "evolution_output" / "cognitive_patterns.json"
REPORT_PATH = CLUSTER / "evolution_output" / "insight_report.md"


def load_config():
    """加载API配置"""
    config = {}
    exec((CLUSTER / "api_config.py").read_text(), config)
    return config


def extract_recent_knowledge(n: int = 30) -> list[dict]:
    """从海马体提取最近N条有价值的外部知识"""
    with open(HIPPOCAMPUS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chains = data.get('causal_chains', [])
    nodes = data.get('nodes', {})

    knowledge_items = []

    # 从causal_chains提取有内容的外部知识
    for c in chains:
        cause = str(c.get('cause', ''))
        effect = str(c.get('effect', ''))
        context = str(c.get('context', ''))
        source = str(c.get('source', ''))

        # 筛选有实际知识内容的链
        is_external = any(kw in cause for kw in ['外部知识', '外部世界'])
        is_business = '业务频道' in context or 'fdm_' in source
        is_deep = any(kw in cause + effect for kw in [
            '量子', '合成生物', '脑机', '混沌', '博弈', '热力',
            '信息论', '分布', 'AlphaFold', '因果', '零信任',
            '涌现', '进化', '神经', '协同', '共识'
        ])

        if (is_external or is_business) and len(effect) > 50:
            knowledge_items.append({
                'question': cause[:200],
                'answer': effect[:300],
                'source': source or context[:50],
                'tags': c.get('tags', [])
            })
        elif is_deep and len(cause) > 30 and '规则执行' not in cause:
            knowledge_items.append({
                'question': cause[:200],
                'answer': effect[:300],
                'source': source,
                'tags': c.get('tags', [])
            })

    # 从nodes提取外部世界知识
    for nid, node in nodes.items():
        content = str(node.get('内容', ''))
        typ = node.get('类型', '')
        if '外部世界' in content and len(content) > 50:
            # 解析 cause → effect 格式
            if ' → ' in content:
                parts = content.split(' → ', 1)
                question = parts[0].strip()
                answer = parts[1].strip()[:300]
            else:
                question = content[:100]
                answer = content[:300]
            knowledge_items.append({
                'question': question,
                'answer': answer,
                'source': f'node:{typ}',
                'tags': node.get('标签', [])
            })

    # 去重（基于问题文本）
    seen = set()
    unique = []
    for item in knowledge_items:
        key = item['question'][:50]
        if key not in seen:
            seen.add(key)
            unique.append(item)

    # 取最近N条
    return unique[-n:]


def cross_domain_analysis(knowledge_items: list[dict], config: dict) -> str:
    """调用API做跨域交叉分析"""
    # 构建知识摘要（控制在300字以内）
    summaries = []
    for i, item in enumerate(knowledge_items):
        q = item['question'][:60]
        summaries.append(f"{i+1}.{q}")
    knowledge_text = '\n'.join(summaries[:15])  # 最多15条

    prompt = f"""基于真元集群海马体中的{len(knowledge_items)}条跨域知识，做交叉分析。

知识摘要:
{knowledge_text}

认知模式参考:
1.世界模型:预测+反馈形成认知闭环
2.因果推理:超越相关掌握因果结构
3.最小基因:精简核心保留可进化性

请返回3个跨域洞察(每个:主题8字+内容80字+行动建议50字),纯JSON数组返回。"""

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {config['API_KEY']}"}
    payload = {
        "model": config.get('MODEL', 'deepseek-v4-pro'),
        "messages": [
            {"role": "system", "content": "你是跨域知识分析专家。只返回JSON数组，不要解释。"},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 4000,
        "temperature": 0.6
    }

    try:
        r = requests.post(
            f"{config['API_BASE']}/chat/completions",
            headers=headers,
            json=payload,
            timeout=180
        )
        result = r.json()
        msg = result.get('choices', [{}])[0].get('message', {})

        content = msg.get('content', '')
        reasoning = msg.get('reasoning_content', '')

        # 解码双编码问题
        if content:
            try:
                content = content.encode('latin-1').decode('utf-8')
            except:
                pass
        if reasoning and not content:
            try:
                reasoning = reasoning.encode('latin-1').decode('utf-8')
            except:
                pass
            # 从reasoning中提取JSON
            import re
            json_match = re.search(r'\[\s*\{.*?\}\s*\]', reasoning, re.DOTALL)
            if json_match:
                content = json_match.group()

        return content or reasoning or ""
    except Exception as e:
        return f"API调用失败: {e}"


def write_to_hippocampus(insights: list[dict], config: dict) -> int:
    """将洞察结果写入海马体"""
    with open(HIPPOCAMPUS_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    chains = data.get('causal_chains', [])
    initial_count = len(chains)

    # 添加新的洞察链
    for insight in insights:
        new_chain = {
            "id": f"insight-{int(time.time()*1000)}-{len(chains)}",
            "cause": f"[洞察引擎·跨域融合] {insight.get('name', '未知主题')}",
            "effect": insight.get('insight', insight.get('content', '')),
            "context": f"行动建议: {insight.get('action', insight.get('value', ''))}",
            "tags": ["insight_engine", "cross_domain", "cognitive_fusion"],
            "timestamp": datetime.now().isoformat(),
            "confidence": 0.85,
            "source": "insight_engine"
        }
        chains.append(new_chain)

    data['causal_chains'] = chains

    # 更新统计
    if 'stats' in data:
        data['stats']['total_writes'] = data['stats'].get('total_writes', 0) + len(insights)
        data['stats']['last_write'] = datetime.now().isoformat()

    with open(HIPPOCAMPUS_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return len(chains) - initial_count


def generate_report(
    knowledge_count: int,
    insights: list[dict],
    chains_added: int,
    api_response: str,
    elapsed: float
) -> str:
    """生成可读的洞察报告"""
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    report = f"""# 真元集群·洞察引擎报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
生成时间: {now}
知识输入: {knowledge_count}条外部知识
新增链条: {chains_added}条
API耗时: {elapsed:.1f}秒

## 认知融合结果
"""

    for i, insight in enumerate(insights):
        name = insight.get('name', insight.get('主题', f'洞察{i+1}'))
        content = insight.get('insight', insight.get('content', ''))
        action = insight.get('action', insight.get('value', insight.get('application', '')))
        report += f"""
### 洞察{i+1}: {name}
- **洞察**: {content}
- **行动**: {action}
"""

    report += f"""
## 技术细节
- 数据源: hippocampus_memory.json
- API: deepseek-v4-pro
- 认知模式: 世界模型 + 因果推理 + 最小基因
- 海马体链增长: {chains_added}

## 下一步建议
1. 将洞察结果接入neuron_daemon的决策循环
2. 定时执行insight_engine.py形成持续认知进化
3. 对重复主题进行去重和归一化处理
"""

    # 保存报告
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write(report)

    return report


def main():
    """主执行流程"""
    print("=" * 60)
    print("  真元集群·洞察引擎 v1.0")
    print("  跨域认知融合 + 海马体写入")
    print("=" * 60)

    # Step 1: 加载配置
    print("\n[1/5] 加载API配置...")
    config = load_config()
    print(f"  API: {config.get('API_BASE', '?')}")
    print(f"  Model: {config.get('MODEL', '?')}")

    # Step 2: 提取知识
    n = 30  # 默认值
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--once":
            n = 30  # 使用默认值
        else:
            try:
                n = int(arg)
            except ValueError:
                print(f"  警告: 无法解析参数 '{arg}'，使用默认值30")
    print(f"\n[2/5] 从海马体提取最近{n}条外部知识...")
    knowledge = extract_recent_knowledge(n)
    print(f"  提取到: {len(knowledge)}条有效知识")

    # 统计领域分布
    domains = Counter()
    for item in knowledge:
        q = item['question']
        for domain in ['量子', '合成生物', '脑机', '混沌', '博弈', '热力',
                       '信息论', '分布', 'AlphaFold', '因果', '零信任',
                       '涌现', '进化', '神经', '共识', '协同']:
            if domain in q or domain in str(item.get('answer', '')):
                domains[domain] += 1
    print(f"  领域分布: {dict(domains.most_common(8))}")

    # Step 3: API交叉分析
    print(f"\n[3/5] 调用API做跨域交叉分析...")
    start = time.time()
    api_result = cross_domain_analysis(knowledge, config)
    elapsed = time.time() - start
    print(f"  API响应 ({elapsed:.1f}s): {len(api_result)}字符")

    # 解析洞察
    insights = []
    try:
        # 尝试直接JSON解析
        insights = json.loads(api_result)
    except:
        # 从文本中提取JSON
        import re
        json_match = re.search(r'\[\s*\{.*?\}\s*\]', api_result, re.DOTALL)
        if json_match:
            try:
                insights = json.loads(json_match.group())
            except:
                pass

    if not insights:
        # 使用备用模式 - 基于知识自动生成
        print("  API解析失败，使用知识自动生成模式...")
        insights = []
        for i, item in enumerate(knowledge[:3]):
            domain = item['question'][:20]
            insights.append({
                "name": f"跨域融合{i+1}",
                "insight": f"从{domain}中提炼: {item['answer'][:80]}",
                "action": f"将{domain}的模式应用到真元集群自进化中"
            })

    print(f"  提取到: {len(insights)}个洞察")
    for p in insights:
        print(f"    • {p.get('name', '?')}: {p.get('insight', '')[:50]}...")

    # Step 3.5: 因果推理器增强洞察
    causal_enhancements = []
    try:
        from causal_reasoner import CausalReasoner
        reasoner = CausalReasoner()
        n_nodes, n_edges, n_chains = reasoner.load()
        print(f"\n[3.5/6] 因果推理器已加载: {n_nodes}节点/{n_edges}边/{n_chains}链")
        for insight in insights:
            try:
                enhanced = reasoner.integrate(insight)
                causal_enhancements.append(enhanced)
                n_links = enhanced.get('causal_links_found', 0)
                kws = enhanced.get('matched_keywords', [])
                print(f"    • {insight.get('name', '?')}: {n_links}条因果链, 关键词={kws[:3]}")
            except Exception as e:
                print(f"    ✗ {insight.get('name', '?')}: integrate失败: {e}")
        print(f"  因果增强完成: {len(causal_enhancements)}/{len(insights)}")
    except Exception as e:
        print(f"  ⚠ 因果推理器加载失败: {e}, 跳过因果增强")

    # Step 4: 写入海马体
    print(f"\n[4/5] 将洞察写入海马体...")
    chains_added = write_to_hippocampus(insights, config)
    print(f"  新增链条: +{chains_added}")

    # 读取总链数
    with open(HIPPOCAMPUS_PATH, 'r') as f:
        data = json.load(f)
    total_chains = len(data.get('causal_chains', []))
    print(f"  海马体总链: {total_chains}")

    # Step 4.5: 执行3条认知内化规则
    print(f"\n[4.5/6] 执行认知内化规则...")
    rule_results = {}
    for rule_name, rule_file in [
        ("对抗熵增", "rule_entropy_decay"),
        ("涌现因果", "rule_causal_extract"),
        ("信任降维", "rule_trust_score"),
    ]:
        try:
            import subprocess
            rule_path = CLUSTER / "rules" / f"{rule_file}.py"
            if rule_path.exists():
                r = subprocess.run(
                    [sys.executable, str(rule_path)],
                    capture_output=True, text=True, timeout=120,
                    cwd=str(CLUSTER)
                )
                # Parse JSON output (first line(s) before "✓ 规则...")
                stdout = r.stdout.strip()
                json_end = stdout.rfind("}")
                if json_end > 0:
                    json_str = stdout[:json_end + 1]
                    try:
                        rule_result = json.loads(json_str)
                        action = rule_result.get("action", "完成")
                        print(f"  ✓ {rule_name}: {action}")
                        rule_results[rule_name] = action
                    except:
                        print(f"  ✓ {rule_name}: 执行完毕 (解析跳过)")
                        rule_results[rule_name] = "执行完毕"
                else:
                    print(f"  ✓ {rule_name}: 执行完毕")
                    rule_results[rule_name] = "执行完毕"
            else:
                print(f"  ⚠ {rule_name}: 规则文件不存在")
                rule_results[rule_name] = "文件不存在"
        except Exception as e:
            print(f"  ✗ {rule_name}: {str(e)[:60]}")
            rule_results[rule_name] = f"失败: {str(e)[:40]}"

    # 重新读取海马体链数（规则可能修改了）
    with open(HIPPOCAMPUS_PATH, 'r') as f:
        data = json.load(f)
    total_chains = len(data.get('causal_chains', []))
    print(f"  规则执行后海马体链: {total_chains}")

    # Step 5: 生成报告
    print(f"\n[5/6] 生成洞察报告...")
    report = generate_report(knowledge_count=len(knowledge), insights=insights,
                            chains_added=chains_added, api_response=api_result[:500],
                            elapsed=elapsed)

    # 追加因果增强报告到文件
    if causal_enhancements:
        causal_report = "\n## 因果推理增强\n"
        for i, ce in enumerate(causal_enhancements):
            orig = ce.get('original_insight', {})
            name = orig.get('name', orig.get('主题', f'洞察{i+1}'))
            kws = ce.get('matched_keywords', [])
            n_links = ce.get('causal_links_found', 0)
            enhanced = ce.get('enhanced_explanation', '')
            causal_report += f"\n### 洞察{i+1}: {name}\n"
            causal_report += f"- 匹配关键词: {', '.join(kws[:5])}\n"
            causal_report += f"- 因果链数: {n_links}\n"
            causal_report += f"```\n{enhanced}\n```\n"
        with open(REPORT_PATH, 'a', encoding='utf-8') as f:
            f.write(causal_report)
        print(f"  因果增强报告已追加: {REPORT_PATH}")

    print(f"  报告已保存: {REPORT_PATH}")

    # 输出摘要
    print("\n" + "=" * 60)
    print("  洞察引擎执行完毕")
    print(f"  知识输入: {len(knowledge)}条")
    print(f"  跨域洞察: {len(insights)}个")
    print(f"  因果增强: {len(causal_enhancements)}个")
    print(f"  海马体链: {total_chains}")
    print(f"  新增: +{chains_added}链")
    print("=" * 60)

    return {
        'knowledge_count': len(knowledge),
        'insights': len(insights),
        'causal_enhanced': len(causal_enhancements),
        'chains_added': chains_added,
        'total_chains': total_chains,
        'elapsed': elapsed
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False))
