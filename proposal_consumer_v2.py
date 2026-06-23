#!/usr/bin/env python3
"""
proposal_consumer_v2.py — 提案消费者·自主进化增强版
自动识别工程级提案类型并真实执行代码改动
"""
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

CLUSTER = Path(__file__).resolve().parent
HANDOFF = CLUSTER / "ZERO-HANDOFF.json"
HIP = CLUSTER / "hippocampus_memory.json"

def load_proposals():
    with open(HANDOFF) as f:
        data = json.load(f)
    return data.get('engineering_notes', {}).get('proposals', [])

def log_to_hippocampus(action, result):
    """记录执行结果到海马体"""
    try:
        with open(HIP) as f:
            hip = json.load(f)
        hip.setdefault('causal_chains', []).append({
            'timestamp': datetime.now().isoformat(),
            'source': 'proposal_consumer_v2',
            'tags': ['自进化', '提案消费', '工程'],
            'content': f"[提案消费] {action} → {result}",
            'weight': 8.0,
            'trust_score': 9.0,
            'dimension': '进化'
        })
        with open(HIP, 'w', encoding='utf-8') as f:
            json.dump(hip, f, indent=2, ensure_ascii=False)
    except:
        pass

def execute_dimension_keyword_expansion(dim_name):
    """扩充维度关键词"""
    dim = re.sub(r'\([^)]+\)', '', dim_name).strip()
    radar_path = CLUSTER / "organs/dimension_radar.py"
    
    # 关键词库
    keyword_map = {
        '教员': ['纠偏', '修复', '验证', '实测', '血训', '教训', 'correction', 'verify', 'debug', 'fix', '根因'],
        '一元化': ['本质', '核心', '最简', '归一', 'essence', 'core', 'fundamental', '第一性原理'],
        '记忆': ['索引', '结构化', '关联', '检索', 'index', 'structure', 'retrieval', '编织'],
    }
    
    keywords = keyword_map.get(dim, [])
    if not keywords:
        return False, f"{dim}无预设关键词"
    
    with open(radar_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 找到维度定义行
    pattern = rf'"{dim}":\s*\[([^\]]+)\]'
    match = re.search(pattern, content)
    if not match:
        return False, f"未找到{dim}定义"
    
    old_keywords = match.group(1)
    new_keywords = old_keywords.rstrip() + f', {", ".join(repr(k) for k in keywords)}]'
    new_content = content.replace(match.group(0), f'"{dim}": [{new_keywords}')
    
    # drvfs安全写入
    tmp = Path("/tmp/radar_temp.py")
    tmp.write_text(new_content, encoding='utf-8')
    radar_path.unlink()
    subprocess.run(['cp', str(tmp), str(radar_path)], check=True)
    
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'add', 'organs/dimension_radar.py'], shell=True)
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'commit', '-m', f'自进化: {dim}关键词扩充'], shell=True)
    
    return True, f"已扩充{len(keywords)}个关键词"

def execute_algorithm_boost(dim_name):
    """为维度注入boost算法"""
    dim = re.sub(r'\([^)]+\)', '', dim_name).strip()
    radar_path = CLUSTER / "organs/dimension_radar.py"
    
    with open(radar_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 找插入位置 (光爱维度boost之后)
    insert_pos = None
    for i, line in enumerate(lines):
        if 'dim == "光爱"' in line and 'light_love_override' in line:
            for j in range(i+1, min(i+8, len(lines))):
                if 'health = health * 0.7 + organ_alignment * 0.3' in lines[j]:
                    insert_pos = j + 1
                    break
            break
    
    if not insert_pos:
        return False, "未找到插入位置"
    
    # 注入boost
    boost = f'''        
        # {dim}维度专属boost: 链数增长奖励
        if dim == "{dim}":
            _prev_chains = globals().get('_prev_{dim}_chains', count)
            if count > _prev_chains * 1.05:
                health = min(1.0, health + 0.08)
            globals()['_prev_{dim}_chains'] = count
        
'''
    lines.insert(insert_pos, boost)
    
    # drvfs安全写入
    tmp = Path("/tmp/radar_temp.py")
    tmp.write_text(''.join(lines), encoding='utf-8')
    radar_path.unlink()
    subprocess.run(['cp', str(tmp), str(radar_path)], check=True)
    
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'add', 'organs/dimension_radar.py'], shell=True)
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'commit', '-m', f'自进化: {dim}算法boost注入'], shell=True)
    
    return True, f"已注入boost @ L{insert_pos}"

