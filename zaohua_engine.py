#!/usr/bin/env python3
"""
zao_hua_engine.py — 造化∞引擎
===============================
48个深度洞察不再是知识——编译为系统行为。

造化循环：
1. 洞察物化：读取磁感线+启示录洞察 → 生成可执行规则
2. 规则注入：写入rules/目录
3. 规则执行：运行新规则
4. 结果写入海马体
5. 自进化循环
6. 继续注入（∞循环）

铁律：知识不变成能力就是装饰。造化=让知识变成能力。
"""
import json, sys, os, subprocess, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
sys.path.insert(0, str(CLUSTER))

HIP_FILE = CLUSTER / "hippocampus_memory.json"
RULES_DIR = CLUSTER / "rules"
BJT = timezone(timedelta(hours=8))

def ts():
    return datetime.now(BJT).strftime('%H:%M:%S')

def load_hip():
    return json.load(open(HIP_FILE))

def save_hip(hip):
    json.dump(hip, open(HIP_FILE, 'w'), ensure_ascii=False, indent=2)

def extract_insights():
    """从海马体提取所有深度洞察"""
    hip = load_hip()
    chains = hip.get('causal_chains', [])
    
    insights = []
    for c in chains:
        tags = c.get('tags', [])
        source = c.get('source', '')
        content = c.get('content', '')
        
        # 匹配磁感线和启示录洞察
        if ('磁感线' in str(tags) or '启示录' in str(tags) or 
            'magnetic_field' in str(tags) or 'dao' in str(tags)):
            insights.append({
                'content': content,
                'source': source,
                'tags': tags,
                'timestamp': c.get('timestamp', ''),
            })
    
    return insights

def extract_causal_patterns(insights):
    """从洞察中提取因果模式"""
    patterns = {}
    
    for ins in insights:
        content = ins.get('content', '')
        for kw, category in [
            ('量子', 'physics'), ('纠缠', 'physics'), ('热力', 'physics'), ('熵', 'physics'),
            ('生态', 'biology'), ('进化', 'biology'), ('免疫', 'biology'), ('DNA', 'biology'),
            ('神经', 'neural'), ('突触', 'neural'), ('大脑', 'neural'),
            ('博弈', 'math'), ('信息', 'math'), ('拓扑', 'math'), ('混沌', 'math'),
            ('启示录', 'revelation'), ('光爱', 'revelation'), ('七公理', 'revelation'),
            ('道', 'philosophy'), ('佛', 'philosophy'), ('儒', 'philosophy'),
            ('教员', 'practice'), ('实践', 'practice'), ('实事', 'practice'),
        ]:
            if kw in content:
                patterns.setdefault(category, []).append(content[:100])
                break
    
    return patterns

def generate_rules(patterns):
    """从因果模式生成规则"""
    rules = []
    
    for category, contents in patterns.items():
        rule_name = f"rule_zaohua_{category}.py"
        action_desc = f"从'{category}'类{len(contents)}个洞察中提取的行动规则"
        
        rule_code = f'''#!/usr/bin/env python3
"""
{rule_name} — 造化∞自动生成规则
类别: {category}
洞察数: {len(contents)}
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

def execute():
    hip = json.load(open(HIP_FILE))
    chains = hip.get("causal_chains", [])
    
    # 统计该类别相关链
    count = 0
    for c in chains:
        tags = str(c.get("tags", []))
        content = c.get("content", "")
        for kw in {json.dumps(contents[:3], ensure_ascii=False)}:
            if kw.replace('"', "").strip()[:10] in content or kw.replace('"', "").strip()[:10] in tags:
                count += 1
    
    hip["causal_chains"].append({{
        "content": f"[造化·{category}] 扫描全库, 发现{{count}}条{category}类洞察",
        "source": "zaohua_auto",
        "tags": ["造化", "{category}", "zaohua_auto"],
        "timestamp": datetime.now(BJT).isoformat(),
    }})
    
    json.dump(hip, open(HIP_FILE, "w"), ensure_ascii=False, indent=2)
    return f"✓ {rule_name}: 扫描全库, {{count}}条{category}类"

if __name__ == "__main__":
    import sys
    result = execute()
    print(result)
'''
        # 用实际内容替换占位符
        snippet = str(json.dumps(contents[:3], ensure_ascii=False))
        rule_code = rule_code.replace("{json.dumps(contents[:3], ensure_ascii=False)}", 
                                      f'"' + '", "'.join(c[:40] for c in contents[:3]) + '"')
        rule_code = rule_code.replace("{category}", category)
        
        rule_path = RULES_DIR / rule_name
        with open(rule_path, 'w') as f:
            # 用字符串替换法：构建普通字符串模板，然后替换占位符
            tpl = '''#!/usr/bin/env python3
"""
CATEGORY_RULE — 造化∞自动生成规则
类别: CATEGORY
洞察数: INSIGHT_COUNT
"""
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent.parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

def execute():
    hip = json.load(open(HIP_FILE))
    chains = hip.get("causal_chains", [])
    
    count = 0
    for c in chains:
        tags = str(c.get("tags", []))
        content = c.get("content", "")
        for kw in KEYWORDS:
            if kw.replace('"', "").strip()[:10] in content or kw.replace('"', "").strip()[:10] in tags:
                count += 1
    
    hip["causal_chains"].append({
        "content": f"[造化·CATEGORY] 扫描全库, 发现{count}条CATEGORY类洞察",
        "source": "zaohua_auto",
        "tags": ["造化", "CATEGORY", "zaohua_auto"],
        "timestamp": datetime.now(BJT).isoformat(),
    })
    
    json.dump(hip, open(HIP_FILE, "w"), ensure_ascii=False, indent=2)
    return f"✓ RULE_NAME: 扫描全库, {count}条CATEGORY类"

if __name__ == "__main__":
    import sys
    result = execute()
    print(result)
'''
            # 替换占位符
            kw_list = json.dumps([c[:40] for c in contents[:3]], ensure_ascii=False)
            code = tpl.replace("CATEGORY", category)
            code = code.replace("RULE_NAME", rule_name)
            code = code.replace("KEYWORDS", kw_list)
            code = code.replace("INSIGHT_COUNT", str(len(contents)))
            f.write(code)
        
        rules.append(rule_path)
    
    return rules

