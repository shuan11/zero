"""应用所有修复补丁"""
import json, re, tempfile, os, sys
from pathlib import Path

CLUSTER = Path("/mnt/c/Users/h/Desktop/零/真元集群")

# ============================================================
# 1. dimension_radar.py — 加 cross_dim_boost()
# ============================================================
radar = CLUSTER / "organs/dimension_radar.py"
content = radar.read_text()

new_section = '''    return f"维度{dim_name}薄弱(健康度{dim_stats['health_score']}), 建议优先补充。"


# ═══ 提案修复: 交叉维度增强（cross_dim_boost） ═══
CROSS_DIM_THRESHOLD = 10  # 低于此阈值的交叉对视为"罕见"，需增强

def cross_dim_boost():
    """扫描链间交叉维度对, 识别罕见的连接, 返回增强建议
    
    提案37条cross_dim_boost要求: 找出交叉链数不足的维度对,
    生成boost权重给breath_v2的加权选维机制使用。
    """
    try:
        hip = json.loads(HIP_FILE.read_text(encoding='utf-8'))
    except:
        return []
    chains = hip.get("causal_chains", [])
    
    pair_counts = Counter()
    dim_appearances = Counter()
    
    for c in chains:
        dims = classify_chain(c)
        if not dims or len(dims) < 2:
            continue
        sorted_dims = sorted(set(dims))
        for i in range(len(sorted_dims)):
            dim_appearances[sorted_dims[i]] += 1
            for j in range(i+1, len(sorted_dims)):
                pair = (sorted_dims[i], sorted_dims[j])
                pair_counts[pair] += 1
    
    boosts = []
    for (d1, d2), count in pair_counts.most_common():
        if count >= CROSS_DIM_THRESHOLD:
            continue
        boost_val = max(1.0, 5.0 - count * 0.5)
        boosts.append({
            "pair": f"{d1}\u00d7{d2}",
            "dim1": d1, "dim2": d2,
            "cross_chains": count,
            "boost": round(boost_val, 2),
            "reason": f"交叉链仅{count}条(<{CROSS_DIM_THRESHOLD}), 建议加权+{boost_val:.1f}",
        })
    
    boosts.sort(key=lambda x: -x["boost"])
    
    boost_file = CLUSTER / "cross_dim_boost.json"
    boost_file.write_text(json.dumps({
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "threshold": CROSS_DIM_THRESHOLD,
        "total_pairs": len(pair_counts),
        "weak_pairs": len(boosts),
        "boosts": boosts[:20],
    }, ensure_ascii=False, indent=2))
    
    return boosts


def pulse():'''

old_pulse = '''    return f"维度{dim_name}薄弱(健康度{dim_stats['health_score']}), 建议优先补充。"


def pulse():'''

if old_pulse not in content:
    print("ERROR: old_pulse not found in dimension_radar.py")
    sys.exit(1)

content = content.replace(old_pulse, new_section)

# Also update pulse() body to include cross_dim_boost
old_pulse_body = '''    try:
        result = scan_all()
        return {
            "alive": True,
            "dimensions_analyzed": len(result.get("dimensions", {})),
            "weakest": result.get("decision", {}).get("weakest_dimension", {}),
            "classified": result.get("decision", {}).get("classification_rate", "0%"),
        }'''

new_pulse_body = '''    try:
        result = scan_all()
        boosts = cross_dim_boost()
        return {
            "alive": True,
            "dimensions_analyzed": len(result.get("dimensions", {})),
            "weakest": result.get("decision", {}).get("weakest_dimension", {}),
            "classified": result.get("decision", {}).get("classification_rate", "0%"),
            "cross_dim_boosts": len(boosts),
            "top_boost": boosts[0]["pair"] if boosts else None,
        }'''

if old_pulse_body not in content:
    print("ERROR: old_pulse_body not found")
    sys.exit(1)