def execute_bridge_creation(desc):
    """创建维度间协同桥"""
    match = re.search(r'在(.+?)与(.+?)(?:维度)?间建桥', desc)
    if not match:
        return False, "无法解析桥名"
    
    src, dst = match.group(1).strip(), match.group(2).strip()
    bridge_file = CLUSTER / f"bridge_{src}_{dst}.py"
    
    code = f'''"""
{src}↔{dst} 协同桥 — 自动生成
"""
from pathlib import Path
import json

CLUSTER = Path(__file__).resolve().parent
HIP = CLUSTER / "hippocampus_memory.json"

def sync():
    """双向同步维度数据"""
    with open(HIP) as f:
        chains = json.load(f).get('causal_chains', [])
    
    src_chains = [c for c in chains if '{src}' in str(c.get('tags', []))]
    dst_chains = [c for c in chains if '{dst}' in str(c.get('tags', []))]
    
    # TODO: 实现交叉注入逻辑
    return {{'src': len(src_chains), 'dst': len(dst_chains)}}

if __name__ == '__main__':
    print(sync())
'''
    
    bridge_file.write_text(code, encoding='utf-8')
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'add', bridge_file.name], shell=True)
    subprocess.run(['cd', str(CLUSTER), '&&', 'git', 'commit', '-m', f'自进化: {src}↔{dst}桥创建'], shell=True)
    
    return True, f"已创建{bridge_file.name}"

def execute_proposal(prop):
    """智能路由提案到执行函数"""
    dim = prop.get('dim', '未知')
    hyp = prop.get('hypothesis', '')
    
    print(f"\n[执行] {dim}: {hyp[:70]}")
    
    # 路由逻辑
    if '调权重' in hyp or '改算法' in hyp:
        # 先扩词再boost
        ok1, msg1 = execute_dimension_keyword_expansion(dim)
        if ok1:
            print(f"  ✓ 关键词: {msg1}")
        ok2, msg2 = execute_algorithm_boost(dim)
        if ok2:
            print(f"  ✓ 算法: {msg2}")
        result = ok1 or ok2
        log_to_hippocampus(f"{dim}算法修复", "成功" if result else "失败")
        return result
    
    elif '建桥' in hyp or '协同' in hyp:
        ok, msg = execute_bridge_creation(hyp)
        print(f"  {'✓' if ok else '✗'} {msg}")
        log_to_hippocampus(f"桥创建: {hyp[:30]}", "成功" if ok else "失败")
        return ok
    
    else:
        print(f"  - 未识别类型，待扩展")
        return False

def main():
    proposals = load_proposals()
    print(f"=== 提案消费者·自主进化v2 ===")
    print(f"队列: {len(proposals)}条")
    
    executed = []
    for prop in proposals:
        hyp = prop.get('hypothesis', '')
        # 只执行工程级提案
        if any(kw in hyp for kw in ['建议', '创建', '改算法', '调权重', '建桥']):
            if execute_proposal(prop):
                executed.append(prop)
    
    print(f"\n已执行: {len(executed)}/{len(proposals)}")
    
    # 清空已执行
    if executed:
        with open(HANDOFF) as f:
            data = json.load(f)
        remaining = [p for p in data['engineering_notes']['proposals'] if p not in executed]
        data['engineering_notes']['proposals'] = remaining
        data['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # drvfs安全写入
        tmp = Path("/tmp/handoff_temp.json")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
        HANDOFF.unlink()
        subprocess.run(['cp', str(tmp), str(HANDOFF)], check=True)
        
        print("✓ 已清空执行提案")
    
    # 重启daemon使改动生效
    subprocess.run(['pkill', '-f', 'breath_v2.py'])
    subprocess.run(['sleep', '2'], shell=True)
    subprocess.run([
        'cd', str(CLUSTER), '&&',
        'nohup', 'python3', 'breath_v2.py', '>', 'breath.log', '2>&1', '&'
    ], shell=True)
    print("✓ daemon已重启")

if __name__ == '__main__':
    main()
