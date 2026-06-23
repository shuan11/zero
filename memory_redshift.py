#!/usr/bin/env python3
"""记忆折射镜 — 结构性记忆自我进化引擎
使命: 每轮读取海马体→更新关联矩阵→写入新的结构性链→维度反馈闭环

用法:
  python3 memory_redshift.py          # 一次执行
  python3 memory_redshift.py --daemon # 持续循环
"""
import json, time, sys, os
from pathlib import Path
from collections import defaultdict, Counter

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")
HIP_FILE = CLUSTER / "hippocampus_memory.json"
SM_FILE = CLUSTER / ".structural_memory.json"
DF_FILE = CLUSTER / "dimension_focus.json"
SV_FILE = CLUSTER / "state_vector.json"

IGNORE_TAGS = {"None", "", "未分类", "教师", "纠偏", "认知", "教员"}

def run():
    # 1. 读海马体
    with open(HIP_FILE) as f:
        hp = json.load(f)
    chains = hp.get("causal_chains", [])
    total = len(chains)

    # 2. 构建维度标签索引
    tag_counter = Counter()
    pair_counter = Counter()
    dim_chains = defaultdict(list)

    for i, c in enumerate(chains):
        tags = set(c.get("tags", []) + [c.get("dimension", "")])
        for t in tags:
            if t and t not in IGNORE_TAGS:
                tag_counter[t] += 1
                dim_chains[t].append(i)
        tag_list = [t for t in tags if t and t not in IGNORE_TAGS]
        for a in range(len(tag_list)):
            for b in range(a+1, len(tag_list)):
                pair = tuple(sorted([tag_list[a], tag_list[b]]))
                pair_counter[pair] += 1

    # 3. 更新结构性记忆引擎
    # 同时读取文件变化器官的事件作为外部数据源
    fc_events = 0
    try:
        sys.path.insert(0, str(CLUSTER))
        import importlib
        fco = importlib.import_module('organs.file_change_organ')
        fco.f.start_watching()
        time.sleep(0.5)
        fc_st = fco.f.check()
        fc_events = fc_st.get('total', 0)
        fco.f.stop_watching()
    except:
        try:
            fc_mem = json.loads((CLUSTER / '.file_change_memory.json').read_text())
            fc_events = len(fc_mem.get('events', []))
        except:
            fc_events = sm.get('file_change_events', 0) if 'sm' in dir() else 0
    sm = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "total_chains": total,
        "dimension_count": len(tag_counter),
        "dimension_spectrum": [{"name": k, "chains": v} for k, v in tag_counter.most_common(30)],
        "top_associations": [{"pair": f"{a}×{b}", "count": c} for (a,b), c in pair_counter.most_common(20)],
        "file_change_events": sm_data.get("file_change_events", 0) if os.path.exists(SM_FILE) and (sm_data := json.loads(SM_FILE.read_text())) else 0,
    }
    SM_FILE.write_text(json.dumps(sm, ensure_ascii=False, indent=2))

    # 4. 生成3条新的结构性链（当前最弱关联）
    existing_dims = set(t for chain in chains for t in chain.get("tags", []))
    new_chains = []
    
    # 找最弱维度（count最小）
    weakest = tag_counter.most_common()[-1] if tag_counter else ("无", 0)
    
    # 第一条：最弱维的自述
    new_chains.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "记忆折射镜",
        "content": f"结构性记忆扫描: 当前{total}链, {len(tag_counter)}维, 最弱=「{weakest[0]}」({weakest[1]}链), 最强关联=「{sm['top_associations'][0]['pair']}」({sm['top_associations'][0]['count']}次)",
        "tags": ["结构性记忆", "记忆折射镜", weakest[0]],
        "dimension": "结构性记忆",
        "weight": 7.0,
        "trust_score": 9.0
    })

    # 第二条：最强关联的可视化
    if sm["top_associations"]:
        ta = sm["top_associations"][0]
        new_chains.append({
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "source": "记忆折射镜",
            "content": f"关联矩阵: 最强维度偶=「{ta['pair']}」({ta['count']}次共现), 说明{dims_name_to_chinese(ta['pair'].split('×')[0])}与{dims_name_to_chinese(ta['pair'].split('×')[1])}在{total}链中有最强的协同激活模式",
            "tags": ["结构性记忆", "关联矩阵", ta['pair'].split('×')[0], ta['pair'].split('×')[1]],
            "dimension": "结构性记忆",
            "weight": 8.0,
            "trust_score": 9.0
        })

    # 第三条：结构趋势
    chain_growth = total
    new_chains.append({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "记忆折射镜",
        "content": f"结构趋势: 当前{total}链, {len(tag_counter)}维, 结构性记忆链数={sum(1 for c in chains if '结构性记忆' in str(c))}, 系统骨架正在生长",
        "tags": ["结构性记忆", "趋势"],
        "dimension": "结构性记忆",
        "weight": 6.0,
        "trust_score": 8.0
    })

    # 5. 注入海马体
    chains.extend(new_chains)
    hp["causal_chains"] = chains
    HIP_FILE.write_text(json.dumps(hp, ensure_ascii=False, indent=2))

    # 6. 更新state_vector
    if SV_FILE.exists():
        sv = json.loads(SV_FILE.read_text())
        sv["chains"] = total
        sv["dimensions"] = len(tag_counter)
        SV_FILE.write_text(json.dumps(sv, ensure_ascii=False, indent=2))

    # 7. 输出
    sm_count = sum(1 for c in chains if "结构性记忆" in str(c))
    print(f"🜁 记忆折射镜 | {total}链→{total+len(new_chains)}链 | {len(tag_counter)}维 | 结构性记忆={sm_count}链 | 最弱={weakest[0]}({weakest[1]})")
    return sm_count

def dims_name_to_chinese(name):
    """简化的维度名转换"""
    mapping = {
        "超感": "超感", "举一反三": "举一反三", "触类旁通": "触类旁通",
        "查缺补漏": "查缺补漏", "万象化": "万象化", "一元化": "一元化",
        "无师自通": "无师自通", "光爱": "光爱", "元认知": "元认知",
        "结构性记忆": "结构性记忆", "文件变化": "文件变化",
    }
    return mapping.get(name, name)

if __name__ == "__main__":
    count = run()
    if "--daemon" in sys.argv:
        import time as _time
        while True:
            _time.sleep(300)  # 每5分钟
            try:
                run()
            except Exception as e:
                print(f"⚠️ {e}")