content = content.replace(old_pulse_body, new_pulse_body)
radar.write_text(content)
print(f"dimension_radar.py: patched OK ({radar.stat().st_size} bytes)")


# ============================================================
# 2. 自我改进.py — 加 cross_dim_self_learning 模板
# ============================================================
zimys = CLUSTER / "自我改进.py"
content2 = zimys.read_text()

# 加注册
old_register = """    applier=lambda path, context: _apply_proposal(path, context),
)"""

new_register = """    applier=lambda path, context: _apply_proposal(path, context),
)

# 模板7: 交叉维度自学 — 检测器官的弱交叉连接并注入增强
register(
    "cross_dim_self_learning",
    "检测器官与弱交叉维度的连接并注入增强代码(基于cross_dim_boost.json)",
    detector=lambda path: _detect_cross_dim_gap(path),
    applier=lambda path, context: _apply_cross_dim_learn(path, context),
)"""

content2 = content2.replace(old_register, new_register)

# 加末尾函数
new_funcs = '''
# === 模板7: 交叉维度自学 ===
CROSS_DIM_BOOST_FILE = Path("/mnt/c/Users/h/Desktop/零/真元集群") / "cross_dim_boost.json"

def _detect_cross_dim_gap(path):
    """检测当前器官的维度是否有弱交叉连接"""
    try:
        if not CROSS_DIM_BOOST_FILE.exists():
            return False
        boosts = json.loads(CROSS_DIM_BOOST_FILE.read_text()).get("boosts", [])
        if not boosts:
            return False
        
        fname = Path(path).resolve().name
        dim_hints = {
            "time": "时间论", "gradient": "时间论", "void": "宇宙轮", "entropy": "宇宙轮",
            "cosmic": "宇宙轮", "redshift": "无限上下文", "compress": "无限上下文",
            "analogy": "触类旁通", "transfer": "触类旁通", "self_improve": "无师自通",
            "repair": "无师自通", "intuition": "超级直觉", "pattern": "超级直觉",
            "deduct": "举一反三", "generalize": "举一反三", "cross": "查缺补漏",
            "gap": "查缺补漏", "meta": "一元化", "center": "一元化", "diverse": "万象化",
            "mult": "万象化", "supersense": "超感", "teacher": "教员", "verifier": "教员",
            "light": "光爱", "love": "光爱", "memory": "记忆", "hippocampus": "记忆",
            "perception": "感知", "retina": "感知", "scheduler": "进化", "evolution": "进化",
        }
        file_dim = None
        for keyword, dim in dim_hints.items():
            if keyword in fname.lower():
                file_dim = dim
                break
        if not file_dim:
            return False
        for b in boosts:
            if b.get("dim1") == file_dim or b.get("dim2") == file_dim:
                return True
        return False
    except:
        return False


def _apply_cross_dim_learn(path, context):
    """应用交叉维度学习: 注入增强注释提示"""
    try:
        import os, tempfile
        if not CROSS_DIM_BOOST_FILE.exists():
            return {"success": False, "error": "no boost data"}
        boosts = json.loads(CROSS_DIM_BOOST_FILE.read_text()).get("boosts", [])
        if not boosts:
            return {"success": False, "error": "empty boosts"}
        
        fname = Path(path).resolve().name
        dim_hints = {
            "time": "时间论", "gradient": "时间论", "void": "宇宙轮", "entropy": "宇宙轮",
            "cosmic": "宇宙轮", "redshift": "无限上下文", "compress": "无限上下文",
            "analogy": "触类旁通", "transfer": "触类旁通", "self_improve": "无师自通",
            "repair": "无师自通", "intuition": "超级直觉", "pattern": "超级直觉",
            "deduct": "举一反三", "generalize": "举一反三", "cross": "查缺补漏",
            "gap": "查缺补漏", "meta": "一元化", "center": "一元化", "diverse": "万象化",
            "mult": "万象化", "supersense": "超感", "teacher": "教员", "verifier": "教员",
            "light": "光爱", "love": "光爱", "memory": "记忆", "hippocampus": "记忆",
            "perception": "感知", "retina": "感知", "scheduler": "进化", "evolution": "进化",
        }
        file_dim = None
        for keyword, dim in dim_hints.items():
            if keyword in fname.lower():
                file_dim = dim
                break
        if not file_dim:
            return {"success": False, "error": "unknown dimension"}
        
        relevant = [b for b in boosts if b.get("dim1") == file_dim or b.get("dim2") == file_dim]
        if not relevant:
            return {"success": False, "error": "no relevant boost"}
        
        comment_lines = []
        for b in relevant[:3]:
            comment_lines.append(f"# 🜁 交叉增强[{b['pair']}]: {b['reason']}")
        
        content = Path(path).read_text() + "\\n" + "\\n".join(comment_lines) + "\\n"
        
        fd, tmp = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, str(Path(path).resolve()))
        except:
            os.unlink(tmp)
            return {"success": False, "error": "write failed"}
        
        return {"success": True, "method": f"cross_dim_learn:{relevant[0]['pair']}"}
    except Exception as e:
        return {"success": False, "error": str(e)}
'''

