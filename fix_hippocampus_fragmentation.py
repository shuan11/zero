#!/usr/bin/env python3
"""
fix_hippocampus_fragmentation.py — 海马体碎片化修复
====================================================
诊断出的问题:
1. causal_reasoning_enhancer 反馈循环: 23,399条链(97.9%)来自单一源
2. 节点只是关键词桩(count/first_seen)，无真实内容
3. relations=0, memories=0 完全空
4. 链内容污染: 100%含"→"和"因果提取"标签

修复:
1. 归档噪声链 → 保留摘要
2. 给enhancer加限流
3. 重建节点提取
4. 打通relations/memories通道
"""
import json, os, time, sys, subprocess
from pathlib import Path
from datetime import datetime, timezone
import safe_hip

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
BJT = timezone(timedelta(hours=8))

def now():
    return datetime.now(BJT).isoformat()

def load():
    with open(HIP_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save(hip):
    tmp = HIP_FILE.with_suffix(".json.fix_tmp")
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(hip, f, ensure_ascii=False, indent=2)
    os.replace(str(tmp), str(HIP_FILE))

def backup(hip):
    """备份当前状态"""
    bak = CLUSTER / f"hippocampus_pre_fix_{datetime.now(BJT).strftime('%Y%m%d_%H%M%S')}.json"
    save_data = {
        "note": "Pre-fix backup - hippocampus fragmentation repair",
        "timestamp": now(),
        "original_stats": {
            "chains": len(hip.get("causal_chains", [])),
            "nodes": len(hip.get("nodes", {})),
            "relations": len(hip.get("relations", [])),
        },
        "data": hip
    }
    with open(bak, 'w', encoding='utf-8') as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ 备份到 {bak.name}")
    return bak

def archive_noise_chains(hip):
    """
    步骤1: 归档噪声链
    识别规则: source包含'causal_reasoning' 且 content包含'[因果提取]'
    替换为压缩摘要
    """
    chains = hip.get("causal_chains", [])
    total = len(chains)
    
    # 识别噪声链
    noise = []
    clean = []
    for c in chains:
        src = c.get("source", "")
        content = str(c.get("content", ""))
        if ("causal_reasoning" in src or "causal_reasoning" in src) and "[因果提取]" in content:
            noise.append(c)
        else:
            clean.append(c)
    
    print(f"  总链: {total}")
    print(f"  噪声链: {len(noise)} ({len(noise)/max(total,1)*100:.1f}%)")
    print(f"  清洁链: {len(clean)}")
    
    # 从噪声链中提取有意义的摘要
    seen_contents = set()
    unique_insights = []
    for c in noise:
        content = str(c.get("content", ""))
        # 提取[因果提取]后的实际内容
        extracted = content.replace("[因果提取]", "").strip()
        # 去重
        if extracted and extracted not in seen_contents and len(extracted) > 10:
            seen_contents.add(extracted)
            unique_insights.append(extracted)
    
    print(f"  去重后独特内容: {len(unique_insights)}条")
    
    # 只保留有意义的独特洞察（非乱码）
    real_insights = []
    for ins in unique_insights:
        # 跳过纯乱码: 只有→, 空格, 逗号组成的
        clean_text = ins.replace("→", "").replace(" ", "").replace(",", "").strip()
        if len(clean_text) > 5 and any('\u4e00' <= c <= '\u9fff' for c in clean_text):
            real_insights.append(ins)
    
    print(f"  有实际意义的洞察: {len(real_insights)}条")
    
    # 创建压缩摘要链
    summary = {
        "content": f"[自动归档] causal_reasoning_enhancer的{len(noise)}条噪声链被压缩为{len(real_insights)}条独特洞察。原始链已被移至归档。",
        "source": "hippocampus_fix",
        "tags": ["归档", "噪声压缩", "因果提取"],
        "timestamp": now(),
        "weight": 0.9,
    }
    
    # 添加独特洞察作为单独链
    insight_chains = []
    for i, ins in enumerate(real_insights[:50]):  # 最多保留50条
        insight_chains.append({
            "content": f"[因果洞察] {ins}",
            "source": "causal_reasoning_enhancer_archived",
            "tags": ["因果提取", "已归档"],
            "timestamp": now(),
            "weight": 0.5,
        })
    
    # 替换chains: 清洁链 + 摘要 + 洞察
    safe_hip.replace_all_chains(clean + [summary] + insight_chains)
    
    print(f"  归档后链数: {len(hip['causal_chains'])}")
    print(f"  缩减比例: {(1 - len(hip['causal_chains'])/max(total,1))*100:.1f}%")
    
    return hip, len(noise), len(real_insights)

def rebuild_nodes(hip):
    """
    步骤2: 从清洁链中提取真实节点
    之前的节点: 只是关键词桩(导致/产生/促进)，无内容
    重建后: 从chain的tags+content提取有意义的概念节点
    """
    old_nodes = hip.get("nodes", {})
    chains = hip.get("causal_chains", [])
    
    print(f"\n  旧节点: {len(old_nodes)}个")
    print(f"  旧节点列表: {list(old_nodes.keys())[:15]}")
    
    # 从链中提取概念
    concept_counter = {}
    for c in chains:
        tags = c.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if tag and len(tag) > 1:
                    concept_counter[tag] = concept_counter.get(tag, 0) + 1
        # 从content提取关键词
        content = str(c.get("content", ""))
        # 提取中文短语(2-8字)
        phrases = re.findall(r'[\u4e00-\u9fff]{2,8}', content)
        for p in phrases:
            if p not in ["因果提取", "因果洞察", "自动归档", "噪声压缩"]:
                concept_counter[p] = concept_counter.get(p, 0) + 1
    
    # 过滤有意义的概念 (至少出现2次)
    meaningful = {k: v for k, v in concept_counter.items() if v >= 2}
    
    # 构建新节点
    new_nodes = {}
    for i, (concept, count) in enumerate(sorted(meaningful.items(), key=lambda x: -x[1])[:200]):
        new_nodes[concept] = {
            "count": count,
            "first_seen": now(),
            "tag": concept,
            "dimension": "auto_extracted",
        }
    
    # 保留旧的relation类型节点(导致/产生/促进等)但标记为type节点
    for nid, ndata in old_nodes.items():
        if nid not in new_nodes and nid in ["导致", "产生", "促进", "触发", "推动", "引起", "造成", "因此", "所以"]:
            new_nodes[nid] = {
                "count": ndata.get("count", 0),
                "first_seen": ndata.get("first_seen", now()),
                "tag": nid,
                "dimension": "relation_keyword",
                "type": "causal_relation",
            }
    
    hip["nodes"] = new_nodes
    print(f"  新节点: {len(new_nodes)}个")
    print(f"  新节点示例: {list(new_nodes.keys())[:20]}")
    
    return hip

def build_relations(hip):
    """
    步骤3: 从链中建立relations
    之前的relations: 空[]
    重建后: 从相同source/相同tags的链之间建立关系
    """
    chains = hip.get("causal_chains", [])
    nodes = hip.get("nodes", {})
    
    relations = []
    
    # 方法1: 同source链之间建立时序关系
    source_groups = {}
    for i, c in enumerate(chains):
        src = c.get("source", "unknown")
        source_groups.setdefault(src, []).append(i)
    
    for src, indices in source_groups.items():
        if len(indices) >= 2:
            # 相邻链之间建立时序关系
            for j in range(len(indices)-1):
                c1 = chains[indices[j]]
                c2 = chains[indices[j+1]]
                rel = {
                    "from": f"chain_{indices[j]}",
                    "to": f"chain_{indices[j+1]}",
                    "type": "temporal_sequence",
                    "strength": 0.3,
                    "context": f"同source({src})的时序延续",
                    "timestamp": now(),
                }
                relations.append(rel)
    
    # 方法2: 共享tag的链之间建立关联
    tag_chains = {}
    for i, c in enumerate(chains):
        tags = c.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if tag in nodes:
                    tag_chains.setdefault(tag, []).append(i)
    
    for tag, indices in tag_chains.items():
        if len(indices) >= 3:
            # 只取前几个做示例关系
            for j in range(min(3, len(indices)-1)):
                rel = {
                    "from": f"chain_{indices[0]}",
                    "to": f"chain_{indices[j+1]}",
                    "type": "shared_tag",
                    "strength": 0.5,
                    "context": f"共享tag: {tag}",
                    "timestamp": now(),
                }
                relations.append(rel)
    
    hip["relations"] = relations[:500]  # 最多500条关系
    print(f"  建立relations: {len(relations)}条 (限制500)")
    
    return hip

def build_memories(hip):
    """
    步骤4: 从有意义的链中提取memories
    之前的memories: 空[]
    """
    chains = hip.get("causal_chains", [])
    memories = []
    
    # 取高权重/有意义的链作为memories
    for i, c in enumerate(chains):
        weight = c.get("weight", c.get("confidence", 0.5))
        if isinstance(weight, (int, float)) and weight >= 0.7:
            content = str(c.get("content", ""))
            if content and len(content) > 20:
                memories.append({
                    "id": f"mem_{i}",
                    "content": content[:200],
                    "source": c.get("source", "unknown"),
                    "weight": weight,
                    "timestamp": c.get("timestamp", now()),
                })
    
    hip["memories"] = memories[:100]  # 最多100条
    print(f"  建立memories: {len(memories)}条 (限制100)")
    
    return hip

def add_throttle_to_enhancer():
    """
    步骤5: 给causal_reasoning_enhancer加限流
    修改: 只在新增链>阈值时才运行
    """
    enhancer_path = CLUSTER / "causal_reasoning_enhancer.py"
    if not enhancer_path.exists():
        print("  ⚠️ enhancer文件不存在，跳过")
        return False
    
    content = enhancer_path.read_text(encoding='utf-8')
    
    # 在第4行后插入限流逻辑
    throttle_code = """
import hashlib
# ── 限流保护: 防止反馈循环 ──
THROTTLE_THRESHOLD = 50  # 只有上次运行后新增了50+条链才执行
THROTTLE_MARKER = CLUSTER / ".causal_reasoning_last_count"
def _should_run():
    hip = safe_hip.read()
    current = len(hip.get("causal_chains", []))
    try:
        last = int(THROTTLE_MARKER.read_text().strip())
    except:
        last = current
    diff = current - last
    if diff < THROTTLE_THRESHOLD:
        print(f"[限流] 新增链({diff}) < 阈值({THROTTLE_THRESHOLD}), 跳过本次因果增强")
        print(f"[限流] 上次链数: {last}, 当前: {current}")
        return False
    # 更新标记
    THROTTLE_MARKER.write_text(str(current))
    return True
"""
    
    if "# ── 限流保护" not in content:
        lines = content.split('\n')
        # 在 import 块后, def 前插入
        insert_pos = 0
        for i, line in enumerate(lines):
            if line.startswith("def ") or line.startswith("class "):
                insert_pos = i
                break
        if insert_pos > 0:
            lines.insert(insert_pos, throttle_code)
            
            # 修改 main 入口
            new_content = '\n'.join(lines)
            new_content = new_content.replace(
                "if __name__ == \"__main__\":",
                "if __name__ == \"__main__\":\n    if not _should_run():\n        sys.exit(0)"
            )
            # 只替换第一次出现
            enhanced_path = enhancer_path
            enhanced_path.write_text(new_content, encoding='utf-8')
            print(f"  ✅ 限流已添加到 {enhancer_path.name}")
            return True
    
    print(f"  ⏭️ enhancer已有限流，跳过")
    return True

def main():
    print("=" * 60)
    print("🧠 海马体碎片化修复")
    print("=" * 60)
    
    # 加载
    print("\n📖 加载海马体...")
    hip = load()
    print(f"  加载: {len(hip.get('causal_chains',[]))}链, {len(hip.get('nodes',{}))}节点, {len(hip.get('relations',[]))}关系, {len(hip.get('memories',[]))}记忆")
    
    # 备份
    print("\n💾 备份...")
    backup(hip)
    
    # 步骤1: 归档噪声链
    print("\n📦 步骤1: 归档噪声链...")
    hip, noise_count, insight_count = archive_noise_chains(hip)
    
    # 步骤2: 重建节点
    print("\n🏷️ 步骤2: 重建节点提取...")
    hip = rebuild_nodes(hip)
    
    # 步骤3: 建立relations
    print("\n🔗 步骤3: 建立relations...")
    hip = build_relations(hip)
    
    # 步骤4: 建立memories  
    print("\n📝 步骤4: 建立memories...")
    hip = build_memories(hip)
    
    # 更新stats
    hip["stats"] = {
        "updated": now(),
        "version": "v2_fixed",
        "nodes": len(hip["nodes"]),
        "relations": len(hip["relations"]),
        "chains": len(hip["causal_chains"]),
        "memories": len(hip["memories"]),
        "chains_archived": noise_count,
        "insights_preserved": insight_count,
        "note": "碎片化修复: 归档噪声链, 重建节点, 建立relations/memories",
    }
    
    # 保存
    print("\n💾 保存修复后海马体...")
    save(hip)
    
    # 步骤5: 给enhancer加限流
    print("\n🚦 步骤5: 给causal_reasoning_enhancer加限流...")
    add_throttle_to_enhancer()
    
    print("\n" + "=" * 60)
    print(f"✅ 修复完成!")
    print(f"  链: 压缩到 {len(hip['causal_chains'])} 条 (归档 {noise_count} 条噪声)")
    print(f"  节点: {len(hip['nodes'])} 个 (从关键词桩→真概念)")
    print(f"  关系: {len(hip['relations'])} 条 (之前为0)")
    print(f"  记忆: {len(hip['memories'])} 条 (之前为0)")
    print("=" * 60)

if __name__ == "__main__":
    main()
