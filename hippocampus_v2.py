#!/usr/bin/env python3
"""
hippocampus_v2.py — 零·海马体v2 读写接口
==========================================
干净的、编码安全的、原子写入的海马体操作接口。

核心原则:
  - 所有读写通过此模块
  - 永远使用纯英文键名
  - 永远使用UTF-8编码
  - 原子写入 (tmp + rename)
  - 所有旧数据只读不删

用法:
  from hippocampus_v2 import load, save, add_chain, add_node, add_relation
"""

import json, os, time
from pathlib import Path
from datetime import datetime, timezone, timedelta

CLUSTER = Path(__file__).resolve().parent
HIP_FILE = CLUSTER / "hippocampus_memory.json"
ARCHIVE_FILE = HIP_FILE.with_name("hippocampus_memory_v1.archive.json")
BJT = timezone(timedelta(hours=8))


def _now():
    return datetime.now(BJT).isoformat()


def load():
    """安全加载海马体，不存在则初始化"""
    if not HIP_FILE.exists():
        return _new()
    try:
        data = json.loads(HIP_FILE.read_text(encoding="utf-8"))
        # Validate structure
        if not isinstance(data, dict):
            return _new()
        for key in ["nodes", "relations", "causal_chains", "memories"]:
            if key not in data:
                data[key] = {} if key == "nodes" else []
        return data
    except (json.JSONDecodeError, UnicodeDecodeError):
        # Corrupted — rebuild from archive or start fresh
        return _new()


def _new():
    """创建新海马体骨架"""
    return {
        "nodes": {},
        "relations": [],
        "causal_chains": [],
        "memories": [],
        "stats": {
            "created": _now(),
            "version": "v2",
            "note": "hippocampus_v2.py interface"
        }
    }


def save(hip):
    """原子写入海马体"""
    tmp = HIP_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(hip, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(HIP_FILE))
    return True


# ─── 节点操作 ───

def add_node(hip, node_id, node_data):
    """添加或更新节点，node_data必须全部使用英文键名"""
    hip["nodes"][node_id] = node_data
    return hip


def get_node(hip, node_id):
    return hip["nodes"].get(node_id)


# ─── 关系操作 ───

def add_relation(hip, source_id, target_id, rel_type, strength=0.5, context=""):
    """添加关系边"""
    rel = {
        "from": source_id,
        "to": target_id,
        "type": rel_type,
        "strength": strength,
        "timestamp": _now(),
    }
    if context:
        rel["context"] = context
    hip["relations"].append(rel)
    return hip


# ─── 因果链操作 ───

def add_chain(hip, content, source, tags=None, extra=None):
    """添加因果链条目"""
    chain = {
        "content": content,
        "source": source,
        "tags": tags or [],
        "timestamp": _now(),
    }
    if extra:
        chain.update(extra)
    hip["causal_chains"].append(chain)
    return hip


# ─── 记忆操作 ───

def add_memory(hip, memory_dict):
    """添加系统记忆"""
    memory_dict["timestamp"] = memory_dict.get("timestamp", _now())
    hip["memories"].append(memory_dict)
    return hip


# ─── 统计 ───

def update_stats(hip):
    """更新统计信息"""
    hip["stats"] = {
        "updated": _now(),
        "version": "v2",
        "nodes": len(hip["nodes"]),
        "relations": len(hip["relations"]),
        "chains": len(hip["causal_chains"]),
        "memories": len(hip["memories"]),
    }
    return hip


# ─── 旧数据迁移工具 ───

def migrate_from_archive(hip, source_name, max_items=None):
    """
    从_v1.archive.json迁移特定来源的因果链到当前海马体
    返回迁移数量
    """
    if not ARCHIVE_FILE.exists():
        return 0
    
    old = json.loads(ARCHIVE_FILE.read_text(encoding="utf-8"))
    old_chains = old.get("causal_chains", [])
    
    migrated = 0
    for c in old_chains:
        if not isinstance(c, dict):
            continue
        src = c.get("source", "")
        if src != source_name:
            continue
        
        content = c.get("content", "")
        # Fix double encoding if needed
        fixed = _fix_encoding(content)
        has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in fixed)
        
        if has_chinese or len(fixed) > 20:
            new_chain = {
                "content": fixed,
                "source": src,
                "tags": c.get("tags", []),
                "timestamp": c.get("timestamp", c.get("time", _now())),
            }
            # Copy confidence fields if exist
            for k in ["confidence", "trust_score", "entropy_score"]:
                if k in c:
                    new_chain[k] = c[k]
            hip["causal_chains"].append(new_chain)
            migrated += 1
            if max_items and migrated >= max_items:
                break
    
    return migrated


def _fix_encoding(s):
    """尝试修复double-encoded UTF-8字符串"""
    if not isinstance(s, str):
        return str(s)
    try:
        encoded = s.encode("latin-1")
        decoded = encoded.decode("utf-8")
        if any("\u4e00" <= c <= "\u9fff" for c in decoded):
            return decoded
    except:
        pass
    return s


# ─── 自检 ───

def health_check():
    """海马体健康检查"""
    hip = load()
    checks = []
    
    # 顶层键纯英文
    garbled = [k for k in hip if not k.isascii()]
    checks.append(("顶层键纯净", len(garbled) == 0, f"{len(garbled)}个非ASCII键" if garbled else "OK"))
    
    # 节点键名
    node_garbled = 0
    for nid, n in hip.get("nodes", {}).items():
        if isinstance(n, dict):
            for k in n:
                if not k.isascii():
                    node_garbled += 1
                    break
    checks.append(("节点键名纯净", node_garbled == 0, f"{node_garbled}个含非ASCII" if node_garbled else "OK"))
    
    # 关系键名
    rel_garbled = 0
    for r in hip.get("relations", []):
        if isinstance(r, dict):
            for k in r:
                if not k.isascii():
                    rel_garbled += 1
                    break
    checks.append(("关系键名纯净", rel_garbled == 0, f"{rel_garbled}个含非ASCII" if rel_garbled else "OK"))
    
    # 一致性
    nodes = hip.get("nodes", {})
    rels = hip.get("relations", [])
    dangling = 0
    for r in rels:
        if isinstance(r, dict):
            src = r.get("from", "")
            tgt = r.get("to", "")
            if src and src not in nodes:
                dangling += 1
            if tgt and tgt not in nodes:
                dangling += 1
    checks.append(("关系一致性", dangling == 0, f"{dangling}条悬挂关系" if dangling else f"{len(rels)}关系/{len(nodes)}节点"))
    
    print("海马体健康检查:")
    for name, passed, detail in checks:
        icon = "✅" if passed else "⚠️"
        print(f"  {icon} {name}: {detail}")
    
    print(f"\n  总节点: {len(nodes)}")
    print(f"  总关系: {len(rels)}")
    print(f"  总链: {len(hip.get('causal_chains', []))}")
    print(f"  总记忆: {len(hip.get('memories', []))}")


if __name__ == "__main__":
    if "--check" in sys.argv:
        health_check()
    elif "--migrate" in sys.argv:
        source = sys.argv[2] if len(sys.argv) > 2 else None
        max_n = int(sys.argv[3]) if len(sys.argv) > 3 else None
        hip = load()
        if source:
            n = migrate_from_archive(hip, source, max_n)
            save(hip)
            print(f"迁移 {source}: {n}条")
        else:
            print("需指定source名称")
    else:
        hip = load()
        print(f"海马体v2: {len(hip['nodes'])}节点 {len(hip['relations'])}关系 {len(hip['causal_chains'])}链")