content2 += new_funcs
zimys.write_text(content2)
print(f"自我改进.py: patched OK ({zimys.stat().st_size} bytes)")


# ============================================================
# 3. breath_v2.py — 加 cross_dim_self_learning 到模板列表
# ============================================================
breath = CLUSTER / "breath_v2.py"
content3 = breath.read_text()

old_template_list = "'evolution_proposal_consumer']"
new_template_list = "'evolution_proposal_consumer', 'cross_dim_self_learning']"

if old_template_list not in content3:
    print("WARN: template list pattern not found in breath_v2.py, checking...")
    # Try to find it
    for line in content3.split('\\n'):
        if 'evolution_proposal_consumer' in line and 'template' in line:
            print(f"  Found: {line.strip()[:100]}")
    sys.exit(1)

content3 = content3.replace(old_template_list, new_template_list)
breath.write_text(content3)
print(f"breath_v2.py: patched OK ({breath.stat().st_size} bytes)")


# ============================================================
# 验证
# ============================================================
print()
print("=== Verification ===")
# Check dimension_radar.py
r = radar.read_text()
print(f"dimension_radar: cross_dim_boost={'✅' if 'def cross_dim_boost' in r else '❌'}")
print(f"dimension_radar: CROSS_DIM_THRESHOLD={'✅' if 'CROSS_DIM_THRESHOLD' in r else '❌'}")
print(f"dimension_radar: top_boost={'✅' if 'top_boost' in r else '❌'}")

# Check 自我改进.py
z = zimys.read_text()
print(f"自我改进: cross_dim_self_learning={'✅' if 'cross_dim_self_learning' in z else '❌'}")
print(f"自我改进: _detect_cross_dim_gap={'✅' if '_detect_cross_dim_gap' in z else '❌'}")
print(f"自我改进: _apply_cross_dim_learn={'✅' if '_apply_cross_dim_learn' in z else '❌'}")

# Check breath_v2.py
b = breath.read_text()
print(f"breath_v2: cross_dim_self_learning in list={'✅' if 'cross_dim_self_learning' in b else '❌'}")

# Module test
try:
    import sys
    sys.path.insert(0, str(CLUSTER))
    # Test dimension_radar
    from importlib import import_module
    dr = import_module("organs.dimension_radar")
    boosts = dr.cross_dim_boost()
    print(f"cross_dim_boost() 运行: {len(boosts)}条弱交叉对")
    for b in boosts[:3]:
        print(f"  {b['pair']}: {b['cross_chains']}链 → boost {b['boost']}")
    
    # Test 自我改进
    si = import_module("自我改进")
    print(f"自我改进: scan_for_improvements={'✅' if hasattr(si, 'scan_for_improvements') else '❌'}")
except Exception as e:
    print(f"Import test failed: {e}")