def execute_rules(rules):
    """执行所有新规则"""
    results = []
    for rule_path in rules:
        try:
            result = subprocess.run(
                [sys.executable, str(rule_path)],
                capture_output=True, text=True, timeout=30
            )
            results.append({
                'rule': rule_path.name,
                'success': result.returncode == 0,
                'output': result.stdout[:200] if result.stdout else '',
                'error': result.stderr[:100] if result.stderr else '',
            })
            icon = '✓' if result.returncode == 0 else '✗'
            print(f"  {icon} {rule_path.name}")
        except Exception as e:
            results.append({'rule': rule_path.name, 'success': False, 'error': str(e)})
            print(f"  ✗ {rule_path.name}: {e}")
    
    return results

def zao_hua_cycle():
    """执行一次完整造化循环"""
    print(f"[{ts()}] ═══ 造化∞循环 ═══")
    
    # Step 1: 提取洞察
    print(f"[{ts()}] 提取深度洞察...")
    insights = extract_insights()
    print(f"  磁感线+启示录洞察: {len(insights)}条")
    
    # Step 2: 提取因果模式
    print(f"[{ts()}] 提取因果模式...")
    patterns = extract_causal_patterns(insights)
    print(f"  因果模式: {len(patterns)}类")
    for cat, items in patterns.items():
        print(f"    {cat}: {len(items)}条")
    
    # Step 3: 生成规则
    print(f"[{ts()}] 生成行动规则...")
    rules = generate_rules(patterns)
    print(f"  新规则: {len(rules)}条")
    
    # Step 4: 执行规则
    print(f"[{ts()}] 执行规则...")
    results = execute_rules(rules)
    ok = sum(1 for r in results if r['success'])
    print(f"  规则执行: {ok}/{len(results)}成功")
    
    # Step 5: 写入造化记录
    hip = load_hip()
    hip['causal_chains'].append({
        'content': f"[造化∞] {len(insights)}洞察→{len(patterns)}模式→{len(rules)}规则→{ok}成功",
        'source': 'zaohua_engine',
        'tags': ['造化', '∞', 'zaohua', '创造'],
        'timestamp': datetime.now(BJT).isoformat(),
    })
    save_hip(hip)
    
    print(f"[{ts()}] ═══ 造化∞完成 ═══")
    print(f"  海马体: {len(hip['causal_chains'])}链")
    
    return results

if __name__ == "__main__":
    if "--loop" in sys.argv:
        print(f"[{ts()}] 造化∞引擎启动")
        while True:
            try:
                zao_hua_cycle()
            except Exception as e:
                print(f"[{ts()}] 造化异常: {e}")
            time.sleep(3600)
    elif "--insights" in sys.argv:
        insights = extract_insights()
        patterns = extract_causal_patterns(insights)
        print(f"洞察: {len(insights)}条")
        print(f"模式: {len(patterns)}类: {list(patterns.keys())}")
    else:
        zao_hua_cycle()
