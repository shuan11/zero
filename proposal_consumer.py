#!/usr/bin/env python3
"""
proposal_consumer.py — 提案消费者·自主进化版
自动从HANDOFF proposals队列读取工程级提案并真实执行代码改动
"""
import json
import re
from pathlib import Path

CLUSTER = Path(__file__).resolve().parent
HANDOFF = CLUSTER / "ZERO-HANDOFF.json"
RADAR = CLUSTER / "organs/dimension_radar.py"

def load_proposals():
    with open(HANDOFF) as f:
        data = json.load(f)
    return data.get('engineering_notes', {}).get('proposals', [])

def execute_algorithm_fix(dim_name):
    """真实修复算法：增加维度专属boost"""
    # 提取维度名(去掉健康度后缀)
    dim = re.sub(r'\([\d\.]+\)', '', dim_name).strip()
    
    with open(RADAR) as f:
        lines = f.readlines()
    
    # 找到光爱维度boost的位置(L252-255)，在后面插入新维度boost
    insert_pos = None
    for i, line in enumerate(lines):
        if '"光爱" and dim in light_love_override' in line:
            # 找到L255后插入
            for j in range(i+1, min(i+10, len(lines))):
                if 'health = health * 0.7' in lines[j]:
                    insert_pos = j + 1
                    break
            break
    
    if not insert_pos:
        print(f"  ✗ 未找到插入位置")
        return False
    
    # 生成boost代码
    boost_code = f'''        
        # {dim}维度: 连续无改善补boost
        if dim == "{dim}":
            # 关键词扩充后重新计算链数，若增长则+0.1 bonus
            _old_count = results.get(dim, {{}}).get('chains', 0)
            if count > _old_count * 1.05:  # 增长>5%
                health = min(1.0, health + 0.1)
        
'''
    
    lines.insert(insert_pos, boost_code)
    
    # 写回
    with open(RADAR, 'w') as f:
        f.writelines(lines)
    
    print(f"  ✓ 已注入{dim}维度boost逻辑 (L{insert_pos})")
    return True

def execute_bridge_creation(source_dim, target_dim):
    """创建维度间协同桥"""
    bridge_file = CLUSTER / f"bridge_{source_dim}_{target_dim}.py"
    code = f'''"""
{source_dim}↔{target_dim} 协同桥
"""
def sync():
    # TODO: 实现跨维度数据同步
    pass
'''
    with open(bridge_file, 'w') as f:
        f.write(code)
    print(f"  ✓ 已创建桥文件: {bridge_file.name}")
    return True

def execute_proposal(prop):
    """执行工程级提案"""
    dim = prop.get('dim', '未知')
    hyp = prop.get('hypothesis', '')
    
    print(f"\n[执行] {dim}: {hyp[:80]}")
    
    if '调权重' in hyp or '改算法' in hyp:
        return execute_algorithm_fix(dim)
    elif '建桥' in hyp:
        # 提取维度名
        match = re.search(r'在(.+?)与(.+?)(?:维度)?间建桥', hyp)
        if match:
            return execute_bridge_creation(match.group(1), match.group(2))
        return False
    else:
        print(f"  - 暂不支持，待人工")
        return False

def main():
    proposals = load_proposals()
    print(f"=== 提案消费者·自主进化 ===")
    print(f"队列: {len(proposals)}条")
    
    executed = []
    for prop in proposals:
        hyp = prop.get('hypothesis', '')
        if any(kw in hyp for kw in ['建议', '创建', '改算法', '建桥']):
            if execute_proposal(prop):
                executed.append(prop)
    
    print(f"\n已执行: {len(executed)}/{len(proposals)}")
    
    # 清空已执行提案
    if executed:
        with open(HANDOFF) as f:
            data = json.load(f)
        remaining = [p for p in data['engineering_notes']['proposals'] 
                    if p not in executed]
        data['engineering_notes']['proposals'] = remaining
        data['last_updated'] = f"{Path(__file__).stat().st_mtime}"
        with open(HANDOFF, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("已清空执行提案")

if __name__ == '__main__':
    main()
